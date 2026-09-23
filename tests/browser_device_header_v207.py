"""Compact header and quiet manual steps, optionally using the full current UI."""
import argparse
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'custom_components/cook4me/frontend'
parser=argparse.ArgumentParser()
parser.add_argument('--full-chain',action='store_true')
parser.add_argument('--screenshots',type=Path)
args=parser.parse_args()
if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)
def url(path):return 'data:text/javascript;base64,'+base64.b64encode(path.read_bytes()).decode()

def focused_html():
    # Actual inherited status logic; only the page shell and HA are boundaries.
    old=(F/'cook4me-panel-v81.js').read_text()
    words=old[old.index('const WORDS='):old.index('class Cook4MeRecipeHubPanelV81')]
    view=old[old.index(' _v81View(){'):old.index(' async _v81Subscribe()')]
    return '''<!doctype html><meta charset="utf-8"><body><script type="module">
    import {CompactDeviceHeaderMixin} from "'''+url(F/'device-header-v207.js')+'''";
    '''+words+'''
    class Base extends HTMLElement{
     constructor(){super();this.attachShadow({mode:'open'});this._entryId='one';this._hass={user:{id:'test'},connection:{}};this._entries=[{entry_id:'one',title:'Cook4Me',state:{},connected:false}];}
     _entry(){return this._entries[0];}_prefKey(){return 'test.'+this._entryId;}
     _escape(v){return String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');}
     _v81Text(k){return WORDS.el[k]||k;}_v81OpenInfo(){this.infoOpened=(this.infoOpened||0)+1;}
     '''+view+'''
     _updateHeader(){const root=this.shadowRoot.querySelector('#status');if(root)root.innerHTML=this._v130DeviceHtml(this._entry());}
     _renderTab(){this._updateHeader();}
     _renderShell(){this.classList.add('ui203');this.shadowRoot.innerHTML=`<style>
      :host{display:block;font:14px system-ui;--primary-color:#009a96;--primary-text-color:#eee;--secondary-text-color:#aaa;--card-background-color:#222;--error-color:#c44;color:var(--primary-text-color)}
      .wrap{padding:12px}.top{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;border:1px solid #444;border-radius:16px;background:var(--card-background-color)}
      .v130-device-summary{min-height:108px}.top{padding:14px 20px;min-height:140px}.v100-device{min-width:0}.actions{display:flex;gap:6px}.actions button{min-width:44px;height:44px}
      </style><div class="wrap"><div class="top v100-top"><div class="v100-device"><div id="status"></div></div><div class="actions"><button>EL</button><button>EUR</button></div></div></div>`;this._updateHeader();}
    }
    customElements.define('header-test',CompactDeviceHeaderMixin(Base));
    window.app=document.body.appendChild(document.createElement('header-test'));app._renderShell();window.ready=true;
    </script>'''

if args.full_chain:
    from ui_offline_loader_v203 import local_html
    html=local_html(ROOT)
else:html=focused_html()
checks=[]
def check(page,expression,name):
    passed = page.evaluate(expression)
    if not passed:
        print('HEADER DIAGNOSTICS:', page.evaluate("""()=>{
            const node=app.shadowRoot.querySelector('.ui207-device-state');
            const colors=[];
            for(let n=node;n;n=n.parentElement){
                const s=getComputedStyle(n);
                colors.push({node:n.tagName,id:n.id,classes:n.className,color:s.color,
                    secondary:s.getPropertyValue('--secondary-text-color'),
                    muted:s.getPropertyValue('--ui203-muted'),style:n.getAttribute('style')});
            }
            colors.push({node:'host',style:app.getAttribute('style'),
                secondary:getComputedStyle(app).getPropertyValue('--secondary-text-color'),
                muted:getComputedStyle(app).getPropertyValue('--ui203-muted')});
            return colors;
        }"""), flush=True)
    assert passed,name
    checks.append(name)
    print('PASS:', name, flush=True)

with sync_playwright() as p:
    # Prefer the pinned Playwright browser in CI; local executable is explicit.
    import os
    executable=os.environ.get('COOK4ME_TEST_CHROMIUM')
    browser=p.chromium.launch(executable_path=executable,args=['--no-sandbox'])
    for width,height in [(360,800),(390,844),(844,390),(1440,1000)]:
        page=browser.new_page(viewport={'width':width,'height':height},reduced_motion='reduce')
        page.set_default_timeout(7000)
        errors=[];page.on('pageerror',lambda e:(errors.append(str(e)),print('BROWSER ERROR:',e,flush=True)))
        page.set_content(html);page.wait_for_function('window.ready')
        prefix=f'{width}: '
        page.evaluate("""()=>{const e=app._entry();e.state={deviceName:'Χύτρα κουζίνας',phase:'idle'};e.connected=true;e.accessible=true;app._v81Subscription={context:app._prefKey(),connection:app._hass.connection,live:true};app._updateHeader();}""")
        check(page,"app.shadowRoot.querySelector('.ui207-device-name')?.textContent==='Χύτρα κουζίνας'",prefix+'HA device name is visible')
        check(page,"!app.shadowRoot.querySelector('.top .v130-model,.top .v81-cooker,.top .v130-live-screen,.top img')",prefix+'no cooker image or illustrated model in header')
        check(page,"app.shadowRoot.querySelector('.ui207-device-state').textContent.includes('Έτοιμο')",prefix+'ready state retains localized label')
        check(page,"app.shadowRoot.querySelector('.ui207-device>ha-icon').getAttribute('icon')==='mdi:check-circle-outline'",prefix+'status has a meaningful icon')
        check(page,"app.shadowRoot.querySelector('.top').getBoundingClientRect().height<=100",prefix+'single-device header is thinner than old 108px model alone')
        check(page,"app.shadowRoot.querySelector('.top').getBoundingClientRect().right<=innerWidth+1",prefix+'header fits viewport')
        page.evaluate("app._entry().connected=false;app._updateHeader()")
        check(page,"app.shadowRoot.querySelector('.ui207-device').dataset.phase==='offline'&&app.shadowRoot.querySelector('.ui207-device-state').textContent.includes('εκτός σύνδεσης')",prefix+'disconnected cooker cannot appear ready')
        page.evaluate("app._entry().connected=true;app._entry().state.phase='cooking';app._updateHeader()")
        check(page,"app.shadowRoot.querySelector('.ui207-device').dataset.phase==='cooking'",prefix+'live cooking changes status')
        page.evaluate("app._v81Subscription.live=false;app._v81Subscription.failed=true;app._updateHeader()")
        check(page,"app.shadowRoot.querySelector('.ui207-device').dataset.phase==='unavailable'",prefix+'lost telemetry does not keep stale cooking state')
        page.evaluate("app._v81Subscription.live=true;app._v81Subscription.failed=false;app._entry().state.deviceName='<img src=x onerror=window.injected=true> '+ 'Πολύμεγάλοόνομα'.repeat(25);app._updateHeader()")
        check(page,"!window.injected&&!app.shadowRoot.querySelector('.ui207-device img')&&app.shadowRoot.querySelector('.ui207-device').title.includes('<img')",prefix+'long user name is safe text with full tooltip')
        check(page,"app.shadowRoot.querySelector('.ui207-device').getBoundingClientRect().right<=innerWidth+1",prefix+'long name cannot widen header')
        page.evaluate("app._entry().state.deviceName='Χύτρα κουζίνας';app._updateHeader();app.shadowRoot.querySelector('.ui207-device').focus();app._entry().state.phase='paused';app._updateHeader()")
        check(page,"app.shadowRoot.activeElement?.classList.contains('ui207-device')",prefix+'status redraw preserves keyboard focus')
        # Keep inherited details action; intercept only opening in the small shell.
        page.keyboard.press('Enter')
        check(page,"!!app._v81InfoDialog?.isConnected||app.infoOpened===1",prefix+'Enter opens device information')
        if args.full_chain:page.evaluate('app._v81CloseInfo()')
        page.evaluate("app._entry().state.phase='idle';app._updateHeader()")
        # Theme variables remain inherited, not a hardcoded dark header.
        page.evaluate("document.body.classList.add('light');app.style.setProperty('--card-background-color','#ffffff');app.style.setProperty('--primary-text-color','#182f32');app.style.setProperty('--secondary-text-color','#526a6e')")
        check(page,"getComputedStyle(app.shadowRoot.querySelector('.ui207-device-state')).color==='rgb(82, 106, 110)'",prefix+'light theme status contrast follows HA variables')
        # Reuse DOM to prove that a former operation can become a quiet manual step.
        page.evaluate('''async module=>{const {decorateStepModes}=await import(module);window.preview=document.createElement('div');preview.innerHTML='<div data-v66-step="0"><span class="step-num">1</span><span>Keep this instruction</span></div>';app.shadowRoot.append(preview);decorateStepModes(preview,{steps:[{programName:'Browning'}]},'el');window.decorateModes=decorateStepModes;}''',url(F/'recipe-step-modes-v204.js'))
        check(page,"!!preview.querySelector('[data-v204-step-modes]')",prefix+'actual operation gets a badge')
        page.evaluate("decorateModes(preview,{steps:[{typeName:'Preparation',instruction:'Keep this instruction'}]},'el')")
        check(page,"!preview.querySelector('[data-v204-step-modes],.v204-program-step,.v204-step-content')&&preview.textContent==='1Keep this instruction'",prefix+'manual step removes metadata and extra spacing, retains instruction')
        page.evaluate("decorateModes(preview,{steps:[{instruction:'Pressure cooking mentioned as text'}]},'el')")
        check(page,"!preview.querySelector('[data-v204-step-modes]')",prefix+'instructions alone never invent device operation')
        if args.screenshots:
            page.locator('.top').screenshot(path=str(args.screenshots/f'compact-header-{width}.png'))
        assert not errors,errors
        page.close()
    browser.close()
print('\n'.join('PASS: '+name for name in checks))
print(f'PASS: {len(checks)} assertions ({"full frontend" if args.full_chain else "production status/renderer, controlled shell"})')
