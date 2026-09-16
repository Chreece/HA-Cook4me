import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const version=process.env.COOK4ME_TEST_PANEL_VERSION||'82';
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu','--disable-software-rasterizer','--use-gl=disabled']});
try{
 const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><style>body{margin:0;font-family:Arial;--primary-color:#3d775d;--primary-text-color:#253b30;--primary-background-color:#f8faf8;--card-background-color:#fff;--secondary-background-color:#edf2ee;--secondary-text-color:#627468;--divider-color:#dce5df}</style><body></body>'}));
 await page.goto('http://cook4me.test/');
 await page.addScriptTag({path:fileURLToPath(new URL(`../custom_components/cook4me/frontend/cook4me-panel-v${version}-bundle.js`,import.meta.url))});
 await page.evaluate(version=>{
  const p=window.panel=document.createElement(`cook4me-recipe-hub-panel-v${version}`);window.calls=[];window.subscriptions=[];window.connectionEvents={};window.saved={};window.priceAmount=2;window.savedManual=null;
  for(const method of ['_restorePreferences','_loadOverview','_loadBookState','_requestSection','_loadRecipeNutrition','_loadNutritionSettings','_loadFoodState','_loadInventoryState','_loadIngredientCatalog','_loadTodayOptions'])p[method]=async()=>{};
  const connection={subscribeMessage:async(callback,msg)=>{const r={callback,msg,removed:false};window.subscriptions.push(r);return()=>{r.removed=true;};},addEventListener:(type,cb)=>window.connectionEvents[type]=cb,removeEventListener:(type,cb)=>{if(window.connectionEvents[type]===cb)delete window.connectionEvents[type];}};
  p._hass={language:'en',user:{id:'alice'},states:{},config:{country:'DE'},connection};
  p._entryId='one';p._entries=['one','two'].map(id=>({entry_id:id,title:id==='one'?'Kitchen Cook4Me':'Second Cook4Me',connected:true,state:{phase:'idle'},recipes:[],profile:{diet:'vegetarian',houseIngredients:[],allergies:[],avoid:[],preferences:[],householdMembers:[]}}));p._tab='mine';
  p._ingredientCatalog=[{key:'rice',name:'Rice'}];p._ingredientCatalogLanguage='en';p._capabilities={ingredientCatalogLanguage:'en',deviceCatalogLanguage:'en',defaultAiTaskAvailable:true,languages:[{code:'en',name:'English'}]};p._inventoryLoadedEntry='one';p._houseEntryId='one';p._nutritionSettings={};p._foodState={history:[],summary:{}};
  const state={storageLocations:[{id:'pantry',name:'Pantry',kind:'pantry'}],houseIngredients:[],aiEntityId:'',aiChoices:[]};p._v78AcceptState(state);
  p._loadIngredientCatalog=async()=>{p._ingredientCatalog=[{key:'rice',name:'Rice'}];p._ingredientCatalogLanguage='en';const c=p.shadowRoot.querySelector('#content');if(c)p._renderManualCatalogChoices(c);};
  p._api=async(type,payload)=>{
   window.calls.push({type,...structuredClone(payload)});
   if(type.endsWith('/scanner_state'))return state;
   if(type==='cook4me/recipe_save'){window.savedManual=structuredClone(payload.recipe);p._entry().recipes.push({...payload.recipe,id:'manual-saved',source:'manual'});return p._entry().recipes.at(-1);}
   if(type.endsWith('/ai_create')){if(window.delayAi)return new Promise(resolve=>window.releaseAi=resolve);const recipe={id:'ai-saved',title:'AI rice supper',source:'ai',servings:2,ingredients:[{key:'rice',name:'Rice',quantity:100,unit:'g'}],steps:['Cook'],match:{safe:true,dietCheckVersion:76,diet:'vegetarian'}};p._entry().recipes.push(recipe);return {recipe};}
   const cost=recipe=>({complete:recipe.ingredients?.length>0,totalsByCurrency:{EUR:window.priceAmount},perServingByCurrency:{EUR:window.priceAmount/2},estimated:true,targetCountry:'DE',checkedAt:new Date().toISOString(),ingredients:(recipe.ingredients||[]).map(item=>({name:item.name,coverage:1,costsByCurrency:{EUR:window.priceAmount}}))});
   if(type.endsWith('/recipe_cost')){if(window.delayAuto)return new Promise(resolve=>window.releaseAuto=resolve);return cost(payload.recipe);}
   if(type.endsWith('/recipe_cost_refresh')){if(window.failPrice){window.failPrice=false;throw new Error('Price service offline');}if(window.delayPrices)return new Promise(resolve=>window.releasePrices=()=>resolve({costs:payload.recipes.map(cost)}));return {costs:payload.recipes.map(cost)};}

   if(type.endsWith('/device_settings')){
    const key=p._hass.user.id+':'+payload.entry_id;
    if(payload.settings)window.saved[key]=structuredClone(payload.settings);
    return {settings:window.saved[key]||{enabled:false,recipe:true,steps:true,state:true,connection:false,players:[],tts:'',ai:'',language:'',voice:''},choices:{players:[{id:'media_player.kitchen',name:'Kitchen speaker',announce:true}],tts:[{id:'tts.home',name:'Home voice',languages:['en','el','de'],defaultLanguage:'en',voices:{en:[{id:'warm',name:'Warm voice'}],el:[],de:[]}}],ai:[]}};
   }
   return {};
  };
  window.emit=(state,connected=true)=>{
   const sub=window.subscriptions.findLast(r=>r.msg.type.endsWith('/device_state_subscribe')&&!r.removed);
   sub.callback({entry_id:sub.msg.entry_id,accessible:true,connected,canAcceptRecipe:state.phase==='idle',loadedRecipe:null,state});
  };
  document.body.append(p);p._renderShell();p._renderTab();p._updateHeader();
 },version);
 const panel=page.locator(`cook4me-recipe-hub-panel-v${version}`);
 assert.deepEqual(await panel.locator('#tabs [data-tab]').evaluateAll(nodes=>nodes.map(n=>n.dataset.tab)),['today','week','official','book','mine','shopping','profile']);
 assert.deepEqual(await panel.locator('#tabs [data-tab]').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('aria-label'))),['Today','Week','Search recipe','Cooking book','Recipe creator','Shopping list','My kitchen & preferences']);
 assert.ok(await panel.locator('#tabs [data-tab]').evaluateAll(nodes=>nodes.every(n=>n.innerText.trim()===''&&n.querySelector('ha-icon')&&n.title)),'Navigation is icons only with accessible labels: '+JSON.stringify(await panel.locator('#tabs [data-tab]').evaluateAll(nodes=>nodes.map(n=>n.outerHTML))));
 assert.equal(await panel.locator('[data-v82-creator]').count(),2);
 assert.equal(await panel.locator('[data-v82-creator=manual]').getAttribute('open'),null);
 assert.equal(await panel.locator('#v82RefreshPrices').isDisabled(),true);
 await panel.locator('[data-v82-creator=manual]>summary').click();
 await panel.locator('#manualTitle').fill('My rice supper');await panel.locator('#manualServings').fill('2');await panel.locator('#manualSteps').fill('Cook the rice');await panel.locator('#manualCatalogSelect').selectOption('0');await panel.locator('#manualCatalogAdd').click();
 await panel.locator('[data-manual-qty="0"]').fill('150');await panel.locator('[data-manual-unit="0"]').fill('g');
 await panel.locator('[data-v82-creator=ai]>summary').click();await panel.locator('#aiRequest').fill('A vegetarian rice dish');
 await page.evaluate(()=>window.panel._renderTab());
 assert.equal(await panel.locator('#manualTitle').inputValue(),'My rice supper');assert.equal(await panel.locator('[data-manual-qty="0"]').inputValue(),'150');assert.equal(await panel.locator('#aiRequest').inputValue(),'A vegetarian rice dish');
 await panel.locator('#tabs [data-tab=profile]').click();await panel.locator('#tabs [data-tab=mine]').click();
 assert.equal(await panel.locator('#manualTitle').inputValue(),'My rice supper');assert.equal(await panel.locator('#aiRequest').inputValue(),'A vegetarian rice dish');
 await panel.locator('#manualSave').click();await page.waitForFunction(()=>window.savedManual?.title==='My rice supper');
 assert.equal(await page.evaluate(()=>window.savedManual.ingredients[0].quantity),'150');assert.equal(await panel.locator('#manualTitle').inputValue(),'');
 await panel.locator('#aiCreate').click();await page.waitForFunction(()=>!window.panel._aiBusy&&window.panel._v82AiRecipe?.title==='AI rice supper');
 assert.equal(await panel.locator('#tabs [data-tab=mine]').getAttribute('aria-pressed'),'true');
 assert.ok((await panel.locator('#mineGrid').innerText()).includes('My rice supper'));
 assert.ok((await panel.locator('[data-v82-ai-body]').innerText()).includes('AI rice supper'));
 // Both independent sections fit mobile and keep their drafts/open state across renders.
 for(const lang of ['en','de','el']){
  await page.setViewportSize({width:360,height:740});await page.evaluate(lang=>{window.panel._hass.language=lang;window.panel._renderTabs();window.panel._renderTab();},lang);
  assert.ok(await panel.locator('#tabs').evaluate(el=>el.scrollWidth<=el.clientWidth+1),'Seven icons fit a 360 px phone');
  assert.ok(await panel.locator('#content').evaluate(el=>el.scrollWidth<=el.clientWidth+1),'Creators fit mobile');
 }
 if(process.env.COOK4ME_SCREENSHOT_DIR)await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+'/v82-creator-mobile.png',fullPage:true});
 await page.setViewportSize({width:1280,height:900});await page.evaluate(()=>{window.panel._hass.language='en';window.panel._renderTabs();window.panel._renderTab();});
 await page.evaluate(()=>{const p=window.panel;p.shadowRoot.querySelectorAll('[data-v82-creator]').forEach(d=>d.open=false);document.scrollingElement.scrollTop=0;p.shadowRoot.querySelector('.wrap').scrollTop=0;p._updateHeader();});
 if(process.env.COOK4ME_SCREENSHOT_DIR)await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+'/v82-creators.png'});
 // Use real cards; refresh only this rendered page, not the rest of a result set.
 await page.evaluate(version=>{
  const p=window.panel;p._v66PreferLanguages=async()=>{};
  p._results=Array.from({length:10},(_,index)=>({id:'r'+index,displayVariantId:'r'+index,title:'Recipe '+index,source:'sebplatform_search',language:'en',servings:2,ingredients:[{key:'rice',name:'Rice',quantity:100+index,unit:'g'}],steps:['Cook'],match:{safe:true,dietCheckVersion:76,diet:'vegetarian'}}));
  p._tab='official';p._renderTabs();p._renderTab();
 });
 assert.equal(await panel.locator('#content [data-v66-ref]').count(),8,JSON.stringify(await page.evaluate(()=>({tab:window.panel._tab,results:window.panel._results.length,html:window.panel.shadowRoot.querySelector('#content').innerHTML.slice(0,1200),calls:window.calls.slice(-3)}))));assert.equal(await panel.locator('#v82RefreshPrices').isEnabled(),true);
 await panel.locator('#v82RefreshPrices').click();await page.waitForFunction(()=>!window.panel._v82Refresh);
 const refreshCalls=await page.evaluate(()=>window.calls.filter(c=>c.type.endsWith('/recipe_cost_refresh')));
 assert.equal(refreshCalls.at(-1).recipes.length,8);assert.ok(refreshCalls.at(-1).recipes.every(r=>r.title!=='Recipe 8'&&r.title!=='Recipe 9'));
 assert.ok((await panel.locator('[data-v82-card-cost]').first().innerText()).includes('2.00'));
 // Old automatic responses must not overwrite an explicit refresh.
 await page.evaluate(()=>{window.delayAuto=true;const p=window.panel,r=p._results[0],s=p._v79CostState(r);s.started=false;void p._v79LoadCost(r);window.priceAmount=4;});
 await panel.locator('#v82RefreshPrices').click();await page.waitForFunction(()=>!window.panel._v82Refresh);
 await page.evaluate(()=>{window.releaseAuto({complete:true,totalsByCurrency:{EUR:1},ingredients:[]});window.delayAuto=false;});
 assert.equal(await page.evaluate(()=>window.panel._v79CostState(window.panel._results[0]).cost.totalsByCurrency.EUR),4);
 // Failed refresh preserves existing totals and can be retried.
 await page.evaluate(()=>window.failPrice=true);await panel.locator('#v82RefreshPrices').click();await page.waitForFunction(()=>!window.panel._v82Refresh);
 assert.equal(await page.evaluate(()=>window.panel._v79CostState(window.panel._results[0]).cost.totalsByCurrency.EUR),4);
 await panel.locator('#v82RefreshPrices').click();await page.waitForFunction(()=>!window.panel._v82Refresh);
 if(process.env.COOK4ME_SCREENSHOT_DIR)await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+'/v82-recipe-prices.png'});
 // Fullscreen exposes the same action but scopes it to the open recipe.
 await panel.locator('[data-v66-ref]').first().locator('h3').click();const fullscreen=panel.locator('[data-recipe-dialog]');await fullscreen.waitFor();
 await fullscreen.locator('[data-v82-refresh-prices]').click();await page.waitForFunction(()=>!window.panel._v82Refresh);
 assert.equal(await page.evaluate(()=>window.calls.filter(c=>c.type.endsWith('/recipe_cost_refresh')).at(-1).recipes.length),1);
 await fullscreen.locator('[data-modal-close]').click();
 // A late response cannot paint another page/account.
 await page.evaluate(()=>window.delayPrices=true);await panel.locator('#v82RefreshPrices').click();await page.waitForFunction(()=>Boolean(window.releasePrices));
 await panel.locator('#tabs [data-tab=shopping]').click();await page.evaluate(()=>{window.releasePrices();window.delayPrices=false;});
 assert.equal(await panel.locator('#tabs [data-tab=shopping]').getAttribute('aria-pressed'),'true');assert.equal(await panel.locator('#v82RefreshPrices').isDisabled(),true);
 // Restored old AI tab lands in the shared creator, expanded at AI.
 await page.evaluate(()=>{window.panel._tab='ai';window.panel._renderTabs();window.panel._renderTab();});
 assert.equal(await panel.locator('#tabs [data-tab=ai]').count(),0);assert.equal(await panel.locator('#aiRequest').isVisible(),true);
 await page.evaluate(()=>window.delayAi=true);await panel.locator('#aiCreate').click();await page.waitForFunction(()=>Boolean(window.releaseAi));
 await page.evaluate(()=>{window.panel._hass.user={id:'bob'};window.panel._renderTab();window.releaseAi({recipe:{id:'private',title:'Alice private recipe',ingredients:[]}});});
 assert.equal(await panel.locator('#manualTitle').inputValue(),'');assert.ok(!(await panel.locator('#content').innerText()).includes('Alice private recipe'));
 await page.evaluate(()=>window.panel.remove());assert.deepEqual(errors,[]);
 console.log('v82: ordered icon navigation, merged creators, draft/save/AI flows, mobile layouts, visible recipe refresh, cache races and account isolation passed');
}finally{await browser.close();}
