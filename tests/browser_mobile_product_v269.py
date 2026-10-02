"""Mobile product-editor responsiveness and camera-startup regressions."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright
from ui_offline_loader_v203 import local_html

ROOT = Path(__file__).resolve().parents[1]

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or None, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True)
        page.set_content(local_html(ROOT))
        page.wait_for_function('window.ready')
        page.evaluate("app._v78Open('manual')")
        report = page.evaluate("""() => {
            const dialog=app._v78Dialog;
            const scale=dialog.querySelector('[data-v116-weight="editor"]');
            const select=dialog.querySelector('[data-v154-container]');
            const checkbox=dialog.querySelector('[data-v154-deduct]');
            const prototypeMethods={};
            for(let proto=Object.getPrototypeOf(app);proto;proto=Object.getPrototypeOf(proto)) {
                for(const key of Object.getOwnPropertyNames(proto)) {
                    if(/_v.*(DecorateCapture|ProductContainer|DraftWeight|AutoWeight|KeepCameraWarm)$/.test(key)) {
                        const descriptor=Object.getOwnPropertyDescriptor(proto,key);
                        if(typeof descriptor.value==='function') prototypeMethods[proto.constructor.name+'.'+key]=String(descriptor.value);
                    }
                }
            }
            const layout=scale?.parentElement?.parentElement?.outerHTML || dialog.querySelector('main')?.innerHTML;
            for(let i=0;i<5;i++)app._v111Paint();
            return {layout,prototypeMethods,stableSelect:select===dialog.querySelector('[data-v154-container]'),stableCheckbox:checkbox===dialog.querySelector('[data-v154-deduct]')};
        }""")
        print(report, flush=True)
        assert report['stableSelect'], 'Scanner paints replace the active container selector'
        assert report['stableCheckbox'], 'Scanner paints replace the active tare checkbox'
        browser.close()

if __name__ == '__main__':
    run()
