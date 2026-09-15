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

const version="69";
await import(`../custom_components/cook4me/frontend/cook4me-panel-v${version}-bundle.js`);
const panel=document.createElement(`cook4me-recipe-hub-panel-v${version}`),requests=[];
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
const make=(i,language="de")=>({id:`r${i}`,displayFamilyId:`family:${i}`,displayVariantId:`${i}-${language}-4`,searchVariantId:`${i}-${language}-4`,sendVariantId:language==="de"?`${i}-de-4`:null,title:`Garden recipe ${i}`,canonicalName:`Garden recipe ${i}`,cover:`https://example.test/${i}.jpg`,language,selectedLanguage:language,selectedServings:4,servings:4,
 ingredients:[{ingredientId:"carrot",key:"carrot",name:"Karotte",originalName:"Karotte",displayName:"Καρότο",quantity:200,unit:"g"}],
 steps:[{functionalId:"s0",stepIndex:0,instruction:"Prepare vegetables"},{functionalId:"s1",stepIndex:1,instruction:"Cook vegetables"}],
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
 if(msg.type.endsWith("recipe_translation"))return {available:true,recipe:{...msg.recipe,title:"Συνταγή κήπου",translatedTo:"el",steps:msg.recipe.steps.map((step,i)=>({...step,instruction:["Ετοιμάστε τα λαχανικά","Μαγειρέψτε τα λαχανικά"][i]}))}};
 return {};
}};
panel._entryId="one";panel._entries=[{entry_id:"one",title:"Kitchen",connected:false,state:{},profile:{houseIngredients:[]},recipes:[]},{entry_id:"two",title:"Second device",connected:false,state:{},recipes:[]}];
panel._hass={language:"el",config:{country:"DE"},user:{id:"user"},states:{},connection};
panel._capabilities={languages:filters.languages.map(code=>({code})),deviceCatalogLanguage:"de"};
panel._loadWeekState=async()=>{};panel._requestSection=async()=>{};panel._loadRecipeNutrition=async()=>{};panel._loadOverview=async()=>{};panel._loadIngredientCatalog=async()=>{};
panel._renderShell();await panel._restorePreferences();panel._tab="official";await panel._search("garden");
const content=()=>panel.shadowRoot.querySelector('#content');
const verifyCard=card=>{
 assert.ok(card.firstElementChild.classList.contains('rx-v66-title'),'Title comes first');
 const frame=card.querySelector('.rx-v69-media'),photo=frame.querySelector('[data-v66-photo]'),actions=frame.querySelector('.rx-v69-overlay');
 assert.equal(card.firstElementChild.nextElementSibling,frame,'Photo follows title');
 assert.equal(photo.parentElement,frame);assert.equal(actions.parentElement,frame);
 assert.equal(photo.querySelector('button,select'),null,'Actions are siblings, never nested buttons');
 assert.ok(actions.querySelector('[data-v66-action=send]'));
 assert.ok(actions.querySelector('[data-v66-action=expand]'));
 assert.equal(card.querySelector('.rx-v66-title button'),null);
 assert.equal(actions.querySelector('[data-v66-action=send]').querySelectorAll('ha-icon').length,1);
};
for(const tab of ['official','today','week','mine','book']){
 panel._tab=tab;panel._v66Tags=new Map();panel._todayResults=structuredClone(all);
 panel._entries[0].recipes=structuredClone(all);
 panel._bookState={favorites:structuredClone(all),recipeList:structuredClone(all)};
 panel._v67Today=()=> '2026-09-15';
 panel._weekState={weekStart:'2026-09-15',slots:all.slice(0,7).map((recipe,index)=>({id:`slot-${index}`,date:`2026-09-${15+index}`,mealType:'breakfast',recipe})),settings:{}};
 panel._renderTabs();panel._renderTab();panel._modernizeSoon();await tick();
 const cards=[...content().querySelectorAll('article.recipe')];assert.ok(cards.length,tab);
 for(const card of cards)verifyCard(card);
 assert.ok(panel.shadowRoot.querySelector('[data-tab=week] svg[data-v67-week-icon]'));
}
panel._tab='official';panel._renderTab();await tick();
let card=content().querySelector('article.recipe');
card.querySelector('[data-v66-action=expand]').click();await tick();
card=content().querySelector('article.recipe');verifyCard(card);
assert.ok(card.querySelector('.rx-v66-body'));assert.equal(panel.shadowRoot.querySelector('[data-recipe-dialog]'),null,'Action click does not open the photo');
card.querySelector('[data-v66-photo]').click();await tick();
let dialog=panel.shadowRoot.querySelector('[data-recipe-dialog]');assert.ok(dialog);
assert.equal(dialog.querySelector('.rx-dialog').firstElementChild.tagName,'HEADER');
assert.ok(dialog.querySelector('.rx-v69-media .rx-v69-overlay [data-v66-action=send]'));
assert.equal(dialog.querySelector('.rx-v66-full-photo button'),null);
dialog.querySelector('[data-v66-action=cook]').click();await tick();
dialog=panel.shadowRoot.querySelector('[data-recipe-dialog]');assert.ok(dialog.hasAttribute('data-v67-cooking'));
assert.ok(dialog.querySelector('[aria-current=step]'));
assert.ok(dialog.querySelector('.rx-v69-media .rx-v69-overlay'));
const css=panel.shadowRoot.querySelector('#cook4meV69Styles').textContent;
assert.ok(css.includes('opacity:.5'));assert.ok(css.includes(':has(button:hover,select:hover)'));assert.ok(css.includes(':focus-within'));assert.ok(css.includes('{opacity:1}'));
assert.ok(css.includes('position:absolute'));assert.ok(css.includes('inset:auto 0 0'));
panel._v63CloseRecipe();panel.disconnectedCallback();console.log('v69 title-first cards, photo action overlays, deferred icons and fullscreen cooking passed');process.exit(0);
