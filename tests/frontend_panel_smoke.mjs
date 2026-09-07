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

await import("../custom_components/cook4me/frontend/cook4me-panel-v39.js");

const tag="cook4me-recipe-hub-panel-v39";
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
console.log("Recipe Hub v39 runtime smoke OK");
