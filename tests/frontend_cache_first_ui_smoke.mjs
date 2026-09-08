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
const clone=value=>JSON.parse(JSON.stringify(value));
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));

await import("../custom_components/cook4me/frontend/cook4me-panel-v56.js");
const tag="cook4me-recipe-hub-panel-v56";
if(!customElements.get(tag))throw new Error(`${tag} was not registered`);

const languages=[{code:"de",country:"DE"},{code:"en",country:"GB"},{code:"fr",country:"FR"}];
const minimalEntry={
  entry_id:"cache-entry",title:"Cook4Me",connected:true,canAcceptRecipe:true,
  loadedRecipe:null,state:{phase:"idle"},
};
const fullEntry={
  ...minimalEntry,
  profile:{diet:"vegetarian",allergies:[],avoid:[],preferences:[],houseIngredients:[{key:"M_FOOD_TOMATO",name:"Tomato",quantity:2,unit:"pcs"}],householdMembers:[]},
  recipes:[{id:"local-1",title:"Cached soup",source:"manual",servings:2,ingredients:["Tomato"],steps:["Cook"]}],
  history:[],habitTerms:["tomato"],configuredLanguage:"de",country:"DE",
};
const weekState={
  weekStart:"2026-09-07",slots:[],leftovers:[],reservations:{items:[],shortages:[],unknown:[]},shoppingDelta:[],weeklyCostByCurrency:{EUR:12},
  costSettings:{currency:"EUR",country:"DE",autoGlobalPrices:true},
  settings:{mealTypes:["breakfast","lunch","dinner"],leftoversFirst:true,avoidRecentDays:7,nutritionTargets:{}},
  nutritionDashboard:{todayTargetProgress:{},series:[],totals:{},costByCurrency:{}},feedback:{},substitutions:{},suggestedCountry:"DE",
};
const currencyState={currency:"EUR",mode:"auto",defaultCurrency:"EUR",currencies:["EUR","GBP","USD"],rates:{EUR:1,GBP:.86,USD:1.17},rateDate:"2026-09-08",source:"ecb_reference_rates",stale:false};
const capabilities={languages:clone(languages),defaultAiTaskAvailable:true,defaultAiTaskEntityId:"ai_task.default",deviceCatalogLanguage:"de",ingredientCatalogLanguage:"de",preferences:{lastTab:"today",catalogLanguage:"auto",translateResults:true}};
const todayOptions={languages:clone(languages),defaultLanguage:"de",maxLanguages:8,mealTypes:["breakfast","main"],nutritionGoals:["balanced"],dietOptions:["profile","vegetarian"]};
const bookState={favorites:[],recipeList:[],queuedSend:null};
const nutritionSettings={fdcApiKeyConfigured:false,catalogCount:12,catalogTotal:12,remaining:0,blockedFailures:0,actionableRemaining:0};

function cachedSnapshot(){
  return {
    version:1,savedAt:Date.now(),selectedEntryId:"cache-entry",fullOverviewCached:true,
    entries:[clone(fullEntry)],
    perEntry:{
      "cache-entry":{
        capabilities:clone(capabilities),uiPreferences:{catalogLanguage:"auto",translateResults:true,lastTab:"today",recipeLanguageSelections:{},recipeServingSelections:{}},
        bookState:clone(bookState),todayOptions:clone(todayOptions),ingredientCatalog:[{key:"M_FOOD_TOMATO",name:"Tomato"}],ingredientCatalogLanguage:"de",
        shoppingItems:[{uid:"shop-1",summary:"Milk",status:"needs_action"}],shoppingEntityId:"todo.shopping_list",shoppingAvailable:true,
        houseIngredients:clone(fullEntry.profile.houseIngredients),houseStateLoaded:true,pendingConsumption:null,nutritionSettings:clone(nutritionSettings),
        weekState:clone(weekState),currencyState:clone(currencyState),results:[],recommendations:[],todayResults:[],todayMeta:null,searchQuery:"",savedAt:Date.now(),
      },
    },
  };
}

function makeConnection(calls,{bootstrapDelay=25,delayMs=30}={}){
  let active=0,maxActive=0;
  const sendMessagePromise=async message=>{
    const type=String(message?.type||"");calls.push(type);active++;maxActive=Math.max(maxActive,active);
    try{
      await delay(type==="cook4me/v27/bootstrap"?bootstrapDelay:delayMs);
      if(type==="cook4me/v27/bootstrap")return {entries:[clone(minimalEntry)],bootstrapContract:"minimal-device-header-v1"};
      if(type==="cook4me/overview")return {entries:[clone(fullEntry)]};
      if(type==="cook4me/v20/week_state")return clone(weekState);
      if(type==="cook4me/v24/currency_state")return clone(currencyState);
      if(type.includes("capabilities"))return clone(capabilities);
      if(type==="cook4me/v19/book_state")return clone(bookState);
      if(type==="cook4me/v18/today_options")return clone(todayOptions);
      if(type.includes("ingredient_catalog"))return {items:[{key:"M_FOOD_TOMATO",name:"Tomato"}],language:"de"};
      if(type==="cook4me/v12/shopping_list")return {available:true,entityId:"todo.shopping_list",items:[{uid:"shop-1",summary:"Milk",status:"needs_action"}]};
      if(type==="cook4me/v14/inventory_state")return {houseIngredients:clone(fullEntry.profile.houseIngredients),pendingConsumption:null};
      if(type==="cook4me/v16/nutrition_settings")return clone(nutritionSettings);
      if(type==="cook4me/v16/nutrition_catalog_fill")throw new Error("Automatic nutrition catalog enrichment is forbidden");
      return {};
    }finally{active--;}
  };
  return {connection:{sendMessagePromise},maxActive:()=>maxActive};
}

// ---------------------------------------------------------------------------
// 1. Warm cache: first paint is real UI, startup does only minimal bootstrap.
// ---------------------------------------------------------------------------
const cachedUser="cache-first-user";
storage.set(`cook4me.ui.lastSection.v1.${cachedUser}`,"today");
storage.set(`cook4me.ui.snapshot.v54.${cachedUser}`,JSON.stringify(cachedSnapshot()));
const cachedCalls=[];
const cachedTransport=makeConnection(cachedCalls);
const cachedHass={language:"en",user:{id:cachedUser},states:{},connection:cachedTransport.connection};
const cachedPanel=document.createElement(tag);
cachedPanel.hass=cachedHass;

// Cache must paint BEFORE the element is even connected/bootstrap starts.
if(!cachedPanel.shadowRoot?.getElementById("content")?.querySelector(".rx-today-planner"))throw new Error("Cached Today UI was not painted immediately on hass assignment");
if(cachedPanel.shadowRoot.querySelector("#cook4meLoadSection,.rx-v51-deferred"))throw new Error("Whole-section Load gate still exists in active cache-first UI");
if(!cachedPanel.shadowRoot.getElementById("status")?.textContent?.includes("Cook4Me"))throw new Error("Cached device header did not paint before bootstrap");

document.body.appendChild(cachedPanel);
await delay(90);
if(JSON.stringify(cachedCalls)!==JSON.stringify(["cook4me/v27/bootstrap"]))throw new Error(`Warm-cache startup made unnecessary requests: ${JSON.stringify(cachedCalls)}`);
if(cachedPanel._entries[0]?.profile?.diet!=="vegetarian")throw new Error("Minimal bootstrap replaced instead of merging cached profile data");
if(cachedPanel.shadowRoot.querySelector("#cook4meLoadSection,.rx-v51-deferred"))throw new Error("Load-section wall appeared after bootstrap");
if(cachedCalls.some(type=>type.includes("nutrition_catalog_fill")))throw new Error("Nutrition enrichment leaked into dashboard render");

const beforeHassUpdates=cachedCalls.length;
for(let index=0;index<80;index++)cachedPanel.hass={...cachedHass,states:{[`sensor.tick_${index}`]:{state:String(index)}}};
await delay(35);
if(cachedCalls.length!==beforeHassUpdates)throw new Error(`Repeated HA state propagation caused requests: ${JSON.stringify(cachedCalls.slice(beforeHassUpdates))}`);
if(cachedPanel._cook4meUiGuardTripped)throw new Error(`Cache-first startup caused DOM storm: ${cachedPanel._cook4meUiGuardReason}`);

// Cached Week must switch instantly with zero requests.
const beforeWeek=cachedCalls.length;
const weekTab=cachedPanel.shadowRoot.querySelector('[data-tab="week"]');
if(!weekTab)throw new Error("Week tab missing");
weekTab.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
if(!cachedPanel.shadowRoot.getElementById("content")?.querySelector("#generateWeek"))throw new Error("Cached Week UI did not render synchronously on tab click");
await delay(45);
if(cachedCalls.length!==beforeWeek)throw new Error(`Cached Week tab triggered refresh instead of using cache: ${JSON.stringify(cachedCalls.slice(beforeWeek))}`);

// Explicit refresh is allowed, but cached Week must remain visible while it runs.
const refresh=cachedPanel.shadowRoot.getElementById("refresh");
if(!refresh)throw new Error("Refresh button missing");
refresh.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
await delay(8);
if(!cachedPanel.shadowRoot.getElementById("content")?.querySelector("#generateWeek"))throw new Error("Explicit refresh replaced cached Week content");
if(!(cachedPanel.shadowRoot.getElementById("cook4meLoadStatus")?.textContent||""))throw new Error("Explicit refresh did not tell the user that data is loading");
await delay(150);
const refreshCalls=cachedCalls.slice(beforeWeek);
if(refreshCalls.filter(type=>type==="cook4me/v27/bootstrap").length!==1)throw new Error(`Refresh did not perform one live bootstrap: ${JSON.stringify(refreshCalls)}`);
if(refreshCalls.filter(type=>type==="cook4me/overview").length!==1)throw new Error(`Refresh did not refresh full overview once: ${JSON.stringify(refreshCalls)}`);
if(refreshCalls.filter(type=>type==="cook4me/v20/week_state").length!==1)throw new Error(`Refresh did not refresh Week once: ${JSON.stringify(refreshCalls)}`);
if(refreshCalls.filter(type=>type==="cook4me/v24/currency_state").length!==1)throw new Error(`Refresh did not refresh currency once: ${JSON.stringify(refreshCalls)}`);
if(cachedTransport.maxActive()>1)throw new Error(`Cache-first requests overlapped; max active=${cachedTransport.maxActive()}`);

// ---------------------------------------------------------------------------
// 2. Cold cache: real Today UI still paints immediately; only missing pieces
//    load serially after the tiny bootstrap, with element/background feedback.
// ---------------------------------------------------------------------------
const coldUser="cold-cache-first-user";
storage.set(`cook4me.ui.lastSection.v1.${coldUser}`,"today");
const coldCalls=[];
const coldTransport=makeConnection(coldCalls,{bootstrapDelay:25,delayMs:30});
const coldHass={language:"en",user:{id:coldUser},states:{},connection:coldTransport.connection};
const coldPanel=document.createElement(tag);
coldPanel.hass=coldHass;
if(!coldPanel.shadowRoot?.getElementById("content")?.querySelector(".rx-today-planner"))throw new Error("Cold-cache Today did not render its actual UI immediately");
if(coldPanel.shadowRoot.querySelector("#cook4meLoadSection,.rx-v51-deferred"))throw new Error("Cold-cache startup rendered a whole-section gate");
document.body.appendChild(coldPanel);

await delay(8);
if(JSON.stringify(coldCalls)!==JSON.stringify(["cook4me/v27/bootstrap"]))throw new Error(`Cold startup began more than minimal bootstrap before it completed: ${JSON.stringify(coldCalls)}`);
if(!coldPanel.shadowRoot.getElementById("content")?.querySelector(".rx-today-planner"))throw new Error("Bootstrap replaced the visible Today UI");

await delay(38);
if(!coldPanel.shadowRoot.getElementById("content")?.querySelector(".rx-today-planner"))throw new Error("Missing-data load replaced Today UI");
const loadingText=(coldPanel.shadowRoot.getElementById("cook4meLoadStatus")?.textContent||"")+(coldPanel.shadowRoot.getElementById("content")?.textContent||"");
if(!/Loading|Updating/i.test(loadingText))throw new Error(`Cold-cache missing resources had no visible loading state: ${loadingText}`);

await delay(200);
const requiredCold=[
  "cook4me/v27/bootstrap","cook4me/overview","cook4me/v11/capabilities","cook4me/v19/book_state","cook4me/v18/today_options","cook4me/v11/ingredient_catalog",
];
for(const type of requiredCold){if(!coldCalls.includes(type))throw new Error(`Cold-cache Today did not load missing ${type}: ${JSON.stringify(coldCalls)}`);}
for(const forbidden of ["cook4me/v20/week_state","cook4me/v24/currency_state","cook4me/v12/shopping_list","cook4me/v14/inventory_state","cook4me/v16/nutrition_settings","cook4me/v16/nutrition_catalog_fill"]){
  if(coldCalls.includes(forbidden))throw new Error(`Unrequested resource ${forbidden} loaded during Today: ${JSON.stringify(coldCalls)}`);
}
if(coldTransport.maxActive()>1)throw new Error(`Cold-cache requests were not serialized; max active=${coldTransport.maxActive()}`);
if(!coldPanel.shadowRoot.getElementById("content")?.querySelector(".rx-today-planner"))throw new Error("Today UI disappeared after missing data loaded");
if(coldPanel._cook4meUiGuardTripped)throw new Error(`Cold-cache element loading tripped DOM guard: ${coldPanel._cook4meUiGuardReason}`);

// A normal visit to the same cached tab must not immediately re-fetch it.
const beforeRepeatTab=coldCalls.length;
const officialTab=coldPanel.shadowRoot.querySelector('[data-tab="official"]');
const todayTab=coldPanel.shadowRoot.querySelector('[data-tab="today"]');
if(!officialTab||!todayTab)throw new Error("Navigation tabs missing");
officialTab.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
await delay(40);
const afterOfficial=coldCalls.length;
todayTab.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
await delay(40);
if(coldCalls.length!==afterOfficial)throw new Error(`Returning to fully cached Today triggered network traffic: ${JSON.stringify(coldCalls.slice(afterOfficial))}`);

cachedPanel.remove();
coldPanel.remove();
console.log("Recipe Hub v56 cache-first always-available UI smoke OK");
