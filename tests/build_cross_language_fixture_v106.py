"""Actual screenshot editions resolved for a German-configured appliance."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def recipes():
    spec = importlib.util.spec_from_file_location('cross_language_catalog', ROOT / 'custom_components/cook4me/release_catalog.py')
    catalog = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(catalog)
    return [catalog.recipe_by_variant(variant, language=language, configured_language='de', country='DE', group_families=True)
            for variant, language in [('407079', 'tr'), ('321369', 'bg'), ('314559', 'ro'), ('357222', 'ar')]]


if __name__ == '__main__':
    print(json.dumps(recipes(), ensure_ascii=False))
