"""Today generation must show real work and keep the expensive pass bounded."""
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"custom_components/cook4me/shared_recipe_runtime.py"

spec=importlib.util.spec_from_file_location("shared_recipe_runtime_v273",PATH)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def rows(count=1000):
    return [
        {"displayFamilyId":f"family-{i}","language":"de","match":{"score":count-i}}
        for i in range(count)
    ]

def test_bounded_rotation_never_hands_the_whole_catalog_to_expensive_today_pass():
    source=rows()
    target=192
    budget=min(len(source),max(target,target*2))
    first=module._bounded_suggestion_candidates(
        source,{"mealTypes":[]},["de"],budget,candidate_history=[]
    )
    assert len(first)==384
    history=[row["displayFamilyId"] for row in first]
    second=module._bounded_suggestion_candidates(
        source,{"mealTypes":[]},["de"],budget,candidate_history=history
    )
    assert len(second)==384
    assert {row["displayFamilyId"] for row in first}.isdisjoint(
        {row["displayFamilyId"] for row in second}
    )

def test_source_reports_evaluated_work_not_survivor_quota():
    source=PATH.read_text(encoding="utf-8")
    processor=source[source.index("async def processor"):]
    assert "scan_budget = min(len(rows), max(target, target * 2))" in processor
    assert "batch_size = max(8, min(32, target))" in processor
    assert "progress=ranking_progress" in processor
    assert "completed=len(evaluated)" in processor
    assert "total=total_ordered or 1" in processor
    assert "completed=min(len(accepted), target)" not in processor
    assert "len(rows) or 1,\n                candidate_history=candidate_history" not in processor
