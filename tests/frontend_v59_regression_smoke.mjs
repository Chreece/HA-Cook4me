import {parseHTML} from "linkedom";

const {window}=parseHTML("<!doctype html><html><body></body></html>");
for(const key of [
  "document","customElements","HTMLElement","Node","Event","CustomEvent",
  "MutationObserver","Element","ShadowRoot","HTMLInputElement","HTMLSelectElement",
])if(window[key])globalThis[key]=window[key];
globalThis.window=window;
if(!globalThis.navigator)Object.defineProperty(globalThis,"navigator",{value:window.navigator||{language:"en"},configurable:true});
globalThis.requestAnimationFrame=callback=>setTimeout(()=>callback(Date.now()),0);
globalThis.cancelAnimationFrame=id=>clearTimeout(id);
globalThis.requestIdleCallback=callback=>setTimeout(()=>callback({didTimeout:false,timeRemaining:()=>10}),1);
globalThis.cancelIdleCallback=id=>clearTimeout(id);
globalThis.ResizeObserver=class{observe(){} unobserve(){} disconnect(){}};
globalThis.CSS=globalThis.CSS||{escape:value=>String(value).replace(/[^a-zA-Z0-9_-]/g,"\\$&")};

const storage=new Map();
const reads=[];
globalThis.localStorage={
  getItem:key=>{reads.push(String(key));return storage.get(String(key))??null;},
  setItem:(key,value)=>storage.set(String(key),String(value)),
  removeItem:key=>storage.delete(String(key)),
  clear:()=>storage.clear(),
};

const user="v59-user";
storage.set(`cook4me.ui.snapshot.v54.${user}`,"{"+"x".repeat(500000)+"}");
storage.set(`cook4me.ui.shell.v2.${user}`,JSON.stringify({
  version:2,savedAt:1,selectedEntryId:"entry",
  entries:[{entry_id:"entry",title:"Cook4Me",connected:true,canAcceptRecipe:true}],
  perEntry:{entry:{
    uiPreferences:{lastTab:"today",catalogLanguage:"auto",translateResults:false},
    todayOptions:{languages:[{code:"de",country:"DE"}],defaultLanguage:"de"},
    todayResults:[{title:"Cached Today",searchVariantId:"r1",cover:"https://example.test/a.jpg",todayCatalogLanguage:"de",nutrition:{perServing:{energyKcal:123,protein:5,carbohydrates:12,fat:3,fiber:4},coverage:.9,estimated:true}}],
    todayMeta:{date:"2026-09-09",catalogMode:"release_offline"},
  }},fullOverviewCached:false,
}));

await import("../custom_components/cook4me/frontend/cook4me-panel-v59.js");
const tag="cook4me-recipe-hub-panel-v59";
if(!customElements.get(tag))throw new Error(`${tag} was not registered`);

const calls=[];let eventHandler=null;
const connection={
  sendMessagePromise:async message=>{calls.push(message);return {items:[]};},
  subscribeEvents:async callback=>{eventHandler=callback;return async()=>{};},
};
const panel=document.createElement(tag);
panel.hass={language:"en",user:{id:user},states:{},connection};
await new Promise(resolve=>setTimeout(resolve,5));

if(reads.some(key=>key===`cook4me.ui.snapshot.v54.${user}`))throw new Error("v59 synchronously read the legacy rich snapshot");
if(panel._tab!=="today")throw new Error(`Remembered tab was not restored: ${panel._tab}`);
if(panel._todayResults?.[0]?.title!=="Cached Today")throw new Error("Compact cached Today card was not restored before async hydration");

panel._entries=[{entry_id:"entry",title:"Cook4Me",connected:true,canAcceptRecipe:true}];
panel._entryId="entry";
panel._capabilities={deviceCatalogLanguage:"de",ingredientCatalogLanguage:"de",defaultAiTaskAvailable:true};
panel._todayOptions={languages:[{code:"de",country:"DE"}],defaultLanguage:"de"};
panel._todayResults=[{
  title:"Heavy Today",searchVariantId:"r2",cover:"https://example.test/b.jpg",todayCatalogLanguage:"de",
  steps:Array.from({length:200},(_,i)=>({instruction:`step-${i}-${"x".repeat(200)}`})),
  ingredients:Array.from({length:80},(_,i)=>({name:`ingredient-${i}`,provenance:{blob:"x".repeat(500)}})),
  nutrition:{perServing:{energyKcal:500,protein:20,carbohydrates:50,fat:15,fiber:8},coverage:.93,estimated:true},
}];
panel._todayMeta={date:"2026-09-09",catalogMode:"release_offline"};
panel._persistUiSnapshot();
const shell=storage.get(`cook4me.ui.shell.v2.${user}`)||"";
if(shell.length>120000)throw new Error(`Synchronous shell exceeded hard bound: ${shell.length}`);
if(shell.includes('"steps"')||shell.includes('"ingredients"'))throw new Error("Heavy recipe detail leaked into synchronous shell cache");

panel._renderShell();
const token=panel._processStart("Cook4Me · Today","Preparing");
if(!panel.shadowRoot.querySelector(".rx-v59-op"))throw new Error("Non-blocking operation card was not rendered");
if(panel.shadowRoot.querySelector(".rx-overlay")||panel.shadowRoot.querySelector("#processCancel"))throw new Error("Blocking/fake-cancel process UI survived in v59");
await panel._api("cook4me/v18/today_suggest",{entry_id:"entry",languages:["de"]});
const last=calls.at(-1);
if(last.type!=="cook4me/v30/today_suggest")throw new Error(`Today request was not routed to v30: ${last.type}`);
if(last.client_operation_id!==token.id)throw new Error("Client operation id was not attached to v30 request");

if(eventHandler){
  eventHandler({data:{operationId:token.id,phase:"nutrition",completed:7,total:10,message:"7/10",done:false,error:""}});
  const count=panel.shadowRoot.querySelector(".rx-v59-op-count")?.textContent||"";
  if(!count.includes("70%"))throw new Error(`Real progress did not update the same card: ${count}`);
}

const card=panel._recipeCard({
  title:"Nutrition card",searchVariantId:"r3",language:"de",sendable:true,ingredients:[],match:{safe:true,score:1},
  nutrition:{perServing:{energyKcal:500,protein:20,carbohydrates:50,fat:15,fiber:8},coverage:.93,estimated:true},
},false);
if(!card.includes("Fibre")||!card.includes("93%"))throw new Error(`Compact nutrition coverage/fibre missing: ${card}`);

const detail=panel._detailHtml({
  title:"Official nutrition",searchVariantId:"r4",language:"de",ingredients:[],steps:[],sendable:true,match:{safe:true,score:1},
  officialNutrition:{
    energyPer100gValue:123,
    hierarchicalNutrients:[{path:["Carbohydrates","Sugars"],valuePer100g:4.2,unit:{abbreviation:"g"}}],
    nutrients:[{key:"FAT",quantity:7.3,unit:{abbreviation:"g"},basis:"unspecified"}],
  },
});
if(!detail.includes("Official SEB nutrition")||!detail.includes("basis not specified by SEB"))throw new Error("Official SEB nutrition was not rendered as a separate evidence block");

panel._processEnd(token);
console.log("Recipe Hub v59 bounded cache + offline routing + progress + nutrition smoke OK");
