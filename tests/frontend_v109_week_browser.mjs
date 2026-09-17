import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const fixture=JSON.parse(readFileSync(root+'/docs/price-confidence-v99-preview.json','utf8'));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage({viewport:{width:390,height:1000}}),errors=[];
 page.on('pageerror',error=>{errors.push(error.message);console.error(error.stack);});
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><body style="margin:0;font:16px Arial;--primary-color:#00a4ca;--card-background-color:#202525;--primary-background-color:#111;--primary-text-color:#eee;--text-primary-color:#fff;--secondary-text-color:#aaa;--divider-color:#3e4444;--secondary-background-color:#292e2e"></body>'}));
 await page.goto('http://cook4me.test/');
 // HA supplies this element in production. A compact SVG stand-in makes the
 // isolated layout screenshot readable without contacting the HA frontend.
 await page.evaluate(()=>customElements.define('ha-icon',class extends HTMLElement{
  static get observedAttributes(){return ['icon'];}
  connectedCallback(){this.paint();}attributeChangedCallback(){this.paint();}
  paint(){if(!this.shadowRoot)this.attachShadow({mode:'open'});const name=this.getAttribute('icon')||'';
   const symbols={'mdi:weather-sunny':'☼','mdi:calendar-week':'▣','mdi:magnify':'⌕','mdi:book-open-page-variant-outline':'▤','mdi:chef-hat':'♧','mdi:cart-outline':'🛒','mdi:home-heart':'⌂','mdi:web':'◎','mdi:refresh':'⟳','mdi:filter-variant':'☰','mdi:leaf':'♧','mdi:clock-outline':'◷'};
   this.shadowRoot.innerHTML=`<style>:host{display:inline-flex;width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px);align-items:center;justify-content:center;vertical-align:middle;flex-shrink:0}span{font:24px/1 Arial;color:inherit}</style><span aria-hidden="true">${symbols[name]||'◇'}</span>`;
  }
 }));
 await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v109-bundle.js'});
 await page.evaluate(fixture=>{
  window.fixture=fixture;window.requests=[];window.subscriptions=[];
  globalThis.customElements.define('cook4me-v109-test',class extends globalThis.customElements.get('cook4me-recipe-hub-panel-v109'){connectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v109-test');
  p._hass={language:'el',user:{id:'alice'},states:{},config:{country:'DE',time_zone:'Europe/Berlin'},connection:{
   sendMessagePromise:async message=>{const request=message.request||message;requests.push(request);if(window.respond)return respond(request);if(request.type.endsWith('/currency_set'))return {currency:request.currency||'EUR',defaultCurrency:'EUR',mode:request.mode,currencies:['EUR','USD','GBP']};return {};},
   subscribeMessage:async(callback,request)=>{subscriptions.push({callback,request});return ()=>{};},addEventListener(){},removeEventListener(){}}};
  for(const method of ['_restorePreferences','_loadOverview','_requestSection','_loadRecipeNutrition','_loadIngredientCatalog','_loadTodayOptions','_loadCurrencyState','_loadBookState','_loadShoppingList','_v78Load','_v79LoadSettings','_loadNutritionOptions'])p[method]=async()=>{};
  p._v84SchedulePricePoll=()=>{};p._v86QueuePreview=()=>{};p._v66PreferLanguages=async rows=>rows;
  p._entryId='one';p._entries=[{entry_id:'one',title:'Cook4Me της κουζίνας',connected:false,state:{phase:'idle'},profile:{diet:'vegetarian',houseIngredients:[]},recipes:[]}];p._tab='week';p._v67Today=()=> '2026-09-17';
  p._v63FilterKey=p._prefKey();p._v63Filters={diet:'vegetarian',dietProfile:'manual',ingredients:[],languages:p._languageRows().map(row=>row.code),mealTypes:['breakfast','starter','salad','soup','main','side','dessert','snack'],onlyHome:false,preferExpiring:true,avoidRecentDays:7,maxMissing:'',nutritionGoal:'balanced',maxCost:'',excludedIngredients:[],excludedTerms:[]};
  p._currencyState={currency:'EUR',defaultCurrency:'EUR',mode:'auto',currencies:['EUR','USD','GBP']};p._currencyStateEntry='one';
  p._bookState={favorites:[],recipeList:[]};p._shoppingList=[];p._v78State={storageLocations:[],products:[]};p._v78Loaded=p._prefKey();
  p._todayResults=fixture.slice(0,2).map(row=>({...row.recipe,match:{diet:'vegetarian',dietCheckVersion:76,safe:true}}));
  p._v67WeekLoaded=`${p._prefKey()}:${p._v67Today()}`;p._v93Now=()=>new Date('2026-09-17T08:07:00Z');
  
  const cost=(amount,complete=true)=>({totalsByCurrency:{EUR:amount},budgetTotalsByCurrency:{EUR:amount},complete,budgetComplete:complete,ingredients:[],priceConfidence:complete?'reference':'partial'});
  const recipe=(id,nutrition,price,servings=2)=>({...fixture[0].recipe,id,displayVariantId:id,title:id,language:'en',languageVariants:[],availableLanguages:['en'],servings,catalogNutrition:nutrition,cost:price,mealTypes:[id==='A'?'breakfast':'main'],match:{diet:'vegetarian',dietCheckVersion:76,safe:true}});
  window.plan={weekStart:'2026-09-17',settings:{},leftovers:[],reservations:{},shoppingDelta:[],slots:[
   {id:'a',date:'2026-09-17',mealType:'breakfast',recipe:recipe('A',{perServing:{energyKcal:100,proteinG:5,sugarsG:0},coverage:1},cost(8)),cost:cost(.01)},
   {id:'b',date:'2026-09-17',mealType:'dinner',recipe:recipe('B',{totals:{energyKcal:900,protein:30},coverage:.5},cost(12,false),3),cost:cost(.01)},
   {id:'c',date:'2026-09-18',mealType:'dinner',leftoverId:'rest',nutrition:{totals:{energyKcal:120,protein:6}},cost:cost(2),recipe:recipe('C',{totals:{energyKcal:3000}},cost(18),6)},
   {id:'d',date:'2026-09-19',mealType:'dinner',recipe:recipe('D',{},null,null)}]};
  window.respond=async request=>{
   if(request.type.endsWith('/week_slot_clear')){plan.slots=plan.slots.filter(row=>row.id!==request.slot_id);return structuredClone(plan);}
   if(request.type.endsWith('/week_state')||request.type.endsWith('/week_generate')){
    if(window.failWeek)throw Error('temporary connection failure');
    if(window.holdWeek){window.pendingWeek={request,resolve:null};return await new Promise(resolve=>pendingWeek.resolve=resolve);}
    const copy=structuredClone(plan),meals=request.shared_filters?.mealTypes||[];
    if(meals.length&&meals.length<8)copy.slots=copy.slots.filter(slot=>meals.includes(slot.recipe.mealTypes[0]));
    copy.filteredSlotCount=plan.slots.length-copy.slots.length;return copy;
   }
   return {};
  };
  p._renderShell();document.body.append(p);p._renderEntrySelect();p._updateHeader();p._renderTab();

 },fixture);
 const p=page.locator('cook4me-v109-test');
 await page.waitForFunction(()=>panel._weekState?._v109Key===panel._v109Key()&&!panel._weekLoading);
 assert.equal(await p.locator('.rx-week-slot').count(),4);
 assert.equal(await p.locator('ha-icon[icon="mdi:calendar-cog"],#savePlanner,#targetCalories,[data-week-meal]').count(),0);
 assert.equal(await p.locator('.v100-filter-slot .rx-shared-filters').count(),1);
 assert.deepEqual(await p.locator('[data-week-summary-date]').evaluateAll(rows=>rows.map(row=>row.dataset.weekSummaryDate)),['2026-09-17','2026-09-18','2026-09-19','2026-09-20','2026-09-21','2026-09-22','2026-09-23']);
 const totals=()=>page.evaluate(()=>panel._v109Totals(panel._v109Rows(true)));
 let result=await totals();assert.equal(result.count,4);assert.equal(result.values[0].value,1220);assert.equal(result.values[1].value,46);assert.equal(result.values[1].known,3);assert.equal(result.values[5].value,0);assert.equal(result.values[5].known,1);assert.deepEqual(result.cost,{EUR:22});
 assert.ok((await p.locator('[data-week-total] [data-week-cost]').innerText()).includes('22'));
 assert.equal(await p.locator('[data-week-summary-date="2026-09-19"] td').nth(1).innerText(),'—');
 // Live price changes update both summaries without replacing recipe cards or scrolling.
 await page.evaluate(()=>{window.originalCard=panel.shadowRoot.querySelector('[data-slot-id=a]');const recipe=panel._weekState.slots[0].recipe;const state=panel._v79CostState(recipe);state.cost={...recipe.cost,budgetTotalsByCurrency:{EUR:14}};recipe.cost=state.cost;panel._v79PaintRecipe(recipe,state);});
 await page.waitForFunction(()=>panel.shadowRoot.querySelector('[data-week-total] [data-week-cost]').textContent.includes('28'));
 assert.equal(await page.evaluate(()=>originalCard===panel.shadowRoot.querySelector('[data-slot-id=a]')),true);
 // Only the common right-hand filters control the plan, including real Apply clicks.
 await p.locator('.v93-filter-toggle').click();await p.locator('[data-filter=meals]').click();
 for(const checkbox of await p.locator('[data-filter-dialog=meals] input[data-list=mealTypes]').all())await checkbox.uncheck();
 await p.locator('[data-filter-dialog=meals] input[value=main]').check();
 await p.locator('[data-filter-dialog=meals] [data-apply]').click();
 await page.waitForFunction(()=>!panel._weekLoading&&panel._weekState?._v109Key===panel._v109Key());
 assert.equal(await p.locator('.rx-week-slot').count(),3);
 assert.equal((await totals()).count,3);
 assert.equal(await page.evaluate(()=>plan.slots.length),4,'filtering must not delete saved meals');
 await p.locator('#generateWeek').click();
 await page.waitForFunction(()=>requests.some(r=>r.type.endsWith('/week_generate')));
 assert.deepEqual(await page.evaluate(()=>requests.findLast(r=>r.type.endsWith('/week_generate')).shared_filters.mealTypes),['main']);
 assert.equal(await page.evaluate(()=>requests.findLast(r=>r.type.endsWith('/week_generate')).shared_filters.diet),'vegetarian');
 // Clearing uses a newly filtered state rather than restoring hidden meals.
 await page.evaluate(()=>panel._weekClear('b'));
 assert.equal(await p.locator('.rx-week-slot').count(),2);
 assert.equal((await totals()).values[0].value,120);
 // A slow response for an old filter cannot overwrite a new selection.
 await page.evaluate(()=>{holdWeek=true;panel._filters().mealTypes=['breakfast'];panel._renderTab();});
 await page.waitForFunction(()=>window.pendingWeek?.resolve);
 await page.evaluate(()=>{panel._filters().mealTypes=['main'];holdWeek=false;pendingWeek.resolve(structuredClone(plan));});
 await page.waitForFunction(()=>!panel._weekLoading&&panel._weekState?._v109Key===panel._v109Key());
 assert.equal(await p.locator('[data-slot-id=a]').count(),0);
 // Read failure stops automatically retrying; Retry recovers.
 await page.evaluate(()=>{failWeek=true;panel._filters().mealTypes=['breakfast'];panel._renderTab();});
 await p.locator('[data-week-retry]').waitFor();
 const calls=await page.evaluate(()=>requests.filter(r=>r.type.endsWith('/week_state')).length);
 await page.waitForTimeout(150);
 assert.equal(await page.evaluate(()=>requests.filter(r=>r.type.endsWith('/week_state')).length),calls);
 await page.evaluate(()=>failWeek=false);await p.locator('[data-week-retry]').click();
 await page.waitForFunction(()=>!panel._weekLoading&&panel._weekState?._v109Key===panel._v109Key());
 assert.equal(await p.locator('[data-slot-id=a]').count(),1);
 for(const language of ['el','de','en']){
  await page.evaluate(language=>{panel._hass.language=language;panel._renderTab();},language);
  await page.waitForFunction(()=>!panel._weekLoading&&panel._weekState?._v109Key===panel._v109Key());
  for(const width of [390,1600]){
   await page.setViewportSize({width,height:1000});
   await page.evaluate(()=>panel.shadowRoot.querySelectorAll('.rx-v59-op').forEach(n=>n.remove()));
   const card=p.locator('[data-week-summary]');
   assert.equal(await card.evaluate(n=>n.scrollWidth<=n.clientWidth+1),true,language+' '+width);
   assert.equal(await page.evaluate(()=>panel._cook4meUiGuardTripped),false);
   if(process.env.COOK4ME_SCREENSHOT_DIR&&language==='el')await card.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+`/v109-week-summary-${width}.png`});
  }
 }
 assert.deepEqual(errors,[]);
 console.log('v109: planned quantities, seven future dates, partial/missing/zero values, live budget totals, shared filter Apply/generate/clear, stale responses, retry recovery and el/de/en responsive layout passed');
}finally{await browser.close();}
