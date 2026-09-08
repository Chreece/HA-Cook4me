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

await import("../custom_components/cook4me/frontend/cook4me-panel-v50.js");
const tag="cook4me-recipe-hub-panel-v50";
if(!customElements.get(tag))throw new Error(`${tag} was not registered`);

const languages=[
  {code:"de",country:"DE"},{code:"en",country:"GB"},{code:"fr",country:"FR"},
];
const entries=[
  {entry_id:"dev-a",title:"Kitchen Cook4Me",connected:true,canAcceptRecipe:true,state:{phase:"idle"},profile:{diet:"vegetarian",allergies:[],avoid:[],houseIngredients:[],householdMembers:[]},recipes:[]},
  {entry_id:"dev-b",title:"Second Cook4Me",connected:true,canAcceptRecipe:false,state:{phase:"preparation"},profile:{diet:"vegetarian",allergies:[],avoid:[],houseIngredients:[],householdMembers:[]},recipes:[]},
];
const ingredientCatalog=[
  {key:"M_FOOD_TOMATO",name:"Tomato"},{key:"M_FOOD_ONION",name:"Onion"},
];
let active=0,maxActive=0;
const calls=[];
let officialPayload=null,aiPayload=null,sendPayload=null;
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const chooseOption=(select,value)=>{
  for(const option of select?.options||[]){
    const selected=String(option.value)===String(value);
    option.selected=selected;
    if(selected)option.setAttribute("selected","");else option.removeAttribute("selected");
  }
};
const setInput=(input,value)=>input?.setAttribute("value",String(value));
const sendMessagePromise=async message=>{
  active++;maxActive=Math.max(maxActive,active);calls.push(structuredClone(message));
  try{
    await delay(4);
    const type=String(message?.type||"");
    if(type==="cook4me/overview")return {entries:structuredClone(entries)};
    if(type.includes("capabilities"))return {
      languages:structuredClone(languages),defaultAiTaskAvailable:true,defaultAiTaskEntityId:"ai_task.default",
      deviceCatalogLanguage:"de",ingredientCatalogLanguage:"de",preferences:{},
    };
    if(type==="cook4me/v19/book_state")return {favorites:[],recipeList:[],queuedSend:null};
    if(type==="cook4me/v18/today_options")return {languages:structuredClone(languages),defaultLanguage:"de",maxLanguages:8,mealTypes:["breakfast","main"],nutritionGoals:["balanced","high_protein"],dietOptions:["profile","vegetarian"]};
    if(type.includes("ingredient_catalog"))return {items:structuredClone(ingredientCatalog),language:"de"};
    if(type==="cook4me/v24/currency_state"||type==="cook4me/v24/currency_set")return {currency:"EUR",mode:"auto",defaultCurrency:"GBP",currencies:["EUR","GBP","USD"],rates:{EUR:1,GBP:.86,USD:1.17},rateDate:"2026-09-08",source:"ecb_reference_rates",stale:false};
    if(type==="cook4me/v22/official_search"){
      officialPayload=structuredClone(message);
      return {items:[],languages:message.languages||[],catalogs:[],count:0};
    }
    if(type==="cook4me/v25/ai_create"){
      aiPayload=structuredClone(message);
      return {recipe:{id:"ai-1",source:"ai",title:"Tomato bowl",servings:2,ingredients:[{key:"M_FOOD_TOMATO",name:"Tomato",quantity:200,unit:"g"}],steps:[{instruction:"Cook."}],match:{safe:true}}};
    }
    if(type==="cook4me/v25/send_multi"){
      sendPayload=structuredClone(message);
      return {results:[],targetCount:(message.entry_ids||[]).length,sentCount:1,queuedCount:1};
    }
    if(type==="cook4me/v26/barcode_scan")return {status:"needs_mapping",barcode:String(message.barcode||""),product:{},suggestions:[],houseIngredients:[]};
    if(type==="cook4me/v24/recipe_detail")return {title:"Detail",ingredients:[],steps:[]};
    if(type==="cook4me/test/serial")return {ok:true,n:message.n};
    return {};
  }finally{active--;}
};

const panel=document.createElement(tag);
document.body.appendChild(panel);
panel.hass={language:"en",user:{id:"orchestration-user"},states:{},connection:{sendMessagePromise}};
await delay(180);
panel._entries=structuredClone(entries);
panel._entryId="dev-a";
panel._capabilities={languages:structuredClone(languages),defaultAiTaskAvailable:true,defaultAiTaskEntityId:"ai_task.default",deviceCatalogLanguage:"de",ingredientCatalogLanguage:"de",preferences:{}};
panel._todayOptions={languages:structuredClone(languages),maxLanguages:8};
panel._ingredientCatalog=structuredClone(ingredientCatalog);
panel._ingredientCatalogLoading=false;
panel._ensureTargetDeviceControl();

const targetControl=panel.shadowRoot.getElementById("cook4meTargetDevicesControl");
if(!targetControl)throw new Error("v50 multi-device target control missing");
const targetRows=[...targetControl.querySelectorAll("[data-target-entry]")];
if(targetRows.length!==2)throw new Error(`Expected 2 target devices, got ${targetRows.length}`);
targetRows.forEach(row=>{row.checked=true;row.setAttribute("checked","");row.dispatchEvent(new Event("change",{bubbles:true}));});
if(panel._targetEntryIds().length!==2)throw new Error("Target-device multi-selection was not persisted");

panel._tab="official";panel._renderTabs();panel._renderTab();
const content=panel.shadowRoot.getElementById("content");
const officialPicker=content.querySelector("#officialCatalogLanguages");
if(!officialPicker)throw new Error("Official catalog-language multi-select missing");
const officialRows=[...officialPicker.querySelectorAll("[data-official-language]")];
if(officialRows.length!==3)throw new Error(`Expected 3 official catalog languages, got ${officialRows.length}`);
officialRows.forEach(row=>{const checked=["de","en"].includes(String(row.dataset.officialLanguage));row.checked=checked;if(checked)row.setAttribute("checked","");else row.removeAttribute("checked");row.dispatchEvent(new Event("change",{bubbles:true}));});
await panel._search("soup");
if(!officialPayload)throw new Error("Official search did not use the v22 multi-language API");
if(JSON.stringify(officialPayload.languages)!==JSON.stringify(["de","en"]))throw new Error(`Official search languages mismatch: ${JSON.stringify(officialPayload.languages)}`);

panel._tab="ai";panel._opened=null;panel._aiSettings=null;panel._renderTabs();panel._renderTab();
for(const oldId of ["aiBatchPrompt","aiAddQueue","aiRunQueue","aiStopQueue"]){if(content.querySelector(`#${oldId}`))throw new Error(`Legacy AI queue control still rendered: ${oldId}`);}
for(const required of ["aiRequest","aiDiet","aiNutritionGoal","aiCalories","aiIngredients","aiCalTolerance","aiMaxMissing","aiRecent","aiPreferExpiring","aiOnlyHome","aiCreate"]){if(!content.querySelector(`#${required}`))throw new Error(`Direct AI Create missing #${required}`);}
const aiLanguageRows=[...content.querySelectorAll("[data-ai-language]")];
const aiMealRows=[...content.querySelectorAll("[data-ai-meal-type]")];
if(aiLanguageRows.length!==3||aiMealRows.length<2)throw new Error("AI multi-select preferences were not rendered");
content.querySelector("#aiRequest").textContent="tomato dinner";
chooseOption(content.querySelector("#aiDiet"),"vegetarian");
chooseOption(content.querySelector("#aiNutritionGoal"),"high_protein");
setInput(content.querySelector("#aiCalories"),600);
setInput(content.querySelector("#aiMaxMissing"),2);
aiLanguageRows.forEach(row=>{const checked=["de","en"].includes(String(row.dataset.aiLanguage));row.checked=checked;if(checked)row.setAttribute("checked","");else row.removeAttribute("checked");});
aiMealRows.forEach(row=>{const checked=String(row.dataset.aiMealType)==="main";row.checked=checked;if(checked)row.setAttribute("checked","");else row.removeAttribute("checked");});
const ingredientOptions=[...content.querySelector("#aiIngredients").options];
ingredientOptions.forEach(option=>{const selected=String(option.textContent).includes("Tomato");option.selected=selected;if(selected)option.setAttribute("selected","");else option.removeAttribute("selected");});
await panel._createAiRecipe(content);
await delay(30);
if(!aiPayload)throw new Error("AI Create did not use the hardened serialized API");
if(aiPayload.diet!=="vegetarian"||aiPayload.nutrition_goal!=="high_protein")throw new Error("AI Create lost Today-style diet/nutrition preferences");
if(JSON.stringify(aiPayload.catalog_languages)!==JSON.stringify(["de","en"]))throw new Error(`AI catalog languages mismatch: ${JSON.stringify(aiPayload.catalog_languages)}`);
if(JSON.stringify(aiPayload.meal_types)!==JSON.stringify(["main"]))throw new Error(`AI meal types mismatch: ${JSON.stringify(aiPayload.meal_types)}`);
if(Number(aiPayload.calorie_target)!==600||Number(aiPayload.max_missing)!==2)throw new Error("AI calorie/missing preferences were not forwarded");
if(!Array.isArray(aiPayload.ingredients)||aiPayload.ingredients.length!==1)throw new Error("AI preferred ingredient selection was not forwarded");

await panel._send({title:"Official soup",sendVariantId:"variant-123",sendable:true,match:{safe:true}});
await delay(20);
if(!sendPayload)throw new Error("Official send did not use the multi-device API");
if(JSON.stringify(sendPayload.entry_ids)!==JSON.stringify(["dev-a","dev-b"]))throw new Error(`Multi-device send target mismatch: ${JSON.stringify(sendPayload.entry_ids)}`);

await delay(50);active=0;maxActive=0;
await Promise.all([
  panel._api("cook4me/test/serial",{n:1}),
  panel._api("cook4me/test/serial",{n:2}),
  panel._api("cook4me/test/serial",{n:3}),
]);
if(maxActive!==1)throw new Error(`Client request lane overlapped ${maxActive} requests`);

calls.length=0;
await panel._api("cook4me/v15/barcode_scan",{entry_id:"dev-a",barcode:"12345678"});
await panel._api("cook4me/v21/currency_state",{entry_id:"dev-a",language:"en",refresh:true});
await panel._api("cook4me/v7/recipe_detail",{entry_id:"dev-a",variant_id:"v1",language:"de",refresh:true});
const routed=calls.map(row=>row.type);
for(const expected of ["cook4me/v26/barcode_scan","cook4me/v24/currency_state","cook4me/v24/recipe_detail"]){if(!routed.includes(expected))throw new Error(`Active online endpoint was not routed to ${expected}: ${JSON.stringify(routed)}`);}

panel.remove();
console.log("Recipe Hub v50 orchestration smoke OK");
