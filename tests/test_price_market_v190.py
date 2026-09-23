"""Market/language regressions; production functions, controlled catalog/network.

This unit suite does not fetch retailer data or run a live Home Assistant. Run
from a full checkout; the development bundle also records tests against fetched
function excerpts, with that narrower scope explicitly documented.
"""
from __future__ import annotations
import ast
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'custom_components' / 'cook4me'


def load(name, injected=None, selected=None):
    path = COMPONENT / (name + '.py')
    tree = ast.parse(path.read_text(encoding='utf-8'))
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.level or (node.module or '').startswith('homeassistant')):
            continue
        if selected is not None and not isinstance(node, (ast.Import, ast.ImportFrom)):
            if getattr(node, 'name', '') not in selected:
                continue
        nodes.append(node)
    ns = {'__name__': 'market_audit_' + name, '__file__': str(path), **(injected or {})}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), ns)
    return ns


# These lightweight doubles implement the dependency contracts. Price-market,
# catalog label evidence and the tested automatic_prices entry points are real
# production source, loaded above. The fixture is not the shipped catalog.
def text(value):
    return str(value or '').strip()


def country(value):
    token = text(value).upper()
    return token if len(token) == 2 and token.isalpha() else ''


def currency(value):
    token = text(value).upper()
    return token if len(token) == 3 and token.isalpha() else ''


def number(value):
    import math
    if isinstance(value, bool):
        return None
    try:
        result = float(value.replace(',', '.') if isinstance(value, str) else value)
        return result if math.isfinite(result) and result >= 0 else None
    except (TypeError, ValueError):
        return None


def identity(item):
    key = item.get('key') or item.get('foodKey')
    if key:
        return 'k:' + str(key)
    name = str(item.get('name') or item.get('foodName') or '').strip().casefold()
    return 'n:' + name if name else ''


def convert(value, source, target):
    value = number(value)
    scales = {'g': ('mass', 1), 'kg': ('mass', 1000), 'ml': ('volume', 1), 'l': ('volume', 1000), 'pcs': ('count', 1)}
    if value is None:
        return None
    if source == target:
        return value
    left, right = scales.get(source), scales.get(target)
    return value * left[1] / right[1] if left and right and left[0] == right[0] else None


def amount_for(ref, quantity, unit):
    value = convert(quantity, unit, ref.get('basisUnit'))
    return ref['amount'] * value / ref['basisQuantity'] if value is not None else None


NORMALIZER = load('shopping_presentation', {
    'COUNTRY_LANGUAGE': {'DE': 'de', 'AT': 'de', 'CH': 'de', 'GR': 'el', 'FR': 'fr', 'CA': 'en', 'GB': 'en'},
    'SUPPORTED_SUPERMARKET_LANGUAGES': frozenset({'en', 'de', 'el', 'fr', 'es', 'it'}),
}, {'normalize_supermarket_language'})['normalize_supermarket_language']

LABELS = {'de': {'rice': 'Reis', 'sesame oil': 'Sesamöl', 'tofu': 'Tofu', 'cooked rice': 'Gekochter Reis', 'dry rice': 'Trockener Reis'},
          'el': {'rice': 'Ρύζι', 'sesame oil': 'Σησαμέλαιο'},
          'fr': {'rice': 'Riz', 'sesame oil': 'Huile de sésame'}}
CATALOG = {'rice': {'canonicalName': 'rice', 'translations': {'de': 'Reis aus Katalog'}},
           'oil': {'canonicalName': 'sesame oil'}, 'tofu': {'canonicalName': 'tofu'},
           'dry': {'canonicalName': 'dry rice'}, 'cooked': {'canonicalName': 'cooked rice'},
           'rare': {'canonicalName': 'rare ingredient'},
           'source': {'canonicalName': 'sourced ingredient', 'translations': {'de': 'Quellzutat'}}}


def name_key(value):
    return ' '.join(str(value).casefold().split())


PRESENTATION = load('catalog_presentation', {'clean_name': lambda x: str(x or '').strip(),
    'name_key': name_key, 'labels': lambda: LABELS}, {'display_name'})
CORE = SimpleNamespace(_global_ingredient=lambda payload, item: CATALOG.get(item.get('ingredientId') or item.get('key') or item.get('foodKey')),
    _presentation=SimpleNamespace(clean_name=lambda x: str(x or '').strip(), name_key=name_key,
        labels=lambda: LABELS, display_name=PRESENTATION['display_name']))
CAT = load('release_catalog', {'_core': CORE, 'load_release_catalog': lambda: {}}, {'ingredient_price_label'})
MARKET = load('price_market', {'release_catalog': SimpleNamespace(ingredient_price_label=CAT['ingredient_price_label']),
    '_country': country, '_currency': currency, '_number': number,
    'inventory_identity': identity, 'normalize_supermarket_language': NORMALIZER})
DE = {'country': 'DE', 'currency': 'EUR', 'supermarketLanguage': 'de', 'autoGlobalPrices': True}


def observation(**kwargs):
    row = {'id': 'demo', 'usable': True, 'amount': 2., 'basisQuantity': 1000., 'basisUnit': 'g',
           'country': 'DE', 'currency': 'EUR', 'date': datetime.now(timezone.utc).date().isoformat(),
           'source': 'open_prices_category', 'identity': 'k:rice'}
    row.update(kwargs)
    return row


def ingredient(**kwargs):
    item = {'key': 'rice', 'name': 'Ρύζι (Reis; Riz)', 'quantity': 250., 'unit': 'g'}
    item.update(kwargs)
    return item


class Store:
    def __init__(self, refs=(), settings=None):
        self._data = {'settings': dict(settings or DE), 'references': {str(i): deepcopy(ref) for i, ref in enumerate(refs)}}
        self.calls = []

    @property
    def settings(self):
        return deepcopy(self._data['settings'])

    def best_reference(self, ident, *, country='', currency='', unit=''):
        self.calls.append((ident, country, currency, unit))
        rows = [r for r in self._data['references'].values() if r.get('identity') == ident
                and (not country or r.get('country') == country)
                and (not currency or r.get('currency') == currency)
                and (not unit or convert(1, unit, r.get('basisUnit')) is not None)]
        return deepcopy(rows[-1]) if rows else None

    def barcode_reference(self, code, **kwargs):
        return self.best_reference('barcode:' + code, **kwargs)


class Hass:
    def __init__(self):
        self.executor_functions = []
        self.config = SimpleNamespace(country='DE')

    async def async_add_executor_job(self, action, *args):
        self.executor_functions.append(getattr(getattr(action, 'func', action), '__name__', ''))
        await asyncio.sleep(0)
        return action(*args)

    def async_create_background_task(self, coro, name):
        return asyncio.create_task(coro, name=name)


class CostCache:
    def __init__(self):
        self.stores = []

    async def async_cost(self, recipe, inventory, store, **kwargs):
        self.stores.append(store)
        rows = []
        total = 0
        for item in recipe['ingredients']:
            ident = identity(item)
            ref = store.best_reference(ident, country=kwargs.get('country', ''), currency=kwargs.get('currency', ''), unit=item.get('unit', ''))
            value = amount_for(ref, item.get('quantity'), item.get('unit')) if ref else None
            total += value or 0
            rows.append({'identity': ident, 'name': item['name'], 'coverage': 1 if value is not None else 0,
                         'costsByCurrency': {'EUR': value} if value is not None else {}})
        return {'ingredients': rows, 'totalsByCurrency': {'EUR': total} if total else {}}


def environment(refs=(), settings=None, live=None, snapshots=None):
    store = Store(refs, settings)
    bridge = SimpleNamespace(hass=Hass(), recipe_hub=SimpleNamespace(profile={'houseIngredients': []}))
    calls = []
    snapshots = [] if snapshots is None else snapshots
    cache = CostCache()
    async def get_store(bridge):
        return store
    async def get_settings(bridge):
        return store.settings
    async def get_cache(bridge):
        return cache
    def provider(code='', **kwargs):
        calls.append((code, deepcopy(kwargs)))
        return {'ok': True, 'items': deepcopy(live if live is not None else [observation(barcode=code)])}
    async def save(store, ident, row, **kwargs):
        store._data['references'][ident] = {**deepcopy(row), 'identity': ident}
    categories = {'rice': ('en:rices', 'PRODUCT'), 'dry rice': ('en:rices', 'PRODUCT'),
                  'cooked rice': ('en:cooked-rice', 'PRODUCT'), 'sesame oil': ('en:sesame-oils', 'PRODUCT')}
    def category(item):
        return categories.get(str((item or {}).get('canonicalName') or (item or {}).get('name') or '').casefold())
    ns = load('automatic_prices', {
        **{k: v for k, v in MARKET.items() if not k.startswith('__')},
        'cost_store_for_bridge': get_store, 'price_settings': get_settings,
        'recipe_cost_cache_for_bridge': get_cache, 'inventory_identity': identity,
        'convert_amount': convert, '_cost_for_amount': amount_for, '_fresh': lambda ref: bool(ref),
        'category_for': category, 'snapshot_observations': lambda **kwargs: deepcopy(snapshots),
        'category_observation_allowed': lambda row, category: True,
        'lookup_open_prices': provider, '_store_observation': save,
        'canonical_recipe': lambda recipe, *a, **k: deepcopy(recipe),
        'price_options': lambda item: [{'quantity': item.get('quantity'), 'unit': item.get('unit')}],
        '_RECIPE_WAIT_SECONDS': 1, '_mark_food_coverage': lambda *args: None,
    }, {'_observations', 'product_price', 'recipe_price', 'offline_price_inputs', 'offline_recipe_price'})
    return ns, bridge, store, calls, cache


class LanguageContractTests(unittest.TestCase):
    def test_local_name_not_ui_or_shopping_composite(self):
        raw = ingredient()
        before = deepcopy(raw)
        result = MARKET['price_lookup_ingredient'](raw, DE)
        self.assertEqual(result['name'], 'Reis')
        self.assertEqual(result['canonicalName'], 'rice')
        self.assertEqual(result['priceLookup']['queryName'], 'Reis')
        self.assertEqual(raw, before)

    def test_explicit_supermarket_language_beats_country_default(self):
        result = MARKET['price_lookup_ingredient'](ingredient(), {**DE, 'supermarketLanguage': 'fr'})
        self.assertEqual(result['name'], 'Riz')
        self.assertEqual(result['priceLookup']['country'], 'DE')

    def test_country_is_not_inferred_from_ui_or_market_language(self):
        settings = MARKET['normalize_price_market']({'country': '', 'currency': 'EUR', 'supermarketLanguage': 'de', 'language': 'el'})
        self.assertFalse(MARKET['market_ready'](settings))
        self.assertEqual(settings['country'], '')

    def test_blank_or_unsupported_language_uses_country_default(self):
        for lang in ('', None, 'invalid'):
            with self.subTest(language=lang):
                self.assertEqual(MARKET['normalize_price_market']({**DE, 'supermarketLanguage': lang})['supermarketLanguage'], 'de')

    def test_regional_language_country_currency_normalization(self):
        result = MARKET['normalize_price_market']({'country': ' de ', 'currency': ' eur ', 'supermarketLanguage': 'de_DE'})
        self.assertEqual((result['country'], result['currency'], result['supermarketLanguage']), ('DE', 'EUR', 'de'))

    def test_language_switch_does_not_convert_currency(self):
        result = MARKET['normalize_price_market']({'country': 'CH', 'currency': 'CHF', 'supermarketLanguage': 'fr'})
        self.assertEqual(result['currency'], 'CHF')
        self.assertEqual(result['country'], 'CH')

    def test_missing_translation_not_misreported_as_local(self):
        result = MARKET['price_lookup_ingredient'](ingredient(key='rare'), DE)['priceLookup']
        self.assertTrue(result['translationMissing'])
        self.assertEqual(result['queryName'], '')
        self.assertEqual(result['ingredientLanguage'], 'en')
        self.assertEqual(result['country'], 'DE')

    def test_same_spelling_is_still_proven_translation(self):
        result = MARKET['price_lookup_ingredient'](ingredient(key='tofu'), DE)
        self.assertEqual(result['name'], 'Tofu')
        self.assertFalse(result['priceLookup']['translationMissing'])

    def test_source_translation_when_no_overlay(self):
        result = MARKET['price_lookup_ingredient'](ingredient(key='source'), DE)
        self.assertEqual(result['name'], 'Quellzutat')
        self.assertEqual(result['priceLookup']['nameSource'], 'catalog_translation')

    def test_preserves_keys_quantities_and_canonical_food_form(self):
        dry = MARKET['price_lookup_ingredient'](ingredient(key='dry'), DE)
        cooked = MARKET['price_lookup_ingredient'](ingredient(key='cooked'), DE)
        self.assertNotEqual(dry['canonicalName'], cooked['canonicalName'])
        self.assertEqual(dry['key'], 'dry')
        self.assertEqual(dry['quantity'], 250)
        self.assertEqual(dry['unit'], 'g')

    def test_unkeyed_identity_does_not_change_when_translated(self):
        raw = {'name': 'Ρύζι', 'canonicalName': 'rice', 'quantity': 1, 'unit': 'kg'}
        result = MARKET['price_lookup_ingredient'](raw, DE)
        self.assertEqual(result['name'], 'Reis')
        self.assertEqual(result['priceLookupIdentity'], identity(raw))

    def test_ingredient_id_only_uses_a_stable_key(self):
        result = MARKET['price_lookup_ingredient']({'ingredientId': 'rice', 'name': 'Ρύζι'}, DE)
        self.assertEqual(result['priceLookupIdentity'], 'k:rice')
        self.assertEqual(result['key'], 'rice')
        self.assertEqual(result['name'], 'Reis')

    def test_effective_key_beats_stale_provider_ingredient_id(self):
        result = MARKET['price_lookup_ingredient'](ingredient(key='cooked', ingredientId='dry'), DE)
        self.assertEqual(result['canonicalName'], 'cooked rice')
        self.assertEqual(result['name'], 'Gekochter Reis')

    def test_reviewed_synthetic_identity_is_not_reverted(self):
        result = MARKET['price_lookup_ingredient'](ingredient(key='cook4me:recipe-override', ingredientId='rice', canonicalName='sesame oil'), DE)
        self.assertEqual(result['canonicalName'], 'sesame oil')
        self.assertEqual(result['name'], 'Sesamöl')
        self.assertEqual(result['priceLookupIdentity'], 'k:cook4me:recipe-override')

    def test_unknown_free_text_not_claimed_as_english_or_german(self):
        result = MARKET['price_lookup_ingredient']({'name': 'Μυστικό μίγμα'}, DE)['priceLookup']
        self.assertTrue(result['translationMissing'])
        self.assertEqual(result['ingredientLanguage'], '')
        self.assertEqual(result['queryName'], '')


class LocalEvidenceTests(unittest.TestCase):
    def test_same_currency_foreign_country_rejected(self):
        result = MARKET['local_observation_result']({'ok': True, 'items': [observation(country='FR'), observation()]}, DE)
        self.assertEqual([r['country'] for r in result['items']], ['DE'])

    def test_wrong_currency_rejected_without_fx(self):
        result = MARKET['local_observation_result']({'ok': True, 'items': [observation(currency='USD')]}, DE)
        self.assertEqual(result['items'], [])

    def test_dates_missing_expired_and_future_rejected(self):
        today = datetime.now(timezone.utc).date()
        rows = [observation(date=d) for d in ('', None, 'not-a-date', (today-timedelta(days=181)).isoformat(), (today+timedelta(days=1)).isoformat())]
        result = MARKET['local_observation_result']({'items': rows}, DE)
        self.assertEqual(result['usableCount'], 0)

    def test_date_boundary_is_inclusive(self):
        today = datetime.now(timezone.utc).date()
        result = MARKET['local_observation_result']({'items': [observation(date=(today-timedelta(days=180)).isoformat())]}, DE)
        self.assertEqual(result['usableCount'], 1)

    def test_invalid_basis_and_non_finite_prices_rejected(self):
        rows = [observation(basisQuantity=0), observation(basisQuantity=True), observation(amount=float('nan')), observation(amount=-1), observation(basisUnit='')]
        self.assertEqual(MARKET['local_observation_result']({'items': rows}, DE)['items'], [])

    def test_explicit_zero_is_distinct_from_unknown(self):
        result = MARKET['local_observation_result']({'items': [observation(amount=0)]}, DE)
        self.assertEqual(result['usableCount'], 1)
        self.assertEqual(result['items'][0]['amount'], 0)

    def test_malformed_items_fail_as_invalid_response(self):
        for value in (42, 'bad', {'not': 'a list'}):
            result = MARKET['local_observation_result']({'ok': True, 'items': value}, DE)
            self.assertFalse(result['ok'])
            self.assertEqual(result['reason'], 'invalid_response')
            self.assertEqual(result['items'], [])

    def test_snapshot_and_live_sources_use_same_boundary(self):
        for source in ('retail_snapshot', 'utility_snapshot', 'open_prices_category'):
            with self.subTest(source=source):
                result = MARKET['local_observation_result']({'items': [observation(country='FR', source=source)]}, DE)
                self.assertEqual(result['items'], [])

    def test_local_cost_view_preserves_exact_paid_foreign_lots_only(self):
        refs = [observation(), observation(identity='k:foreign', country='FR'),
                observation(identity='lot:paid', country='US', currency='USD', source='purchase', confidence='exact_purchase')]
        saved = Store(refs)
        before = deepcopy(saved._data)
        view = MARKET['local_cost_store'](saved, DE)
        self.assertEqual({r['identity'] for r in view._data['references'].values()}, {'k:rice', 'lot:paid'})
        self.assertEqual(saved._data, before)

    def test_unset_market_has_no_generic_references(self):
        view = MARKET['local_cost_store'](Store([observation()]), {**DE, 'country': ''})
        self.assertEqual(view._data['references'], {})

    def test_annotations_update_without_changing_numeric_or_ui_values(self):
        raw = {'ingredients': [{'identity': 'k:rice', 'name': 'Ρύζι', 'costsByCurrency': {'EUR': .5}}], 'totalsByCurrency': {'EUR': .5}}
        result = MARKET['annotate_market_cost'](raw, {'ingredients': [ingredient()]}, DE)
        self.assertEqual(result['ingredients'][0]['supermarketName'], 'Reis')
        self.assertEqual(result['ingredients'][0]['name'], 'Ρύζι')
        self.assertEqual(result['totalsByCurrency'], raw['totalsByCurrency'])
        self.assertNotIn('supermarketName', raw['ingredients'][0])


class LookupPathTests(unittest.IsolatedAsyncioTestCase):
    async def test_product_adapter_receives_supermarket_language_ingredient(self):
        ns, bridge, store, calls, _ = environment()
        captured = []
        original = ns['market_observations']
        async def spy(*args, **kwargs):
            captured.append(deepcopy(kwargs['ingredient']))
            return await original(*args, **kwargs)
        ns['market_observations'] = spy
        result = await ns['product_price'](bridge, ingredient=ingredient(), quantity=250, unit='g')
        self.assertEqual(result['estimate'], .5)
        self.assertEqual(captured[0]['name'], 'Reis')
        self.assertEqual(result['lookupIngredient']['supermarketLanguage'], 'de')
        self.assertEqual(calls[0][1]['category'], 'en:rices')
        self.assertEqual(calls[0][1]['country'], 'DE')
        self.assertNotIn('search_terms', calls[0][1])
        self.assertNotIn('lc', calls[0][1])

    async def test_no_country_does_not_use_saved_foreign_reference(self):
        ns, bridge, store, calls, _ = environment([observation(country='FR')], {**DE, 'country': ''})
        result = await ns['product_price'](bridge, ingredient=ingredient(), quantity=250, unit='g')
        self.assertIsNone(result['estimate'])
        self.assertEqual(result['status'], 'choose_country')
        self.assertEqual(calls, [])
        self.assertEqual(store.calls, [])

    async def test_barcode_query_remains_exact_and_local(self):
        ns, bridge, store, calls, _ = environment(live=[observation(barcode='123', country='FR')])
        result = await ns['product_price'](bridge, barcode='123', ingredient=ingredient(), quantity=250, unit='g')
        self.assertIsNone(result['estimate'])
        self.assertEqual(calls[0][0], '123')
        self.assertEqual(calls[0][1]['country'], 'DE')
        self.assertEqual(store._data['references'], {})

    async def test_no_local_result_remains_unknown_not_free(self):
        ns, bridge, store, calls, _ = environment(live=[])
        result = await ns['product_price'](bridge, ingredient=ingredient(), quantity=250, unit='g')
        self.assertIsNone(result['estimate'])
        self.assertIsNone(result['reference'])

    async def test_stale_source_row_cannot_be_saved(self):
        ns, bridge, store, calls, _ = environment(live=[observation(date='2000-01-01')])
        result = await ns['product_price'](bridge, ingredient=ingredient(), quantity=250, unit='g')
        self.assertIsNone(result['estimate'])
        self.assertEqual(store._data['references'], {})

    async def test_localization_runs_in_executor(self):
        ns, bridge, *_ = environment()
        await ns['product_price'](bridge, ingredient=ingredient(), quantity=250, unit='g')
        self.assertIn('price_lookup_ingredient', bridge.hass.executor_functions)

    async def test_automatic_disabled_makes_no_provider_requests(self):
        ns, bridge, _, calls, _ = environment(settings={**DE, 'autoGlobalPrices': False})
        result = await ns['product_price'](bridge, ingredient=ingredient(), quantity=250, unit='g')
        self.assertEqual(result['status'], 'automatic_disabled')
        self.assertEqual(calls, [])

    async def test_force_refresh_uses_same_local_market(self):
        ns, bridge, _, calls, _ = environment(settings={**DE, 'autoGlobalPrices': False})
        await ns['product_price'](bridge, ingredient=ingredient(), quantity=250, unit='g', refresh_since=1)
        self.assertTrue(calls)
        self.assertTrue(all(c[1]['country'] == 'DE' and c[1]['currency'] == 'EUR' for c in calls))

    async def test_cache_keys_separate_supermarket_languages(self):
        ns, bridge, _, calls, _ = environment()
        for language in ('de', 'fr'):
            await ns['_observations'](bridge, category='en:rices', settings={**DE, 'supermarketLanguage': language}, unit='g')
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(bridge._price_queries), 2)

    async def test_same_language_observations_coalesce(self):
        ns, bridge, _, calls, _ = environment()
        await asyncio.gather(*(ns['_observations'](bridge, category='en:rices', settings=DE, unit='g') for _ in range(8)))
        self.assertEqual(len(calls), 1)

    async def test_cached_evidence_does_not_reuse_another_ingredient_label(self):
        ns, bridge, _, calls, _ = environment()
        a = MARKET['price_lookup_ingredient'](ingredient(), DE)
        b = MARKET['price_lookup_ingredient'](ingredient(key='dry'), DE)
        left = await MARKET['market_observations'](bridge, fetch=ns['_observations'], ingredient=a, settings=DE, category='en:rices', unit='g')
        right = await MARKET['market_observations'](bridge, fetch=ns['_observations'], ingredient=b, settings=DE, category='en:rices', unit='g')
        self.assertEqual(len(calls), 1)
        self.assertEqual(left['lookupIngredient']['ingredientName'], 'Reis')
        self.assertEqual(right['lookupIngredient']['ingredientName'], 'Trockener Reis')

    async def test_offline_preview_and_live_recipe_have_local_labels(self):
        ns, bridge, _, _, cache = environment(snapshots=[observation()])
        recipe = {'ingredients': [ingredient(canonicalName='rice')]}
        offline = await ns['offline_recipe_price'](bridge, recipe, [])
        live = await ns['recipe_price'](bridge, recipe, [])
        for result in (offline, live):
            self.assertEqual(result['ingredients'][0]['supermarketName'], 'Reis')
            self.assertEqual(result['ingredients'][0]['name'], recipe['ingredients'][0]['name'])
            self.assertEqual(result['totalsByCurrency']['EUR'], .5)
        self.assertIn('annotate_market_cost', bridge.hass.executor_functions)
        self.assertIn('local_cost_store', bridge.hass.executor_functions)

    async def test_offline_snapshot_foreign_rows_rejected(self):
        ns, _, store, _, _ = environment(snapshots=[observation(country='FR')])
        _, view = ns['offline_price_inputs']({'ingredients': [ingredient(canonicalName='rice')]}, [], store, DE)
        self.assertEqual(view._data['references'], {})

    async def test_offline_unset_market_cannot_reuse_a_global_reference(self):
        ns, bridge, _, calls, _ = environment([observation(country='FR')], {**DE, 'country': ''})
        result = await ns['offline_recipe_price'](bridge, {'ingredients': [ingredient(canonicalName='rice')]}, [])
        self.assertEqual(result['totalsByCurrency'], {})
        self.assertEqual(calls, [])

    async def test_language_change_rebinds_current_market_names(self):
        ns, bridge, store, _, _ = environment([observation()])
        recipe = {'ingredients': [ingredient(canonicalName='rice')]}
        first = await ns['offline_recipe_price'](bridge, recipe, [])
        store._data['settings']['supermarketLanguage'] = 'fr'
        second = await ns['offline_recipe_price'](bridge, recipe, [])
        self.assertEqual(first['ingredients'][0]['supermarketName'], 'Reis')
        self.assertEqual(second['ingredients'][0]['supermarketName'], 'Riz')
        self.assertEqual(first['totalsByCurrency'], second['totalsByCurrency'])
        self.assertEqual(second['lookupMarket']['country'], 'DE')


if __name__ == '__main__':
    unittest.main()
