"""Cook4Me: real command dispatch must skip AWS only for account discovery.

Exercise the actual functions from the shipped vendor client without importing
its cloud SDK or issuing network requests.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "custom_components/cook4me/vendor/cook4me_auto.py"


def functions():
    tree = ast.parse(CLIENT.read_text(encoding="utf-8"))
    picked = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in {"prepare", "main"}
    ]
    if {node.name for node in picked} != {"prepare", "main"}:
        raise AssertionError("Required vendor entry points not found")
    module = ast.fix_missing_locations(ast.Module(body=picked, type_ignores=[]))
    ns = {
        "__name__": "_cook4me_discovery_test",
        "argparse": argparse,
        "Path": Path,
        "sys": sys,
        "DEFAULT_APP_VERSION": "36.0.0-RC3",
        "TOKENS": Path("/not-used/tokens.json"),
        "AWS": Path("/not-used/aws.json"),
        "JSON_LINES": False,
    }
    exec(compile(module, str(CLIENT), "exec"), ns)
    return ns


def noop(*args, **kwargs):
    raise AssertionError("Unexpected cloud/AWS operation")


class DiscoveryWithoutAWSTests(unittest.TestCase):
    def test_prepare_skips_unnecessary_aws_for_discovery(self):
        ns = functions()
        client = SimpleNamespace(
            read_apk_config=Mock(return_value={"region": "eu-west-1"}),
            load_json=noop,
            aws_credentials=noop,
        )
        ns.update(
            c4m=client,
            token_valid=lambda: True,
            aws_valid=noop,
            run_auth=noop,
        )
        args = SimpleNamespace(apk=None, force_login=False, auth_only=False)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = ns["prepare"](args, require_aws=False)
        self.assertEqual(result, ({"region": "eu-west-1"}, None))
        client.read_apk_config.assert_called_once_with(None)

    def test_normal_watcher_bootstrap_still_uses_aws(self):
        ns = functions()
        cloud_creds = {"opaque": "temporary"}
        client = SimpleNamespace(
            read_apk_config=Mock(return_value={"region": "eu-west-1"}),
            load_json=Mock(return_value=cloud_creds),
            aws_credentials=noop,
        )
        ns.update(c4m=client, token_valid=lambda: True, aws_valid=lambda: True, run_auth=noop)
        args = SimpleNamespace(apk=None, force_login=False, auth_only=False, force_aws=False)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = ns["prepare"](args, require_aws=True)
        self.assertEqual(result, ({"region": "eu-west-1"}, cloud_creds))
        client.load_json.assert_called_once()

    def test_cli_discover_passes_no_aws_credentials(self):
        ns = functions()
        prepared = []
        calls = []
        output = []
        ns["prepare"] = lambda args, **kw: (
            prepared.append((args.command, kw.get("require_aws"))) or ({"api": "ok"}, None)
        )
        ns["c4m"] = SimpleNamespace(
            load_json=lambda _p: {"access_token": "opaque"},
            discover_appliances=lambda cfg, creds, tokens, country, language, version: (
                calls.append((creds, country, language, version)) or [{"uuid": "test-device"}]
            ),
        )
        ns["dump"] = output.append
        original = sys.argv
        try:
            sys.argv = ["cook4me_auto.py", "--json-lines", "discover"]
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                ns["main"]()
        finally:
            sys.argv = original
        self.assertEqual(prepared, [("discover", False)])
        self.assertEqual(calls[0][:3], (None, "DE", "de"))
        self.assertEqual(len(output[0]["appliances"]), 1)

    def test_cli_status_still_requires_aws(self):
        ns = functions()
        requested = []
        ns["prepare"] = lambda args, **kw: (
            requested.append((args.command, kw.get("require_aws"))) or ({"region": "eu-west-1"}, {"aws": True})
        )
        ns["c4m"] = SimpleNamespace(cooking_status=lambda cfg, creds: {"active": False})
        ns["dump"] = lambda result: None
        original = sys.argv
        try:
            sys.argv = ["cook4me_auto.py", "status"]
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                ns["main"]()
        finally:
            sys.argv = original
        self.assertEqual(requested, [("status", True)])


if __name__ == "__main__":
    unittest.main()
