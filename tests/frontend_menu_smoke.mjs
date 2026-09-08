import {parseHTML} from "linkedom";

const {window}=parseHTML("<!doctype html><html><body></body></html>");
for(const key of [
  "document","customElements","HTMLElement","Node","Event","CustomEvent",
  "MutationObserver","Element","ShadowRoot","HTMLInputElement","HTMLSelectElement",
]){
  if(window[key])globalThis[key]=window[key];
}
globalThis.window=window;
if(!globalThis.navigator){
  Object.defineProperty(globalThis,"navigator",{value:window.navigator||{language:"en"},configurable:true});
}
globalThis.requestAnimationFrame=(callback)=>setTimeout(()=>callback(Date.now()),0);
globalThis.cancelAnimationFrame=(id)=>clearTimeout(id);
globalThis.ResizeObserver=class{observe(){} unobserve(){} disconnect(){}};
globalThis.CSS=globalThis.CSS||{escape:value=>String(value).replace(/[^a-zA-Z0-9_-]/g,"\\$&")};
const store=new Map();
globalThis.localStorage={
  getItem:key=>store.has(String(key))?store.get(String(key)):null,
  setItem:(key,value)=>store.set(String(key),String(value)),
  removeItem:key=>store.delete(String(key)),
  clear:()=>store.clear(),
};

await import("../custom_components/cook4me/frontend/cook4me-panel-v48.js");
const tag="cook4me-recipe-hub-panel-v48";
if(!customElements.get(tag))throw new Error(`${tag} was not registered`);

const panel=document.createElement(tag);
document.body.appendChild(panel);
const sendMessagePromise=async message=>{
  if(message?.type==="cook4me/v21/currency_state"||message?.type==="cook4me/v21/currency_set"){
    return {currency:"GBP",mode:"auto",defaultCurrency:"GBP",currencies:["EUR","GBP","USD"],rates:{EUR:1,GBP:0.8,USD:1.2},rateDate:"2026-09-07",source:"ecb_reference_rates",stale:false};
  }
  return {entries:[]};
};
panel.hass={language:"en",user:{id:"menu-smoke"},connection:{sendMessagePromise}};
await new Promise(resolve=>setTimeout(resolve,0));

panel._entries=[{
  entry_id:"smoke-entry",title:"Cook4Me",connected:true,canAcceptRecipe:true,
  state:{phase:"idle"},profile:{diet:"vegetarian",houseIngredients:[]},recipes:[],
}];
panel._entryId="smoke-entry";
panel._todayOptions={};
panel._ingredientCatalog=[{key:"M_FOOD_SMOKE",name:"Tomato"}];
panel._ingredientCatalogLoading=false;
panel._todaySettings=panel._todayDefaults();
panel._todayResults=[];
panel._todayMeta=null;
panel._tab="today";
panel._renderTabs();
panel._renderTab();
await new Promise(resolve=>setTimeout(resolve,0));
await new Promise(resolve=>setTimeout(resolve,0));

const content=panel.shadowRoot.getElementById("content");
const languageMenu=content.querySelector('details[data-rx-picker="languages"]');
if(!languageMenu)throw new Error("Catalog languages menu missing when language rows are empty");

const advanced=content.querySelector("details.rx-advanced");
const advancedSummary=advanced?.querySelector(":scope > summary");
if(!advanced||!advancedSummary)throw new Error("More filters control missing");
if(advanced.hasAttribute("open"))throw new Error("More filters unexpectedly starts open");
advancedSummary.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
if(!advanced.hasAttribute("open"))throw new Error("Clicking More filters did not open the menu");
if(advancedSummary.getAttribute("aria-expanded")!=="true")throw new Error("More filters aria-expanded was not updated");
if(!advanced.querySelector("#todayCalTolerance")||!advanced.querySelector("#todayMaxMissing")||!advanced.querySelector("#todayRecent")){
  throw new Error("More filters opened without its filter controls");
}

const mealBulk=content.querySelector('[data-today-bulk="meals"]');
const mealMenu=mealBulk?.closest("details.rx-today-picker");
if(!mealBulk||!mealMenu)throw new Error("Meal Select all / Deselect all menu missing");
const mealSummary=mealMenu.querySelector(":scope > summary");
mealSummary.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
if(!mealMenu.hasAttribute("open"))throw new Error("Meal picker did not open");
if(advanced.hasAttribute("open"))throw new Error("Opening another picker did not close More filters");

// LinkeDOM does not initialize the .checked property from the HTML checked
// attribute exactly like browsers do. Normalize the runtime state explicitly
// so this smoke tests the real Deselect-all -> Select-all interaction.
const mealRows=[...content.querySelectorAll("[data-today-meal-type]")];
mealRows.forEach(row=>{row.checked=true;row.closest(".rx-choice-card")?.classList.add("selected");});
panel._refreshBulkButton(content,"meals");

const beforeNode=mealMenu;
mealBulk.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
if(beforeNode!==mealBulk.closest("details.rx-today-picker")||!beforeNode.isConnected){
  throw new Error("Bulk selection rebuilt the Today picker DOM");
}
if(!mealMenu.hasAttribute("open"))throw new Error("Deselect all closed the open meal picker");
if(mealRows.some(row=>row.checked))throw new Error("Deselect all did not clear meal selections");
if(!mealBulk.textContent.includes("Select all"))throw new Error("Bulk button label did not update after Deselect all");

mealBulk.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
if(!mealMenu.hasAttribute("open"))throw new Error("Select all closed the open meal picker");
if(!mealRows.every(row=>row.checked))throw new Error("Select all did not restore meal selections");
if(!mealBulk.textContent.includes("Deselect all"))throw new Error("Bulk button label did not update after Select all");

advancedSummary.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
if(!advanced.hasAttribute("open"))throw new Error("More filters did not reopen after using another picker");
advancedSummary.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
if(advanced.hasAttribute("open"))throw new Error("More filters did not close on second click");

panel.remove();
console.log("Recipe Hub v48 Today menu interaction smoke OK");
