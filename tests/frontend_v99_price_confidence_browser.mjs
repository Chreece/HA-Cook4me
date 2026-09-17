import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const fixture=JSON.parse(readFileSync(root+'/docs/price-confidence-v99-preview.json','utf8'));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><body style="margin:0;font:16px Arial;--primary-color:#397b58;--card-background-color:#fff;--primary-background-color:#f5f7f5;--primary-text-color:#183526;--secondary-text-color:#596f63;--divider-color:#d7dfd9;--secondary-background-color:#edf2ee"></body>'}));
 await page.goto('http://cook4me.test/');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v99-bundle.js'});
 await page.evaluate(fixture=>{
  window.fixture=fixture;
  globalThis.customElements.define('cook4me-v99-test',class extends globalThis.customElements.get('cook4me-recipe-hub-panel-v99'){connectedCallback(){} disconnectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v99-test');
  p._hass={language:'en',user:{id:'alice'},states:{},config:{country:'DE',time_zone:'Europe/Berlin'},connection:{sendMessagePromise:async()=>({}),subscribeMessage:async()=>()=>{},addEventListener(){},removeEventListener(){}}};
  for(const method of ['_restorePreferences','_loadOverview','_requestSection','_loadRecipeNutrition','_loadIngredientCatalog','_loadTodayOptions'])p[method]=async()=>{};
  p._v84SchedulePricePoll=()=>{};p._v86QueuePreview=()=>{};p._v66PreferLanguages=async rows=>rows;
  p._entryId='one';p._entries=[{entry_id:'one',title:'Kitchen Cook4Me',connected:true,state:{phase:'idle'},profile:{diet:'omnivore',houseIngredients:[]}}];p._tab='today';
  p._v63FilterKey=p._prefKey();p._v63Filters={diet:'omnivore',ingredients:[],languages:[],mealTypes:[],onlyHome:false,avoidRecentDays:7,maxMissing:'',nutritionGoal:'balanced',maxCost:'',excludedIngredients:[],excludedTerms:[]};
  p._todayResults=fixture.map(row=>row.recipe);p._renderShell();document.body.append(p);
  window.render=()=>{
   for(const {recipe,cost} of fixture){recipe.cost=cost;Object.assign(p._v79CostState(recipe),{cost,loading:false});}
   p._renderTab();
  };render();
 },fixture);
 const p=page.locator('cook4me-v99-test');
 assert.equal(await p.locator('#todayGrid [data-v66-ref]').count(),fixture.length);
 const levels=await p.locator('#todayGrid [data-v99-confidence]').evaluateAll(nodes=>nodes.map(node=>node.dataset.v99Confidence));
 assert.deepEqual(levels,fixture.map(row=>row.cost.priceConfidence));
 const colours=await p.locator('#todayGrid [data-v99-confidence]').evaluateAll(nodes=>nodes.map(node=>getComputedStyle(node).backgroundColor));
 assert.equal(new Set(colours.slice(0,5)).size,5);
 for(const language of ['en','de','el']){
  for(const width of [360,390,1600]){
   await page.setViewportSize({width,height:1000});await page.evaluate(language=>{panel._hass.language=language;render();},language);
   const positions=await p.locator('#todayGrid [data-v66-ref]').evaluateAll(cards=>cards.map(card=>{
    const media=card.querySelector('.rx-v69-media').getBoundingClientRect(),node=card.querySelector('[data-v82-card-cost]'),badge=node.getBoundingClientRect(),diet=card.querySelector('[data-v76-diet-badge]')?.getBoundingClientRect();
    return {left:badge.left-media.left,top:badge.top-media.top,inside:badge.right<=media.right,overlap:!!diet&&badge.bottom>diet.top,title:node.title,aria:node.getAttribute('aria-label')};
   }));
   for(const pos of positions){assert.ok(Math.abs(pos.left-10)<1&&Math.abs(pos.top-10)<1,JSON.stringify(pos));assert.ok(pos.inside&&!pos.overlap);assert.ok(pos.title&&pos.aria);}
   assert.equal(await p.locator('#todayGrid').evaluate(grid=>grid.scrollWidth<=grid.clientWidth+1),true);
  }
  await page.evaluate(()=>{
   panel.shadowRoot.querySelector('#v99-details')?.remove();
   const row=fixture.find(row=>row.key==='assumed'),box=document.createElement('section');box.id='v99-details';box.innerHTML=panel._v79CostHtml(row.recipe,{cost:row.cost});panel.shadowRoot.append(box);
   const list=document.createElement('div');list.id='v99-items';list.innerHTML=row.recipe.ingredients.map((_,index)=>`<small data-v79-item="${index}"></small>`).join('');box.append(list);
   list.querySelectorAll('[data-v79-item]').forEach(node=>panel._v79PaintItem(node,{cost:row.cost}));
  });
  assert.equal(await p.locator('#v99-details [data-v86-missing]').count(),0);
  assert.equal(await p.locator('#v99-details [data-v99-zero-note]').count(),1);
  assert.equal(await p.locator('#v99-details .v79-evidence>[data-v99-zero]').count(),3);
  assert.equal(await p.locator('#v99-items [data-v99-zero]').count(),3);
  for(const text of await p.locator('#v99-items [data-v99-zero]').allTextContents())assert.match(text,/0[,.]00/);
  assert.equal(await p.locator('#v99-details .v79-evidence>[data-v99-zero] .v82-price-reasons').count(),0);
 }
 // A zero-only recipe must display an explicit amount; failed requests retain retry.
 await page.evaluate(()=>{panel._hass.language='en';render();});
 assert.match(await p.locator('#todayGrid [data-v82-card-cost]').last().innerText(),/0\.00/);
 await page.evaluate(()=>{const row=fixture[0],state=panel._v79CostState(row.recipe);state.cost=null;state.v90Failed=true;panel._v82PaintCard(row.recipe);});
 assert.equal(await p.locator('[data-v90-retry]').count(),1);
 assert.equal(await p.locator('[data-v90-retry]').evaluate(node=>node.parentElement.dataset.v99Confidence),'unavailable');
 await page.evaluate(()=>{window.retried=false;panel._v86QueuePreview=()=>window.retried=true;});await p.locator('[data-v90-retry]').click();assert.equal(await page.evaluate(()=>retried),true);
 await page.evaluate(()=>render());
 if(process.env.COOK4ME_SCREENSHOT_DIR){
  await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+'/v99-desktop.png'});
  await page.setViewportSize({width:390,height:1000});await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+'/v99-mobile.png'});
 }
 assert.deepEqual(errors,[]);console.log('v99: actual cards show five confidence states at upper left; mobile/translated layouts, zero allowances, missing rows and retry passed');
}finally{await browser.close();}
