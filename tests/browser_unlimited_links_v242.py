"""Edit actual catalog links on unlimited stock using the production UI chain."""
from pathlib import Path
import shutil
from playwright.sync_api import expect,sync_playwright
from test_catalog_lifecycle_v227 import catalog
from test_catalog_lifecycle_v231 import actual_choice
from ui_offline_loader_v203 import local_html

ROOT=Path(__file__).resolve().parents[1]
rows=catalog.ingredient_choices('el')
fine=actual_choice(rows,'local:fr:87539cfe8febf2a1f850')
sea=actual_choice(rows,'local:de:bc258b7cadb2219a4cda')
key=lambda row:row.get('key') or row.get('ingredientId') or row['id']
html=local_html(ROOT).replace('_api(type,data={}){\n  this.calls.push',
    '_api(type,data={}){\n  if(type.endsWith("/inventory_update")||type.endsWith("/inventory_remove"))return super._api(type,data);\n  this.calls.push')

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox'])
    for width,height in ((390,844),(1440,980)):
        page=browser.new_page(viewport={'width':width,'height':height})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.set_default_timeout(7000)
        page.set_content(html);page.wait_for_function('window.ready')
        page.evaluate("""rows=>{
            app._ingredientCatalog=rows;app._ingredientCatalogLanguage='el';
            app._houseIngredients=[...app._houseIngredients,{key:'M_FOOD_457',name:'Αλάτι',productName:'Αλάτι κουζίνας',unlimited:true,storageLocationId:'pantry',bestBefore:'2027-01-02'},
                {key:'M_FOOD_165',name:'Νερό',unlimited:true}];
            app._entry().profile.houseIngredients=app._houseIngredients;
            window.stockWrites=[];window.failStock=false;
            app._hass.connection.sendMessagePromise=async msg=>{
                if(msg.type.endsWith('/job_run'))return app._hass.connection.sendMessagePromise(msg.request);
                if(msg.type.endsWith('/inventory_remove'))return {houseIngredients:app._houseIngredients.filter(row=>'k:'+row.key!==msg.identity)};
                if(msg.type.endsWith('/inventory_update')){
                    stockWrites.push(structuredClone(msg));await new Promise(resolve=>setTimeout(resolve,120));
                    if(failStock)throw new Error('Save failed');
                    const data=structuredClone(app._houseIngredients),row=data.find(row=>'k:'+row.key===msg.identity);
                    row.ingredientLinks=msg.ingredient_links;row.unlimited=msg.unlimited;
                    if(msg.best_before)row.bestBefore=msg.best_before;else delete row.bestBefore;
                    return {houseIngredients:data};
                }
                return {};
            };
            app.show('profile');
        }""",rows)
        stock=page.locator('[data-stock-row="2"]')
        for parent in stock.locator('xpath=ancestor::details').all():
            if not parent.evaluate('node=>node.open'):parent.locator(':scope > summary').click()
        fold=stock.locator('[data-v242-links]')
        fold.locator(':scope > summary').click()
        expect(fold.locator('[data-v242-link="M_FOOD_457"]')).to_be_checked()
        expect(fold.locator('[data-v242-link="M_FOOD_457"]')).to_be_disabled()
        assert fold.locator('[data-v242-link]').count()>3000
        for ingredient,query in ((fine,'Fine salt'),(sea,'Sea salt')):
            fold.locator('[data-v242-search]').fill(query)
            target=fold.locator('[data-v242-link="'+key(ingredient)+'"]')
            target.scroll_into_view_if_needed()
            before=fold.locator('[data-v242-list]').evaluate('node=>node.scrollTop')
            target.check()
            assert abs(fold.locator('[data-v242-list]').evaluate('node=>node.scrollTop')-before)<2
        expect(fold.locator(':scope > summary')).to_contain_text('(3)')
        stock.locator('[data-stock-save]').click()
        expect(stock.locator('[data-stock-save]')).to_be_disabled()
        page.wait_for_function('stockWrites.length===1&&app._houseIngredients[2].ingredientLinks?.length===3')
        request=page.evaluate('stockWrites[0]')
        assert request['unlimited'] is True and request['identity']=='k:M_FOOD_457'
        assert {r['key'] for r in request['ingredient_links']}=={'M_FOOD_457',key(fine),key(sea)}
        assert 'lots' not in request and 'quantity' not in request
        assert page.evaluate("app._houseIngredients[2].storageLocationId==='pantry'&&app._houseIngredients[2].bestBefore==='2027-01-02'")
        assert page.evaluate('ingredient=>app._v112StockRows(ingredient).some(row=>row.unlimited)',sea)
        # Navigate away and reopen: saved secondary assignments remain checked.
        page.evaluate("app.show('today');app.show('profile')")
        for parent in stock.locator('xpath=ancestor::details').all():
            if not parent.evaluate('node=>node.open'):parent.locator(':scope > summary').click()
        if not fold.evaluate('node=>node.open'):fold.locator(':scope > summary').click()
        expect(fold.locator('[data-v242-link="'+key(fine)+'"]')).to_be_checked()
        expect(fold.locator('[data-v242-link="'+key(sea)+'"]')).to_be_checked()
        # Failure keeps the user's selection and allows retry; it does not mutate stock.
        fold.locator('[data-v242-link="'+key(fine)+'"]').uncheck()
        page.evaluate('failStock=true')
        stock.locator('[data-stock-save]').click()
        page.wait_for_function('stockWrites.length===2')
        expect(stock.locator('[data-stock-save]')).to_be_enabled()
        expect(fold.locator('[data-v242-link="'+key(fine)+'"]')).not_to_be_checked()
        assert page.evaluate('app._houseIngredients[2].ingredientLinks.length===3')
        page.evaluate('failStock=false')
        stock.locator('[data-stock-save]').click()
        page.wait_for_function('stockWrites.length===3&&app._houseIngredients[2].ingredientLinks.length===2')
        assert not page.evaluate('key=>app._houseIngredients[2].ingredientLinks.some(row=>row.key===key)',key(fine))
        assert page.evaluate('app._houseIngredients.length===4&&app._houseIngredients[2].unlimited&&!app._houseIngredients[2].lots')
        assert stock.evaluate('node=>node.scrollWidth<=node.clientWidth+1')
        # Removing an item also removes an unsaved assignment draft.
        if not fold.evaluate('node=>node.open'):fold.locator(':scope > summary').click()
        fold.locator('[data-v242-search]').fill('Fine salt')
        fold.locator('[data-v242-link="'+key(fine)+'"]').check()
        stock.locator('[data-stock-remove]').click()
        page.wait_for_function('app._houseIngredients.length===3')
        assert page.evaluate("![...app._v242Edits.keys()].some(key=>JSON.parse(key)[1]==='k:M_FOOD_457')")
        assert not errors,errors
        print(f'PASS {width}: full catalog, add/remove, reload, retry, linked stock preview, one unlimited item and no scroll jump')
        page.close()
    browser.close()
