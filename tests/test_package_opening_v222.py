"""Package opening expiry, exact-lot deductions and reviewed catalog scope."""
import importlib
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
PKG='cook4me_opening_v222'
pkg=ModuleType(PKG);pkg.__path__=[str(ROOT/'custom_components/cook4me')];sys.modules[PKG]=pkg
inv=importlib.import_module(PKG+'.inventory')
opening=importlib.import_module(PKG+'.product_opening')
life=importlib.import_module(PKG+'.ingredient_lifecycle')
release=importlib.import_module(PKG+'.release_catalog')
receipts=importlib.import_module(PKG+'.receipts')

class PackageOpening(unittest.TestCase):
    def stock(self, **extra):
        return [{'key':'milk','name':'Milk','unit':'ml','lots':[
            {'id':'a','quantity':1000,'bestBefore':'2026-12-31','useWithinDays':3,'applyOpeningExpiry':True,**extra},
            {'id':'b','quantity':1000,'bestBefore':'2026-12-31','useWithinDays':3}]}]

    def request(self, **extra):
        return {'identity':'k:milk','quantity':100,'unit':'ml','lotId':'a','consume':True,
                'packageOpenings':[{'lotId':'a','applyOpeningExpiry':True}],**extra}

    def test_opening_updates_only_consumed_package(self):
        before=self.stock();snapshot=deepcopy(before)
        rows,report=inv.apply_consumption(before,[self.request()])
        a=next(lot for lot in rows[0]['lots'] if lot['id']=='a');b=next(lot for lot in rows[0]['lots'] if lot['id']=='b')
        self.assertEqual(a['quantity'],900);self.assertEqual(a['openedAt'],date.today().isoformat())
        self.assertEqual(a['effectiveBestBefore'],min('2026-12-31',(date.today()+timedelta(days=3)).isoformat()))
        self.assertNotIn('openedAt',b);self.assertEqual(before,snapshot)
        self.assertEqual(report['deductedLots'][0]['openedAt'],a['openedAt'])

    def test_review_does_not_restart_opening_clock(self):
        rows,_=inv.apply_consumption(self.stock(openedAt='2026-01-01'),[self.request()])
        a=next(lot for lot in rows[0]['lots'] if lot['id']=='a')
        self.assertEqual(a['openedAt'],'2026-01-01');self.assertEqual(a['effectiveBestBefore'],'2026-01-04')

    def test_opt_out_is_retained_through_normalization_and_history_restore(self):
        rows,report=inv.apply_consumption(self.stock(),[self.request(quantity=1000,packageOpenings=[{'lotId':'a','applyOpeningExpiry':False}])])
        lot=report['deductedLots'][0];self.assertFalse(lot['applyOpeningExpiry'])
        self.assertEqual(lot['effectiveBestBefore'],'2026-12-31')
        restored,_=inv.restore_consumption(rows,report)
        self.assertFalse(next(lot for lot in restored[0]['lots'] if lot['id']=='a')['applyOpeningExpiry'])

    def test_earlier_printed_date_caps_opening_deadline(self):
        lot=inv.normalize_inventory(self.stock(openedAt='2026-09-24',bestBefore='2026-09-25'))[0]['lots'][0]
        self.assertEqual(lot['effectiveBestBefore'],'2026-09-25');self.assertEqual(lot['bestBefore'],'2026-09-25')

    def test_no_printed_expiry_still_uses_opening_deadline(self):
        lot=inv.normalize_inventory(self.stock(openedAt='2026-09-24',noExpiry=True))[0]['lots'][0]
        self.assertEqual(lot['effectiveBestBefore'],'2026-09-27');self.assertNotIn('bestBefore',lot)

    def test_legacy_opened_dates_keep_existing_behavior(self):
        self.assertEqual(inv._effective_best_before({'openedAt':'2026-09-24','useWithinDays':3}),'2026-09-27')
        self.assertEqual(inv._effective_best_before({'openedAt':'2026-09-24','useWithinDays':3,'applyOpeningExpiry':False}),'')

    def test_unopened_with_known_window_does_not_start_clock(self):
        self.assertNotIn('openedAt',inv.normalize_inventory(self.stock())[0]['lots'][0])
        self.assertEqual(inv._effective_best_before({'useWithinDays':3,'applyOpeningExpiry':True}),'')

    def test_not_consumed_or_wrong_lot_cannot_be_marked_opened(self):
        for request in [self.request(consume=False),self.request(lotId='b'),self.request(quantity=0),self.request(packageOpenings=[{'lotId':'missing'}])]:
            with self.subTest(request=request),self.assertRaises(ValueError):inv.apply_consumption(self.stock(),[request])

    def test_missing_window_rejected_without_mutating_input(self):
        before=self.stock(useWithinDays=None);snapshot=deepcopy(before)
        with self.assertRaises(ValueError):inv.apply_consumption(before,[self.request()])
        self.assertEqual(before,snapshot)

    def test_invalid_boolean_is_not_silently_treated_as_opt_in(self):
        with self.assertRaises(ValueError):inv._lot_metadata({'applyOpeningExpiry':'false'},strict=True)

    def test_linked_ingredient_opens_owner_package_only_once(self):
        stock=self.stock(ingredientLinks=[{'key':'milk','name':'Milk'},{'key':'drink','name':'Drink'}])
        rows,report=inv.apply_consumption(stock,[self.request(identity='k:drink')])
        self.assertEqual(rows[0]['quantity'],1900);self.assertEqual(len(report['deductedLots']),1)
        self.assertTrue(next(lot for lot in rows[0]['lots'] if lot['id']=='a')['openedAt'])

    def profile(self,name):
        payload={'ingredients':[{'canonicalName':name,'classification':'food'}]}
        life.enrich_catalog_ingredients(payload)
        return life.lifecycle_profile(payload['ingredients'][0])

    def test_catalog_rules_require_exact_scope_and_confirmation(self):
        with patch.object(release,'ingredient_lifecycle_profile',return_value=self.profile('mozzarella')):
            rules=opening.opening_rules({'key':'fixture'},{'brand':'Galbani'})
            rule=next(r for r in rules if r.get('brand','').casefold()=='galbani')
            metadata={'brand':'Galbani','openingRuleId':rule['id'],'useWithinDays':999}
            with self.assertRaises(ValueError):opening.configure_opening({'key':'fixture'},metadata)
            configured=opening.configure_opening({'key':'fixture'},{**metadata,'openingConditionsConfirmed':True})
            self.assertEqual(configured['useWithinDays'],2);self.assertEqual(configured['storage'],'fridge')
            for changed in [{'brand':'Other'}, {'storage':'pantry'}]:
                with self.assertRaises(ValueError):opening.configure_opening({'key':'fixture'},{**metadata,'openingConditionsConfirmed':True,**changed})

    def test_catalog_identity_does_not_fall_back_to_display_name(self):
        self.assertEqual(opening.opening_rules({'key':'not-a-catalog-id','name':'Mozzarella'},{'brand':'Galbani'}),[])

    def test_dmbio_package_choice_keeps_distinct_intervals_and_opening_opt_in(self):
        cases=[('Tomato sauce','4066447887747',2,'2026-09-27'),
               ('Tomato sauce','4066447972153',4,'2026-09-29'),
               ('Tomato paste','4066447887716',21,'2026-10-16'),
               ('Hummus','4066447910865',3,'2026-09-28'),
               ('Canned jackfruit, drained','4066447443318',3,'2026-09-28')]
        for name,barcode,days,deadline in cases:
            with self.subTest(name=name,barcode=barcode),patch.object(release,'ingredient_lifecycle_profile',return_value=self.profile(name)):
                metadata={'brand':'dmBio','barcode':barcode,'applyOpeningExpiry':False}
                rules=opening.opening_rules({'key':'fixture'},metadata)
                self.assertEqual(len(rules),1)
                selected={**metadata,'openingRuleId':rules[0]['id']}
                with self.assertRaises(ValueError):opening.configure_opening({'key':'fixture'},selected)
                configured=opening.configure_opening({'key':'fixture'},{**selected,'openingConditionsConfirmed':True})
                self.assertEqual(configured['useWithinDays'],days)
                self.assertFalse(configured['applyOpeningExpiry'])
                self.assertNotIn('openedAt',configured)
                opened=opening.mark_package_opened({'key':'fixture'},configured,
                    {'applyOpeningExpiry':True},opened_on='2026-09-25')
                self.assertEqual(inv._effective_best_before(opened),deadline)
                self.assertEqual(opening.opening_rules({'key':'fixture'},{'brand':'dmBio'}),[])
                self.assertEqual(opening.opening_rules({'key':'fixture'},metadata|{'brand':'Alnatura'}),[])

    def test_cream_cheese_package_guidance_requires_opt_in_and_valid_identity(self):
        with patch.object(release,'ingredient_lifecycle_profile',return_value=self.profile('Cream cheese')):
            for barcode in ('00021000075997','00021000000142'):
                metadata={'brand':'Philadelphia','barcode':barcode,'applyOpeningExpiry':False}
                rules=opening.opening_rules({'key':'fixture'},metadata)
                self.assertEqual(len(rules),1)
                selected={**metadata,'openingRuleId':rules[0]['id']}
                with self.assertRaises(ValueError):opening.configure_opening({'key':'fixture'},selected)
                configured=opening.configure_opening({'key':'fixture'},{**selected,'openingConditionsConfirmed':True})
                self.assertEqual(configured['useWithinDays'],10)
                self.assertFalse(configured['applyOpeningExpiry'])
                self.assertNotIn('openedAt',configured)
                opened=opening.mark_package_opened({'key':'fixture'},configured,
                    {'applyOpeningExpiry':True},opened_on='2026-09-25')
                self.assertEqual(inv._effective_best_before(opened),'2026-10-05')
            for metadata in ({'brand':'Philadelphia'},{'barcode':'00021000000142'},
                    {'brand':'Other','barcode':'00021000000142'},
                    {'brand':'Philadelphia','barcode':'00021000083206'}):
                self.assertEqual(opening.opening_rules({'key':'fixture'},metadata),[])

    def test_cooking_applies_validated_catalog_duration(self):
        with patch.object(release,'ingredient_lifecycle_profile',return_value=self.profile('mozzarella')):
            rule=next(r for r in opening.opening_rules({'key':'milk'},{'brand':'Galbani'}) if r.get('brand','').casefold()=='galbani')
            request=self.request(packageOpenings=[{'lotId':'a','ruleId':rule['id'],'confirmed':True,'applyOpeningExpiry':True}],_openingDate='2026-09-25')
            rows,report=inv.apply_consumption(self.stock(brand='Galbani',useWithinDays=None),[request])
            lot=next(lot for lot in rows[0]['lots'] if lot['id']=='a')
            self.assertEqual(lot['useWithinDays'],2);self.assertEqual(lot['effectiveBestBefore'],'2026-09-27')
            self.assertEqual(lot['openingRuleId'],rule['id']);self.assertEqual(lot['storage'],'fridge')
            self.assertTrue(report['deductedLots'][0]['markedOpened'])
            request['packageOpenings'][0]['confirmed']=False
            with self.assertRaises(ValueError):inv.apply_consumption(self.stock(brand='Galbani',useWithinDays=None),[request])

    def test_opening_on_another_request_cannot_claim_an_unused_package(self):
        with self.assertRaises(ValueError):
            inv.apply_consumption(self.stock(),[self.request(lotId='b'),self.request(packageOpenings=[])])

    def test_manual_days_take_priority_without_catalog_rule(self):
        data={'useWithinDays':1,'applyOpeningExpiry':False,'brand':'Galbani'}
        self.assertEqual(opening.configure_opening({'key':'fixture'},data),data)

    def test_receipt_keeps_reviewed_opening_choices(self):
        raw={'id':'item','kind':'product','productName':'Milk','quantity':1,'unit':'l','packageCount':1,
             'ingredientLinks':[{'key':'milk','name':'Milk'}], 'useWithinDays':'3','openedAt':'2026-09-25',
             'applyOpeningExpiry':False,'openingRuleId':'rule','openingConditionsConfirmed':True}
        item=receipts.editable_item(raw)
        self.assertFalse(item['applyOpeningExpiry']);self.assertEqual(item['openingRuleId'],'rule')
        self.assertTrue(item['openingConditionsConfirmed'])

# Use the existing integration harness for actual add/edit handlers and durable stock.
import test_product_packages_v112 as package_routes

class OpeningSaveRoutes(unittest.IsolatedAsyncioTestCase):
    setUp=package_routes.PackageTests.setUp
    asyncTearDown=package_routes.PackageTests.asyncTearDown

    async def test_add_then_edit_keeps_printed_date_and_changes_effective_expiry(self):
        ns=await package_routes.PackageTests.api(self)
        msg=package_routes.PackageTests.message(self,package_count=1,best_before='2026-12-31',
            lot_metadata={'productName':'Fixture','openedAt':'2026-09-25','useWithinDays':3,'applyOpeningExpiry':True})
        await ns['ws_product_add'](self.hass,self.connection,msg)
        self.assertEqual(self.errors,[])
        row=self.bridge.recipe_hub.profile['houseIngredients'][0];lot=row['lots'][0]
        self.assertEqual(lot['bestBefore'],'2026-12-31');self.assertEqual(lot['effectiveBestBefore'],'2026-09-28')
        edit={**msg,'request_id':'opening-edit-fixture-0001','edit_lot_id':lot['id'],
              'expected_version':self.packages.package_version(row,lot),
              'lot_metadata':{**msg['lot_metadata'],'applyOpeningExpiry':False}}
        await ns['ws_product_add'](self.hass,self.connection,edit)
        self.assertEqual(self.errors,[])
        current=self.bridge.recipe_hub.profile['houseIngredients'][0]['lots'][0]
        self.assertFalse(current['applyOpeningExpiry']);self.assertEqual(current['effectiveBestBefore'],'2026-12-31')
        self.assertEqual(current['openedAt'],'2026-09-25')

    async def test_unopened_add_retains_choice_without_creating_an_opening_date(self):
        ns=await package_routes.PackageTests.api(self)
        msg=package_routes.PackageTests.message(self,package_count=1,best_before='2026-12-31',
            lot_metadata={'useWithinDays':3,'applyOpeningExpiry':True})
        await ns['ws_product_add'](self.hass,self.connection,msg)
        self.assertEqual(self.errors,[])
        lot=self.bridge.recipe_hub.profile['houseIngredients'][0]['lots'][0]
        self.assertNotIn('openedAt',lot);self.assertTrue(lot['applyOpeningExpiry'])
        self.assertEqual(lot['effectiveBestBefore'],'2026-12-31')

if __name__=='__main__':unittest.main()
