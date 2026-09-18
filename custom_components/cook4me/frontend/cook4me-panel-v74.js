import "./cook4me-panel-v73.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v73");
const BUILD="2026.9.15.16";
const RESOURCES={
 today:["fullOverview","capabilities","book","today","catalog"],
 week:["capabilities","fullOverview","week","currency"],book:["capabilities","book"],
 official:["capabilities","book"],recommend:["fullOverview","capabilities","book","catalog"],
 mine:["fullOverview","capabilities","book","catalog"],
 profile:["fullOverview","capabilities","catalog","inventory","nutrition"],
 ai:["fullOverview","capabilities","book","today","catalog"],shopping:["fullOverview","shopping"],
};

class Cook4MeRecipeHubPanelV74 extends BasePanel{
 _syncSectionLoading(){
  this._v54RefreshingSections.clear();
  for(const load of this._v74SectionLoads||[]){
   if(load.context===this._prefKey())this._v54RefreshingSections.add(load.tab);
  }
 }
 _resetEntryScopedUiState(){super._resetEntryScopedUiState();this._syncSectionLoading();}
 _selectV52Tab(tab){
  this._v74Navigation={context:this._prefKey(),tab:tab==="recommend"?"today":tab};
  return super._selectV52Tab(tab);
 }
 // The older Week/Book preloader restored its captured tab after any await.
 // Load capabilities with the other section resources and preserve newer input.
 async _requestSection(tab,{missingOnly=false,force=false}={}){
  const value=String(tab||"");if(!value||!this._entryId)return;
  this._v54RequestedSections.add(value);this._grantNetworkForSection(value);
  const key=JSON.stringify([this._prefKey(),value,missingOnly,force]);
  if(this._v54RefreshTasks.has(key))return this._v54RefreshTasks.get(key);
  const task=this._refreshSection(value,{missingOnly,force}).finally(()=>this._v54RefreshTasks.delete(key));
  this._v54RefreshTasks.set(key,task);return task;
 }
 async _refreshSection(tab,{missingOnly=false,force=false}={}){
  const context=this._prefKey(),resources=RESOURCES[tab]||[];
  const wanted=missingOnly?resources.filter(resource=>!this._resourceHasData(resource)):resources;
  if(!wanted.length)return;
  const load={context,tab};this._v74SectionLoads??=new Set();this._v74SectionLoads.add(load);
  this._syncSectionLoading();this._updateBackgroundStatus();this._decorateElementLoadingStates();
  try{
   for(const resource of wanted){
    if(context!==this._prefKey())return;
    if(resource==="fullOverview")await this._loadFullOverview(true,false,force);
    else if(resource==="capabilities"){
     this._allowResource("capabilities");
     const selected=this._tab,navigation=this._v74Navigation;
     await this._loadCapabilities();
     if(context!==this._prefKey())return;
     const latest=this._v74Navigation;
     const target=latest!==navigation&&latest?.context===context?latest.tab:selected;
     if(this._tab!==target){this._tab=target;this._renderTabs();this._renderTab();}
    }
    else if(resource==="book")await this._loadBookState(true);
    else if(resource==="today")await this._loadTodayOptions();
    else if(resource==="catalog")await this._loadIngredientCatalog(this._uiIngredientLanguage(),force);
    else if(resource==="week")await this._loadWeekState();
    else if(resource==="currency")await this._loadCurrencyState(Boolean(force||this._currencyState));
    else if(resource==="shopping")await this._loadShoppingList(true);
    else if(resource==="inventory")await this._loadInventoryState();
    else if(resource==="nutrition")await this._loadNutritionSettings();
   }
  }finally{
   this._v74SectionLoads.delete(load);this._syncSectionLoading();
   if(context===this._prefKey()){
    if(this._tab===tab)this._renderTab();else this._updateBackgroundStatus();
    this._scheduleSnapshotPersist();
   }else this._updateBackgroundStatus();
  }
 }
 async _flushPreferences(){
  if(this._v63Saving||!this._v63Dirty||!this._hass?.connection)return;
  const key=this._prefKey(),entry=this._entryId,connection=this._hass.connection;
  const patch=this._v63Dirty;this._v63Dirty=null;this._v63Saving=true;
  let failed=false;
  try{await connection.sendMessagePromise({type:"cook4me/v31/ui_preferences",entry_id:entry,preferences:patch});}
  catch(_error){
   failed=true;
   if(key===this._prefKey()){
    this._v63Dirty={...patch,...this._v63Dirty};this._message(this._t("preferencesPending"),true);
   }
  }finally{
   this._v63Saving=false;
   if(key===this._prefKey())this._cachePreferences();
  }
  // Retry only a newer context after failure; an offline current context waits
  // for reconnect instead of entering an automatic retry loop.
  if(this._v63Dirty&&(!failed||key!==this._prefKey()))void this._flushPreferences();
 }
 _renderTab(){const result=super._renderTab();this.setAttribute("data-cook4me-build",BUILD);return result;}
}
customElements.define("cook4me-recipe-hub-panel-v74",Cook4MeRecipeHubPanelV74);
