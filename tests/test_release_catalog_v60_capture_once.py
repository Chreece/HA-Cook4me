from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

spec = importlib.util.spec_from_file_location(
    "cook4me_release_catalog_v60_capture_once_test",
    TOOLS / "run_release_catalog_v60_capture_once.py",
)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def manifest(status: str, *, capture_valid: bool = True, activated: bool = False) -> dict:
    return {
        "status": status,
        "providerCaptureCount": 1,
        "captureValidation": {
            "valid": capture_valid,
            "errors": [] if capture_valid else ["capture failed"],
        },
        "finalNutritionQueue": {"pendingNutritionCount": 42},
        "activated": activated,
        "paths": {
            "nutritionQueue": "/tmp/q.json",
            "nutritionPending": "/tmp/pending.json",
            "capturedSemanticCatalog": "/tmp/capture.json",
            "candidateCatalog": "/tmp/candidate.json",
        },
    }


class ReleaseCatalogV60CaptureOnceTests(unittest.TestCase):
    def _args(self, root: Path):
        return SimpleNamespace(
            catalog_version="capture-test-v60",
            storage_home=str(root / "home"),
            configured_language="de",
            configured_country="DE",
            english_overrides="",
            workers=3,
            verbose=False,
            build_dir=str(root / "build"),
            nutrition_cache=str(root / "nutrition.json"),
            review_root=str(root / "reviews"),
            live_path=str(root / "live.json"),
            # These unsafe values must be ignored even if a caller tries to add them.
            fdc_key="must-not-pass",
            require_intelligence=True,
            activate=True,
        )

    def test_expected_nutrition_pending_is_success_and_forces_safe_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            captured_args = None

            def run_func(args):
                nonlocal captured_args
                captured_args = args
                return manifest("nutrition-review-pending")

            _raw, summary, code = mod.capture_once(self._args(root), run_func=run_func)
            self.assertEqual(code, 0)
            self.assertEqual(summary["status"], "nutrition-review-pending")
            self.assertEqual(summary["nutritionPending"], 42)
            self.assertFalse(summary["activated"])
            self.assertIsNotNone(captured_args)
            self.assertFalse(captured_args.activate)
            self.assertFalse(captured_args.require_intelligence)
            self.assertEqual(captured_args.fdc_key, "")
            self.assertEqual(captured_args.workers, 3)
            self.assertEqual(
                summary["manifest"], str(root / "build" / "release-manifest.v60.json")
            )

    def test_awaiting_fdc_key_is_still_successful_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            _raw, summary, code = mod.capture_once(
                self._args(Path(tmp)),
                run_func=lambda _args: manifest("awaiting-fdc-key"),
            )
            self.assertEqual(code, 0)
            self.assertEqual(summary["status"], "awaiting-fdc-key")

    def test_ready_for_activation_is_success_but_capture_wrapper_does_not_activate(self):
        with tempfile.TemporaryDirectory() as tmp:
            _raw, summary, code = mod.capture_once(
                self._args(Path(tmp)),
                run_func=lambda args: (
                    self.assertFalse(args.activate) or manifest("ready-for-activation")
                ),
            )
            self.assertEqual(code, 0)
            self.assertFalse(summary["activated"])

    def test_capture_validation_failure_is_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            _raw, summary, code = mod.capture_once(
                self._args(Path(tmp)),
                run_func=lambda _args: manifest(
                    "capture-validation-failed", capture_valid=False
                ),
            )
            self.assertEqual(code, 2)
            self.assertFalse(summary["captureValidationValid"])

    def test_final_validation_failure_is_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            _raw, summary, code = mod.capture_once(
                self._args(Path(tmp)),
                run_func=lambda _args: manifest("final-validation-failed"),
            )
            self.assertEqual(code, 2)
            self.assertEqual(summary["status"], "final-validation-failed")

    def test_any_activation_from_capture_only_path_is_hard_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "must never activate"):
                mod.capture_once(
                    self._args(Path(tmp)),
                    run_func=lambda _args: manifest(
                        "activated", activated=True
                    ),
                )


if __name__ == "__main__":
    unittest.main()
