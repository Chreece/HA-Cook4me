"""Exercise the real installer without contacting or restarting a real server."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "tools/deploy_offline_runtime_v86.sh"
COMMIT = "849280cf7e6ee2e2af089f47532301a900f08900"
FAKE_COMMAND = r'''#!/usr/bin/env python3
import json, os, pathlib, shutil, subprocess, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
root = pathlib.Path(os.environ["DEPLOY_TEST_ROOT"])
scenario = os.environ["DEPLOY_TEST_SCENARIO"]
with (root / "calls").open("a") as log:
    log.write(json.dumps([name, *args]) + "\n")
config = root / "config"
if name == "git":
    if args[0] == "init":
        pathlib.Path(args[-1]).mkdir()
    elif "checkout" in args:
        staged = pathlib.Path(args[1]) / "custom_components/cook4me"
        shutil.copytree(os.environ["DEPLOY_TEST_COMPONENT"], staged,
                        ignore=shutil.ignore_patterns("__pycache__", "frontend"))
        (staged / "frontend").mkdir(parents=True)
        (staged / "frontend/cook4me-panel-v86-bundle.js").write_text("new panel\n")
        if scenario == "missing_prices":
            (staged / "catalog/observed_prices.v1.json").unlink()
        if scenario in ("invalid_prices", "truncated_prices"):
            prices_path = staged / "catalog/observed_prices.v1.json"
            payload = json.loads(prices_path.read_text())
            if scenario == "invalid_prices":
                payload["schemaVersion"] = 999
            else:
                payload["observations"].pop()
            prices_path.write_text(json.dumps(payload))
        if scenario == "missing_retail":
            (staged / "catalog/retail_prices.v1.json").unlink()
        (staged / "installed.txt").write_text("new")
        if scenario == "missing_locale":
            (staged / "catalog_ui_locales/el.json").unlink()
    elif "rev-parse" in args:
        print("849280cf7e6ee2e2af089f47532301a900f08900")
elif name == "docker":
    if args[0] == "inspect":
        if "State.Running" in args[2]:
            print("true")
        else:
            print(json.dumps([{"Destination": "/config", "Type": "bind", "RW": True,
                "Source": str(config if scenario != "wrong_mount" else root / "other-config")}]))
    elif args[0] == "exec":
        if "unittest" in args and scenario == "preflight_failure":
            sys.exit(1)
        if "--interactive" in args:
            code = sys.stdin.read()
            python_args = args[args.index("python") + 1:]
            python_args = [str(config / value.removeprefix("/config/"))
                           if value.startswith("/config/") else value for value in python_args]
            result = subprocess.run([sys.executable, *python_args], input=code, text=True)
            if result.returncode:
                sys.exit(result.returncode)
            if scenario == "probe_failure" and "/config/custom_components/cook4me" in args:
                sys.exit(1)
    elif args[0] == "stop":
        (root / "running").write_text("false")
    elif args[0] == "start":
        if scenario == "start_failure" and not (root / "start_failed").exists():
            (root / "start_failed").touch()
            sys.exit(1)
        (root / "running").write_text("true")
elif name == "curl":
    if "-o" in args:
        if scenario == "panel_failure":
            sys.exit(22)
        pathlib.Path(args[args.index("-o") + 1]).write_text("new panel\n")
elif name == "python3":
    if args and args[0].endswith("build_ingredient_ui_locale.py"):
        if scenario == "translation_failure":
            sys.exit(1)
        output = pathlib.Path(args[args.index("--output") + 1])
        output.parent.mkdir(parents=True)
        output.write_text("{}")
    else:
        os.execv(sys.executable, [sys.executable, *args])
elif name == "mv":
    if scenario == "swap_failure" and args[0].endswith("source/custom_components/cook4me"):
        sys.exit(1)
    shutil.move(args[0], args[1])
'''


@unittest.skipUnless(os.geteuid() == 0, "Installer integration test uses root-owned temporary files")
class DeploymentTests(unittest.TestCase):
    def run_install(self, scenario):
        temporary = tempfile.TemporaryDirectory(prefix="cook4me-deploy-test-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        config = root / "config"
        target = config / "custom_components/cook4me"
        target.mkdir(parents=True)
        (target / "installed.txt").write_text("original")
        storage = config / ".storage/cook4me"
        storage.mkdir(parents=True)
        (storage / "profile").write_text("preserve profile")
        (root / "running").write_text("true")
        bin_dir = root / "bin"
        bin_dir.mkdir()
        for name in ("git", "docker", "curl", "mv", "python3"):
            executable = bin_dir / name
            executable.write_text(FAKE_COMMAND.replace("#!/usr/bin/env python3", "#!"+sys.executable))
            executable.chmod(0o755)
        env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}",
                   COOK4ME_CONFIG=str(config), COOK4ME_CONTAINER="test-homeassistant",
                   COOK4ME_HEALTH_SECONDS="1", COOK4ME_UI_LANGUAGE="el",
                   DEPLOY_TEST_COMPONENT=str(SCRIPT.parents[1] / "custom_components/cook4me"),
                   DEPLOY_TEST_ROOT=str(root), DEPLOY_TEST_SCENARIO=scenario)
        result = subprocess.run(["bash", str(SCRIPT)], env=env, text=True, capture_output=True, timeout=90)
        self.assertEqual((storage / "profile").read_text(), "preserve profile")
        self.assertEqual((root / "running").read_text(), "true", result.stdout + result.stderr)
        calls = [json.loads(line) for line in (root / "calls").read_text().splitlines()]
        return result, root, target, calls

    def test_success_keeps_backup_and_installs_pinned_complete_component(self):
        result, root, target, calls = self.run_install("success")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((target / "installed.txt").read_text(), "new")
        runs = list((root / "config/.cook4me-deploy").glob("v86-*"))
        self.assertEqual(len(runs), 1)
        self.assertEqual((runs[0] / "previous-cook4me/installed.txt").read_text(), "original")
        self.assertEqual((runs[0] / "installed-commit.txt").read_text().strip(), COMMIT)
        self.assertIn("DEPLOYMENT PASSED", result.stdout)
        self.assertEqual(result.stdout.count("Offline price snapshot: 377 observations"), 2)
        probes = [i for i, call in enumerate(calls) if "--interactive" in call]
        stop = next(i for i, call in enumerate(calls) if call[:2] == ["docker", "stop"])
        self.assertEqual(len(probes), 2)
        self.assertLess(probes[0], stop)
        self.assertGreater(probes[1], stop)
        self.assertTrue(any("test_product_capture_v78.py" in call for call in calls))
        self.assertTrue(any("test_automatic_prices_v79.py" in call for call in calls))
        self.assertTrue(any("test_ingredient_endpoint_v80.py" in call for call in calls))
        self.assertTrue(any("test_device_state_v81.py" in call for call in calls))
        self.assertTrue(any("test_price_refresh_v82.py" in call for call in calls))
        self.assertTrue(any("test_diet_profiles_v83.py" in call for call in calls))
        self.assertTrue(any("test_price_coverage_v84.py" in call for call in calls))
        self.assertTrue(any("test_offline_catalog_v84.py" in call for call in calls))
        self.assertTrue(any("test_offline_prices_v85.py" in call for call in calls))
        self.assertTrue(any("test_recipe_cost_coverage_v86.py" in call for call in calls))
        self.assertTrue(any("test_diet_send_v77.py" in call for call in calls))
        self.assertFalse(any("ollama" in str(call).lower() or "build_ingredient_ui_locale.py" in str(call) for call in calls))
        self.assertTrue(any(call[0] == "git" and "fetch" in call and call[-1] == COMMIT for call in calls))

    def test_missing_bundled_locale_leaves_installation_and_container_untouched(self):
        result, _, target, calls = self.run_install("missing_locale")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((target / "installed.txt").read_text(), "original")
        self.assertFalse(any(call[:2] == ["docker", "stop"] for call in calls))

    def test_missing_offline_price_file_leaves_installation_untouched(self):
        for scenario in ("missing_prices", "missing_retail"):
            with self.subTest(scenario=scenario):
                result, _, target, calls = self.run_install(scenario)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((target / "installed.txt").read_text(), "original")
                self.assertFalse(any(call[:2] == ["docker", "stop"] for call in calls))

    def test_invalid_snapshot_is_rejected_before_home_assistant_stops(self):
        for scenario, message in (("invalid_prices", "unsupported schema"),
                                  ("truncated_prices", "expected 371 observations, found 370")):
            with self.subTest(scenario=scenario):
                result, _, target, calls = self.run_install(scenario)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertEqual((target / "installed.txt").read_text(), "original")
                self.assertFalse(any(call[:2] == ["docker", "stop"] for call in calls))

    def test_wrong_config_mount_is_rejected_before_source_fetch(self):
        result, _, target, calls = self.run_install("wrong_mount")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((target / "installed.txt").read_text(), "original")
        self.assertFalse(any(call[0] == "git" for call in calls))

    def test_failed_activation_restores_original_and_restarts_home_assistant(self):
        for scenario in ("probe_failure", "panel_failure", "start_failure", "swap_failure"):
            with self.subTest(scenario=scenario):
                result, _, target, calls = self.run_install(scenario)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((target / "installed.txt").read_text(), "original")
                self.assertIn("Previous integration restored", result.stderr)
                self.assertTrue(any(call[:2] == ["docker", "start"] for call in calls))
                self.assertNotIn("DEPLOYMENT PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
