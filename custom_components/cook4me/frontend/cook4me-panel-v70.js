import "./cook4me-panel-v69.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v69");
const BUILD="2026.9.15.12";

class Cook4MeRecipeHubPanelV70 extends BasePanel{
 async _v66Translate(recipe,state){
  // Weekly slots and fullscreen have separate view states. Share the pending
  // action for this edition so changing views cannot start a second AI job.
  this._v70Translations??=new Set();
  const key=JSON.stringify([this._prefKey(),recipe.displayVariantId||this._recipeKey(recipe),this._uiIngredientLanguage()]);
  if(this._v70Translations.has(key))return;
  this._v70Translations.add(key);
  try{return await super._v66Translate(recipe,state);}
  finally{this._v70Translations.delete(key);}
 }
 async _api(type,data={}){
  if(type.endsWith("/recipe_translation")){
   // Freeze the source text while hydration, stock and cooking updates render.
   const result=await super._api(type,{...data,recipe:structuredClone(data.recipe)});
   if(result?.reason==="instructions_unavailable")throw new Error(this._t("instructionsUnavailable"));
   return result;
  }
  return super._api(type,data);
 }
 _renderTab(){const result=super._renderTab();this.setAttribute("data-cook4me-build",BUILD);return result;}
}
customElements.define("cook4me-recipe-hub-panel-v70",Cook4MeRecipeHubPanelV70);
