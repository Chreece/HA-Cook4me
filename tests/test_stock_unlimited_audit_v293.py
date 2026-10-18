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
