import "./cook4me-panel-v54.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v54");

class Cook4MeRecipeHubPanelV55 extends BasePanel{
  constructor(){
    super();
    this._v55EntryRefreshBound=false;
  }

  get hass(){return this._hass;}
  set hass(value){
    const nextUser=String(value?.user?.id||value?.user?.name||"anonymous");
    if(this._v54CacheHydrated&&this._v54CacheUser&&nextUser!==this._v54CacheUser){
      this._resetUserScopedUiState();
    }
    super.hass=value;
  }

  _resetUserScopedUiState(){
    if(this._v54PersistTimer){clearTimeout(this._v54PersistTimer);this._v54PersistTimer=null;}
    this._entries=[];this._entryId=null;
    this._results=[];this._recommendations=[];this._opened=null;this._searchQuery="";
    this._capabilities={languages:[],defaultAiTaskAvailable:false,defaultAiTaskEntityId:null,persistentCache:true};
    this._uiPreferences={catalogLanguage:"auto",translateResults:true,lastTab:"official",recipeLanguageSelections:{},recipeServingSelections:{}};
    this._preferencesLoaded=false;this._translationPreferenceInitialized=false;
    this._bookState=null;this._todayOptions=null;this._todayResults=[];this._todayMeta=null;this._todaySettings=null;
    this._ingredientCatalog=[];this._ingredientCatalogLanguage="";this._houseIngredients=[];this._houseEntryId="";this._houseFilter="";
    this._shoppingItems=[];this._shoppingEntityId="";this._shoppingAvailable=null;
    this._inventoryLoadedEntry="";this._pendingConsumption=null;
    this._nutritionSettings=null;this._nutritionAutoFillEntry="";this._nutritionAutoFillResult=null;
    this._weekState=null;this._weekStateEntry="";this._currencyState=null;this._currencyStateEntry="";
    this._v54CacheHydrated=false;this._v54HadUiCache=false;this._v54HasCachedFullOverview=false;
    this._v54RequestedSections.clear();this._v54RefreshingSections.clear();this._v54RefreshTasks.clear();
    this._v54InitialVisibleRequested=false;this._v54SeedStarted=false;
    this._v51AllowedResources=new Set(["overview"]);
    this._v51ActivatedSections.clear();this._v51PreparedSections.clear();this._v51PreparingSections.clear();
    this._v51OverviewStarted=false;this._v51OverviewDone=true;
    this._v53BootstrapDone=false;this._v53FullOverviewDone=false;this._v53FullOverviewLoading=false;
  }

  _selectV52Tab(tab){
    const value=String(tab||"");if(!value)return;
    this._tab=value;this._opened=null;this._rememberSection?.(value);
    this._v51ActivatedSections.add(value);this._v51PreparedSections.add(value);
    this._renderTabs();
    // Cached content paints first. Normal navigation fetches only data that is
    // genuinely absent; the toolbar refresh button is the force-refresh path.
    this._renderTab();
    void this._requestSection(value,{missingOnly:true,force:false});
  }

  _resourceHasData(resource){
    if(resource==="inventory")return Boolean(this._inventoryLoadedEntry===String(this._entryId||""));
    return super._resourceHasData(resource);
  }

  _captureEntrySnapshot(entryId=this._entryId){
    super._captureEntrySnapshot(entryId);
    const id=String(entryId||"");
    const row=this._v54Cache?.perEntry?.[id];
    if(row)row.houseStateLoaded=Boolean(this._inventoryLoadedEntry===id);
  }

  _renderEntrySelect(){
    super._renderEntrySelect();
    const select=this.shadowRoot?.getElementById("entrySelect");if(!select||select.dataset.cook4meV55Entry)return;
    select.dataset.cook4meV55Entry="1";
    select.addEventListener("change",()=>{
      this._v54InitialVisibleRequested=true;
      queueMicrotask(()=>void this._requestSection(String(this._tab||"official"),{missingOnly:true,force:false}));
    });
  }
}

customElements.define("cook4me-recipe-hub-panel-v55",Cook4MeRecipeHubPanelV55);
