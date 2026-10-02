"""Regression coverage for unconditional post-cook finite stock deduction."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=spec_from_file_location("cook4me_inventory_v272",ROOT/"custom_components/cook4me/inventory.py")
inventory=module_from_spec(SPEC);SPEC.loader.exec_module(inventory)

def test_unlimited_items_are_not_offered_for_recipe_consumption():
    recipe={"ingredients":[{"key":"salt","name":"Salt","quantity":2,"unit":"g"}]}
    stock=[{"key":"salt","name":"Salt","unlimited":True,"unit":"g"}]
    assert inventory.recipe_consumption_items(recipe,stock)==[]

def test_stale_selected_lot_falls_back_to_current_fefo_lot():
    stock=[{"key":"mint","name":"Mint","unit":"g","lots":[{"id":"current","quantity":100,"bestBefore":"2026-10-03"}]}]
    rows,report=inventory.apply_consumption(stock,[{"identity":"k:mint","name":"Mint","quantity":30,"unit":"g","consume":True,"lotId":"gone"}])
    assert rows[0]["quantity"]==70
    assert rows[0]["lots"][0]["id"]=="current"
    assert report["deducted"][0]["quantity"]==30
    assert report["deductedLots"][0]["lotId"]=="current"

def test_confirmed_over_request_consumes_whats_left_and_removes_zero_row():
    stock=[{"key":"paprika","name":"Paprika","unit":"g","lots":[{"id":"p1","quantity":25}]}]
    rows,report=inventory.apply_consumption(stock,[{"identity":"k:paprika","name":"Paprika","quantity":100,"unit":"g","consume":True}])
    assert rows==[]
    assert report["deducted"][0]["quantity"]==25
    assert report["depleted"]==[{"identity":"k:paprika","name":"Paprika"}]

def test_confirm_backend_keeps_shortfalls_as_diagnostics_instead_of_raising():
    source=(ROOT/"custom_components/cook4me/recipe_hub.py").read_text()
    block=source[source.index("async def async_confirm_consumption"):source.index("async def async_revise_consumption")]
    assert 'report["shortfalls"] = shortfalls' in block
    assert "The selected storage amount is no longer available" not in block


def test_confirmed_incompatible_units_are_not_a_silent_noop():
    stock=[{"key":"mint","name":"Mint","unit":"pcs","lots":[{"id":"mint-pack","quantity":1}]}]
    rows,report=inventory.apply_consumption(stock,[{"identity":"k:mint","name":"Mint","quantity":2,"unit":"tbsp","consume":True}])
    assert rows==[]
    assert report["deducted"][0]["quantity"]==1
    assert report["deducted"][0]["unit"]=="pcs"
