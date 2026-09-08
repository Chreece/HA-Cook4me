import {parseHTML} from "linkedom";

const {window}=parseHTML("<!doctype html><html><body></body></html>");
for(const key of [
  "document","customElements","HTMLElement","Node","Event","CustomEvent",
  "MutationObserver","Element","ShadowRoot","HTMLInputElement","HTMLSelectElement",
]){
  if(window[key])globalThis[key]=window[key];
}
globalThis.window=window;
globalThis.requestAnimationFrame=(callback)=>setTimeout(()=>callback(Date.now()),0);
globalThis.cancelAnimationFrame=(id)=>clearTimeout(id);
globalThis.ResizeObserver=class{observe(){} unobserve(){} disconnect(){}};
globalThis.CSS=globalThis.CSS||{escape:value=>String(value).replace(/[^a-zA-Z0-9_-]/g,"\\$&")};
const storage=new Map();
globalThis.localStorage={
  getItem:key=>storage.get(String(key))??null,
  setItem:(key,value)=>storage.set(String(key),String(value)),
  removeItem:key=>storage.delete(String(key)),
};

await import("../custom_components/cook4me/frontend/cook4me-panel-v45.js");
const tag="cook4me-recipe-hub-panel-v45";
const panel=document.createElement(tag);
document.body.appendChild(panel);
panel.hass={
  language:"en",
  user:{id:"menu-smoke"},
  connection:{sendMessagePromise:async message=>{
    if(message?.type==="cook4me/v21/currency_state"){
      return {currency:"GBP",mode:"auto",defaultCurrency:"GBP",currencies:["EUR","GBP"],rates:{EUR:1,GBP:.8},rateDate:"2026-09-07"};
    }
    return {entries:[]};
  }},
};
await new Promise(resolve=>setTimeout(resolve,0));

panel._entries=[{
  entry_id:"menu-entry",title:"Cook4Me",connected:true,canAcceptRecipe:true,
  state:{phase:"idle"},profile:{diet:"vegetarian",houseIngredients:[]},recipes:[],
}];
panel._entryId="menu-entry";
panel._todayOptions={};
panel._ingredientCatalog=[{key:"M_FOOD_TOMATO",name:"Tomato"},{key:"M_FOOD_ONION",name:"Onion"}];
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
if(!content)throw new Error("Today content missing");

for(const group of ["meals","languages","ingredients"]){
  const menu=content.querySelector(`details[data-rx-picker="${group}"]`);
  if(!menu)throw new Error(`Today ${group} menu missing`);
  menu.setAttribute("open","");
  const before=menu;
  panel._toggleTodayBulk(content,group);
  const after=content.querySelector(`details[data-rx-picker="${group}"]`);
  if(after!==before||!after?.isConnected)throw new Error(`${group} bulk action rebuilt the open menu DOM`);
  if(!after.hasAttribute("open"))throw new Error(`${group} bulk action closed its menu`);
}

const advanced=content.querySelector("details.rx-advanced");
if(!advanced)throw new Error("More filters disclosure missing");
advanced.setAttribute("open","");
if(!advanced.querySelector(".rx-advanced-content"))throw new Error("More filters content missing");
if(!advanced.querySelector("#todayCalTolerance"))throw new Error("More filters did not retain calorie tolerance control");
if(!advanced.querySelector("#todayMaxMissing"))throw new Error("More filters did not retain max-missing control");
if(!advanced.querySelector("#todayRecent"))throw new Error("More filters did not retain recent-meal control");

const v45Style=panel.shadowRoot.getElementById("cook4meCurrencyV45")?.textContent||"";
if(!v45Style.includes(".rx-today-row>details.rx-advanced{overflow:visible!important")){
  throw new Error("v45 did not override inherited More filters clipping");
}

panel.remove();
console.log("Recipe Hub v45 Today menu smoke OK");
