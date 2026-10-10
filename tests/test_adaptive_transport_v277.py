"""Offline contracts for Cook4Me network selection: all routable address families,
proxy routing, and no loss of TLS authentication.

Run: python -m unittest -v tests/test_adaptive_transport_v277.py
No credentials, network access or Home Assistant required.
"""
from __future__ import annotations

from contextlib import contextmanager
import errno
import importlib.util
import os
from pathlib import Path
import socket
import ssl
import sys
import types
import unittest
from unittest.mock import patch, MagicMock

SRC = Path(__file__).resolve().parents[1] / "custom_components/cook4me/vendor/adaptive_transport.py"
SPEC = importlib.util.spec_from_file_location("cook4me_adaptive_v277", SRC)
a = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(a)


def entry(family, address, port=443):
    addr = (address, port, 0, 0) if family == socket.AF_INET6 else (address, port)
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", addr)


class NetworkFamilies(unittest.TestCase):
    def test_dual_stack_interleaves_in_dns_first_family_order(self):
        rows = [
            entry(socket.AF_INET6, "2001:db8::1"),
            entry(socket.AF_INET6, "2001:db8::2"),
            entry(socket.AF_INET, "192.0.2.1"),
            entry(socket.AF_INET, "192.0.2.2"),
        ]
        with patch.object(a.socket, "getaddrinfo", return_value=rows):
            found = a._alternating_addresses("example.invalid", 443)
        self.assertEqual([v[0] for v in found],
                         [socket.AF_INET6, socket.AF_INET, socket.AF_INET6, socket.AF_INET])
        self.assertEqual([v[-1][0] for v in found],
                         ["2001:db8::1", "192.0.2.1", "2001:db8::2", "192.0.2.2"])

    def test_ipv4_only_and_ipv6_only_are_not_forced_to_other_family(self):
        for family, ip in (
            (socket.AF_INET, "192.0.2.1"),
            (socket.AF_INET6, "2001:db8::1"),
        ):
            with self.subTest(family=family), patch.object(
                a.socket, "getaddrinfo", return_value=[entry(family, ip)]
            ):
                result = a._alternating_addresses("example.invalid", 443)
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0][0], family)

    def test_duplicate_dns_records_ignored(self):
        row = entry(socket.AF_INET, "192.0.2.1")
        with patch.object(a.socket, "getaddrinfo", return_value=[row, row, row]):
            self.assertEqual(len(a._alternating_addresses("example.invalid", 443)), 1)

    def test_empty_dns_fails_without_guessing(self):
        with patch.object(a.socket, "getaddrinfo", return_value=[]):
            with self.assertRaises(OSError):
                a.connect_tls_dual_stack("example.invalid", timeout=1)

    def test_invalid_deadline_rejected(self):
        for seconds in (0, -1):
            with self.assertRaises(ValueError):
                a.connect_tls_dual_stack("example.invalid", timeout=seconds)


class ProxyContracts(unittest.TestCase):
    @contextmanager
    def clean_proxy_env(self, **kwargs):
        names = ("wss_proxy", "WSS_PROXY", "https_proxy", "HTTPS_PROXY",
                 "all_proxy", "ALL_PROXY", "no_proxy", "NO_PROXY")
        with patch.dict(os.environ, {k: v for k, v in kwargs.items()}, clear=True):
            yield

    def test_no_proxy_prefers_direct(self):
        with self.clean_proxy_env(HTTPS_PROXY="http://proxy.invalid:3128", NO_PROXY="*"):
            self.assertIsNone(a._proxy_options("mqtt.example.invalid", 12))

    def test_https_env_proxy_is_respected(self):
        with self.clean_proxy_env(HTTPS_PROXY="http://proxy.invalid:3128"):
            p = a._proxy_options("mqtt.example.invalid", 12)
        self.assertEqual((p["http_proxy_host"], p["http_proxy_port"], p["proxy_type"]),
                         ("proxy.invalid", 3128, "http"))

    def test_socks_proxy_remote_dns_not_lost(self):
        with self.clean_proxy_env(ALL_PROXY="socks5h://user:pass@proxy.invalid:1080"):
            p = a._proxy_options("mqtt.example.invalid", 12)
        self.assertEqual(p["proxy_type"], "socks5h")
        self.assertEqual(p["http_proxy_auth"], ("user", "pass"))

    def test_https_to_proxy_must_not_silently_downgrade(self):
        with self.clean_proxy_env(HTTPS_PROXY="https://proxy.invalid:443"):
            with self.assertRaises(OSError):
                a._proxy_options("mqtt.example.invalid", 12)

    def test_proxy_connection_never_calls_direct_tls(self):
        proxy = {"http_proxy_host": "proxy.invalid", "http_proxy_port": 8080, "proxy_type": "http"}
        fake_ws = types.SimpleNamespace(create_connection=MagicMock(return_value=object()))
        with patch.dict(sys.modules, {"websocket": fake_ws}), \
             patch.object(a, "_proxy_options", return_value=proxy), \
             patch.object(a, "connect_tls_dual_stack", side_effect=AssertionError("proxy bypass")):
            a.create_mqtt_websocket("wss://example.invalid/mqtt", "example.invalid")
        self.assertEqual(fake_ws.create_connection.call_count, 1)
        self.assertEqual(fake_ws.create_connection.call_args.kwargs["http_proxy_host"], "proxy.invalid")

    def test_direct_socket_cleanup_when_ws_upgrade_fails(self):
        fake_tls = MagicMock()
        fake_ws = types.SimpleNamespace(create_connection=MagicMock(side_effect=TimeoutError))
        with patch.dict(sys.modules, {"websocket": fake_ws}), \
             patch.object(a, "_proxy_options", return_value=None), \
             patch.object(a, "connect_tls_dual_stack", return_value=fake_tls):
            with self.assertRaises(TimeoutError):
                a.create_mqtt_websocket("wss://example.invalid/mqtt", "example.invalid")
        fake_tls.close.assert_called_once()


class TLSContracts(unittest.TestCase):
    def test_default_ssl_context_verifies_identity(self):
        ctx = a._tls_context()
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)

    def test_no_protocol_downgrade(self):
        # An unsuccessful TLS connection must raise, never return a raw socket.
        with patch.object(a, "_alternating_addresses", return_value=[]):
            with self.assertRaises(OSError):
                a.connect_tls_dual_stack("example.invalid")


if __name__ == "__main__":
    unittest.main()
