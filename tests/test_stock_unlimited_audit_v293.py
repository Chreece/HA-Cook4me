"""Audit physical stock against stale recipe matches: unlimited and finite foods."""
from pathlib import Path
import sys, types, unittest
from copy import deepcopy

ROOT=Path(__file__).resolve().parents[1]
COMP=ROOT/"custom_components"/"cook4me"
pkg=types.ModuleType("coverage_v293")
pkg.__path__=[str(COMP)]
sys.modules[pkg.__name__]=pkg
from coverage_v293.stock_coverage import warm_stock_catalog
from coverage_v293.food_intelligence import recipe_quantity_feasibility

def item(key, quantity=100,unit="g"):
    return {"key":key,"name":key,"foodName":key,"quantity":quantity,"unit":unit}

def stock(key, *, unlimited=False, count=200, links=None):
    row={"key":key,"name":key,"unit":"g"}
    if links:row["ingredientLinks"]=[{"key":link,"name":link} for link in links]
    if unlimited:row["unlimited"]=True
    else:row["lots"]=[{"id":key+"-lot","quantity":count}]
    return [row]

class AvailabilityAudit(unittest.TestCase):
 def setUp(self):warm_stock_catalog({"ingredients":[]})
 def check(self,ingredient,inventory,status="missing"):
    recipe={"ingredients":[ingredient]}
    before=deepcopy((recipe,inventory))
    result=recipe_quantity_feasibility(recipe,inventory,availability=[{"key":ingredient["key"],"status":status}])
    self.assertEqual(before,(recipe,inventory))
    return result["items"][0]

 def test_unlimited_salt_stale_missing_annotation(self):
    result=self.check(item("salt"),stock("salt",unlimited=True))
    self.assertEqual(result["status"],"enough")
    self.assertEqual(result["coverage"],1)
    self.assertTrue(result["unlimited"])

 def test_unlimited_with_unknown_recipe_amount(self):
    result=self.check(item("salt",None,""),stock("salt",unlimited=True))
    self.assertEqual(result["coverage"],1)
    self.assertEqual(result["status"],"enough")

 def test_unlimited_source_catalog_assignment(self):
    result=self.check(item("salt-seb-ja"),stock("salt-bin",unlimited=True,links=["salt-seb-ja"]))
    self.assertEqual(result["coverage"],1)
    self.assertEqual(result["status"],"enough")
    # The published source key must be preserved separately from the physical
    # container's identity so all recipe views can locate this quantity row.
    self.assertEqual(result["key"],"salt-seb-ja")
    self.assertEqual(result["identity"],"k:salt-bin")
    self.assertTrue(result["unlimited"])

 def test_unlimited_and_finite_stock_both_count_in_aggregate_coverage(self):
    recipe={"ingredients":[item("salt",quantity=None,unit=""),
                           item("rice",quantity=100,unit="g")]}
    inventory=[*stock("salt",unlimited=True),*stock("rice",count=50)]
    before=deepcopy((recipe,inventory))
    result=recipe_quantity_feasibility(
        recipe,inventory,
        availability=[{"key":"salt","status":"missing"},
                      {"key":"rice","status":"at_home"}],
    )
    self.assertEqual([row["status"] for row in result["items"]],["enough","shortage"])
    self.assertEqual(result["items"][0]["coverage"],1.0)
    self.assertEqual(result["items"][1]["coverage"],.5)
    self.assertEqual(result["quantityCoverage"],.75)
    self.assertEqual(result["confidence"],1.0)
    self.assertFalse(result["fullyAvailable"])
    self.assertEqual(len(result["shortages"]),1)
    self.assertEqual((recipe,inventory),before)

 def test_unlimited_staples_are_general_not_rice_or_salt_specific(self):
    for name in ("salt", "black-pepper", "water", "cooking-oil"):
        with self.subTest(ingredient=name):
            source=name+"-official"
            stored=stock(name+"-jar",unlimited=True,links=[source])
            row=self.check(item(source,None,""),stored)
            self.assertEqual(row["key"],source)
            self.assertEqual(row["identity"],"k:"+name+"-jar")
            self.assertEqual(row["status"],"enough")
            self.assertTrue(row["unlimited"])
            self.assertEqual(row["coverage"],1.0)

 def test_declared_staple_without_physical_stock_remains_excluded_from_average(self):
    recipe={"ingredients":[item("salt",None,""),item("rice",100,"g")]}
    result=recipe_quantity_feasibility(
        recipe,stock("rice",count=50),
        availability=[{"key":"salt","status":"staple"},{"key":"rice","status":"at_home"}],
    )
    self.assertEqual(result["items"][0]["status"],"staple")
    self.assertEqual(result["items"][1]["coverage"],.5)
    self.assertEqual(result["quantityCoverage"],.5)

 def test_finite_stale_missing_still_uses_actual_amount(self):
    result=self.check(item("rice",100),stock("rice",count=200))
    self.assertEqual(result["coverage"],1)
    self.assertEqual(result["status"],"enough")

 def test_finite_shortage_is_not_granted_unlimited_status(self):
    result=self.check(item("rice",200),stock("rice",count=25))
    self.assertEqual(result["coverage"],.125)
    self.assertEqual(result["status"],"shortage")

 def test_unrelated_same_name_does_not_borrow_unlimited(self):
    result=self.check(item("salt-unknown"),stock("salt",unlimited=True))
    self.assertEqual(result["status"],"shortage")
    self.assertEqual(result["coverage"],0)

 def test_no_stock_remains_missing(self):
    result=self.check(item("salt"),[])
    self.assertEqual(result["coverage"],0)

if __name__=="__main__":unittest.main()
