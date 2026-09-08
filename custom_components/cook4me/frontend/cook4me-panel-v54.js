import "./cook4me-panel-v53.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v53");
const SNAPSHOT_VERSION=1;
const ALL_SECTIONS=["today","week","book","official","recommend","mine","profile","ai","shopping"];
const SECTION_RESOURCES={
  today:["fullOverview","capabilities","book","today","catalog"],
  week:["fullOverview","week","currency"],
  book:["book"],
  official:["capabilities","book"],
  recommend:["fullOverview","capabilities","book","catalog"],
  mine:["fullOverview","capabilities","book","catalog"],
  profile:["fullOverview","capabilities","catalog","inventory","nutrition"],
  ai:["fullOverview","capabilities","book","today","catalog"],
  shopping:["fullOverview","shopping"],
};
const V51_RESOURCES=new Set(["capabilities","book","today","catalog","week","currency"]);

const TEXT={
  en:{
    cacheUpdating:"Updating in the background",cacheFirst:"Cached content stays available while fresh data loads.",
    cacheSeeding:"Loading saved Cook4Me data",loadingInventory:"Loading house stock…",loadingShopping:"Loading Shopping List…",loadingNutritionSettings:"Loading nutrition settings…",
  },
  de:{
    cacheUpdating:"Aktualisierung im Hintergrund",cacheFirst:"Zwischengespeicherte Inhalte bleiben sichtbar, während aktuelle Daten geladen werden.",
    cacheSeeding:"Gespeicherte Cook4Me-Daten werden geladen",loadingInventory:"Vorrat wird geladen…",loadingShopping:"Einkaufsliste wird geladen…",loadingNutritionSettings:"Nährwert-Einstellungen werden geladen…",
  },
  el:{
    cacheUpdating:"Ενημέρωση στο παρασκήνιο",cacheFirst:"Το αποθηκευμένο περιεχόμενο παραμένει διαθέσιμο όσο φορτώνονται τα νεότερα δεδομένα.",
    cacheSeeding:"Φόρτωση αποθηκευμένων δεδομένων Cook4Me",loadingInventory:"Φόρτωση αποθέματος…",loadingShopping:"Φόρτωση λίστας αγορών…",loadingNutritionSettings:"Φόρτωση ρυθμίσεων διατροφής…",
  },
};

function cloneValue(value){
  if(value===undefined)return undefined;
  try{return typeof structuredClone==="function"?structuredClone(value):JSON.parse(JSON.stringify(value));}
  catch(_e){try{return JSON.parse(JSON.stringify(value));}catch(_ignored){return value;}}
}

class Cook4MeRecipeHubPanelV54 extends BasePanel{
  constructor(){
    super();
    this._v54CacheUser="";
    this._v54Cache={version:SNAPSHOT_VERSION,savedAt:0,selectedEntryId:"",entries:[],perEntry:{}};
    this._v54CacheHydrated=false;
    this._v54HadUiCache=false;
    this._v54HasCachedFullOverview=false;
    this._v54RequestedSections=new Set();
    this._v54RefreshingSections=new Set();
    this._v54RefreshTasks=new Map();
    this._v54PersistTimer=null;
    this._v54SeedStarted=false;
    this._v54InitialVisibleRequested=false;
    // v51 used this flag to decide whether to replace the entire tab with a
    // deferred gate. v54 never gates rendering: the UI exists even before data.
    this._v51OverviewDone=true;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  get hass(){return this._hass;}
  set hass(value){
    const user=String(value?.user?.id||value?.user?.name||"anonymous");
    if(!this._v54CacheHydrated||user!==this._v54CacheUser)this._hydrateUiSnapshot(user);
    // Rendering must see cached data before the inherited setter builds the shell.
    this._v51OverviewDone=true;
    super.hass=value;
  }

  _snapshotKey(user=this._v54CacheUser||String(this._hass?.user?.id||"anonymous")){
    return `cook4me.ui.snapshot.v54.${user}`;
  }

  _hydrateUiSnapshot(user){
    this._v54CacheUser=String(user||"anonymous");
    this._v54CacheHydrated=true;
    let cached=null;
    try{cached=JSON.parse(globalThis.localStorage?.getItem(this._snapshotKey(this._v54CacheUser))||"null");}catch(_e){}
    if(!cached||cached.version!==SNAPSHOT_VERSION||typeof cached!=="object"){
      this._v54Cache={version:SNAPSHOT_VERSION,savedAt:0,selectedEntryId:"",entries:[],perEntry:{}};
      this._v54HadUiCache=false;
      this._v54HasCachedFullOverview=false;
      return;
    }
    this._v54Cache=cached;
    const entries=Array.isArray(cached.entries)?cloneValue(cached.entries):[];
    if(entries.length){
      this._entries=entries;
      const wanted=String(cached.selectedEntryId||"");
      this._entryId=entries.some(row=>String(row?.entry_id||"")===wanted)?wanted:String(entries[0]?.entry_id||"")||null;
    }
    this._v54HadUiCache=entries.length>0;
    this._v54HasCachedFullOverview=Boolean(cached.fullOverviewCached);
    if(this._entryId)this._applyEntrySnapshot(this._entryId);
  }

  _entrySnapshot(entryId=this._entryId){
    return this._v54Cache?.perEntry?.[String(entryId||"")]||null;
  }

  _applyEntrySnapshot(entryId){
    const row=this._entrySnapshot(entryId);
    if(!row)return;
    if(row.capabilities&&typeof row.capabilities==="object")this._capabilities=cloneValue(row.capabilities);
    if(row.uiPreferences&&typeof row.uiPreferences==="object"){
      this._uiPreferences={...(this._uiPreferences||{}),...cloneValue(row.uiPreferences)};
      this._catalogLanguage=String(this._uiPreferences.catalogLanguage||this._catalogLanguage||"auto");
      this._translateEnabled=Boolean(this._uiPreferences.translateResults);
      this._preferencesLoaded=true;
      this._translationPreferenceInitialized=true;
    }
    this._bookState=row.bookState===undefined?this._bookState:cloneValue(row.bookState);
    this._todayOptions=row.todayOptions===undefined?this._todayOptions:cloneValue(row.todayOptions);
    if(Array.isArray(row.ingredientCatalog))this._ingredientCatalog=cloneValue(row.ingredientCatalog);
    if(row.ingredientCatalogLanguage!==undefined)this._ingredientCatalogLanguage=String(row.ingredientCatalogLanguage||"");
    if(Array.isArray(row.shoppingItems))this._shoppingItems=cloneValue(row.shoppingItems);
    if(row.shoppingEntityId!==undefined)this._shoppingEntityId=String(row.shoppingEntityId||"");
    if(row.shoppingAvailable!==undefined)this._shoppingAvailable=row.shoppingAvailable;
    if(Array.isArray(row.houseIngredients))this._houseIngredients=cloneValue(row.houseIngredients);
    if(row.houseStateLoaded){this._houseEntryId=String(entryId||"");this._inventoryLoadedEntry=String(entryId||"");}
    if(row.pendingConsumption!==undefined)this._pendingConsumption=cloneValue(row.pendingConsumption);
    if(row.nutritionSettings!==undefined)this._nutritionSettings=cloneValue(row.nutritionSettings);
    if(row.weekState!==undefined){this._weekState=cloneValue(row.weekState);this._weekStateEntry=row.weekState?String(entryId||""):"";}
    if(row.currencyState!==undefined){this._currencyState=cloneValue(row.currencyState);this._currencyStateEntry=row.currencyState?String(entryId||""):"";}
    if(Array.isArray(row.results))this._results=cloneValue(row.results);
    if(Array.isArray(row.recommendations))this._recommendations=cloneValue(row.recommendations);
    if(Array.isArray(row.todayResults))this._todayResults=cloneValue(row.todayResults);
    if(row.todayMeta!==undefined)this._todayMeta=cloneValue(row.todayMeta);
    if(row.searchQuery!==undefined)this._searchQuery=String(row.searchQuery||"");
  }

  _captureEntrySnapshot(entryId=this._entryId){
    const id=String(entryId||"");if(!id)return;
    const previous=this._v54Cache.perEntry?.[id]||{};
    this._v54Cache.perEntry={...(this._v54Cache.perEntry||{}),[id]:{
      ...previous,
      capabilities:cloneValue(this._capabilities),
      uiPreferences:cloneValue(this._uiPreferences),
      bookState:cloneValue(this._bookState),
      todayOptions:cloneValue(this._todayOptions),
      ingredientCatalog:cloneValue(this._ingredientCatalog||[]),
      ingredientCatalogLanguage:String(this._ingredientCatalogLanguage||""),
      shoppingItems:cloneValue(this._shoppingItems||[]),
      shoppingEntityId:String(this._shoppingEntityId||""),
      shoppingAvailable:this._shoppingAvailable,
      houseIngredients:cloneValue(this._houseIngredients||[]),
      houseStateLoaded:Boolean(this._houseEntryId===id||this._inventoryLoadedEntry===id),
      pendingConsumption:cloneValue(this._pendingConsumption),
      nutritionSettings:cloneValue(this._nutritionSettings),
      weekState:this._weekStateEntry===id?cloneValue(this._weekState):null,
      currencyState:this._currencyStateEntry===id?cloneValue(this._currencyState):null,
      results:cloneValue((this._results||[]).slice(0,30)),
      recommendations:cloneValue((this._recommendations||[]).slice(0,30)),
      todayResults:cloneValue((this._todayResults||[]).slice(0,16)),
      todayMeta:cloneValue(this._todayMeta),
      searchQuery:String(this._searchQuery||""),
      savedAt:Date.now(),
    }};
  }

  _scheduleSnapshotPersist(){
    if(this._v54PersistTimer)clearTimeout(this._v54PersistTimer);
    this._v54PersistTimer=setTimeout(()=>{this._v54PersistTimer=null;this._persistUiSnapshot();},120);
  }

  _persistUiSnapshot(){
    if(!this._v54CacheUser)return;
    this._captureEntrySnapshot();
    this._v54Cache.version=SNAPSHOT_VERSION;
    this._v54Cache.savedAt=Date.now();
    this._v54Cache.selectedEntryId=String(this._entryId||"");
    this._v54Cache.entries=cloneValue(this._entries||[]);
    this._v54Cache.fullOverviewCached=Boolean(this._v54HasCachedFullOverview||this._v53FullOverviewDone);
    try{
      let text=JSON.stringify(this._v54Cache);
      // localStorage is intentionally only a fast UI cache. If a very large
      // ingredient catalog would exceed a normal browser quota, keep the core
      // dashboard state and drop only that regenerable catalog from the cache.
      if(text.length>3800000){
        const reduced=cloneValue(this._v54Cache);
        for(const row of Object.values(reduced.perEntry||{}))if(row)row.ingredientCatalog=[];
        text=JSON.stringify(reduced);
      }
      globalThis.localStorage?.setItem(this._snapshotKey(),text);
    }catch(_e){
      // Cache failure must never affect the live UI.
    }
  }

  async _api(type,data={}){
    const result=await super._api(type,data);
    // Mutating actions usually update local state immediately after await. Use a
    // timer so the snapshot is taken after that caller has applied the result.
    setTimeout(()=>this._scheduleSnapshotPersist(),0);
    return result;
  }

  _ensureV54Styles(){
    if(this.shadowRoot?.getElementById("cook4meV54Styles"))return;
    const style=document.createElement("style");style.id="cook4meV54Styles";style.textContent=`
      .rx-v54-background{display:flex;align-items:center;gap:9px;margin:0 0 10px;padding:8px 11px;border:1px solid color-mix(in srgb,var(--primary-color) 20%,var(--divider-color));border-radius:11px;background:color-mix(in srgb,var(--primary-color) 5%,var(--card-background-color));font-size:13px;color:var(--secondary-text-color)}
      .rx-v54-background ha-icon{--mdc-icon-size:18px;color:var(--primary-color);animation:rxV51Spin 1s linear infinite}.rx-v54-background strong{color:var(--primary-text-color)}
      .rx-v54-inline-loading{display:flex;align-items:center;gap:7px;padding:7px 0;color:var(--secondary-text-color);font-size:13px}.rx-v54-inline-loading ha-icon{--mdc-icon-size:17px;animation:rxV51Spin 1s linear infinite}
    `;this.shadowRoot.appendChild(style);
  }

  _renderShell(){
    super._renderShell();
    this._ensureV54Styles();
    const refresh=this.shadowRoot?.getElementById("refresh");
    if(refresh&&!refresh.dataset.cook4meV54Refresh){
      refresh.dataset.cook4meV54Refresh="1";
      refresh.addEventListener("click",event=>{
        event.preventDefault();event.stopImmediatePropagation();
        void this._explicitRefresh();
      },true);
    }
  }

  _renderTab(){
    const tab=String(this._tab||"official");
    // Bypass only the v51/v52 whole-section gate. Do NOT grant network access:
    // inherited renderers may ask for data, but requests stay blocked until the
    // section is actually requested below.
    this._v51OverviewDone=true;
    this._v51ActivatedSections.add(tab);
    this._v51PreparedSections.add(tab);
    const result=super._renderTab();
    this._ensureV54Styles();
    this._updateBackgroundStatus();
    this._decorateElementLoadingStates();
    this._scheduleSnapshotPersist();
    return result;
  }

  _selectV52Tab(tab){
    const value=String(tab||"");if(!value)return;
    this._tab=value;this._opened=null;this._rememberSection?.(value);
    this._v51ActivatedSections.add(value);this._v51PreparedSections.add(value);
    this._renderTabs();
    // Paint cached/known content BEFORE any refresh request is started.
    this._renderTab();
    void this._requestSection(value,{missingOnly:false});
  }

  _grantNetworkForSection(tab){
    const resources=SECTION_RESOURCES[String(tab||"")]||[];
    for(const resource of resources){
      if(V51_RESOURCES.has(resource))this._allowResource(resource);
      if(resource==="fullOverview")this._allowResource("fullOverview");
    }
  }

  _resourceHasData(resource){
    const id=String(this._entryId||"");
    if(resource==="fullOverview")return Boolean(this._v54HasCachedFullOverview||this._v53FullOverviewDone||this._entries.some(row=>row&&("profile" in row||"recipes" in row||"history" in row||"habitTerms" in row)));
    if(resource==="capabilities")return Boolean((this._capabilities?.languages||[]).length||this._preferencesLoaded);
    if(resource==="book")return this._bookState!==null&&this._bookState!==undefined;
    if(resource==="today")return this._todayOptions!==null&&this._todayOptions!==undefined;
    if(resource==="catalog")return Boolean(this._ingredientCatalogLanguage||this._ingredientCatalog?.length);
    if(resource==="week")return Boolean(this._weekState&&this._weekStateEntry===id);
    if(resource==="currency")return Boolean(this._currencyState&&this._currencyStateEntry===id);
    if(resource==="shopping")return this._shoppingAvailable!==null&&this._shoppingAvailable!==undefined;
    if(resource==="inventory")return Boolean(this._inventoryLoadedEntry===id||this._houseEntryId===id);
    if(resource==="nutrition")return this._nutritionSettings!==null&&this._nutritionSettings!==undefined;
    return false;
  }

  async _requestSection(tab,{missingOnly=false,force=false}={}){
    const value=String(tab||"");if(!value||!this._entryId)return;
    this._v54RequestedSections.add(value);
    this._grantNetworkForSection(value);
    const key=`${value}:${missingOnly?"missing":"refresh"}:${force?"force":"normal"}`;
    if(this._v54RefreshTasks.has(key))return this._v54RefreshTasks.get(key);
    const task=this._refreshSection(value,{missingOnly,force}).finally(()=>this._v54RefreshTasks.delete(key));
    this._v54RefreshTasks.set(key,task);
    return task;
  }

  async _refreshSection(tab,{missingOnly=false,force=false}={}){
    const resources=SECTION_RESOURCES[tab]||[];
    const wanted=missingOnly?resources.filter(resource=>!this._resourceHasData(resource)):resources;
    if(!wanted.length)return;
    this._v54RefreshingSections.add(tab);this._updateBackgroundStatus();
    const preserveTab=()=>String(this._tab||"");
    try{
      for(const resource of wanted){
        if(resource==="fullOverview"){
          await this._loadFullOverview(true,false,force);
        }else if(resource==="capabilities"){
          const selected=preserveTab();await this._loadCapabilities();
          if(this._tab!==selected){this._tab=selected;this._renderTabs();}
        }else if(resource==="book"){
          await this._loadBookState(true);
        }else if(resource==="today"){
          await this._loadTodayOptions();
        }else if(resource==="catalog"){
          const language=this._ingredientCatalogLanguage||this._capabilities?.ingredientCatalogLanguage||this._capabilities?.deviceCatalogLanguage||this._selectedLanguage?.()||"de";
          await this._loadIngredientCatalog(language,force);
        }else if(resource==="week"){
          await this._loadWeekState();
        }else if(resource==="currency"){
          await this._loadCurrencyState(Boolean(force||this._currencyState));
        }else if(resource==="shopping"){
          await this._loadShoppingList(true);
        }else if(resource==="inventory"){
          await this._loadInventoryState();
        }else if(resource==="nutrition"){
          await this._loadNutritionSettings();
        }
      }
    }finally{
      this._v54RefreshingSections.delete(tab);
      if(String(this._tab||"")===tab)this._renderTab();else this._updateBackgroundStatus();
      this._scheduleSnapshotPersist();
    }
  }

  _updateBackgroundStatus(){
    const c=this.shadowRoot?.getElementById("content");if(!c)return;
    c.querySelector("[data-v54-background]")?.remove();
    const tab=String(this._tab||"");if(!this._v54RefreshingSections.has(tab))return;
    const node=document.createElement("div");node.dataset.v54Background="1";node.className="rx-v54-background";node.setAttribute("role","status");node.setAttribute("aria-live","polite");
    node.innerHTML=`<ha-icon icon="mdi:loading"></ha-icon><span><strong>${this._escape(this._t("cacheUpdating"))}</strong> · ${this._escape(this._t("cacheFirst"))}</span>`;
    c.prepend(node);
  }

  _decorateElementLoadingStates(){
    const c=this.shadowRoot?.getElementById("content");if(!c)return;
    c.querySelectorAll("[data-v54-element-loading]").forEach(node=>node.remove());
    if(this._tab==="profile"){
      if(this._inventoryLoading&&this._inventoryLoadedEntry!==this._entryId){
        const target=c.querySelector("#houseInventoryRows");if(target){const n=document.createElement("div");n.dataset.v54ElementLoading="inventory";n.className="rx-v54-inline-loading";n.innerHTML=`<ha-icon icon="mdi:loading"></ha-icon><span>${this._escape(this._t("loadingInventory"))}</span>`;target.prepend(n);}
      }
      if(this._nutritionSettingsLoading&&!this._nutritionSettings){
        const n=document.createElement("div");n.dataset.v54ElementLoading="nutrition";n.className="rx-v54-inline-loading";n.innerHTML=`<ha-icon icon="mdi:loading"></ha-icon><span>${this._escape(this._t("loadingNutritionSettings"))}</span>`;c.append(n);
      }
    }
  }

  async _explicitRefresh(){
    await this._loadBootstrap(true,false,true);
    await this._requestSection(String(this._tab||"official"),{missingOnly:false,force:true});
  }

  async _loadBootstrap(silent=false,rerender=true,force=false){
    if(this._overviewLoading||(!force&&this._v53BootstrapDone))return;
    this._v51OverviewStarted=true;this._overviewLoading=true;
    try{
      const res=await this._api("cook4me/v27/bootstrap");
      const live=Array.isArray(res?.entries)?res.entries:[];
      const cachedById=new Map((this._entries||[]).map(row=>[String(row?.entry_id||""),row]));
      this._entries=live.map(row=>{
        const previous=cachedById.get(String(row?.entry_id||""));
        return previous?{...previous,...row,state:{...(previous.state||{}),...(row.state||{})}}:{...row};
      });
      if(!this._entryId||!this._entries.some(row=>row.entry_id===this._entryId))this._entryId=this._entries[0]?.entry_id||null;
      this._lastOverviewRefresh=Date.now();this._v53BootstrapDone=true;this._v51OverviewDone=true;
      if(this._entryId&&!this._entrySnapshot(this._entryId))this._applyEntrySnapshot(this._entryId);
      this._renderEntrySelect();this._updateHeader();if(rerender)this._renderTab();if(!silent)this._message("");
    }catch(e){
      this._v53BootstrapDone=true;this._v51OverviewDone=true;
      if(!silent)this._message(`${this._t("error")}: ${e.message||e}`,true);
      if(rerender)this._renderTab();
    }finally{
      this._overviewLoading=false;
      this._scheduleSnapshotPersist();
      // The visible tab counts as user-requested content. Load ONLY resources
      // that are absent from the UI cache; cached resources are not refreshed.
      if(!this._v54InitialVisibleRequested&&this._entryId){
        this._v54InitialVisibleRequested=true;
        queueMicrotask(()=>void this._requestSection(String(this._tab||"official"),{missingOnly:true}));
      }
    }
  }

  async _loadFullOverview(silent=true,rerender=false,force=false){
    const result=await super._loadFullOverview(silent,rerender,force);
    if(this._v53FullOverviewDone){this._v54HasCachedFullOverview=true;this._scheduleSnapshotPersist();}
    return result;
  }

  _renderEntrySelect(){
    super._renderEntrySelect();
    const select=this.shadowRoot?.getElementById("entrySelect");if(!select||select.dataset.cook4meV54Entry)return;
    select.dataset.cook4meV54Entry="1";
    select.addEventListener("change",event=>{
      const previous=String(this._entryId||"");this._captureEntrySnapshot(previous);
      const next=String(event.target.value||"");
      this._entryId=next;this._applyEntrySnapshot(next);
      this._v53FullOverviewDone=false;
      this._v54HasCachedFullOverview=Boolean(this._v54Cache.fullOverviewCached);
      this._scheduleSnapshotPersist();
    },true);
  }

  // Additional auto-loaders that predate v51 must obey the same request rule.
  async _loadShoppingList(silent=false){
    if(!this._v54RequestedSections.has("shopping"))return;
    return super._loadShoppingList(silent);
  }

  async _loadInventoryState(){
    if(!this._v54RequestedSections.has("profile"))return;
    return super._loadInventoryState();
  }

  async _loadNutritionSettings(){
    if(!this._v54RequestedSections.has("profile"))return;
    return super._loadNutritionSettings();
  }

  async _maybeAutoFillNutritionCatalog(){
    // v42/v43 used to start USDA enrichment merely because a tab rendered.
    // External enrichment is now explicit only; the existing Build button still
    // calls nutrition_catalog_fill directly when the user requests it.
    return;
  }

  _renderShopping(c){
    // Keep the Shopping UI available even while its list is being loaded. The
    // old renderer replaced the whole tab with one Loading card.
    if(this._shoppingLoading&&this._shoppingAvailable===null){
      c.innerHTML=`<section class="card"><div class="detail-head"><div><h2 style="margin:0">${this._escape(this._t("shopping"))}</h2><div class="rx-v54-inline-loading"><ha-icon icon="mdi:loading"></ha-icon><span>${this._escape(this._t("loadingShopping"))}</span></div></div><button id="shoppingRefresh" class="btn secondary">${this._escape(this._t("shoppingRefresh"))}</button></div><div class="toolbar" style="margin:14px 0"><input id="shoppingManual" class="grow" placeholder="${this._escape(this._t("shoppingInput"))}"><button id="shoppingAddManual" class="btn">${this._escape(this._t("shoppingAdd"))}</button></div><div class="muted">${this._escape(this._t("loadingShopping"))}</div></section>`;
      c.querySelector("#shoppingRefresh")?.addEventListener("click",()=>void super._loadShoppingList(false));
      const add=async()=>{const input=c.querySelector("#shoppingManual");const value=String(input?.value||"").trim();if(!value)return;await this._addShopping([value]);if(input)input.value="";};
      c.querySelector("#shoppingAddManual")?.addEventListener("click",()=>void add());
      c.querySelector("#shoppingManual")?.addEventListener("keydown",event=>{if(event.key==="Enter"){event.preventDefault();void add();}});
      return;
    }
    return super._renderShopping(c);
  }
}

customElements.define("cook4me-recipe-hub-panel-v54",Cook4MeRecipeHubPanelV54);
