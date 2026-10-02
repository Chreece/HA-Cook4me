"""Full shipped catalog, not the three-row fixture: input latency and semantics."""
import json
import os
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright, expect
from test_catalog_lifecycle_v227 import catalog
from ui_offline_loader_v203 import local_html

ROOT=Path(__file__).resolve().parents[1]

def settled(page,query):
    page.wait_for_function('''q=>!app._v270QueryTimer && app._v78Dialog.querySelector('[data-v114-links]')?._v270State?.query===q && app._v270CatalogIndex.position===app._v270CatalogIndex.index.rows.length''',arg=query)

def run():
    data={lang:catalog.ingredient_choices(lang) for lang in ('el','de')}
    html=local_html(ROOT);reports=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or None,args=['--no-sandbox'])
        for width in (390,1440):
            page=browser.new_page(viewport={'width':width,'height':844},is_mobile=width<500,has_touch=True)
            page.set_default_timeout(12000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.set_content(html);page.wait_for_function('window.ready')
            page.evaluate('''raw=>{
                const data=JSON.parse(raw);
                app._ingredientCatalog=data.el;app._ingredientCatalogLanguage='el';
                app._v79Settings={country:'DE',supermarketLanguage:'de'};
                app._v140MarketNames=new Map();for(const r of data.de)for(const id of [r.key,r.ingredientId,...r.sourceIngredientIds||[]])if(id)app._v140MarketNames.set(id,r.name);
                app._v140MarketCatalogKey=app._prefKey()+':de';app._filters().seasonalIngredients=true;
                window.renders=0;const render=app._v78RenderCapture.bind(app);app._v78RenderCapture=(...args)=>{renders++;return render(...args);};
            }''',json.dumps(data,ensure_ascii=False))
            if width<500:page.context.new_cdp_session(page).send('Emulation.setCPUThrottlingRate',{'rate':4})
            timing=page.evaluate('''async()=>{const start=performance.now();await app._v78Open('manual');return {openMs:performance.now()-start,nodes:app._v78Dialog.querySelectorAll('*').length};}''')
            assert timing['openMs']<2000,timing
            assert timing['nodes']<650,timing
            assert page.locator('dialog [data-v223-toggle]').count()==0
            assert page.locator('[data-v114-link]').count()==60
            page.wait_for_function('app._v270CatalogIndex.position===app._v270CatalogIndex.index.rows.length')
            timing['idlePaintMs']=page.evaluate('''()=>{const start=performance.now();for(let i=0;i<10;i++)app._v111Paint();return (performance.now()-start)/10;}''')
            assert timing['idlePaintMs']<60,timing
            # Every row remains accessible via bounded pages, including the last.
            assert page.evaluate('''()=>{
                const seen=new Set();let pages=0;
                do{for(const n of app._v78Dialog.querySelectorAll('[data-v220-ingredient]'))seen.add(n.dataset.v220Ingredient);
                   const next=app._v78Dialog.querySelector('[data-v270-next]');if(next.disabled)break;next.click();
                }while(++pages<100);
                return seen.size;
            }''')==3249
            name=page.locator('main [data-draft="productName"]');name.fill('Natron')
            page.locator('main [data-draft="quantity"]').focus()
            settled(page,'natron')
            expect(page.locator('[data-v78-search]')).to_have_value('Natron')
            assert page.locator('[data-v114-link]').count()==1
            assert page.evaluate('app._v114Links().length')==0
            page.locator('[data-v114-link]').check()
            assert page.evaluate('app._v114Links()[0].canonicalName')=='Bicarbonate of soda'
            page.evaluate('''()=>{window.kept=app._v78Dialog.querySelector('[data-v114-link]');for(let i=0;i<10;i++){app._v111Paint();app._v78IngredientOptions();}if(kept!==app._v78Dialog.querySelector('[data-v114-link]'))throw Error('replaced checkbox');}''')
            search=page.locator('[data-v78-search]');search.fill('Pfeffer');settled(page,'pfeffer')
            results=page.evaluate('''()=>[...app._v78Dialog.querySelectorAll('.v114-link-list label')].filter(n=>!n.firstElementChild.checked).map(n=>n._v220Ingredient.canonicalName)''')
            assert 'Salmon fillets' not in results and 'Fresh cheese' not in results,results
            assert results[0]=='Pepper',results
            assert len(results)==7,results
            # Explicit catalog searches and linked ingredients are not overwritten.
            name.fill('Other product name');page.locator('main [data-draft="quantity"]').focus()
            expect(search).to_have_value('Pfeffer')
            assert page.evaluate('app._v114Links()[0].canonicalName')=='Bicarbonate of soda'
            # A stale debounced query cannot be installed on the next fresh form.
            search.fill('obsolete query')
            page.evaluate("app._v196Reset('discarded')")
            settled(page,'');expect(page.locator('[data-v78-search]')).to_have_value('')
            assert page.locator('[data-v114-link]').count()==60
            # Seasonal preference remains active in recipe/catalog views, not here.
            assert page.evaluate('app._filters().seasonalIngredients') is True
            page.locator('[data-v78-search]').fill('Erdbeer');settled(page,'erdbeer')
            assert page.locator('[data-v114-link]').count()>0
            page.evaluate("app._v78Close(true)")
            page.evaluate("app._v112EditLot('lot-rice')")
            assert page.evaluate("app._v78Draft.editLotId")=='lot-rice'
            assert page.locator('dialog [data-v223-toggle]').count()==0
            assert page.locator('[data-v114-link]').count()<=61
            # Pending search/prime work cannot reopen a closed editor.
            page.locator('[data-v78-search]').fill('Pfeffer');page.evaluate('app._v78Close(true)')
            page.wait_for_timeout(200);assert page.evaluate('app._v78Dialog===null')
            assert not errors,errors
            reports.append({'width':width,'cpuThrottle':4 if width<500 else 1,**timing,'pfeffer':results})
            print('PASS full-catalog product editor',json.dumps(reports[-1],ensure_ascii=False),flush=True)
            page.close()
        browser.close()
    target=os.environ.get('PRODUCT_CATALOG_REPORT')
    if target:Path(target).write_text(json.dumps(reports,ensure_ascii=False,indent=2))

if __name__=='__main__':run()
