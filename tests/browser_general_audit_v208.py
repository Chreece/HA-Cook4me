"""Actual current frontend: delayed reads must not undo user actions."""
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright
from ui_offline_loader_v203 import local_html

ROOT=Path(__file__).resolve().parents[1]
checks=[]

def check(page,expression,description):
    assert page.evaluate(expression),description
    checks.append(description)
    print('PASS:',description,flush=True)

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium') or None,args=['--no-sandbox'])
    html=local_html(ROOT)
    for width,height in [(360,800),(390,844),(844,390),(1440,1000)]:
        page=browser.new_page(viewport={'width':width,'height':height},reduced_motion='reduce')
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.set_default_timeout(7000)
        page.set_content(html);page.wait_for_function('window.ready')
        page.evaluate("""()=>{
          app.show('profile');window.originalApi=app._api.bind(app);window.releaseDetails={};
          app._api=(type,data)=>type.endsWith('/product_details')
            ?new Promise(resolve=>{releaseDetails[data.lot_id]=()=>originalApi(type,data).then(resolve);})
            :originalApi(type,data);
          window.first=app._v112EditLot('lot-rice');window.second=app._v112EditLot('lot-carrot');
        }""")
        page.evaluate("async()=>{releaseDetails['lot-carrot']();await second;releaseDetails['lot-rice']();await first;}")
        check(page,"app._v78Draft.editLotId==='lot-carrot'&&app._v78Draft.quantity===750",f'{width}: latest selected package wins reversed responses')
        check(page,"app._v78Draft.expectedVersion==='fixture-revision'&&app.shadowRoot.querySelectorAll('.v78-capture').length===1",f'{width}: one editor and original optimistic revision')
        check(page,"app._v78Dialog.querySelector('[data-v196-save]')&&!app.calls.some(c=>c.type.endsWith('/product_add'))",f'{width}: opening an edit never mutates stock')
        page.evaluate("async()=>{app._v78Close(true);window.late=app._v112EditLot('lot-rice');await app._v78Open('manual');}")
        page.locator('main [data-draft=productName]').fill('Keep my new draft')
        page.evaluate("async()=>{releaseDetails['lot-rice']();await late;}")
        check(page,"app._v78Draft.productName==='Keep my new draft'&&!app._v78Draft.editLotId",f'{width}: late lookup cannot erase manual input')
        page.evaluate("async()=>{app._v78Close(true);window.late=app._v112EditLot('lot-rice');app.show('week');releaseDetails['lot-rice']();await late;}")
        check(page,"!app._v78Dialog&&app._tab==='week'",f'{width}: navigation cancels stale editor opening')
        page.evaluate("""async()=>{
          window.releaseWrite=null;
          app._hass.connection.sendMessagePromise=message=>message.preferences
            ?new Promise(resolve=>{releaseWrite=resolve;})
            :Promise.resolve({lastTab:'today',filtersByView:{week:{maxCost:99,ingredients:[]}}});
          app._v63PrefsLoaded='';
          app._persistPreferences({filters:{...app._filters(),maxCost:7,ingredients:['k:rice']},lastTab:'week'});
          await app._restorePreferences();
        }""")
        check(page,"app._tab==='week'&&app._filters().maxCost===7&&app._filters().ingredients.includes('k:rice')",f'{width}: pending filters and active view survive refresh')
        page.evaluate('releaseWrite({})');page.wait_for_timeout(60)
        check(page,"app._filters().maxCost===7&&!app._v63Dirty&&!app._v199PreferenceRequest",f'{width}: confirmed save retains filters and clears pending state')
        assert not errors,errors
        page.close()
    browser.close()
print(f'PASS: {len(checks)} full-current-frontend browser assertions')
