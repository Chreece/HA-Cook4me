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

await import("../custom_components/cook4me/frontend/cook4me-panel-v47.js");
const tag="cook4me-recipe-hub-panel-v47";
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

// Prove the runtime circuit breaker exists: an artificial storm must be cut
// off instead of being allowed to monopolize the browser indefinitely.
const protectedPanel=document.createElement(tag);
let allowed=true;
for(let index=0;index<200&&allowed;index++)allowed=protectedPanel._guardPulse("dom");
if(!protectedPanel._cook4meUiGuardTripped)throw new Error("UI loop circuit breaker did not trip under an artificial DOM storm");
if(protectedPanel.dataset.cook4meUiGuard!=="tripped")throw new Error("UI loop circuit breaker did not expose diagnostic state");

panel.remove();
protectedPanel.remove();
console.log("Recipe Hub v47 startup stability smoke OK");
