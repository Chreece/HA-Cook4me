"""Regression coverage for literal Max missing ingredients semantics."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COMP=ROOT/"custom_components"/"cook4me"
FILTERS=COMP/"shared_recipe_filters.py"


def load_helpers():
    tree=ast.parse(FILTERS.read_text(encoding="utf-8"))
    names={"missing_ingredient_count","home_missing_filter_allows"}
    body=[
        node for node in tree.body
        if isinstance(node,ast.FunctionDef) and node.name in names
    ]
    assert {node.name for node in body}==names
    ns={}
    exec(compile(ast.fix_missing_locations(ast.Module(body=body,type_ignores=[])),str(FILTERS),"exec"),ns)
    return ns


def match(*statuses, fully=False):
    availability=[]
    for index,status in enumerate(statuses):
        availability.append({
            "key":f"ingredient-{index}",
            "name":f"Ingredient {index}",
            "status":status,
        })
    return {
        "ingredientAvailability":availability,
        "fullyAvailableByQuantity":fully,
        # Deliberately make quantity diagnostics disagree with presence. These
        # must not define the Max missing ingredient count.
        "quantityShortages":[{"name":"present but low"} for _ in range(9)],
        "quantityUnknown":[{"name":"present unknown unit"} for _ in range(5)],
    }


def test_only_home_plus_three_missing_allows_three_genuinely_absent():
    ns=load_helpers()
    row=match("at_home","missing","missing","missing","at_home",fully=False)
    assert ns["missing_ingredient_count"](row)==3
    assert ns["home_missing_filter_allows"](row,only_home=True,max_missing=3) is True


def test_only_home_plus_three_rejects_four_missing():
    ns=load_helpers()
    row=match("missing","missing","missing","missing","at_home",fully=False)
    assert ns["missing_ingredient_count"](row)==4
    assert ns["home_missing_filter_allows"](row,only_home=True,max_missing=3) is False


def test_present_unknown_or_incompatible_quantity_does_not_consume_missing_slot():
    ns=load_helpers()
    row=match("at_home","at_home","missing",fully=False)
    assert len(row["quantityUnknown"])==5
    assert len(row["quantityShortages"])==9
    assert ns["missing_ingredient_count"](row)==1
    assert ns["home_missing_filter_allows"](row,only_home=True,max_missing=3) is True


def test_zero_or_blank_only_home_remains_strict_quantity_aware():
    ns=load_helpers()
    uncertain=match("at_home","at_home",fully=False)
    complete=match("at_home","at_home",fully=True)
    assert ns["home_missing_filter_allows"](uncertain,only_home=True,max_missing=0) is False
    assert ns["home_missing_filter_allows"](complete,only_home=True,max_missing=0) is True
    assert ns["home_missing_filter_allows"](uncertain,only_home=True,max_missing=None) is False


def test_max_missing_without_only_home_uses_presence_not_quantity_shortages():
    ns=load_helpers()
    row=match("missing","missing","at_home",fully=False)
    assert ns["home_missing_filter_allows"](row,only_home=False,max_missing=2) is True
    assert ns["home_missing_filter_allows"](row,only_home=False,max_missing=1) is False


def test_duplicate_missing_identity_counts_once():
    ns=load_helpers()
    row={
        "ingredientAvailability":[
            {"key":"tomato","name":"Tomato","status":"missing"},
            {"key":"tomato","name":"Tomato","status":"missing"},
            {"name":"Basil","status":"missing"},
            {"name":" basil ","status":"missing"},
        ]
    }
    assert ns["missing_ingredient_count"](row)==2


def test_current_and_fallback_today_paths_share_the_same_helper():
    filters=FILTERS.read_text(encoding="utf-8")
    runtime=(COMP/"websocket_v30.py").read_text(encoding="utf-8")
    assert "if not home_missing_filter_allows(" in filters
    assert 'settings["maxMissing"]' in filters
    assert "settings[\"onlyHome\"]" in filters
    assert "settings[\"maxCost\"] is not None or settings[\"maxMissing\"] is not None" not in filters
    assert "from .shared_recipe_filters import home_missing_filter_allows" in runtime
    assert "only_home=only_home" in runtime
    assert "max_missing=max_missing" in runtime
    old='len(shortages) > int(max_missing)'
    assert old not in runtime


def test_ui_three_is_sent_both_top_level_and_in_shared_filters():
    v34=(COMP/"frontend"/"cook4me-panel-v34.js").read_text(encoding="utf-8")
    v63=(COMP/"frontend"/"cook4me-panel-v63.js").read_text(encoding="utf-8")
    assert 'maxMissing:String(c.querySelector("#todayMaxMissing")?.value||"")' in v34
    assert 'if(s.maxMissing!=="")payload.max_missing=Number(s.maxMissing)' in v34
    assert "shared_filters:filters" in v63
