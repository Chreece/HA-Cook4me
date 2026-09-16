import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage({viewport:{width:1100,height:850}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><body style="font:16px Arial"></body>'}));
 await page.goto('http://cook4me.test/');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v91-bundle.js'});
 await page.evaluate(()=>{
  globalThis.customElements.define('cook4me-v91-test',class extends customElements.get('cook4me-recipe-hub-panel-v91'){connectedCallback(){} disconnectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v91-test');
  p._hass={language:'en',user:{id:'alice'},config:{country:'DE'}};p._entryId='one';
  p._uiIngredientLanguage=()=> 'en';p._langCode=()=> 'en';p._prefKey=()=>p._entryId;p._v84SchedulePricePoll=()=>{};
  p._v79Payload=r=>({variantFunctionalId:r.variantFunctionalId||r.id});p._v79PaintRecipe=(recipe,state)=>p._v82PaintCard(recipe);
  window.calls=[];window.active=0;window.maximum=0;window.releases=[];
  p._api=async(type,data)=>{if(!type.endsWith('/recipe_cost'))return {};calls.push({type,...data});active++;maximum=Math.max(maximum,active);await new Promise(resolve=>releases.push(resolve));active--;return {offlinePreview:true,ingredients:[{name:'Onion',coverage:1,costsByCurrency:{EUR:.22}}],totalsByCurrency:{EUR:.22},complete:true};};
  document.body.append(p);if(!p.shadowRoot)p.attachShadow({mode:'open'});p.shadowRoot.innerHTML='<div id="content"></div>';
  for(let i=0;i<5;i++){const recipe={id:String(i),variantFunctionalId:String(i)},card=document.createElement('article');card.dataset.v66Ref=String(i);card._v82Recipe=recipe;card.innerHTML='<span data-v82-card-cost></span>';p.shadowRoot.querySelector('#content').append(card);p._v86QueuePreview(recipe,card);}
 });
 await page.waitForFunction(()=>window.calls.length===3);
 assert.equal(await page.evaluate(()=>maximum),3,'card previews have bounded concurrency');
 assert.equal(await page.evaluate(()=>calls.every(call=>call.offline_only===true)),true);
 await page.evaluate(()=>{releases.splice(0).forEach(resolve=>resolve());});
 await page.waitForFunction(()=>calls.length===5);
 await page.evaluate(()=>{releases.splice(0).forEach(resolve=>resolve());});
 await page.waitForFunction(()=>window.panel._v86Running===0);
 assert.match(await page.locator('cook4me-v91-test [data-v82-card-cost]').first().innerText(),/0\.22/);
 assert.match(await page.locator('cook4me-v91-test [data-v82-card-cost]').first().innerText(),/1\/1 ingredients priced/);
 await page.evaluate(()=>{
  const card=panel.shadowRoot.querySelector('[data-v66-ref]'),recipe=card._v82Recipe;
  panel._v79CostState(recipe).cost={complete:false,estimated:true,totalsByCurrency:{EUR:2.12},ingredients:[{name:'Milk',coverage:1},{name:'Salt <unsafe>',coverage:0,priceStatus:'recipe_amount_unknown'}]};
  panel._v82PaintCard(recipe);
 });
 assert.match(await page.locator('cook4me-v91-test [data-v82-card-cost]').first().innerText(),/Subtotal.*2.12.*1\/2 ingredients priced/);
 assert.match(await page.locator('cook4me-v91-test [data-v82-card-cost]').first().getAttribute('title'),/Salt <unsafe>.*quantity missing/);
 assert.equal(await page.locator('cook4me-v91-test unsafe').count(),0);
 // An old account/entry's response cannot repaint the new account's cards.
 await page.evaluate(()=>{
  const p=panel,recipe={id:'late'},card=document.createElement('article');card.dataset.v66Ref='late';card._v82Recipe=recipe;card.innerHTML='<span data-v82-card-cost></span>';p.shadowRoot.append(card);window.lateRecipe=recipe;p._v86QueuePreview(recipe,card);p._entryId='two';releases.splice(0).forEach(resolve=>resolve());
 });
 await page.waitForFunction(()=>panel._v86Running===0);
 assert.equal(await page.evaluate(()=>panel._v79CostState(lateRecipe).cost),null);
 await page.evaluate(()=>{
  const state={cost:{complete:false,estimated:true,targetCountry:'DE',totalsByCurrency:{EUR:.22},perServingByCurrency:{EUR:.11},ingredients:[
   {name:'Onion',coverage:1,costsByCurrency:{EUR:.22},quantityEstimate:{sourceQuantity:1,sourceUnit:'piece',quantity:110,unit:'g',label:'USDA medium onion',sourceUrl:'https://fdc.nal.usda.gov/food-details/170000/nutrients'}},
   {name:'Salt <unsafe>',coverage:0,costsByCurrency:{},priceStatus:'recipe_amount_unknown'}]}};
  panel.shadowRoot.innerHTML=panel._v79CostHtml({},state);
 });
 const panel=page.locator('cook4me-v91-test');
 assert.match(await panel.locator('[data-v86-missing]').innerText(),/Salt <unsafe>.*quantity missing/);
 await panel.locator('.v79-evidence>summary').click();
 assert.match(await panel.locator('[data-v86-quantity-estimate]').innerText(),/Estimated quantity: 1 piece ≈ 110 g/);
 assert.equal(await panel.locator('unsafe').count(),0);
 assert.match(await panel.locator('[data-v86-quantity-estimate] a').getAttribute('href'),/^https:\/\/fdc\.nal\.usda\.gov/);
 assert.match(await page.evaluate(()=>panel._v79Reference({source:'retail_snapshot',productName:'dmBio sugar',location:'dm Germany',date:'2026-09-16',amount:2.45,currency:'EUR',basisQuantity:500,basisUnit:'g',sourceUrl:'https://www.dm.de/p/d/1454994/dmbio-vollrohrzucker'})),/data-v87-reference.*dmBio sugar/);
 for(const url of ['javascript:alert(1)','https://www.dm.de.evil.test/x','https://www.dm.de@evil.test/x','https://www.dallmayr-versand.de.evil.test/x','https://www.dallmayr-versand.de@evil.test/x']){
  const html=await page.evaluate(url=>panel._v79Reference({source:'utility_snapshot',productName:'Water <unsafe>',note:'Local tariff <unsafe>',sourceUrl:url}),url);
  assert.equal(html.includes('<a '),false);assert.equal(html.includes('<unsafe>'),false);
 }
 const regional=await page.evaluate(()=>panel._v79Reference({source:'utility_snapshot',productName:'Berlin water',note:'Regional benchmark; excludes fixed charges',sourceUrl:'https://www.bwb.de/de/gebuehren.php'}));
 assert.match(regional,/Regional benchmark/);assert.match(regional,/href="https:\/\/www.bwb.de/);
 const onion=await page.evaluate(()=>panel._v79Reference({source:'retail_snapshot',productName:'Spring onion',note:'130 g bunch; Munich-only delivery',sourceUrl:'https://www.dallmayr-versand.de/p/lauchzwiebel-2669BD/'}));
 assert.match(onion,/130 g bunch/);assert.match(onion,/href="https:\/\/www.dallmayr-versand.de\/p\/lauchzwiebel/);
 for(const url of ['https://www.africshopping.com/product/coconut','https://www.clubhouseforchefs.ca/en-ca/products/curry','https://www.alnatura.de/de-de/rezepte/test']){
  const html=await page.evaluate(url=>panel._v79Reference({source:'retail_snapshot',productName:'Reference',sourceUrl:url}),url);
  assert.equal(html.includes('<a '),true);
 }
 const spoon=await page.evaluate(()=>panel._v79CostHtml({}, {cost:{totalsByCurrency:{EUR:.11},ingredients:[{name:'Curry paste',coverage:1,costsByCurrency:{EUR:.11},quantityEstimate:{sourceQuantity:.5,sourceUnit:'tbsp',quantity:7.5,unit:'g',label:'Thai Kitchen red curry paste: 1 tbsp = 15 g',sourceUrl:'https://www.clubhouseforchefs.ca/en-ca/products/thai-kitchen/thai-kitchen-red-curry-paste'}}]}}));
 assert.match(spoon,/href="https:\/\/www.clubhouseforchefs.ca/);
 for(const url of ['https://www.africshopping.com.evil.test/a','https://www.clubhouseforchefs.ca@evil.test/a','http://www.alnatura.de/a']){
  const html=await page.evaluate(url=>panel._v79Reference({source:'retail_snapshot',sourceUrl:url}),url);assert.equal(html.includes('<a '),false);
 }
 // Estimated budgets remain distinct from known costs and unresolved amounts.
 await page.evaluate(()=>{
  window.budgetCost={complete:false,totalsByCurrency:{EUR:1},perServingByCurrency:{EUR:.5},targetCountry:'DE',fallbackIngredientCount:1,budgetTotalsByCurrency:{EUR:2.5},budgetPerServingByCurrency:{EUR:1.25},budgetRangeByCurrency:{EUR:{low:1.5,high:5}},budgetIngredientCount:2,budgetComplete:false,ingredients:[
   {name:'Onion',coverage:1,costsByCurrency:{EUR:1}},
   {name:'Rare food <unsafe>',coverage:0,costsByCurrency:{},priceStatus:'offline_price_missing',fallbackEstimate:{amount:1.5,currency:'EUR',quantity:100,unit:'g',level:'food_basket',group:'basket',groupLabel:'Local food basket',sampleCount:20,low:.5,high:4,sources:[{name:'Source <unsafe>',date:'2026-09-16',rate:.015,unit:'g',sourceUrl:'javascript:alert(1)'},{name:'Onion reference',date:'2026-09-16',rate:.01,unit:'g',sourceUrl:'https://prices.openfoodfacts.org/prices/123'}]}},
   {name:'Salt',coverage:0,costsByCurrency:{},priceStatus:'recipe_amount_unknown'}]};
  panel.shadowRoot.innerHTML=panel._v79CostHtml({}, {cost:budgetCost});
 });
 assert.match(await panel.locator('[data-v91-budget]').innerText(),/Known cost.*1.00.*1 rough estimates/);
 assert.match(await panel.locator('.v79-price-head').innerText(),/Estimated subtotal.*2.50/s);
 assert.match(await panel.locator('[data-v86-missing]').innerText(),/Salt/);
 assert.doesNotMatch(await panel.locator('[data-v86-missing]').innerText(),/Rare food/);
 await panel.locator('.v79-evidence>summary').click();
 assert.match(await panel.locator('[data-v91-fallback]').innerText(),/Broad food basket/);
 assert.equal(await panel.locator('unsafe').count(),0);
 assert.equal(await panel.locator('a[href^="javascript:"]').count(),0);
 assert.equal(await panel.locator('a[href="https://prices.openfoodfacts.org/prices/123"]').count(),1);
 await page.evaluate(()=>{
  window.budgetRecipe={id:'budget'};const card=document.createElement('article');card.dataset.v66Ref='budget';card._v82Recipe=budgetRecipe;card.innerHTML='<span data-v82-card-cost></span>';panel.shadowRoot.append(card);panel._v79CostState(budgetRecipe).cost=budgetCost;panel._v82PaintCard(budgetRecipe);
 });
 assert.match(await panel.locator('[data-v82-card-cost]').innerText(),/Estimated subtotal.*2.50.*2\/3 ingredients covered.*1 rough estimates/);
 await page.evaluate(()=>{panel._uiIngredientLanguage=()=> 'el';panel._v82PaintCard(budgetRecipe);});
 assert.match(await panel.locator('[data-v82-card-cost]').innerText(),/Εκτιμώμενο μερικό σύνολο/);
 await page.evaluate(()=>{panel._uiIngredientLanguage=()=> 'en';});
 // Failed previews retry twice and retain an explicit retry control.
 await page.evaluate(()=>{
  panel.shadowRoot.innerHTML='<div id="content"></div>';panel._v90Validation=null;window.failCalls=0;
  panel._api=async type=>{if(type.endsWith('/price_settings'))return {};failCalls++;throw new Error('offline');};
  const recipe={id:'failure'},card=document.createElement('article');card.dataset.v66Ref='failure';card._v82Recipe=recipe;card.innerHTML='<span data-v82-card-cost></span>';panel.shadowRoot.append(card);panel._v86QueuePreview(recipe,card);
 });
 await page.waitForFunction(()=>panel.shadowRoot.querySelector('[data-v90-retry]'));
 assert.equal(await page.evaluate(()=>failCalls),3);
 assert.match(await panel.locator('[data-v82-card-cost]').innerText(),/Cost unavailable.*Retry/);
 await page.evaluate(()=>{panel._api=async type=>type.endsWith('/price_settings')?{}:{ingredients:[{coverage:1}],totalsByCurrency:{EUR:1},complete:true};});
 await panel.locator('[data-v90-retry]').click();
 await page.waitForFunction(()=>panel.shadowRoot.querySelector('[data-v82-card-cost]').textContent.includes('1/1'));
 // A changed recipe payload during an outstanding request is re-queued.
 await page.evaluate(()=>{
  panel.shadowRoot.innerHTML='';window.changedCalls=[];window.changedRelease=null;
  panel._api=async(type,data)=>{if(type.endsWith('/price_settings'))return {};changedCalls.push(data.recipe.variantFunctionalId);if(changedCalls.length===1)await new Promise(resolve=>changedRelease=resolve);return {ingredients:[{coverage:1}],totalsByCurrency:{EUR:changedCalls.length},complete:true};};
  window.changedRecipe={id:'before'};const card=document.createElement('article');card.dataset.v66Ref='changed';card._v82Recipe=changedRecipe;card.innerHTML='<span data-v82-card-cost></span>';panel.shadowRoot.append(card);panel._v86QueuePreview(changedRecipe,card);
 });
 await page.waitForFunction(()=>changedRelease);await page.evaluate(()=>{changedRecipe.id='after';changedRelease();});
 await page.waitForFunction(()=>changedCalls.length===2&&panel._v86Running===0);
 assert.deepEqual(await page.evaluate(()=>changedCalls),['before','after']);
 await page.evaluate(()=>{const state=panel._v79CostState(changedRecipe);state.cost={waterOnlyEstimate:true,ingredients:[{name:'Water',coverage:1},{name:'Food',coverage:0}],totalsByCurrency:{EUR:0},complete:false};panel._v82PaintCard(changedRecipe);});
 assert.match(await panel.locator('[data-v82-card-cost]').innerText(),/No food prices available/);
 assert.doesNotMatch(await panel.locator('[data-v82-card-cost]').innerText(),/0.00/);
 // Persist across a real reload, validated with one cheap settings/token request.
 const installHarness=()=>{
  globalThis.customElements.define('cook4me-cache-test',class extends customElements.get('cook4me-recipe-hub-panel-v91'){connectedCallback(){}});
  const p=window.cachePanel=document.createElement('cook4me-cache-test');p._hass={language:'en',user:{id:window.testUser||'alice'}};p._entryId='cache-entry';p._prefKey=()=>p._entryId;p._uiIngredientLanguage=()=> 'en';p._langCode=()=> 'en';
  p._v79Payload=r=>({variantFunctionalId:r.id,ingredients:r.ingredients});window.cacheCalls=0;window.settingsCalls=0;
  p._api=async type=>{if(type.endsWith('/price_settings')){settingsCalls++;return {priceCacheToken:window.testToken||'token-one'};}cacheCalls++;return {offlinePreview:true,ingredients:[{name:'Pasta',coverage:1}],totalsByCurrency:{EUR:2},complete:true};};
  document.body.append(p);if(!p.shadowRoot)p.attachShadow({mode:'open'});
  const recipe={id:'cache-recipe',ingredients:[{name:'Pasta',quantity:100,unit:'g'}]},card=document.createElement('article');card.dataset.v66Ref='cache';card._v82Recipe=recipe;card.innerHTML='<span data-v82-card-cost></span>';p.shadowRoot.append(card);p._v86QueuePreview(recipe,card);
 };
 await page.evaluate(installHarness);await page.waitForFunction(()=>cachePanel._v86Running===0&&cacheCalls===1);
 assert.equal(await page.evaluate(()=>settingsCalls),1);
 await page.reload();await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v91-bundle.js'});await page.evaluate(installHarness);
 await page.waitForFunction(()=>cachePanel.shadowRoot.querySelector('[data-v82-card-cost]').textContent.includes('1/1'));
 assert.equal(await page.evaluate(()=>cacheCalls),0,'a reload must reuse the persisted preview');
 assert.equal(await page.evaluate(()=>settingsCalls),1);
 // Changed server evidence and a different user both invalidate cached previews.
 for(const changes of [{testToken:'token-two'},{testUser:'bob'}]){
  await page.reload();await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v91-bundle.js'});await page.evaluate(changes=>Object.assign(window,changes),changes);await page.evaluate(installHarness);
  await page.waitForFunction(()=>cachePanel._v86Running===0&&cacheCalls===1);
 }
 await page.evaluate(async()=>{
  delete cachePanel._api;cachePanel._hass.connection={sendMessagePromise:async()=>({priceCacheToken:'after-refresh',costs:[]})};
  await cachePanel._api('cook4me/v34/recipe_cost_refresh',{entry_id:'cache-entry',recipes:[]});
 });
 assert.equal(await page.evaluate(()=>cachePanel._v90Cache.token),'after-refresh');
 assert.equal(await page.evaluate(()=>cachePanel._v90Validation),null);
 assert.deepEqual(errors,[]);console.log('v91 browser: offline previews, concurrency, entry isolation, persistent reload cache, changed evidence, retries, quantity sources and missing-cost explanation passed');
}finally{await browser.close();}
