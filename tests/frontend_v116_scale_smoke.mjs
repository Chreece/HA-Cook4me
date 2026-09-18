import assert from "node:assert/strict";
import {parseHTML} from "linkedom";

const {window}=parseHTML("<!doctype html><html><body></body></html>");
for(const key of ["document","customElements","HTMLElement","Node","Event","CustomEvent","MutationObserver","Element","ShadowRoot","HTMLInputElement","HTMLSelectElement","Option"])if(window[key])globalThis[key]=window[key];
globalThis.window=window;
globalThis.requestAnimationFrame=callback=>setTimeout(callback,0);
globalThis.cancelAnimationFrame=clearTimeout;
globalThis.ResizeObserver=class{observe(){} disconnect(){}};
globalThis.CSS={escape:String};
const storage=new Map();
globalThis.localStorage={getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)};

const selectValue=Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype,"value");
if(selectValue?.get)Object.defineProperty(window.HTMLSelectElement.prototype,"value",{configurable:true,get:selectValue.get,set(value){for(const option of this.options)option.selected=option.value===String(value);}});

await import("../custom_components/cook4me/frontend/cook4me-panel-v116-bundle.js");
const panel=document.createElement("cook4me-recipe-hub-panel-v116");
const calls=[];
panel._entryId="one";
panel._entries=[{entry_id:"one",title:"Cook4Me",connected:true,state:{},recipes:[],profile:{houseIngredients:[],householdMembers:[],diet:"vegetarian",allergies:[],avoid:[],preferences:[]}}];
panel._houseIngredients=[];
panel._capabilities={ingredientCatalogLanguage:"en",deviceCatalogLanguage:"en"};
panel._requestSection=async()=>{};
panel._loadIngredientCatalog=async()=>{};
panel._loadNutritionSettings=async()=>{};
panel._loadFoodState=async()=>{};
panel._loadInventoryState=async()=>{};
panel._loadOverview=async()=>{};
panel._loadBookState=async()=>{};
panel._hass={
 language:"en",
 user:{id:"scale-test"},
 states:{
  "sensor.cosori_measurement":{state:"125.4",attributes:{unit_of_measurement:"g",friendly_name:"COSORI Nutrition Scale Measurement"}},
  "binary_sensor.cosori_stable":{state:"on",attributes:{}},
  "binary_sensor.cosori_connected":{state:"on",attributes:{}},
 },
 connection:{sendMessagePromise:async()=>({})},
 callService:async(domain,service,data)=>calls.push({domain,service,data}),
};
const scaleState={
 selectedEntityId:"sensor.cosori_measurement",
 candidates:[{entityId:"sensor.cosori_measurement",name:"COSORI Nutrition Scale Measurement",provider:"VeSync Local BT",adapter:"vesync_local_bt",available:true,unit:"g"}],
 reading:{entityId:"sensor.cosori_measurement",available:true,grams:125.4,provider:"VeSync Local BT",adapter:"vesync_local_bt",stableEntityId:"binary_sensor.cosori_stable",connectedEntityId:"binary_sensor.cosori_connected",tareButtonEntityId:"button.cosori_tare",nativeTare:true},
 containers:[],session:null,leftovers:[],
};
panel._api=async(type,payload={})=>{
 if(type==="cook4me/v37/scale_state")return structuredClone(scaleState);
 if(type==="cook4me/v37/scale_select")return {...structuredClone(scaleState),selectedEntityId:payload.entity_id};
 if(type==="cook4me/v37/container_save")return structuredClone(scaleState);
 if(type==="cook4me/v37/container_delete")return structuredClone(scaleState);
 return {};
};
panel._renderShell();
panel._tab="profile";
panel._renderTab();
await new Promise(resolve=>setTimeout(resolve,20));
const root=panel.shadowRoot;
assert.ok(root.querySelector("#v116Scale"),"Smart scale card is present on the current v115 profile UI");
assert.match(root.querySelector("#v116Entity").textContent,/COSORI Nutrition Scale Measurement/);
assert.match(root.querySelector("#v116Entity").textContent,/VeSync Local BT/);
assert.equal(root.querySelector("[data-v116-live]").textContent,"125.4 g");
assert.match(root.querySelector("[data-v116-meta]").textContent,/Stable/);
assert.match(root.querySelector("[data-v116-meta]").textContent,/Connected/);

root.querySelector("#v116Tare").click();
await new Promise(resolve=>setTimeout(resolve,0));
assert.deepEqual(calls.at(-1),{domain:"button",service:"press",data:{entity_id:"button.cosori_tare"}});

const recipe={title:"Rice",functionalId:"RICE",servings:2,ingredients:[{key:"M_FOOD_RICE",name:"Rice",quantity:250,unit:"g"}],steps:[{text:"Cook"}]};
const detail=panel._detailHtml(recipe);
assert.match(detail,/data-v116-recipe/);
assert.match(detail,/250 g/);

panel._v116Scale=structuredClone(scaleState);
panel._v116Scale.reading.stableEntityId="binary_sensor.cosori_stable";
panel._hass.states["binary_sensor.cosori_stable"].state="off";
assert.equal(panel._v116Net({stable:true}),null,"Explicitly unstable smart-scale readings are not recorded");
panel._hass.states["binary_sensor.cosori_stable"].state="on";
assert.equal(panel._v116Net({stable:true}),125.4);

console.log("v116 smart-scale card, sleeping-adapter metadata, native tare and stable-reading guard passed");
