"""Product saves reach the real transport while unrelated background work waits."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import expect, sync_playwright
from ui_offline_loader_v203 import local_html

ROOT=Path(__file__).resolve().parents[1]

def run():
    html=local_html(ROOT).replace(
        '_api(type,data={}){\n  this.calls.push',
        "_api(type,data={}){\n  if(/\\/(product_add|ai_create)$/.test(type))return super._api(type,data);\n  this.calls.push",
    )
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or None,args=['--no-sandbox'])
        for width,height in ((390,844),(1440,980)):
            page=browser.new_page(viewport={'width':width,'height':height})
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.set_default_timeout(5000);page.set_content(html);page.wait_for_function('window.ready')
            page.evaluate("""async () => {
                window.requests=[];window.pendingSaves=[];
                app._hass.connection.sendMessagePromise=async message=>{
                    const request=message.request||message;requests.push(structuredClone(message));
                    if(request.type.endsWith('/ai_create'))return new Promise(resolve=>window.finishBackground=resolve);
                    if(request.type.endsWith('/product_add'))return new Promise((resolve,reject)=>pendingSaves.push({resolve,reject}));
                    return {};
                };
                window.background=app._api('cook4me/v22/ai_create',{entry_id:app._entryId}).catch(error=>{window.backgroundError=error;});
                await app._v78Open('manual');
                app._v78Dialog.querySelector('[data-v112-barcode-edit]').value='1234567890123';
                await app._v196Lookup();
                const d=app._v78Draft;
                if(!d.scanRecognized||d.quantity!==500)throw new Error('Barcode lookup did not populate the editor');
                Object.assign(d,{productName:'Scanned and edited rice',quantity:750,unit:'g',
                    ingredient:app._ingredientCatalog[0],ingredientLinks:[app._ingredientCatalog[0]],
                    nutrition:{basisUnit:'g',basisQuantity:100,values:{protein:7}},editorOpen:true});
                app._v78RenderCapture();
                window.savedDraft=d;
            }""")
            page.wait_for_function("typeof finishBackground==='function'")
            page.locator('[data-v196-save]').click()
            # Never release the blocked background job to let Save pass.
            page.wait_for_function('pendingSaves.length===1',timeout=1500)
            assert page.evaluate('app._v78Busy') is True
            assert page.evaluate('app._v78Draft===savedDraft') is True
            payload=page.evaluate('requests.find(m=>(m.request||m).type.endsWith("/product_add"))')
            request=payload.get('request',payload)
            assert request['quantity']==750 and request['lot_metadata']['barcode']=='1234567890123'
            assert request['lot_metadata']['productName']=='Scanned and edited rice'
            assert request['nutrition']['values']['protein']==7
            background=page.evaluate('requests.find(m=>(m.request||m).type.endsWith("/ai_create"))')
            assert payload['job_id']!=background['job_id']
            # Repeated taps cannot add another product while storage is pending.
            page.evaluate('app._v78Save()')
            assert page.evaluate('pendingSaves.length')==1
            page.evaluate("pendingSaves[0].reject({code:'connection_lost',message:'Reply lost'})")
            page.wait_for_function('!app._v78Busy')
            assert page.evaluate('app._v78Draft===savedDraft') is True
            page.locator('[data-v196-save]').click()
            page.wait_for_function('pendingSaves.length===2',timeout=1500)
            retry=page.evaluate('requests.filter(m=>(m.request||m).type.endsWith("/product_add"))[1]')
            assert retry['request']==request
            if width==1440:
                page.evaluate('app._v93CancelJob(app._v63Jobs.get(requests.find(m=>(m.request||m).type.endsWith("/ai_create")).job_id))')
                assert page.evaluate('backgroundError.code')=='job_cancelled'
                assert page.evaluate('app._v78Busy') is True
                assert page.evaluate('app._v63Jobs.has(requests.filter(m=>(m.request||m).type.endsWith("/product_add"))[1].job_id)') is True
            page.evaluate("pendingSaves[1].resolve({houseIngredients:app._houseIngredients,warnings:[]})")
            page.wait_for_function('app._v78Draft!==savedDraft&&!app._v78Busy')
            expect(page.locator('main [data-draft="productName"]')).to_have_value('')
            if width==390:
                assert page.evaluate('app._v63Jobs.has(requests.find(m=>(m.request||m).type.endsWith("/ai_create")).job_id)') is True
            page.evaluate('finishBackground({});background')
            assert not errors,errors
            print(f'PASS {width}px: immediate dispatch, separate jobs/cancellation, durable acknowledgement, identical retry')
            page.close()
        browser.close()

if __name__=='__main__':run()
