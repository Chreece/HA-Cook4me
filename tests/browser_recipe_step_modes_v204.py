"""Step badges in real shared renderer; optionally the whole current UI chain."""
import argparse
import base64
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--full-chain',action='store_true')
parser.add_argument('--screenshots',type=Path)
args=parser.parse_args()
if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)

# Test data uses explicit metadata; instruction prose must never set a mode.
STEPS=[
 {'stepIndex':3,'typeName':'Préparation','instruction':'Ετοιμάστε τα υλικά.'},
 {'stepIndex':5,'functionalId':'brown','programKey':'PROGRAM_B','programName':'Dorer','instruction':'Σοτάρετε τα λαχανικά.'},
 {'stepIndex':8,'functionalId':'pressure','programKey':'PROGRAM_P','programName':'Druckgaren','instruction':'Μαγειρέψτε για 5 λεπτά.'},
 {'instruction':'Στη συνέχεια διατηρήστε το φαγητό ζεστό.','programs':[{'programName':'Steaming'},{'programName':'Keep warm'}]},
 {'programKey':'PROGRAM_999','instruction':'Pressure cooking is mentioned, but the mode is unknown.'},
 {'programName':'<img src=x onerror="window.injected=true">','instruction':'Original source text, not HTML.'},
]

def renderer_html():
    module=(ROOT/'custom_components/cook4me/frontend/recipe-step-modes-v204.js').read_bytes()
    url='data:text/javascript;base64,'+base64.b64encode(module).decode()
    source=(ROOT/'custom_components/cook4me/frontend/cook4me-panel-v66.js').read_text()
    body=source[source.index(' _v66Body('):source.index('\n _v66IngredientName(')]
    return '''<!doctype html><html><meta charset="utf-8"><body><script type="module">
    import {RecipeStepModesMixin,decorateStepModes} from "'''+url+'''";
    class Boundary extends HTMLElement {
     constructor(){super();this.attachShadow({mode:'open'});this.language='el';}
     _uiIngredientLanguage(){return this.language;}
     _escape(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');}
     _t(value){return value;}_languageName(value){return value;}_v66IngredientName(value){return value.name;}
     _coverage(){return {percent:null};}_displayAmount(){return '';}_servingOptions(){return [];}_servings(){return 2;}
     _v66LocalAiAvailable(){return false;}_isFavorite(){return false;}_v66Icon(){return '';}
     _stepText(step){return typeof step==='string'?step:step?.instruction||'';}
    '''+body+'''
    }
    class Fixture extends RecipeStepModesMixin(Boundary){}
    customElements.define('step-mode-test',Fixture);
    window.app=document.body.appendChild(document.createElement('step-mode-test'));
    app.shadowRoot.innerHTML='<style>:host{display:block;font:16px system-ui;--primary-color:#007f7a;--primary-text-color:#183337;--secondary-text-color:#526a6e;--card-background-color:#fff;--secondary-background-color:#eaf0ee;--divider-color:#d4dedb}#modePreview{padding:12px}.rx-v66-steps{padding:0;list-style:none}.step{padding:12px 0;line-height:1.5}.step-num{font-weight:700}</style>';
    window.decorateStepModes=decorateStepModes;window.ready=true;
    </script></body></html>'''

if args.full_chain:
    from ui_offline_loader_v203 import local_html
    html=local_html(ROOT)
else:html=renderer_html()
checks=[]
def check(page,expression,name):
    assert page.evaluate(expression),name
    checks.append(name)

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium') or None,args=['--no-sandbox'])
    for width,height in [(390,844),(844,390),(1440,1000)]:
        page=browser.new_page(viewport={'width':width,'height':height},reduced_motion='reduce')
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(html);page.wait_for_function('window.ready')
        page.evaluate('steps=>{window.modeRecipe=window.samples?samples(0):{title:"Ρύζι με λαχανικά",language:"el",ingredients:[]};modeRecipe.steps=steps;window.originalModes=JSON.stringify(modeRecipe);window.modeState={sections:new Set(["steps"]),expanded:true};const main=document.createElement("section");main.id="modePreview";app.shadowRoot.append(main);window.drawModes=()=>{main.innerHTML=app._v66Body(modeRecipe,false,modeState)};drawModes()}',STEPS)
        prefix=f'{width}: '
        check(page,"app.shadowRoot.querySelectorAll('#modePreview [data-v204-step-modes]').length===5",prefix+'only the five device-operation steps receive mode metadata')
        check(page,"!app.shadowRoot.querySelector('#modePreview [data-v66-step=\"0\"] [data-v204-step-modes]')",prefix+'preparation step has no device label or metadata row')
        check(page,"app.shadowRoot.querySelector('#modePreview [data-v204-mode=pressure]').textContent.includes('Μαγείρεμα υπό πίεση')",prefix+'Greek mode from German program name')
        check(page,"app.shadowRoot.querySelector('#modePreview [data-v66-step=\"2\"] .step-num').textContent==='9'",prefix+'sparse provider numbering remains unchanged')
        check(page,"app.shadowRoot.querySelector('#modePreview [data-v66-step=\"3\"] .v204-mode-list').textContent.includes('→')",prefix+'multiple modes shown in order')
        check(page,"app.shadowRoot.querySelector('#modePreview [data-v66-step=\"4\"] [data-v204-mode=missing]')!==null",prefix+'opaque program is not guessed from instructions')
        check(page,"!window.injected&&!app.shadowRoot.querySelector('#modePreview .v204-step-modes img')",prefix+'program names rendered as text not markup')
        check(page,"JSON.stringify(modeRecipe)===originalModes",prefix+'recipe data and instructions not modified')
        page.evaluate('drawModes();drawModes()')
        check(page,"app.shadowRoot.querySelectorAll('#modePreview [data-v204-step-modes]').length===5&&app.shadowRoot.querySelectorAll('#stepModesV204').length===1",prefix+'repeat rendering does not duplicate badges or stylesheet')
        check(page,"[...app.shadowRoot.querySelectorAll('#modePreview .v204-step-modes')].every(x=>x.getBoundingClientRect().right<=innerWidth+1)",prefix+'mode labels fit viewport')
        check(page,"!app.shadowRoot.querySelector('#modePreview .v204-step-modes button, #modePreview .v204-step-modes input')",prefix+'badges are information not cooker controls')
        if not args.full_chain:
            page.evaluate("app.language='de';drawModes()")
        else:page.evaluate("app._uiIngredientLanguage=()=> 'de';drawModes()")
        check(page,"app.shadowRoot.querySelector('#modePreview [data-v204-mode=pressure]').textContent.includes('Druckgaren')",prefix+'UI-language change updates mode')
        if args.screenshots and not args.full_chain:page.screenshot(path=str(args.screenshots/f'step-modes-{width}.png'),full_page=True)
        page.evaluate("modeRecipe.steps=[];drawModes()")
        check(page,"!app.shadowRoot.querySelector('#modePreview [data-v204-step-modes]')",prefix+'empty recipe does not retain stale badges')
        if args.full_chain:
            page.evaluate('steps=>{app.shadowRoot.getElementById("modePreview").remove();app._uiIngredientLanguage=()=>"el";app.show("today");const r=app._todayResults[0];r.steps=steps;const s=app._v66State(r);s.expanded=true;s.sections.add("steps");app._renderTab()}',STEPS)
            check(page,"app.shadowRoot.querySelector('article.ui203-recipe [data-v204-mode=pressure]')!==null",prefix+'actual v203 card renderer retains step modes')
            page.locator('[data-v66-photo]').first.click()
            page.wait_for_function('app._v63RecipeDialog?.isConnected')
            check(page,"app._v63RecipeDialog.querySelectorAll('[data-v204-step-modes]').length===5",prefix+'actual fullscreen recipe receives same badges')
            page.evaluate('window.modeBefore=app._opened.steps[2].programName;app._renderRecipeDialog()')
            check(page,"app._opened.steps[2].programName===modeBefore&&app._v63RecipeDialog.querySelectorAll('[data-v204-step-modes]').length===5",prefix+'fullscreen redraw retains evidence once')
            # Actual inherited previous/next highlighting is untouched.
            page.evaluate('const s=app._v66State(app._opened);s.cooking=true;s.step=2;app._renderRecipeDialog()')
            check(page,"app._v63RecipeDialog.querySelector('[data-v66-step=\"2\"]').getAttribute('aria-current')==='step'",prefix+'active cooking-step highlighting preserved')
            if args.screenshots:page.screenshot(path=str(args.screenshots/f'fullscreen-modes-{width}.png'),full_page=True)
            page.locator('[data-modal-close]').click()
            page.evaluate('app.show("official");app.show("today")')
            page.wait_for_timeout(80)
            check(page,"!app._v63RecipeDialog?.isConnected",prefix+'explicitly closed fullscreen stays closed')
            check(page,"!app.sendRequests",prefix+'displaying modes never sends cooker actions')
        assert not errors,errors
        page.close()
    browser.close()
print('\n'.join('PASS: '+v for v in checks))
print(f'PASS: {len(checks)} browser assertions ({"full current UI chain" if args.full_chain else "shared production renderer"})')
