"""Today generation must show real work and keep the expensive pass bounded."""
from __future__ import annotations

import ast
from pathlib import Path
import sys
import types

ROOT=Path(__file__).resolve().parents[1]
COMP=ROOT/"custom_components"/"cook4me"
PATH=COMP/"shared_recipe_runtime.py"
NAME="today_progress_v273_test"

pkg=types.ModuleType(NAME);pkg.__path__=[str(COMP)];sys.modules[NAME]=pkg
today=types.ModuleType(NAME+".today_logic")
today.recipe_identity=lambda row: str(row.get("id") or "")
today.recipe_matches_meal_types=lambda row,meals: bool(set(row.get("mealTypes") or []) & set(meals or []))
sys.modules[today.__name__]=today;setattr(pkg,"today_logic",today)

def load_function(name):
    tree=ast.parse(PATH.read_text(encoding="utf-8"))
    wanted={"_candidate_identity",name}
    body=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in wanted]
    ns={"__name__":NAME+".runtime","__package__":NAME}
    exec(compile(ast.fix_missing_locations(ast.Module(body=body,type_ignores=[])),str(PATH),"exec"),ns)
    return ns[name]

def rows(count=1000):
    return [
        {"id":f"recipe-{i}","displayFamilyId":f"family-{i}","language":"de","match":{"score":count-i}}
        for i in range(count)
    ]

def test_bounded_rotation_never_hands_the_whole_catalog_to_expensive_today_pass():
    bound=load_function("_bounded_suggestion_candidates")
    source=rows()
    target=192
    budget=min(len(source),max(target,target*2))
    first=bound(source,{"mealTypes":[]},["de"],budget,candidate_history=[])
    assert len(first)==384
    history=[row["displayFamilyId"] for row in first]
    second=bound(source,{"mealTypes":[]},["de"],budget,candidate_history=history)
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
