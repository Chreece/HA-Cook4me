import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu','--disable-software-rasterizer','--use-gl=disabled']});
try{
 const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><style>body{margin:0;font-family:Arial;--primary-color:#3d775d;--primary-text-color:#253b30;--primary-background-color:#f8faf8;--card-background-color:#fff;--secondary-background-color:#edf2ee;--secondary-text-color:#627468;--divider-color:#dce5df}</style><body></body>'}));
 await page.goto('http://cook4me.test/');
 await page.addScriptTag({path:fileURLToPath(new URL('../custom_components/cook4me/frontend/cook4me-panel-v83-bundle.js',import.meta.url))});
 await page.evaluate(()=>{
  const p=window.panel=document.createElement('cook4me-recipe-hub-panel-v83');window.calls=[];window.subscriptions=[];window.connectionEvents={};window.saved={};window.priceAmount=2;window.savedManual=null;
  for(const method of ['_restorePreferences','_loadOverview','_loadBookState','_requestSection','_loadRecipeNutrition','_loadNutritionSettings','_loadFoodState','_loadInventoryState','_loadIngredientCatalog','_loadTodayOptions'])p[method]=async()=>{};
  const connection={sendMessagePromise:async msg=>msg.preferences||{},subscribeMessage:async(callback,msg)=>{const r={callback,msg,removed:false};window.subscriptions.push(r);return()=>{r.removed=true;};},addEventListener:(type,cb)=>window.connectionEvents[type]=cb,removeEventListener:(type,cb)=>{if(window.connectionEvents[type]===cb)delete window.connectionEvents[type];}};
  p._hass={language:'en',user:{id:'alice'},states:{},config:{country:'DE'},connection};
  p._entryId='one';p._entries=['one','two'].map(id=>({entry_id:id,title:id==='one'?'Kitchen Cook4Me':'Second Cook4Me',connected:true,state:{phase:'idle'},recipes:[],profile:{diet:'vegetarian',houseIngredients:[],allergies:[],avoid:[],preferences:[],householdMembers:[]}}));p._tab='profile';
  p._ingredientCatalog=[{key:'rice',name:'Rice'}];p._ingredientCatalogLanguage='en';p._capabilities={ingredientCatalogLanguage:'en',deviceCatalogLanguage:'en',defaultAiTaskAvailable:true,languages:[{code:'en',name:'English'}]};p._inventoryLoadedEntry='one';p._houseEntryId='one';p._nutritionSettings={};p._foodState={history:[],summary:{}};
  const state={storageLocations:[{id:'pantry',name:'Pantry',kind:'pantry'}],houseIngredients:[],aiEntityId:'',aiChoices:[]};p._v78AcceptState(state);
  p._loadIngredientCatalog=async()=>{p._ingredientCatalog=[{key:'rice',name:'Rice'}];p._ingredientCatalogLanguage='en';const c=p.shadowRoot.querySelector('#content');if(c)p._renderManualCatalogChoices(c);};
  Object.getPrototypeOf(Object.getPrototypeOf(p))._api=async(type,payload)=>{
   window.calls.push({type,...structuredClone(payload)});
   if(type.endsWith('/scanner_state'))return state;
   if(type.endsWith('/diet_profiles')){if(window.failProfiles){window.failProfiles=false;throw new Error('Save failed');}if(window.delayProfiles)return new Promise(resolve=>window.releaseProfiles=resolve);window.profiles=structuredClone(payload.profiles);for(const row of [window.profiles.household,...window.profiles.members])for(const key of ['calorieTarget','proteinTarget','carbsTarget','fatTarget','saturatedFatTarget','sugarsTarget','fiberTarget','saltTarget','sodiumTarget'])row[key]=row[key]===''||row[key]==null?null:Number(row[key]);return {profile:{...p._entry().profile,dietProfiles:window.profiles,householdMembers:payload.profiles.members.map(r=>r.name),preferences:payload.preferences}};}
   if(type.endsWith('/recipe_detail')){if(window.delayDetail)return new Promise(resolve=>window.releaseDetail=resolve);return {title:'Detail',ingredients:[]};}

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
  p._entries[0].profile.allergies=['nuts'];p._entries[0].profile.avoid=['onion'];
  p._loadWeekState=async()=>{};
  const catalog=Array.from({length:3000},(_,i)=>({ingredientId:'food-'+i,key:'food-'+i,name:i===2999?'Tomato':i===0?'Rice':'Ingredient '+i,canonicalName:i===2999?'Tomato':i===0?'Rice':'Ingredient '+i,sourceIngredientIds:['food-'+i,'sibling-'+i]}));
  p._ingredientCatalog=catalog;p._houseEntryId='one';p._loadIngredientCatalog=async()=>{p._ingredientCatalog=catalog;};
  document.body.append(p);p._renderShell();p._renderTab();p._updateHeader();
 });
 const panel=page.locator('cook4me-recipe-hub-panel-v83');
 await panel.locator('[data-v78-pane=food]').click();
 assert.equal(await panel.locator('#allergies,#avoid,#householdMembers').count(),0);
 const household=panel.locator('[data-v83-profile=household]');
 assert.equal(await household.locator('.v83-excluded-chip').count(),2,'Existing exclusions survive');
 await household.locator('[data-v83-field=diet]').selectOption('vegan');
 await household.locator('.v83-target-section>summary').click();
 assert.equal(await household.locator('.v83-targets input').count(),9);
 await household.locator('[data-v83-field=calorieTarget]').fill('600');await household.locator('[data-v83-field=proteinTarget]').fill('25');
 await household.locator('.v83-ingredient-picker>summary').click();
 await household.locator('[data-v83-ingredient] option').last().waitFor({state:'attached'});
 assert.equal(await household.locator('[data-v83-ingredient] option').count(),3001,'The entire catalog is selectable');
 await household.locator('[data-v83-ingredient-search]').fill('Rice');await household.locator('[data-v83-ingredient]').selectOption('0');await household.locator('[data-v83-exclude]').click();
 await panel.locator('[data-v83-add]').click();
 const member=panel.locator('details[data-v83-profile]').first();
 await member.locator('[data-v83-field=name]').fill('Alex');await member.locator('[data-v83-field=icon]').selectOption('star');await member.locator('[data-v83-field=diet]').selectOption('omnivore');
 await member.locator('.v83-target-section>summary').click();await member.locator('[data-v83-field=calorieTarget]').fill('800');
 await member.locator('.v83-excluded-chip button[aria-label$="Rice"]').click();
 await member.locator('.v83-ingredient-picker>summary').click();await member.locator('[data-v83-ingredient-search]').fill('Tomato');await member.locator('[data-v83-ingredient]').selectOption('0');await member.locator('[data-v83-exclude]').click();
 await panel.locator('#preferences').fill('Quick dinners');
 await page.evaluate(()=>window.panel._renderTab());assert.equal(await member.locator('[data-v83-field=name]').inputValue(),'Alex');assert.equal(await member.locator('[data-v83-field=calorieTarget]').inputValue(),'800');assert.equal(await panel.locator('#preferences').inputValue(),'Quick dinners');
 await page.evaluate(()=>window.failProfiles=true);await panel.locator('[data-v83-save]').click();await page.waitForFunction(()=>!window.panel._v83Saving);assert.ok((await panel.locator('[data-v83-status]').innerText()).includes('Save failed'));
 await panel.locator('[data-v83-save]').click();await page.waitForFunction(()=>window.profiles?.members[0]?.name==='Alex'&&!window.panel._v83Saving);
 const saved=await page.evaluate(()=>window.profiles);assert.equal(saved.household.diet,'vegan');assert.equal(saved.members[0].diet,'omnivore');assert.equal(saved.members[0].icon,'star');assert.equal(saved.household.excludedIngredients[0].ingredientId,'food-0');assert.equal(saved.members[0].excludedIngredients[0].ingredientId,'food-2999');assert.deepEqual(saved.household.excludedTerms,['nuts','onion']);
 for(const lang of ['en','de','el']){
  await page.setViewportSize({width:360,height:740});await page.evaluate(lang=>{window.panel._hass.language=lang;window.panel._renderTab();},lang);
  assert.ok(await panel.locator('[data-v78-section=food]').evaluate(el=>el.scrollWidth<=el.clientWidth+1),'Profiles fit mobile '+lang);
 }
 if(process.env.COOK4ME_SCREENSHOT_DIR)await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+'/v83-profiles-mobile.png'});
 await page.setViewportSize({width:1280,height:900});await page.evaluate(()=>{window.panel._hass.language='en';window.panel._renderTab();});
 const choose=async source=>{await panel.locator('[data-filter=dietProfile]').click();const dialog=panel.locator('[data-filter-dialog=dietProfile]');await dialog.locator('select').selectOption(source);await dialog.locator('[data-apply]').click();};
 await panel.locator('#tabs [data-tab=today]').click();
 assert.equal(await panel.locator('.v83-controls .rx-shared-filters button').count(),8);
 await choose('member:'+saved.members[0].id);
 let filters=await page.evaluate(()=>window.panel._filters());assert.equal(filters.diet,'omnivore');assert.equal(Number(filters.calorieTarget),800);assert.equal(filters.excludedIngredients[0].ingredientId,'food-2999');
 assert.ok((await panel.locator('[data-filter=dietProfile]').getAttribute('aria-label')).includes('Alex'));
 await panel.locator('[data-filter=diet]').click();await panel.locator('[data-filter-dialog=diet] [data-field=diet]').selectOption('vegetarian');await panel.locator('[data-filter-dialog=diet] [data-apply]').click();
 filters=await page.evaluate(()=>window.panel._filters());assert.equal(filters.dietProfile,'manual');assert.equal(filters.diet,'vegetarian');assert.equal(Number(filters.calorieTarget),800);assert.equal(filters.excludedIngredients[0].ingredientId,'food-2999');
 await choose('household');await panel.locator('[data-filter=diet]').click();await panel.locator('[data-filter-dialog=diet] [data-apply]').click();assert.equal(await page.evaluate(()=>window.panel._filters().dietProfile),'household','Applying unchanged values keeps profile');
 await panel.locator('[data-filter=nutrition]').click();await panel.locator('[data-filter-dialog=nutrition] [data-field=calorieTarget]').fill('650');await panel.locator('[data-filter-dialog=nutrition] [data-apply]').click();assert.equal(await page.evaluate(()=>window.panel._filters().dietProfile),'manual');assert.equal(await page.evaluate(()=>window.panel._filters().calorieTarget),'650');
 await choose('household');await panel.locator('[data-filter=diet]').click();await panel.locator('[data-filter-dialog=diet] .v83-excluded-chip button[aria-label$="Rice"]').click();await panel.locator('[data-filter-dialog=diet] [data-apply]').click();assert.equal(await page.evaluate(()=>window.panel._filters().dietProfile),'manual');assert.equal(await page.evaluate(()=>window.panel._filters().excludedIngredients.length),0);
 for(const tab of ['today','week','official']){
  await panel.locator(`#tabs [data-tab=${tab}]`).click();assert.equal(await panel.locator('.v83-controls .rx-shared-filters').count(),1,tab+' merges controls');
  const rects=await panel.locator('.v83-controls').evaluate(el=>{const bar=el.querySelector('.rx-shared-filters').getBoundingClientRect(),action=el.querySelector('#todaySuggest,#generateWeek,#searchBtn').getBoundingClientRect();return {bar:bar.y,action:action.y};});assert.ok(Math.abs(rects.bar-rects.action)<50,tab+' controls share desktop row');
  for(const width of [390,360]){await page.setViewportSize({width,height:740});assert.ok(await panel.locator('.v83-controls').evaluate(el=>el.scrollWidth<=el.clientWidth+1),tab+' toolbar fits '+width);}
  await page.setViewportSize({width:1280,height:900});
 }
 if(process.env.COOK4ME_SCREENSHOT_DIR)await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+'/v83-search-toolbar.png'});
 await choose('member:'+saved.members[0].id);
 await page.evaluate(async()=>{await window.panel._api('cook4me/v31/recipe_detail',{entry_id:'one',variant_id:'r1'});});
 assert.equal(await page.evaluate(()=>window.calls.filter(c=>c.type.endsWith('/recipe_detail')).at(-1).shared_filters.dietProfile),'member:'+saved.members[0].id);
 await page.evaluate(()=>{window.delayDetail=true;window.oldDetail=window.panel._api('cook4me/v31/recipe_detail',{entry_id:'one',variant_id:'r1'}).then(()=>false,()=>true);});await choose('household');await page.evaluate(()=>window.releaseDetail({title:'Old member recipe'}));assert.equal(await page.evaluate(()=>window.oldDetail),true,'Late detail is rejected after selecting another profile');
 // Server-proven exclusions are required even when the diet itself is unchanged.
 assert.equal(await page.evaluate(()=>window.panel._v76Allowed({match:{safe:true,diet:'vegan',dietCheckVersion:76}})),false);
 assert.equal(await page.evaluate(()=>window.panel._v76Allowed({match:{safe:true,diet:'vegan',dietCheckVersion:76,dietRulesSignature:window.panel._v83RulesSignature()}})),true);
 // A cancelled filter dialog must not turn a later profile edit into Manual.
 await choose('member:'+saved.members[0].id);await panel.locator('[data-filter=diet]').click();await panel.locator('[data-filter-dialog=diet] [data-close]').click();
 await panel.locator('#tabs [data-tab=profile]').click();await panel.locator('[data-v78-pane=food]').click();await member.locator('[data-v83-field=calorieTarget]').fill('900');await panel.locator('[data-v83-save]').click();await page.waitForFunction(()=>!window.panel._v83Saving);
 assert.equal(await page.evaluate(()=>window.panel._filters().dietProfile),'member:'+saved.members[0].id);assert.equal(await page.evaluate(()=>Number(window.panel._filters().calorieTarget)),900);
 await panel.locator('#tabs [data-tab=official]').click();
 // Removing a selected person switches to Manual and keeps the last explicit filters.
 await choose('member:'+saved.members[0].id);await panel.locator('#tabs [data-tab=profile]').click();await panel.locator('[data-v78-pane=food]').click();await panel.locator('details[data-v83-profile] [data-v83-remove]').click();await panel.locator('[data-v83-save]').click();await page.waitForFunction(()=>!window.panel._v83Saving&&window.profiles.members.length===0);assert.equal(await page.evaluate(()=>window.panel._filters().dietProfile),'manual');
 await panel.locator('#preferences').fill('Private draft');await page.evaluate(()=>{window.panel._hass.user={id:'bob'};window.panel._renderTab();});assert.equal(await panel.locator('#preferences').inputValue(),'Quick dinners');
 await page.evaluate(()=>window.panel.remove());assert.deepEqual(errors,[]);
 console.log('v83 browser: merged toolbars, full catalog exclusions, independent profiles, all nutrient targets, save/retry/drafts, manual reset, mobile layouts, stale detail rejection and account isolation passed');
}finally{await browser.close();}
