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

const userId="minimal-bootstrap-user";
storage.set(`cook4me.ui.lastSection.v1.${userId}`,"week");

await import("../custom_components/cook4me/frontend/cook4me-panel-v53.js");
const tag="cook4me-recipe-hub-panel-v53";
if(!customElements.get(tag))throw new Error(`${tag} was not registered`);

const minimalEntry={
  entry_id:"lazy-entry",title:"Cook4Me",connected:true,canAcceptRecipe:true,
  loadedRecipe:null,state:{phase:"idle"},
};
const fullEntry={
  ...minimalEntry,
  profile:{diet:"vegetarian",allergies:[],avoid:[],houseIngredients:[],householdMembers:[]},
  recipes:[],history:[],habitTerms:[],configuredLanguage:"de",country:"DE",
};
const forbiddenBootstrapFields=["profile","recipes","history","habitTerms","inventory","nutrition"];
const weekState={
  weekStart:"2026-09-07",slots:[],leftovers:[],reservations:{items:[],shortages:[],unknown:[]},shoppingDelta:[],weeklyCostByCurrency:{},
  costSettings:{currency:"EUR",country:"DE",autoGlobalPrices:true},
  settings:{mealTypes:["breakfast","lunch","dinner"],leftoversFirst:true,avoidRecentDays:7,nutritionTargets:{}},
  nutritionDashboard:{todayTargetProgress:{},series:[],totals:{},costByCurrency:{}},feedback:{},substitutions:{},suggestedCountry:"DE",
};
const languages=[{code:"de",country:"DE"},{code:"en",country:"GB"},{code:"fr",country:"FR"}];
const calls=[];
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const sendMessagePromise=async message=>{
  const type=String(message?.type||"");calls.push(type);
  if(type==="cook4me/v27/bootstrap"){await delay(35);return {entries:[structuredClone(minimalEntry)],bootstrapContract:"minimal-device-header-v1"};}
  if(type==="cook4me/overview"){await delay(45);return {entries:[structuredClone(fullEntry)]};}
  if(type==="cook4me/v20/week_state"){await delay(45);return structuredClone(weekState);}
  if(type==="cook4me/v24/currency_state"){await delay(45);return {currency:"EUR",mode:"auto",defaultCurrency:"GBP",currencies:["EUR","GBP","USD"],rates:{EUR:1,GBP:.86,USD:1.17},rateDate:"2026-09-08",source:"ecb_reference_rates",stale:false};}
  if(type.includes("capabilities")){await delay(25);return {languages:structuredClone(languages),defaultAiTaskAvailable:true,defaultAiTaskEntityId:"ai_task.default",deviceCatalogLanguage:"de",ingredientCatalogLanguage:"de",preferences:{}};}
  if(type==="cook4me/v19/book_state"){await delay(25);return {favorites:[],recipeList:[],queuedSend:null};}
  if(type==="cook4me/v18/today_options"){await delay(25);return {languages:structuredClone(languages),defaultLanguage:"de",maxLanguages:8,mealTypes:["breakfast","main"],nutritionGoals:["balanced"],dietOptions:["profile","vegetarian"]};}
  if(type.includes("ingredient_catalog")){await delay(25);return {items:[{key:"M_FOOD_TOMATO",name:"Tomato"}],language:"de"};}
  return {};
};
const hass={language:"en",user:{id:userId},states:{},connection:{sendMessagePromise}};

const panel=document.createElement(tag);
panel.hass=hass;
document.body.appendChild(panel);

await delay(8);
const startupStatus=panel.shadowRoot.getElementById("cook4meLoadStatus")?.textContent||"";
if(!startupStatus.includes("Cook4Me"))throw new Error(`Bootstrap loading message was not visible: ${startupStatus}`);

await delay(80);
if(panel._tab!=="week")throw new Error(`Remembered Week section was not restored; got ${panel._tab}`);
if(JSON.stringify(calls)!==JSON.stringify(["cook4me/v27/bootstrap"]))throw new Error(`Startup violated minimal-bootstrap contract: ${JSON.stringify(calls)}`);
if(calls.includes("cook4me/overview"))throw new Error("Full overview leaked into dashboard startup");
if(!panel.shadowRoot.getElementById("cook4meLoadSection"))throw new Error("Remembered heavy section was not deferred after bootstrap");
for(const field of forbiddenBootstrapFields){if(field in panel._entries[0])throw new Error(`Bootstrap entry leaked heavy field ${field}`);}
if(!panel._entries[0]?.state||Object.keys(panel._entries[0].state).some(key=>!["phase","status","recipeTitle","currentInstruction"].includes(key)))throw new Error(`Bootstrap state was not minimal: ${JSON.stringify(panel._entries[0]?.state)}`);

const beforeUpdates=calls.length;
for(let index=0;index<80;index++)panel.hass={...hass,states:{[`sensor.tick_${index}`]:{state:String(index)}}};
await delay(35);
if(calls.length!==beforeUpdates)throw new Error(`Repeated hass updates triggered API traffic: ${JSON.stringify(calls.slice(beforeUpdates))}`);
if(panel._cook4meUiGuardTripped)throw new Error(`Repeated hass updates caused DOM churn: ${panel._cook4meUiGuardReason}`);

const loadWeek=panel.shadowRoot.getElementById("cook4meLoadSection");
loadWeek.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
await delay(8);
const weekLoading=panel.shadowRoot.getElementById("cook4meLoadStatus")?.textContent||"";
if(!weekLoading)throw new Error("User-triggered Week load did not show a loading message");
await delay(190);
if(calls.filter(type=>type==="cook4me/overview").length!==1)throw new Error(`Full overview was not deferred exactly until Week activation: ${JSON.stringify(calls)}`);
if(calls.filter(type=>type==="cook4me/v20/week_state").length!==1)throw new Error(`Week state did not load exactly once: ${JSON.stringify(calls)}`);
if(calls.filter(type=>type==="cook4me/v24/currency_state").length!==1)throw new Error(`Currency state did not load exactly once after Week activation: ${JSON.stringify(calls)}`);
if(!panel._v53FullOverviewDone)throw new Error("Explicit heavy-section activation never loaded full overview");
if(!panel._entries[0]?.profile||!Array.isArray(panel._entries[0]?.recipes))throw new Error("Full overview did not restore deferred profile/recipe data");

const todayTab=panel.shadowRoot.querySelector('[data-tab="today"]');
if(!todayTab)throw new Error("Today tab missing");
todayTab.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
await delay(8);
const todayLoading=panel.shadowRoot.getElementById("cook4meLoadStatus")?.textContent||"";
if(!todayLoading)throw new Error("User-triggered Today load did not show a loading message");
await delay(190);
if(calls.filter(type=>type==="cook4me/overview").length!==1)throw new Error("Already-loaded full overview was fetched again while switching sections");
if(!calls.some(type=>type.includes("capabilities")))throw new Error("Today activation did not load capabilities");
if(!calls.includes("cook4me/v18/today_options"))throw new Error("Today activation did not load Today choices");
if(!calls.some(type=>type.includes("ingredient_catalog")))throw new Error("Today activation did not load ingredient catalog");
if(!panel.shadowRoot.getElementById("content")?.querySelector(".rx-today-planner"))throw new Error("Today section did not render after explicit loads finished");
if(panel._cook4meUiGuardTripped)throw new Error(`Normal lazy section loads tripped DOM guard: ${panel._cook4meUiGuardReason}`);

panel.remove();
console.log("Recipe Hub v53 minimal-bootstrap startup contract smoke OK");
