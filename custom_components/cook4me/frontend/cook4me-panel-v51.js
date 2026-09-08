import "./cook4me-panel-v50.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v50");

const TEXT={
  en:{
    dashboardLoading:"Loading Cook4Me status…",deferredTitle:"Dashboard ready",deferredHelp:"This section is intentionally not loaded during dashboard startup. Open it when you need it so Cook4Me does not start many requests at once.",loadSection:"Load section",preparingSection:"Loading section…",loadingPrefix:"Loading",queuedLoads:"queued",currencyDeferred:"Currency data loads only when you use the currency control or open Week.",
    loadOverview:"Cook4Me status",loadOptions:"dashboard options",loadBook:"recipe book",loadToday:"Today choices",loadWeek:"weekly planner",loadCurrency:"currency and exchange rates",loadCatalog:"ingredient catalog",loadShopping:"Shopping List",loadRecipe:"recipe details",loadSearch:"recipes",loadNutrition:"nutrition data",loadBarcode:"product information",loadPrice:"price information",
  },
  de:{
    dashboardLoading:"Cook4Me-Status wird geladen…",deferredTitle:"Dashboard bereit",deferredHelp:"Dieser Bereich wird beim Start des Dashboards absichtlich nicht geladen. Öffne ihn erst bei Bedarf, damit Cook4Me nicht viele Anfragen gleichzeitig startet.",loadSection:"Bereich laden",preparingSection:"Bereich wird geladen…",loadingPrefix:"Lädt",queuedLoads:"in Warteschlange",currencyDeferred:"Währungsdaten werden erst geladen, wenn die Währung benutzt oder Woche geöffnet wird.",
    loadOverview:"Cook4Me-Status",loadOptions:"Dashboard-Optionen",loadBook:"Rezeptbuch",loadToday:"Heute-Auswahl",loadWeek:"Wochenplaner",loadCurrency:"Währung und Wechselkurse",loadCatalog:"Zutatenkatalog",loadShopping:"Einkaufsliste",loadRecipe:"Rezeptdetails",loadSearch:"Rezepte",loadNutrition:"Nährwertdaten",loadBarcode:"Produktinformationen",loadPrice:"Preisinformationen",
  },
  el:{
    dashboardLoading:"Φόρτωση κατάστασης Cook4Me…",deferredTitle:"Το dashboard είναι έτοιμο",deferredHelp:"Αυτή η ενότητα δεν φορτώνεται σκόπιμα κατά την εκκίνηση του dashboard. Άνοιξέ την όταν τη χρειάζεσαι ώστε το Cook4Me να μην ξεκινά πολλά αιτήματα μαζί.",loadSection:"Φόρτωση ενότητας",preparingSection:"Φόρτωση ενότητας…",loadingPrefix:"Φόρτωση",queuedLoads:"σε αναμονή",currencyDeferred:"Τα δεδομένα νομίσματος φορτώνονται μόνο όταν χρησιμοποιήσεις το νόμισμα ή ανοίξεις την Εβδομάδα.",
    loadOverview:"κατάστασης Cook4Me",loadOptions:"επιλογών dashboard",loadBook:"βιβλίου συνταγών",loadToday:"επιλογών Σήμερα",loadWeek:"εβδομαδιαίου πλάνου",loadCurrency:"νομίσματος και ισοτιμιών",loadCatalog:"καταλόγου υλικών",loadShopping:"λίστας αγορών",loadRecipe:"λεπτομερειών συνταγής",loadSearch:"συνταγών",loadNutrition:"διατροφικών δεδομένων",loadBarcode:"πληροφοριών προϊόντος",loadPrice:"πληροφοριών τιμής",
  },
};

class Cook4MeRecipeHubPanelV51 extends BasePanel{
  constructor(){
    super();
    this._v51OverviewStarted=false;
    this._v51OverviewDone=false;
    this._v51ActivatedSections=new Set();
    this._v51PreparedSections=new Set();
    this._v51PreparingSections=new Map();
    this._v51AllowedResources=new Set(["overview"]);
    this._v51LoadSequence=0;
    this._v51LoadTokens=new Map();
    this._v51Connected=false;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  get hass(){return this._hass;}
  set hass(value){
    const user=String(value?.user?.id||"anonymous");
    if(user!==this._restoredSectionUser){
      this._restoredSectionUser=user;
      const saved=this._loadLastSection?.(user);
      if(saved)this._tab=saved;
    }
    this._hass=value;
    if(!this.shadowRoot.innerHTML)this._renderShell();else this._updateHeader();
    // Contract: HA state propagation must never become a polling trigger. The
    // only automatic request permitted by panel mount is the first overview.
    if(this.isConnected&&!this._v51OverviewStarted)queueMicrotask(()=>void this._loadOverview(false,true));
  }

  connectedCallback(){
    if(this._v51Connected)return;
    this._v51Connected=true;
    if(this._hass){
      if(!this.shadowRoot.innerHTML)this._renderShell();
      this._installModernObserver?.();
      this._modernizeSoon?.();
      if(this._outsidePointerHandler)document.addEventListener("pointerdown",this._outsidePointerHandler,true);
      if(!this._v51OverviewStarted)void this._loadOverview(false,true);
    }
  }

  disconnectedCallback(){
    this._v51Connected=false;
    if(this._outsidePointerHandler)document.removeEventListener("pointerdown",this._outsidePointerHandler,true);
    if(super.disconnectedCallback)super.disconnectedCallback();
  }

  _ensureV51Styles(){
    if(this.shadowRoot?.getElementById("cook4meV51Styles"))return;
    const style=document.createElement("style");style.id="cook4meV51Styles";style.textContent=`
      #cook4meLoadStatus{min-height:0;margin:0 0 10px}
      #cook4meLoadStatus:empty{display:none}
      .rx-v51-loading{display:flex;align-items:center;gap:9px;padding:10px 13px;border:1px solid color-mix(in srgb,var(--primary-color) 25%,var(--divider-color));border-radius:12px;background:color-mix(in srgb,var(--primary-color) 7%,var(--card-background-color));font-weight:600}
      .rx-v51-loading ha-icon{--mdc-icon-size:19px;color:var(--primary-color);animation:rxV51Spin 1s linear infinite}
      @keyframes rxV51Spin{to{transform:rotate(360deg)}}
      .rx-v51-deferred{max-width:760px;margin:10px auto;text-align:center;padding:28px!important}
      .rx-v51-deferred ha-icon{--mdc-icon-size:36px;color:var(--primary-color);margin-bottom:8px}
      .rx-v51-deferred h2{margin:4px 0 8px}.rx-v51-deferred .muted{max-width:620px;margin:0 auto 16px;line-height:1.5}
    `;this.shadowRoot.appendChild(style);
  }

  _ensureLoadStatus(){
    const root=this.shadowRoot;if(!root)return null;
    let status=root.getElementById("cook4meLoadStatus");
    if(status)return status;
    status=document.createElement("div");status.id="cook4meLoadStatus";status.setAttribute("role","status");status.setAttribute("aria-live","polite");
    const message=root.getElementById("message");
    if(message)message.after(status);else root.querySelector("main")?.before(status);
    return status;
  }

  _renderShell(){
    super._renderShell();
    this._ensureV51Styles();
    this._ensureLoadStatus();
    this._bindV51TabIntent();
    this._ensureCurrencyControl();
  }

  _loadLabel(type){
    const value=String(type||"");
    if(value==="cook4me/overview")return this._t("loadOverview");
    if(value.includes("capabilities"))return this._t("loadOptions");
    if(value.includes("book_state"))return this._t("loadBook");
    if(value.includes("today_options"))return this._t("loadToday");
    if(value.includes("week_state"))return this._t("loadWeek");
    if(value.includes("currency_state"))return this._t("loadCurrency");
    if(value.includes("ingredient_catalog"))return this._t("loadCatalog");
    if(value.includes("shopping_list")||value.includes("shopping_reconcile"))return this._t("loadShopping");
    if(value.includes("recipe_detail")||value.includes("ingredient_info"))return this._t("loadRecipe");
    if(value.includes("nutrition"))return this._t("loadNutrition");
    if(value.includes("barcode_scan"))return this._t("loadBarcode");
    if(value.includes("global_price_lookup")||value.includes("recipe_cost"))return this._t("loadPrice");
    if(value.includes("search")||value.includes("recommend")||value.includes("today_suggest"))return this._t("loadSearch");
    return "";
  }

  _beginLoad(label){
    if(!label)return null;
    const token=++this._v51LoadSequence;
    this._v51LoadTokens.set(token,String(label));
    this._refreshLoadStatus();
    return token;
  }

  _endLoad(token){
    if(token===null||token===undefined)return;
    this._v51LoadTokens.delete(token);
    this._refreshLoadStatus();
  }

  _refreshLoadStatus(){
    const target=this._ensureLoadStatus();if(!target)return;
    const labels=[...this._v51LoadTokens.values()];
    if(!labels.length){target.textContent="";return;}
    const extra=labels.length>1?` · ${labels.length-1} ${this._t("queuedLoads")}`:"";
    target.innerHTML=`<div class="rx-v51-loading"><ha-icon icon="mdi:loading"></ha-icon><span>${this._escape(this._t("loadingPrefix"))}: ${this._escape(labels[0])}…${this._escape(extra)}</span></div>`;
  }

  async _api(type,data={}){
    const token=this._beginLoad(this._loadLabel(type));
    try{return await super._api(type,data);}finally{this._endLoad(token);}
  }

  async _loadOverview(silent=false,rerender=true){
    if(this._overviewLoading)return;
    this._v51OverviewStarted=true;
    this._overviewLoading=true;
    try{
      const res=await this._api("cook4me/overview");
      this._entries=Array.isArray(res?.entries)?res.entries:[];
      if(!this._entryId||!this._entries.some(entry=>entry.entry_id===this._entryId))this._entryId=this._entries[0]?.entry_id||null;
      this._lastOverviewRefresh=Date.now();
      this._v51OverviewDone=true;
      this._renderEntrySelect();
      this._updateHeader();
      if(rerender)this._renderTab();
      if(!silent)this._message("");
    }catch(e){
      this._v51OverviewDone=true;
      if(!silent)this._message(`${this._t("error")}: ${e.message||e}`,true);
      if(rerender)this._renderTab();
    }finally{this._overviewLoading=false;}
  }

  _allowResource(name){this._v51AllowedResources.add(String(name));}
  _resourceAllowed(name){return this._v51AllowedResources.has(String(name));}

  _grantSectionResources(tab){
    const value=String(tab||"");
    const map={
      today:["capabilities","today","catalog","book"],
      official:["capabilities","book"],
      recommend:["capabilities","book"],
      book:["book"],
      mine:["capabilities","catalog","book"],
      profile:["capabilities","catalog"],
      shopping:["shopping"],
      ai:["capabilities","today","catalog","book"],
      week:["week","currency"],
    };
    for(const resource of map[value]||[])this._allowResource(resource);
  }

  _activateSection(tab){
    const value=String(tab||this._tab||"official");
    this._v51ActivatedSections.add(value);
    this._grantSectionResources(value);
  }

  _bindV51TabIntent(){
    const tabs=this.shadowRoot?.getElementById("tabs");
    if(!tabs||tabs.dataset.cook4meV51Intent==="1")return;
    tabs.dataset.cook4meV51Intent="1";
    tabs.addEventListener("click",event=>{
      const target=event.target instanceof Element?event.target.closest("[data-tab]"):null;
      if(target&&tabs.contains(target))this._activateSection(target.dataset.tab);
    },true);
  }

  _renderTabs(){
    super._renderTabs();
    this._bindV51TabIntent();
  }

  _renderEntrySelect(){
    super._renderEntrySelect();
    const select=this.shadowRoot?.getElementById("entrySelect");
    if(!select||select.dataset.cook4meV51Intent==="1")return;
    select.dataset.cook4meV51Intent="1";
    select.addEventListener("change",()=>{
      this._v51PreparedSections.clear();
      this._activateSection(this._tab);
    },true);
  }

  _sectionTitle(tab){
    const value=String(tab||"");
    return this._t(value)||value||"Cook4Me";
  }

  _renderDeferredSection(preparing=false){
    const c=this.shadowRoot?.getElementById("content");if(!c)return;
    const tab=String(this._tab||"official");
    if(!this._v51OverviewDone){
      c.innerHTML=`<section class="card rx-v51-deferred"><ha-icon icon="mdi:pot-steam-outline"></ha-icon><h2>${this._escape(this._t("dashboardLoading"))}</h2></section>`;
      return;
    }
    c.innerHTML=`<section class="card rx-v51-deferred"><ha-icon icon="mdi:${preparing?"loading":"power-sleep"}"></ha-icon><h2>${this._escape(preparing?this._t("preparingSection"):this._t("deferredTitle"))}</h2><div class="muted">${this._escape(preparing?`${this._t("loadingPrefix")}: ${this._sectionTitle(tab)}…`:this._t("deferredHelp"))}</div>${preparing?"":`<button id="cook4meLoadSection" class="btn"><ha-icon icon="mdi:download-outline"></ha-icon><span>${this._escape(this._t("loadSection"))}: ${this._escape(this._sectionTitle(tab))}</span></button>`}</section>`;
    c.querySelector("#cook4meLoadSection")?.addEventListener("click",()=>{this._activateSection(tab);this._renderTab();});
  }

  async _prepareSection(tab){
    const value=String(tab||"");
    this._grantSectionResources(value);
    if(["today","official","recommend","mine","profile","ai"].includes(value))await this._loadCapabilities();
    if(["today","official","recommend","book","mine","ai"].includes(value))await this._loadBookState(true);
    if(["today","ai"].includes(value))await this._loadTodayOptions();
    if(["today","mine","profile","ai"].includes(value)){
      const language=this._ingredientCatalogLanguage||this._capabilities?.ingredientCatalogLanguage||this._capabilities?.deviceCatalogLanguage||this._selectedLanguage?.()||"de";
      await this._loadIngredientCatalog(language,false);
    }
    if(value==="week"){
      await this._loadWeekState();
      await this._loadCurrencyState(false);
    }
  }

  _renderTab(){
    const tab=String(this._tab||"official");
    if(!this._v51OverviewDone){this._renderDeferredSection(false);return;}
    if(!this._v51ActivatedSections.has(tab)){this._renderDeferredSection(false);return;}
    if(!this._v51PreparedSections.has(tab)){
      this._renderDeferredSection(true);
      if(!this._v51PreparingSections.has(tab)){
        const task=this._prepareSection(tab)
          .then(()=>this._v51PreparedSections.add(tab))
          .catch(error=>this._message(`${this._t("error")}: ${error?.message||error}`,true))
          .finally(()=>{
            this._v51PreparingSections.delete(tab);
            if(String(this._tab||"")===tab)this._renderTab();
          });
        this._v51PreparingSections.set(tab,task);
      }
      return;
    }
    return super._renderTab();
  }

  async _loadCapabilities(){
    if(!this._resourceAllowed("capabilities"))return;
    return super._loadCapabilities();
  }

  async _loadBookState(silent=false){
    if(!this._resourceAllowed("book"))return;
    return super._loadBookState(silent);
  }

  async _loadTodayOptions(){
    if(!this._resourceAllowed("today"))return;
    return super._loadTodayOptions();
  }

  async _loadIngredientCatalog(language=null,refresh=false){
    if(!this._resourceAllowed("catalog"))return;
    return super._loadIngredientCatalog(language,refresh);
  }

  async _loadWeekState(){
    if(!this._resourceAllowed("week"))return;
    return super._loadWeekState();
  }

  async _loadCurrencyState(force=false){
    if(!this._resourceAllowed("currency")){
      this._ensureCurrencyControl();
      return;
    }
    return super._loadCurrencyState(force);
  }

  async _setCurrency(value){
    this._allowResource("currency");
    return super._setCurrency(value);
  }

  _ensureCurrencyControl(){
    super._ensureCurrencyControl();
    const select=this.shadowRoot?.getElementById("cook4meCurrency");if(!select)return;
    if(!this._currencyState&&!this._resourceAllowed("currency")){
      select.innerHTML=`<option value="">…</option>`;
      select.title=this._t("currencyDeferred");
      if(select.dataset.cook4meV51Lazy!=="1"){
        select.dataset.cook4meV51Lazy="1";
        const activate=()=>{
          if(this._resourceAllowed("currency"))return;
          this._allowResource("currency");
          void this._loadCurrencyState(false);
        };
        select.addEventListener("pointerdown",activate,{once:true});
        select.addEventListener("focus",activate,{once:true});
      }
    }
  }
}

customElements.define("cook4me-recipe-hub-panel-v51",Cook4MeRecipeHubPanelV51);
