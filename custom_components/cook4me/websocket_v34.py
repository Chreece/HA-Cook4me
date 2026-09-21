"""Automatic country-scoped product and recipe prices."""
from __future__ import annotations

import asyncio
import time

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import callback

from . import websocket as legacy, websocket_v11 as v11
from .websocket_v32 import _authorized
from .automatic_prices import country_currency, price_settings, product_price, recipe_price, offline_recipe_price, validate_market
from .barcode import normalize_barcode
from .costs import _country, _currency, cost_store_for_bridge
from .inventory import inventory_identity
from .recipe_cost_cache import preview_cache_token
from .shopping_presentation import normalize_supermarket_language, supermarket_language_options
from .websocket_v33 import _catalog as scanner_catalog


@websocket_api.websocket_command({vol.Required('type'): 'cook4me/v34/price_settings', vol.Required('entry_id'): str,
    vol.Optional('country'): str, vol.Optional('currency'): str, vol.Optional('supermarket_language'): str,
    vol.Optional('auto_global_prices'): bool})
@websocket_api.async_response
async def ws_price_settings(hass, connection, msg):
    try:
        bridge = _authorized(hass, connection, msg)
        settings = await price_settings(bridge)
        if any(key in msg for key in ('country', 'currency', 'supermarket_language', 'auto_global_prices')):
            country = _country(msg.get('country', settings['country']))
            currency = _currency(msg.get('currency', country_currency(country) if 'country' in msg else settings['currency']))
            if not country or not currency:
                raise ValueError('Choose a country code (for example DE) and currency (for example EUR)')
            validate_market(country, currency)
            supermarket_language = normalize_supermarket_language(
                msg.get('supermarket_language', settings.get('supermarketLanguage')),
                country=country,
                fallback=settings.get('supermarketLanguage') or 'en',
            )
            requested_language = str(msg.get('supermarket_language') or '').strip().lower().replace('_', '-').split('-', 1)[0]
            if 'supermarket_language' in msg and requested_language != supermarket_language:
                raise ValueError('Choose a supported supermarket language')
            store = await cost_store_for_bridge(bridge)
            settings = await store.async_set_settings(
                country=country,
                currency=currency,
                supermarket_language=supermarket_language,
                auto_global_prices=msg.get('auto_global_prices', settings['autoGlobalPrices']),
            )
        connection.send_result(msg['id'], {
            'settings': settings,
            'supermarketLanguages': supermarket_language_options(),
            'priceCacheToken': await preview_cache_token(bridge),
        })
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command({vol.Required('type'): 'cook4me/v34/product_price', vol.Required('entry_id'): str,
    vol.Optional('barcode', default=''): str, vol.Optional('ingredient'): dict, vol.Optional('language', default='en'): str,
    vol.Optional('quantity'): vol.Any(int, float, str), vol.Optional('unit', default=''): str})
@websocket_api.async_response
async def ws_product_price(hass, connection, msg):
    try:
        bridge = _authorized(hass, connection, msg)
        barcode = normalize_barcode(msg['barcode']) if msg.get('barcode') else ''
        ingredient = None
        if msg.get('ingredient'):
            catalog = await scanner_catalog(hass, bridge, msg)
            wanted = inventory_identity(msg['ingredient'])
            ingredient = next((row for row in catalog
                               if inventory_identity({**row, 'key': row.get('key') or row.get('foodKey')
                                   or row.get('ingredientId') or row.get('id')}) == wanted
                               or inventory_identity(row) == wanted), None)
            if ingredient is None:
                raise ValueError('Choose an ingredient from the Cook4Me catalog')
            ingredient = {**ingredient, 'key': ingredient.get('key') or ingredient.get('ingredientId') or ingredient.get('id')}
        result = await product_price(bridge, barcode=barcode, ingredient=ingredient, quantity=msg.get('quantity'), unit=msg.get('unit', ''))
        result['priceCacheToken'] = await preview_cache_token(bridge)
        connection.send_result(msg['id'], result)
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command({vol.Required('type'): 'cook4me/v34/recipe_cost', vol.Required('entry_id'): str,
    vol.Required('recipe'): dict, vol.Optional('offline_only', default=False): bool})
@websocket_api.async_response
async def ws_recipe_cost(hass, connection, msg):
    try:
        bridge = _authorized(hass, connection, msg)
        if len(msg['recipe'].get('ingredients') or []) > 200:
            raise ValueError('This recipe has too many ingredients')
        if msg.get('offline_only'):
            from .release_catalog import recipe_by_variant, async_warm_release_catalog
            payload = await async_warm_release_catalog(hass)
            recipe = msg['recipe']
            if not recipe.get('ingredients'):
                recipe = recipe_by_variant(str(recipe.get('variantFunctionalId') or ''), language='en',
                    configured_language='en', country=_country(getattr(hass.config, 'country', '')))
                if not recipe:
                    raise ValueError('Recipe details are not available offline')
            # Display choices group and simplify names; costing needs each source
            # identity and its complete canonical preparation/measurement label.
            result = await offline_recipe_price(bridge, recipe, payload['ingredients'])
        else:
            catalog = await v11._ingredient_catalog(hass, bridge, 'en', refresh=False)
            result = await recipe_price(bridge, msg['recipe'], catalog.get('items', []))
        result['priceCacheToken'] = await preview_cache_token(bridge)
        connection.send_result(msg['id'], result)
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command({vol.Required('type'): 'cook4me/v34/recipe_cost_refresh',
    vol.Required('entry_id'): str, vol.Required('recipes'): vol.All([dict], vol.Length(min=1, max=32))})
@websocket_api.async_response
async def ws_recipe_cost_refresh(hass, connection, msg):
    try:
        bridge = _authorized(hass, connection, msg)
        recipes = msg['recipes']
        if any(len(recipe.get('ingredients') or []) > 200 for recipe in recipes):
            raise ValueError('This recipe has too many ingredients')
        catalog = await v11._ingredient_catalog(hass, bridge, 'en', refresh=False)
        since = time.monotonic()
        costs = await asyncio.gather(*(recipe_price(bridge, recipe, catalog.get('items', []),
                                      refresh_since=since) for recipe in recipes))
        connection.send_result(msg['id'], {'costs': costs, 'priceCacheToken': await preview_cache_token(bridge)})
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@callback
def async_register(hass):
    for command in (ws_price_settings, ws_product_price, ws_recipe_cost, ws_recipe_cost_refresh):
        websocket_api.async_register_command(hass, command)
