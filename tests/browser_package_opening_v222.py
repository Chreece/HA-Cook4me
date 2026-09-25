"""Exercise actual product editor and cooking review at mobile/desktop sizes."""
from pathlib import Path
import shutil
from playwright.sync_api import expect, sync_playwright
from ui_offline_loader_v203 import local_html
ROOT=Path(__file__).resolve().parents[1]

def run():
    html=local_html(ROOT).replace('_api(type,data={}){\n  this.calls.push',
        '_api(type,data={}){\n  if(/\\/(opening_guidance|product_add|product_details|consumption_confirm)$/.test(type))return super._api(type,data);\n  this.calls.push')
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=shutil.which('chromium') or None,args=['--no-sandbox'])
        for width,height in [(390,844),(1440,980)]:
            page=browser.new_page(viewport={'width':width,'height':height});page.set_default_timeout(7000)
            errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
            page.set_content(html);page.wait_for_function('window.ready')
            page.evaluate('''async () => {
                window.requests=[];
                window.rule={id:'fixture-rule',daysMin:3,daysMax:3,brand:'Fixture',storage:'fridge',maxTemperatureC:4,conditions:['closed_container']};
                window.stock=[{key:'rice',name:'Ρύζι',unit:'g',lots:[
                    {id:'first',quantity:500,productName:'Πρώτη συσκευασία',bestBefore:'2099-12-31',useWithinDays:3,applyOpeningExpiry:false},
                    {id:'second',quantity:500,productName:'Δεύτερη συσκευασία',bestBefore:'2099-12-31',useWithinDays:3,applyOpeningExpiry:true},
                    {id:'old',quantity:500,productName:'Ήδη ανοιχτό',bestBefore:'2099-12-31',openedAt:'2026-09-01',useWithinDays:3,applyOpeningExpiry:true}]}];
                app._hass.connection.sendMessagePromise=async msg=>{
                    if(msg.type.endsWith('/job_run'))return app._hass.connection.sendMessagePromise(msg.request);
                    requests.push(structuredClone(msg));
                    if(msg.type.endsWith('/opening_guidance'))return {rules:msg.lot_metadata.brand==='Fixture'?[rule]:[]};
                    if(msg.type.endsWith('/product_details'))return {lot:stock[0].lots[0],unit:'g',ingredient:{key:'rice',name:'Ρύζι'},version:'fixture'};
                    return {houseIngredients:stock};
                };
                await app._v78Open('manual');
                Object.assign(app._v78Draft,{productName:'Γάλα',quantity:500,unit:'g',bestBefore:'2099-12-31',ingredient:{key:'rice',name:'Ρύζι'},ingredientLinks:[{key:'rice',name:'Ρύζι'}],editorOpen:true});
                app._v78RenderCapture();
            }''')
            days=page.locator('main [data-draft="useWithinDays"]')
            section=days.locator('xpath=ancestor::details')
            section.locator('summary').click()
            expect(page.locator('[data-v222-opened]')).not_to_be_visible()
            days.fill('3')
            expect(page.locator('[data-v222-opened]')).to_be_visible()
            page.locator('[data-v222-apply]').check();page.locator('[data-v222-opened]').check()
            today=page.evaluate('app._todayIso()')
            expect(page.locator('main [data-draft="openedAt"]')).to_have_value(today)
            assert page.evaluate('app._v78Draft.applyOpeningExpiry')
            # Repainting the existing form retains the chosen state and open section.
            before=page.evaluate('app._v78Dialog.scrollTop');page.evaluate('app._v78RenderCapture()')
            page.wait_for_timeout(100)
            assert abs(page.evaluate('app._v78Dialog.scrollTop')-before)<3
            expect(page.locator('[data-v222-opened]')).to_be_checked()
            page.locator('[data-v196-save]').click()
            page.wait_for_function("requests.some(r=>r.type.endsWith('/product_add'))")
            metadata=page.evaluate("requests.find(r=>r.type.endsWith('/product_add')).lot_metadata")
            assert metadata['openedAt']==today and metadata['useWithinDays']=='3' and metadata['applyOpeningExpiry'] is True,metadata
            page.evaluate('app._v78Close(true)')

            # Editing preserves an explicit opt-out, then allows opening the package.
            page.evaluate("app._v112EditLot('first')")
            page.wait_for_function("app._v78Draft?.editLotId==='first'")
            section=page.locator('main [data-draft="useWithinDays"]').locator('xpath=ancestor::details')
            if not section.evaluate('(n)=>n.open'):section.locator('summary').click()
            expect(page.locator('[data-v222-apply]')).not_to_be_checked()
            page.locator('[data-v222-opened]').check();page.locator('[data-v222-apply]').check()
            page.locator('[data-v196-save]').click()
            page.wait_for_function("requests.some(r=>r.type.endsWith('/product_add')&&r.edit_lot_id==='first')")
            assert page.evaluate("requests.find(r=>r.edit_lot_id==='first').lot_metadata.openedAt") == today

            # Catalog guidance is gated by its handling instructions; manual entry overrides it.
            page.evaluate('''() => {Object.assign(app._v78Draft,{brand:'Fixture',ingredient:{key:'rice',name:'Ρύζι'},ingredientLinks:[{key:'rice',name:'Ρύζι'}],editorOpen:true});app._v78RenderCapture();}''')
            page.wait_for_function("app._v78Dialog.querySelector('[data-v222-rule] option[value=\"fixture-rule\"]')")
            section=page.locator('main [data-draft="useWithinDays"]').locator('xpath=ancestor::details')
            if not section.evaluate('(n)=>n.open'):section.locator('summary').click()
            page.locator('[data-v222-rule]').select_option('fixture-rule')
            expect(page.locator('[data-v222-opened]')).to_be_disabled()
            page.locator('[data-v222-conditions]').check()
            expect(page.locator('[data-v222-opened]')).to_be_enabled()
            page.locator('[data-v222-opened]').check()
            page.locator('[data-v222-rule]').select_option('')
            days.fill('2');assert page.evaluate('app._v78Draft.openingRuleId')==''
            page.evaluate('app._v78Close(true)')

            # The completion review sends exact package IDs, leaving other packages closed.
            page.evaluate('''() => {
                app._houseIngredients=stock;app._syncEntryProfile();
                app._pendingConsumption={id:'pending-fixture',recipeTitle:'Δοκιμή',servings:2,ingredients:[{identity:'k:rice',name:'Ρύζι',quantity:100,unit:'g'}]};
                const host=document.createElement('div');host.id='opening-review';app.shadowRoot.append(host);
                host.innerHTML=app._pendingHtml();app._bindPending(host);
            }''')
            first=page.locator('[data-v222-package="first"]')
            expect(first.locator('[data-opened]')).not_to_be_checked()
            first.locator('[data-opened]').check();first.locator('[data-apply]').check()
            expect(page.locator('[data-v222-package="second"] [data-opened]')).not_to_be_checked()
            expect(page.locator('[data-v222-package="old"] [data-opened]')).to_be_checked()
            expect(page.locator('[data-v222-package="old"] [data-opened]')).to_be_disabled()
            page.locator('#confirmConsumption').click()
            page.wait_for_function("requests.some(r=>r.type.endsWith('/consumption_confirm'))")
            openings=page.evaluate("requests.find(r=>r.type.endsWith('/consumption_confirm')).ingredients[0].packageOpenings")
            assert openings==[{'lotId':'first','applyOpeningExpiry':True}],openings
            assert not errors,errors
            print(f'PASS {width}: manual, edit, catalog conditions, scroll retention and exact-package cooking review',flush=True)
            page.close()
        browser.close()
if __name__=='__main__':run()
