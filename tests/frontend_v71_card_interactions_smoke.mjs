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

const version=process.env.COOK4ME_TEST_PANEL_VERSION||"71";
await import(`../custom_components/cook4me/frontend/cook4me-panel-v${version}-bundle.js`);
const panel=document.createElement(`cook4me-recipe-hub-panel-v${version}`),requests=[];
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
const make=(i,language="de")=>({id:`r${i}`,displayFamilyId:`family:${i}`,displayVariantId:`${i}-${language}-4`,searchVariantId:`${i}-${language}-4`,sendVariantId:language==="de"?`${i}-de-4`:null,source:"release_offline",title:`Garden recipe ${i}`,canonicalName:`Garden recipe ${i}`,cover:`https://example.test/${i}.jpg`,language,selectedLanguage:language,selectedServings:4,servings:4,
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
 if(msg.type.endsWith('/book_toggle')){
  const key=panel._recipeKeyLocal(msg.recipe),rows=panel._bookState[msg.collection];
  const index=rows.findIndex(row=>panel._recipeKeyLocal(row)===key);
  if(msg.remove||index>=0){if(index>=0)rows.splice(index,1);}else rows.push({...msg.recipe,bookKey:key});
  return structuredClone(panel._bookState);
 }
 if(msg.type==='cook4me/recipe_delete'){
  assert.equal(msg.recipe_id,'local-one','Official favorites must never call local deletion');
  return {deleted:true,book:{favorites:[],recipeList:[],queuedSend:null}};
 }
 if(msg.type.endsWith("recipe_translation"))return {available:true,recipe:{...msg.recipe,title:"Συνταγή κήπου",translatedTo:"el",steps:msg.recipe.steps.map((step,i)=>({...step,instruction:["Ετοιμάστε τα λαχανικά","Μαγειρέψτε τα λαχανικά"][i]}))}};
 return {};
}};
panel._entryId="one";panel._entries=[{entry_id:"one",title:"Kitchen",connected:false,state:{},profile:{houseIngredients:[]},recipes:[]},{entry_id:"two",title:"Second device",connected:false,state:{},recipes:[]}];
panel._hass={language:"el",config:{country:"DE"},user:{id:"user"},states:{},connection};
panel._capabilities={languages:filters.languages.map(code=>({code})),deviceCatalogLanguage:"de"};
panel._loadWeekState=async()=>{};panel._requestSection=async()=>{};panel._loadRecipeNutrition=async()=>{};panel._loadOverview=async()=>{};panel._loadIngredientCatalog=async()=>{};
panel._renderShell();await panel._restorePreferences();panel._tab="official";await panel._search("garden");
const content=()=>panel.shadowRoot.querySelector('#content'),dialog=()=>panel.shadowRoot.querySelector('[data-recipe-dialog]');
const key=(code)=>{const event=new Event('keydown',{bubbles:true,cancelable:true});Object.defineProperty(event,'key',{value:code});return event;};
const card=()=>content().querySelector('article.recipe');
for(const tab of ['official','today','week','mine','book']){
 panel._tab=tab;panel._v66Tags=new Map();panel._v66States=new Map();panel._todayResults=structuredClone(all);
 panel._entries[0].recipes=structuredClone(all);
 panel._bookState={favorites:structuredClone(all),recipeList:[],queuedSend:null};
 panel._v67Today=()=> '2026-09-15';
 panel._weekState={weekStart:'2026-09-15',slots:[{id:'slot',date:'2026-09-15',mealType:'breakfast',recipe:all[0]}],settings:{}};
 panel._renderTab();await tick();
 const before=requests.filter(msg=>msg.type.endsWith('recipe_detail')).length;
 card().querySelector('h3').click();await tick();
 assert.ok(dialog(),`${tab}: title opens fullscreen`);
 assert.equal(requests.filter(msg=>msg.type.endsWith('recipe_detail')).length,before+1,'Exactly one detail fetch');
 panel._v63CloseRecipe();card().click();await tick();assert.ok(dialog(),`${tab}: card background opens fullscreen`);panel._v63CloseRecipe();
 card().dispatchEvent(key('Enter'));await tick();assert.ok(dialog(),`${tab}: keyboard opens fullscreen`);panel._v63CloseRecipe();
 card().querySelector('[data-v66-action=expand]').click();await tick();assert.equal(dialog(),null,'Expand is independent');
 card().querySelector('summary').click();await tick();assert.equal(dialog(),null,'Disclosure is independent');
 const select=card().querySelector('[data-v66-language]');select.dispatchEvent(key(' '));select.click();await tick();assert.equal(dialog(),null,'Select is independent');
 card().querySelector('[data-v66-photo]').click();await tick();assert.ok(dialog());panel._v63CloseRecipe();
}
// Official source="release_offline" formerly received a local Delete action
// because the legacy book renderer only recognized two provider source names.
panel._tab='book';const favorite=make(42);delete favorite.id;
favorite.bookKey='v:42-de-4';panel._bookState={favorites:[favorite],recipeList:[structuredClone(favorite)],queuedSend:null};
panel._renderTab();await tick();
assert.ok(panel._isFavorite(favorite));assert.equal(panel._recipeKeyLocal({variantFunctionalId:'42-de-4'}),'v:42-de-4');
assert.equal(card().querySelector('[data-v66-action=delete]'),null);
assert.equal(card().querySelector('[data-v66-action=send]').disabled,false);
assert.ok(card().querySelector('[data-v71-remove]'));
card().querySelector('[data-v71-remove]').click();await tick();
assert.equal(panel._bookState.favorites.length,0);assert.equal(panel._bookState.recipeList.length,1);
assert.equal(dialog(),null);assert.equal(requests.filter(msg=>msg.type==='cook4me/recipe_delete').length,0);
// Fullscreen removal acts on its source collection and closes only that dialog.
card().querySelector('h3').click();await tick();assert.ok(dialog().querySelector('[data-v71-remove]'));
dialog().querySelector('[data-v71-remove]').click();await tick();
assert.equal(panel._bookState.recipeList.length,0);assert.equal(dialog(),null);

// The actual My recipes Delete action removes a favorited local recipe and
// adopts the backend's cleaned collections immediately, without stale cards.
const local={id:'local-one',source:'manual',title:'My vegetable soup',language:'de',servings:2,ingredients:[],steps:['Stir']};
panel._entries[0].recipes=[local];panel._bookState={favorites:[{...local,bookKey:'local:local-one'}],recipeList:[]};
panel._tab='mine';panel._renderTab();await tick();assert.ok(panel._isFavorite(local));
card().querySelector('[data-v66-action=delete]').click();await tick();
assert.equal(panel._entries[0].recipes.length,0);assert.equal(panel._bookState.favorites.length,0);assert.equal(card(),null);
panel._entries[0].recipes=[local];panel._bookState={favorites:[{...local,bookKey:'local:local-one'}],recipeList:[]};
panel._tab='book';panel._renderTab();await tick();
card().querySelector('[data-v66-action=cook]').click();await tick();
assert.ok(dialog().hasAttribute('data-v67-cooking'));
assert.equal(dialog().querySelector('[data-v66-action=delete]'),null,'Favorite cooking keeps collection-removal semantics');
dialog().querySelector('[data-v71-remove]').click();await tick();
assert.equal(panel._bookState.favorites.length,0);assert.equal(panel._entries[0].recipes.length,1,'Removing a cooking favorite preserves its local original');

// Fixed geometry includes placeholders; fit long titles down to a readable
// minimum. Emulate layout metrics because linkedom has no layout engine.
panel._tab='official';panel._renderTab();await tick();
const title=card().querySelector('h3'),box=title.parentElement;
title.textContent='A long multilingual recipe title with vegetables and noodles';
Object.defineProperties(box,{clientWidth:{get:()=>190},clientHeight:{get:()=>88}});
Object.defineProperties(title,{clientWidth:{get:()=>162},scrollWidth:{get:()=>162},scrollHeight:{get:()=>{
 const size=parseFloat(title.style.fontSize)||20;return Math.ceil(title.textContent.length/Math.floor(162/(size*.5)))*size*1.25;
}}});
panel._v71FitTitle(title);assert.ok(parseFloat(title.style.fontSize)<20);assert.ok(parseFloat(title.style.fontSize)>=12);assert.ok(title.scrollHeight<=60);
title.textContent='Soup';panel._v71FitTitle(title);assert.ok(parseFloat(title.style.fontSize)>19,'Short title restores normal size');
const css=panel.shadowRoot.querySelector('#cook4meV71Styles').textContent;
assert.ok(css.includes('justify-content:center'));assert.ok(css.includes('height:310px'));
assert.ok(css.includes('height:88px'));assert.ok(css.includes('height:220px'));assert.ok(css.includes('height:600px'));
panel.disconnectedCallback();console.log('v71 centered controls, uniform card geometry, title fitting, whole-card/keyboard opening and favorite/local removal passed');process.exit(0);
