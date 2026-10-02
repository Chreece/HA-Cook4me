"""Real-browser regression for finite-only deduction UI and depleted shopping prompt."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import expect, sync_playwright
from ui_offline_loader_v203 import local_html

ROOT=Path(__file__).resolve().parents[1]

def run():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or None,args=['--no-sandbox'])
        for width,height in ((390,844),(1440,980)):
            page=browser.new_page(viewport={'width':width,'height':height},is_mobile=width<500,has_touch=width<500)
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.set_default_timeout(6000);page.set_content(local_html(ROOT));page.wait_for_function('window.ready')
            result=page.evaluate("""() => {
                app._houseIngredients=[
                  {key:'salt',name:'Salt',unlimited:true,unit:'g'},
                  {key:'mint',name:'Mint',unit:'g',quantity:12,lots:[{id:'m1',quantity:12}]},
                ];
                const options=app._v131StockOptions('k:mint');
                window.shoppingCalls=[];
                app._api=async(type,data)=>{shoppingCalls.push({type,data:structuredClone(data)});return {added:1};};
                app._v272DepletedPrompt=[{key:'mint',name:'Mint'}];
                app._v272ShowDepletedPrompt();
                return {options};
            }""")
            assert 'Mint' in result['options']
            assert 'Salt' not in result['options']
            expect(page.locator('[data-v272-depleted-overlay]')).to_be_visible()
            expect(page.locator('[data-v272-depleted-overlay]')).to_contain_text('Mint')
            call=page.evaluate("""async () => {
                const button=app.shadowRoot.querySelector('[data-v272-shopping-add]');
                await button.onclick();
                return shoppingCalls[0]||null;
            }""")
            assert call is not None, errors
            assert call['type']=='cook4me/v11/shopping_add'
            assert call['data']['ingredients']==[{'key':'mint','name':'Mint'}]
            expect(page.locator('[data-v272-depleted-overlay]')).to_have_count(0)
            assert not errors,errors
            print(f'PASS {width}px: unlimited hidden; depleted stock asks and adds exact item to shopping list')
            page.close()
        browser.close()

if __name__=='__main__':
    run()
