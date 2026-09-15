from pathlib import Path
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cook4me_ui_locale_builder_test", ROOT/"tools/build_ingredient_ui_locale.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class IngredientLocaleBuilderTests(unittest.TestCase):
    def test_translation_is_keyed_and_rejects_missing_ids_and_english_fallback(self):
        with patch.object(builder, "http_json", return_value={"message": {"content": json.dumps({"labels": [{"id": 1, "name": "Ρύζι"}, {"id": 0, "name": "Κρεμμύδι"}]})}}):
            self.assertEqual(builder.translate_batch("http://localhost", "test", "el", ["onion", "rice"]), {"onion": "Κρεμμύδι", "rice": "Ρύζι"})
        for rows in ([{"id": 0, "name": "Κρεμμύδι"}], [{"id": 0, "name": "Onion"}, {"id": 1, "name": "Rice"}], [{"id": 0, "name": "Ρύζι"}, {"id": 0, "name": "Ρύζι"}]):
            with patch.object(builder, "http_json", return_value={"message": {"content": json.dumps({"labels": rows})}}):
                with self.assertRaises(ValueError):
                    builder.translate_batch("http://localhost", "test", "el", ["onion", "rice"])

    def test_cached_locale_is_complete_and_rerun_needs_no_model_or_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            component = root/"component"
            (component/"catalog").mkdir(parents=True)
            payload = {"ingredients": [{"id": "one", "canonicalName": "Example fruit"}, {"id": "two", "canonicalName": "Example herb"}]}
            (component/"catalog/merged_catalog.v1.json").write_text(json.dumps(payload))
            output, cache = root/"output/el.json", root/"cache/el.json"
            calls = []
            def translate(url, model, language, names):
                calls.append(names)
                return {name: "Μεταφρασμένο "+name for name in names}
            with patch.object(builder, "COMPONENT", component), patch.object(builder, "http_json", side_effect=AssertionError("network was not expected")):
                builder.build("el", output, cache, "http://localhost", model="test", translate=translate)
                self.assertEqual(len(calls), 1)
                output.unlink()
                builder.build("el", output, cache, "http://localhost", translate=lambda *args: self.fail("cached names were translated again"))
            self.assertEqual(json.loads(output.read_text()), json.loads(cache.read_text()))
            self.assertEqual(len(json.loads(output.read_text())["labels"]), len(builder.presentation.labels()["el"])+2)
            self.assertEqual(json.loads((component/"catalog/merged_catalog.v1.json").read_text()), payload)

    def test_model_selection_avoids_embeddings_and_large_models(self):
        models = [{"name": "embed-model", "size": 1000}, {"name": "large:32b", "size": 20*1024**3}, {"name": "small:8b", "size": 5*1024**3}, {"name": "tiny:1b", "size": 1024**3}]
        self.assertEqual(builder.choose_model(models), "small:8b")


if __name__ == "__main__":
    unittest.main()
