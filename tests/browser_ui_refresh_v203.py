"""Actual frontend-chain checks, with local HA/API/icon and recipe-data fixtures.

No server, remote photos, HA instance, real inventory, AI or physical camera.
"""
from pathlib import Path
import argparse
import shutil
from playwright.sync_api import sync_playwright
from ui_offline_loader_v203 import local_html

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--screenshots',type=Path)
parser.add_argument('--width',type=int)
args=parser.parse_args()
if args.screenshots: args.screenshots.mkdir(parents=True,exist_ok=True)
results=[]

def check(page,expression,description):
    assert page.evaluate(expression),description
    results.append(description)
    print('PASS:',description,flush=True)

def shot(page,name,full=False):
    if args.screenshots:page.screenshot(path=str(args.screenshots/(name+'.png')),full_page=full)

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium') or None,args=['--no-sandbox'])
    html=local_html(ROOT)
    sizes=[(360,800),(390,844),(844,390),(1440,1000)]
    if args.width:sizes=[x for x in sizes if x[0]==args.width]
    for width,height in sizes:
        page=browser.new_page(viewport={'width':width,'height':height},reduced_motion='reduce')
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_default_timeout(5000)
        page.set_content(html)
        page.wait_for_function('window.ready')
        prefix=f'{width}: '
        for tab,expected in [('today',3),('week',21),('official',8),('book',3),('mine',2),('shopping',0),('profile',0)]:
            page.evaluate('(tab)=>app.show(tab)',tab)
            page.wait_for_timeout(70)
            check(page,"app.classList.contains('ui203') && app.shadowRoot.querySelectorAll('#ui203Theme').length===1",prefix+tab+' shares one design layer')
            check(page,f"app.shadowRoot.querySelectorAll('article.ui203-recipe').length==={expected}",prefix+tab+' keeps expected records')
            check(page,"document.documentElement.scrollWidth<=innerWidth+1 && app.shadowRoot.getElementById('content').getBoundingClientRect().right<=innerWidth+1",prefix+tab+' fits viewport')
            check(page,"(()=>{const ns=[...app.shadowRoot.querySelectorAll('#tabs .tab')];return ns.length===7&&ns.every((n,i)=>{const s=n.querySelector('.ui203-nav-label');return s&&getComputedStyle(s).display!=='none'&&n.offsetHeight>=44&&(!i||n.getBoundingClientRect().left>=ns[i-1].getBoundingClientRect().right-1)})})()",prefix+tab+' navigation labels do not overlap')
        # Correct source identities and dietary eligibility must survive styling.
        page.evaluate("app.show('week')")
        check(page,"[...app.shadowRoot.querySelectorAll('.rx-week-day')].every(n=>n.querySelectorAll('.rx-week-slot').length===3 && n.querySelector('.ui203-day-meta')?.textContent.includes('3'))",prefix+'day grouping keeps all three meals with each date')
        check(page,"[...app.shadowRoot.querySelectorAll('article.ui203-recipe')].every(n=>{const media=n.querySelector('.rx-v69-media'),dock=n.querySelector('.ui203-action-dock');return media&&!media.contains(dock)&&dock.getBoundingClientRect().top>=media.getBoundingClientRect().bottom-1})",prefix+'recipe actions stay below photos')
        page.locator('article.ui203-recipe details.ui203-more > summary').first.click()
        page.locator('article.ui203-recipe details.ui203-more[open] [data-v66-action=expand]').first.click()
        page.wait_for_timeout(80)
        check(page,"(()=>{const list=app.shadowRoot.querySelector('article.ui203-recipe .rx-v66-ingredients');if(!list)return false;const labels=[...list.querySelectorAll('.v218-stored-at')].map(n=>n.textContent);return labels.some(x=>x.includes('Ντουλάπι'))&&labels.some(x=>x.includes('Ψυγείο'))})()",prefix+'expanded recipe ingredients show their defined storage places')
        check(page,"app.shadowRoot.querySelector('[aria-current=date] .ui203-today')?.textContent==='Σήμερα'",prefix+'today has an explicit day badge')
        shot(page,f'weekly-{width}')
        # Original day selector still sends exactly the original slot IDs.
        page.locator('[data-week-day-select]').first.uncheck()
        page.wait_for_timeout(100)
        check(page,"(()=>{let c=app.calls.filter(x=>x.type.endsWith('/week_select')).at(-1);return c?.data.slot_ids.length===3&&c.data.selected===false&&app._weekState.slots.filter(s=>!s.selected).length===3})()",prefix+'day checkbox preserves original selection route')
        # Unavailable records remain information-only within the same day container.
        page.evaluate("app._weekState.slots[0].recipe=null;app._renderTab()")
        check(page,"app.shadowRoot.querySelectorAll('.rx-week-day').length===7&&app.shadowRoot.querySelectorAll('[data-v202-recipe-gap]').length>=1&&!app.shadowRoot.querySelector('[data-v202-recipe-gap] [data-v66-action]')",prefix+'missing recipe retains day and non-actionable placeholder')
        # Per-view filters unchanged; styling itself does not write preferences.
        page.evaluate("app.show('today');app._filters().maxCost=2;app.show('official');app._filters().maxCost=8;app.show('today')")
        check(page,"app._filters().maxCost===2",prefix+'per-view filters stay independent')
        # More is native disclosure; its original button routes still run.
        card=page.locator('article.ui203-recipe').first
        page.evaluate("(()=>{const s=app.shadowRoot.querySelector('article.ui203-recipe details.ui203-more > summary').getBoundingClientRect();window.moreBefore={left:s.left,top:s.top,width:s.width}})()")
        card.locator('details.ui203-more > summary').click()
        check(page,"!!app.shadowRoot.querySelector('details.ui203-more[open]')&&!app._v63RecipeDialog",prefix+'More opens without opening recipe')
        check(page,"(()=>{const d=app.shadowRoot.querySelector('article.ui203-recipe details.ui203-more[open]'),s=d.querySelector(':scope > summary').getBoundingClientRect();return Math.abs(s.left-moreBefore.left)<2&&Math.abs(s.top-moreBefore.top)<2&&d.querySelector('.ui203-more-grid')?.parentElement===d&&getComputedStyle(d).borderTopStyle!=='none'})()",prefix+'More stays anchored and groups expanded actions inside itself')
        card.locator('[data-v66-action=list]').click()
        page.wait_for_timeout(80)
        check(page,"app.calls.some(x=>x.type.endsWith('book_toggle')&&x.data.collection==='recipeList')",prefix+'secondary action retains its binding')
        # New labels and positioning must never make a disabled action usable.
        page.evaluate("(()=>{let b=app.shadowRoot.querySelector('article.ui203-recipe [data-v66-action=send]');b.disabled=true;window.sendBefore=app.sendRequests||0;b.click()})()")
        check(page,"(app.sendRequests||0)===sendBefore",prefix+'disabled controls remain disabled')
        # Long title still readable, in place above image, not shrunk to 11px.
        page.evaluate("app._todayResults[0].title='Συνταγή με πολλά διαφορετικά λαχανικά και μυρωδικά — '+ 'Πολύμεγάλοόνομα'.repeat(5);app._renderTab()")
        check(page,"(()=>{let t=app.shadowRoot.querySelector('article.ui203-recipe h3');return t.scrollHeight<=t.clientHeight+2&&parseFloat(getComputedStyle(t).fontSize)>=14})()",prefix+'long Greek recipe title wraps without clipping')
        # Fullscreen routes are actual inherited methods, not stubbed renderers.
        page.locator('[data-v66-photo]').first.click()
        page.wait_for_function('app._v63RecipeDialog?.isConnected')
        page.wait_for_timeout(80)
        check(page,"app._v63RecipeDialog.querySelectorAll('.ui203-action-dock').length===1",prefix+'fullscreen shares action dock')
        full=page.locator('[data-recipe-dialog]')
        full.locator('details.ui203-more > summary').click()
        page.keyboard.press('Escape')
        check(page,"!!app._v63RecipeDialog?.isConnected&&!app._v63RecipeDialog.querySelector('details.ui203-more[open]')",prefix+'Escape closes More before fullscreen')
        page.locator('[data-modal-close]').click()
        page.evaluate("app.show('official');app.show('today')")
        page.wait_for_timeout(70)
        check(page,"!app._v63RecipeDialog?.isConnected&&app._v179TabState('today').openRecipe===null",prefix+'closed recipe stays closed after navigation')
        # Selected first and focus in actual filter dialog.
        assert page.evaluate('app._ingredientCatalog.length>0'), 'Fixture catalog unexpectedly cleared'
        page.evaluate("app._filters().ingredients=['k:carrot'];app._showFilter('ingredients')")
        page.wait_for_timeout(50)
        check(page,"(()=>{const d=app.shadowRoot.querySelector('[data-filter-dialog]');const boxes=[...d.querySelectorAll('input[data-list]')];return boxes.length>1&&boxes[0].checked})()",prefix+'selected filter remains first in redesigned dialog')
        shot(page,f'filters-{width}')
        page.locator('[data-filter-dialog] [data-close]').click()
        page.evaluate("app.show('profile')")
        # All kitchen subpages use their actual renderers and controls.
        for pane in ['food','places','integration','stock']:
            page.locator(f'[data-v78-pane={pane}]').click()
            check(page,f"app.shadowRoot.querySelector('[data-v78-section={pane}]').hidden===false",prefix+'kitchen '+pane+' still navigable')
        page.evaluate("""(()=>{const salt={key:'salt',name:'Αλάτι',unlimited:true,storageLocationId:'pantry',storage:'pantry'};app._houseIngredients=[...(app._houseIngredients||[]),salt];const entry=app._entry?.();if(entry?.profile)entry.profile.houseIngredients=app._houseIngredients;app._v78State={...(app._v78State||{}),houseIngredients:app._houseIngredients};app._syncEntryProfile?.();app._renderTab();})()""")
        page.locator('[data-v78-pane=places]').click()
        page.locator('[data-place="pantry"] [data-items]').click()
        check(page,"(()=>{const n=app.shadowRoot.querySelector('[data-place=pantry] .v218-unlimited-item');return n&&n.textContent.includes('Αλάτι')&&n.textContent.includes('Απεριόριστο')})()",prefix+'unlimited stock appears inside its defined storage place')
        page.evaluate("""(()=>{app._v116Scale=structuredClone(app._fixtureScale);app.shadowRoot.querySelector('[data-v218-scale-probe]')?.remove();const section=document.createElement('section');section.dataset.v78Section='scale';section.dataset.v218ScaleProbe='';app.shadowRoot.append(section);app._v116Card(section);})()""")
        page.wait_for_function("app.shadowRoot.querySelector('[data-v218-scale-probe] [data-v117-container] [data-v117-use]')")
        page.locator('[data-v218-scale-probe] [data-v117-container] [data-v117-use]').click()
        check(page,"app._v117ActiveContainerId==='jar-1'&&app.shadowRoot.querySelector('[data-v218-scale-probe] [data-v117-container] [data-v117-use]').textContent.includes('Ακύρωση χρήσης')",prefix+'container Use changes to Unuse when active')
        page.locator('[data-v218-scale-probe] [data-v117-container] [data-v117-use]').click()
        check(page,"app._v117ActiveContainerId===''&&app._v116SoftwareTare===0&&app.shadowRoot.querySelector('[data-v218-scale-probe] [data-v117-container] [data-v117-use]').textContent.includes('Χρήση')",prefix+'container Unuse restores unused state')
        page.evaluate("app.shadowRoot.querySelector('[data-v218-scale-probe]')?.remove()")
        check(page,"app.shadowRoot.querySelectorAll('[data-v218-unresolved]').length===1&&app.shadowRoot.querySelector('.v218-fallback-help')?.textContent.includes('προαιρετικός')",prefix+'nutrition fallback explains unresolved entries instead of implying broken catalog')
        page.locator('[data-v218-unresolved] [data-v218-retry]').click()
        page.wait_for_timeout(80)
        check(page,"app._nutritionSettings.blockedFailures===0&&app.shadowRoot.querySelectorAll('[data-v218-unresolved]').length===0",prefix+'unresolved nutrition can be retried immediately')
        shot(page,f'kitchen-{width}')
        # Manual form, validation, barcode lookup, save/discard with original code.
        page.evaluate("app._v78Open('manual')")
        page.wait_for_function('app._v78Dialog?.querySelector("[data-v196-save]")')
        check(page,"app._v78Dialog.classList.contains('ui203-form')",prefix+'manual editor uses full form surface')
        check(page,"(()=>{let f=app._v78Dialog.querySelector('[data-v196-actions]').getBoundingClientRect();return f.width<=innerWidth+1&&f.bottom<=innerHeight+1&&f.height>=44})()",prefix+'outside Save and Discard remain on screen')
        page.locator('[data-v196-save]').click()
        page.wait_for_timeout(70)
        check(page,"app.shadowRoot.activeElement?.dataset.draft==='quantity'&&app.shadowRoot.activeElement.getAttribute('aria-invalid')==='true'&&!app.calls.some(x=>x.type.endsWith('product_add'))",prefix+'Save blocks missing fields and focuses first error')
        page.locator('[data-v112-barcode-edit]').fill('01234567')
        page.locator('[data-v196-lookup]').click()
        page.wait_for_timeout(100)
        check(page,"app._v78Draft.productName==='Βιολογικό ρύζι'&&app._v78Draft.quantity===500",prefix+'manual barcode lookup still fills product')
        # Select a real suggestion button rather than assigning state directly.
        page.wait_for_function('app._v78Dialog.querySelector("[data-v194-index]")')
        page.locator('[data-v194-index]').first.click()
        page.locator('[data-v196-save]').click()
        page.wait_for_timeout(160)
        check(page,"app.calls.some(x=>x.type.endsWith('product_add'))&&app._v78Draft.productName===''&&app._v78Draft.quantity===''",prefix+'successful save opens fresh form')
        page.locator('main [data-draft=productName]').fill('Unsaved test')
        page.locator('[data-v196-discard]').click()
        check(page,"app._v78Draft.productName===''&&app.shadowRoot.activeElement?.dataset.draft==='productName'",prefix+'Discard resets and focuses form without deletion')
        shot(page,f'manual-{width}')
        # Existing package editing retains the optimistic target and never deletes.
        page.evaluate("app._v78Close(true);app._v112EditLot('lot-rice')")
        page.wait_for_function("app._v78Draft?.editLotId==='lot-rice'")
        check(page,"app._v78Draft.quantity===500&&app._v78Draft.expectedVersion==='fixture-revision'&&app._v78Dialog.classList.contains('ui203-form')",prefix+'existing package edit preserves target and version')
        page.locator('main [data-draft=productName]').fill('Edited rice')
        page.locator('[data-v196-discard]').click()
        check(page,"app._v78Draft.editLotId===''&&app._houseIngredients[0].lots[0].productName==='Ρύζι μπασμάτι'",prefix+'discarding edit leaves stored package unchanged')
        # HA light theme: inherited hardcoded camera whites must not leak into form.
        page.evaluate("document.body.classList.add('light');app._hass.themes.darkMode=false")
        page.wait_for_timeout(350)
        check(page,"(()=>{let n=app._v78Dialog.querySelector('main h2');let s=getComputedStyle(n);return s.color!=='rgb(255, 255, 255)'&&s.color!=='rgb(232, 238, 238)'})()",prefix+'light theme form title uses dark readable text')
        check(page,"""(()=>{const n=app._v78Dialog.querySelector('main [data-draft=productName]'),s=getComputedStyle(n),c=document.createElement('canvas');c.width=c.height=1;const x=c.getContext('2d');const l=color=>{x.fillStyle=color;x.fillRect(0,0,1,1);return [...x.getImageData(0,0,1,1).data].slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0)};const a=l(s.color),b=l(s.backgroundColor);return b>.6&&(Math.max(a,b)+.05)/(Math.min(a,b)+.05)>=4.5})()""",prefix+'light theme input has readable foreground/background contrast')
        shot(page,f'manual-light-{width}')
        # Rotation of the open form preserves its content and fixed footer.
        page.locator('main [data-draft=productName]').fill('Rotation preserved')
        page.set_viewport_size({'width':height,'height':width})
        page.wait_for_timeout(100)
        check(page,"app._v78Draft.productName==='Rotation preserved'&&app._v78Dialog.querySelector('[data-v196-actions]').getBoundingClientRect().bottom<=innerHeight+1",prefix+'rotation preserves form and actions')
        page.set_viewport_size({'width':width,'height':height})
        page.evaluate("app._v78Close(true);document.body.classList.remove('light');app._hass.themes.darkMode=true")
        # Actual pending-receipt review uses separate workflow, never manual reset.
        page.evaluate("app._v78Open('manual')")
        page.evaluate("app._r195SetReceipt({id:'r1',revision:1,currency:'EUR',merchant:'Example store',purchaseDate:'2026-09-23',items:[{id:'row-1',status:'pending',kind:'product',productName:'Ρύζι',quantity:500,unit:'g',packageCount:1,lineTotal:2,ingredientLinks:[]},{id:'row-2',status:'pending',kind:'product',productName:'Καρότο',quantity:750,unit:'g',packageCount:1,lineTotal:3,ingredientLinks:[]}]})")
        page.wait_for_timeout(80)
        check(page,"app._r195Session.receipt.items.length===2&&app._v78Dialog.querySelector('[data-v196-actions]').hidden",prefix+'receipt review keeps its separate controls')
        page.locator('[data-r195-next]').click()
        check(page,"app._v78Draft.productName==='Καρότο'",prefix+'receipt next item still works')
        shot(page,f'receipt-{width}')
        # No cropping regression or guide in receipt live view; stream start stub.
        page.evaluate("app._r195Session=null;app._v78Dirty=false;app._r195Start(true,false)")
        page.wait_for_timeout(70)
        check(page,"!app._v78Dialog.classList.contains('ui203-form')&&getComputedStyle(app._v78Dialog.querySelector('[data-v111-guide]')).display==='none'",prefix+'receipt live view remains unframed')
        page.evaluate("app._v78Close(true)")
        check(page,"!app._ui203FooterObserver&&!app._v202CameraWatch",prefix+'scanner observers disposed on close')
        # Exact data eligibility still enforced: visual layer cannot show unsafe data.
        page.evaluate("app._todayResults=[{...samples(0),match:{diet:'vegetarian',dietCheckVersion:76,safe:false}}];app.show('today')")
        check(page,"app.shadowRoot.querySelectorAll('article.ui203-recipe').length===0",prefix+'diet-ineligible recipes are not exposed by refresh')
        # HA hosts the panel inside other shadow roots. Escape must still be local.
        page.evaluate("(()=>{app.remove();const outer=document.createElement('section');document.body.append(outer);const r=outer.attachShadow({mode:'open'});const a=document.createElement('cook4me-ui-fixture-v203');r.append(a);window.app=a;a.seed();a.show('today')})()")
        page.locator('[data-v66-photo]').first.click()
        page.wait_for_function('app._v63RecipeDialog?.isConnected')
        page.locator('[data-recipe-dialog] details.ui203-more > summary').click()
        page.keyboard.press('Escape')
        check(page,"app._v63RecipeDialog?.isConnected&&!app._v63RecipeDialog.querySelector('details.ui203-more[open]')",prefix+'More keyboard dismissal works inside nested HA shadow roots')
        # Same live controls survive idempotent decoration, and no mutation storm.
        page.evaluate("window.uiNodes=[...app.shadowRoot.querySelectorAll('#tabs button')];window.mutations=0;window.uiObserver=new MutationObserver(ms=>window.mutations+=ms.length);uiObserver.observe(app.shadowRoot,{subtree:true,childList:true});for(let i=0;i<20;i++)app._ui203Page()")
        page.wait_for_timeout(100)
        check(page,"window.mutations<5&&uiNodes.every((n,i)=>n===app.shadowRoot.querySelectorAll('#tabs button')[i])",prefix+'idempotent decoration preserves nodes without observer loop')
        page.evaluate('uiObserver.disconnect()')
        assert not errors,(prefix,errors)
        page.close()
    browser.close()
print(f'PASS: {len(results)} full-frontend browser checks')
