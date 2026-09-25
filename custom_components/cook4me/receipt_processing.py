"""Durable receipt enrichment, independent of browsers and stock mutations."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
import logging
import re
from time import monotonic
import urllib.parse
import urllib.request

from .barcode import (_OFF_FIELDS, _USER_AGENT, _norm, normalize_barcode,
                      normalize_openfoodfacts_payload)
from .receipts import receipt_store_for_bridge, text

_LOGGER = logging.getLogger(__name__)


def receipt_product_query(item):
    """Search receipt wording, including legacy drafts with translated names."""
    name = text(item.get('originalName')) or text(item.get('productName'))
    if not name:
        return ''
    brand = text(item.get('brand'))
    # Compare normalized words, but send the original accents/script/variants.
    if brand and f' {_norm(brand)} ' not in f' {_norm(name)} ':
        return f'{brand} {name}'
    return name


def search_products(query):
    params = urllib.parse.urlencode({'search_terms': text(query, 160), 'search_simple': 1,
        'action': 'process', 'json': 1, 'page_size': 8, 'fields': _OFF_FIELDS})
    request = urllib.request.Request('https://world.openfoodfacts.org/cgi/search.pl?' + params,
        headers={'Accept': 'application/json', 'User-Agent': _USER_AGENT})
    with urllib.request.urlopen(request, timeout=15) as response:
        raw = json.loads(response.read(1_000_000).decode('utf-8'))
    result = []
    for product in (raw.get('products') or [])[:8]:
        try:
            code = normalize_barcode(product.get('code'))
        except ValueError:
            continue
        result.append(normalize_openfoodfacts_payload(code, {'product': product}))
    return result


def same_package(item, candidate):
    """A unique exact name + brand + compatible size can supply a barcode."""
    if not item.get('brand') or _norm(item['brand']) != _norm(candidate.get('brand')):
        return False
    def name(value):
        value = re.sub(r'\b\d+(?:[.,]\d+)?\s*(?:kg|g|ml|cl|dl|l)\b', '', str(value), flags=re.I)
        words = _norm(value).split(); brand = set(_norm(item['brand']).split())
        return ' '.join(w for w in words if w not in brand)
    candidate_name = name(candidate.get('productName'))
    if not candidate_name or candidate_name not in {name(item.get('productName')), name(item.get('originalName'))}:
        return False
    if item.get('quantity') and item.get('unit'):
        factors = {'kg': ('g',1000), 'g': ('g',1), 'l': ('ml',1000), 'cl': ('ml',10), 'dl': ('ml',100), 'ml': ('ml',1), 'pcs': ('pcs',1)}
        a, b = factors.get(item['unit']), factors.get(candidate.get('unit'))
        if not a or not b or a[0] != b[0] or candidate.get('quantity') is None:
            return False
        if abs(float(item['quantity'])*a[1]-float(candidate['quantity'])*b[1]) > .001:
            return False
    return True


class ReceiptProcessor:
    def __init__(self, bridge):
        self.bridge = bridge
        self.task = None
        self.closed = False
        self.cache = {}

    def start(self):
        if not self.closed and (self.task is None or self.task.done()):
            self.task = self.bridge.hass.async_create_background_task(self.run(), 'Cook4Me receipt enrichment')

    async def close(self):
        self.closed = True
        if self.task and not self.task.done():
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)

    async def network(self, callback):
        # Shared across entries. Stay below OFF's search/read limits; do not
        # occupy HA's executor while waiting, and never queue interactive saves.
        hass = self.bridge.hass
        gate = hass.data.setdefault('cook4me_receipt_network', {'lock': asyncio.Lock(), 'last': 0})
        async with gate['lock']:
            await asyncio.sleep(max(0, 7-(monotonic()-gate['last'])))
            gate['last'] = monotonic()
            async with asyncio.timeout(25):
                return await callback()

    async def enrich(self, item, catalog, mappings, stage):
        from . import websocket_v23
        from .product_packages import resolve_ingredient_links
        from .scanner_matching import suggest_catalog_matches
        hass = self.bridge.hass
        patch, product, notes = {}, {}, []
        await stage('barcode')
        code = item.get('barcode')
        if not code:
            candidates = [m for m in mappings.values() if same_package(item, m)]
            if len(candidates) == 1:
                code = candidates[0]['barcode']
            else:
                query = receipt_product_query(item)
                if query:
                    try:
                        if query not in self.cache:
                            self.cache[query] = await self.network(lambda: hass.async_add_executor_job(search_products, query))
                            if len(self.cache) > 300:
                                self.cache.pop(next(iter(self.cache)))
                        candidates = self.cache[query]
                        matches = [p for p in candidates if same_package(item, p)]
                        if len({p['barcode'] for p in matches}) == 1:
                            product = matches[0]; code = product['barcode']
                        elif candidates:
                            notes.append('barcode_ambiguous')
                    except Exception:
                        notes.append('lookup_failed')
        await stage('nutrition')
        mapping = mappings.get(code, {}) if code else {}
        if code and not product:
            try:
                product = await self.network(lambda: websocket_v23._cached_product(hass, self.bridge, code))
            except Exception:
                notes.append('lookup_failed')
        if code:
            patch['barcode'] = code
        for key in ('brand', 'quantity', 'unit'):
            if not item.get(key) and (value := product.get(key) or mapping.get(key)):
                patch[key] = value
        if not (item.get('nutrition') or {}).get('values'):
            nutrition = product.get('nutrition') or mapping.get('nutrition')
            if nutrition and nutrition.get('basisQuantity') == 100 and nutrition.get('basisUnit') in {'g','ml'}:
                patch['nutrition'] = deepcopy(nutrition)
        await stage('ingredients')
        evidence = {**product, 'productName': product.get('productName') or item.get('productName'),
                    'ingredientName': item.get('ingredientName'), 'brand': item.get('brand')}
        suggestions = await hass.async_add_executor_job(suggest_catalog_matches, evidence, catalog)
        links = resolve_ingredient_links(mapping.get('ingredientLinks') or [mapping.get('ingredient')], catalog)
        if not links:
            exact = [s for s in suggestions if s.get('reason') == 'name_exact']
            if len(exact) == 1:
                links = [exact[0]['ingredient']]
        if not item.get('ingredientLinks') and links:
            patch['ingredientLinks'] = links
        patch['enrichment'] = {'state': 'ready', 'notes': list(dict.fromkeys(notes)),
                               'suggestions': suggestions[:12], 'source': product.get('source') or ('saved_barcode' if mapping else 'catalog')}
        return patch

    async def run(self):
        from .websocket_v33 import _catalog
        from .websocket_v15 import _store
        from .device_settings import device_access
        store = await receipt_store_for_bridge(self.bridge)
        while not self.closed:
            work = await store.work()
            if not work:
                return
            for receipt in work:
                owner, ident = receipt['owner'], receipt['id']
                try:
                    user = await self.bridge.hass.auth.async_get_user(owner)
                    if not user or not user.is_active or not device_access(self.bridge.hass, self.bridge, user):
                        await store.progress(owner, ident, state='failed', stage='permission', error='permission')
                        continue
                    catalog = await _catalog(self.bridge.hass, self.bridge, {'language': receipt.get('language', 'en')})
                    mappings = (await _store(self.bridge)).all()
                    items = [i for i in receipt['items'] if i['kind'] == 'product']
                    for index, item in enumerate(items):
                        try:
                            latest = await store.get(owner, ident)
                        except ValueError:
                            break  # The user deleted the receipt during lookup.
                        item = next(i for i in latest['items'] if i['id'] == item['id'])
                        if item['status'] != 'pending' or item.get('enrichment', {}).get('state') in {'ready','reviewed'}:
                            continue
                        async def stage(name):
                            await store.progress(owner, ident, state='processing', stage=name, done=index,
                                                 total=len(items), currentItemId=item['id'])
                        patch = await self.enrich(item, catalog, mappings, stage)
                        await store.enrich_item(owner, ident, item, patch)
                        await store.progress(owner, ident, done=index+1)
                    await store.progress(owner, ident, state='ready', stage='ready', done=len(items), currentItemId='')
                except asyncio.CancelledError:
                    raise  # queued/processing remains durable for the next startup
                except Exception:
                    _LOGGER.exception('Receipt background processing failed')
                    await store.progress(owner, ident, state='failed', stage='failed', error='processing_failed')


def start_receipt_processing(bridge):
    processor = getattr(bridge, '_receipt_processor', None)
    if processor is None:
        processor = bridge._receipt_processor = ReceiptProcessor(bridge)
    processor.start()
    return processor
