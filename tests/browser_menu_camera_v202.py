"""Real browser interaction/layout tests, with inherited HA/API boundaries controlled."""
from pathlib import Path
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import re
import shutil
from threading import Thread
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
css=''
for version in [78,111,112]:
    text=(ROOT/f'custom_components/cook4me/frontend/cook4me-panel-v{version}.js').read_text()
    css+='\n'+text.split('style.textContent=`',1)[1].split('`;',1)[0]
results=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=shutil.which('chromium') or None,args=['--no-sandbox'])
  for viewport in [{'width':390,'height':844},{'width':844,'height':390}]:
   page=browser.new_page(viewport=viewport);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   html=(ROOT/'tests/menu_camera_fixture_v202.html').read_text()
   for symbol,filename in [('SelectedFilterMixin','filter-selection-v202.js'),('RecipeGapsMixin','recipe-gaps-v202.js'),('ScannerCameraMixin','scanner-camera-v202.js')]:
    source=(ROOT/'custom_components/cook4me/frontend'/filename).read_text().replace('export ','')
    html=html.replace("import {"+symbol+"} from '../custom_components/cook4me/frontend/"+filename+"';",source)
   page.set_content(html);page.wait_for_function('window.ready')
   page.evaluate('(css)=>window.legacyCSS=css',css);page.evaluate('setup()')
   run=page.evaluate
   run("panel._showFilter('ingredients')")
   assert run("[...panel.shadowRoot.querySelectorAll('[data-list]')].map(n=>n.value)")==['B','A','C','D']
   page.locator('[data-list][value=C]').check()
   assert run("[...panel.shadowRoot.querySelectorAll('[data-list]')].map(n=>n.value)")==['B','C','A','D']
   assert run("panel.shadowRoot.activeElement.value")=='C'
   results.append('selected items first with stable order and retained focus')
   page.locator('[data-ingredient-search]').fill('D')
   assert page.locator('label:visible').count()==3
   page.locator('[data-list][value=B]').uncheck();assert page.locator('[data-list][value=B]').is_visible() is False
   assert page.locator('[data-list][value=C]').is_visible()
   page.locator('[data-apply]').click();assert run('panel.saved')==1
   results.append('search preserves selected rows; deselection and original Apply listener work')
   run("panel._tab='today';panel._showFilter('ingredients')")
   assert run("panel.shadowRoot.querySelector('[data-list]').value")=='C'
   run("panel._tab='week';panel._showFilter('ingredients')")
   assert run('panel.viewFilters.week')==['C'];results.append('sorting leaves independent view selections intact')
   run("panel.shadowRoot.querySelector('[data-filter-dialog]').remove();panel._v78Draft={mode:'receipt',editorOpen:false,requestId:'keep',ingredientLinks:['rice'],nutrition:{values:{protein:7}}};panel._v78RenderCapture()")
   page.wait_for_timeout(80)
   assert run("panel._v78Dialog.querySelector('[data-v80-scan=receipt] ha-icon').getAttribute('icon')")=='mdi:receipt-text-outline'
   assert not page.locator('[data-v111-guide]').is_visible()
   assert run("getComputedStyle(panel._v78Dialog.querySelector('video')).objectFit")=='contain'
   results.append('receipt icon corrected and guide/mask removed with uncropped preview')
   assert run('panel._v111Canvas().crop') is False
   results.append('receipt capture uses the entire source image')
   dimensions=run("(()=>{const f=panel._v78Dialog.querySelector('[data-v111-frame]').getBoundingClientRect();return {top:f.top,bottom:f.bottom,height:f.height}})()")
   assert dimensions['bottom']<=viewport['height']+1,dimensions
   assert dimensions['height']<viewport['height'],dimensions
   take=page.locator('[data-v78-take]').bounding_box();assert take['y']+take['height']<=viewport['height']
   results.append('preview and capture controls fit actual inherited portrait/landscape CSS')
   page.set_viewport_size({'width':viewport['height'],'height':viewport['width']});page.wait_for_timeout(100)
   assert run("panel._v78Dialog.classList.contains('v202-camera-landscape')")==(viewport['height']>viewport['width'])
   assert run('panel._v78Draft.requestId')=='keep';assert run('panel._v78Draft.ingredientLinks')==['rice']
   assert run('panel.cameraStarts')==0;assert run('panel.cameraStops')==0
   results.append('rotating the existing preview preserves draft and stream without reopening')
   run("Object.defineProperty(panel._v78Dialog.querySelector('video'),'videoWidth',{value:1080,configurable:true});Object.defineProperty(panel._v78Dialog.querySelector('video'),'videoHeight',{value:1920,configurable:true});panel._v78Dialog.querySelector('video').dispatchEvent(new Event('resize'))")
   page.wait_for_timeout(80);assert float(run("panel._v78Dialog.style.getPropertyValue('--v202-video-ratio')"))==1080/1920
   results.append('video intrinsic resize updates the layout independently of viewport events')
   run("panel._v78Draft.mode='barcode';panel._v111Paint()")
   assert page.locator('[data-v111-guide]').is_visible();assert run('panel._v111Canvas().crop') is True
   results.append('switching back restores barcode guide and original crop semantics')
   run("panel._v78Close(true)");assert run('panel._v202CameraWatch') is None
   results.append('closing scanner disposes observers and rotation listeners')
   run("panel._weekState={slots:[{id:'ok',date:'2026-09-23',mealType:'lunch',recipe:{title:'Loaded recipe'}}],unavailableSlots:[{id:'bad',date:'2026-09-23',mealType:'breakfast',reason:'processing_error'}],expectedMealSlots:[{date:'2026-09-23',mealType:'breakfast'},{date:'2026-09-23',mealType:'lunch'},{date:'2026-09-23',mealType:'dinner'}]};const c=document.createElement('div');c.id='results';panel.shadowRoot.append(c);panel._renderWeek(c)")
   assert page.locator('[data-v202-week-gap]').count()==2
   assert page.locator('[data-slot-id]').count()==1
   assert run("[...panel.shadowRoot.querySelector('[data-week-date]').children].filter(n=>n.matches('div,section')).map(n=>n.dataset.v202MealType||'lunch')")==['breakfast','lunch','dinner']
   assert page.locator('[data-v202-recipe-gap] button').count()==0
   results.append('missing weekly positions remain in order, with no fake actionable recipes')
   run("panel._todayResults=[{title:'Loaded',todayMealType:'lunch'}];panel._todayMeta={emptyMealTypes:['dinner']};panel._renderToday(panel.shadowRoot.querySelector('#results'))")
   assert page.locator('[data-v202-day-gap=dinner]').count()==1
   assert page.locator('[data-v202-recipe-gap=no_match]').count()==1
   results.append('daily missing categories show individual explanatory slots')
   run("panel._todayResults=[{title:'Loaded'},{title:'Broken',broken:true},{title:'Third'}];panel._todayMeta={};panel._renderToday(panel.shadowRoot.querySelector('#results'))")
   assert page.locator('#todayGrid article').count()==3
   assert page.locator('[data-v202-recipe-gap=processing_error]').count()==1
   assert 'private' not in page.locator('#todayGrid').inner_text()
   results.append('single card parse failure leaves siblings and an explained hole')
   assert not errors,errors
   page.close()
  browser.close()
finally:pass
for i,result in enumerate(results,1):print(f'{i}. {result}')
print(f'PASS: {len(results)} browser scenario groups')
