import {parseHTML} from "linkedom";

const {window}=parseHTML("<!doctype html><html><body></body></html>");
for(const key of ["document","customElements","HTMLElement","Node","Event","CustomEvent","MutationObserver","Element","ShadowRoot","HTMLInputElement","HTMLSelectElement"]){if(window[key])globalThis[key]=window[key];}
globalThis.window=window;
if(!globalThis.navigator)Object.defineProperty(globalThis,"navigator",{value:window.navigator||{language:"en"},configurable:true});
globalThis.requestAnimationFrame=callback=>setTimeout(()=>callback(Date.now()),0);
globalThis.cancelAnimationFrame=id=>clearTimeout(id);
globalThis.ResizeObserver=class{observe(){} unobserve(){} disconnect(){}};
globalThis.CSS=globalThis.CSS||{escape:value=>String(value).replace(/[^a-zA-Z0-9_-]/g,"\\$&")};
const storage=new Map();
globalThis.localStorage={getItem:key=>storage.get(String(key))??null,setItem:(key,value)=>storage.set(String(key),String(value)),removeItem:key=>storage.delete(String(key)),clear:()=>storage.clear()};

await import("../custom_components/cook4me/frontend/cook4me-panel-v57.js");
const tag="cook4me-recipe-hub-panel-v57";
if(!customElements.get(tag))throw new Error("v57 panel missing");

const entry={entry_id:"seed-entry",title:"Cook4Me",connected:true,canAcceptRecipe:true,loadedRecipe:null,state:{phase:"idle"},profile:{diet:"vegetarian",allergies:[],avoid:[],preferences:[],houseIngredients:[{key:"M_FOOD_TOMATO",name:"Tomato",quantity:2,unit:"pcs"}]},recipes:[],history:[],habitTerms:[],configuredLanguage:"de",country:"DE"};
const languages=[{code:"de",country:"DE"},{code:"en",country:"GB"},{code:"el",country:"GR"}];
const perEntry={
  "seed-entry":{
    capabilities:{languages,deviceCatalogLanguage:"de",ingredientCatalogLanguage:"de",defaultAiTaskAvailable:true,defaultAiTaskEntityId:"ai_task.default",preferences:{catalogLanguage:"auto",translateResults:true,lastTab:"official",nutritionGoal:"balanced",recipeLanguageSelections:{},recipeServingSelections:{}}},
    uiPreferences:{catalogLanguage:"auto",translateResults:true,lastTab:"official",nutritionGoal:"balanced",recipeLanguageSelections:{},recipeServingSelections:{}},
    bookState:{favorites:[],recipeList:[],queuedSend:null,deviceConnected:true,deviceCanAccept:true,loadedRecipe:null,myRecipes:[]},
    todayOptions:{languages,defaultLanguage:"de",maxLanguages:8,mealTypes:["breakfast","main"],nutritionGoals:["balanced"],dietOptions:["profile","vegetarian"]},
    ingredientCatalog:[{key:"M_FOOD_TOMATO",name:"Tomato"},{key:"M_FOOD_ONION",name:"Onion"}],ingredientCatalogLanguage:"de",houseIngredients:entry.profile.houseIngredients,houseStateLoaded:true,pendingConsumption:null,results:[],recommendations:[],todayResults:[],todayMeta:null,searchQuery:""
  }
};
const calls=[];const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const sendMessagePromise=async message=>{
  const type=String(message?.type||"");calls.push(type);
  if(type==="cook4me/v28/ui_seed"){await delay(45);return {entries:[structuredClone(entry)],perEntry:structuredClone(perEntry),selectedEntryId:"seed-entry",fullOverviewCached:true,serverSeedContract:"local-persistent-ui-v1",onlineRequests:0};}
  if(type==="cook4me/v27/bootstrap")throw new Error("cold new-browser startup must not need a second bootstrap");
  if(type.includes("capabilities")||type.includes("book_state")||type.includes("today_options")||type.includes("ingredient_catalog")||type==="cook4me/overview")throw new Error(`server seed should prevent cold startup dependency call ${type}`);
  return {};
};
const hass={language:"en",user:{id:"brand-new-browser"},states:{},connection:{sendMessagePromise}};
const panel=document.createElement(tag);
panel.hass=hass;document.body.appendChild(panel);

// Before the local server seed returns, the actual dashboard UI must already exist.
await delay(5);
if(panel.shadowRoot.getElementById("cook4meLoadSection"))throw new Error("historical whole-section Load gate appeared on a new browser");
if(!panel.shadowRoot.querySelector("#searchQ"))throw new Error("Official recipe UI was not painted immediately on a cold browser");

await delay(90);
if(JSON.stringify(calls)!==JSON.stringify(["cook4me/v28/ui_seed"]))throw new Error(`cold startup made unexpected calls: ${JSON.stringify(calls)}`);
if(!panel._entry()?.profile||panel._entry().profile.diet!=="vegetarian")throw new Error("server seed did not hydrate cached profile");
if(panel._ingredientCatalog.length!==2)throw new Error("server seed did not hydrate retained ingredient catalog");
if((panel._capabilities?.languages||[]).length!==3)throw new Error("server seed did not hydrate language options");
if(panel.shadowRoot.getElementById("cook4meLoadSection"))throw new Error("whole-section gate appeared after server seed");

const beforeUpdates=calls.length;
for(let index=0;index<80;index++)panel.hass={...hass,states:{[`sensor.tick_${index}`]:{state:String(index)}}};
await delay(30);
if(calls.length!==beforeUpdates)throw new Error(`HA updates triggered requests: ${JSON.stringify(calls.slice(beforeUpdates))}`);

const today=panel.shadowRoot.querySelector('[data-tab="today"]');
if(!today)throw new Error("Today tab missing");
today.dispatchEvent(new Event("click",{bubbles:true,cancelable:true}));
await delay(10);
if(!panel.shadowRoot.querySelector(".rx-today-planner"))throw new Error("Today UI did not render synchronously from server seed");
if(calls.length!==beforeUpdates)throw new Error(`cached Today triggered extra calls: ${JSON.stringify(calls.slice(beforeUpdates))}`);
if(panel.shadowRoot.getElementById("cook4meLoadSection"))throw new Error("whole-section gate appeared during cached navigation");

panel.remove();
console.log("Recipe Hub v57 new-browser server-seeded UI smoke OK");
