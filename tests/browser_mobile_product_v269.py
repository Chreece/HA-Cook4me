"""Use the active production runtime; fake only HA/device boundaries."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import expect, sync_playwright
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]

LAYOUT = """() => {
    const c=app._v78Dialog;
    const quantity=c.querySelector('main [data-draft="quantity"]');
    const unit=c.querySelector('main [data-draft="unit"]');
    const row=quantity.closest('[data-v269-weight-row]');
    const block=c.querySelector('[data-v154-container-field]');
    const date=c.querySelector('main [data-draft="bestBefore"]');
    if(!row||!row.contains(unit)||row.nextElementSibling!==block)throw Error('Tare must immediately follow weight AND unit');
    if(!block.compareDocumentPosition(date)&Node.DOCUMENT_POSITION_FOLLOWING)throw Error('Dates must follow tare');
    if(!(block.compareDocumentPosition(date)&Node.DOCUMENT_POSITION_FOLLOWING))throw Error('Dates precede tare');
    if(c.querySelectorAll('[data-v154-container-field]').length!==1)throw Error('Duplicate container block');
    const r=row.getBoundingClientRect(),b=block.getBoundingClientRect(),dt=date.getBoundingClientRect();
    if(b.top<r.bottom-1||dt.top<b.bottom-1)throw Error('Tare is not visually between weight and dates');
    return {weightBottom:r.bottom,containerTop:b.top,containerBottom:b.bottom,dateTop:dt.top};
}"""

def run():
    html=local_html(ROOT)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or None,args=['--no-sandbox'])
        for width in (360,390,1440):
            page=browser.new_page(viewport={'width':width,'height':844},is_mobile=width<500,has_touch=True)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.set_default_timeout(8000)
            page.set_content(html);page.wait_for_function('window.ready')
            page.evaluate("app._v78Open('manual')")
            page.locator('main [data-draft="quantity"]').scroll_into_view_if_needed()
            print('LAYOUT',width,page.evaluate(LAYOUT),flush=True)
            page.locator('[data-v154-container]').select_option('jar-1')
            page.locator('[data-v154-deduct]').check()
            page.evaluate("""() => {
                window.controls={select:app._v78Dialog.querySelector('[data-v154-container]'),check:app._v78Dialog.querySelector('[data-v154-deduct]'),name:app._v78Dialog.querySelector('main [data-draft="productName"]')};
                app._ingredientCatalogLoading=true;app._v78Draft.priceLoading=true;
                const start=performance.now();for(let i=0;i<20;i++)app._v111Paint();
                window.paintTime=performance.now()-start;
                for(const [key,selector] of Object.entries({select:'[data-v154-container]',check:'[data-v154-deduct]',name:'main [data-draft="productName"]'})) {
                    if(controls[key]!==app._v78Dialog.querySelector(selector))throw Error('Replaced live control: '+key);
                }
            }""")
            # Background metadata must not mask the form or intercept touch input.
            name=page.locator('main [data-draft="productName"]')
            name.tap();name.press_sequentially('Natron',delay=25)
            expect(name).to_have_value('Natron')
            page.locator('[data-v154-deduct]').uncheck()
            page.locator('[data-v154-deduct]').check()
            page.evaluate("""() => {
                app._ingredientCatalogLoading=false;app._v78Draft.priceLoading=false;
                app._v116Net=()=>1000;
                app._v116UseDraftWeight();
                if(Number(app._v78Draft.quantity)!==873)throw Error('Container tare not preserved');
                if(app._v78Draft.containerId!=='jar-1'||!app._v78Draft.deductContainer)throw Error('Container selection lost');
            }""")
            expect(page.locator('main [data-draft="quantity"]')).to_have_value('873')
            print('PASS',width,'touch typing, persistent controls, metadata loads, 1000-127=873g; 20 paints(ms)=',page.evaluate('paintTime'),flush=True)
            page.evaluate("app._v78Close(true)")
            page.evaluate("app._v112EditLot('lot-rice')")
            assert page.evaluate("app._v78Draft.editLotId")=='lot-rice'
            page.locator('main [data-draft="quantity"]').scroll_into_view_if_needed()
            page.evaluate(LAYOUT)
            assert not errors,errors
            page.close()

        page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_default_timeout(8000);page.set_content(html);page.wait_for_function('window.ready')
        page.evaluate("""() => {
            const real=customElements.get('cook4me-recipe-hub-panel-v180-runtime-v269').prototype;
            // Remove the fixture's camera no-ops. Production acquisition and
            // cancellation run against a deliberately slow device boundary.
            app._v78Camera=real._v78Camera.bind(app);
            app._v141KeepCameraWarm=real._v141KeepCameraWarm.bind(app);
            window.requests=0;window.enumerations=0;window.stopped=0;
            Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{
                enumerateDevices:()=>{enumerations++;return Promise.resolve([]);},
                getUserMedia:()=>{requests++;return new Promise((resolve,reject)=>{window.cameraResolve=resolve;window.cameraReject=reject;});}
            }});
            if(app._v180CameraCapability()!==true||enumerations!==0)throw Error('Form capability waits on enumeration');
            window.opening=app._v78Open('barcode');
        }""")
        expect(page.locator('[data-v269-startup]')).to_be_visible()
        expect(page.locator('[data-v269-status]')).to_contain_text('κάμερας')
        page.wait_for_function("typeof cameraResolve==='function'")
        assert page.evaluate('requests')==1
        page.locator('[data-v269-manual]').tap()
        expect(page.locator('main [data-draft="productName"]')).to_be_visible()
        page.locator('main [data-draft="productName"]').fill('Natron during startup')
        page.evaluate("cameraResolve({getTracks:()=>[{stop:()=>stopped++}],getVideoTracks:()=>[]})")
        page.wait_for_function('stopped===1')
        expect(page.locator('main [data-draft="productName"]')).to_have_value('Natron during startup')
        assert page.evaluate('requests')==1
        assert page.evaluate('app._v78Draft.mode')=='manual'
        print('PASS camera: immediate status, manual touch during pending permission, late stream stopped without replacing draft',flush=True)
        page.evaluate("app._v78Close(true);window.cameraResolve=null;window.opening=app._v78Open('barcode');void 0")
        page.wait_for_function("typeof cameraResolve==='function'")
        page.locator('[data-v78-close]').tap()
        page.evaluate("cameraResolve({getTracks:()=>[{stop:()=>stopped++}],getVideoTracks:()=>[]})")
        page.wait_for_function('stopped===2')
        assert page.evaluate('app._v78Dialog===null')
        print('PASS camera: close remains responsive during acquisition; late stream released',flush=True)
        assert not errors,errors
        page.close();browser.close()

if __name__=='__main__':run()
