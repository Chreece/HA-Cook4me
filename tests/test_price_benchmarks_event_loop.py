from pathlib import Path
import ast
import unittest

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "custom_components" / "cook4me" / "price_benchmarks.py"
INIT = ROOT / "custom_components" / "cook4me" / "__init__.py"


class PriceBenchmarkEventLoopTests(unittest.TestCase):
    def test_benchmark_json_read_is_isolated_in_explicit_sync_loader(self):
        tree = ast.parse(BENCH.read_text(encoding="utf-8"))
        funcs = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertIn("_read_groups", funcs)
        self.assertIn("warm_price_benchmarks", funcs)
        self.assertIn("_groups", funcs)

        def calls_named(node, name):
            return any(
                isinstance(child, ast.Call)
                and (
                    isinstance(child.func, ast.Attribute)
                    and child.func.attr == name
                    or isinstance(child.func, ast.Name)
                    and child.func.id == name
                )
                for child in ast.walk(node)
            )

        self.assertTrue(calls_named(funcs["_read_groups"], "read_text"))
        self.assertFalse(calls_named(funcs["_groups"], "read_text"))
        self.assertFalse(calls_named(funcs["_groups"], "open"))
        self.assertTrue(calls_named(funcs["_groups"], "get_running_loop"))

    def test_home_assistant_setup_warms_benchmarks_in_executor(self):
        source = INIT.read_text(encoding="utf-8")
        self.assertIn("from .price_benchmarks import warm_price_benchmarks", source)
        self.assertIn(
            "await hass.async_add_executor_job(warm_price_benchmarks)",
            source,
        )

    def test_event_loop_path_refuses_lazy_disk_io(self):
        source = BENCH.read_text(encoding="utf-8")
        self.assertIn("if _BENCHMARK_GROUPS is not None:", source)
        self.assertIn("asyncio.get_running_loop()", source)
        self.assertIn(
            "Cook4Me price benchmarks were not preloaded before synchronous pricing",
            source,
        )


if __name__ == "__main__":
    unittest.main()
