"""Alphabetical stock/search and post-save camera continuity on the active runtime."""
from pathlib import Path
import shutil
from playwright.sync_api import expect, sync_playwright
from ui_offline_loader_v203 import local_html

ROOT=Path(__file__).resolve().parents[1]
STOCK_SEED="""() => {
 const names=[['tom','Tomaten Stücke','Ντομάτα κονσέρβας'],['kidney','Kidneybohnen','Κόκκινα φασόλια'],['coconut','Kokosmilch','Γάλα καρύδας'],['chili','Chili Mix','Πιπεριά τσίλι']];
 app._houseIngredients=names.map(([key,product,name],i)=>({key,name,unit:'g',quantity:100+i,lots:[{id:'lot-'+key,productName:product,quantity:100+i,storageLocationId:'pantry',ingredientLinks:[{key,name}]}]}));
 app._houseIngredients.push({key:'salt',name:'Αλάτι',unit:'g',quantity:null,unlimited:true,ingredientLinks:[{key:'salt',name:'Αλάτι'}]});
 app._ingredientCatalog=app._houseIngredients.map(({key,name})=>({key,name,ingredientId:key,presentationVersion:63,displayLanguage:'el',searchAliases:[name]}));
 app._v78State.houseIngredients=app._entry().profile.houseIngredients=app._houseIngredients;
 window.originalStock=JSON.stringify(app._houseIngredients);app.show('profile');app.shadowRoot.querySelector('#houseInventoryRows').parentElement.open=true;
}"""
CAMERA="""() => {
 window.cameraCalls=0;window.barcode='';window.lookups=0;window.photos=[];window.pendingSaves=[];window.saveCalls=[];window.detects=0;
 Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>{
  cameraCalls++;const canvas=document.createElement('canvas');canvas.width=640;canvas.height=480;canvas.getContext('2d').fillRect(0,0,640,480);
  return canvas.captureStream(10);
 }}});
 window.BarcodeDetector=class {static async getSupportedFormats(){return ['ean_13'];}async detect(){detects++;return barcode?[{rawValue:barcode}]:[];}};
 const api=app._api.bind(app);
 app._api=(type,data)=>{
  if(type.endsWith('/barcode_lookup'))lookups++;
  if(type.endsWith('/recognize_photo')){
   photos.push(data.mode);
   return Promise.resolve(data.mode==='date'?{product:{bestBefore:'2026-12-31'}}:{product:{productName:'AI Rice',quantity:500,unit:'g'},match:{ingredient:app._ingredientCatalog[0]}});
  }
  if(type.endsWith('/product_add')){saveCalls.push(structuredClone(data));return new Promise((resolve,reject)=>pendingSaves.push({resolve,reject}));}
  return api(type,data);
 };
}"""

def run():
    html=local_html(ROOT)
    # Only the network/device boundaries are mocked. Use production acquisition,
    # barcode-loop, recognition, save acknowledgement and cancellation methods.
    camera_html=html.replace("async _v78Camera(){this.cameraRequested=(this.cameraRequested||0)+1;}", "").replace("_v141KeepCameraWarm(){}", "")
    assert camera_html!=html
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=shutil.which('chromium') or None,args=['--no-sandbox'])
        for width in (390,1440):
            page=browser.new_page(viewport={'width':width,'height':844},is_mobile=width<500,has_touch=True)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.set_default_timeout(10000);page.set_content(html);page.wait_for_function('window.ready');page.evaluate(STOCK_SEED)
            groups=page.locator('#houseInventoryRows > .v112-stock-group')
            headings=groups.locator(':scope > summary > strong').all_text_contents()
            assert [x.split(' (')[0] for x in headings]==['Αλάτι','Chili Mix','Kidneybohnen','Kokosmilch','Tomaten Stücke'],headings
            assert page.evaluate('JSON.stringify(app._houseIngredients)===originalStock')
            search=page.locator('[data-v271-stock-query]')
            expect(search).to_be_visible()
            # Open a group and keep its DOM/input state while filtering.
            page.evaluate("window.stockGroup=app.shadowRoot.querySelector('[data-v112-group=kokosmilch]');stockGroup.open=true;window.stockNode=stockGroup.querySelector('[data-v112-edit-lot]')")
            search.fill('ΓΑΛΑ ΚΑΡΥΔΑΣ')
            expect(page.locator('#houseInventoryRows > .v112-stock-group:not([hidden])')).to_have_count(1)
            assert page.evaluate('stockGroup.open&&stockGroup.querySelector("[data-v112-edit-lot]")===stockNode')
            page.evaluate("app._renderInventoryOnly(app.shadowRoot.querySelector('[data-v78-kitchen]'))")
            expect(search).to_have_value('ΓΑΛΑ ΚΑΡΥΔΑΣ')
            expect(page.locator('#houseInventoryRows > .v112-stock-group:not([hidden])')).to_have_count(1)
            search.fill('not-in-stock');expect(page.locator('[data-v271-stock-status]')).to_contain_text('Δεν βρέθηκαν')
            search.fill('tom stuck')
            expect(page.locator('#houseInventoryRows > .v112-stock-group:not([hidden])')).to_have_count(1)
            # Filtering does not rebind a different product to an existing button.
            page.locator('[data-v112-group="tomaten stücke"] > summary').click()
            page.locator('#houseInventoryRows [data-v112-edit-lot="lot-tom"]').click()
            page.wait_for_function("app._v78Draft?.editLotId==='lot-tom'")
            page.evaluate('app._v78Close(true)')
            search=page.locator('[data-v271-stock-query]');expect(search).to_have_value('tom stuck')
            search.press('Escape');expect(search).to_have_value('')
            expect(page.locator('#houseInventoryRows > .v112-stock-group:not([hidden])')).to_have_count(5)
            # A sorted legacy unlimited row must still address its original index.
            assert page.locator('[data-v112-group="k:salt"] [data-stock-row]').get_attribute('data-stock-row')=='4'
            search.fill('Kidney');page.evaluate("app._entryId='other-context';app._v271StockControls(app.shadowRoot)")
            expect(search).to_have_value('')
            search.fill('Chili');expect(page.locator('#houseInventoryRows > .v112-stock-group:not([hidden])')).to_have_count(1)
            page.locator('[data-v271-stock-clear]').click();expect(search).to_have_value('')
            if width==390 and Path('/mnt/data').is_dir():
                search.scroll_into_view_if_needed();page.screenshot(path='/mnt/data/cook4me-v271-stock-mobile.png')
            assert not errors,errors
            print(f'PASS {width}px: alphabetical groups, Greek/German search, clear/no-results, refresh retention, exact lot edit and unchanged stock indices',flush=True)
            page.close()

        page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_default_timeout(10000);page.set_content(camera_html);page.wait_for_function('window.ready');page.evaluate(CAMERA)
        page.evaluate("window.barcode='1234567890123';window.opening=app._v78Open('barcode');void 0")
        page.wait_for_function("app._v78Draft?.scanRecognized&&!app._v78Busy")
        assert page.evaluate('app._v271ReturnMode()')=='barcode'
        page.evaluate("app._v112Editor(true);app._v78Draft.ingredient=app._ingredientCatalog[0];app._v78Draft.ingredientLinks=[app._ingredientCatalog[0]];app._v78RenderCapture();window.oldDraft=app._v78Draft")
        page.locator('[data-v196-save]').click();page.wait_for_function('pendingSaves.length===1')
        page.evaluate('app._v78Save()');assert page.evaluate('pendingSaves.length')==1
        assert page.evaluate('app._v78Draft===oldDraft&&app._v78Busy')
        page.evaluate("pendingSaves[0].reject({code:'connection_lost',message:'Reply lost'})")
        page.wait_for_function('!app._v78Busy');assert page.evaluate('app._v78Draft===oldDraft')
        page.locator('[data-v196-save]').click();page.wait_for_function('pendingSaves.length===2')
        assert page.evaluate('JSON.stringify(saveCalls[0])===JSON.stringify(saveCalls[1])')
        page.evaluate('pendingSaves[1].resolve({houseIngredients:app._houseIngredients})')
        page.wait_for_function("app._v78Draft!==oldDraft&&app._v78Draft.mode==='barcode'&&!app._v78Draft.editorOpen&&app._v78Stream")
        page.wait_for_timeout(750)
        assert page.evaluate('lookups')==1,'Same saved barcode immediately scanned again'
        assert page.evaluate('app._v78Draft.productName')==''
        assert page.evaluate('app._v78Draft.requestId!==oldDraft.requestId')
        print('PASS barcode: durable retry, no early reset, resume live barcode scan and suppress old barcode',flush=True)
        page.evaluate("window.barcode='';app._v78Close(true)")
        page.wait_for_timeout(80)
        page.evaluate("window.opening=app._v78Open('product');void 0")
        page.wait_for_function('app._v78Stream&&app._v78Dialog.querySelector("video").videoWidth>0')
        page.evaluate('app._v78CaptureFrame()')
        page.wait_for_function('app._v78Draft.scanRecognized&&!app._v78Busy')
        assert page.evaluate('app._v271ReturnMode()')=='product'
        page.evaluate("app._v80Scan('date')")
        page.wait_for_function('app._v78Stream&&app._v78Dialog.querySelector("video").videoWidth>0')
        page.evaluate('app._v78CaptureFrame()')
        assert page.evaluate('app._v271ReturnMode()')=='product'
        # Save directly from the collapsed scan result, not just manual editor.
        page.evaluate("app._v78Draft.ingredient=app._ingredientCatalog[0];app._v78Draft.ingredientLinks=[app._ingredientCatalog[0]];window.oldDraft=app._v78Draft;void app._v78Save()")
        page.wait_for_function('pendingSaves.length===3')
        page.evaluate('pendingSaves[2].resolve({houseIngredients:app._houseIngredients})')
        page.wait_for_function("app._v78Draft!==oldDraft&&app._v78Draft.mode==='product'&&!app._v78Draft.editorOpen&&app._v78Stream")
        page.wait_for_timeout(250)
        assert page.evaluate('photos')==['product','date'],'AI auto-captured or lost previous mode'
        assert page.evaluate('app._v78Draft.productName')==''
        if Path('/mnt/data').is_dir():page.screenshot(path='/mnt/data/cook4me-v271-ai-resumed-mobile.png')
        print('PASS AI: returns to AI after auxiliary date scan; fresh draft, live camera, no automatic AI request',flush=True)
        page.evaluate('app._v78Close(true)');page.wait_for_timeout(80)
        page.evaluate("app._v78Open('manual')")
        page.locator('[data-v112-barcode-edit]').fill('1234567890123');page.evaluate('app._v196Lookup()')
        assert page.evaluate('!app._v271ReturnMode()')
        page.evaluate("app._v78Draft.ingredient=app._ingredientCatalog[0];app._v78Draft.ingredientLinks=[app._ingredientCatalog[0]];window.beforeCamera=cameraCalls;void app._v78Save()")
        page.wait_for_function('pendingSaves.length===4');page.evaluate('pendingSaves[3].resolve({houseIngredients:app._houseIngredients})')
        page.wait_for_function("app._v78Draft.mode==='manual'&&!app._v78Busy&&app._v78Draft.productName===''")
        assert page.evaluate('cameraCalls===beforeCamera')
        print('PASS manual: typed barcode lookup/save stays manual; scan mode does not leak between products',flush=True)
        page.evaluate('app._v78Close(true)');page.wait_for_timeout(80)
        page.evaluate("window.opening=app._v78Open('product');void 0")
        page.wait_for_function('app._v78Stream&&app._v78Dialog.querySelector("video").videoWidth>0')
        page.evaluate('app._v78CaptureFrame()')
        page.evaluate("app._v112Editor(true);app._v78Draft.quantity='';app._v78RenderCapture();window.before=cameraCalls;void app._v78Save()")
        expect(page.locator('main [data-draft="quantity"]')).to_have_attribute('aria-invalid','true')
        assert page.evaluate('pendingSaves.length')==4
        assert page.evaluate('cameraCalls===before&&app._v78Draft.editorOpen')
        page.locator('main [data-draft="quantity"]').fill('500')
        page.evaluate("app._v78Draft.ingredient=app._ingredientCatalog[0];app._v78Draft.ingredientLinks=[app._ingredientCatalog[0]];window.oldDraft=app._v78Draft;void app._v78Save()")
        page.wait_for_function('pendingSaves.length===5')
        page.evaluate("pendingSaves[4].resolve({houseIngredients:app._houseIngredients,warnings:['Review required']})")
        page.wait_for_function('!app._v78Busy')
        assert page.evaluate('app._v78Draft===oldDraft&&app._v78Draft.editorOpen&&cameraCalls===before')
        page.evaluate('void app._v78Save()');page.wait_for_function('pendingSaves.length===6')
        page.evaluate('app._v78Close(true);pendingSaves[5].resolve({houseIngredients:app._houseIngredients})')
        page.wait_for_timeout(150)
        assert page.evaluate('app._v78Dialog===null&&cameraCalls===before')
        print('PASS safeguards: validation/warning does not resume; late save acknowledgement after close cannot reopen camera',flush=True)
        assert not errors,errors
        page.close();browser.close()

if __name__=='__main__':run()
