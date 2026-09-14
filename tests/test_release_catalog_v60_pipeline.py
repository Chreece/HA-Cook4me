from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
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
    "cook4me_release_catalog_v60_pipeline_test",
    TOOLS / "run_release_catalog_v60_pipeline.py",
)
assert spec is not None and spec.loader is not None
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


def captured_catalog() -> dict:
    return {
        "schemaVersion": 1,
        "catalogVersion": "test-v60",
        "complete": True,
        "source": {
            "semanticCoverageComplete": True,
            "reviewedNutritionComplete": False,
        },
        "ingredients": [],
        "recipes": [],
    }


def valid_result() -> dict:
    return {"valid": True, "errors": [], "warnings": [], "stats": {}}


def task_queue(pending: bool = True) -> tuple[dict, dict]:
    tasks = (
        [
            {
                "ingredientId": "M_FOOD_TOMATO",
                "canonicalEnglishName": "Tomato",
                "identityKind": "provider",
                "usageCount": 3,
                "usedByRecipe": True,
            }
        ]
        if pending
        else []
    )
    return (
        {
            "schemaVersion": 1,
            "kind": "cook4me-release-catalog-nutrition-queue-v60",
            "identityPolicy": {
                "providerIdentityInference": False,
                "ambiguousExcluded": True,
                "reviewedExactFdcProvenanceRequired": True,
                "searchResultAutoAccepted": False,
            },
            "taskCount": len(tasks),
            "tasks": tasks,
        },
        {
            "foodIdentityCount": 1,
            "resolvedNutritionCount": 0 if pending else 1,
            "pendingNutritionCount": len(tasks),
            "usedPendingCount": len(tasks),
        },
    )


class ReleaseCatalogV60PipelineTests(unittest.TestCase):
    def _args(self, root: Path, **overrides):
        values = {
            "catalog_version": "test-v60",
            "storage_home": str(root / "home"),
            "configured_language": "de",
            "configured_country": "DE",
            "english_overrides": "",
            "workers": 2,
            "verbose": False,
            "build_dir": str(root / "build"),
            "nutrition_cache": str(root / "reviewed-cache.json"),
            "review_root": str(root / "reviews"),
            "fdc_key": "",
            "live_path": str(root / "live" / "merged_catalog.v1.json"),
            "require_intelligence": False,
            "activate": False,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_ready_pipeline_captures_once_and_atomically_activates_exact_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root, fdc_key="test", activate=True)
            build_calls: list[object] = []
            queue_calls = 0
            fetch_calls: list[tuple[int, str]] = []

            def build_func(build_args):
                build_calls.append(build_args)
                self.assertTrue(build_args.allow_missing_nutrition)
                self.assertFalse(build_args.resolve_nutrition)
                self.assertEqual(
                    json.loads(Path(build_args.nutrition_cache).read_text(encoding="utf-8")),
                    {},
                )
                return captured_catalog()

            def queue_func(catalog, _cache):
                nonlocal queue_calls
                queue_calls += 1
                pending = not bool((catalog.get("source") or {}).get("reviewedNutritionComplete"))
                return task_queue(pending=pending)

            def review_loader(_root):
                return {
                    "M_FOOD_TOMATO": {
                        "ingredientId": "M_FOOD_TOMATO",
                        "canonicalEnglishName": "Tomato",
                        "fdcId": 123,
                    }
                }

            def fdc_fetcher(fdc_id, api_key):
                fetch_calls.append((fdc_id, api_key))
                return {"fdcId": fdc_id}

            def resolve_func(queue, cache, reviews, *, fetcher):
                self.assertEqual(queue["taskCount"], 1)
                self.assertIn("M_FOOD_TOMATO", reviews)
                fetcher(123)
                resolved = dict(cache)
                resolved["M_FOOD_TOMATO"] = {"reviewed": True}
                return resolved, {
                    "summary": {
                        "queueTaskCount": 1,
                        "resolvedNow": 1,
                        "pendingCount": 0,
                        "secretsPersisted": False,
                    },
                    "pending": [],
                }

            def finalize_func(catalog, cache):
                self.assertIn("M_FOOD_TOMATO", cache)
                result = deepcopy(catalog)
                result["source"]["reviewedNutritionComplete"] = True
                return result

            manifest = pipeline.run_pipeline(
                args,
                build_func=build_func,
                validate_func=lambda *_args, **_kwargs: valid_result(),
                queue_func=queue_func,
                review_loader=review_loader,
                resolve_func=resolve_func,
                fdc_fetcher=fdc_fetcher,
                finalize_func=finalize_func,
            )

            self.assertEqual(len(build_calls), 1)
            self.assertEqual(queue_calls, 2)
            self.assertEqual(fetch_calls, [(123, args.fdc_key)])
            self.assertTrue(manifest["readyForActivation"])
            self.assertTrue(manifest["activated"])
            self.assertEqual(manifest["status"], "activated")
            self.assertEqual(manifest["providerCaptureCount"], 1)
            candidate = Path(manifest["paths"]["candidateCatalog"])
            live = Path(manifest["paths"]["liveCatalog"])
            self.assertEqual(candidate.read_bytes(), live.read_bytes())
            self.assertEqual(manifest["candidateSha256"], manifest["activatedSha256"])
            self.assertNotIn("fdc_key", manifest)
            self.assertTrue(manifest["fdcKeyProvided"])

    def test_reviewed_pending_task_without_fdc_key_refuses_resolution_and_activation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root, activate=True)
            build_count = 0

            def build_func(_args):
                nonlocal build_count
                build_count += 1
                return captured_catalog()

            def queue_func(catalog, _cache):
                pending = not bool((catalog.get("source") or {}).get("reviewedNutritionComplete"))
                return task_queue(pending=pending)

            def resolve_must_not_run(*_args, **_kwargs):
                self.fail("resolver must not perform reviewed FDC fetches without a key")

            manifest = pipeline.run_pipeline(
                args,
                build_func=build_func,
                validate_func=lambda *_args, **_kwargs: valid_result(),
                queue_func=queue_func,
                review_loader=lambda _root: {
                    "M_FOOD_TOMATO": {"ingredientId": "M_FOOD_TOMATO", "fdcId": 123}
                },
                resolve_func=resolve_must_not_run,
                finalize_func=lambda catalog, _cache: deepcopy(catalog),
            )

            self.assertEqual(build_count, 1)
            self.assertEqual(manifest["status"], "awaiting-fdc-key")
            self.assertFalse(manifest["readyForActivation"])
            self.assertFalse(manifest["activated"])
            self.assertEqual(manifest["reviewedTasksAwaitingFetch"], 1)
            self.assertFalse(Path(args.live_path).exists())

    def test_unreviewed_pending_task_stays_pending_and_never_activates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root, activate=True)

            def resolve_func(queue, cache, reviews, *, fetcher):
                self.assertFalse(reviews)
                self.assertEqual(queue["taskCount"], 1)
                return dict(cache), {
                    "summary": {
                        "queueTaskCount": 1,
                        "missingReview": 1,
                        "pendingCount": 1,
                        "secretsPersisted": False,
                    },
                    "pending": list(queue["tasks"]),
                }

            manifest = pipeline.run_pipeline(
                args,
                build_func=lambda _args: captured_catalog(),
                validate_func=lambda *_args, **_kwargs: valid_result(),
                queue_func=lambda _catalog, _cache: task_queue(True),
                review_loader=lambda _root: {},
                resolve_func=resolve_func,
                finalize_func=lambda catalog, _cache: deepcopy(catalog),
            )

            self.assertEqual(manifest["status"], "nutrition-review-pending")
            self.assertFalse(manifest["readyForActivation"])
            self.assertFalse(Path(args.live_path).exists())

    def test_final_validation_failure_refuses_activation_even_with_zero_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root, activate=True)
            validation_calls = 0

            def validate_func(_catalog, **_kwargs):
                nonlocal validation_calls
                validation_calls += 1
                if validation_calls == 1:
                    return valid_result()
                return {
                    "valid": False,
                    "errors": ["tampered derived index"],
                    "warnings": [],
                    "stats": {},
                }

            def finalize_func(catalog, _cache):
                result = deepcopy(catalog)
                result["source"]["reviewedNutritionComplete"] = True
                return result

            manifest = pipeline.run_pipeline(
                args,
                build_func=lambda _args: captured_catalog(),
                validate_func=validate_func,
                queue_func=lambda catalog, _cache: task_queue(
                    pending=not bool((catalog.get("source") or {}).get("reviewedNutritionComplete"))
                ),
                review_loader=lambda _root: {},
                resolve_func=lambda _queue, cache, _reviews, **_kwargs: (
                    dict(cache),
                    {"summary": {"pendingCount": 0}, "pending": []},
                ),
                finalize_func=finalize_func,
            )

            self.assertEqual(validation_calls, 2)
            self.assertEqual(manifest["status"], "final-validation-failed")
            self.assertFalse(manifest["readyForActivation"])
            self.assertFalse(Path(args.live_path).exists())

    def test_capture_validation_failure_stops_before_queue_or_activation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root, activate=True)
            queue_called = False

            def queue_must_not_run(_catalog, _cache):
                nonlocal queue_called
                queue_called = True
                self.fail("queue must not run after capture validation failure")

            manifest = pipeline.run_pipeline(
                args,
                build_func=lambda _args: captured_catalog(),
                validate_func=lambda *_args, **_kwargs: {
                    "valid": False,
                    "errors": ["capture incomplete"],
                    "warnings": [],
                    "stats": {},
                },
                queue_func=queue_must_not_run,
            )

            self.assertFalse(queue_called)
            self.assertEqual(manifest["status"], "capture-validation-failed")
            self.assertFalse(manifest["activated"])
            self.assertFalse(Path(args.live_path).exists())


if __name__ == "__main__":
    unittest.main()
