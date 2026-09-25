"""Real receipt state machine: no HA, network, camera or user data required."""
import asyncio
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('receipt_model_v195', ROOT/'custom_components/cook4me/receipts.py')
m = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(m)


def receipt():
    return {'merchant':'Example supermarket', 'purchaseDate':'2026-09-20','currency':'EUR','total':3.98,
            'items':[{'productName':'Bio Karotten','originalName':'BIO KAROTTEN','lineTotal':'3,98','packageCount':2,
                      'quantity':500,'unit':'g','ingredientLinks':[{'key':'carrot','name':'Καρότο'}],
                      'nutrition':{'basisQuantity':100,'basisUnit':'g','values':{'protein':1.0}}}]}


class Memory:
    def __init__(self): self.data=None; self.writes=0; self.fail=False
    async def async_load(self): await asyncio.sleep(0); return deepcopy(self.data)
    async def async_save(self,data):
        await asyncio.sleep(0)
        if self.fail: raise OSError('disk fixture')
        self.data=deepcopy(data); self.writes+=1


class Normalization(unittest.TestCase):
    def test_recognition_keeps_each_printed_language_instead_of_ai_translation(self):
        raw={'items':[
            {'productName':'Ρόφημα βρώμης','originalName':'dmBio HAFERDRINK NATUR','ingredientName':'Ρόφημα βρώμης'},
            {'productName':'Κρέμα γάλακτος','originalName':'Crème fraîche 30%'},
            {'productName':'Feta cheese','originalName':'ΦΕΤΑ ΠΟΠ'},
        ]}
        rows=m.normalize_receipt(raw,model=True)['items']
        self.assertEqual([i['productName'] for i in rows],[i['originalName'] for i in raw['items']])
        self.assertEqual(rows[0]['ingredientName'],'Ρόφημα βρώμης')

    def test_source_name_fallback_and_manual_corrections_are_preserved(self):
        parsed=m.editable_item({'productName':'Bio Haferdrink','originalName':'  '},model=True)
        self.assertEqual(parsed['productName'],'Bio Haferdrink')
        self.assertEqual(parsed['originalName'],'Bio Haferdrink')
        edited=m.editable_item({**parsed,'productName':'Bio Haferdrink Natur'})
        self.assertEqual(edited['productName'],'Bio Haferdrink Natur')
        self.assertEqual(edited['originalName'],'Bio Haferdrink')

    def test_incomplete_nutrition_is_kept_until_basis_confirmed(self):
        raw=receipt();raw['items'][0]['nutrition']['basisUnit']=''
        cleaned=m.normalize_receipt(raw)
        self.assertEqual(cleaned['items'][0]['nutrition']['values']['protein'],1)
        cleaned['id']='a'*32;cleaned['items'][0]['id']='b'*32
        with self.assertRaises(ValueError):m.product_payload(cleaned,cleaned['items'][0],'entry','el')

    def test_invalid_user_price_is_not_silently_dropped(self):
        raw=receipt();raw['items'][0]['lineTotal']='not money'
        with self.assertRaises(ValueError):m.normalize_receipt(raw)
        self.assertIsNone(m.normalize_receipt(raw,model=True)['items'][0]['lineTotal'])

    def test_decimal_comma_and_unknown_prices(self):
        self.assertEqual(m.number('1,29'),1.29)
        for invalid in ('1.234,56', '€1.29', 'NaN', float('inf'), True, {}, -1):
            self.assertIsNone(m.number(invalid))
        self.assertEqual(m.number(0),0)
        self.assertEqual(m.number('-0,25',signed=True),-.25)

    def test_ai_cannot_assign_ingredients_nutrients_or_expiry(self):
        raw=receipt(); raw['items'][0].update(status='applied',payload={'evil':True},bestBefore='2030-01-01',barcode='123')
        value=m.normalize_receipt(raw,model=True)['items'][0]
        self.assertEqual(value['status'],'pending'); self.assertEqual(value['ingredientLinks'],[])
        self.assertEqual(value['nutrition']['values'],{}); self.assertEqual(value['bestBefore'],''); self.assertEqual(value['barcode'],'')
        self.assertNotIn('payload',value)

    def test_unknowns_remain_editable_and_do_not_gain_today(self):
        value=m.normalize_receipt({'items':[{'productName':'Unclear'}]},model=True)
        self.assertEqual(value['purchaseDate'],''); self.assertEqual(value['currency'],'')
        self.assertIsNone(value['items'][0]['lineTotal']); self.assertIsNone(value['items'][0]['quantity'])
        self.assertEqual(value['items'][0]['unit'],'')

    def test_ambiguous_dates_are_not_guessed(self):
        for bad in ['01/02/26','2026-02-30','20260920','2026-9-2',None]:self.assertEqual(m.iso_date(bad),'')
        self.assertEqual(m.iso_date('2026-09-20'),'2026-09-20')

    def test_no_silent_truncation_of_long_receipts(self):
        with self.assertRaises(ValueError):m.normalize_receipt({'items':[{}]*121})
        self.assertEqual(len(m.normalize_receipt({'items':[{}]*120})['items']),120)

    def test_empty_or_invalid_receipts_are_rejected(self):
        for invalid in [None,[],{}, {'items':[]},{'items':['bad']}]:
            with self.assertRaises(ValueError):m.normalize_receipt(invalid)

    def test_invalid_package_counts_are_not_silently_one(self):
        for invalid in [0,101,True,'2.5','abc']:
            raw=receipt();raw['items'][0]['packageCount']=invalid
            with self.assertRaises(ValueError):m.normalize_receipt(raw)

    def test_nutrition_basis_cannot_be_relabelled_as_100(self):
        raw=receipt();raw['items'][0]['nutrition']['basisQuantity']=50
        with self.assertRaises(ValueError):m.normalize_receipt(raw)

    def test_invalid_nutrients_are_rejected_before_any_save(self):
        raw=receipt();raw['items'][0]['nutrition']['values']['protein']=-1
        with self.assertRaises(ValueError):m.normalize_receipt(raw)

    def test_discounts_are_signed_and_keep_nonstock_kind(self):
        raw=receipt();raw['items'][0].update(kind='discount',lineTotal='-1,00')
        item=m.normalize_receipt(raw)['items'][0]
        self.assertEqual(item['lineTotal'],-1);self.assertEqual(item['kind'],'discount')

    def test_bounded_text_and_no_photo_saved(self):
        raw=receipt();raw.update(image='SECRET',owner='someone');raw['merchant']='A'*1000
        value=m.normalize_receipt(raw)
        self.assertNotIn('image',value);self.assertNotIn('owner',value);self.assertEqual(len(value['merchant']),300)


class Drafts(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.disk=Memory();self.store=m.ReceiptDraftStore(self.disk);self.raw=receipt()
        self.saved=await self.store.save('alice',self.raw)
        self.calls=[]
    async def add(self,payload):
        self.assertEqual(self.disk.data['drafts'][self.saved['id']]['items'][0]['status'],'applying')
        self.calls.append(deepcopy(payload));return {'status':'added','lotId':'lot-1','lotIds':['lot-1','lot-2'],'warnings':[]}
    async def apply(self,add=None,rev=None):
        return await self.store.apply('alice',self.saved['id'],rev or self.saved['revision'],self.saved['items'][0]['id'],
                                     entry_id='entry',language='el',add_product=add or self.add)
    async def get(self):return await self.store.get('alice',self.saved['id'])

    async def test_save_is_private_and_does_not_add_stock(self):
        self.assertEqual(len(await self.store.list('alice')),1);self.assertEqual(await self.store.list('bob'),[])
        with self.assertRaises(ValueError):await self.store.get('bob',self.saved['id'])
        self.assertEqual(self.calls,[]);self.assertNotIn('owner',self.saved)

    async def test_model_status_and_request_payload_are_not_trusted(self):
        raw=deepcopy(self.raw);raw['items'][0].update(status='applied',payload={'request_id':'stolen'})
        value=await self.store.save('alice',raw)
        self.assertEqual(value['items'][0]['status'],'pending');self.assertNotIn('payload',value['items'][0])

    async def test_stable_server_ids_and_revision(self):
        changed=deepcopy(self.saved);changed['items'][0]['productName']='Carrot'
        updated=await self.store.save('alice',changed,ident=changed['id'],revision=changed['revision'])
        self.assertEqual(updated['items'][0]['id'],changed['items'][0]['id']);self.assertEqual(updated['revision'],2)
        with self.assertRaises(m.ReceiptConflict):await self.store.save('alice',changed,ident=changed['id'],revision=1)

    async def test_item_ids_cannot_be_replaced_or_duplicated(self):
        changed=deepcopy(self.saved);changed['items'][0]['id']='other'
        with self.assertRaises(ValueError):await self.store.save('alice',changed,ident=changed['id'],revision=1)

    async def test_failed_draft_write_does_not_change_memory(self):
        self.disk.fail=True;changed=deepcopy(self.saved);changed['merchant']='Lost change'
        with self.assertRaises(OSError):await self.store.save('alice',changed,ident=changed['id'],revision=1)
        self.assertEqual((await self.get())['merchant'],self.saved['merchant'])

    async def test_incomplete_drafts_save_but_cannot_be_applied(self):
        raw={'items':[{'productName':'Unclear'}]};value=await self.store.save('alice',raw)
        with self.assertRaises(ValueError):await self.store.apply('alice',value['id'],1,value['items'][0]['id'],entry_id='entry',language='el',add_product=self.add)
        self.assertEqual(self.calls,[])

    async def test_line_total_basis_does_not_multiply_paid_cost(self):
        result=await self.apply();payload=self.calls[0]
        self.assertEqual(payload['package_count'],2);self.assertEqual(payload['quantity'],500)
        self.assertEqual(payload['paid_price']['amount'],3.98);self.assertEqual(payload['paid_price']['basisQuantity'],1000)
        self.assertAlmostEqual(payload['paid_price']['amount']*500/1000*2,3.98)
        self.assertEqual(payload['paid_price']['location'],'Example supermarket')
        self.assertEqual(payload['lot_metadata']['purchaseDate'],'2026-09-20')
        self.assertEqual(result['receipt']['items'][0]['status'],'applied')
        self.assertLessEqual(len(payload['request_id']),80)

    async def test_double_apply_does_not_call_stock_twice(self):
        a,b=await asyncio.gather(self.apply(),self.apply())
        self.assertEqual(len(self.calls),1);self.assertTrue(b['alreadyApplied'])

    async def test_unknown_failure_freezes_and_retries_exact_payload_after_restart(self):
        async def failed(payload):self.calls.append(deepcopy(payload));raise OSError('uncertain transport')
        with self.assertRaises(OSError):await self.apply(failed)
        frozen=await self.get();self.assertEqual(frozen['items'][0]['status'],'applying')
        changed=deepcopy(frozen);changed['items'][0]['quantity']=999;changed['currency']='USD'
        changed=await self.store.save('alice',changed,ident=changed['id'],revision=changed['revision'])
        self.store=m.ReceiptDraftStore(self.disk)
        result=await self.apply(rev=changed['revision'])
        self.assertEqual(self.calls[0],self.calls[1]);self.assertEqual(result['receipt']['items'][0]['status'],'applied')

    async def test_validation_failure_unfreezes_without_stock_write(self):
        class Validation(Exception):code='product_validation'
        async def invalid(payload):raise Validation('Choose catalog ingredient')
        with self.assertRaises(Validation):await self.apply(invalid)
        self.assertEqual((await self.get())['items'][0]['status'],'pending');self.assertEqual(self.calls,[])

    async def test_side_effect_warning_keeps_same_retry_request(self):
        async def warning(payload):self.calls.append(deepcopy(payload));return {'status':'added','lotId':'lot-1','warnings':['Prices need retry']}
        result=await self.apply(warning);self.assertEqual(result['receipt']['items'][0]['status'],'applying')
        await self.apply(rev=result['receipt']['revision']);self.assertEqual(self.calls[0],self.calls[1])

    async def test_final_write_failure_remains_durably_retryable(self):
        async def saved_then_disk_failure(payload):self.calls.append(deepcopy(payload));self.disk.fail=True;return {'status':'added','warnings':[]}
        with self.assertRaises(OSError):await self.apply(saved_then_disk_failure)
        self.assertEqual((await self.get())['items'][0]['status'],'applying')
        self.disk.fail=False;self.store=m.ReceiptDraftStore(self.disk);current=await self.get()
        await self.apply(rev=current['revision']);self.assertEqual(self.calls[0],self.calls[1])

    async def test_intent_failure_never_calls_inventory(self):
        self.disk.fail=True
        with self.assertRaises(OSError):await self.apply()
        self.assertEqual(self.calls,[]);self.assertEqual((await self.get())['items'][0]['status'],'pending')

    async def test_applied_items_cannot_be_reset_by_draft_save(self):
        result=await self.apply();value=result['receipt'];value['items'][0].update(status='pending',quantity=999)
        saved=await self.store.save('alice',value,ident=value['id'],revision=value['revision'])
        self.assertEqual(saved['items'][0]['status'],'applied');self.assertEqual(saved['items'][0]['quantity'],500)

    async def test_discard_individual_and_whole_draft(self):
        value=await self.store.discard('alice',self.saved['id'],1,self.saved['items'][0]['id'])
        self.assertEqual(value['items'][0]['status'],'discarded')
        with self.assertRaises(ValueError):await self.apply(rev=value['revision'])
        await self.store.discard('alice',value['id'],value['revision']);self.assertEqual(await self.store.list('alice'),[])

    async def test_unsaved_discarded_items_stay_discarded_on_save(self):
        raw=receipt();raw['items'][0]['status']='discarded';value=await self.store.save('alice',raw)
        self.assertEqual(value['items'][0]['status'],'discarded')

    async def test_applied_draft_delete_is_not_inventory_rollback(self):
        result=await self.apply();value=result['receipt'];await self.store.discard('alice',value['id'],value['revision'])
        self.assertEqual(len(self.calls),1);self.assertEqual(await self.store.list('alice'),[])

    async def test_uncertain_apply_cannot_be_discarded(self):
        async def fail(payload):raise OSError('uncertain')
        with self.assertRaises(OSError):await self.apply(fail)
        value=await self.get()
        with self.assertRaises(m.ReceiptConflict):await self.store.discard('alice',value['id'],value['revision'])

    async def test_nonproduct_is_not_stock(self):
        raw=receipt();raw['items'][0]['kind']='deposit';value=await self.store.save('alice',raw)
        with self.assertRaises(ValueError):await self.store.apply('alice',value['id'],value['revision'],value['items'][0]['id'],entry_id='entry',language='el',add_product=self.add)
        self.assertEqual(self.calls,[])

    async def test_unknown_paid_currency_and_date_need_confirmation(self):
        for key in ['purchaseDate','currency']:
            raw=receipt();raw[key]='';value=await self.store.save('alice',raw)
            with self.assertRaises(ValueError):await self.store.apply('alice',value['id'],value['revision'],value['items'][0]['id'],entry_id='entry',language='el',add_product=self.add)

    async def test_draft_limit_does_not_evict_saved_receipts(self):
        for _ in range(m.MAX_DRAFTS-1):await self.store.save('alice',self.raw)
        with self.assertRaises(ValueError):await self.store.save('alice',self.raw)
        self.assertEqual(len(await self.store.list('alice')),m.MAX_DRAFTS)
        self.assertEqual((await self.get())['id'],self.saved['id'])


if __name__=='__main__':unittest.main()
