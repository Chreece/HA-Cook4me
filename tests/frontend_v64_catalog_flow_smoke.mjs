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
await import("../custom_components/cook4me/frontend/cook4me-panel-v64-bundle.js");
const panel=document.createElement("cook4me-recipe-hub-panel-v64");
const requests=[];let resolveToday;
const filters={...fixture.today.filters,ingredients:[],maxCost:"",onlyHome:false};
const connection={sendMessagePromise:async msg=>{
 requests.push(msg);
 if(msg.type.endsWith("ui_preferences"))return {lastTab:"today",filters};
 if(msg.type.endsWith("today_suggest"))return new Promise(resolve=>{resolveToday=resolve;});
 if(msg.type.endsWith("official_search"))return fixture.official;
 if(msg.type.endsWith("recipe_detail"))return {...fixture.today.items[0],steps:[{text:"Detailed cooking step"}]};
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
assert.equal(panel.getAttribute("data-cook4me-build"),"2026.9.15.6");
assert.equal(panel.shadowRoot.querySelector("#cook4meLoadStatus")?.textContent||"","");
// The real Ramen response passes through Official's actual search/render path.
panel._tab="official";panel._renderTab();await panel._search("ramen");
assert.ok(panel._results.length>0);assert.ok(panel.shadowRoot.querySelectorAll("article.recipe").length>0);
assert.equal(panel.shadowRoot.querySelector("#cook4meLoadStatus")?.textContent||"","");
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
