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

const storage=new Map();
globalThis.localStorage={
  getItem:key=>storage.has(String(key))?storage.get(String(key)):null,
  setItem:(key,value)=>storage.set(String(key),String(value)),
  removeItem:key=>storage.delete(String(key)),
  clear:()=>storage.clear(),
};

const userId="startup-stability-user";
storage.set(`cook4me.ui.lastSection.v1.${userId}`,"week");

await import("../custom_components/cook4me/frontend/cook4me-panel-v48.js");
const tag="cook4me-recipe-hub-panel-v48";
if(!customElements.get(tag))throw new Error(`${tag} was not registered`);

const entry={
  entry_id:"startup-entry",
  title:"Cook4Me",
  connected:true,
  canAcceptRecipe:true,
  state:{phase:"idle"},
  profile:{diet:"vegetarian",houseIngredients:[],householdMembers:[]},
  recipes:[],
};
const weekState={
  weekStart:"2026-09-07",
  slots:[],
  leftovers:[],
  reservations:{items:[],shortages:[],unknown:[]},
  shoppingDelta:[],
  weeklyCostByCurrency:{},
  costSettings:{currency:"EUR",country:"DE",autoGlobalPrices:true},
  settings:{mealTypes:["breakfast","lunch","dinner"],leftoversFirst:true,avoidRecentDays:7,nutritionTargets:{}},
  nutritionDashboard:{todayTargetProgress:{},series:[],totals:{},costByCurrency:{}},
  feedback:{},substitutions:{},suggestedCountry:"DE",
};
const calls=new Map();
const count=type=>calls.set(type,(calls.get(type)||0)+1);
const sendMessagePromise=async message=>{
  const type=String(message?.type||"");count(type);
  if(type==="cook4me/overview")return {entries:[entry]};
  if(type==="cook4me/v20/week_state")return structuredClone(weekState);
  if(type==="cook4me/v18/today_options")return {
    languages:[{code:"de",country:"DE"},{code:"en",country:"GB"},{code:"fr",country:"FR"}],
    defaultLanguage:"de",maxLanguages:8,mealTypes:["breakfast","main"],nutritionGoals:["balanced"],dietOptions:["profile","vegetarian"],
  };
  if(type==="cook4me/v21/currency_state"||type==="cook4me/v21/currency_set"){
    return {currency:"EUR",mode:"auto",defaultCurrency:"GBP",currencies:["EUR","GBP","USD"],rates:{EUR:1,GBP:.86,USD:1.17},rateDate:"2026-09-07",source:"ecb_reference_rates",stale:false};
  }
  return {};
};
const hass={
  language:"en",
  user:{id:userId},
  states:{},
  connection:{sendMessagePromise},
};

// Reproduce Home Assistant panel navigation: hass can be assigned before the
// custom element is connected, then assigned repeatedly as HA state updates.
const panel=document.createElement(tag);
panel.hass=hass;
document.body.appendChild(panel);
await new Promise(resolve=>setTimeout(resolve,80));

if(panel._tab!=="week")throw new Error(`Remembered Week section was not restored; got ${panel._tab}`);
if(panel._cook4meUiGuardTripped)throw new Error(`UI guard tripped during normal startup: ${panel._cook4meUiGuardReason}`);
if(!panel.shadowRoot?.getElementById("content"))throw new Error("Cook4Me content did not render after navigation");

for(let index=0;index<40;index++){
  panel.hass={...hass,states:{[`sensor.tick_${index}`]:{state:String(index)}}};
}
await new Promise(resolve=>setTimeout(resolve,80));

if(panel._cook4meUiGuardTripped)throw new Error(`UI guard tripped during normal hass updates: ${panel._cook4meUiGuardReason}`);
if((calls.get("cook4me/overview")||0)>3)throw new Error(`Overview loader storm: ${calls.get("cook4me/overview")}`);
if((calls.get("cook4me/v20/week_state")||0)>2)throw new Error(`Week-state loader storm: ${calls.get("cook4me/v20/week_state")}`);
if((calls.get("cook4me/v21/currency_state")||0)>2)throw new Error(`Currency loader storm: ${calls.get("cook4me/v21/currency_state")}`);

// The old freeze came from rewriting an already-correct option.textContent on
// every MutationObserver pass. A second decoration must preserve the text node
// identity; otherwise it creates another childList mutation and can self-loop.
const languageSelect=panel.shadowRoot.getElementById("cook4meUiLanguage");
const option=languageSelect?.options?.[0];
if(!option||!option.firstChild)throw new Error("UI language option missing from stability smoke");
panel._decorateLanguages(panel.shadowRoot);
const decoratedTextNode=option.firstChild;
panel._decorateLanguages(panel.shadowRoot);
if(option.firstChild!==decoratedTextNode)throw new Error("Language decoration is not idempotent; repeated pass replaced the same text node");

// Core navigation must remain functional even after the safety guard disables
// optional DOM decoration. This protects against a visually live but inert UI.
panel._tripUiGuard("test-navigation-guard");
if(!panel._cook4meUiGuardTripped)throw new Error("Test guard did not trip");
panel._todayOptions=null;
panel._todayOptionsLoading=true;
panel._ingredientCatalog=[{key:"M_FOOD_SMOKE",name:"Tomato"}];
panel._ingredientCatalogLoading=false;
const todayTab=panel.shadowRoot.querySelector('[data-tab="today"]');
if(!todayTab)throw new Error("Today tab missing after guard trip");
todayTab.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
if(panel._tab!=="today")throw new Error(`Guard blocked Today navigation; tab=${panel._tab}`);
let content=panel.shadowRoot.getElementById("content");
if(!content?.querySelector(".rx-today-planner"))throw new Error("Guard blocked Today content render");
const loadingLanguagePicker=content.querySelector('details[data-rx-picker="languages"]');
if(!loadingLanguagePicker)throw new Error("Catalog languages picker disappeared while options were loading");
if(!loadingLanguagePicker.querySelector("[data-cook4me-catalog-language-state]"))throw new Error("Catalog languages loading state missing");

// Once today_options arrives, the same control must populate with the official
// catalog language choices rather than disappearing or requiring a reload.
panel._todayOptions={
  languages:[{code:"de",country:"DE"},{code:"en",country:"GB"},{code:"fr",country:"FR"}],
  defaultLanguage:"de",maxLanguages:8,
};
panel._todayOptionsLoading=false;
panel._renderTab();
content=panel.shadowRoot.getElementById("content");
const populatedLanguagePicker=content.querySelector('details[data-rx-picker="languages"]');
if(!populatedLanguagePicker)throw new Error("Catalog languages picker missing after options loaded");
const catalogLanguages=[...populatedLanguagePicker.querySelectorAll("[data-today-language]")];
if(catalogLanguages.length!==3)throw new Error(`Expected 3 catalog languages, got ${catalogLanguages.length}`);

const officialTab=panel.shadowRoot.querySelector('[data-tab="official"]');
if(!officialTab)throw new Error("Official tab missing after guard trip");
officialTab.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
if(panel._tab!=="official")throw new Error(`Guard blocked Official navigation; tab=${panel._tab}`);
if(panel.shadowRoot.getElementById("content")?.querySelector(".rx-today-planner"))throw new Error("Official tab click did not replace Today content");

// Prove the optional DOM-decoration circuit breaker still exists: an artificial
// storm must be cut off, but v48 no longer allows it to disable core rendering.
const protectedPanel=document.createElement(tag);
let allowed=true;
for(let index=0;index<200&&allowed;index++)allowed=protectedPanel._guardPulse("dom");
if(!protectedPanel._cook4meUiGuardTripped)throw new Error("UI decoration circuit breaker did not trip under an artificial DOM storm");
if(protectedPanel.dataset.cook4meUiGuard!=="tripped")throw new Error("UI decoration circuit breaker did not expose diagnostic state");
if(protectedPanel._guardPulse("render")!==true)throw new Error("Tripped decoration guard incorrectly blocked core rendering");

panel.remove();
protectedPanel.remove();
console.log("Recipe Hub v48 startup/navigation stability smoke OK");
