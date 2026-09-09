import {parseHTML} from "linkedom";

const {window}=parseHTML("<!doctype html><html><body></body></html>");
for(const key of [
  "document","customElements","HTMLElement","Node","Event","CustomEvent",
  "MutationObserver","Element","ShadowRoot","HTMLInputElement","HTMLSelectElement",
]){
  if(window[key])globalThis[key]=window[key];
}
globalThis.window=window;
if(!globalThis.navigator){Object.defineProperty(globalThis,"navigator",{value:window.navigator||{language:"en"},configurable:true});}
globalThis.requestAnimationFrame=callback=>setTimeout(()=>callback(Date.now()),0);
globalThis.cancelAnimationFrame=id=>clearTimeout(id);
globalThis.ResizeObserver=class{observe(){} unobserve(){} disconnect(){}};
globalThis.CSS=globalThis.CSS||{escape:value=>String(value).replace(/[^a-zA-Z0-9_-]/g,"\\$&")};
const storage=new Map();
globalThis.localStorage={
  getItem:key=>storage.get(String(key))??null,
  setItem:(key,value)=>storage.set(String(key),String(value)),
  removeItem:key=>storage.delete(String(key)),
  clear:()=>storage.clear(),
};

await import("../custom_components/cook4me/frontend/cook4me-panel-v58.js");
const tag="cook4me-recipe-hub-panel-v58";
if(!customElements.get(tag))throw new Error(`${tag} was not registered`);

const calls=[];
const panel=document.createElement(tag);
panel._hass={
  language:"en",
  user:{id:"v58-user"},
  states:{},
  connection:{sendMessagePromise:async message=>{calls.push(String(message.type||""));return {items:[]};}},
};
panel._entries=[{
  entry_id:"entry",title:"Cook4Me",connected:true,canAcceptRecipe:true,loadedRecipe:null,
  state:{phase:"idle"},profile:{diet:"vegetarian",houseIngredients:[]},recipes:[],history:[],habitTerms:[],
}];
panel._entryId="entry";
panel._v51OverviewDone=true;
panel._v53BootstrapDone=true;
panel._v53FullOverviewDone=true;
panel._v54HasCachedFullOverview=true;
panel._v54HadUiCache=true;
panel._preferencesLoaded=true;
panel._capabilities={languages:[{code:"de",country:"DE"},{code:"en",country:"GB"}],deviceCatalogLanguage:"de",ingredientCatalogLanguage:"de",preferences:{}};
panel._todayOptions={languages:panel._capabilities.languages,defaultLanguage:"de",maxLanguages:8,mealTypes:["main"],nutritionGoals:["balanced"],dietOptions:["profile","vegetarian"]};
panel._bookState={favorites:[],recipeList:[],queuedSend:null};
panel._renderShell();

// Active v58 must route the inherited Today request to the fixed v29 endpoint.
await panel._api("cook4me/v18/today_suggest",{entry_id:"entry",languages:["de","en"]});
if(calls.at(-1)!=="cook4me/v29/today_suggest")throw new Error(`Today request was not routed to v29: ${JSON.stringify(calls)}`);

const recipe={
  title:"Cached image recipe",groupingFunctionalId:"g1",recipeFunctionalId:"r1",searchVariantId:"r1",
  language:"de",todayCatalogLanguage:"de",cover:"https://images.example.test/recipe-1.jpg",sendable:true,
  ingredients:[{foodKey:"TOMATO",foodName:"Tomato"}],steps:[{instruction:"Cook"}],match:{safe:true,score:100},
};
panel._results=[recipe];
panel._tab="official";
panel._renderTabs();
panel._renderTab();
const first=panel.shadowRoot.querySelector("#recipeGrid img.cover");
if(!first)throw new Error("Initial recipe image was not rendered");
first.dispatchEvent(new Event("load"));
if(first.dataset.cook4meV58Ready!=="1")throw new Error("Loaded recipe image was not marked reusable");

// Rendering a different section stashes the already-loaded image node. Recipe
// Book deliberately avoids LinkeDOM's incomplete writable <select>.value model
// while exercising the same inherited innerHTML section replacement path.
panel._tab="book";
panel._renderTabs();
panel._renderTab();
if(!panel._v58ImagePool.has(recipe.cover))throw new Error("Loaded image was not stashed before section replacement");

// Returning to the section must restore the exact same DOM image node, not
// create another lazy image and visibly reload/decode it.
panel._tab="official";
panel._renderTabs();
panel._renderTab();
const second=panel.shadowRoot.querySelector("#recipeGrid img.cover");
if(second!==first)throw new Error("Returning to a section recreated the recipe image instead of reusing the loaded node");

// Today cards expose the actual source catalog so mixed-language results are
// visible and testable even when result translation is enabled.
panel._tab="today";
const todayCard=panel._recipeCard(recipe,false);
if(!todayCard.includes("data-today-catalog-chip")||!todayCard.includes("DE"))throw new Error(`Today card did not surface catalog language: ${todayCard}`);

console.log("Recipe Hub v58 Today multi-catalog + image reuse smoke OK");
