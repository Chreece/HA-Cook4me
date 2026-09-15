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

import {spawnSync} from "node:child_process";
import {readFileSync,mkdtempSync,rmSync} from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";
const temp=mkdtempSync(join(tmpdir(),"cook4me-v64-flow-")),fixturePath=join(temp,"flow.json");
const backend=spawnSync("python",["tests/test_catalog_flow_v64.py","--fixture",fixturePath],{encoding:"utf8",timeout:120000});
assert.equal(backend.status,0,backend.stderr);
const fixture=JSON.parse(readFileSync(fixturePath,"utf8"));rmSync(temp,{recursive:true});
const version=process.env.COOK4ME_TEST_PANEL_VERSION||"64";
await import(`../custom_components/cook4me/frontend/cook4me-panel-v${version}-bundle.js`);
const panel=document.createElement(`cook4me-recipe-hub-panel-v${version}`);
const requests=[];let resolveToday;
const filters={...fixture.today.filters,ingredients:[],maxCost:"",onlyHome:false};
const connection={sendMessagePromise:async msg=>{
 requests.push(msg);
 if(msg.type.endsWith("ui_preferences"))return {lastTab:"today",filters};
 if(msg.type.endsWith("today_suggest"))return new Promise(resolve=>{resolveToday=resolve;});
 if(msg.type.endsWith("official_search"))return msg.query==="Ράμεν"?fixture.officialGreek:fixture.official;
 if(msg.type.endsWith("recipe_detail"))return fixture.ramenDetails[msg.variant_id]||{...fixture.today.items[0],steps:[{text:"Detailed cooking step"}]};
 return {};
}};
panel._entryId="entry";panel._entries=[{entry_id:"entry",title:"Cook4Me",profile:{houseIngredients:[]},recipes:[]}];
panel._hass={language:"el",user:{id:"user1"},states:{},connection};
panel._capabilities={languages:filters.languages.map(code=>({code})),deviceCatalogLanguage:"de"};
panel._requestSection=async()=>{};panel._loadRecipeNutrition=async()=>{};
panel._renderShell();await panel._restorePreferences();panel._tab="today";panel._renderTab();
const tick=()=>new Promise(resolve=>setTimeout(resolve,5));
// Click the actual Today button with five languages and all eight meal types.
panel.shadowRoot.querySelector("#todaySuggest").click();await tick();
const request=requests.findLast(row=>row.type.endsWith("today_suggest"));
assert.deepEqual(request.languages,filters.languages);assert.deepEqual(request.meal_types,filters.mealTypes);
assert.equal(request.group_by_meal_type,true);
assert.equal(requests.filter(row=>row.type.endsWith("today_suggest")).length,1);
const job=panel._v63Jobs.get(request.client_operation_id);assert.ok(job);
assert.equal(panel.shadowRoot.querySelector("#cook4meLoadStatus")?.textContent||"","");
assert.equal(panel._v63Jobs.size,1);
for(const event of fixture.events.filter(row=>row.operationId==="today-flow")){
 panel._v59HandleProgress({...event,operationId:job.id});
 assert.equal(job.ended,undefined,"No server phase completes the UI action early");
 assert.equal(panel._v63Jobs.size,1,"No blinking nested operation");
}
assert.ok(panel._todayBusy);assert.ok(job.card.parentNode);
resolveToday(fixture.today);await tick();
assert.equal(panel._todayBusy,false);assert.equal(job.ended,true);
assert.equal(panel.shadowRoot.querySelectorAll("#todayGrid article.recipe").length,fixture.today.items.length);
assert.equal(panel.shadowRoot.querySelectorAll(".rx-category-result").length,fixture.today.items.length);
assert.equal(panel.getAttribute("data-cook4me-build"),version==="65"?"2026.9.15.7":"2026.9.15.6");
assert.equal(panel.shadowRoot.querySelector("#cook4meLoadStatus")?.textContent||"","");
// The real Ramen response passes through Official's actual search/render path.
panel._tab="official";panel._renderTab();await panel._search("ramen");
assert.ok(panel._results.length>0);assert.ok(panel.shadowRoot.querySelectorAll("article.recipe").length>0);
assert.equal(panel.shadowRoot.querySelector("#cook4meLoadStatus")?.textContent||"","");
if(version==="65"){
 panel._ingredientCatalog=fixture.ingredientChoices;
 panel._showFilter("ingredients");
 const dialog=panel.shadowRoot.querySelector('[data-filter-dialog="ingredients"]'),input=dialog.querySelector("[data-ingredient-search]");
 for(const [query,name] of [["arroz","Ρύζι"],["cauliflower","Κουνουπίδι"],["κουνουπίδι","Κουνουπίδι"]]){
  input.value=query;input.dispatchEvent(new Event("input"));
  assert.ok([...dialog.querySelectorAll("[data-ingredient-choices] label")].some(label=>label.style.display!=="none"&&label.textContent===name),query);
 }
 dialog.querySelector("[data-close]").click();
 const latinIds=panel._results.map(row=>row.displayFamilyId);
 await panel._search("Ράμεν");assert.deepEqual(panel._results.map(row=>row.displayFamilyId),latinIds);
 assert.equal(panel._results.length,2);
 const regional=panel._results.find(row=>row.regionalPublications);
 assert.ok(regional);assert.equal(regional.publicationCount,5);
 await panel._selectRecipeLanguage(regional,"en",false);
 const selected=regional.displayVariantId;
 panel._recipeCard(regional,false);
 assert.equal(regional.displayVariantId,selected,"Rendering must not silently change display-only servings");
 assert.equal(regional.sendVariantId,null,"English edition must not acquire a German send identity");
 const html=document.createElement("div");html.innerHTML=panel._servingSelectHtml(regional);
 const ids=[...html.querySelectorAll("option")].map(option=>option.value);
 assert.equal(ids.length,3);assert.equal(new Set(ids).size,3);assert.ok(ids.every(Boolean));
 await panel._selectServing(regional,ids.find(id=>id!==selected),false);
 assert.notEqual(regional.displayVariantId,selected);
 assert.deepEqual(regional.ingredients,fixture.ramenDetails[regional.displayVariantId].ingredients);
 await panel._selectRecipeLanguage(regional,"de",false);
 html.innerHTML=panel._servingSelectHtml(regional);
 assert.equal(html.querySelectorAll("option").length,6);
 assert.ok(html.textContent.includes("Εκδοχή 1")&&html.textContent.includes("Εκδοχή 2"));
 for(const variant of ["316542","326387"]){
  await panel._selectServing(regional,variant,false);panel._recipeCard(regional,false);
  assert.equal(regional.displayVariantId,variant);
  assert.deepEqual(regional.ingredients,fixture.ramenDetails[variant].ingredients);
  assert.equal(regional.sendVariantId,fixture.ramenDetails[variant].sendVariantId);
 }
}
// An empty result has a visible explanation, and a failure is not success.
panel._tab="today";panel._renderTab();panel.shadowRoot.querySelector("#todaySuggest").click();await tick();
resolveToday({...fixture.today,items:[],emptyMealTypes:filters.mealTypes});await tick();
assert.ok(panel.shadowRoot.querySelector("[data-today-outcome]").textContent.includes("Δεν βρέθηκαν"));
const normal=connection.sendMessagePromise;
connection.sendMessagePromise=async msg=>{if(msg.type.endsWith("today_suggest"))throw new Error("Test connection failure");return normal(msg);};
panel.shadowRoot.querySelector("#todaySuggest").click();await tick();
assert.ok([...panel.shadowRoot.querySelectorAll(".rx-v59-op.bad")].some(node=>node.textContent.includes("Test connection failure")));
assert.equal(panel._todayBusy,false);
// Switching user/device before a response must not put that old plan on screen.
connection.sendMessagePromise=normal;panel.shadowRoot.querySelector("#todaySuggest").click();await tick();
panel._entryId="other-entry";resolveToday(fixture.today);await tick();assert.equal(panel._todayResults.length,0);
panel.disconnectedCallback();
console.log(`${fixture.official.items.length} ramen families; ${fixture.today.items.length} Today categories`);
console.log("v64 real catalog, Today button, Official ramen, progress, empty/error and stale response flows passed");
process.exit(0);
