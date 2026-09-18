import "./cook4me-panel-v62.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v62");
const BUILD="2026.9.15.5";
const SECTIONS=new Set(["today","week","official","book","mine","profile","shopping","ai"]);
const MEALS=["breakfast","starter","salad","soup","main","side","dessert","snack"];
const FILTERS=[["diet","leaf","diet"],["meals","silverware-fork-knife","mealTypes"],["languages","translate","officialCatalogs"],["ingredients","food-apple-outline","preferredIngredients"],["home","home-outline","onlyHome"],["nutrition","bullseye-arrow","servingTargets"],["cost","cash-multiple","costSettings"]];
const TEXT={
  en:{sharedFilters:"Recipe filters",servingTargets:"Nutrition targets per serving",targetHelp:"Recipes with known nutrients are ranked closer to these targets. Missing values stay unknown.",maxCost:"Maximum cost per serving",costFilterHelp:"A cost limit includes only recipes with complete price coverage in the selected currency.",preferencesPending:"Preferences saved on this device; Home Assistant sync will retry when connected.",apply:"Apply",recipeUnavailable:"The original recipe is unavailable for this leftover.",sourceText:"Recipe text follows the selected recipe language."},
  el:{sharedFilters:"Φίλτρα συνταγών",servingTargets:"Διατροφικοί στόχοι ανά μερίδα",targetHelp:"Οι συνταγές με γνωστά θρεπτικά στοιχεία κατατάσσονται με βάση την εγγύτητα στους στόχους. Οι ελλιπείς τιμές παραμένουν άγνωστες.",maxCost:"Μέγιστο κόστος ανά μερίδα",costFilterHelp:"Το όριο κόστους περιλαμβάνει μόνο συνταγές με πλήρη κάλυψη τιμών στο επιλεγμένο νόμισμα.",preferencesPending:"Οι προτιμήσεις αποθηκεύτηκαν στη συσκευή. Ο συγχρονισμός με το Home Assistant θα επαναληφθεί όταν συνδεθεί.",apply:"Εφαρμογή",recipeUnavailable:"Η αρχική συνταγή για αυτό το περίσσευμα δεν είναι διαθέσιμη.",sourceText:"Το κείμενο της συνταγής ακολουθεί την επιλεγμένη γλώσσα συνταγής."},
  de:{sharedFilters:"Rezeptfilter",servingTargets:"Nährwertziele pro Portion",targetHelp:"Rezepte mit bekannten Nährwerten werden nach Nähe zu diesen Zielen sortiert. Fehlende Werte bleiben unbekannt.",maxCost:"Maximale Kosten pro Portion",costFilterHelp:"Ein Kostenlimit berücksichtigt nur Rezepte mit vollständiger Preisabdeckung in der gewählten Währung.",preferencesPending:"Einstellungen auf diesem Gerät gespeichert; Home Assistant wird bei Verbindung erneut synchronisiert.",apply:"Anwenden",recipeUnavailable:"Das ursprüngliche Rezept für diese Reste ist nicht verfügbar.",sourceText:"Der Rezepttext folgt der gewählten Rezeptsprache."},
};

class Cook4MeRecipeHubPanelV63 extends BasePanel{
  _t(key){return TEXT[this._uiIngredientLanguage()]?.[key]||TEXT.en[key]||super._t(key);}
  _shouldTranslate(){return false;} // Offline labels are shipped; never start implicit AI translation.
  _discardOldCatalog(){
    const language=this._uiIngredientLanguage();
    if(this._ingredientCatalog?.some(row=>row.presentationVersion!==63||row.displayLanguage!==language))this._ingredientCatalog=[];
    this._ingredientCatalogLanguage=language;
  }
  _resourceHasData(resource){return resource==="catalog"?Boolean(this._ingredientCatalog?.length&&this._ingredientCatalog.every(row=>row.presentationVersion===63&&row.displayLanguage===this._uiIngredientLanguage())):super._resourceHasData(resource);}
  async _loadIngredientCatalog(_language=null,refresh=false){
    if(!this._entryId||this._ingredientCatalogLoading)return;
    const entry=this._entryId,language=this._uiIngredientLanguage(),key=`${entry}:${language}`;
    if(!refresh&&this._v63CatalogFailure===key)return;
    this._ingredientCatalogLoading=true;
    try{
      const result=await this._api("cook4me/v31/ingredient_catalog",{entry_id:entry,language,refresh:Boolean(refresh)});
      if(entry!==this._entryId||language!==this._uiIngredientLanguage())return;
      if(result.presentationVersion!==63)throw new Error("Cook4Me v63 is not active; restart Home Assistant and reload this page.");
      this._ingredientCatalog=(result.items||[]).sort((a,b)=>String(a.name).localeCompare(String(b.name),language));
      this._v63CatalogFailure=null;
    }catch(error){this._v63CatalogFailure=key;this._message(`${this._t("error")}: ${error.message||error}`,true);}
    finally{this._ingredientCatalogLoading=false;}
    if(entry===this._entryId)this._renderTab();
  }
  _todayIngredientIdentity(row){return row?.ingredientId&&!row.key&&!row.foodKey?`i:${row.ingredientId}`:super._todayIngredientIdentity(row);}
  _prefKey(){return `cook4me.ui.v63.${this._hass?.user?.id||"anonymous"}.${this._entryId||""}`;}
  _filters(){
    const key=this._prefKey();
    if(this._v63FilterKey!==key){
      this._v63FilterKey=key;this._v63PrefsLoaded="";
      let cached={};try{cached=JSON.parse(localStorage.getItem(key)||"{}");}catch(_e){}
      this._v63Filters={...this._loadTodaySettings(),proteinTarget:"",fiberTarget:"",maxCost:"",currency:this._currencyState?.currency||"EUR",...cached.filters};
      this._v63Dirty=cached.pending||null;
      if(SECTIONS.has(cached.lastTab))this._tab=cached.lastTab;
    }
    return this._v63Filters;
  }
  _cachePreferences(){
    try{localStorage.setItem(this._prefKey(),JSON.stringify({lastTab:this._tab,filters:this._filters(),pending:this._v63Dirty}));}catch(_e){}
  }
  get hass(){return super.hass;}
  set hass(value){
    const changed=this._hass?.user?.id!==value?.user?.id||this._hass?.connection!==value?.connection;
    if(changed){this._v63CloseRecipe?.();this._v63CloseFilter?.();this._v63RecipeRequest=null;this._v63PrefsLoaded="";}
    super.hass=value;
    if(this._entryId)void this._restorePreferences();
  }
  async _restorePreferences(){
    if(!this._entryId||!this._hass?.user?.id)return;
    this._filters();
    const key=this._prefKey(),connection=this._hass.connection;
    if(this._v63PrefsLoaded===key||this._v63PrefsLoading?.key===key)return;
    const request={key,connection};this._v63PrefsLoading=request;
    const revision=this._v63PrefRevision||0;
    try{
      const saved=await connection.sendMessagePromise({type:"cook4me/v31/ui_preferences",entry_id:this._entryId});
      if(key!==this._prefKey()||connection!==this._hass?.connection)return;
      this._v63PrefsLoaded=key;
      if(revision===(this._v63PrefRevision||0)){
        const prefs={...saved,...this._v63Dirty};
        if(prefs.filters)this._v63Filters={...this._v63Filters,...prefs.filters};
        if(SECTIONS.has(prefs.lastTab))this._tab=prefs.lastTab;
        this._cachePreferences();this._renderTabs();this._renderTab();
      }
      if(this._v63Dirty)void this._flushPreferences();
    }catch(_e){this._v63PrefsLoaded=key; /* reconnect/visibility explicitly retries */}
    finally{if(this._v63PrefsLoading===request)this._v63PrefsLoading=null;}
  }
  _persistPreferences(patch){
    this._v63PrefRevision=(this._v63PrefRevision||0)+1;
    this._v63Dirty={...this._v63Dirty,...patch};this._cachePreferences();
    void this._flushPreferences();
  }
  async _flushPreferences(){
    if(this._v63Saving||!this._v63Dirty||!this._hass?.connection)return;
    const key=this._prefKey(),entry=this._entryId,connection=this._hass.connection;
    const patch=this._v63Dirty;this._v63Dirty=null;this._v63Saving=true;
    try{await connection.sendMessagePromise({type:"cook4me/v31/ui_preferences",entry_id:entry,preferences:patch});}
    catch(_e){if(key===this._prefKey()){this._v63Dirty={...patch,...this._v63Dirty};this._message(this._t("preferencesPending"),true);return;}}
    finally{this._v63Saving=false;if(key===this._prefKey())this._cachePreferences();}
    if(this._v63Dirty)void this._flushPreferences();
  }
  connectedCallback(){
    super.connectedCallback();
    this._v63Resume=()=>{if(document.visibilityState!=="hidden"){this._v63PrefsLoaded="";void this._restorePreferences();}};
    document.addEventListener("visibilitychange",this._v63Resume);window.addEventListener("online",this._v63Resume);
  }
  _selectV52Tab(tab){
    const value=tab==="recommend"?"today":tab;
    this._v63CloseRecipe?.();this._v63CloseFilter?.();
    this._v63RecipeRequest=null;
    super._selectV52Tab(value);this._persistPreferences({lastTab:value});
  }
  _renderTabs(){
    if(this._tab==="recommend")this._tab="today";
    super._renderTabs();const tabs=this.shadowRoot?.getElementById("tabs");if(!tabs)return;
    tabs.querySelector('[data-tab="recommend"]')?.remove();
    const week=tabs.querySelector('[data-tab="week"]');
    if(week)week.innerHTML=`<ha-icon icon="mdi:calendar-week" aria-hidden="true"></ha-icon><span>${this._escape(this._t("week"))}</span>`;
    if(!tabs._v63Nav){tabs._v63Nav=true;tabs.addEventListener("click",event=>{
      const button=event.target.closest?.("[data-tab]");if(!button)return;
      event.preventDefault();event.stopImmediatePropagation();this._selectV52Tab(button.dataset.tab);
    },true);}
  }
  _ensureV63Styles(){
    if(this.shadowRoot?.getElementById("cook4meV63Styles"))return;
    const style=document.createElement("style");style.id="cook4meV63Styles";style.textContent=`
      .rx-shared-filters{display:grid!important;grid-template-columns:repeat(7,minmax(0,1fr));gap:4px;width:100%;max-width:460px;margin:0 0 14px;box-sizing:border-box}
      .rx-shared-filters button{display:flex!important;align-items:center;justify-content:center;width:100%;min-width:0!important;min-height:44px;padding:6px!important;border-radius:12px;overflow:visible}
      .rx-shared-filters ha-icon{display:block!important;--mdc-icon-size:22px;color:currentColor;opacity:1!important}
      .rx-shared-filters button[aria-pressed=true]{color:var(--primary-color);border-color:var(--primary-color);background:color-mix(in srgb,var(--primary-color) 12%,var(--card-background-color))}
      .tab[data-tab=week] ha-icon{display:inline-flex!important;opacity:1!important;color:currentColor;--mdc-icon-size:22px}
      [data-recipe-dialog] .rx-dialog{width:min(960px,calc(100vw - 24px));max-width:960px;max-height:90dvh;overflow:auto;padding:16px;box-sizing:border-box}
      [data-recipe-dialog] #recipeDetail{margin:0!important}
      [data-recipe-dialog] [data-modal-close]{position:sticky;top:0;float:right;z-index:2;min-height:44px}
      [data-filter-dialog] .rx-dialog{width:min(480px,calc(100vw - 24px));max-height:85dvh;overflow:auto;box-sizing:border-box}
      [data-filter-dialog] label{display:flex;align-items:center;gap:8px;margin:10px 0}
      [data-filter-dialog] .field{margin:12px 0}
      [data-filter-dialog] input:not([type=checkbox]),[data-filter-dialog] select{box-sizing:border-box;width:100%}
      [data-filter-dialog] footer{position:sticky;bottom:0;background:var(--card-background-color);padding:10px 0 0;display:flex;justify-content:flex-end}
      .rx-week-slot[role=button]{cursor:pointer}.rx-week-slot[role=button]:focus-visible{outline:2px solid var(--primary-color);outline-offset:3px}
      .rx-v63-progress{position:fixed;right:12px;bottom:12px;display:flex;flex-direction:column;gap:8px;z-index:10050;max-height:65dvh;overflow:auto;width:min(390px,calc(100vw - 24px));pointer-events:none}
      .rx-v63-progress .rx-v59-op{position:relative;right:auto;bottom:auto;width:100%;box-sizing:border-box;pointer-events:auto}
    `;this.shadowRoot?.appendChild(style);
  }
  _renderShell(){super._renderShell();this._ensureV63Styles();}
  _filterActive(key){const f=this._filters();return {diet:f.diet!=="profile",meals:f.mealTypes?.length!==MEALS.length,languages:f.languages?.length!==this._languageRows().length,ingredients:!!f.ingredients?.length,home:!!f.onlyHome,nutrition:!!(f.calorieTarget||f.proteinTarget||f.fiberTarget||f.nutritionGoal!=="balanced"),cost:f.maxCost!==""&&f.maxCost!=null}[key];}
  _mountFilters(c){
    c.querySelector(".rx-shared-filters")?.remove();
    const bar=document.createElement("div");bar.className="rx-shared-filters";bar.setAttribute("role","group");bar.setAttribute("aria-label",this._t("sharedFilters"));
    bar.innerHTML=FILTERS.map(([key,icon,label])=>`<button type="button" class="btn secondary" data-filter="${key}" aria-pressed="${Boolean(this._filterActive(key))}" title="${this._escape(this._t(label))}" aria-label="${this._escape(this._t(label))}"><ha-icon icon="mdi:${icon}" aria-hidden="true"></ha-icon></button>`).join("");
    bar.querySelectorAll("button").forEach(button=>button.addEventListener("click",()=>this._showFilter(button.dataset.filter)));
    c.prepend(bar);
  }
  _renderToday(c){
    this._todaySettings=this._collectTodayV34();
    c.innerHTML=`<section class="card"><div class="toolbar"><h2>${this._escape(this._t("today"))}</h2><button id="todaySuggest" class="btn" ${this._todayBusy?"disabled":""}><ha-icon icon="mdi:chef-hat"></ha-icon>${this._escape(this._t("suggestToday"))}</button></div></section><div id="todayGrid" class="rx-category-results">${(this._todayResults||[]).map(recipe=>`<section class="rx-category-result"><h3>${this._escape(this._t(recipe.todayMealType||"main"))}</h3>${this._recipeCard(recipe,false)}</section>`).join("")}</div>`;
    this._mountFilters(c);this._bindCards(c.querySelector("#todayGrid"),this._todayResults||[],false);
    c.querySelector("#todaySuggest").addEventListener("click",()=>void this._suggestTodayV34(c));
  }
  _collectTodayV34(){const f=this._filters();return {...f,calorieTarget:f.calorieTarget??"",maxMissing:f.maxMissing??"",calorieTolerance:f.calorieTolerance||25,avoidRecentDays:f.avoidRecentDays||0,languages:f.languages??this._languageRows().map(row=>row.code),variety:true};}
  _recipeHasTodayIngredients(recipe,rows){
    const ids=new Set((recipe._nutritionIngredients||recipe.ingredients||[]).flatMap(row=>[row.ingredientId,row.key,row.foodKey]).filter(Boolean).map(String));
    return rows.every(row=>(row.sourceIngredientIds||[row.ingredientId,row.key,row.foodKey]).some(id=>ids.has(String(id))));
  }
  _renderOfficial(c){super._renderOfficial(c);c.querySelector("#officialCatalogLanguages")?.remove();this._mountFilters(c);}
  _renderWeek(c){
    super._renderWeek(c);
    this._mountFilters(c);
    c.querySelectorAll(".rx-week-slot").forEach(node=>{
      const slot=this._weekState?.slots?.find(row=>String(row.id)===node.dataset.slotId);
      node.setAttribute("role","button");node.tabIndex=0;node.setAttribute("aria-label",this._slotTitle(slot));
      const open=()=>{const recipe=slot?.recipe||this._leftoverById(slot?.leftoverId)?.recipe;if(recipe)void this._showRecipe(recipe,!this._isOfficialRecipe(recipe));else this._message(this._t("recipeUnavailable"),true);};
      node.addEventListener("click",event=>{if(!event.target.closest("button,input,select,a"))open();});
      node.addEventListener("keydown",event=>{if(event.target===node&&["Enter"," "].includes(event.key)){event.preventDefault();open();}});
    });
  }
  _showFilter(key){
    this._v63CloseFilter?.();const f=this._filters(),escape=value=>this._escape(String(value??""));
    const field=(name,label,type="number")=>`<div class="field"><label for="filter-${name}">${escape(this._t(label))}</label><input id="filter-${name}" data-field="${name}" type="${type}" ${type==="number"?'min="0" step="any"':""} value="${escape(f[name])}"></div>`;
    const check=(name,label)=>`<label><input type="checkbox" data-field="${name}" ${f[name]?"checked":""}>${escape(this._t(label))}</label>`;
    const choices=(name,rows)=>rows.map(([value,label])=>`<label><input type="checkbox" data-list="${name}" value="${escape(value)}" ${f[name]?.includes(value)?"checked":""}>${escape(label)}</label>`).join("");
    const select=(name,html)=>`<select data-field="${name}" aria-label="${escape(this._t(name))}">${html}</select>`;
    const content={
      diet:select("diet",this._todayDietOptions(f.diet)),
      meals:choices("mealTypes",MEALS.map(value=>[value,this._t(value)])),
      languages:choices("languages",this._languageRows().map(row=>[row.code,this._languageName(row.code)])),
      ingredients:`<input type="search" data-ingredient-search aria-label="${escape(this._t("ingredientSearch"))}" placeholder="${escape(this._t("ingredientSearch"))}"><div data-ingredient-choices>${choices("ingredients",this._todayIngredientRows().map(row=>[this._todayIngredientIdentity(row),row.name]))}</div>`,
      home:check("onlyHome","onlyHome")+check("preferExpiring","preferExpiring")+field("maxMissing","maxMissing")+field("avoidRecentDays","avoidRecent"),
      nutrition:select("nutritionGoal",this._todayGoalOptions(f.nutritionGoal))+field("calorieTarget","targetCalories")+field("proteinTarget","targetProtein")+field("fiberTarget","targetFiber")+`<p class="muted">${escape(this._t("targetHelp"))}</p>`,
      cost:field("maxCost","maxCost")+`<p>${escape(this._t("currency"))}: ${escape(this._currencyState?.currency||f.currency)}</p><p class="muted">${escape(this._t("costFilterHelp"))}</p>`,
    }[key]||"";
    const title=this._t(FILTERS.find(row=>row[0]===key)?.[2]||key),overlay=document.createElement("div");overlay.className="rx-overlay";overlay.setAttribute("data-filter-dialog",key);
    overlay.innerHTML=`<div class="rx-dialog" role="dialog" aria-modal="true" aria-label="${escape(title)}"><div class="detail-head"><h2>${escape(title)}</h2><button type="button" class="btn secondary" data-close aria-label="${escape(this._t("closeDialog"))}">✕</button></div>${content}<footer><button class="btn" data-apply>${escape(this._t("apply"))}</button></footer></div>`;
    const restore=this.shadowRoot.activeElement;
    const close=()=>{document.removeEventListener("keydown",keydown);overlay.remove();this._v63CloseFilter=null;restore?.focus?.();};
    const keydown=event=>{if(event.key==="Escape")close();this._trapFocus(event,overlay);};
    this._v63CloseFilter=close;document.addEventListener("keydown",keydown);
    overlay.querySelector("[data-close]").addEventListener("click",close);overlay.addEventListener("click",event=>{if(event.target===overlay)close();});
    overlay.querySelector("[data-apply]").addEventListener("click",()=>{
      const next={...f};overlay.querySelectorAll("[data-field]").forEach(input=>{next[input.dataset.field]=input.type==="checkbox"?input.checked:input.value;});
      const list={meals:"mealTypes",languages:"languages",ingredients:"ingredients"}[key];
      if(list)next[list]=[...overlay.querySelectorAll(`[data-list="${list}"]`)].filter(input=>input.checked).map(input=>input.value);
      next.currency=this._currencyState?.currency||next.currency;
      this._v63Filters=next;this._todaySettings=this._collectTodayV34();this._saveOfficialLanguages(next.languages||[]);
      this._persistPreferences({filters:next});close();this._renderTab();
    });
    overlay.querySelector("[data-ingredient-search]")?.addEventListener("input",event=>{
      const fold=value=>String(value).normalize("NFD").replace(/\p{M}/gu,"").toLowerCase();
      overlay.querySelectorAll("[data-ingredient-choices] label").forEach(label=>{label.style.display=fold(label.textContent).includes(fold(event.target.value))?"":"none";});
    });
    this.shadowRoot.appendChild(overlay);overlay.querySelector("[data-close]").focus();
    if(key==="ingredients"&&!this._ingredientCatalog?.length&&!this._ingredientCatalogLoading){
      const entry=this._entryId;void this._loadIngredientCatalog().then(()=>{if(entry===this._entryId&&overlay.isConnected)this._showFilter(key);});
    }
  }
  _trapFocus(event,overlay){
    if(event.key!=="Tab")return;
    const nodes=[...overlay.querySelectorAll("button:not([disabled]),input,select,textarea,a[href],[tabindex='0']")].filter(node=>node.style.display!=="none");
    const first=nodes[0],last=nodes.at(-1),active=this.shadowRoot.activeElement;
    if(event.shiftKey&&active===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&active===last){event.preventDefault();first?.focus();}
  }
  async _api(type,data={}){
    if(/\/(today_suggest|official_search|week_generate)$/.test(type)){
      const filters={...(data.shared_filters||this._filters()),currency:this._currencyState?.currency||this._filters().currency};
      data={...data,shared_filters:filters};
      if(type.endsWith("official_search"))data.languages=filters.languages;
      else data.ui_language=this._uiIngredientLanguage();
      if(type.endsWith("today_suggest")&&filters.ingredients?.length)data.query="";
      if(type.endsWith("week_generate"))Object.assign(data,{languages:filters.languages,diet:filters.diet});
    }
    const job=this._process?null:this._processStart(this._t("backgroundWork"),this._t("loading"));
    try{return await super._api(type,data);}catch(error){if(job)this._v59FailProcess(job,`${this._t("error")}: ${error.message||error}`);throw error;}finally{if(job)this._processEnd(job);}
  }
  async _search(query){
    const request=(this._v61SearchRequest||0)+1;this._v61SearchRequest=request;
    const entry=this._entryId,user=this._hass?.user?.id;this._searchQuery=String(query||"").trim();
    const filters={...this._filters()},job=this._processStart(this._t("official"),this._t("loading"));
    try{
      if(!filters.languages?.length)throw new Error(this._t("chooseCatalog"));
      const result=await this._api("cook4me/v31/official_search",{entry_id:entry,query:this._searchQuery,query_language:this._uiIngredientLanguage(),languages:filters.languages,shared_filters:filters,page:0,size:20});
      if(entry!==this._entryId||user!==this._hass?.user?.id||request!==this._v61SearchRequest)return;
      this._results=result.items||[];this._results.forEach(recipe=>this._ensureRecipeSelections(recipe));this._searchMeta=result;this._renderTab();
    }catch(error){this._v59FailProcess(job,`${this._t("error")}: ${error.message||error}`);}finally{this._processEnd(job);}
  }
  async _generateWeek(replace=""){
    const entry=this._entryId,user=this._hass?.user?.id,filters={...this._filters()};
    const job=this._processStart(this._t("week"),this._t("loading"));
    try{
      if(!filters.languages?.length)throw new Error(this._t("chooseCatalog"));
      const result=await this._api("cook4me/v20/week_generate",{entry_id:entry,week_start:this._weekState?.weekStart||"",replace_slot_id:replace,shared_filters:filters});
      if(entry!==this._entryId||user!==this._hass?.user?.id)return;
      this._weekState=result;this._weekStateEntry=entry;if(this._tab==="week")this._renderTab();
    }catch(error){this._v59FailProcess(job,`${this._t("error")}: ${error.message||error}`);}finally{this._processEnd(job);}
  }
  _loadOfficialLanguages(){return this._v63Filters?.languages||super._loadOfficialLanguages();}
  _isOfficialRecipe(recipe){return !!(recipe?.displayVariantId||recipe?.searchVariantId||recipe?.recipeFunctionalId||recipe?.variantFunctionalId);}
  _ensureRecipeSelections(recipe){
    const id=String(recipe?.displayVariantId||recipe?.searchVariantId||"");
    const language=(recipe?.languageVariants||[]).find(row=>row.servingVariants?.some(option=>String(option.displayVariantId)===id));
    const option=language?.servingVariants.find(row=>String(row.displayVariantId)===id);
    if(!option)return super._ensureRecipeSelections(recipe);
    Object.assign(recipe,{selectedLanguage:language.language,servingVariants:language.servingVariants,availableServings:language.availableServings,selectedServings:option.servings,selectedDisplayVariantId:id,selectedSendVariantId:option.sendVariantId||null,sendVariantId:option.sendVariantId||null,sendGroupingFunctionalId:option.sendGroupingFunctionalId||null,sendRecipeFunctionalId:option.sendRecipeFunctionalId||null,sendable:Boolean(option.sendVariantId)});
    return option;
  }
  _selectServing(recipe,variant,fromDetail=false){
    const option=(recipe.servingVariants||[]).find(row=>String(row.sendVariantId||row.displayVariantId)===String(variant));
    if(option)return this._changeRecipeVariant(recipe,option,recipe.selectedLanguage||recipe.language,fromDetail);
  }
  _selectRecipeLanguage(recipe,language,fromDetail=false){
    const options=(recipe.languageVariants||[]).find(row=>row.language===language)?.servingVariants||[];
    const option=options.find(row=>row.servings===recipe.selectedServings)||options[0];
    if(option)return this._changeRecipeVariant(recipe,option,language,fromDetail);
  }
  async _changeRecipeVariant(recipe,option,language,fromDetail){
    this._v63VariantRequests??=new WeakMap();const request={};this._v63VariantRequests.set(recipe,request);
    const entry=this._entryId,user=this._hass?.user?.id;
    const dialog=this._v63RecipeDialog,job=this._processStart(this._t("openingRecipe"),recipe.title||"");
    try{
      const detail=await this._api("cook4me/v31/recipe_detail",{entry_id:entry,variant_id:String(option.displayVariantId),language});
      if(entry!==this._entryId||user!==this._hass?.user?.id||this._v63VariantRequests.get(recipe)!==request||(fromDetail&&(dialog!==this._v63RecipeDialog||this._opened!==recipe)))return;
      Object.assign(recipe,detail,{selectedLanguage:language,selectedDisplayVariantId:detail.displayVariantId,selectedSendVariantId:detail.sendVariantId||null,selectedServings:detail.servings});
      delete recipe._nutritionIngredients;delete recipe.translationMethod;delete recipe.translatedFrom;delete recipe.cost;
      this._ensureRecipeSelections(recipe);this._renderTab();if(fromDetail)void this._loadRecipeNutrition(recipe);
    }catch(error){this._v59FailProcess(job,`${this._t("error")}: ${error.message||error}`);}finally{this._processEnd(job);}
  }
  _openOfficial(recipe){return this._showRecipe(recipe,false);}
  _openLocal(recipe){return this._showRecipe(recipe,true);}
  _toggleInlineRecipe(_card,recipe,custom){return this._showRecipe(recipe,custom);}
  _bindCards(container,items,custom=false){
    super._bindCards(container,items,custom);
    container.querySelectorAll(".recipe").forEach((card,index)=>{
      const recipe=items[index];if(!recipe)return;
      card.tabIndex=0;card.setAttribute("role","button");card.setAttribute("aria-label",recipe.title||"");
      card.addEventListener("keydown",event=>{if(event.target===card&&["Enter"," "].includes(event.key)){event.preventDefault();void this._showRecipe(recipe,custom);}});
      const send=card.querySelector('[data-action="send"]');if(send)send.disabled=!recipe.sendVariantId||recipe.match?.safe===false;
    });
  }
  _bindDetail(container){super._bindDetail(container);const send=container.querySelector("[data-detail-send]");if(send)send.disabled=!this._opened?.sendVariantId||this._opened?.match?.safe===false;}
  _detailHtml(){return "";}
  async _showRecipe(recipe,custom=false){
    this._v63CloseRecipe?.();this._v62CloseIngredient?.();
    const request={entry:this._entryId,user:this._hass?.user?.id};this._v63RecipeRequest=request;
    const current=()=>this._v63RecipeRequest===request&&this._entryId===request.entry&&this._hass?.user?.id===request.user;
    const job=this._processStart(this._t("openingRecipe"),recipe?.title||"");
    try{
      const selected=this._ensureRecipeSelections?.(recipe);
      const variant=selected?.displayVariantId||recipe.selectedDisplayVariantId||recipe.displayVariantId||recipe.searchVariantId||recipe.variantFunctionalId||recipe.recipeFunctionalId;
      let detail={...recipe};
      if(!custom&&variant)detail=await this._api("cook4me/v31/recipe_detail",{entry_id:request.entry,variant_id:String(variant),language:recipe.selectedLanguage||recipe.language||this._uiIngredientLanguage()});
      if(!current())return;
      // Fresh detail owns quantity, language and send identity; never copy proofs from another serving variant.
      this._opened={...recipe,...detail};this._ensureRecipeSelections?.(this._opened);
      const overlay=document.createElement("div");overlay.className="rx-overlay";overlay.setAttribute("data-recipe-dialog",BUILD);this._v63RecipeDialog=overlay;
      const restore=this.shadowRoot.activeElement;
      const close=()=>{document.removeEventListener("keydown",keydown);overlay.remove();this._opened=null;this._v63RecipeRequest=null;this._v63RecipeDialog=null;this._v63CloseRecipe=null;restore?.focus?.();};
      const keydown=event=>{if(event.key==="Escape"&&!this._v62CloseIngredient&&!this._v63CloseFilter)close();if(!this._v62CloseIngredient)this._trapFocus(event,overlay);};
      this._v63CloseRecipe=close;document.addEventListener("keydown",keydown);
      overlay.addEventListener("click",event=>{if(event.target===overlay)close();});
      this.shadowRoot.appendChild(overlay);this._renderRecipeDialog();overlay.querySelector("[data-modal-close]").focus();
      void this._loadRecipeNutrition(this._opened);
    }catch(error){if(current())this._v59FailProcess(job,`${this._t("error")}: ${error.message||error}`);}
    finally{this._processEnd(job);}
  }
  _renderRecipeDialog(){
    const overlay=this._v63RecipeDialog;if(!overlay)return;
    if(!this._opened){this._v63CloseRecipe?.();return;}
    overlay.innerHTML=`<div class="rx-dialog" role="dialog" aria-modal="true" aria-label="${this._escape(this._opened.title||"")}"><button class="btn secondary" data-modal-close aria-label="${this._escape(this._t("closeDialog"))}">✕</button>${super._detailHtml(this._opened)}</div>`;
    overlay.querySelector("[data-modal-close]").addEventListener("click",()=>this._v63CloseRecipe?.());this._bindDetail(overlay);
  }
  async _loadRecipeNutrition(recipe){
    const entry=this._entryId,user=this._hass?.user?.id;
    const job=this._processStart(this._t("nutrition"),recipe?.title||"");
    const variant=recipe.displayVariantId;
    const current=()=>entry===this._entryId&&user===this._hass?.user?.id&&this._opened===recipe&&recipe.displayVariantId===variant;
    try{
      const payload=this._nutritionRecipePayload(recipe);
      const [nutrition,cost]=await Promise.allSettled([
        this._api("cook4me/v16/nutrition_recipe",{entry_id:entry,recipe:payload,resolve_missing:false,max_resolve:0}),
        this._api("cook4me/v20/recipe_cost",{entry_id:entry,recipe:payload,refresh_global:false}),
      ]);
      if(!current())return;
      if(nutrition.status==="fulfilled"&&nutrition.value?.nutrition?.totals&&Object.keys(nutrition.value.nutrition.totals).length)recipe.nutrition=nutrition.value.nutrition;
      if(cost.status==="fulfilled")recipe.cost=cost.value;
      this._renderRecipeDialog();
    }finally{this._processEnd(job);}
  }
  _renderTab(){
    this._filters();if(this._tab==="recommend")this._tab="today";
    const result=super._renderTab();this._ensureV63Styles();this.setAttribute("data-cook4me-build",BUILD);this._renderRecipeDialog();this.shadowRoot?.querySelector("#translateResults")?.closest("label")?.remove();
    void this._restorePreferences();return result;
  }
  _processStart(title,detail=""){
    // Use the existing popup appearance; concurrent jobs retain separate progress.
    const previous=this._process;this._process=null;
    const token=super._processStart(title,detail);this._process=token;
    this._v63Jobs??=new Map();this._v63Jobs.set(token.id,token);
    this._ensureV63Styles();let stack=this.shadowRoot?.querySelector(".rx-v63-progress");
    if(!stack){stack=document.createElement("div");stack.className="rx-v63-progress";this.shadowRoot?.appendChild(stack);}
    stack.appendChild(token.card);token.previous=previous;return token;
  }
  _processUpdate(token,detail,done=null,total=null){if(!token||token.ended)return;token.detail=String(detail||"");this._v59RenderProcess(token,token.detail,done,total);}
  _processEnd(token){
    if(!token||token.ended)return;token.ended=true;super._processEnd(token);
    this._v63Jobs?.delete(token.id);
    if(this._process===token)this._process=[...(this._v63Jobs?.values()||[])].at(-1)||null;
  }
  _v59HandleProgress(event){
    const data=event?.data||event||{},token=this._v63Jobs?.get(String(data.operationId||""));if(!token)return;
    if(data.error)this._v59FailProcess(token,data.message||data.error);
    else this._processUpdate(token,`${this._v59PhaseLabel(data.phase)}${data.message?`: ${data.message}`:""}`,data.completed,data.total);
    if(data.done)this._processEnd(token);
  }
  _message(text,isError=false){
    super._message("",false);if(!String(text||""))return;
    const created=!this._process,token=this._process||this._processStart(this._t("backgroundWork"),String(text));
    if(isError)this._v59FailProcess(token,text);else this._processUpdate(token,text);
    if(created){this._processEnd(token);if(!isError)this._v59RenderProcess(token,text,1,1);}
  }
  _updateBackgroundStatus(){
    this.shadowRoot?.querySelectorAll("[data-v54-background]").forEach(node=>node.remove());
    const active=this._v54RefreshingSections?.size>0;
    if(active&&!this._v63RefreshJob)this._v63RefreshJob=this._processStart(this._t("backgroundWork"),this._t("cacheUpdating"));
    if(!active&&this._v63RefreshJob){this._processEnd(this._v63RefreshJob);this._v63RefreshJob=null;}
  }
  _decorateElementLoadingStates(){this.shadowRoot?.querySelectorAll("[data-v54-element-loading]").forEach(node=>node.remove());}
  disconnectedCallback(){
    this._v63CloseRecipe?.();this._v63CloseFilter?.();this._v63RecipeRequest=null;
    document.removeEventListener("visibilitychange",this._v63Resume);window.removeEventListener("online",this._v63Resume);
    for(const token of this._v63Jobs?.values()||[]){clearTimeout(token.removeTimer);token.card?.remove();}this._v63Jobs?.clear();
    super.disconnectedCallback();
  }
}

customElements.define("cook4me-recipe-hub-panel-v63",Cook4MeRecipeHubPanelV63);
