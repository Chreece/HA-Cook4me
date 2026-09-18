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

const version=process.env.COOK4ME_TEST_PANEL_VERSION||"63";
await import(`../custom_components/cook4me/frontend/cook4me-panel-v${version}-bundle.js`);
const panel=document.createElement(`cook4me-recipe-hub-panel-v${version}`);
const requests=[];
let server={lastTab:"today",filters:{diet:"vegetarian",languages:["de"],mealTypes:["main"],ingredients:[],maxCost:"",onlyHome:false}};
const recipe={title:"Test rice",displayVariantId:"278301",searchVariantId:"278301",sendVariantId:"278301",sendGroupingFunctionalId:"3141015",language:"de",servings:4,ingredients:[{ingredientId:"rice",name:"Ρύζι",quantity:200,unit:"g"}],steps:[{text:"Cook the rice for 10 minutes."}],match:{safe:true},languageVariants:[{language:"de",servingVariants:[{displayVariantId:"278301",sendVariantId:"278301",servings:4},{displayVariantId:"278302",sendVariantId:"278302",servings:6}]}]};
const connection={sendMessagePromise:async msg=>{requests.push(msg);if(msg.type.endsWith("ui_preferences")){if(msg.preferences)server={...server,...msg.preferences};return server;}if(msg.type.endsWith("recipe_detail"))return {...recipe,displayVariantId:msg.variant_id,steps:[{text:`Steps for ${msg.variant_id}`} ]};if(msg.type.endsWith("official_search"))return {items:[recipe]};return {};}};
panel._entryId="entry";panel._entries=[{entry_id:"entry",title:"Cook4Me",profile:{houseIngredients:[]},recipes:[]}];
panel._hass={language:"el",user:{id:"user1"},states:{},connection};panel._capabilities={languages:[{code:"de"},{code:"fr"}],deviceCatalogLanguage:"de"};
panel._weekState={weekStart:"2026-09-14",slots:[{id:"slot",date:"2026-09-15",mealType:"dinner",recipe}],settings:{mealTypes:["dinner"]}};panel._weekStateEntry="entry";
if(Number(version)>=67){panel._v67Today=()=>"2026-09-15";panel._loadWeekState=async()=>{};}
panel._requestSection=async()=>{};panel._loadRecipeNutrition=async()=>{};
panel._renderShell();await panel._restorePreferences();
const tick=()=>new Promise(resolve=>setTimeout(resolve,5));
let controls;
for(const tab of ["today","week","official"]){
 panel._tab=tab;panel._renderTabs();panel._renderTab();
 const bar=panel.shadowRoot.querySelector(".rx-shared-filters");assert.ok(bar,tab);
 const keys=[...bar.querySelectorAll("button")].map(x=>x.dataset.filter);
 assert.equal(keys.length,7);if(controls)assert.deepEqual(keys,controls);controls=keys;
 assert.equal(panel.shadowRoot.querySelector('[data-tab="recommend"]'),null);
 if(Number(version)>=67)assert.ok(panel.shadowRoot.querySelector('[data-tab="week"] svg[data-v67-week-icon]'));else assert.equal(panel.shadowRoot.querySelector('[data-tab="week"] ha-icon').getAttribute("icon"),"mdi:calendar-week");
 assert.equal(panel.shadowRoot.querySelector("#officialCatalogLanguages"),null);
}
panel._tab="week";panel._renderTab();
panel.shadowRoot.querySelector(".rx-week-slot").dispatchEvent(new Event("click",{bubbles:true}));await tick();
assert.ok(panel.shadowRoot.querySelector("[data-recipe-dialog]"),"Weekly opens the common dialog");
assert.ok(panel.shadowRoot.querySelector("[data-recipe-dialog]").textContent.includes("Steps for 278301"));
assert.ok(panel.shadowRoot.querySelector("[data-detail-send]"),"Dialog includes recipe actions");
assert.equal(panel.shadowRoot.querySelectorAll("#recipeDetail").length,1);
panel.shadowRoot.querySelector("[data-modal-close]").click();
assert.equal(panel.shadowRoot.querySelector("[data-recipe-dialog]"),null);
for(const method of ["_openOfficial","_openLocal"]){await panel[method](recipe);assert.ok(panel.shadowRoot.querySelector("[data-recipe-dialog]"));panel._v63CloseRecipe();}
panel._showFilter("diet");
assert.ok(panel.shadowRoot.querySelector('[data-filter-dialog="diet"]'));
panel.shadowRoot.querySelector('[data-field="diet"]').value="vegan";
panel.shadowRoot.querySelector("[data-apply]").click();await tick();
assert.equal(server.filters.diet,"vegan");
panel.shadowRoot.querySelector('[data-tab="official"]').click();await tick();assert.equal(server.lastTab,"official");
await panel._search("ρύζι");
const search=requests.findLast(msg=>msg.type.endsWith("official_search"));assert.equal(search.shared_filters.diet,"vegan");assert.deepEqual(search.languages,["de"]);
assert.ok(panel.shadowRoot.querySelector(".rx-v63-progress"));assert.equal(panel.shadowRoot.querySelector("[data-v54-background]"),null);
const a=panel._processStart("A","First"),b=panel._processStart("B","Second");panel._processUpdate(a,"Still first",1,2);assert.ok(a.card.textContent.includes("Still first"));assert.ok(b.card.parentNode);panel._processEnd(a);assert.equal(panel._process,b);panel._processEnd(b);
assert.equal(panel._shouldTranslate(),false,"No implicit Ollama/AI translation");
// A second browser with empty local storage restores the server's menu and filters.
storage.clear();
const second=document.createElement(`cook4me-recipe-hub-panel-v${version}`);
second._entryId="entry";second._entries=panel._entries;second._hass=panel._hass;second._capabilities=panel._capabilities;
second._requestSection=async()=>{};second._renderShell();await second._restorePreferences();await tick();
assert.equal(second._tab,"official");assert.equal(second._filters().diet,"vegan");
// A delayed server read cannot overwrite a newer local navigation choice.
const normal=connection.sendMessagePromise;let releasePreferences;
connection.sendMessagePromise=msg=>msg.type.endsWith("ui_preferences")&&!msg.preferences?new Promise(resolve=>{releasePreferences=()=>resolve({lastTab:"today"});}):normal(msg);
second._v63PrefsLoaded="";const restoring=second._restorePreferences();
second._selectV52Tab("week");releasePreferences();await restoring;await tick();assert.equal(second._tab,"week");assert.equal(server.lastTab,"week");
connection.sendMessagePromise=normal;
// Serving changes refresh the same dialog; late responses cannot resurrect a closed one.
await panel._openOfficial(recipe);
await panel._selectServing(panel._opened,"278302",true);
assert.ok(panel.shadowRoot.querySelector("[data-recipe-dialog]").textContent.includes("Steps for 278302"));
assert.equal(panel.shadowRoot.querySelectorAll("[data-recipe-dialog]").length,1);
let releaseVariant;
connection.sendMessagePromise=msg=>msg.type.endsWith("recipe_detail")?new Promise(resolve=>{releaseVariant=()=>resolve({...recipe,displayVariantId:msg.variant_id});}):normal(msg);
const changing=panel._selectServing(panel._opened,"278301",true);panel._v63CloseRecipe();releaseVariant();await changing;
assert.equal(panel.shadowRoot.querySelector("[data-recipe-dialog]"),null);
const opening=panel._openOfficial(recipe);panel._selectV52Tab("today");releaseVariant();await opening;
assert.equal(panel.shadowRoot.querySelector("[data-recipe-dialog]"),null,"Navigation cancels stale dialog opening");
connection.sendMessagePromise=normal;
// Today and Weekly carry the exact same filter model as Official.
await panel._api("cook4me/v18/today_suggest",{entry_id:"entry",languages:["de"],meal_types:["main"]});
await panel._api("cook4me/v20/week_generate",{entry_id:"entry"});
assert.equal(requests.findLast(msg=>msg.type.endsWith("today_suggest")).shared_filters.diet,"vegan");
assert.equal(requests.findLast(msg=>msg.type.endsWith("week_generate")).shared_filters.diet,"vegan");
if(version==="65"){
 panel._ingredientCatalog=[{name:"Ρύζι",presentationVersion:63,displayLanguage:"el"}];
 assert.equal(panel._resourceHasData("catalog"),false);
 panel._discardOldCatalog();assert.deepEqual(panel._ingredientCatalog,[]);
 panel._ingredientCatalog=[{name:"Ρύζι",presentationVersion:63,displayLanguage:"el",searchAliases:["Rice","Arroz"]}];
 panel._discardOldCatalog();assert.equal(panel._resourceHasData("catalog"),true);
 assert.equal(panel._ingredientQueryMatches(panel._ingredientCatalog[0],"arroz"),true);
}
second.disconnectedCallback();
console.log("v63 shared controls, navigation, recipe dialogs and concurrent progress passed");
panel.disconnectedCallback();process.exit(0);
