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

const lastSectionKey="cook4me.ui.lastSection.v1.smoke-user";
store.set(lastSectionKey,"official");

await import("../custom_components/cook4me/frontend/cook4me-panel-v41.js");

const tag="cook4me-recipe-hub-panel-v41";
if(!customElements.get(tag))throw new Error(`${tag} was not registered`);
const panel=document.createElement(tag);
document.body.appendChild(panel);
panel.hass={
  language:"en",
  user:{id:"smoke-user"},
  connection:{sendMessagePromise:async()=>({entries:[]})},
};
await new Promise(resolve=>setTimeout(resolve,0));

if(!panel.shadowRoot)throw new Error("Recipe Hub did not create a shadow root");
for(const selector of ["#status","#tabs","#content","#refresh","#cook4meUiLanguage","#cook4meV38Styles","#cook4meV39Styles"]){
  if(!panel.shadowRoot.querySelector(selector))throw new Error(`Recipe Hub runtime smoke missing ${selector}`);
}
if(!panel.shadowRoot.querySelector(".top.rx-v38-top"))throw new Error("Unified top bar was not applied");
const refresh=panel.shadowRoot.querySelector("#refresh");
if(refresh.children.length!==1){
  const tags=[...refresh.children].map(node=>`${node.tagName}:${node.getAttribute?.("icon")||""}`).join(",");
  throw new Error(`Refresh control leaked ${refresh.children.length} children [${tags}] html=${refresh.innerHTML}`);
}
if(String(refresh.firstElementChild?.tagName||"").toUpperCase()!=="HA-ICON")throw new Error("Refresh control direct child is not HA-ICON");

if(panel._tab!=="official")throw new Error(`Last section was not restored; got ${panel._tab}`);
panel._tab="mine";
panel._renderTabs();
panel._renderTab();
if(store.get(lastSectionKey)!=="mine")throw new Error(`Section render was not remembered; got ${store.get(lastSectionKey)}`);

// Render the real Today planner and let every queued v30/v32 modernization pass
// finish. This catches the exact regression where v34's literal <ha-icon> and
// the global modernizer both decorated Suggest/Reset.
panel._entries=[{
  entry_id:"smoke-entry",
  title:"Cook4Me",
  connected:true,
  canAcceptRecipe:true,
  state:{phase:"idle"},
  profile:{diet:"vegetarian",houseIngredients:[]},
  recipes:[],
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

for(const [id,expected] of [["todaySuggest","mdi:chef-hat"],["todayReset","mdi:backup-restore"]]){
  const button=panel.shadowRoot.querySelector(`#${id}`);
  if(!button)throw new Error(`Today smoke missing #${id}`);
  const icons=[...button.children].filter(node=>String(node.tagName||"").toUpperCase()==="HA-ICON");
  if(icons.length!==1)throw new Error(`${id} leaked ${icons.length} direct icons html=${button.innerHTML}`);
  if(icons[0].getAttribute("icon")!==expected)throw new Error(`${id} has ${icons[0].getAttribute("icon")} instead of ${expected}`);
  if(!icons[0].classList.contains("rx-leading-icon"))throw new Error(`${id} icon is not marked for the inherited modernizer`);
}
if(panel.shadowRoot.querySelector("#todayReset").children.length!==1)throw new Error("Today Reset must remain icon-only");

const picker=panel.shadowRoot.querySelector("details.rx-today-picker");
const advanced=panel.shadowRoot.querySelector("details.rx-advanced");
if(!picker||!advanced)throw new Error("Today popup controls missing from outside-click smoke");
picker.setAttribute("open","");
advanced.setAttribute("open","");
panel._dismissOpenMenusFromPointer({composedPath:()=>[picker]});
if(!picker.hasAttribute("open"))throw new Error("Click inside a menu incorrectly closed that menu");
if(advanced.hasAttribute("open"))throw new Error("Click in another menu did not close the previously open menu");
advanced.setAttribute("open","");
document.body.dispatchEvent(new Event("pointerdown",{bubbles:true,composed:true}));
if(picker.hasAttribute("open")||advanced.hasAttribute("open"))throw new Error("Outside pointer did not close all Cook4Me menus");

panel._tab="mine";
panel._renderTabs();
panel._renderTab();
if(store.get(lastSectionKey)!=="mine")throw new Error("Final remembered section was not mine");
panel.remove();

const restored=document.createElement(tag);
document.body.appendChild(restored);
restored.hass={
  language:"en",
  user:{id:"smoke-user"},
  connection:{sendMessagePromise:async()=>({entries:[]})},
};
await new Promise(resolve=>setTimeout(resolve,0));
if(restored._tab!=="mine")throw new Error(`New panel did not reopen remembered section; got ${restored._tab}`);
restored.remove();

console.log("Recipe Hub v41 runtime smoke OK");
