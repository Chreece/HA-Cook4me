import "./cook4me-panel-v54.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v54");

class Cook4MeRecipeHubPanelV55 extends BasePanel{
  get hass(){return this._hass;}
  set hass(value){
    const nextUser=String(value?.user?.id||value?.user?.name||"anonymous");
    if(this._v54CacheHydrated&&this._v54CacheUser&&nextUser!==this._v54CacheUser){
      this._resetUserScopedUiState();
      // Never leave the previous user's cached DOM visible while the next
      // user's snapshot/bootstrap is being selected.
      this.shadowRoot?.replaceChildren();
    }
    const firstPaint=!this.shadowRoot?.innerHTML;
    super.hass=value;
    if(firstPaint&&this._v54HadUiCache){
      // Cached device/header/content are useful immediately. Bootstrap is only
      // the small live correction that follows this paint.
      this._renderEntrySelect();this._updateHeader();this._renderTab();
    }
  }

  _renderShell(){
    super._renderShell();
    const original=this.shadowRoot?.getElementById("refresh");if(!original)return;
    if(original.dataset.cook4meV55RefreshAuthoritative==="1")return;
    // Base v3 and v54 both attached refresh handlers. Replace the node so one
    // user click has exactly one owner and cannot issue duplicate overviews.
    const refresh=original.cloneNode(true);
    refresh.dataset.cook4meV55RefreshAuthoritative="1";
    original.replaceWith(refresh);
    refresh.addEventListener("click",event=>{
      event.preventDefault();event.stopPropagation();
      void this._explicitRefresh();
    });
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

  _resetEntryScopedUiState(){
    this._results=[];this._recommendations=[];this._opened=null;this._searchQuery="";
    this._capabilities={languages:[],defaultAiTaskAvailable:false,defaultAiTaskEntityId:null,persistentCache:true};
    this._preferencesLoaded=false;this._translationPreferenceInitialized=false;
    this._bookState=null;this._todayOptions=null;this._todayResults=[];this._todayMeta=null;this._todaySettings=null;
    this._ingredientCatalog=[];this._ingredientCatalogLanguage="";this._houseIngredients=[];this._houseEntryId="";this._houseFilter="";
    this._shoppingItems=[];this._shoppingEntityId="";this._shoppingAvailable=null;
    this._inventoryLoadedEntry="";this._pendingConsumption=null;this._nutritionSettings=null;
    this._weekState=null;this._weekStateEntry="";this._currencyState=null;this._currencyStateEntry="";
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
    const original=this.shadowRoot?.getElementById("entrySelect");if(!original)return;
    if(original.dataset.cook4meV55Authoritative==="1")return;

    // Remove every inherited entry-change listener. Several historical layers
    // independently react to this selector and can otherwise wipe a restored
    // cache or start duplicate loaders before v55 gets control.
    const select=original.cloneNode(true);
    select.dataset.cook4meV55Authoritative="1";
    original.replaceWith(select);
    select.addEventListener("change",()=>{
      const previous=String(this._entryId||"");
      this._captureEntrySnapshot(previous);
      const next=String(select.value||"");
      if(!next||next===previous)return;
      this._entryId=next;
      this._resetEntryScopedUiState();
      this._applyEntrySnapshot(next);
      this._v53FullOverviewDone=false;
      this._v54InitialVisibleRequested=true;
      this._renderTabs();this._renderTab();this._updateHeader();
      this._scheduleSnapshotPersist();
      queueMicrotask(()=>void this._requestSection(String(this._tab||"official"),{missingOnly:true,force:false}));
    });
  }
}

customElements.define("cook4me-recipe-hub-panel-v55",Cook4MeRecipeHubPanelV55);
