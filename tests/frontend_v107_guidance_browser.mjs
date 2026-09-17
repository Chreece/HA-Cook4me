import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
const root=fileURLToPath(new URL('..',import.meta.url));
const recipe=JSON.parse(execFileSync('python3',['-c',`import sys,json;sys.path.insert(0,'tests');from test_recipe_logic import logic
r={'title':'Ingredient replacements','source':'official','displayVariantId':'official-one','sendVariantId':'official-one','groupingFunctionalId':'original-group','recipeFunctionalId':'official-one','language':'en','servings':2,'ingredients':[{'name':'Duck breast','displayName':'Duck breast','quantity':200,'unit':'g'},{'name':'Gelatin','quantity':10,'unit':'g'},{'name':'Rice','quantity':100,'unit':'g'}],'steps':[{'instruction':'Prepare the ingredients.'},{'instruction':'Follow the original cooking program.'}]}
r['match']=logic.score_recipe(r,{'diet':'vegetarian'});print(json.dumps(r))`],{cwd:root}));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage({viewport:{width:1360,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><style>body{margin:0;font-family:Arial;--primary-color:#009bbb;--primary-text-color:#eee;--primary-background-color:#111;--card-background-color:#1e2223;--secondary-background-color:#222;--secondary-text-color:#aaa;--divider-color:#444}</style><body></body>'}));
 await page.goto('http://cook4me.test/');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v107-bundle.js'});
 await page.evaluate(recipe=>{
  window.recipe=recipe;window.before=JSON.stringify(recipe);window.calls=[];
  globalThis.customElements.define('cook4me-v107-test',class extends globalThis.customElements.get('cook4me-recipe-hub-panel-v107'){connectedCallback(){} disconnectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v107-test');
  p._hass={language:'el',user:{id:'alice'},states:{},config:{country:'DE'},connection:{sendMessagePromise:async()=>({}),subscribeMessage:async()=>()=>{},addEventListener(){},removeEventListener(){}}};
  for(const method of ['_restorePreferences','_loadOverview','_requestSection','_loadRecipeNutrition','_loadIngredientCatalog','_loadTodayOptions'])p[method]=async()=>{};
  p._v84SchedulePricePoll=()=>{};p._v86QueuePreview=()=>{};p._v79LoadCost=async()=>{};p._v66PreferLanguages=async rows=>rows;
  p._api=async(type,data)=>{calls.push({type,data});if(type.endsWith('/recipe_detail'))return structuredClone(recipe);if(type.endsWith('/send_multi'))return {sentCount:1};return {};};
  p._entryId='one';p._entries=[{entry_id:'one',title:'Cook4Me',connected:true,profile:{diet:'vegetarian',houseIngredients:[]}}];p._tab='book';
  p._v63FilterKey=p._prefKey();p._v63Filters={diet:'vegetarian',languages:[],mealTypes:[],ingredients:[]};
  p._bookState={favorites:[recipe],recipeList:[]};p._renderShell();document.body.append(p);p._renderTab();
  window.openRecipe=()=>{p._opened=recipe;p._v63RecipeDialog=document.createElement('div');p._v63RecipeDialog.className='rx-v63-recipe-overlay';p.shadowRoot.append(p._v63RecipeDialog);p._renderRecipeDialog();};
 },recipe);
 const p=page.locator('cook4me-v107-test');
 // A saved selection remains sendable even when replacements are incomplete.
 assert.equal(await page.evaluate(()=>panel._v77CanSend(recipe)),true);
 const filter=await page.evaluate(()=>{panel._tab='official';const hidden=panel._recipeCard(recipe);panel._tab='book';return hidden;});assert.equal(filter,'');
 await page.evaluate(()=>openRecipe());
 for(const language of ['el','de','en']){
  await page.evaluate(language=>{panel._hass.language=language;panel._v66State(recipe).cooking=false;panel._v66State(recipe).step=0;panel._v66State(recipe).sections.add('ingredients');panel._renderRecipeDialog();},language);
  const full=p.locator('[data-v66-fullscreen]');
  assert.equal(await full.locator('[data-v66-action="send"]').isEnabled(),true);
  assert.equal(await full.locator('[data-v107-original]').count(),2);
  assert.equal(await full.locator('[data-v66-ingredient="2"] s').count(),0);
  assert.equal(await full.locator('[data-v107-original] .rx-v66-quantity,[data-v107-original] [data-v79-item]').count(),0);
  const label=await page.evaluate(()=>panel._v76Text('tofu')),choose=await page.evaluate(()=>panel._v107Text('choose'));
  assert.equal(await full.locator('[data-v107-replacement="0"]').innerText(),'→ '+label);
  assert.equal(await full.locator('[data-v107-replacement="1"]').innerText(),'→ '+choose);
  await full.locator('[data-v66-action="cook"]').click();
  const note=full.locator('[data-v66-section="steps"] [data-v107-changes]');await note.waitFor({state:'visible'});
  assert.equal(await note.locator('s').count(),2);assert.ok((await note.innerText()).includes(label));
  assert.equal(await full.locator('[data-v66-step="0"]').getAttribute('aria-current'),'step');
  await full.locator('[data-v66-action="next"]').click();
  assert.equal(await full.locator('[data-v66-step="1"]').getAttribute('aria-current'),'step');
  assert.equal(await full.locator('[data-v76-substitutions]').count(),0);
  for(const width of [390,1360]){
   await page.setViewportSize({width,height:1000});
   assert.equal(await note.evaluate(n=>n.scrollWidth<=n.clientWidth+1),true);
   if(language==='el'&&process.env.COOK4ME_SCREENSHOT_DIR)await note.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+`/v107-cooking-${width}.png`});
  }
 }
 const state=await page.evaluate(()=>({same:JSON.stringify(recipe)===before,custom:panel._v67Dom(panel._v66Body(recipe,true,{sections:new Set()})).querySelector('[data-v66-action="send"]').disabled}));
 assert.equal(state.same,true);assert.equal(state.custom,true);
 await p.locator('[data-v66-fullscreen] [data-v66-action="send"]').click();await page.waitForFunction(()=>calls.some(r=>r.type.endsWith('/send_multi')));
 const sent=await page.evaluate(()=>calls.find(r=>r.type.endsWith('/send_multi')).data.recipe);
 assert.deepEqual(sent.ingredients,recipe.ingredients);assert.deepEqual(sent.steps,recipe.steps);assert.equal(sent.recipeFunctionalId,'official-one');
 assert.deepEqual(errors,[]);
 console.log('v107: dietary filter retained; unrestricted official Send, real cooking toggle and step navigation, struck names only, localized replacements and unresolved guidance, original ingredients/program retained, and mobile/desktop layout passed');
}finally{await browser.close();}
