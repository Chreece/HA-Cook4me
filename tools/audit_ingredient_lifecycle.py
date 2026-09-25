#!/usr/bin/env python3
"""Report offline lifecycle coverage against the actual shipped catalog."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/cook4me"


def audit():
    spec = importlib.util.spec_from_file_location("cook4me_lifecycle_audit", COMPONENT / "ingredient_lifecycle.py")
    lifecycle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lifecycle)
    data = lifecycle.load_lifecycle_data()
    payload = json.loads((COMPONENT / "catalog/merged_catalog.v1.json").read_text(encoding="utf-8"))
    lifecycle.enrich_catalog_ingredients(payload)
    covered = [row for row in payload["ingredients"] if row.get("lifecycle")]
    product_rules = [
        rule for profile in data["profiles"].values()
        for rule in profile["afterOpening"].get("rules", [])
        if rule.get("productBarcodes")
    ]
    result = {
        **payload["_runtimeLifecycleSummary"],
        "catalogIngredientRows": len(payload["ingredients"]),
        "enrichedIngredientRows": len(covered),
        "exactCanonicalNames": len(data["canonicalNames"]),
        "exactIngredientIds": len(data.get("ingredientIds", {})),
        "seasonGroups": sum(p["seasonality"]["status"] == "reviewed" for p in data["profiles"].values()),
        "openingRuleGroups": sum(bool(p["afterOpening"].get("rules")) for p in data["profiles"].values()),
        "productScopedRules": len(product_rules),
        "reviewedProductBarcodes": len({code.zfill(14) for rule in product_rules for code in rule["productBarcodes"]}),
        "sourceCount": len(data["sources"]),
    }
    if not result["coverage"]["seasonality"] or not result["coverage"]["afterOpening"]:
        raise ValueError("Shipped catalog has no applicable lifecycle evidence")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    audit()
