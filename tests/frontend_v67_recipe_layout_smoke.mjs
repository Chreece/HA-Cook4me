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

const version=process.env.COOK4ME_TEST_PANEL_VERSION||"67";
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
const connection={sendMessagePromise:async msg=>{
 requests.push(msg);
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
const content=()=>panel.shadowRoot.querySelector("#content"),cards=()=>[...content().querySelectorAll("article.recipe")];
assert.equal(requests.findLast(msg=>msg.type.endsWith("official_search")).size,8);
assert.equal(cards().length,8);assert.ok(cards()[0].textContent.includes("(Γερμανικά)"));
assert.equal(cards()[0].querySelector(".rx-v66-body"),null);assert.ok(cards()[0].querySelectorAll("button").length>=7);
assert.ok(cards()[0].querySelector("[data-v66-photo]").nextElementSibling.classList.contains("rx-v67-photo-actions"));
assert.equal(cards()[0].querySelectorAll('[data-v66-action="send"]').length,1);
// Cooking mode works directly from a collapsed recipe and opens the viewport dialog.
cards()[0].querySelector('[data-v66-action="cook"]').click();await tick();
let cooking=panel.shadowRoot.querySelector("[data-v67-cooking]");assert.ok(cooking);
assert.ok(cooking.querySelector('[aria-current="step"]'));
assert.ok(cooking.querySelector(".rx-v67-photo-side .rx-v67-photo-actions [data-v66-action=send]"));
cooking.querySelector("[data-modal-close]").click();
content().querySelector("[data-load-more]").click();await tick();assert.equal(cards().length,16);
content().querySelector("[data-load-more]").click();await tick();assert.equal(cards().length,19);assert.equal(content().querySelector("[data-load-more]"),null);
await panel._search("new search");assert.equal(cards().length,8);
cards()[0].querySelector('[data-v66-action="expand"]').click();await tick();
assert.equal(cards()[0].querySelectorAll("details").length,3);
assert.equal(cards()[0].querySelector('.rx-v66-body [data-v66-action="send"]'),null);
assert.equal(cards()[0].querySelector('.rx-v67-nutrition h4').textContent,"Διατροφικά στοιχεία");
assert.equal(cards()[0].querySelector('[data-nutrient="energy"] [data-daily-percent]').dataset.dailyPercent,"50");
assert.equal(cards()[0].querySelector('[data-nutrient="protein"] [data-daily-percent]').dataset.dailyPercent,"50");
assert.equal(cards()[0].querySelector('[data-nutrient="salt"] [data-daily-percent]').dataset.dailyPercent,"0");
assert.equal(cards()[0].querySelector('[data-nutrient="sugars"]'),null);
assert.equal(panel._v67Dom(panel._v60NutritionChips({nutrition:{totals:{energyKcal:1000}}})).querySelector('[data-daily-percent]'),null);
assert.ok(cards()[0].textContent.includes("Καρότο (Karotte)"));assert.ok(cards()[0].textContent.includes("50%"));
assert.equal(cards()[0].querySelectorAll("[data-v66-device] option").length,2);
// Translation is absent for no AI, a cloud default, or unavailable local AI.
const translationCalls=()=>requests.filter(msg=>msg.type.endsWith("recipe_translation")).length;
assert.equal(cards()[0].querySelector('[data-v66-action="translate"]'),null);
panel._capabilities.defaultAiTaskAvailable=true;panel._renderTab();
assert.equal(cards()[0].querySelector('[data-v66-action="translate"]'),null);
panel._capabilities.localAiTaskEntityIds=["ai_task.local"];
panel._hass.states["ai_task.local"]={state:"unavailable"};panel._updateHeader();
assert.equal(cards()[0].querySelector('[data-v66-action="translate"]'),null);
panel._hass.states["ai_task.local"]={state:"ready"};panel._updateHeader();
assert.ok(cards()[0].querySelector('[data-v66-action="translate"]'));
assert.equal(translationCalls(),0,"Expansion and availability changes never translate automatically");
cards()[0].querySelector('[data-v66-action="translate"]').click();await tick();
assert.equal(translationCalls(),1);assert.equal(panel._results[0].translatedTo,"el");
assert.equal(cards()[0].querySelector('[data-v66-action="translate"]'),null);
panel._hass.states["ai_task.local"]={state:"unavailable"};
await panel._v66Translate(panel._results[1],panel._v66State(panel._results[1]));
assert.equal(translationCalls(),1,"The click handler also refuses unavailable local AI");
await panel._showIngredientInfo(panel._results[0].ingredients[0],panel._results[0]);
let ingredientDialog=panel.shadowRoot.querySelector("[data-ingredient-dialog]");
assert.equal(ingredientDialog.querySelectorAll("article.recipe").length,8);
ingredientDialog.querySelector("[data-usage-more]").click();assert.equal(ingredientDialog.querySelectorAll("article.recipe").length,16);
ingredientDialog.querySelector("[data-close]").click();
let inspected;panel._showIngredientInfo=async item=>{inspected=item;};cards()[0].querySelector("[data-v66-ingredient]").click();assert.equal(inspected.ingredientId,"carrot");
let shopping;panel._addShopping=async items=>{shopping=items;};cards()[0].querySelector('[data-v66-action="shopping"]').click();await tick();assert.ok(shopping.length);
const device=cards()[0].querySelector("[data-v66-device]");device.value="two";device.dispatchEvent(new Event("change"));
cards()[0].querySelector('[data-v66-action="send"]').click();await tick();
assert.deepEqual(requests.findLast(msg=>msg.type.endsWith("send_multi")).entry_ids,["two"]);
const servings=cards()[0].querySelector("[data-v66-servings]");servings.value="0-de-6";servings.dispatchEvent(new Event("change"));await tick();
assert.equal(panel._results[0].displayVariantId,"0-de-6");assert.equal(panel._results[0].translatedTo,undefined);assert.equal(panel._results[0].ingredients[0].quantity,300);
cards()[0].querySelector("[data-v66-photo]").click();await tick();
let dialog=panel.shadowRoot.querySelector("[data-v66-fullscreen]");assert.ok(dialog);assert.equal(dialog.querySelectorAll(".step").length,2);
panel._v66State(panel._opened).cooking=false;dialog.querySelector('[data-v66-action="cook"]').click();dialog=panel.shadowRoot.querySelector("[data-v66-fullscreen]");assert.equal(dialog.querySelector('[aria-current="step"]').dataset.v66Step,"0");
dialog.querySelector('[data-v66-action="next"]').click();dialog=panel.shadowRoot.querySelector("[data-v66-fullscreen]");assert.equal(dialog.querySelector('[aria-current="step"]').dataset.v66Step,"1");
panel._entries[0].state={variantFunctionalId:"0-de-6",stepIndex:0};panel._updateHeader();assert.equal(dialog.querySelector('[aria-current="step"]').dataset.v66Step,"0");
panel._entries[0].state={variantFunctionalId:"unrelated",stepIndex:0};panel._updateHeader();assert.equal(dialog.querySelector('[aria-current="step"]').dataset.v66Step,"1");
dialog.querySelector("[data-modal-close]").click();assert.equal(panel.shadowRoot.querySelector("[data-v66-fullscreen]"),null);
cards()[0].querySelector('[data-v66-tag="meal"]').click();await tick();assert.deepEqual(requests.findLast(msg=>msg.type.endsWith("official_search")).shared_filters.mealTypes,["main"]);assert.equal(cards().length,8);
// The same cap and expansion renderer applies to Today, saved lists and weekly slots.
panel._v66Tags=new Map();panel._todayResults=structuredClone(all);panel._todayMeta=null;panel._tab="today";panel._renderTab();assert.equal(cards().length,8);content().querySelector("[data-load-more]").click();await tick();assert.equal(cards().length,16);
panel._bookState={favorites:structuredClone(all),recipeList:[]};panel._tab="book";panel._renderTab();assert.equal(cards().length,8);content().querySelector("[data-load-more]").click();await tick();assert.equal(cards().length,16);
panel._entries[0].recipes=structuredClone(all).map(row=>({...row,source:"manual"}));panel._tab="mine";panel._renderTab();assert.equal(cards().length,8);
// All seven HA-local days are rendered, with all planned recipes and empty days.
const realToday=panel._v67Today.bind(panel);
panel._hass.config.time_zone="Europe/Berlin";
assert.equal(realToday(new Date("2026-09-15T22:30:00Z")),"2026-09-16");
panel._v67Today=()=>"2026-09-15";
panel._weekState={weekStart:"2026-09-07",settings:{},slots:all.map((recipe,i)=>({id:`slot${i}`,date:`2026-09-${15+i%7}`,mealType:"dinner",recipe:structuredClone(recipe)})),leftovers:[]};
panel._weekState.slots.push({id:"old",date:"2026-09-07",mealType:"dinner",recipe:make(30)});
panel._weekStateEntry="one";panel._tab="week";panel._renderTabs();panel._renderTab();
assert.equal(cards().length,19);assert.equal(content().querySelector('[data-load-more]'),null);
assert.deepEqual([...content().querySelectorAll('[data-week-date]')].map(day=>day.dataset.weekDate),["2026-09-15","2026-09-16","2026-09-17","2026-09-18","2026-09-19","2026-09-20","2026-09-21"]);
assert.equal(content().querySelector('[data-slot-id="old"]'),null);
assert.ok(panel.shadowRoot.querySelector('[data-tab="week"] svg[data-v67-week-icon]'));
panel._weekState.slots=[];panel._renderTab();assert.equal(content().querySelectorAll('[data-week-date]').length,7);assert.equal(content().querySelectorAll('.rx-v67-empty-day').length,7);
await panel._api("cook4me/v20/week_generate",{entry_id:"one",week_start:"2026-09-07"});
assert.equal(requests.findLast(msg=>msg.type.endsWith("week_generate")).week_start,"2026-09-15");
panel._v67Today=()=>"2026-09-16";panel._updateHeader();assert.equal(content().querySelector('[data-week-date]').dataset.weekDate,"2026-09-16");
panel._v67Today=()=>"2026-12-29";assert.equal(panel._v67Days().at(-1),"2027-01-04");
// An unpaged weekly view also applies edition preference beyond the first eight.
panel._hass.config.country="FR";const editions=Array.from({length:19},(_,i)=>make(100+i));
await panel._v66PreferLanguages(editions);assert.ok(editions.every(row=>row.language==="fr"));
panel._hass.config.country="DE";
// Language preference is UI, HA country, English, then actual catalog order.
assert.equal(panel._v66PreferredLanguage(make(0)),"de");panel._hass.config.country="FR";assert.equal(panel._v66PreferredLanguage(make(0)),"fr");panel._hass.config.country="XX";assert.equal(panel._v66PreferredLanguage(make(0)),"en");assert.equal(panel._v66PreferredLanguage({languageVariants:[{language:"pl"},{language:"it"}]}),"pl");panel._hass.language="fr";panel._hass.config.country="DE";assert.equal(panel._v66PreferredLanguage(make(0)),"fr");
assert.notEqual(panel._v66Key({id:"custom1",title:"My soup"}),panel._v66Key({id:"custom2",title:"My soup"}));
panel.disconnectedCallback();console.log("v67: visible actions, nutrient percentages, fullscreen cooking and rolling seven-day calendar passed");process.exit(0);
