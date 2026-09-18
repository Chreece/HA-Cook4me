#!/usr/bin/env python3
"""Compare recipe-level DE/EUR offline eligibility with the published v85 tree.

No network, live household prices, stock or HA installation are required. A
variant is complete only when every ingredient has a usable amount and price.
Counts are language/serving variants, not unique recipe families.
"""
import argparse
import ast
from collections import Counter, defaultdict
import importlib
import json
from pathlib import Path
import subprocess
import sys
import types

ROOT=Path(__file__).resolve().parents[1]
COMPONENT=ROOT/'custom_components/cook4me'
BASE='b21d95d2f095af50e691e76997073770e8774c6d'


def categories(source):
    result={}
    for node in ast.parse(source).body:
        if isinstance(node,ast.For) and isinstance(node.iter,ast.Tuple):
            for tag,_kind,names in ast.literal_eval(node.iter):
                for name in names.split('|'):
                    result[name]=tag if ':' in tag else 'en:'+tag
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default=BASE);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    def previous(path):
        return subprocess.check_output(['git','show',args.base+':custom_components/cook4me/'+path],cwd=ROOT,text=True)
    package=types.ModuleType('_cook4me_coverage_audit');package.__path__=[str(COMPONENT)]
    sys.modules[package.__name__]=package
    measures=importlib.import_module(package.__name__+'.price_measurements')
    inventory=importlib.import_module(package.__name__+'.inventory')
    namespace={};exec(compile(previous('price_units.py'),'v85_price_units','exec'),namespace)
    catalog=json.loads((COMPONENT/'catalog/merged_catalog.v1.json').read_text())
    names={row['id']:row['canonicalName'] for row in catalog['ingredients']}
    snapshot=json.loads((COMPONENT/'catalog/observed_prices.v1.json').read_text())
    snapshot['observations']+=json.loads((COMPONENT/'catalog/retail_prices.v1.json').read_text())['observations']
    result={'market':'DE','currency':'EUR','base':args.base,'variantCounts':True,'results':{}}
    for version,evidence,mapping in [
            ('before',json.loads(previous('catalog/observed_prices.v1.json')),categories(previous('automatic_prices.py'))),
            ('after',snapshot,categories((COMPONENT/'automatic_prices.py').read_text()))]:
        refs=defaultdict(list)
        for row in evidence['observations']:
            if row['country']=='DE' and row['currency']=='EUR':
                for cat in row['categories']:refs[cat].append(row)
        summary=defaultdict(Counter);missing=Counter()
        for recipe in catalog['recipes']:
            for variant in recipe['variants']:
                covered=0;rows=variant.get('ingredients',[])
                for raw in rows:
                    item={**raw,'canonicalName':names.get(raw.get('ingredientId'),'')}
                    if version=='after':options=measures.price_options(item)
                    else:
                        item=namespace['price_ingredient'](item)
                        options=[item] if item.get('quantity') is not None and item.get('unit') else []
                    tag=mapping.get(item['canonicalName'].strip().casefold())
                    priced=any(inventory.convert_amount(1,o['unit'],r['basisUnit']) is not None
                        for o in options for r in refs[tag]) if tag else False
                    covered+=priced
                    if not priced:missing[item['canonicalName']]+=1
                status='complete' if rows and covered==len(rows) else 'partial' if covered else 'noCost'
                for language in ['all',variant.get('language','unknown')]:
                    summary[language][status]+=1;summary[language]['pricedIngredients']+=covered
                    summary[language]['totalIngredients']+=len(rows)
        result['results'][version]={'summary':dict(summary),'largestMissing':missing.most_common(20)}
    if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({version:{lang:data['summary'][lang] for lang in ['all','de','en']}
                      for version,data in result['results'].items()},indent=2))


if __name__=='__main__':main()
