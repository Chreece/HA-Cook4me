import {spawnSync} from "node:child_process";
import assert from "node:assert/strict";
import {parseHTML} from "linkedom";
const {window}=parseHTML("<!doctype html><html><body></body></html>");
for(const key of ["document","customElements","HTMLElement","Node","Event","CustomEvent","MutationObserver","Element","ShadowRoot","HTMLInputElement","HTMLSelectElement"])if(window[key])globalThis[key]=window[key];
globalThis.window=window;
globalThis.requestAnimationFrame=callback=>setTimeout(callback,0);
globalThis.cancelAnimationFrame=clearTimeout;
globalThis.ResizeObserver=class{observe(){} disconnect(){}};
globalThis.CSS={escape:String};
// Linkedom exposes select.value as getter-only; browsers provide this setter.
const selectValue=Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype,"value");
Object.defineProperty(window.HTMLSelectElement.prototype,"value",{configurable:true,get:selectValue.get,set(value){for(const option of this.options)option.selected=option.value===String(value);}});
const storage=new Map();
globalThis.localStorage={getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)};

const version=process.env.COOK4ME_TEST_PANEL_VERSION||"70";
await import(`../custom_components/cook4me/frontend/cook4me-panel-v${version}-bundle.js`);
const panel=document.createElement(`cook4me-recipe-hub-panel-v${version}`),requests=[];
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
const make=(i,language="de")=>({id:`r${i}`,displayFamilyId:`family:${i}`,displayVariantId:`${i}-${language}-4`,searchVariantId:`${i}-${language}-4`,sendVariantId:language==="de"?`${i}-de-4`:null,title:"Quinoa-Feta-Salat mit Melone",canonicalName:`Garden recipe ${i}`,cover:`https://example.test/${i}.jpg`,language,selectedLanguage:language,selectedServings:4,servings:4,
 ingredients:[{ingredientId:"carrot",key:"carrot",name:"Karotte",originalName:"Karotte",displayName:"Καρότο",quantity:200,unit:"g"}],
 steps:[{functionalId:"s0",stepIndex:0,instruction:"Zutaten vorbereiten."},{functionalId:"s1",stepIndex:1,instruction:"Wassermelone in 3cm große Würfel schneiden."}],
 catalogNutrition:{perServing:{energyKcal:1000,proteinG:25,carbohydrateG:26,fatG:7,fiberG:2.5,saltG:0,sugarsG:null},coverage:{coveragePercent:40}},
 dietary:{vegan:true,vegetarian:true,pescatarian:true},mealTypes:["main"],
 match:{safe:true,dietary:{vegan:true,vegetarian:true,pescatarian:true},quantityAvailability:[{key:"carrot",name:"Karotte",coverage:0.5,status:"shortage",missingQuantity:100,missingUnit:"g"}],quantityShortages:[{key:"carrot",name:"Karotte",missingQuantity:100,missingUnit:"g"}]},
 languageVariants:["de","en","fr"].map(code=>({language:code,servingVariants:[4,6].map(servings=>({displayVariantId:`${i}-${code}-${servings}`,sendVariantId:code==="de"?`${i}-de-${servings}`:null,servings,label:String(servings)}))}))});
const all=Array.from({length:19},(_,i)=>make(i));
const filters={diet:"vegetarian",languages:["de","en","fr"],mealTypes:["breakfast","starter","salad","soup","main","side","dessert","snack"],ingredients:[],nutritionGoal:"balanced",onlyHome:false,maxCost:"",currency:"EUR"};
const capsRun=spawnSync("python",["tests/test_recipe_actions_v68.py","--capabilities"],{encoding:"utf8"});
assert.equal(capsRun.status,0,capsRun.stderr);const liveCaps=JSON.parse(capsRun.stdout).active;
const connection={sendMessagePromise:async msg=>{
 requests.push(msg);
 if(msg.type.endsWith("/capabilities"))return liveCaps;
 if(msg.type.endsWith("ui_preferences"))return {lastTab:"official",filters};
 if(msg.type.endsWith("official_search"))return {items:structuredClone(all.slice(msg.page*8,(msg.page+1)*8)),page:{number:msg.page,size:8,totalElements:all.length}};
 if(msg.type.endsWith("recipe_detail")){
  const [id,language,servings]=msg.variant_id.split("-");const row=make(Number(id),language);
  Object.assign(row,{displayVariantId:msg.variant_id,searchVariantId:msg.variant_id,sendVariantId:language==="de"?msg.variant_id:null,servings:Number(servings),selectedServings:Number(servings),presentationLanguage:"el"});row.ingredients[0].quantity=Number(servings)*50;return row;
 }
 if(msg.type.endsWith("ingredient_info"))return {ingredientInfoContract:"offline-ingredient-info-v62",ingredient:{name:"Καρότο"},officialRecipeUsage:structuredClone(all)};
 if(msg.type.endsWith("send_multi"))return {targetCount:1,sentCount:0,queuedCount:1};
 if(msg.type.endsWith("recipe_translation")){
  const run=spawnSync("python",["tests/test_translation_v70.py","--translate"],{encoding:"utf8",input:JSON.stringify(msg.recipe),timeout:20000});
  assert.equal(run.status,0,run.stderr);const result=JSON.parse(run.stdout);
  assert.equal(result.testAiCalls,3,'Incomplete output repaired in smaller requests by actual backend');
  return result;
 }
 return {};
}};
panel._entryId="one";panel._entries=[{entry_id:"one",title:"Kitchen",connected:false,state:{},profile:{houseIngredients:[]},recipes:[]},{entry_id:"two",title:"Second device",connected:false,state:{},recipes:[]}];
panel._hass={language:"el",config:{country:"DE"},user:{id:"user"},states:{},connection};
panel._capabilities={languages:filters.languages.map(code=>({code})),deviceCatalogLanguage:"de"};
panel._loadWeekState=async()=>{};panel._requestSection=async()=>{};panel._loadRecipeNutrition=async()=>{};panel._loadOverview=async()=>{};panel._loadIngredientCatalog=async()=>{};
panel._renderShell();await panel._restorePreferences();panel._tab="official";await panel._search("garden");
panel._hass.states['ai_task.local']={state:'unknown'};
panel._capabilities=liveCaps;panel._renderTab();
const content=()=>panel.shadowRoot.querySelector('#content');
const dialog=()=>panel.shadowRoot.querySelector('[data-recipe-dialog]');
const card=()=>content().querySelector('article.recipe');
const translated='Σαλάτα κινόα με φέτα και καρπούζι';
assert.equal(requests.filter(msg=>msg.type.endsWith('recipe_translation')).length,0);
// Start with fullscreen cooking (the reported failing direction), without
// first translating or expanding a result card.
card().querySelector('[data-v66-action=cook]').click();await tick();
assert.ok(dialog().hasAttribute('data-v67-cooking'));
dialog().querySelector('[data-v66-action=next]').click();await tick();
assert.equal(dialog().querySelector('[aria-current=step]').dataset.v66Step,'1');
const edition=panel._opened.displayVariantId;
dialog().querySelector('[data-v66-action=translate]').click();await tick();
assert.equal(dialog().querySelector('h2').textContent.includes(translated),true);
assert.ok(dialog().textContent.includes('Κόψτε το καρπούζι σε κύβους 3 εκ.'));
assert.equal(dialog().querySelector('[aria-current=step]').dataset.v66Step,'1','Current step survives translation');
assert.ok(dialog().hasAttribute('data-v67-cooking'));
assert.equal(panel._opened.displayVariantId,edition);
assert.equal(panel._opened.steps[1].functionalId,'s1');
assert.equal(panel._opened.steps[1].stepIndex,1);
assert.equal(card().querySelector('h3').textContent.includes(translated),true);
assert.equal(dialog().querySelector('[data-v66-action=translate]'),null);
panel._v63CloseRecipe();
assert.equal(card().querySelector('[data-v66-action=translate]'),null);
card().querySelector('[data-v66-action=expand]').click();await tick();
assert.ok(card().textContent.includes('Κόψτε το καρπούζι σε κύβους 3 εκ.'));

// Reverse direction uses the same endpoint and survives a fresh detail fetch.
const second=()=>content().querySelectorAll('article.recipe')[1];
second().querySelector('[data-v66-action=translate]').click();await tick();
second().querySelector('[data-v66-photo]').click();await tick();
assert.ok(dialog().querySelector('h2').textContent.includes(translated));
assert.ok(dialog().textContent.includes('Κόψτε το καρπούζι σε κύβους 3 εκ.'));
assert.equal(requests.filter(msg=>msg.type.endsWith('recipe_translation')).length,2);
panel._v63CloseRecipe();

// Weekly slot state differs from fullscreen state. Two clicks during the
// pending response must not launch two model operations for the same edition.
let release;
const realSend=connection.sendMessagePromise;
connection.sendMessagePromise=async msg=>{
 if(msg.type.endsWith('recipe_translation')){requests.push(msg);return new Promise(resolve=>{release=resolve;});}
 return realSend(msg);
};
const recipe=panel._results[2];await panel._showRecipe(recipe);
const before=requests.filter(msg=>msg.type.endsWith('recipe_translation')).length;
const pending=panel._v66Translate(panel._opened,panel._v66State(panel._opened));await tick();
await panel._v66Translate(recipe,panel._v66State(recipe,'weekly-slot'));
assert.equal(requests.filter(msg=>msg.type.endsWith('recipe_translation')).length,before+1);
release({available:false,reason:'incomplete_translation'});await pending;
assert.equal(panel._v70Translations.size,0,'Failed operation releases the per-edition guard');
assert.equal(panel._opened.title,'Quinoa-Feta-Salat mit Melone');
panel._v63CloseRecipe();panel.disconnectedCallback();
console.log('v70 actual translation handler repairs incomplete output in fullscreen cooking and regular cards; current step and identity preserved');process.exit(0);
