import "./cook4me-panel-v58.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v58");
const SHELL_VERSION=2;
const MAX_SYNC_SHELL_BYTES=120000;
const TARGET_SYNC_SHELL_BYTES=96000;
const PROGRESS_EVENT="cook4me_operation_progress";

const TEXT={
  en:{officialSebNutrition:"Official SEB nutrition",per100g:"per 100 g",basisUnspecified:"basis not specified by SEB",nutritionCoverageShort:"coverage",estimatedShort:"estimated",fiberShort:"Fibre",phaseStarting:"Starting",phaseCatalogIndex:"Searching local catalog",phaseCatalogNetwork:"Loading official catalog",phaseCatalogs:"Catalogs",phaseExpiryCandidates:"Expiring ingredients",phaseRanking:"Ranking recipes",phaseNutrition:"Calculating nutrition",phaseDetailCache:"Loading cached recipe",phaseDetailNetwork:"Retrieving recipe",phaseDetailNormalize:"Caching recipe",phasePersist:"Saving locally",phaseCost:"Calculating price",phaseCostSources:"Checking price sources",phaseDone:"Done",phaseFailed:"Failed"},
  de:{officialSebNutrition:"Offizielle SEB-Nährwerte",per100g:"pro 100 g",basisUnspecified:"Bezugsbasis von SEB nicht angegeben",nutritionCoverageShort:"Abdeckung",estimatedShort:"geschätzt",fiberShort:"Ballastst.",phaseStarting:"Start",phaseCatalogIndex:"Lokaler Katalog wird durchsucht",phaseCatalogNetwork:"Offizieller Katalog wird geladen",phaseCatalogs:"Kataloge",phaseExpiryCandidates:"Bald ablaufende Zutaten",phaseRanking:"Rezepte werden bewertet",phaseNutrition:"Nährwerte werden berechnet",phaseDetailCache:"Gespeichertes Rezept wird geladen",phaseDetailNetwork:"Rezept wird abgerufen",phaseDetailNormalize:"Rezept wird gespeichert",phasePersist:"Lokal speichern",phaseCost:"Preis wird berechnet",phaseCostSources:"Preisquellen werden geprüft",phaseDone:"Fertig",phaseFailed:"Fehlgeschlagen"},
  el:{officialSebNutrition:"Επίσημα διατροφικά στοιχεία SEB",per100g:"ανά 100 g",basisUnspecified:"η βάση δεν καθορίζεται από τη SEB",nutritionCoverageShort:"κάλυψη",estimatedShort:"εκτίμηση",fiberShort:"Ίνες",phaseStarting:"Έναρξη",phaseCatalogIndex:"Αναζήτηση τοπικού καταλόγου",phaseCatalogNetwork:"Φόρτωση επίσημου καταλόγου",phaseCatalogs:"Κατάλογοι",phaseExpiryCandidates:"Υλικά που λήγουν",phaseRanking:"Κατάταξη συνταγών",phaseNutrition:"Υπολογισμός διατροφής",phaseDetailCache:"Φόρτωση αποθηκευμένης συνταγής",phaseDetailNetwork:"Ανάκτηση συνταγής",phaseDetailNormalize:"Αποθήκευση συνταγής",phasePersist:"Τοπική αποθήκευση",phaseCost:"Υπολογισμός τιμής",phaseCostSources:"Έλεγχος πηγών τιμών",phaseDone:"Ολοκληρώθηκε",phaseFailed:"Απέτυχε"},
};

function copySmall(value,fallback=null){
  if(value===undefined)return fallback;
  try{return typeof structuredClone==="function"?structuredClone(value):JSON.parse(JSON.stringify(value));}
  catch(_e){return fallback;}
}

class Cook4MeRecipeHubPanelV59 extends BasePanel{
  constructor(){
    super();
    this._v59IdlePersist=null;
    this._v59ProgressConnection=null;
    this._v59ProgressUnsub=null;
    this._v59ProcessSequence=0;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  get hass(){return this._hass;}
  set hass(value){
    const next=String(value?.user?.id||value?.user?.name||"anonymous");
    if(this._v54CacheUser&&next!==this._v54CacheUser)this._v59CancelIdlePersist();
    super.hass=value;
    void this._v59EnsureProgressSubscription();
  }

  _snapshotKey(user=this._v54CacheUser||String(this._hass?.user?.id||"anonymous")){
    return `cook4me.ui.shell.v2.${user}`;
  }

  _legacySnapshotKey(user=this._v54CacheUser||String(this._hass?.user?.id||"anonymous")){
    return `cook4me.ui.snapshot.v54.${user}`;
  }

  _v59BlankShell(){return {version:SHELL_VERSION,savedAt:0,selectedEntryId:"",entries:[],perEntry:{},fullOverviewCached:false};}

  _hydrateUiSnapshot(user){
    this._v54CacheUser=String(user||"anonymous");
    this._v54CacheHydrated=true;
    let cached=null;
    try{
      const raw=globalThis.localStorage?.getItem(this._snapshotKey(this._v54CacheUser));
      // Never parse an unexpectedly large synchronous startup payload.
      if(raw&&raw.length<=MAX_SYNC_SHELL_BYTES)cached=JSON.parse(raw);
    }catch(_e){}
    if(!cached||cached.version!==SHELL_VERSION||typeof cached!=="object"){
      this._v54Cache=this._v59BlankShell();
      this._v54HadUiCache=false;
      this._v54HasCachedFullOverview=false;
      this._v59ScheduleLegacySnapshotCleanup();
      return;
    }
    this._v54Cache={...this._v59BlankShell(),...cached,fullOverviewCached:false};
    const entries=Array.isArray(cached.entries)?cached.entries:[];
    if(entries.length){
      this._entries=entries;
      const wanted=String(cached.selectedEntryId||"");
      this._entryId=entries.some(row=>String(row?.entry_id||"")===wanted)?wanted:String(entries[0]?.entry_id||"")||null;
    }
    this._v54HadUiCache=entries.length>0;
    // The shell is intentionally not a full overview. Heavy state must hydrate
    // asynchronously from HA-side stores after the browser gets its first paint.
    this._v54HasCachedFullOverview=false;
    if(this._entryId){
      this._applyEntrySnapshot(this._entryId);
      const remembered=String(this._entrySnapshot(this._entryId)?.uiPreferences?.lastTab||"");
      if(remembered)this._tab=remembered;
    }
    this._v59ScheduleLegacySnapshotCleanup();
  }

  _v59ScheduleLegacySnapshotCleanup(){
    const run=()=>{try{globalThis.localStorage?.removeItem(this._legacySnapshotKey());}catch(_e){}};
    if(typeof globalThis.requestIdleCallback==="function")globalThis.requestIdleCallback(run,{timeout:3000});
    else setTimeout(run,1500);
  }

  _v59CompactNutrition(value){
    if(!value||typeof value!=="object")return null;
    const out={};
    for(const key of ["totals","perServing"]){
      const raw=value[key];if(!raw||typeof raw!=="object")continue;
      out[key]={};for(const [name,number] of Object.entries(raw))if(Number.isFinite(Number(number)))out[key][name]=Number(number);
    }
    for(const key of ["servings","coverage","fullyCovered","estimated"])if(value[key]!==undefined)out[key]=value[key];
    if(Array.isArray(value.sourceKinds))out.sourceKinds=value.sourceKinds.slice(0,8).map(String);
    return Object.keys(out).length?out:null;
  }

  _v59CompactMatch(value){
    if(!value||typeof value!=="object")return null;
    const out={};
    for(const key of ["score","baseScore","pantryCoverage","quantityCoverage","quantityConfidence","fullyAvailableByQuantity","expiryPriority","expiryBonus","nutritionGoal","nutritionGoalBonus","nutritionGoalCoverage","calorieTarget","caloriePerServing","calorieDelta","calorieTargetBonus","todayBaseScore"]){if(value[key]!==undefined)out[key]=value[key];}
    if(Array.isArray(value.quantityShortages))out.quantityShortageCount=value.quantityShortages.length;
    if(Array.isArray(value.missingIngredients))out.missingIngredientCount=value.missingIngredients.length;
    return Object.keys(out).length?out:null;
  }

  _v59CompactTodayRecipe(recipe){
    if(!recipe||typeof recipe!=="object")return null;
    const out={};
    for(const key of ["groupingFunctionalId","recipeFunctionalId","variantFunctionalId","searchVariantId","displayVariantId","sendVariantId","sendGroupingFunctionalId","sendRecipeFunctionalId","title","originalTitle","originalLanguage","canonicalName","cover","language","market","groupSize","todayCatalogLanguage","source","releaseCatalogVersion","deviceCanAccept","sendable"]){if(recipe[key]!==undefined&&recipe[key]!==null&&recipe[key]!=="")out[key]=recipe[key];}
    if(recipe.yield&&typeof recipe.yield==="object")out.yield=Object.fromEntries(Object.entries(recipe.yield).filter(([key,value])=>["quantity","quantityDisplay","unit","unitKey"].includes(key)&&value!==null&&value!==""));
    const nutrition=this._v59CompactNutrition(recipe.nutrition);if(nutrition)out.nutrition=nutrition;
    const match=this._v59CompactMatch(recipe.match);if(match)out.match=match;
    return out.title||out.searchVariantId?out:null;
  }

  _v59CompactTodayMeta(meta){
    if(!meta||typeof meta!=="object")return meta??null;
    const out={};
    for(const key of ["date","candidateCount","rankedCount","catalogMode","catalogVersion","catalogCandidateCounts","catalogRankedCounts","catalogSelectedCounts","catalogLanguagesUsed","filters"]){if(meta[key]!==undefined)out[key]=copySmall(meta[key],meta[key]);}
    return out;
  }

  _v59CompactEntry(entry){
    if(!entry||typeof entry!=="object")return null;
    const out={};
    for(const key of ["entry_id","title","connected","canAcceptRecipe","loadedRecipe","configuredLanguage","country"]){if(entry[key]!==undefined)out[key]=copySmall(entry[key],entry[key]);}
    if(entry.state&&typeof entry.state==="object"){
      const state={};let count=0;
      for(const [key,value] of Object.entries(entry.state)){
        if(count>=24)break;
        if(value===null||["string","number","boolean"].includes(typeof value)){state[key]=value;count++;}
      }
      if(Object.keys(state).length)out.state=state;
    }
    return out.entry_id?out:null;
  }

  _v59CompactCapabilities(value){
    if(!value||typeof value!=="object")return null;
    const out={};
    for(const key of ["deviceCatalogLanguage","ingredientCatalogLanguage","defaultAiTaskAvailable","persistentCache"]){if(value[key]!==undefined)out[key]=value[key];}
    return Object.keys(out).length?out:null;
  }

  _captureEntrySnapshot(entryId=this._entryId){
    const id=String(entryId||"");if(!id)return;
    const previous=this._v54Cache?.perEntry?.[id]||{};
    const today=(this._todayResults||[]).slice(0,8).map(row=>this._v59CompactTodayRecipe(row)).filter(Boolean);
    const row={
      ...previous,
      uiPreferences:copySmall(this._uiPreferences||{},{}),
      todayOptions:copySmall(this._todayOptions||null,null),
      todayResults:today,
      todayMeta:this._v59CompactTodayMeta(this._todayMeta),
      capabilities:this._v59CompactCapabilities(this._capabilities),
      savedAt:Date.now(),
    };
    this._v54Cache={...(this._v54Cache||this._v59BlankShell()),perEntry:{...(this._v54Cache?.perEntry||{}),[id]:row}};
  }

  _v59CancelIdlePersist(){
    if(this._v54PersistTimer){clearTimeout(this._v54PersistTimer);this._v54PersistTimer=null;}
    if(this._v59IdlePersist!==null&&typeof globalThis.cancelIdleCallback==="function"){
      try{globalThis.cancelIdleCallback(this._v59IdlePersist);}catch(_e){}
    }
    this._v59IdlePersist=null;
  }

  _scheduleSnapshotPersist(){
    this._v59CancelIdlePersist();
    const persist=()=>{this._v54PersistTimer=null;this._v59IdlePersist=null;this._persistUiSnapshot();};
    if(typeof globalThis.requestIdleCallback==="function")this._v59IdlePersist=globalThis.requestIdleCallback(persist,{timeout:1800});
    else this._v54PersistTimer=setTimeout(persist,800);
  }

  _v59BuildShell(){
    this._captureEntrySnapshot();
    const entries=(this._entries||[]).map(row=>this._v59CompactEntry(row)).filter(Boolean);
    const known=this._v54Cache?.perEntry||{};
    const perEntry={};
    for(const entry of entries){
      const id=String(entry.entry_id||"");const raw=known[id]||{};
      perEntry[id]={
        uiPreferences:copySmall(raw.uiPreferences||{},{}),
        todayOptions:copySmall(raw.todayOptions||null,null),
        todayResults:(raw.todayResults||[]).slice(0,8).map(row=>this._v59CompactTodayRecipe(row)).filter(Boolean),
        todayMeta:this._v59CompactTodayMeta(raw.todayMeta),
        capabilities:this._v59CompactCapabilities(raw.capabilities),
        savedAt:Number(raw.savedAt||Date.now()),
      };
    }
    return {version:SHELL_VERSION,savedAt:Date.now(),selectedEntryId:String(this._entryId||""),entries,perEntry,fullOverviewCached:false};
  }

  _persistUiSnapshot(){
    if(!this._v54CacheUser)return;
    let shell=this._v59BuildShell();
    try{
      let text=JSON.stringify(shell);
      if(text.length>TARGET_SYNC_SHELL_BYTES){
        for(const [id,row] of Object.entries(shell.perEntry||{}))if(id!==shell.selectedEntryId)row.todayResults=[];
        text=JSON.stringify(shell);
      }
      if(text.length>TARGET_SYNC_SHELL_BYTES){
        const selected=shell.perEntry?.[shell.selectedEntryId];if(selected)selected.todayResults=(selected.todayResults||[]).slice(0,4);
        text=JSON.stringify(shell);
      }
      if(text.length>MAX_SYNC_SHELL_BYTES){
        const selected=shell.perEntry?.[shell.selectedEntryId];if(selected)selected.todayResults=[];
        text=JSON.stringify(shell);
      }
      if(text.length<=MAX_SYNC_SHELL_BYTES){
        globalThis.localStorage?.setItem(this._snapshotKey(),text);
        this._v54Cache=shell;
      }
    }catch(_e){}
  }

  _v59MapApi(type){
    const value=String(type||"");
    const map={
      "cook4me/search":"cook4me/v30/search",
      "cook4me/v9/search":"cook4me/v30/search",
      "cook4me/v10/search":"cook4me/v30/search",
      "cook4me/recommend":"cook4me/v30/recommend",
      "cook4me/v9/recommend":"cook4me/v30/recommend",
      "cook4me/v10/recommend":"cook4me/v30/recommend",
      "cook4me/v13/recommend":"cook4me/v30/recommend",
      "cook4me/recipe_detail":"cook4me/v30/recipe_detail",
      "cook4me/v9/recipe_detail":"cook4me/v30/recipe_detail",
      "cook4me/v24/recipe_detail":"cook4me/v30/recipe_detail",
      "cook4me/v11/ingredient_catalog":"cook4me/v30/ingredient_catalog",
      "cook4me/v28/ingredient_catalog":"cook4me/v30/ingredient_catalog",
      "cook4me/v18/today_suggest":"cook4me/v30/today_suggest",
      "cook4me/v29/today_suggest":"cook4me/v30/today_suggest",
      "cook4me/v28/ui_seed":"cook4me/v30/ui_seed",
      "cook4me/v20/recipe_cost":"cook4me/v30/recipe_cost",
    };
    return map[value]||value;
  }

  async _api(type,data={}){
    const mapped=this._v59MapApi(type);
    const payload={...(data||{})};
    if(mapped.startsWith("cook4me/v30/")&&this._process?.id&&!payload.client_operation_id)payload.client_operation_id=this._process.id;
    return super._api(mapped,payload);
  }

  _ensureV59Styles(){
    if(this.shadowRoot?.getElementById("cook4meV59Styles"))return;
    const style=document.createElement("style");style.id="cook4meV59Styles";style.textContent=`
      .rx-v59-op{position:fixed;right:18px;bottom:18px;z-index:10050;width:min(390px,calc(100vw - 36px));padding:13px 14px;border:1px solid var(--divider-color);border-radius:14px;background:var(--card-background-color);box-shadow:0 10px 35px rgba(0,0,0,.24);color:var(--primary-text-color);pointer-events:none}
      .rx-v59-op.bad{border-color:var(--error-color)}.rx-v59-op-head{display:flex;gap:10px;align-items:center}.rx-v59-op-head ha-icon{--mdc-icon-size:20px;color:var(--primary-color)}.rx-v59-op.bad .rx-v59-op-head ha-icon{color:var(--error-color)}
      .rx-v59-op-title{font-weight:700;line-height:1.25}.rx-v59-op-detail{margin-top:5px;color:var(--secondary-text-color);font-size:13px;line-height:1.35}.rx-v59-op-count{margin-left:auto;font-size:12px;color:var(--secondary-text-color);white-space:nowrap}
      .rx-v59-op-track{height:5px;margin-top:10px;border-radius:999px;background:color-mix(in srgb,var(--primary-text-color) 12%,transparent);overflow:hidden}.rx-v59-op-bar{height:100%;width:28%;border-radius:inherit;background:var(--primary-color);transition:width .18s ease}.rx-v59-op.indeterminate .rx-v59-op-bar{animation:rxV59Progress 1.15s ease-in-out infinite}.rx-v59-op.bad .rx-v59-op-bar{background:var(--error-color)}
      @keyframes rxV59Progress{0%{transform:translateX(-130%)}55%{transform:translateX(160%)}100%{transform:translateX(320%)}}
      .rx-v59-nutrition-meta{font-size:11px;opacity:.9}
      .rx-v59-official-nutrition{margin:12px 0}.rx-v59-official-row{display:flex;justify-content:space-between;gap:12px;padding:6px 0;border-bottom:1px solid var(--divider-color)}.rx-v59-official-row:last-child{border-bottom:0}
    `;this.shadowRoot?.appendChild(style);
  }

  _renderShell(){const result=super._renderShell();this._ensureV59Styles();return result;}

  _v59ProcessId(){
    try{if(globalThis.crypto?.randomUUID)return `cook4me-${globalThis.crypto.randomUUID()}`;}catch(_e){}
    this._v59ProcessSequence+=1;return `cook4me-${Date.now()}-${this._v59ProcessSequence}`;
  }

  _processStart(title,detail=""){
    this._ensureV59Styles();
    if(this._process?.removeTimer)clearTimeout(this._process.removeTimer);
    this._process?.card?.remove();
    const token={cancelled:false,id:this._v59ProcessId(),title:String(title||"Cook4Me"),detail:String(detail||""),failed:false,card:null,removeTimer:null,phase:""};
    const card=document.createElement("div");card.className="rx-v59-op indeterminate";card.setAttribute("role","status");card.setAttribute("aria-live","polite");card.innerHTML=`<div class="rx-v59-op-head"><ha-icon icon="mdi:progress-clock"></ha-icon><div class="rx-v59-op-title"></div><div class="rx-v59-op-count"></div></div><div class="rx-v59-op-detail"></div><div class="rx-v59-op-track"><div class="rx-v59-op-bar"></div></div>`;
    token.card=card;this._process=token;this.shadowRoot?.appendChild(card);this._v59RenderProcess(token,detail,null,null);return token;
  }

  _v59PhaseLabel(phase){
    const map={starting:"phaseStarting",catalog_index:"phaseCatalogIndex",catalog_network:"phaseCatalogNetwork",catalogs:"phaseCatalogs",expiry_candidates:"phaseExpiryCandidates",ranking:"phaseRanking",nutrition:"phaseNutrition",detail_cache:"phaseDetailCache",detail_network:"phaseDetailNetwork",detail_normalize:"phaseDetailNormalize",persist:"phasePersist",cost:"phaseCost",cost_sources:"phaseCostSources",done:"phaseDone",failed:"phaseFailed"};
    return this._t(map[String(phase||"")]||String(phase||""));
  }

  _v59RenderProcess(token,detail,done,total){
    if(!token?.card)return;
    token.card.querySelector(".rx-v59-op-title").textContent=token.title||"Cook4Me";
    token.card.querySelector(".rx-v59-op-detail").textContent=String(detail||token.detail||"");
    const count=token.card.querySelector(".rx-v59-op-count");const bar=token.card.querySelector(".rx-v59-op-bar");
    const d=Number(done),t=Number(total),determinate=Number.isFinite(d)&&Number.isFinite(t)&&t>0;
    token.card.classList.toggle("indeterminate",!determinate&&!token.failed);
    if(determinate){const pct=Math.max(0,Math.min(100,d/t*100));bar.style.width=`${pct}%`;bar.style.transform="none";count.textContent=`${Math.round(d)} / ${Math.round(t)} · ${Math.round(pct)}%`;}
    else{bar.style.width=token.failed?"100%":"28%";count.textContent="";}
  }

  _processUpdate(token,detail,done=null,total=null){if(!token||token!==this._process)return;token.detail=String(detail||"");this._v59RenderProcess(token,token.detail,done,total);}

  _v59FailProcess(token,message){
    if(!token)return;token.failed=true;token.detail=String(message||this._t("phaseFailed"));token.card?.classList.add("bad");token.card?.classList.remove("indeterminate");
    const icon=token.card?.querySelector("ha-icon");if(icon)icon.setAttribute("icon","mdi:alert-circle-outline");
    this._v59RenderProcess(token,token.detail,null,null);
  }

  _processEnd(token){
    if(!token)return;
    if(token.removeTimer)clearTimeout(token.removeTimer);
    if(!token.failed){
      token.card?.classList.remove("indeterminate");const icon=token.card?.querySelector("ha-icon");if(icon)icon.setAttribute("icon","mdi:check-circle-outline");this._v59RenderProcess(token,this._t("phaseDone"),1,1);
    }
    const delay=token.failed?2600:650;
    token.removeTimer=setTimeout(()=>{token.card?.remove();if(this._process===token)this._process=null;},delay);
  }

  _message(text,isError=false){
    if(isError&&this._process&&String(text||"")){
      this._v59FailProcess(this._process,text);
      try{return super._message("",false);}catch(_e){return;}
    }
    return super._message(text,isError);
  }

  async _v59EnsureProgressSubscription(){
    const connection=this._hass?.connection;if(!connection||typeof connection.subscribeEvents!=="function")return;
    if(this._v59ProgressConnection===connection&&this._v59ProgressUnsub)return;
    await this._v59DropProgressSubscription();this._v59ProgressConnection=connection;
    try{this._v59ProgressUnsub=await connection.subscribeEvents(event=>this._v59HandleProgress(event),PROGRESS_EVENT);}catch(_e){this._v59ProgressUnsub=null;}
  }

  async _v59DropProgressSubscription(){
    const unsub=this._v59ProgressUnsub;this._v59ProgressUnsub=null;this._v59ProgressConnection=null;
    if(typeof unsub==="function"){try{await unsub();}catch(_e){}}
  }

  _v59HandleProgress(event){
    const data=event?.data&&typeof event.data==="object"?event.data:event||{};const token=this._process;if(!token||String(data.operationId||"")!==String(token.id||""))return;
    token.phase=String(data.phase||token.phase||"");
    const phase=this._v59PhaseLabel(token.phase);const message=String(data.message||"");const detail=message?`${phase}: ${message}`:phase;
    if(data.error){this._v59FailProcess(token,message||String(data.error));return;}
    this._processUpdate(token,detail,data.completed,data.total);
    if(data.done)this._processEnd(token);
  }

  _v59Metric(value,key,unit="g"){
    const number=Number(value);if(!Number.isFinite(number))return"";const shown=key==="energyKcal"?Math.round(number):Number(number.toFixed(1));return `${shown}${unit?` ${unit}`:""}`;
  }

  _recipeCard(recipe,custom=false){
    let html=super._recipeCard(recipe,custom);const nutrition=recipe?.nutrition;if(!nutrition||typeof nutrition!=="object")return html;
    const values=nutrition.perServing&&Object.keys(nutrition.perServing).length?nutrition.perServing:nutrition.totals;const extras=[];
    if(Number.isFinite(Number(values?.fiber)))extras.push(`<span class="chip" data-v59-nutrition>${this._escape(this._t("fiberShort"))}: ${this._escape(this._v59Metric(values.fiber,"fiber","g"))}</span>`);
    if(Number.isFinite(Number(nutrition.coverage))){const coverage=Math.round(Number(nutrition.coverage)*100);extras.push(`<span class="chip rx-v59-nutrition-meta" data-v59-nutrition>${this._escape(this._t("nutritionCoverageShort"))}: ${coverage}%${nutrition.estimated?` · ${this._escape(this._t("estimatedShort"))}`:""}</span>`);}
    return extras.length?html.replace('<div class="chips">',`<div class="chips">${extras.join("")}`):html;
  }

  _v59OfficialUnit(row){const unit=row?.unit;if(typeof unit==="string")return unit;if(unit&&typeof unit==="object")return String(unit.abbreviation||unit.name||unit.key||"");return"";}

  _v59OfficialNutritionBlock(official){
    if(!official||typeof official!=="object")return"";const rows=[];const energy=Number(official.energyPer100gValue);if(Number.isFinite(energy))rows.push(`<div class="rx-v59-official-row"><span>Energy</span><strong>${this._escape(String(Number(energy.toFixed(2))))} ${this._escape(String(official.energyUnit?.abbreviation||official.energyUnit?.name||""))} · ${this._escape(this._t("per100g"))}</strong></div>`);
    for(const row of official.hierarchicalNutrients||[]){const value=Number(row?.valuePer100g);if(!Number.isFinite(value))continue;const name=Array.isArray(row.path)&&row.path.length?row.path.join(" › "):String(row.name||row.key||"Nutrient");rows.push(`<div class="rx-v59-official-row"><span>${this._escape(name)}</span><strong>${this._escape(String(Number(value.toFixed(3))))} ${this._escape(this._v59OfficialUnit(row))} · ${this._escape(this._t("per100g"))}</strong></div>`);}
    for(const row of official.nutrients||[]){if(String(row?.basis||"")!=="unspecified"||!Number.isFinite(Number(row?.quantity)))continue;const name=String(row.name||row.key||"Nutrient");rows.push(`<div class="rx-v59-official-row"><span>${this._escape(name)}</span><strong>${this._escape(String(row.quantity))} ${this._escape(this._v59OfficialUnit(row))}<br><small>${this._escape(this._t("basisUnspecified"))}</small></strong></div>`);}
    const meta=[];for(const [key,label] of [["nutritionalScore","Score"],["ecologicalScore","Eco"],["nutritionalIndicator","Indicator"],["partWeight","Part weight"]])if(official[key]!==undefined&&official[key]!==null&&official[key]!=="")meta.push(`<span class="chip">${this._escape(label)}: ${this._escape(String(official[key]))}</span>`);
    if(!rows.length&&!meta.length)return"";return `<section class="card rx-v59-official-nutrition"><h3 style="margin-top:0">${this._escape(this._t("officialSebNutrition"))}</h3>${meta.length?`<div class="chips" style="margin-bottom:8px">${meta.join("")}</div>`:""}${rows.join("")}</section>`;
  }

  _detailHtml(recipe){
    let html=super._detailHtml(recipe);if(!html||!recipe)return html;const official=this._v59OfficialNutritionBlock(recipe.officialNutrition);if(!official)return html;const marker='<div class="detail-layout"';const pos=html.indexOf(marker);return pos>=0?`${html.slice(0,pos)}${official}${html.slice(pos)}`:`${official}${html}`;
  }

  disconnectedCallback(){
    this._v59CancelIdlePersist();void this._v59DropProgressSubscription();if(this._process?.removeTimer)clearTimeout(this._process.removeTimer);this._process?.card?.remove();this._process=null;
    if(super.disconnectedCallback)super.disconnectedCallback();
  }
}

customElements.define("cook4me-recipe-hub-panel-v59",Cook4MeRecipeHubPanelV59);
