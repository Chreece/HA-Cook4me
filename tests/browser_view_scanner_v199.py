"""Browser regressions of production state/scanner mixins with controlled HA boundaries."""
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('chromium') or None,args=['--no-sandbox'])
 for width,height in [(390,844),(1366,900)]:
  page=browser.new_page(viewport={'width':width,'height':height});errors=[]
  page.set_default_timeout(4000)
  page.on('pageerror',lambda e: (errors.append(str(e)),print('BROWSER ERROR:',e,flush=True)))
  html=(ROOT/'tests/view_scanner_fixture_v199.html').read_text()
  frontend=ROOT/'custom_components/cook4me/frontend'
  html=html.replace("await import('../custom_components/cook4me/frontend/cook4me-panel-v179.js');",(frontend/'cook4me-panel-v179.js').read_text())
  for symbol,filename in [('ViewFiltersMixin','view-filters-v199.js'),('ReceiptScannerMixin','scanner-receipts-v195.js'),('ReceiptLauncherMixin','receipt-launcher-v199.js')]:
   html=html.replace("const {"+symbol+"}=await import('../custom_components/cook4me/frontend/"+filename+"');",(frontend/filename).read_text().replace('export ',''))
  html=html.replace('<script type="module">','<script type="module">\nconst browserStorage=new Map();Object.defineProperty(window,"localStorage",{value:{getItem:k=>browserStorage.get(k)||null,setItem:(k,v)=>browserStorage.set(k,v),clear:()=>browserStorage.clear()}});')
  page.set_content(html);page.wait_for_function('window.ready')
  def fresh():
   page.evaluate('makeView()');page.wait_for_timeout(30)
  def run(script):return page.evaluate(script)
  fresh();run("view._showRecipe({id:'rice',title:'Rice'})")
  run("view._renderRecipeDialog();view._renderRecipeDialog()")
  page.locator('[data-modal-close] span').click();run('view._renderTab()');page.wait_for_timeout(40)
  assert page.locator('[data-recipe-dialog]').count()==0
  assert run("view._v179TabState('today').openRecipe") is None
  results.append(f'{width}: replaced X button clears fullscreen state and redraw does not reopen')
  run("view._showRecipe({id:'rice',title:'Rice'})");page.keyboard.press('Escape');run("view._selectV52Tab('week');view._selectV52Tab('today')");page.wait_for_timeout(40)
  assert page.locator('[data-recipe-dialog]').count()==0
  results.append(f'{width}: Escape clears state across view changes')
  run("view._showRecipe({id:'rice',title:'Rice'})");run("view._showFilter('cost')");page.keyboard.press('Escape')
  assert run("view._v179TabState('today').openRecipe.token")=='rice'
  assert page.locator('[data-recipe-dialog]').count()==1
  results.append(f'{width}: nested filter Escape preserves genuinely open recipe')
  run("view._selectV52Tab('week')");page.wait_for_timeout(40);assert page.locator('[data-recipe-dialog]').count()==0
  run("view._selectV52Tab('today')");page.wait_for_function('view._v63RecipeDialog?.isConnected')
  results.append(f'{width}: genuinely open recipe restored only in its owning view')
  run("view._showFilter('cost')");page.locator('[data-apply]').click();page.wait_for_timeout(40)
  assert page.locator('[data-recipe-dialog]').count()==0
  results.append(f'{width}: changing filters cancels prior recipe restoration')
  fresh();run("view._v179StoreOpenRecipe({id:'a',title:'A'});view._v179RestoreRecipe();view._v179ClearOpenRecipe()")
  page.wait_for_timeout(40);assert run('view.calls.length')==0
  results.append(f'{width}: queued recipe restoration cancelled by close')
  fresh();run("view._v179StoreOpenRecipe({id:'a',title:'A'});view._v179RestoreRecipe();view._selectV52Tab('week')")
  page.wait_for_timeout(40);assert page.locator('[data-recipe-dialog]').count()==0
  results.append(f'{width}: queued restoration cannot leak across views')
  fresh();run("view.closeImmediately=true;view._showRecipe({id:'a',title:'A'})");page.wait_for_timeout(40)
  assert run('view._v179TabState().openRecipe') is None
  results.append(f'{width}: close before open continuation cannot persist a stale recipe')
  fresh();run("view._filters().maxCost=2;view._selectV52Tab('week');view._filters().maxCost=8;view._cachePreferences();view._selectV52Tab('today')")
  assert run('view._filters().maxCost')==2
  results.append(f'{width}: independent view filters on browser navigation')
  run('makeScanner()');assert page.locator('[data-r199-receipt-photo]').count()==1
  assert run("scanner.shadowRoot.querySelector('[data-v78-open]').nextElementSibling.matches('[data-r199-receipt-photo]')")
  results.append(f'{width}: receipt photo sits next to Add product with image AI')
  run("scanner._v78State.aiChoices=[];scanner._r199Launch()")
  assert page.locator('[data-r199-receipt-photo]').count()==0
  run("scanner._v78State.aiChoices=[{id:'ai_task.vision'}];scanner._r199Launch();scanner._v78Open('manual')")
  assert page.locator('[data-r195-saved],[data-r195-upload],[data-r195-start]').count()==0
  assert run("scanner._v78Dialog.querySelector('[data-v80-scan=nutrition]').nextElementSibling.dataset.v80Scan")=='receipt'
  assert page.locator('[data-r195-tools]').count()==0
  results.append(f'{width}: product editor has no receipt shortcuts; camera receipt follows nutrients')
  page.locator('[data-r199-receipt-file]').set_input_files({'name':'receipt.jpg','mimeType':'image/jpeg','buffer':b'fixture decoded by controlled boundary'})
  page.wait_for_function('scanner._r195Session?.receipt?.items.length===1')
  assert run("scanner.calls.some(c=>c[0]==='camera')") is False
  assert run("scanner.calls.some(c=>c[0]==='cook4me/receipts/recognize')") is True
  assert page.locator('[data-r195-review]').count()==1
  assert page.locator('[data-r195-saved],[data-r195-upload],[data-r195-start]').count()==0
  results.append(f'{width}: saved-device photo reaches receipt review without camera activation')
  assert not errors,errors
  page.close()
 browser.close()
print('\n'.join(results));print(f'PASS: {len(results)} browser scenario groups')
