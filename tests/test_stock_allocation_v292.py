"""An explicit multilingual stock assignment must carry through lot allocation.

Production code, read-only stock and catalog identities. No HA services,
network requests, user inventory or permanent stock changes.
"""
from copy import deepcopy
from pathlib import Path
import sys
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
COMPONENT=ROOT/"custom_components"/"cook4me"
P="coverage_v292"
pkg=types.ModuleType(P)
pkg.__path__=[str(COMPONENT)]
sys.modules[P]=pkg

from coverage_v292.stock_coverage import warm_stock_catalog
from coverage_v292.food_intelligence import recipe_quantity_feasibility
from coverage_v292.stock_allocation import allocate_stock
from coverage_v292.inventory import stock_for_ingredient

def requirement(key,amount=150,unit="g",name="米"):
    return {"key":key,"foodName":name,"name":name,"quantity":amount,"unit":unit}

def imported_package(*, quantity=200, links=None):
    return [{
      "key":"packaged-rice","name":"Rice product","unit":"g",
      "ingredientLinks":links if links is not None else [
          {"key":"rice-ja","name":"米"},
          {"key":"rice-ko","name":"쌀"}
      ],
      "lots":[{"id":"lot-rice-1","quantity":quantity,
               "storageLocationId":"pantry"}]
    }]

class MultilingualStockLotAssignment(unittest.TestCase):
    def setUp(self):
        warm_stock_catalog({"ingredients":[]})

    def test_read_only_inventory_match_is_not_lost_in_flow_allocation(self):
        stock=imported_package()
        item=requirement("rice-ja",amount=150)
        self.assertIsNotNone(stock_for_ingredient(stock,item))
        before=deepcopy((stock,item))
        result=recipe_quantity_feasibility({"ingredients":[item]},stock)
        row=result["items"][0]
        self.assertEqual(row["status"],"enough",row)
        self.assertEqual(row["coverage"],1.0,row)
        self.assertEqual(row["ingredientIndex"],0)
        self.assertTrue(result["fullyAvailable"])
        self.assertEqual((stock,item),before)

    def test_korean_and_japanese_assignments_share_one_physical_package(self):
        stock=imported_package(quantity=200)
        recipe={"ingredients":[requirement("rice-ja",150),requirement("rice-ko",150,name="쌀")]}
        result=recipe_quantity_feasibility(recipe,stock)
        rows=result["items"]
        self.assertEqual(sorted(r["coverage"] for r in rows),[round(50/150,3),1.0],rows)
        self.assertEqual(result["quantityCoverage"],.667,result)
        self.assertFalse(result["fullyAvailable"])
        self.assertEqual(len(result["shortages"]),1)

    def test_unrelated_translated_name_is_not_a_verified_identity(self):
        stock=imported_package()
        item=requirement("rice-unrelated",100,name="米")
        row=recipe_quantity_feasibility({"ingredients":[item]},stock)["items"][0]
        self.assertEqual(row["coverage"],0.0,row)
        self.assertEqual(row["status"],"shortage")

    def test_only_lot_links_also_match_without_row_links(self):
        stock=imported_package(links=[])
        stock[0]["lots"][0]["ingredientLinks"]=[{"key":"rice-ja","name":"米"}]
        row=recipe_quantity_feasibility({"ingredients":[requirement("rice-ja")]},stock)["items"][0]
        self.assertEqual(row["coverage"],1.0,row)

    def test_exact_unknown_unit_is_not_misreported_as_missing(self):
        stock=imported_package()
        row=recipe_quantity_feasibility(
            {"ingredients":[requirement("rice-ja",1,unit="some-unverified-unit")]},stock
        )["items"][0]
        self.assertEqual(row["status"],"incompatible_unit",row)
        self.assertIsNone(row["coverage"])

    def test_read_only_stock_aliases_propagate_to_lot_graph(self):
        stock=[{
            "key":"packaged-rice","name":"Packaged rice","unit":"g",
            "identities":["k:rice-ja"],
            "lots":[{"id":"lot-one","quantity":200}]
        }]
        from coverage_v292.stock_allocation import allocate_stock
        rows=allocate_stock(stock,[{**requirement("rice-ja",150),"consume":True}])
        self.assertEqual(rows[0]["quantity"],150.0,rows)
        self.assertEqual(rows[0]["lots"][0]["sourceIdentity"],"k:packaged-rice")

if __name__=="__main__":
    unittest.main()
