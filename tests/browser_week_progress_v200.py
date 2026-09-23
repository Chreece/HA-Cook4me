"""Offline Chromium checks with real v143 ETA layer plus the weekly fix."""
from pathlib import Path
import shutil
import os
import tempfile
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / 'custom_components/cook4me/frontend'
BOUNDARY = r'''
class Boundary extends HTMLElement {
 constructor(){super();this.attachShadow({mode:'open'});this.now=0;this._v63Jobs=new Map();this._hass={user:{id:'test'}};}
 _prefKey(){return 'test.entry';}_uiIngredientLanguage(){return this.lang||'el';}_langCode(){return this.lang||'el';}
 _t(key){return key;}_v59PhaseLabel(phase){return ({catalog_index:'Αναζήτηση τοπικού καταλόγου',nutrition:'Έλεγχος θρεπτικών',ranking:'Επιλογή γευμάτων',starting:'Προετοιμασία'})[phase]||phase;}
 _processStart(){
  const card=document.createElement('div');card.className='rx-v59-op';card.innerHTML='<div class="head"><strong class="rx-v59-op-title">Εργασία σε εξέλιξη</strong><span class="rx-v59-op-count"></span><button data-cancel>Ακύρωση</button></div><div class="rx-v59-op-detail"></div><div class="rx-v59-op-track"><div class="rx-v59-op-bar"></div></div>';
  this.shadowRoot.append(card);const job={id:'test',title:'Εργασία σε εξέλιξη',card};this._v63Jobs.set(job.id,job);card.querySelector('button').onclick=()=>{job.cancelled=true;this._processEnd(job);};return job;
 }
 _processUpdate(token,detail,done,total){this._v143PaintEta(token,done,total);}
 _v59HandleProgress(event){const d=event.data||event,j=this._v63Jobs.get(d.operationId);if(j)this._processUpdate(j,d.phase,d.completed,d.total);}
 _v59FailProcess(j){j.failed=true;}
 _processEnd(j){j.ended=true;}
 _v93SendJobRequest(){return Promise.resolve({});}
 _renderTab(){} disconnectedCallback(){}
}
customElements.define('cook4me-recipe-hub-panel-v142',Boundary);
'''
bootstrap = BOUNDARY + (FRONTEND/'cook4me-panel-v143.js').read_text() + '\n' + (FRONTEND/'weekly-progress-v200.js').read_text().replace('export ', '') + r'''
class TestPanel extends WeeklyProgressMixin(customElements.get('cook4me-recipe-hub-panel-v143')) {
 _v143Now(){return this.now;}
 connectedCallback(){this.shadowRoot.innerHTML=`<style>:host{font:15px system-ui;color:#eee;background:#191919;display:block;min-height:90vh}.rx-v59-op{position:fixed;right:12px;bottom:18px;width:min(460px,calc(100vw - 48px));padding:14px;border:1px solid #555;border-radius:16px;background:#222;line-height:1.5}.head{display:flex;gap:9px;flex-wrap:wrap;align-items:center;justify-content:space-between}button{font:inherit;padding:8px;color:#eee;background:#222;border:1px solid #777;border-radius:8px}.rx-v59-op-track{height:5px;background:#555;margin-top:12px;overflow:hidden}.rx-v59-op-bar{height:5px;background:#bbb}.indeterminate .rx-v59-op-bar{animation:slide 1s alternate infinite}@keyframes slide{to{transform:translateX(130%)}}</style>`;}
}
customElements.define('week-progress-test',TestPanel);
window.make=()=>{document.querySelector('week-progress-test')?.remove();window.host=document.createElement('week-progress-test');document.body.append(host);window.job=host._processStart();host._v143EtaHistory={'kind:week_generate':{avgMs:3000},'title:εργασία σε εξέλιξη':{avgMs:3000}};};
window.send=(phase,completed,total)=>host._v59HandleProgress({data:{operationId:job.id,kind:'week_generate',phase,completed,total}});
window.ready=true;
'''
OUTPUT = Path(os.environ.get('COOK4ME_TEST_ARTIFACTS', str(Path(tempfile.gettempdir())/'cook4me-v200-browser')))
OUTPUT.mkdir(parents=True, exist_ok=True)
results = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=shutil.which('chromium') or None, args=['--no-sandbox'])
    for width, height in [(390,844),(1366,900)]:
        page = browser.new_page(viewport={'width':width,'height':height})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.set_content('<body style="background:#191919"><script type="module">'+bootstrap+'</script></body>')
        page.wait_for_function('window.ready')
        page.evaluate('make();host._v93SendJobRequest({type:"cook4me/v20/week_generate",__cook4meJobId:job.id})')
        assert page.locator('.rx-v59-op-count').inner_text()==''
        assert 'δεν είναι ακόμη γνωστός' in page.locator('[data-v143-eta]').inner_text()
        results.append(f'{width}: initial unknown work is indeterminate, not 0/1')
        page.evaluate('send("catalog_index",0,1);host.now=65000;host._v200Tick()')
        assert page.evaluate('host._v143EstimateEta(job,0,1)') == 3000  # Original estimator reproduces the faulty claim.
        eta=page.locator('[data-v143-eta]').inner_text()
        assert '1:05' in eta and 'Δεν αναφέρθηκε' in eta and 'λιγότερο' not in eta
        results.append(f'{width}: reproduced long 0/1 stage no longer borrows 3-second history')
        page.evaluate('send("catalog_index",25,200);host.now=67000;send("catalog_index",50,200)')
        assert '50 / 200' in page.locator('.rx-v59-op-count').inner_text()
        assert 'αυτό το στάδιο' in page.locator('[data-v143-eta]').inner_text()
        results.append(f'{width}: real counters and current-stage estimate advance')
        page.evaluate('send("ranking",0,21)')
        assert 'δεν είναι ακόμη γνωστός' in page.locator('[data-v143-eta]').inner_text()
        assert '0 / 21' in page.locator('.rx-v59-op-count').inner_text()
        results.append(f'{width}: next stage does not inherit catalog ETA')
        page.evaluate('host.now=90000;host._v200Tick()')
        bounds=page.locator('.rx-v59-op').bounding_box()
        assert bounds['x']>=0 and bounds['x']+bounds['width']<=width
        assert page.locator('[data-cancel]').is_visible()
        results.append(f'{width}: Greek progress and Cancel fit the viewport')
        if width==390:
            page.screenshot(path=str(OUTPUT/'progress-mobile.png'))
        page.locator('[data-cancel]').click()
        assert page.evaluate('job.cancelled&&job.ended&&host._v200Timer===null')
        results.append(f'{width}: Cancel cleans up progress timers')
        assert not errors,errors
        page.close()
    browser.close()
print('\n'.join(results))
print(f'PASS: {len(results)} browser scenario groups')
