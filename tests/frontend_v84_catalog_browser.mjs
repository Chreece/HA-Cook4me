import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
const root=fileURLToPath(new URL('..',import.meta.url));
const catalogs=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-c',`import importlib.util,json
s=importlib.util.spec_from_file_location('catalog','custom_components/cook4me/release_catalog.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
print(json.dumps({lang:{'items':c.ingredient_choices(lang),'presentationVersion':63,'offline':True} for lang in ['en','el']}))`],{cwd:root,maxBuffer:20_000_000}));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu','--disable-software-rasterizer','--use-gl=disabled']});
try{
 const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[];page.on('pageerror',e=>{errors.push(e.message);console.error(e.message);});
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><style>body{margin:0;font-family:Arial;--primary-color:#3d775d;--primary-text-color:#253b30;--primary-background-color:#f8faf8;--card-background-color:#fff;--secondary-background-color:#edf2ee;--secondary-text-color:#627468;--divider-color:#dce5df}</style><body></body>'}));
 await page.goto('http://cook4me.test/');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v84-bundle.js'});
 await page.evaluate(catalogs=>{
  window.catalogs=catalogs;window.calls=[];
  const p=window.panel=document.createElement('cook4me-recipe-hub-panel-v84');
  for(const method of ['_restorePreferences','_loadOverview','_loadBookState','_requestSection','_loadRecipeNutrition','_loadNutritionSettings','_loadFoodState','_loadInventoryState','_loadTodayOptions'])p[method]=async()=>{};
  p._hass={language:'en',user:{id:'alice'},states:{},config:{country:'DE'},connection:{
   sendMessagePromise:async msg=>{window.calls.push(structuredClone(msg));if(msg.type.endsWith('/ingredient_catalog')){if(window.failCatalog){window.failCatalog=false;throw Error('Temporarily unavailable');}if(window.delayCatalog)return new Promise(resolve=>window.releaseCatalog=()=>resolve(structuredClone(catalogs[msg.language])));return structuredClone(catalogs[msg.language]);}return {};},
   subscribeMessage:async()=>()=>{},addEventListener:()=>{},removeEventListener:()=>{}
  }};
  p._entryId='one';p._entries=['one','two'].map(id=>({entry_id:id,title:id,connected:true,state:{phase:'idle'},recipes:[],profile:{diet:'vegetarian',houseIngredients:[],allergies:[],avoid:[],preferences:[],householdMembers:[]}}));p._tab='profile';
  p._capabilities={ingredientCatalogLanguage:'en',deviceCatalogLanguage:'en'};p._ingredientCatalog=[];p._inventoryLoadedEntry='one';p._houseEntryId='one';p._nutritionSettings={};p._foodState={history:[],summary:{}};
  p._v78AcceptState({storageLocations:[{id:'pantry',name:'Pantry',kind:'pantry'}],houseIngredients:[],aiEntityId:'',aiChoices:[]});
  const original=p._api.bind(p);p._api=async(type,data)=>type.endsWith('/ingredient_catalog')?original(type,data):type.endsWith('/scanner_state')?p._v78State:type.endsWith('/price_settings')?{settings:{country:'DE',currency:'EUR',autoGlobalPrices:false}}:{};
  document.body.append(p);p._renderShell();p._renderTab();
 },catalogs);
 const panel=page.locator('cook4me-recipe-hub-panel-v84');
 await page.waitForFunction(()=>window.panel._ingredientCatalog.length>3000);
 assert.equal(await page.evaluate(()=>window.calls.filter(r=>r.type.endsWith('/ingredient_catalog')).length),1,'cold start loads the real offline catalog once');
 assert.equal(await panel.locator('[data-v84-rows] .v84-ingredient').count(),60);
 await panel.locator('[data-v84-search]').fill('basmati');assert.match(await panel.locator('[data-v84-rows]').innerText(),/basmati/i);
 // Manual product picker, exclusions, recipe filters and creator share the loaded catalog.
 await panel.locator('.v84-ingredient button').nth(1).click();await page.waitForFunction(()=>!!window.panel._v78Draft?.ingredient);
 assert.match(await page.evaluate(()=>window.panel._v78Draft.ingredient.name),/basmati/i);
 await page.evaluate(()=>window.panel._v78Close(true));
 await panel.locator('[data-v78-pane=food]').click();await panel.locator('[data-v83-profile=household] .v83-ingredient-picker>summary').click();
 await page.waitForFunction(()=>window.panel.shadowRoot.querySelector('[data-v83-profile=household] [data-v83-ingredient]')?.options.length>3000);
 assert.equal(await panel.locator('[data-v83-profile=household] [data-v83-ingredient] option').count(),catalogs.en.items.length+1);
 await page.evaluate(()=>window.panel._showFilter('ingredients'));
 assert.ok(await panel.locator('[data-ingredient-choices] label').count()>3000);await page.evaluate(()=>window.panel._v63CloseFilter());
 await page.evaluate(()=>{window.panel._tab='mine';window.panel._renderTab();});
 await panel.locator('[data-v82-creator=manual]>summary').click();
 assert.ok(await panel.locator('#manualCatalogSelect option').count()>0,'creator receives the offline catalog');
 await page.evaluate(()=>{window.panel._tab='profile';window.panel._v78Pane='food';window.panel._renderTab();});
 // Failed loads must settle, expose retry and never loop on an expanded picker.
 await page.evaluate(()=>{window.panel._ingredientCatalog=[];window.failCatalog=true;void window.panel._loadIngredientCatalog(null,true);});
 await page.waitForFunction(()=>!!window.panel._v63CatalogFailure&&!window.panel._ingredientCatalogLoading);
 const failedCalls=await page.evaluate(()=>window.calls.length);await page.waitForTimeout(150);assert.equal(await page.evaluate(()=>window.calls.length),failedCalls);
 await panel.locator('[data-v83-profile=household] .v83-picker-body button').last().click();await page.waitForFunction(()=>window.panel._ingredientCatalog.length>3000);
 await page.waitForFunction(()=>window.panel.shadowRoot.querySelector('[data-v83-profile=household] [data-v83-ingredient]')?.options.length>3000);
 assert.equal(await panel.locator('[data-v83-profile=household] [data-v83-ingredient] option').count(),catalogs.en.items.length+1);
 // Overlapping consumers await the same request; a language change can proceed
 // while an earlier request is still in flight and cannot be overwritten by it.
 await page.evaluate(()=>{window.delayCatalog=true;window.panel._ingredientCatalog=[];window.first=window.panel._loadIngredientCatalog(null,true);window.second=window.panel._loadIngredientCatalog();});
 assert.equal(await page.evaluate(()=>window.first===window.second),true);
 await page.evaluate(()=>{window.delayCatalog=false;window.panel._hass.language='el';void window.panel._loadIngredientCatalog();});
 await page.waitForFunction(()=>window.panel._ingredientCatalog[0]?.displayLanguage==='el');
 await page.evaluate(async()=>{window.releaseCatalog();await window.first;});
 assert.equal(await page.evaluate(()=>window.panel._ingredientCatalog.length),catalogs.el.items.length);
 assert.equal(await page.evaluate(()=>window.panel._ingredientCatalog[0].displayLanguage),'el');
 await panel.locator('[data-v78-pane=stock]').click();await panel.locator('[data-v84-search]').fill('ρύζι');assert.ok(await panel.locator('.v84-ingredient').count()>0);
 await page.setViewportSize({width:390,height:844});await panel.locator('[data-v84-search]').fill('');
 const overflow=await panel.locator('[data-v84-catalog]').evaluate(el=>el.scrollWidth>el.clientWidth+2);assert.equal(overflow,false);
 await page.screenshot({path:'/tmp/cook4me-v84-offline-catalog.png',fullPage:true});assert.deepEqual(errors,[]);
 console.log('v84 real offline catalog: cold load, browser, scanner, exclusions, filters, retry, coalescing, language race and mobile passed');
}finally{await browser.close();}
