from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import selector

from .bridge import (
    async_discover_appliances, Cook4MeInvalidAuth, Cook4MeCloudUnavailable,
    Cook4MeDiscoveryError, Cook4MeInternalError,
)
import logging

_LOGGER = logging.getLogger(__name__)
from .const import *


class Cook4MeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 3

    def __init__(self) -> None:
        self._account_data: dict | None = None
        self._appliances: list[dict] = []
        self._discovered_ble_address: str | None = None
        self._discovered_ble_name: str | None = None

    def _account_schema(self) -> vol.Schema:
        return vol.Schema({
            vol.Required(CONF_EMAIL): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
            ),
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Required(CONF_COUNTRY, default=DEFAULT_COUNTRY): str,
            vol.Required(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): str,
        })

    async def _handle_account_input(self, user_input: dict, *, step_id: str):
        errors = {}
        data = dict(user_input)
        data[CONF_EMAIL] = data[CONF_EMAIL].strip()
        try:
            appliances = await async_discover_appliances(self.hass, data)
        except Cook4MeInvalidAuth:
            errors["base"] = "invalid_auth"
        except Cook4MeCloudUnavailable as exc:
            _LOGGER.warning("Cook4Me cloud unavailable during config flow: %s", exc)
            errors["base"] = "cloud_unavailable"
        except Cook4MeDiscoveryError as exc:
            _LOGGER.error("Cook4Me account discovery failed: %s", exc)
            errors["base"] = "discovery_failed"
        except Cook4MeInternalError as exc:
            _LOGGER.exception("Cook4Me integration setup error: %s", exc)
            errors["base"] = "internal_error"
        except ConfigEntryAuthFailed as exc:
            _LOGGER.warning("Cook4Me authentication failed during config flow: %s", exc)
            errors["base"] = "invalid_auth"
        except ConfigEntryNotReady as exc:
            _LOGGER.warning("Cook4Me setup not ready during config flow: %s", exc)
            errors["base"] = "cloud_unavailable"
        except Exception as exc:
            _LOGGER.exception("Unexpected Cook4Me setup exception: %s", exc)
            errors["base"] = "internal_error"
        else:
            if not appliances:
                errors["base"] = "no_appliances"
            elif len(appliances) == 1:
                return await self._create_for_appliance(data, appliances[0])
            else:
                self._account_data = data
                self._appliances = appliances
                return await self.async_step_appliance()

        description_placeholders = {}
        if self._discovered_ble_name:
            description_placeholders["device"] = self._discovered_ble_name
        return self.async_show_form(
            step_id=step_id,
            data_schema=self._account_schema(),
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return await self._handle_account_input(user_input, step_id="user")
        return self.async_show_form(step_id="user", data_schema=self._account_schema())

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ):
        """Handle a genuine local Cook4Me BLE advertisement.

        The matcher is based on the exact Generic_Service1/2 UUIDs used by the
        Groupe SEB Cook4Me provisioning protocol. We intentionally do not use
        broad Espressif OUI matching: that would surface unrelated ESP devices.
        """
        address = discovery_info.address.upper()
        self._discovered_ble_address = address
        self._discovered_ble_name = discovery_info.name or "Cook4Me"

        # Bluetooth discovery must have a temporary discovery unique ID so HA
        # can deduplicate discovery cards. The final config entry unique ID is
        # replaced with the account-owned IoT UUID after authentication.
        await self.async_set_unique_id(f"ble:{address}", raise_on_progress=False)
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"name": self._discovered_ble_name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(self, user_input=None):
        """Confirm a locally discovered Cook4Me and attach the KRUPS account."""
        if not self._discovered_ble_address:
            return self.async_abort(reason="discovery_expired")
        if user_input is not None:
            return await self._handle_account_input(user_input, step_id="bluetooth_confirm")
        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=self._account_schema(),
            description_placeholders={"device": self._discovered_ble_name or "Cook4Me"},
        )

    async def async_step_appliance(self, user_input=None):
        if self._account_data is None or not self._appliances:
            return self.async_abort(reason="discovery_expired")

        choices = {
            item["uuid"]: item.get("name") or f"Cook4Me {item['uuid'][-8:]}"
            for item in self._appliances
        }
        if user_input is not None:
            selected = str(user_input[CONF_DEVICE_UUID])
            appliance = next((x for x in self._appliances if x["uuid"] == selected), None)
            if appliance is None:
                return self.async_abort(reason="discovery_expired")
            return await self._create_for_appliance(self._account_data, appliance)

        return self.async_show_form(
            step_id="appliance",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_UUID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=value, label=label)
                            for value, label in choices.items()
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }),
        )

    async def _create_for_appliance(self, account_data: dict, appliance: dict):
        uuid = str(appliance["uuid"]).lower()
        # Replace any temporary BLE discovery key with the authoritative,
        # account-owned IoT UUID. This is the stable integration unique ID.
        await self.async_set_unique_id(uuid, raise_on_progress=False)
        self._abort_if_unique_id_configured()
        data = dict(account_data)
        data[CONF_DEVICE_UUID] = uuid
        data[CONF_APP_VERSION] = DEFAULT_APP_VERSION
        if self._discovered_ble_address:
            data["ble_address"] = self._discovered_ble_address
        title = appliance.get("name") or "Cook4Me"
        return self.async_create_entry(title=title, data=data)
