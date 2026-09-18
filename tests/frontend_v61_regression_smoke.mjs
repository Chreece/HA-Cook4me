import assert from "node:assert/strict";
import {parseHTML} from "linkedom";

const {window}=parseHTML("<!doctype html><html><body></body></html>");
for(const key of ["document","customElements","HTMLElement","Node","Event","CustomEvent","MutationObserver","Element","ShadowRoot","HTMLInputElement","HTMLSelectElement"])if(window[key])globalThis[key]=window[key];
globalThis.window=window;
globalThis.requestAnimationFrame=callback=>setTimeout(callback,0);
globalThis.cancelAnimationFrame=clearTimeout;
globalThis.ResizeObserver=class{observe(){} disconnect(){}};
globalThis.CSS={escape:String};
const storage=new Map();
globalThis.localStorage={getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)};
await import("../custom_components/cook4me/frontend/cook4me-panel-v61.js");

const panel=document.createElement("cook4me-recipe-hub-panel-v61");
panel._hass={language:"el",user:{id:"test"},states:{},connection:{sendMessagePromise:async()=>({items:[]})}};
panel._entryId="entry";
panel._entries=[{entry_id:"entry",title:"Cook4Me",connected:false}];
panel._capabilities={languages:[{code:"de"},{code:"fr"},{code:"it"}],deviceCatalogLanguage:"de"};
panel._catalogLanguage="auto";
assert.deepEqual(panel._loadOfficialLanguages(),["de","fr","it"],"New search should include all source catalogs");
panel._saveOfficialLanguages(["de-DE"]);
assert.deepEqual(panel._loadOfficialLanguages(),["de"],"Explicit selection must survive normalization");
panel._saveOfficialLanguages(["el"]);
assert.deepEqual(panel._loadOfficialLanguages(),["de","fr","it"],"Stale unsupported source language must not hide the catalog");
panel._saveOfficialLanguages([]);
assert.deepEqual(panel._loadOfficialLanguages(),[],"Deselect all must not secretly select a fallback");
panel._entryId="other";
panel._capabilities={};
assert.equal(panel._loadOfficialLanguages().length,21,"Audited source languages must remain available while options load");
panel._capabilities={languages:[{code:"de"},{code:"it"}]};
assert.deepEqual(panel._loadOfficialLanguages(),["de","it"]);
panel._saveOfficialLanguages(["de"]);

panel._renderShell();
const content=panel.shadowRoot.querySelector("#content");
panel._renderOfficial(content);
const picker=content.querySelector("#officialCatalogLanguages");
assert.ok(picker,"Catalog picker must render");
assert.ok(picker.querySelector("[data-close-catalog]"),"Mobile picker needs an explicit close control");
picker.setAttribute("open","");
panel._v60OutsidePointer({composedPath:()=>[picker.querySelector("input"),picker]});
assert.ok(picker.hasAttribute("open"),"Picking a language must keep the picker open");
panel._v60OutsidePointer({composedPath:()=>[content]});
assert.ok(!picker.hasAttribute("open"),"Outside pointer must close the picker");
picker.setAttribute("open","");
picker.querySelector("[data-close-catalog]").click();
assert.ok(!picker.hasAttribute("open"));
panel.disconnectedCallback();
const hass=panel._hass;panel._hass=null;panel.connectedCallback();panel._hass=hass;
picker.setAttribute("open","");
const escape=new Event("keydown");Object.defineProperty(escape,"key",{value:"Escape"});document.dispatchEvent(escape);
assert.ok(!picker.hasAttribute("open"),"Escape handler must be restored after reconnect");

const missing={catalogNutrition:{perServing:{},totals:{energyKcal:null},coverage:0}};
assert.equal(panel._v60Nutrition(missing),null,"Missing nutrition is not zero nutrition");
const partial={title:"Test",searchVariantId:"test",language:"de",ingredients:[],steps:[],match:{safe:true},catalogNutrition:{perServing:{},totals:{energyKcal:100,protein:0,fat:null,fiber:""},coverage:0.5,estimated:true}};
let data=panel._v60Nutrition(partial);
assert.equal(data.energy,100);assert.equal(data.protein,0);assert.equal(data.fat,null);assert.equal(data.fiber,null);assert.equal(data.perServing,false);
assert.equal(panel._v60Nutrition({nutrition:{totals:{energyKcal:50}}}).coverage,null);
assert.equal(panel._v60Nutrition({catalogNutrition:{perServing:{}},nutrition:{perServing:{energyKcal:40}}}).energy,40);
const card=panel._recipeCard(partial);
assert.equal((card.match(/100 kcal/g)||[]).length,1,"Nutrition values should appear once");
assert.ok(card.includes(panel._t("recipeTotal")));assert.ok(card.includes(panel._t("partialNutrition")));
const perServing=panel._v60Nutrition({...partial,catalogNutrition:{perServing:{energyKcal:25},totals:{energyKcal:100}}});
assert.equal(perServing.energy,25);assert.equal(perServing.perServing,true);

const ingredient={ingredientId:"M_FOOD_246",foodKey:"M_FOOD_246",foodName:"Olive oil",quantity:1,unit:"tbsp"};
const ingredientInfo={ingredient:{name:"Olive oil"},stock:null,history:[],officialRecipeUsage:[],savedRecipeUsage:[],
  catalogNutrition:{basisQuantity:100,basisUnit:"g",estimated:true,values:{energyKcal:884,protein:0,carbohydrates:0,fat:null,fiber:"",sodium:0.002}},
  genericNutrition:{nutrition:{basisQuantity:100,basisUnit:"g",values:{energyKcal:999}}},
  exactNutritionLots:[{productName:"Test product",nutrition:{basisQuantity:100,basisUnit:"ml",values:{energyKcal:200,fat:5}}}],
};
let ingredientRequest;
panel._hass.language="en";
panel._hass.connection.sendMessagePromise=async msg=>{ingredientRequest=msg;return ingredientInfo;};
panel._cook4meApiTail=new Promise(()=>{});
const ingredientCard=document.createElement("div");ingredientCard.innerHTML='<div class="ingredients"></div>';
panel._decorateCardIngredients(ingredientCard,{ingredients:[ingredient]});
ingredientCard.querySelector(".ingredient-pill").click();
await new Promise(resolve=>setTimeout(resolve,0));
assert.equal(ingredientRequest.type,"cook4me/v19/ingredient_info");
assert.equal(ingredientRequest.ingredient.ingredientId,"M_FOOD_246","Click must retain the actual catalog identity");
const ingredientDialog=panel.shadowRoot.querySelector(".rx-overlay");
assert.ok(ingredientDialog,"Clicking a recipe ingredient should open its popup");
const reference=ingredientDialog.querySelector('[data-ingredient-nutrition="catalog"]');
assert.ok(reference.textContent.includes("per 100 g"));
assert.ok(reference.textContent.includes("884 kcal"));
assert.ok(reference.querySelector('[data-nutrient="protein"]').textContent.includes("0 g"));
assert.ok(reference.querySelector('[data-nutrient="sodium"]').textContent.includes("0.002 g"));
assert.equal(reference.querySelector('[data-nutrient="fat"]'),null,"Unknown fat must not be shown as zero");
assert.equal(reference.querySelector('[data-nutrient="fiber"]'),null);
assert.equal(ingredientDialog.querySelector('[data-ingredient-nutrition="saved"]'),null,"Catalog reference takes precedence over stale generic cache");
const product=ingredientDialog.querySelector('[data-ingredient-nutrition="product"]');
assert.ok(product.textContent.includes("Test product"));assert.ok(product.textContent.includes("per 100 ml"));
assert.ok(product.textContent.includes("200 kcal"));
assert.ok(ingredientDialog.querySelector("[data-shop]"),"Shopping action remains available");
ingredientDialog.querySelector("[data-close]").click();assert.equal(panel.shadowRoot.querySelector(".rx-overlay"),null);
const translatedRecipe={ingredients:[{...ingredient}],sourceLanguage:"de"};
panel._applyTranslation(translatedRecipe,{ingredients:["ελαιόλαδο"]});
await panel._showIngredientInfo(translatedRecipe.ingredients[0],translatedRecipe);
assert.equal(ingredientRequest.ingredient.ingredientId,"M_FOOD_246","Translated display text must still open the original catalog ingredient");
panel.shadowRoot.querySelector(".rx-overlay [data-close]").click();
await panel._showIngredientInfo("same label",{ingredients:["same label","same label"],_nutritionIngredients:[ingredient,{ingredientId:"different"}]});
assert.deepEqual(ingredientRequest.ingredient,{name:"same label"},"Ambiguous translated rows must not receive a guessed identity");
panel.shadowRoot.querySelector(".rx-overlay [data-close]").click();
const fallback=panel._ingredientNutritionHtml({catalogNutrition:{values:{energyKcal:null}},genericNutrition:{nutrition:{basisQuantity:100,basisUnit:"ml",values:{energyKcal:50}}}});
assert.ok(fallback.includes('data-ingredient-nutrition="saved"'));assert.ok(fallback.includes("per 100 ml"));
assert.ok(panel._ingredientNutritionHtml({}).includes("data-ingredient-nutrition-unavailable"));
for(const [language,basis] of [["de","pro 100 g"],["el","ανά 100 g"]]){
  panel._hass.language=language;assert.ok(panel._ingredientNutritionHtml(ingredientInfo).includes(basis));
}

const deferred=()=>{let resolve;const promise=new Promise(done=>resolve=done);return {promise,resolve};};
const requests=[];const translation=deferred();
panel._hass.connection.sendMessagePromise=msg=>{const request=deferred();requests.push({msg,...request});return request.promise;};
panel._shouldTranslate=()=>true;panel._translationNeeded=()=>true;
panel._translateItems=()=>translation.promise;
panel._tab="official";
let renders=0;panel._renderTab=()=>{renders++;};
// A pending cloud operation must not delay an immutable catalog read.
panel._cook4meApiTail=new Promise(()=>{});
const first=panel._search("ριζότο");
assert.equal(requests.length,1);assert.equal(requests[0].msg.query_language,"el");assert.deepEqual(requests[0].msg.languages,["de"]);
requests[0].resolve({items:[{...partial,title:"First"}]});
await first;
assert.equal(panel._results[0].title,"First","Local results must appear while translation is still pending");
assert.ok(renders>0);
const old=panel._search("old"),latest=panel._search("latest");
requests[2].resolve({items:[{...partial,title:"Latest"}]});await latest;
requests[1].resolve({items:[{...partial,title:"Old"}]});await old;
assert.equal(panel._results[0].title,"Latest","An older search must not overwrite newer results");
translation.resolve();await Promise.resolve();
panel._saveOfficialLanguages([]);
const count=requests.length;await panel._search("risotto");
assert.equal(requests.length,count,"Explicitly deselected catalogs must not trigger an all-catalog search");
panel.disconnectedCallback();
console.log("v61 offline search, source languages, reconnect, nutrition, and stale response regressions OK");
