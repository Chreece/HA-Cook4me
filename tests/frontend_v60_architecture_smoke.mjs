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
globalThis.requestIdleCallback=callback=>setTimeout(()=>callback({didTimeout:false,timeRemaining:()=>50}),0);
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

const userId="v60-user";
const shellKey=`cook4me.ui.shell.v2.${userId}`;
const legacyKey=`cook4me.ui.snapshot.v54.${userId}`;
storage.set(legacyKey,JSON.stringify({huge:"x".repeat(2_000_000)}));
storage.set(shellKey,JSON.stringify({
  version:2,
  selectedEntryId:"entry",
  tab:"today",
  entries:[{entry_id:"entry",title:"Cook4Me",connected:true,canAcceptRecipe:true,state:{phase:"idle"},configuredLanguage:"de",country:"DE"}],
  todayByEntry:{entry:{cards:[{
    title:"Cached tomato soup",searchVariantId:"de-soup",displayVariantId:"de-soup",sendVariantId:"de-soup",
    groupingFunctionalId:"GROUP_SOUP",sendGroupingFunctionalId:"GROUP_SOUP",sendRecipeFunctionalId:"de-soup",
    sendable:true,language:"de",todayCatalogLanguage:"de",source:"cook4me_shell_summary",
    nutrition:{perServing:{energyKcal:45,protein:2.25,carbohydrates:7,fat:1,fiber:2},totals:{energyKcal:90},coverage:1,estimated:false},
    match:{score:100,safe:true,pantryCoverage:1},
  }],meta:{date:"2026-09-09",offlineCatalog:true}}},
}));

await import("../custom_components/cook4me/frontend/cook4me-panel-v60.js");
const tag="cook4me-recipe-hub-panel-v60";
if(!customElements.get(tag))throw new Error(`${tag} was not registered`);

const calls=[];
const panel=document.createElement(tag);
panel._hass={
  language:"en",
  user:{id:userId},
  states:{},
  connection:{
    sendMessagePromise:async message=>{calls.push(String(message.type||""));return {items:[]};},
    subscribeEvents:async()=>()=>{},
  },
};

// P0 startup contract: synchronous hydration may read only the tiny v2 shell,
// never the legacy rich v54 snapshot even when that old value is multi-MB.
panel._hydrateUiSnapshot({id:userId});
if(!reads.includes(shellKey))throw new Error(`v60 did not read the tiny shell: ${JSON.stringify(reads)}`);
if(reads.includes(legacyKey))throw new Error("v60 synchronously read the legacy rich v54 snapshot");
if(panel._entryId!=="entry")throw new Error(`shell entry was not restored: ${panel._entryId}`);
if(panel._todayResults?.[0]?.title!=="Cached tomato soup")throw new Error("compact Today shell card was not restored");

panel._capabilities={languages:[{code:"de",country:"DE"},{code:"en",country:"GB"}],deviceCatalogLanguage:"de",ingredientCatalogLanguage:"de",preferences:{}};
panel._todayOptions={languages:panel._capabilities.languages,defaultLanguage:"de",maxLanguages:8,mealTypes:["main"],nutritionGoals:["balanced"],dietOptions:["profile","vegetarian"]};
panel._bookState={favorites:[],recipeList:[],queuedSend:null};
panel._preferencesLoaded=true;
panel._v51OverviewDone=true;
panel._v53BootstrapDone=true;
panel._v53FullOverviewDone=true;
panel._renderShell();

// Active API routing must use offline/lazy v30 catalog endpoints and the corrected
// v31 selective recipe-cost cache endpoint.
await panel._api("cook4me/v18/today_suggest",{entry_id:"entry",languages:["de","en"]});
if(calls.at(-1)!=="cook4me/v30/today_suggest")throw new Error(`Today was not routed to v30: ${JSON.stringify(calls)}`);
await panel._api("cook4me/v23/recipe_cost",{entry_id:"entry",recipe:{title:"Soup",ingredients:[]}});
if(calls.at(-1)!=="cook4me/v31/recipe_cost")throw new Error(`Recipe cost was not routed to v31: ${JSON.stringify(calls)}`);
await panel._api("cook4me/v24/recipe_detail",{entry_id:"entry",variant_id:"de-soup",language:"de"});
if(calls.at(-1)!=="cook4me/v30/recipe_detail")throw new Error(`Recipe detail was not routed to v30: ${JSON.stringify(calls)}`);

// Progress must be non-modal, determinate only when real completed/total exists,
// and must not expose the old fake frontend-only Cancel control.
const token=panel._processStart("Cook4Me · Today's suggestions","Calculating nutrition");
const progressCard=panel.shadowRoot.querySelector(".rx-v59-progress-card");
if(!progressCard)throw new Error("v60 did not create the bottom-right progress card");
if(panel.shadowRoot.querySelector(".rx-process-overlay"))throw new Error("v60 recreated the old blocking process overlay");
if(progressCard.textContent.includes("Cancel"))throw new Error("v60 still exposes the misleading frontend-only Cancel button");
panel._processUpdate(token,"Calculating nutrition",3,4);
if(panel.shadowRoot.querySelector("[data-progress-percent]")?.textContent!=="75%")throw new Error("real determinate progress did not render 75%");
panel._processEnd(token);

const nutrition={
  totals:{energyKcal:972,energyKJ:4067,protein:44,carbohydrates:108,sugars:18,fat:36,saturatedFat:10,fiber:18,salt:3.2,sodium:1.28},
  perServing:{energyKcal:486,energyKJ:2033.5,protein:22,carbohydrates:54,sugars:9,fat:18,saturatedFat:5,fiber:9,salt:1.6,sodium:0.64},
  servings:2,coverage:.93,fullyCovered:false,estimated:true,
};
const recipe={
  title:"Nutrition recipe",groupingFunctionalId:"g1",recipeFunctionalId:"r1",searchVariantId:"r1",
  language:"de",todayCatalogLanguage:"de",cover:"",sendable:true,
  ingredients:[{foodKey:"TOMATO",foodName:"Tomato",quantity:500,unit:"g"}],
  steps:[{instruction:"Cook"}],match:{safe:true,score:100},nutrition,
  officialNutrition:{
    energyPer100gValue:110,
    hierarchicalNutrients:[{name:"Protein",valuePer100g:4.2,unit:{abbreviation:"g"}}],
    nutrients:[{key:"SPECIAL",name:"Special nutrient",quantity:3,unit:{abbreviation:"mg"}}],
    nutritionalScore:"A",ecologicalScore:{grade:"B"},partWeight:250,
  },
};
const cardHtml=panel._recipeCard(recipe,false);
for(const expected of ["486 kcal","P 22g","C 54g","F 18g","🌾 9g","93%","estimated"]){
  if(!cardHtml.includes(expected))throw new Error(`compact nutrition card lost ${expected}: ${cardHtml}`);
}
const detailHtml=panel._detailHtml(recipe);
for(const expected of ["Energy kcal","Energy kJ","Protein","Carbohydrates","Sugars","Fat","Saturated fat","Fiber","Salt","Sodium","Official SEB nutrition","basis not specified by SEB"]){
  if(!detailHtml.includes(expected))throw new Error(`detail nutrition lost ${expected}: ${detailHtml}`);
}

console.log("Recipe Hub v60 startup + release catalog + progress + nutrition smoke OK");
