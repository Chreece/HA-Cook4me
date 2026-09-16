#!/usr/bin/env python3
"""Audit observed coverage and separate budget fallback coverage, with real catalog matches."""
import argparse
from collections import Counter
from datetime import date, timedelta
import importlib
import json
from pathlib import Path
import sys
from audit_recipe_price_coverage_v90 import runtime, COMPONENT, EXAMPLES


def audit():
    quantities, ns = runtime(COMPONENT, '_audit91')
    inventory = importlib.import_module('_audit91.inventory')
    benchmarks = importlib.import_module('_audit91.price_benchmarks')
    snapshot = importlib.import_module('_audit91.price_snapshot')
    catalog = json.loads((COMPONENT/'catalog/merged_catalog.v1.json').read_text())
    by_id = {str(row['id']): row for row in catalog['ingredients']}
    refs = {}
    today = date.today()
    for row in snapshot._load()['observations']:
        if row.get('country')!='DE' or row.get('currency')!='EUR' or not row.get('usable') or not row.get('basisQuantity'):
            continue
        if not today-timedelta(days=180)<=date.fromisoformat(row['date'])<=today: continue
        for category in row.get('categories',[]):
            if category not in row.get('categoryExclusions',[]) and snapshot.category_observation_allowed(row,category):
                refs.setdefault(category,[]).append(row)
    total=Counter();examples=[];cache={};missing=Counter();unavailableNames=Counter()
    for family in catalog['recipes']:
        for variant in family['variants']:
            ingredients=variant.get('ingredients',[])
            subset=[by_id[str(x['ingredientId'])] for x in ingredients if str(x.get('ingredientId')) in by_id]
            recipe=ns['canonical_recipe'](variant,subset);known=fallback=eligible=0;gaps=[];new=[]
            for item in recipe['ingredients']:
                signature=json.dumps(item,sort_keys=True)
                if signature not in cache:
                    options=quantities.price_options(item);category=ns['category_for'](item)
                    priced=bool(category) and any(inventory.convert_amount(1,o['unit'],r['basisUnit']) is not None for o in options for r in refs.get(category[0],[]))
                    usable=item.get('priceCatalogMatched') and any(inventory.convert_amount(1,o['unit'],u) is not None for o in options for u in ['g','ml','pcs'])
                    estimate=benchmarks.fallback_estimate(item,country='DE',currency='EUR') if not priced else None
                    cache[signature]=priced,bool(usable),estimate
                priced,usable,estimate=cache[signature];known+=priced;eligible+=usable;fallback+=bool(estimate)
                if estimate:new.append({'name':item.get('canonicalName') or item['name'],'kind':estimate['level'],'group':estimate['group'],'amount':estimate['amount'],'samples':estimate['sampleCount']})
                if not priced and not estimate:
                    reason='quantity/unit unavailable' if not usable else 'water requires compatible tariff unit' if item.get('canonicalName','').casefold() in {'water','tap water'} else 'benchmark unavailable';unavailableNames[item.get('canonicalName') or item['name']]+=bool(usable);gaps.append({'name':item.get('canonicalName') or item['name'],'reason':reason});missing[reason]+=1
            count=len(recipe['ingredients']);total.update(variants=1,ingredients=count,known=known,fallback=fallback,covered=known+fallback,matchedWithUsableAmount=eligible)
            total['knownComplete']+=known==count and count>0;total['budgetComplete']+=known+fallback==count and count>0
            total['noKnownCost']+=known==0;total['noBudgetCost']+=known+fallback==0
            if str(variant.get('variantId')) in EXAMPLES:examples.append({'id':variant['variantId'],'title':variant['title'],'known':known,'fallback':fallback,'covered':known+fallback,'total':count,'estimates':new,'missing':gaps})
    return {'market':'DE','currency':'EUR','asOf':today.isoformat(),'variantCounts':True,'summary':dict(total),'remainingReasons':dict(missing),'unavailableWithUsableAmount':{k:v for k,v in unavailableNames.items() if v},'examples':examples}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args();result=audit()
    if args.output:args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
