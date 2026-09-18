"""Allowlisted diagnostic evidence shared by every recipe and device."""
from copy import deepcopy
from datetime import datetime, timezone


_STATE_KEYS = ('connected', 'available', 'uiFirmware', 'wifiFirmware', 'phase', 'status',
               'recipeFunctionalId', 'variantFunctionalId', 'eventDate', 'cookingVersion')


def device_snapshot(data):
    return {key: data[key] for key in _STATE_KEYS if key in data and isinstance(data[key], (str, int, float, bool, type(None)))}


def recipe_snapshot(meta):
    out = {key: meta[key] for key in ('groupingFunctionalId', 'recipeFunctionalId', 'searchVariantId', 'language', 'market', 'stepCount')
           if key in meta and isinstance(meta[key], (str, int, float, bool, type(None)))}
    definition = meta.get('deliveryDefinition')
    if isinstance(definition, dict):
        # Generated from public recipe structure, never raw HTTP/auth material.
        out['definition'] = deepcopy(definition)
    return out


def record(bridge, phase, variant_id, meta=None):
    if phase == 'resolving' or not getattr(bridge, '_last_recipe_delivery', None):
        bridge._last_recipe_delivery = {'requestedVariantId': str(variant_id), 'events': []}
    report = bridge._last_recipe_delivery
    if report['requestedVariantId'] != str(variant_id):
        return
    report['phase'] = phase
    if isinstance(meta, dict):
        report['recipe'] = recipe_snapshot(meta)
    report['events'].append({'phase': phase, 'at': datetime.now(timezone.utc).isoformat(),
                             'device': device_snapshot(bridge.data)})
    report['events'] = report['events'][-20:]
