"""Real product handler and durable ledger, with controlled HA/storage boundaries."""
import asyncio
from copy import deepcopy
import hashlib
import json
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from test_scanner_routes_v194 import production_functions
import test_receipt_routes_v195 as receipt_routes


class ProductSave(unittest.IsolatedAsyncioTestCase):
    def environment(self):
        hub = receipt_routes.DurableScannerLedger().hub()
        type(hub).profile = property(lambda self: deepcopy(self._data['profile']))
        bridge = SimpleNamespace(recipe_hub=hub)
        ingredient = {'key': 'rice', 'name': 'Rice'}
        out, errors, mappings, prices = [], [], [], []
        connection = SimpleNamespace(
            user=SimpleNamespace(id='alice'),
            send_result=lambda ident, data: out.append(data),
            send_error=lambda ident, code, message: errors.append((code, message)),
        )
        async def catalog(*args):
            return [deepcopy(ingredient)]
        async def set_mapping(barcode, value):
            mappings.append((barcode, deepcopy(value)))
        async def barcode_store(bridge):
            return SimpleNamespace(async_set=set_mapping)
        async def save_prices(bridge, ingredient, lot_id, msg, metadata):
            prices.append(lot_id)
        # Ingredient resolution is a separate catalog boundary. Stock commits,
        # locking, payload fingerprints and receipt replay execute production code.
        packages = ModuleType('product_save_v224.product_packages')
        packages.resolve_ingredient_links = lambda values, rows, strict: deepcopy(rows)
        module_patch = patch.dict(sys.modules, {packages.__name__: packages})
        module_patch.start()
        self.addCleanup(module_patch.stop)
        namespace = {
            '__package__': 'product_save_v224', 'asyncio': asyncio,
            'hashlib': hashlib, 'json': json, '_authorized': lambda *args: bridge,
            '_catalog': catalog, 'inventory_identity': lambda row: row.get('key'),
            '_quantity': float, 'validate_paid_price': lambda value: None,
            'normalize_barcode': lambda value: value,
            'v15': SimpleNamespace(_store=barcode_store), 'save_product_prices': save_prices,
            'update_expiry_notification': lambda bridge: None,
            '_state': lambda hass, bridge, user: bridge.recipe_hub.profile,
            'legacy': SimpleNamespace(_send_error=lambda c, m, e: errors.append(('save_failed', str(e)))),
        }
        production_functions(['ws_product_add'], namespace)
        msg = {
            'id': 1, 'type': 'cook4me/v33/product_add', 'entry_id': 'entry',
            'request_id': 'reviewed-product-001', '_cook4me_job_id': 'job-one',
            'ingredient': ingredient, 'quantity': 750, 'unit': 'g',
            'lot_metadata': {'barcode': '1234567890123', 'productName': 'Edited rice'},
        }
        async def save(message):
            await namespace['ws_product_add'](object(), connection, message)
        return hub, save, msg, out, errors, mappings, prices

    async def test_lost_reply_retry_with_new_job_does_not_add_stock_again(self):
        hub, save, msg, out, errors, mappings, prices = self.environment()
        await save(msg)
        first = out.pop()
        # Reload the committed state to include reconnect/restart replay.
        hub._data = deepcopy(hub._store.data)
        await save({**msg, 'id': 2, '_cook4me_job_id': 'job-two'})
        self.assertFalse(errors, errors)
        self.assertEqual(out[0]['lotId'], first['lotId'])
        self.assertEqual(hub._store.writes, 1)
        self.assertEqual(len(hub.profile['houseIngredients']), 1)
        self.assertEqual(len(mappings), 2)
        self.assertEqual(prices, [first['lotId'], first['lotId']])

    async def test_changed_product_cannot_reuse_committed_request_id(self):
        hub, save, msg, out, errors, mappings, prices = self.environment()
        await save(msg)
        await save({**msg, 'quantity': 900, '_cook4me_job_id': 'job-two'})
        self.assertEqual(errors[0][0], 'product_validation')
        self.assertEqual(len(out), 1)
        self.assertEqual(hub._store.writes, 1)
        self.assertEqual(len(prices), 1)

    async def test_failed_storage_is_not_acknowledged_and_can_retry(self):
        hub, save, msg, out, errors, mappings, prices = self.environment()
        hub._store.fail = True
        await save(msg)
        self.assertFalse(out)
        self.assertEqual(hub.profile['houseIngredients'], [])
        self.assertEqual(errors[0][0], 'save_failed')
        self.assertFalse(mappings)
        hub._store.fail = False
        await save({**msg, 'id': 2, '_cook4me_job_id': 'job-two'})
        self.assertEqual(len(out), 1)
        self.assertEqual(hub._store.writes, 1)

    async def test_concurrent_retries_share_one_durable_commit(self):
        hub, save, msg, out, errors, mappings, prices = self.environment()
        await asyncio.gather(save(msg), save({**msg, 'id': 2, '_cook4me_job_id': 'job-two'}))
        self.assertFalse(errors, errors)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]['lotId'], out[1]['lotId'])
        self.assertEqual(hub._store.writes, 1)


if __name__ == '__main__':
    unittest.main()
