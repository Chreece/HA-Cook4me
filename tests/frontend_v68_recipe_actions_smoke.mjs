import {spawnSync} from "node:child_process";
import assert from "node:assert/strict";
import {parseHTML} from "linkedom";
const {window}=parseHTML("<!doctype html><html><body></body></html>");
for(const key of ["document","customElements","HTMLElement","Node","Event","CustomEvent","MutationObserver","Element","ShadowRoot","HTMLInputElement","HTMLSelectElement"])if(window[key])globalThis[key]=window[key];
globalThis.window=window;
globalThis.requestAnimationFrame=callback=>setTimeout(callback,0);
globalThis.cancelAnimationFrame=clearTimeout;
globalThis.ResizeObserver=class{observe(){} disconnect(){}};
globalThis.CSS={escape:String};
// Linkedom exposes select.value as getter-only; browsers provide this setter.
const selectValue=Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype,"value");
Object.defineProperty(window.HTMLSelectElement.prototype,"value",{configurable:true,get:selectValue.get,set(value){for(const option of this.options)option.selected=option.value===String(value);}});
const storage=new Map();
globalThis.localStorage={getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)};

const version=process.env.COOK4ME_TEST_PANEL_VERSION||"68";
await import(`../custom_components/cook4me/frontend/cook4me-panel-v${version}-bundle.js`);
const panel=document.createElement(`cook4me-recipe-hub-panel-v${version}`),requests=[];
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
const make=(i,language="de")=>({id:`r${i}`,displayFamilyId:`family:${i}`,displayVariantId:`${i}-${language}-4`,searchVariantId:`${i}-${language}-4`,sendVariantId:language==="de"?`${i}-de-4`:null,title:`Garden recipe ${i}`,canonicalName:`Garden recipe ${i}`,cover:`https://example.test/${i}.jpg`,language,selectedLanguage:language,selectedServings:4,servings:4,
 ingredients:[{ingredientId:"carrot",key:"carrot",name:"Karotte",originalName:"Karotte",displayName:"Καρότο",quantity:200,unit:"g"}],
 steps:[{functionalId:"s0",stepIndex:0,instruction:"Prepare vegetables"},{functionalId:"s1",stepIndex:1,instruction:"Cook vegetables"}],
 catalogNutrition:{perServing:{energyKcal:1000,proteinG:25,carbohydrateG:26,fatG:7,fiberG:2.5,saltG:0,sugarsG:null},coverage:{coveragePercent:40}},
 dietary:{vegan:true,vegetarian:true,pescatarian:true},mealTypes:["main"],
 match:{safe:true,dietary:{vegan:true,vegetarian:true,pescatarian:true},quantityAvailability:[{key:"carrot",name:"Karotte",coverage:0.5,status:"shortage",missingQuantity:100,missingUnit:"g"}],quantityShortages:[{key:"carrot",name:"Karotte",missingQuantity:100,missingUnit:"g"}]},
 languageVariants:["de","en","fr"].map(code=>({language:code,servingVariants:[4,6].map(servings=>({displayVariantId:`${i}-${code}-${servings}`,sendVariantId:code==="de"?`${i}-de-${servings}`:null,servings,label:String(servings)}))}))});
const all=Array.from({length:19},(_,i)=>make(i));
const filters={diet:"vegetarian",languages:["de","en","fr"],mealTypes:["breakfast","starter","salad","soup","main","side","dessert","snack"],ingredients:[],nutritionGoal:"balanced",onlyHome:false,maxCost:"",currency:"EUR"};
const capsRun=spawnSync("python",["tests/test_recipe_actions_v68.py","--capabilities"],{encoding:"utf8"});
assert.equal(capsRun.status,0,capsRun.stderr);const liveCaps=JSON.parse(capsRun.stdout).active;
const connection={sendMessagePromise:async msg=>{
 requests.push(msg);
 if(msg.type.endsWith("/capabilities"))return liveCaps;
 if(msg.type.endsWith("ui_preferences"))return {lastTab:"official",filters};
 if(msg.type.endsWith("official_search"))return {items:structuredClone(all.slice(msg.page*8,(msg.page+1)*8)),page:{number:msg.page,size:8,totalElements:all.length}};
 if(msg.type.endsWith("recipe_detail")){
  const [id,language,servings]=msg.variant_id.split("-");const row=make(Number(id),language);
  Object.assign(row,{displayVariantId:msg.variant_id,searchVariantId:msg.variant_id,sendVariantId:language==="de"?msg.variant_id:null,servings:Number(servings),selectedServings:Number(servings),presentationLanguage:"el"});row.ingredients[0].quantity=Number(servings)*50;return row;
 }
 if(msg.type.endsWith("ingredient_info"))return {ingredientInfoContract:"offline-ingredient-info-v62",ingredient:{name:"Καρότο"},officialRecipeUsage:structuredClone(all)};
 if(msg.type.endsWith("send_multi"))return {targetCount:1,sentCount:0,queuedCount:1};
 if(msg.type.endsWith("recipe_translation"))return {available:true,recipe:{...msg.recipe,title:"Συνταγή κήπου",translatedTo:"el",steps:msg.recipe.steps.map((step,i)=>({...step,instruction:["Ετοιμάστε τα λαχανικά","Μαγειρέψτε τα λαχανικά"][i]}))}};
 return {};
}};
panel._entryId="one";panel._entries=[{entry_id:"one",title:"Kitchen",connected:false,state:{},profile:{houseIngredients:[]},recipes:[]},{entry_id:"two",title:"Second device",connected:false,state:{},recipes:[]}];
panel._hass={language:"el",config:{country:"DE"},user:{id:"user"},states:{},connection};
panel._capabilities={languages:filters.languages.map(code=>({code})),deviceCatalogLanguage:"de"};
panel._loadWeekState=async()=>{};panel._requestSection=async()=>{};panel._loadRecipeNutrition=async()=>{};panel._loadOverview=async()=>{};panel._loadIngredientCatalog=async()=>{};
panel._renderShell();await panel._restorePreferences();panel._tab="official";await panel._search("garden");
const content=()=>panel.shadowRoot.querySelector('#content'),card=()=>content().querySelector('article.recipe');
// Exercise the queued modernizer: these passed synchronously in v67 but were
// replaced again during the later DOM pass on the user's browser.
for(const tab of ['today','week','official','book']){
 panel._tab=tab;panel._renderTabs();panel._modernizeSoon();await tick();
 const week=panel.shadowRoot.querySelector('[data-tab=week]');
 assert.ok(week.querySelector('svg[data-v67-week-icon]'),`Calendar after deferred pass on ${tab}`);
 assert.equal(week.querySelector('ha-icon[icon="mdi:circle-small"]'),null);
 const before=week.innerHTML;panel._modernizeTabs();assert.equal(week.innerHTML,before,'Decorator is idempotent');
}
panel._tab='official';panel._renderTab();panel._modernizeSoon();await tick();
let send=card().querySelector('[data-v66-action=send]');
assert.equal(send.querySelectorAll('ha-icon').length,1);assert.equal(send.querySelector('ha-icon').getAttribute('icon'),'mdi:send');
assert.equal(panel._resourceHasData('capabilities'),false,'Old cached capabilities need refreshing');
panel._hass.states['ai_task.local']={state:'unknown'};
panel._allowResource('capabilities');await panel._loadCapabilities();
assert.ok(requests.some(msg=>msg.type==='cook4me/v11/capabilities'));
assert.ok(panel._v66LocalAiAvailable());assert.ok(card().querySelector('[data-v66-action=translate]'));
assert.equal(requests.filter(msg=>msg.type.endsWith('recipe_translation')).length,0);
card().querySelector('[data-v66-action=translate]').click();await tick();
assert.equal(card().querySelector('h3').textContent.includes('Συνταγή κήπου'),true);
card().querySelector('[data-v66-action=expand]').click();await tick();
assert.ok(card().textContent.includes('Ετοιμάστε τα λαχανικά'),'Translated steps survive expansion');
// The fullscreen copy and the corresponding result both change immediately.
await panel._showRecipe(panel._results[1]);await tick();
let dialog=panel.shadowRoot.querySelector('[data-recipe-dialog]');
panel._modernizeSoon();await tick();
assert.equal(dialog.querySelector('[data-v66-action=send]').querySelectorAll('ha-icon').length,1);
dialog.querySelector('[data-v66-action=translate]').click();await tick();
dialog=panel.shadowRoot.querySelector('[data-recipe-dialog]');
assert.ok(dialog.querySelector('h2').textContent.includes('Συνταγή κήπου'));
assert.ok(dialog.querySelector('.rx-v66-steps').textContent.includes('Μαγειρέψτε τα λαχανικά'));
assert.equal(panel._results[1].title,'Συνταγή κήπου');
panel._v63CloseRecipe();
// Real shopping action retains source language metadata and passes UI language.
card().querySelector('[data-v66-action=shopping]').click();await tick();
const shopping=requests.findLast(msg=>msg.type.endsWith('/shopping_add'));
assert.equal(shopping.ui_language,'el');assert.equal(shopping.ingredients[0].originalName,'Karotte');
assert.equal(shopping.ingredients[0].quantity,100);assert.equal(shopping.ingredients[0].unit,'g');
await panel._addPlanShopping();assert.equal(requests.findLast(msg=>msg.type.endsWith('/week_add_shopping')).ui_language,'el');
// Availability changes arrive through the actual HA setter, no manual refresh.
panel.hass={...panel._hass,states:{'ai_task.local':{state:'unavailable'}}};await tick();
assert.equal(content().querySelector('[data-v66-action=translate]'),null);
panel.hass={...panel._hass,states:{'ai_task.local':{state:'unknown'}}};await tick();
assert.ok(content().querySelector('[data-v66-action=translate]'));
panel.disconnectedCallback();console.log('v68 active capabilities, deferred icons, title/steps translation and shopping actions passed');process.exit(0);
