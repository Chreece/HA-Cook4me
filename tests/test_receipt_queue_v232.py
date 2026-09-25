"""Tax accounting and durable background updates against the real receipt store."""
import asyncio
from copy import deepcopy
import unittest
from test_receipts_v195 import m, Memory, receipt


class Tax(unittest.TestCase):
    def normalize(self, rows, taxes, total, mode='added'):
        return m.normalize_receipt({'items':rows, 'taxMode':mode, 'taxes':taxes, 'total':total}, model=True)

    def test_cent_remainder_and_no_second_tax_on_save(self):
        r=self.normalize([{'productName':str(i),'lineTotal':1} for i in range(3)], [{'amount':.2}], 3.2)
        self.assertEqual([i['lineTotal'] for i in r['items']],[1.07,1.07,1.06])
        self.assertEqual(r['taxStatus'],'allocated')
        self.assertEqual(m.normalize_receipt(r)['items'][0]['lineTotal'],1.07)

    def test_multiple_rates_exempt_deposit_and_discount(self):
        rows=[{'productName':'Milk','lineTotal':10,'taxCode':'A'},
              {'productName':'Discount','kind':'discount','lineTotal':-2,'taxCode':'A'},
              {'productName':'Soap','lineTotal':5,'taxCode':'B'},
              {'productName':'Deposit','kind':'deposit','lineTotal':.25,'taxCode':'Z'}]
        r=self.normalize(rows,[{'code':'A','amount':.56},{'code':'B','amount':.95},{'code':'Z','amount':0}],14.76)
        self.assertEqual(r['taxStatus'],'allocated')
        self.assertEqual([i['lineTotal'] for i in r['items']],[10.7,-2.14,5.95,.25])

    def test_included_vat_never_added_twice(self):
        r=self.normalize([{'productName':'Milk','lineTotal':10.7}],[{'amount':.7}],10.7,'included')
        self.assertEqual(r['items'][0]['lineTotal'],10.7)
        self.assertEqual(r['taxStatus'],'included')

    def test_ambiguous_groups_missing_price_or_total_mismatch_need_review(self):
        for rows,taxes,total in [
            ([{'productName':'Milk','lineTotal':10}],[{'code':'A','amount':.7},{'code':'B','amount':1.9}],12.6),
            ([{'productName':'Milk','lineTotal':None}],[{'amount':.7}],10.7),
            ([{'productName':'Milk','lineTotal':10}],[{'amount':.7}],11.7),
        ]:
            r=self.normalize(rows,taxes,total)
            self.assertEqual(r['taxStatus'],'needs_review')
            self.assertEqual(r['items'][0]['lineTotal'],rows[0]['lineTotal'])

    def test_unresolved_tax_blocks_add_until_line_reviewed(self):
        r=m.normalize_receipt(receipt());r.update(id='r',taxStatus='needs_review');i=r['items'][0];i['id']='i'
        with self.assertRaisesRegex(ValueError,'VAT'):m.product_payload(r,i,'e','en')
        i['taxReviewed']=True;self.assertEqual(m.product_payload(r,i,'e','en')['paid_price']['amount'],3.98)

    def test_model_only_accepts_full_length_printed_barcode(self):
        for code,expected in [('4000000000001','4000000000001'),('4000000000001111',''),('１２３４５６７８','')]:
            self.assertEqual(m.editable_item({'barcode':code},model=True)['barcode'],expected)


class Queue(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.disk=Memory();self.store=m.ReceiptDraftStore(self.disk)
        self.row=await self.store.save('alice',receipt(),processing_language='el')

    async def test_recognition_and_queue_share_one_atomic_write(self):
        self.assertEqual(self.disk.writes,1)
        fresh=m.ReceiptDraftStore(self.disk)
        work=await fresh.work();self.assertEqual(work[0]['language'],'el')
        self.assertEqual(work[0]['processing']['state'],'queued')
        self.assertEqual(work[0]['owner'],'alice')
        self.assertNotIn('owner',self.row)

    async def test_edit_claim_wins_over_inflight_enrichment(self):
        r=self.row;i=r['items'][0]
        saved=await self.store.save_item('alice',r['id'],i['id'],0,{**i,'productName':'My correction'}, {})
        self.assertFalse(await self.store.enrich_item('alice',r['id'],i,{'barcode':'4000000000001'}))
        actual=await self.store.get('alice',r['id'])
        self.assertEqual(actual['items'][0]['productName'],'My correction')
        self.assertEqual(actual['items'][0]['enrichment']['state'],'reviewed')
        with self.assertRaises(m.ReceiptConflict):await self.store.save_item('alice',r['id'],i['id'],0,i,{})

    async def test_other_item_processing_does_not_conflict_with_editor(self):
        raw=receipt();raw['items']*=2;r=await self.store.save('alice',raw,processing_language='en')
        await self.store.enrich_item('alice',r['id'],r['items'][1],{'barcode':'4000000000001'})
        result=await self.store.save_item('alice',r['id'],r['items'][0]['id'],0,{**r['items'][0],'lineTotal':5},{})
        self.assertEqual(result['items'][1]['barcode'],'4000000000001')
        self.assertEqual(result['items'][0]['lineTotal'],5)

    async def test_discard_during_processing_never_resurrects(self):
        r=self.row;i=r['items'][0]
        await self.store.discard('alice',r['id'],r['revision'],i['id'])
        self.assertFalse(await self.store.enrich_item('alice',r['id'],i,{'barcode':'4000000000001'}))
        self.assertEqual((await self.store.list('alice'))[0]['pendingCount'],0)
        loaded=await self.store.get('alice',r['id']);await self.store.discard('alice',r['id'],loaded['revision'])
        self.assertFalse(await self.store.enrich_item('alice',r['id'],i,{}))
        await self.store.progress('alice',r['id'],done=1)
        self.assertEqual(await self.store.work(),[])

    async def test_restart_preserves_partial_progress_and_retry_identity(self):
        r=self.row;i=r['items'][0]
        await self.store.progress('alice',r['id'],state='processing',stage='nutrition',done=0)
        store=m.ReceiptDraftStore(self.disk);work=await store.work()
        self.assertEqual(work[0]['items'][0]['id'],i['id'])
        self.assertEqual(work[0]['processing']['stage'],'nutrition')
        self.assertEqual((await store.get('alice',r['id']))['revision'],r['revision'])

    async def test_private_owner_and_failed_writes_are_enforced(self):
        r=self.row;i=r['items'][0]
        with self.assertRaises(ValueError):await self.store.save_item('bob',r['id'],i['id'],0,i,{})
        self.disk.fail=True
        with self.assertRaises(OSError):await self.store.enrich_item('alice',r['id'],i,{'barcode':'4000000000001'})
        self.assertEqual((await self.store.get('alice',r['id']))['items'][0]['barcode'],'')


if __name__=='__main__':unittest.main()
