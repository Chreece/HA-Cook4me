import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const version=process.env.COOK4ME_TEST_PANEL_VERSION||'79';
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu','--disable-software-rasterizer','--use-gl=disabled']});
try{
 const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><style>body{margin:0;font-family:Arial;--primary-color:#3d775d;--primary-text-color:#253b30;--primary-background-color:#f8faf8;--card-background-color:#fff;--secondary-background-color:#edf2ee;--secondary-text-color:#627468;--divider-color:#dce5df}</style><body></body>'}));
 await page.goto('http://cook4me.test/');
 await page.addScriptTag({path:fileURLToPath(new URL(`../custom_components/cook4me/frontend/cook4me-panel-v${version}-bundle.js`,import.meta.url))});
 await page.evaluate(version=>{
  const panel=document.createElement(`cook4me-recipe-hub-panel-v${version}`);window.panel=panel;window.calls=[];
  for(const method of ['_restorePreferences','_loadOverview','_loadBookState','_requestSection','_loadRecipeNutrition','_loadNutritionSettings','_loadFoodState','_loadInventoryState','_loadIngredientCatalog'])panel[method]=async()=>{};
  panel._hass={language:'en',user:{id:'scanner'},states:{},config:{country:'DE'},connection:{}};
  panel._entryId='one';panel._entries=[{entry_id:'one',title:'Kitchen Cook4Me',connected:true,state:{},recipes:[],profile:{diet:'vegetarian',houseIngredients:[],allergies:['peanuts'],avoid:[],preferences:[],householdMembers:[]}}];panel._tab='profile';
  panel._loadIngredientCatalog=async()=>{panel._ingredientCatalog=[{key:'rice',name:'Rice',searchAliases:['ρύζι']},{key:'milk',name:'Milk'}];panel._ingredientCatalogLanguage='en';};
  panel._capabilities={ingredientCatalogLanguage:'en',deviceCatalogLanguage:'en'};panel._ingredientCatalog=[{key:'rice',name:'Rice',searchAliases:['ρύζι']},{key:'milk',name:'Milk'}];panel._ingredientCatalogLanguage='en';panel._inventoryLoadedEntry='one';panel._nutritionSettings={};panel._foodState={history:[],summary:{}};
  window.state={storageLocations:[{id:'pantry',name:'Kitchen cupboard',kind:'pantry'},{id:'fridge',name:'Main fridge',kind:'fridge'}],houseIngredients:[],aiEntityId:'ai_task.photos',aiChoices:[{id:'ai_task.photos',name:'Photo assistant'}]};panel._v78AcceptState(structuredClone(window.state));
  panel._api=async(type,payload)=>{
   window.calls.push({type,...structuredClone(payload)});
   window.priceSettings??={country:'DE',currency:'EUR',autoGlobalPrices:true};
   if(type.endsWith('/price_settings')){if(payload.country)Object.assign(window.priceSettings,{country:payload.country,currency:payload.currency||'EUR',autoGlobalPrices:payload.auto_global_prices});return {settings:structuredClone(window.priceSettings)};}
   if(type.endsWith('/product_price')){
    if(window.delayPrice)return new Promise(resolve=>window.releasePrice=resolve);
    return {settings:structuredClone(window.priceSettings),status:'priced',matchKind:payload.barcode?'barcode':'ingredient',estimate:Number(payload.quantity)*3/500,reference:{amount:3,currency:'EUR',country:window.priceSettings.country,basisQuantity:500,basisUnit:'g',source:'open_prices',date:'2026-09-15',location:'German shop',observationId:17}};
   }
   if(type==='cook4me/v34/recipe_cost'){
    if(window.delayRecipePrice)return new Promise(resolve=>window.releaseRecipePrice=resolve);
    const amount=payload.recipe.ingredients[0]?.quantity||200;
    return {totalsByCurrency:{EUR:amount*3/500},perServingByCurrency:{EUR:amount*3/500/payload.recipe.servings},complete:payload.recipe.ingredients.length===1,estimated:true,targetCountry:'DE',ingredients:payload.recipe.ingredients.map((row,index)=>({name:row.name,coverage:index?0:1,priced:!index,costsByCurrency:index?{}:{EUR:amount*3/500},references:index?[]:[{amount:3,currency:'EUR',country:'DE',basisQuantity:500,basisUnit:'g',source:'open_prices',date:'2026-09-15',location:'German shop',observationId:17}]}))};
   }
   if(type.endsWith('/scanner_state'))return structuredClone(window.state);
   if(type.endsWith('/barcode_lookup')){if(window.delayLookup)return new Promise(resolve=>window.releaseLookup=resolve);return {barcode:payload.barcode,product:{productName:'Wholegrain rice',quantity:500,unit:'g',nutrition:{basisQuantity:100,basisUnit:'g',values:{energyKcal:350,protein:8,salt:0}}},mapping:{ingredient:{key:'rice',name:'Rice'}},suggestions:[]};}
   if(type.endsWith('/product_add')){if(window.failSave){window.failSave=false;throw new Error('Connection lost; retry');}window.state.houseIngredients=[{key:'rice',name:'Rice',quantity:500,unit:'g',lots:[{id:'lot',quantity:500,storage:'pantry',storageLocationId:'pantry'}]}];return {...structuredClone(window.state),status:'added',warnings:[]};}
   if(type.endsWith('/recognize_photo')){const product=payload.mode==='date'?{bestBefore:'2027-03-10'}:payload.mode==='nutrition'?{nutrition:{basisQuantity:100,basisUnit:'g',values:{protein:0,salt:0.3}}}:{productName:'Brown rice',quantity:750,unit:'g'};return {product,suggestions:[{ingredient:{key:'rice',name:'Rice'}}]};}
   if(type.endsWith('/storage_location')){if(payload.action==='delete')window.state.storageLocations=window.state.storageLocations.filter(r=>r.id!==payload.identity);else if(payload.identity)Object.assign(window.state.storageLocations.find(r=>r.id===payload.identity),{name:payload.name,kind:payload.kind});else window.state.storageLocations.push({id:'new-place',name:payload.name,kind:payload.kind});return structuredClone(window.state);}
   return {};
  };
  document.body.append(panel);panel._renderShell();panel._renderTab();
 },version);
 const panel=page.locator(`cook4me-recipe-hub-panel-v${version}`);
 await panel.locator('[data-v78-pane=integration]').click();
 await page.waitForFunction(()=>window.panel._v79Settings?.country==='DE');
 assert.equal(await panel.locator('[data-v79-country]').inputValue(),'DE');
 await panel.locator('[data-v79-country]').fill('GR');
 assert.equal(await panel.locator('[data-v79-currency]').inputValue(),'');
 await panel.locator('[data-v79-save-settings]').click();
 await page.waitForFunction(()=>window.panel._v79Settings?.country==='GR');
 assert.equal(await panel.locator('[data-v79-currency]').inputValue(),'EUR');
 const settingsCall=await page.evaluate(()=>window.calls.filter(r=>r.type.endsWith('/price_settings')).at(-1));
 assert.ok(!('currency' in settingsCall),'Changing country asks the server to choose its currency');
 await panel.locator('[data-v79-country]').fill('DE');await panel.locator('[data-v79-save-settings]').click();await page.waitForFunction(()=>window.panel._v79Settings?.country==='DE');
 await panel.locator('[data-v78-pane=stock]').click();
 await panel.locator('[data-v78-open=barcode]').first().click();const dialog=panel.locator('dialog.v78-capture');
 await dialog.locator('[data-draft=barcode]').fill('12345678');await dialog.locator('[data-v78-lookup]').click();
 await page.waitForFunction(()=>window.panel._v78Draft?.priceResult?.estimate===3);
 assert.match(await dialog.locator('[data-v79-estimate]').innerText(),/€3.00/);
 assert.match(await dialog.locator('[data-v79-estimate]').innerText(),/German shop/);
 assert.equal(await dialog.locator('[data-v79-paid]').inputValue(),'','Observation must never be presented as paid');
 await dialog.locator('[data-draft=quantity]').fill('250');
 await page.waitForFunction(()=>window.panel._v78Draft?.priceResult?.estimate===1.5);
 await dialog.locator('[data-v79-paid]').fill('0');await dialog.locator('[data-draft=storageLocationId]').selectOption('pantry');
 await page.setViewportSize({width:390,height:844});
 assert.ok(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth+1),'Price card fits mobile');
 if(process.env.COOK4ME_PRICE_SCREENSHOT){await dialog.locator('.v79-product-price').scrollIntoViewIfNeeded();await page.screenshot({path:process.env.COOK4ME_PRICE_SCREENSHOT});}
 await page.evaluate(()=>window.failSave=true);await dialog.locator('[data-v78-save]').click();await page.waitForFunction(()=>window.panel._v78Status.includes('Connection lost'));
 assert.equal(await dialog.locator('[data-v79-paid]').isDisabled(),true);
 await dialog.locator('[data-v78-save]').click();await dialog.locator('.v78-success').waitFor();
 const saves=await page.evaluate(()=>window.calls.filter(r=>r.type.endsWith('/product_add')));
 assert.deepEqual(saves[0],saves[1]);assert.equal(saves[0].paid_price.amount,0);assert.equal(saves[0].paid_price.currency,'EUR');
 await dialog.locator('[data-v78-next]').click();if(Number(version)<80)await dialog.locator('[data-v78-mode=manual]').click();
 await dialog.locator('[data-draft=quantity]').fill('100');await dialog.locator('[data-v78-ingredient]').selectOption('k:rice');
 await page.waitForFunction(()=>window.panel._v78Draft?.priceResult?.matchKind==='ingredient');
 assert.match(await dialog.locator('[data-v79-estimate]').innerText(),/Ingredient estimate/);
 // A slower reply for the old ingredient must not overwrite a newer selection.
 await page.evaluate(()=>window.delayPrice=true);await dialog.locator('[data-draft=quantity]').fill('101');await page.waitForFunction(()=>!!window.releasePrice);
 await page.evaluate(()=>window.delayPrice=false);await dialog.locator('[data-v78-ingredient]').selectOption('k:milk');
 await page.waitForFunction(()=>window.panel._v78Draft?.priceResult?.estimate===.606);
 await page.evaluate(()=>window.releasePrice({estimate:999,reference:{currency:'EUR'}}));
 assert.equal(await page.evaluate(()=>window.panel._v78Draft.priceResult.estimate),.606);
 // A reply after closing cannot recreate capture state or apply a stale result.
 await page.evaluate(()=>{window.releasePrice=null;window.delayPrice=true;});await dialog.locator('[data-draft=quantity]').fill('102');await page.waitForFunction(()=>!!window.releasePrice);
 await page.evaluate(()=>window.panel._v78Close(true));await page.evaluate(()=>window.releasePrice({estimate:999}));
 assert.equal(await page.evaluate(()=>window.panel._v78Draft),null);
 await page.setViewportSize({width:1280,height:900});
 // Render the real recipe body/bind path: expanded cards load automatically.
 await page.evaluate(()=>{
  const p=window.panel;window.recipe={id:'rice-recipe',title:'Rice supper',servings:2,language:'en',ingredients:[{key:'rice',name:'Rice',quantity:200,unit:'g'},{name:'Salt to taste'}],steps:[],match:{safe:true}};
  window.renderCost=()=>{let node=p.shadowRoot.querySelector('#testRecipe');if(!node){node=document.createElement('div');node.id='testRecipe';p.shadowRoot.append(node);}const state=p._v66State(window.recipe);state.expanded=true;node.innerHTML=p._v66Body(window.recipe,true,state);p._v66BindRecipe(node,window.recipe,true);};window.renderCost();
 });
 await page.waitForFunction(()=>window.panel._v79CostState(window.recipe).cost?.totalsByCurrency.EUR===1.2);
 const cost=panel.locator('#testRecipe [data-v79-price]');
 assert.match(await cost.innerText(),/Known subtotal · incomplete/);
 assert.match(await cost.innerText(),/1 \/ 2 ingredients fully priced/);
 assert.match(await cost.innerText(),/€0.60/);
 const firstCalls=await page.evaluate(()=>window.calls.filter(r=>r.type==='cook4me/v34/recipe_cost').length);
 await page.evaluate(()=>window.renderCost());await page.waitForTimeout(100);
 assert.equal(await page.evaluate(()=>window.calls.filter(r=>r.type==='cook4me/v34/recipe_cost').length),firstCalls,'Renders do not trigger repeated price calls');
 await page.evaluate(()=>{window.recipe.servings=4;window.recipe.ingredients[0].quantity=400;window.recipe.ingredients.pop();window.recipe.match.requiresSubstitutions=true;window.renderCost();});
 await page.waitForFunction(()=>window.panel._v79CostState(window.recipe).cost?.totalsByCurrency.EUR===2.4);
 assert.match(await cost.innerText(),/Recipe cost/);assert.match(await cost.innerText(),/Dietary substitutions are not priced/);
 assert.match(await cost.innerText(),/€0.60/);
 await cost.locator('summary').click();assert.match(await cost.innerText(),/German shop/);
 if(process.env.COOK4ME_RECIPE_PRICE_SCREENSHOT)await panel.locator('#testRecipe').screenshot({path:process.env.COOK4ME_RECIPE_PRICE_SCREENSHOT});
 // The previous variant's late response must not replace a newer cost.
 await page.evaluate(()=>{window.delayRecipePrice=true;window.recipe.ingredients[0].quantity=500;window.renderCost();});await page.waitForFunction(()=>!!window.releaseRecipePrice);
 await page.evaluate(()=>{window.delayRecipePrice=false;window.recipe.ingredients[0].quantity=600;window.renderCost();});await page.waitForFunction(()=>window.panel._v79CostState(window.recipe).cost?.totalsByCurrency.EUR===3.6);
 await page.evaluate(()=>window.releaseRecipePrice({totalsByCurrency:{EUR:999}}));
 assert.equal(await page.evaluate(()=>window.recipe.cost.totalsByCurrency.EUR),3.6);
 for(const language of ['de','el']){
  await page.evaluate(language=>{window.panel._hass.language=language;window.renderCost();},language);
  assert.ok(!(await cost.innerText()).includes('Recipe cost'));
 }
 assert.deepEqual(errors,[]);
 console.log('v79 pricing browser passed: country settings, automatic barcode/ingredient estimates, zero paid price, retry payload, mobile layout, recipe total/per-serving/partial costs, variants and stale responses.');
} finally {await browser.close();}
