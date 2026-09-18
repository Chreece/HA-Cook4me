import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const build=process.env.COOK4ME_TEST_BUILD||'104';
const mint=JSON.parse(readFileSync(root+'/docs/price-fixes-v104-preview.json','utf8'));
const fixture=[...JSON.parse(readFileSync(root+'/docs/price-confidence-v99-preview.json','utf8')),mint];
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><body style="margin:0;font:16px Arial;--primary-color:#397b58;--card-background-color:#fff;--primary-background-color:#f5f7f5;--primary-text-color:#183526;--secondary-text-color:#596f63;--divider-color:#d7dfd9;--secondary-background-color:#edf2ee"></body>'}));
 await page.goto('http://cook4me.test/');await page.addScriptTag({path:root+`/custom_components/cook4me/frontend/cook4me-panel-v${build}-bundle.js`});
 await page.evaluate(({fixture,build})=>{
  window.fixture=fixture;
  globalThis.customElements.define('cook4me-v104-test',class extends globalThis.customElements.get(`cook4me-recipe-hub-panel-v${build}`){connectedCallback(){} disconnectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v104-test');
  p._hass={language:'en',user:{id:'alice'},states:{},config:{country:'DE',time_zone:'Europe/Berlin'},connection:{sendMessagePromise:async()=>({}),subscribeMessage:async()=>()=>{},addEventListener(){},removeEventListener(){}}};
  for(const method of ['_restorePreferences','_loadOverview','_requestSection','_loadRecipeNutrition','_loadIngredientCatalog','_loadTodayOptions'])p[method]=async()=>{};
  p._v84SchedulePricePoll=()=>{};p._v86QueuePreview=()=>{};p._v66PreferLanguages=async rows=>rows;
  p._api=async(type,data={})=>{
   window.calls??=[];calls.push({type,data});
   if(type.endsWith('/recipe_detail'))return fixture.at(-1).recipe;
   if(type.endsWith('/ingredient_info'))return {ingredientInfoContract:'offline-ingredient-info-v62',ingredient:{name:'Carrot'},stock:{},history:[],savedRecipeUsage:[],officialRecipeUsage:[]};
   if(type.endsWith('/recipe_cost_refresh')){await new Promise(resolve=>window.finishRefresh=resolve);return {costs:[fixture.at(-1).cost]};}
   if(type.endsWith('/recipe_cost'))return fixture.at(-1).cost;
   if(type.endsWith('/price_settings'))return {priceCacheToken:'test-v104'};
   return {};
  };
  p._entryId='one';p._entries=[{entry_id:'one',title:'Kitchen Cook4Me',connected:true,state:{phase:'idle'},profile:{diet:'omnivore',houseIngredients:[]}}];p._tab='today';
  p._v63FilterKey=p._prefKey();p._v63Filters={diet:'omnivore',ingredients:[],languages:[],mealTypes:[],onlyHome:false,avoidRecentDays:7,maxMissing:'',nutritionGoal:'balanced',maxCost:'',excludedIngredients:[],excludedTerms:[]};
  p._todayResults=fixture.map(row=>row.recipe);p._renderShell();document.body.append(p);
  window.render=()=>{
   for(const {recipe,cost} of fixture){recipe.cost=cost;Object.assign(p._v79CostState(recipe),{cost,loading:false});}
   p._renderTab();
  };render();
 },{fixture,build});
 const p=page.locator('cook4me-v104-test');
 for(const language of ['en','de','el']){
  for(const width of [360,390,1600]){
   await page.setViewportSize({width,height:1000});await page.evaluate(language=>{panel._hass.language=language;render();},language);
   const badges=p.locator('#todayGrid [data-v82-card-cost]');
   assert.equal(await badges.count(),fixture.length);
   for(const text of await badges.allTextContents())assert.doesNotMatch(text,/\p{L}/u);
   assert.equal(await p.locator('#todayGrid').evaluate(grid=>grid.scrollWidth<=grid.clientWidth+1),true);
   const colours=await badges.evaluateAll(nodes=>nodes.map(node=>getComputedStyle(node).backgroundColor));
   assert.equal(new Set(colours.slice(0,5)).size,5);
  }
 }
 // Loading and failure retain accessible, icon-only controls and retry behavior.
 await page.evaluate(()=>{const row=fixture[0],state=panel._v79CostState(row.recipe);state.cost=null;state.loading=true;panel._v82PaintCard(row.recipe);});
 assert.equal(await p.locator('#todayGrid [data-v82-card-cost]').first().innerText(),'');
 await page.evaluate(()=>{const row=fixture[0],state=panel._v79CostState(row.recipe);state.loading=false;state.v90Failed=true;panel._v82PaintCard(row.recipe);});
 assert.equal(await p.locator('[data-v90-retry]').innerText(),'');
 await page.evaluate(()=>{window.retried=false;panel._v86QueuePreview=()=>window.retried=true;});
 await p.locator('[data-v90-retry]').click();assert.equal(await page.evaluate(()=>retried),true);
 await page.evaluate(()=>render());
 for(const width of [390,1600]){
  await page.setViewportSize({width,height:1000});
  await page.evaluate(async()=>{await panel._showRecipe(fixture.at(-1).recipe);});
  const full=p.locator('[data-v66-fullscreen]'),overview=full.locator('.v104-price-overview');
  await overview.locator('[data-v104-total]').filter({hasText:'2,12'}).waitFor();
  assert.equal(await full.locator('header [data-v82-refresh-prices]').count(),0);
  assert.equal(await full.locator('[data-v79-recost]').count(),1);
  assert.equal(await full.locator('[data-v79-recost] ha-icon').getAttribute('icon'),'mdi:cash-sync');
  assert.doesNotMatch(await overview.innerText(),/\p{L}/u);
  const layout=await overview.evaluate(node=>{
   const amount=node.querySelector('[data-v104-total]').getBoundingClientRect(),refresh=node.querySelector('[data-v79-recost]').getBoundingClientRect();
   return {aligned:Math.abs((amount.top+amount.bottom)-(refresh.top+refresh.bottom))<2,next:refresh.left>=amount.right&&refresh.left-amount.right<12,inside:node.scrollWidth<=node.clientWidth+1};
  });assert.ok(layout.aligned&&layout.next&&layout.inside,JSON.stringify(layout));
  await overview.locator('.v104-price-info>summary').click();
  assert.ok((await overview.innerText()).length>100);
  await overview.locator('.v79-evidence>summary').click();
  assert.ok(await overview.locator('a').count()>0);
  await overview.locator('.v104-price-info>summary').click();
  // Exercise the real refresh path, including its busy state and a second click.
  const previous=await page.evaluate(()=>calls.filter(row=>row.type.endsWith('/recipe_cost_refresh')).length);
  await overview.locator('[data-v79-recost]').click();
  await page.waitForFunction(()=>typeof window.finishRefresh==='function');
  assert.equal(await overview.locator('[data-v79-recost]').isDisabled(),true);
  const request=await page.evaluate(()=>calls.filter(row=>row.type.endsWith('/recipe_cost_refresh')).at(-1));
  assert.equal(request.data.recipes.length,1);
  await page.evaluate(()=>{finishRefresh();window.finishRefresh=null;});
  await page.waitForFunction(()=>!panel._v82Refresh);
  assert.equal(await page.evaluate(()=>calls.filter(row=>row.type.endsWith('/recipe_cost_refresh')).length),previous+1);
  assert.equal(await overview.locator('[data-v79-recost]').isEnabled(),true);
  assert.doesNotMatch(await overview.innerText(),/\p{L}/u);
  if(process.env.COOK4ME_SCREENSHOT_DIR)await overview.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+`/v104-price-${width}.png`});
  // Open the real ingredient control, verify hit-testing, keyboard focus and close.
  if(!await full.locator('[data-v66-section="ingredients"]').evaluate(node=>node.open))await full.locator('[data-v66-section="ingredients"]>summary').click();
  const ingredient=full.locator('[data-v66-ingredient]').first();
  await ingredient.click();
  const popup=p.locator('[data-ingredient-dialog]');await popup.waitFor();
  assert.equal(await full.evaluate(node=>node.inert),true);
  const stacking=await popup.evaluate(node=>{
   const box=node.querySelector('.rx-dialog').getBoundingClientRect();
   const target=node.getRootNode().elementFromPoint(box.left+20,box.top+20);
   return node.contains(target)&&Number(getComputedStyle(node).zIndex)>Number(getComputedStyle(node.getRootNode().querySelector('[data-v66-fullscreen]')).zIndex);
  });assert.ok(stacking);
  if(process.env.COOK4ME_SCREENSHOT_DIR)await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+`/v104-ingredient-${width}.png`});
  await popup.locator('[data-close]').focus();await page.keyboard.press('Shift+Tab');
  assert.equal(await p.evaluate(node=>node.shadowRoot.activeElement.closest('[data-ingredient-dialog]')!==null),true);
  await page.keyboard.press('Escape');await popup.waitFor({state:'detached'});
  assert.equal(await full.count(),1);assert.equal(await full.evaluate(node=>node.inert),false);
  assert.equal(await ingredient.evaluate(node=>node.getRootNode().activeElement===node),true);
  await ingredient.click();await popup.waitFor();await popup.locator('[data-close]').click();
  assert.equal(await ingredient.evaluate(node=>node.getRootNode().activeElement===node),true);
  if(process.env.COOK4ME_SCREENSHOT_DIR)await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+`/v104-fullscreen-${width}.png`});
  await full.locator('[data-modal-close]').click();
 }
 assert.equal(await p.locator('#v82RefreshPrices ha-icon').getAttribute('icon'),'mdi:cash-sync');
 assert.deepEqual(errors,[]);
 console.log('v104: translated icon-only prices at 360/390/1600 px, confidence colours, evidence access, real scoped refresh, foreground ingredient dialog, focus trapping/restoration and card retry passed');
}finally{await browser.close();}
