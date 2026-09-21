import "./cook4me-panel-v67.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v67");
const BUILD="2026.9.15.10";
const TABS={today:"calendar-today",week:"calendar-week",official:"pot-steam-outline",book:"book-heart-outline",mine:"notebook-edit-outline",profile:"basket-outline",shopping:"cart-outline",ai:"creation"};
const CALENDAR='<svg data-v67-week-icon viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18M7 14h2m2 0h2m2 0h2M7 18h2m2 0h2m2 0h2"/></svg>';

class Cook4MeRecipeHubPanelV68 extends BasePanel{
 _resourceHasData(resource){return resource==="capabilities"?Array.isArray(this._capabilities?.localAiTaskEntityIds)&&super._resourceHasData(resource):super._resourceHasData(resource);}
 async _requestSection(tab,options={}){
  if(this._entryId&&["week","book"].includes(tab)&&(!this._resourceHasData("capabilities")||options.force)){
   this._allowResource("capabilities");const selected=this._tab;await this._loadCapabilities();
   if(this._tab!==selected){this._tab=selected;this._renderTabs();this._renderTab();}
  }
  return super._requestSection(tab,options);
 }
 _modernizeTabs(){
  // Own the deferred decorator too: the legacy table omitted Week and
  // replaced the calendar with circle-small after the initial render.
  this.shadowRoot?.querySelectorAll('#tabs [data-tab]').forEach(button=>{
   const tab=button.dataset.tab,icon=TABS[tab];if(!icon)return;
   if(tab==="week"&&button.querySelector("svg[data-v67-week-icon]"))return;
   if(tab!=="week"&&button.querySelector(":scope > ha-icon.rx-tab-icon")?.getAttribute("icon")===`mdi:${icon}`)return;
   button.innerHTML=`${tab==="week"?CALENDAR:`<ha-icon class="rx-tab-icon" icon="mdi:${icon}" aria-hidden="true"></ha-icon>`}<span>${this._escape(this._t(tab))}</span>`;
   button.dataset.rxTabIcon=icon;button.title=this._t(tab);
  });
 }
 _buttonIcon(button){return button.hasAttribute("data-v66-action")?null:super._buttonIcon(button);}
 _v66LocalAiAvailable(){
  const caps=this._capabilities||{},ids=caps.localAiTaskEntityIds||[caps.localAiTaskEntityId].filter(Boolean);
  // Unknown is a valid, never-used AI Task; unavailable is the offline state.
  return ids.some(id=>{const state=this._hass?.states?.[id];return state&&state.state!=="unavailable";});
 }
 get hass(){return super.hass;}
 set hass(value){
  const before=this._v66LocalAiAvailable();super.hass=value;
  if(before!==this._v66LocalAiAvailable()&&this.shadowRoot?.getElementById("content")){
   this._renderTab();if(this._opened)this._renderRecipeDialog();
  }
 }
 _missingIngredientObjects(recipe){
  return (super._missingIngredientObjects(recipe)||[]).map(row=>{
   if(!row||typeof row!=="object")return row;
   const key=String(row.ingredientId||row.foodKey||row.key||"");
   const sources=(recipe.ingredients||[]).filter(source=>source&&typeof source==="object"&&(key?
    [source.ingredientId,source.foodKey,source.key].some(value=>String(value||"")===key):source.name===row.name));
   if(sources.length!==1)return row;
   const source=sources[0];return {...source,...row,originalName:source.originalName||source.name||source.foodName||row.name};
  });
 }
 async _api(type,data={}){
  if(type.endsWith("/shopping_add")||type.endsWith("/week_add_shopping"))data={...data,ui_language:data.ui_language||this._uiIngredientLanguage()};
  return super._api(type,data);
 }
 async _v66LoadRecipe(recipe,custom,state,force=false){
  const variant=recipe.displayVariantId,key=this._prefKey();
  const translated=recipe.translatedTo?{title:recipe.title,originalTitle:recipe.originalTitle,steps:recipe.steps,translatedTo:recipe.translatedTo,translationMethod:recipe.translationMethod}:null;
  await super._v66LoadRecipe(recipe,custom,state,force);
  if(translated&&key===this._prefKey()&&variant===recipe.displayVariantId){
   Object.assign(recipe,translated);this._renderTab();if(this._opened===recipe)this._renderRecipeDialog();
  }
 }
 async _v66Translate(recipe,state){
  if(!this._v66LocalAiAvailable()||state.translating)return;
  state.translating=true;
  const key=this._prefKey(),language=this._uiIngredientLanguage();
  let job;
  try{
   if(!recipe.steps?.length)await this._v66LoadRecipe(recipe,!this._isOfficialRecipe(recipe),state);
   if(key!==this._prefKey()||language!==this._uiIngredientLanguage()||state.error)return;
   if(!recipe.steps?.length)throw new Error(this._t("instructionsUnavailable"));
   if(!this._v66LocalAiAvailable())throw new Error(this._t("translationUnavailable"));
   const variant=recipe.displayVariantId;
   job=this._processStart(this._t("translateRecipeUi"),recipe.title||"");
   const result=await this._api("cook4me/v31/recipe_translation",{entry_id:this._entryId,recipe,target_language:language});
   if(key!==this._prefKey()||language!==this._uiIngredientLanguage()||variant!==recipe.displayVariantId)return;
   if(!result?.available)throw new Error(this._t("translationUnavailable"));
   Object.assign(recipe,result.recipe);state.error="";
   // The fullscreen dialog and list may hold distinct copies of this edition.
   const text={title:recipe.title,originalTitle:recipe.originalTitle,steps:recipe.steps,translatedTo:recipe.translatedTo,translationMethod:recipe.translationMethod};
   const copies=[this._opened,...[...(this._v66Refs?.values()||[])].map(row=>row.recipe)];
   for(const copy of copies)if(copy&&(copy===recipe||(variant&&copy.displayVariantId===variant)))Object.assign(copy,text);
   this._renderTab();if(this._opened)this._renderRecipeDialog();
  }catch(error){const message=`${this._t("error")}: ${error.message||error}`;if(job)this._v59FailProcess(job,message);else this._message(message,true);}
  finally{state.translating=false;if(job)this._processEnd(job);}
 }
 _renderTab(){const result=super._renderTab();this.setAttribute("data-cook4me-build",BUILD);return result;}
}
customElements.define("cook4me-recipe-hub-panel-v68",Cook4MeRecipeHubPanelV68);
