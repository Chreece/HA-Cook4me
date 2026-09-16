"""Offline, dated public price evidence, warmed in the setup executor."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
from pathlib import Path

from .inventory import convert_amount

_PATH = Path(__file__).with_name('catalog') / 'observed_prices.v1.json'


@lru_cache(maxsize=1)
def _load():
    try:
        data = json.loads(_PATH.read_text(encoding='utf-8'))
        if data.get('schemaVersion') == 1:
            try:
                retail = json.loads(_PATH.with_name('retail_prices.v1.json').read_text(encoding='utf-8'))
                if retail.get('schemaVersion') == 1:
                    data['observations'].extend(retail.get('observations') or [])
            except (OSError, ValueError, AttributeError):
                pass
            return data
    except (OSError, ValueError, AttributeError):
        pass
    return {}


def country_locations(country):
    """A bounded search hint only; every returned observation is revalidated."""
    rows = _load().get('locationsByCountry', {}).get(country, [])
    return [value for value in rows if type(value) is int and value > 0][:900]


def snapshot_observations(*, barcode='', category='', country='', currency='', unit=''):
    if not country or not currency or not (barcode or category):
        return []
    today = datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=180)
    result = []
    for row in _load().get('observations', []):
        if row.get('country') != country or row.get('currency') != currency:
            continue
        if barcode:
            if row.get('barcode') != barcode:
                continue
        elif (category not in row.get('categories', []) or category in row.get('categoryExclusions', [])
              or not category_observation_allowed(row, category)):
            continue
        try:
            observed = datetime.fromisoformat(row['date']).date()
            if not cutoff <= observed <= today:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        if not row.get('usable') or not row.get('basisQuantity'):
            continue
        if unit and convert_amount(1, unit, row.get('basisUnit')) is None:
            continue
        result.append({**deepcopy(row), 'category': category})
    primary = [row for row in result if row.get('source') not in {'retail_snapshot', 'utility_snapshot'}]
    return primary or result


def category_observation_allowed(row, category):
    """A seasoning mix was incorrectly tagged as chicken meat upstream.

    Keep exact barcode lookup usable; this exclusion is only for generic meat
    estimates, including refreshed observations from Open Prices.
    """
    return not (category == 'en:chickens' and str(row.get('id') or row.get('observationId')) == '307878')
