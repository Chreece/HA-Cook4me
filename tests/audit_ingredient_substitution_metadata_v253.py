from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "custom_components" / "cook4me" / "catalog" / "merged_catalog.v1.json"

TARGET_NAMES = {
    "firm tofu","tofu","mushrooms","chickpeas","vegetable stock","mushroom stock",
    "oat cream","soy cream","coconut cream","oat milk","soy milk","rice milk",
    "soy yogurt","coconut yogurt","maple syrup","soy sauce","coconut aminos",
    "agar-agar","agar agar","microbial rennet","food-grade bentonite","bentonite",
    "soy-based plant cheese","cashew-based plant cheese","nutritional yeast",
    "flax egg","aquafaba","pea protein",
}


EXACT_TARGETS = (
    "Tofu", "Button mushrooms", "Mushrooms", "Chickpeas", "Vegetable stock",
    "Mushroom stock", "Coconut cream", "Oat cream", "Soy cream",
    "Oat milk", "Soy milk", "Unsweetened soy milk", "Rice milk",
    "Soy yogurt", "Coconut yogurt", "Maple syrup", "Soy sauce",
    "Coconut aminos", "Agar agar", "Agar-agar", "Microbial rennet",
    "Bentonite", "Nutritional yeast", "Flaxseed", "Ground flaxseed",
    "Aquafaba", "Pea protein", "Water", "Vegetable stock cube", "Olive oil",
    "Coconut oil", "Sugar", "Agave syrup", "Tamari", "Gluten-free soy sauce",
    "Lemon juice", "Citric acid", "Pectin", "Cornstarch", "Corn starch",
    "Soy protein", "Textured soy protein", "Natural soy yogurt", "Soy yoghurt",
    "Coconut yoghurt", "Plant-based yogurt", "Vegan cheese", "Plant-based cheese",
    "Chickpea liquid", "Chickpea water",
)


def norm(value):
    return " ".join(str(value or "").strip().casefold().replace("_"," ").split())


def main():
    payload=json.loads(CATALOG.read_text(encoding="utf-8"))
    ingredients=[row for row in payload.get("ingredients") or [] if isinstance(row,dict)]
    classes=Counter()
    concepts=0
    intelligence=0
    diet_rows=Counter()
    targets=[]
    samples=defaultdict(list)

    for row in ingredients:
        concept=str(row.get("conceptId") or "").strip()
        if concept:
            concepts+=1
        info=row.get("intelligence") if isinstance(row.get("intelligence"),dict) else {}
        if info:
            intelligence+=1
        klass=str(info.get("substitutionClass") or row.get("substitutionClass") or "").strip()
        if klass:
            classes[klass]+=1
            if len(samples[klass])<8:
                samples[klass].append({
                    "id":row.get("id"),
                    "conceptId":concept,
                    "name":row.get("canonicalName"),
                    "diets":info.get("diets") or row.get("diets"),
                })
        diets=info.get("diets") if isinstance(info.get("diets"),dict) else row.get("diets") if isinstance(row.get("diets"),dict) else {}
        for diet,state in diets.items():
            diet_rows[f"{diet}:{state}"]+=1
        name=norm(row.get("canonicalName") or row.get("name"))
        if name in TARGET_NAMES or any(name.startswith(x+" ") or name.endswith(" "+x) for x in TARGET_NAMES):
            targets.append({
                "id":row.get("id"),
                "key":row.get("key"),
                "conceptId":concept,
                "canonicalName":row.get("canonicalName"),
                "classification":row.get("classification"),
                "substitutionClass":klass,
                "diets":diets,
                "allergens":info.get("allergens") or row.get("allergens"),
            })

    exact = {}
    for wanted in EXACT_TARGETS:
        matches = [
            {
                "id": row.get("id"),
                "key": row.get("key"),
                "conceptId": row.get("conceptId"),
                "canonicalName": row.get("canonicalName"),
            }
            for row in ingredients
            if norm(row.get("canonicalName")) == norm(wanted)
        ]
        # Collapse repeated language/provider rows to distinct semantic targets.
        unique = {}
        for row in matches:
            marker = row.get("conceptId") or row.get("key") or row.get("id")
            unique.setdefault(str(marker), row)
        exact[wanted] = list(unique.values())[:8]

    report={
        "ingredientCount":len(ingredients),
        "withConceptId":concepts,
        "withIntelligence":intelligence,
        "substitutionClasses":dict(classes.most_common()),
        "classSamples":dict(samples),
        "dietStateCounts":dict(diet_rows),
        "targetCandidates":targets[:250],
    }
    print("INGREDIENT_SUBSTITUTION_METADATA_V253="+json.dumps(report,ensure_ascii=False))
    print("SUBSTITUTION_TARGET_RESOLUTION_V253="+json.dumps(exact,ensure_ascii=False))


if __name__=="__main__":
    main()
