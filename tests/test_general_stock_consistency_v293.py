"""Complete recipe-quantity audit across finite, unlimited, unknown, missing and
explicitly linked ingredients. No Home Assistant runtime or stock writes."""
from copy import deepcopy
from pathlib import Path
import sys
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
DOMAIN=ROOT/"custom_components"/"cook4me"
pkg=types.ModuleType("stock_audit_v293")
pkg.__path__=[str(DOMAIN)]
sys.modules[pkg.__name__]=pkg

from stock_audit_v293.stock_coverage import warm_stock_catalog
from stock_audit_v293.food_intelligence import recipe_quantity_feasibility

def ingredient(key,amount=None,unit="g",name="Item"):
    return {"key":key,"foodName":name,"name":name,"quantity":amount,"unit":unit}

def finite(key="rice",amount=500,unit="g"):
    return [{"key":key,"name":key,"unit":unit,"lots":[{"id":"finite-lot", "quantity":amount}]}]

def unlimited(key="salt",links=None):
    return [{"key":key,"name":key,"unlimited":True,
             **({"ingredientLinks":links} if links else {}),
             "storageLocationId":"pantry"}]

def coverage(items,stock,availability=None):
    return recipe_quantity_feasibility({"ingredients":items},stock,availability=availability)

class GeneralStockAudit(unittest.TestCase):
    def setUp(self):
        warm_stock_catalog({"ingredients":[
            {"id":"salt","key":"salt","canonicalName":"Salt","classification":"food"},
            {"id":"salt-seasoning","canonicalName":"Salt (for seasoning)","classification":"food"},
            {"id":"pepper","key":"pepper","canonicalName":"Black Pepper","classification":"food"},
            {"id":"rice","key":"rice","canonicalName":"Rice","classification":"food"},
            {"id":"rice-ja","canonicalName":"Rice","conceptId":"concept:food:rice","classification":"food"},
            {"id":"milk","key":"milk","canonicalName":"Milk","classification":"food"},
            {"id":"soy-milk","canonicalName":"Soy Milk","classification":"food"},
            {"id":"unconfirmed","canonicalName":"Salt","needsSemanticConfirmation":True}
        ]})

    def test_unlimited_ingredients_need_no_known_recipe_quantity(self):
        # Tests source names from different recipe-language markets.
        for key,name in [("salt","Αλάτι"),("pepper","Pfeffer"),
                         ("water","水"),("sugar","설탕")]:
            with self.subTest(key=key):
                stock=unlimited(key)
                original=deepcopy(stock)
                for amount,unit in [(None,"g"),(None,""),(None,"tsp"),(10,"g"),(1,"unknown:measure")]:
                    match=coverage([ingredient(key,amount,unit,name)],stock)
                    row=match["items"][0]
                    self.assertEqual(row["coverage"],1.0,row)
                    self.assertEqual(row["status"],"enough",row)
                    self.assertTrue(row["unlimited"])
                    self.assertTrue(match["fullyAvailable"],match)
                    self.assertEqual(match["shortages"],[])
                    self.assertEqual(match["unknown"],[])
                self.assertEqual(stock,original)

    def test_unlimited_saved_assignment_and_reviewed_source_alias(self):
        stock=unlimited("pantry-salt",[{"key":"salt","name":"Salt"}])
        for key in ("salt","salt-seasoning"):
            with self.subTest(key=key):
                result=coverage([ingredient(key,None,"g","Αλάτι")],stock)
                self.assertEqual(result["items"][0]["coverage"],1.0,result)
                self.assertTrue(result["items"][0]["unlimited"])

    def test_finite_uncertain_must_stay_uncertain_and_missing_must_not_be_forgiven(self):
        cases=[
            (ingredient("rice",None,"g","米"),finite("rice"),"unknown_requirement",None),
            (ingredient("rice",1,"unreviewed:bunch","米"),finite("rice"),"incompatible_unit",None),
            (ingredient("rice",100,"g","米"),finite("rice",amount=50),"shortage",.5),
            (ingredient("rice",100,"g","米"),finite("rice",amount=100),"enough",1.0),
            (ingredient("rice",100,"g","米"),[],"shortage",0.0),
            (ingredient("milk",200,"ml","Milk"),finite("soy-milk",500,"ml"),"shortage",0.0),
            (ingredient("unconfirmed",200,"g","Αλάτι"),finite("salt"),"shortage",0.0)
        ]
        for item,stored,status,wanted in cases:
            with self.subTest(item=item,status=status):
                row=coverage([item],stored)["items"][0]
                self.assertEqual(row["status"],status,row)
                self.assertEqual(row["coverage"],wanted,row)

    def test_only_explicitly_assigned_sources_can_share_one_finite_package(self):
        stock=finite("packaged-rice",200)
        stock[0]["ingredientLinks"]=[{"key":"rice-ja","name":"米"}]
        original=deepcopy(stock)
        result=coverage([ingredient("rice-ja",150,"g","米"),
                         ingredient("rice",150,"g","쌀")],stock)
        self.assertEqual(len(result["items"]),2)
        # The catalog's reviewed rice identity can match both recipe lines,
        # but two requests must not create additional physical capacity.
        self.assertLessEqual(sum(float(x.get("availableQuantity") or 0)
                  for x in result["items"]),200+1e-6,result)
        self.assertEqual(stock,original)

    def test_source_classified_as_staple_remains_separate_from_physical_stock(self):
        row=coverage([ingredient("salt",None,"g","Salt")],[],
                     availability=[{"key":"salt","name":"Salt","status":"staple"}])["items"][0]
        self.assertEqual(row["status"],"staple")
        self.assertEqual(row["coverage"],1.0)
        self.assertNotIn("unlimited",row)

if __name__=="__main__":
    unittest.main()
