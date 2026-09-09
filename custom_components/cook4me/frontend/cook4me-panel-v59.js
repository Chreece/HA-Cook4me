import "./cook4me-panel-v58.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v58");
const SHELL_VERSION=2;
const SHELL_LIMIT=80*1024;
const PROGRESS_EVENT="cook4me_operation_progress";
const VALID_TABS=new Set(["today","official","recommend","book","mine","profile","shopping","ai"]);
const PROGRESS_CAPABLE=new Set(["cook4me/v30/ingredient_catalog","cook4me/v30/official_search","cook4me/v30/recipe_detail","cook4me/v30/recipe_cost","cook4me/v30/today_suggest"]);

const TEXT={
  en:{nutritionCoverage:"Nutrition coverage",estimatedNutrition:"estimated",calculatedNutrition:"Calculated meal nutrition",wholeRecipe:"Whole recipe",perServing:"Per serving",officialNutrition:"Official SEB nutrition",per100g:"per 100 g",basisUnknown:"basis not specified by SEB",nutritionalScore:"Nutritional score",ecologicalScore:"Ecological score",partWeight:"Part weight"},
  de:{nutritionCoverage:"Nährwertabdeckung",estimatedNutrition:"geschätzt",calculatedNutrition:"Berechnete Mahlzeit-Nährwerte",wholeRecipe:"Gesamtes Rezept",perServing:"Pro Portion",officialNutrition:"Offizielle SEB-Nährwerte",per100g:"pro 100 g",basisUnknown:"Bezugsbasis von SEB nicht angegeben",nutritionalScore:"Nährwert-Score",ecologicalScore:"Öko-Score",partWeight:"Portionsgewicht"},
  el:{nutritionCoverage:"Κάλυψη διατροφικών στοιχείων",estimatedNutrition:"εκτίμηση",calculatedNutrition:"Υπολογισμένα διατροφικά στοιχεία γεύματος",wholeRecipe:"Ολόκληρη συνταγή",perServing:"Ανά μερίδα",officialNutrition:"Επίσημα διατροφικά στοιχεία SEB",per100g:"ανά 100 g",basisUnknown:"η βάση δεν προσδιορίζεται από τη SEB",nutritionalScore:"Διατροφική βαθμολογία",ecologicalScore:"Οικολογική βαθμολογία",partWeight:"Βάρος μερίδας"},
};

class Cook4MeRecipeHubPanelV59 extends BasePanel{
  constructor(){
    super();
    this._v59Operations=new Map();
    this._v59ProgressUnsub=null;
    this._v59ProgressSubLoading=null;
    this._v59PersistHandle=null;
    this._v59TodayStateEntry="";
    this._v59TodayStatePromise=null;
    this._v59LegacyCleanupScheduled=false;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  get hass(){return this._hass;}
  set hass(value){
    super.hass=value;
    this._v59EnsureProgressSubscription();
    this._v59ScheduleLegacyCleanup();
  }

  connectedCallback(){
    if(super.connectedCallback)super.connectedCallback();
    this._v59EnsureProgressSubscription();
    this._v59ScheduleLegacyCleanup();
  }

  disconnectedCallback(){
    const unsubscribe=this._v59ProgressUnsub;
    this._v59ProgressUnsub=null;
    if(typeof unsubscribe==="function"){
      try{unsubscribe();}catch(_e){}
    }
    if(super.disconnectedCallback)super.disconnectedCallback();
  }

  _v59UserId(user=null){return String(user?.id||this._hass?.user?.id||"anonymous");}
  _snapshotKey(user=null){return `cook4me.ui.shell.v2.${this._v59UserId(user)}`;}
  _v59LegacySnapshotKey(user=null){return `cook4me.ui.snapshot.v54.${this._v59UserId(user)}`;}

  _hydrateUiSnapshot(user){
    const userId=this._v59UserId(user);
    if(this._v54CacheUser===userId&&this._v54CacheHydrated)return;
    this._v54CacheUser=userId;
    this._v54CacheHydrated=true;
    this._v54Cache=null;
    this._v54HadUiCache=false;
    this._v54HasCachedFullOverview=false;
    let shell=null;
    try{shell=JSON.parse(localStorage.getItem(this._snapshotKey(user))||"null");}catch(_e){shell=null;}
    if(!shell||Number(shell.version)!==SHELL_VERSION)return;
    const entries=Array.isArray(shell.entries)?shell.entries.filter(row=>row&&row.entry_id).slice(0,12):[];
    if(!entries.length)return;
    this._entries=entries;
    const selected=String(shell.selectedEntryId||"");
    this._entryId=entries.some(row=>String(row.entry_id)===selected)?selected:String(entries[0].entry_id);
    const tab=String(shell.tab||"");
    if(VALID_TABS.has(tab))this._tab=tab;
    const today=shell.todayByEntry?.[this._entryId];
    if(today&&Array.isArray(today.cards)){
      this._todayResults=today.cards.slice(0,8);
      this._todayMeta=today.meta||null;
    }
    this._v54Cache={version:1,userId,savedAt:shell.savedAt||Date.now(),selectedEntryId:this._entryId,entries,perEntry:{}};
    if(today)this._v54Cache.perEntry[this._entryId]={todayResults:this._todayResults||[],todayMeta:this._todayMeta||null};
    this._v54HadUiCache=true;
  }

  _captureEntrySnapshot(){return null;}

  _v59CompactEntry(row){
    if(!row||!row.entry_id)return null;
    return {
      entry_id:String(row.entry_id),
      title:String(row.title||"Cook4Me"),
      connected:Boolean(row.connected),
      canAcceptRecipe:Boolean(row.canAcceptRecipe),
      loadedRecipe:row.loadedRecipe?{title:String(row.loadedRecipe.title||""),variantId:String(row.loadedRecipe.variantId||row.loadedRecipe.id||"")}:null,
      state:row.state?{phase:String(row.state.phase||row.state.status||""),status:String(row.state.status||""),recipeTitle:String(row.state.recipeTitle||"")}:null,
      configuredLanguage:String(row.configuredLanguage||""),
      country:String(row.country||""),
    };
  }

  _v59CompactNutrition(value){
    if(!value||typeof value!=="object")return null;
    const pick=source=>{const out={};for(const key of ["energyKcal","energyKJ","protein","carbohydrates","sugars","fat","saturatedFat","fiber","salt","sodium"]){const n=Number(source?.[key]);if(Number.isFinite(n))out[key]=n;}return out;};
    const result={perServing:pick(value.perServing),totals:pick(value.totals),coverage:Number(value.coverage||0),fullyCovered:Boolean(value.fullyCovered),estimated:Boolean(value.estimated),servings:value.servings??null};
    return Object.keys(result.perServing).length||Object.keys(result.totals).length?result:null;
  }

  _v59CompactCard(recipe){
    if(!recipe||typeof recipe!=="object")return null;
    const match=recipe.match||{};
    return {
      releaseCatalogId:recipe.releaseCatalogId||undefined,
      title:String(recipe.title||""),
      cover:String(recipe.cover||""),
      language:String(recipe.language||""),
      todayCatalogLanguage:String(recipe.todayCatalogLanguage||recipe.officialCatalogLanguage||""),
      searchVariantId:recipe.searchVariantId||undefined,
      displayVariantId:recipe.displayVariantId||undefined,
      sendVariantId:recipe.sendVariantId||undefined,
      groupingFunctionalId:recipe.groupingFunctionalId||undefined,
      sendGroupingFunctionalId:recipe.sendGroupingFunctionalId||undefined,
      sendRecipeFunctionalId:recipe.sendRecipeFunctionalId||undefined,
      sendable:recipe.sendable!==false,
      groupSize:recipe.groupSize??undefined,
      yield:recipe.yield?{quantity:recipe.yield.quantity,quantityDisplay:recipe.yield.quantityDisplay,unit:recipe.yield.unit}:undefined,
      nutrition:this._v59CompactNutrition(recipe.nutrition)||undefined,
      match:{
        score:Number(match.score||0),
        pantryCoverage:Number(match.pantryCoverage||0),
        safe:match.safe!==false,
        caloriePerServing:match.caloriePerServing??undefined,
        calorieTarget:match.calorieTarget??undefined,
      },
      source:"cook4me_shell_summary",
      releaseCatalog:Boolean(recipe.releaseCatalog),
    };
  }

  _persistUiSnapshot(){
    if(!this._v54CacheUser)return;
    const entries=(this._entries||[]).map(row=>this._v59CompactEntry(row)).filter(Boolean).slice(0,12);
    if(!entries.length)return;
    const cards=(this._todayResults||[]).slice(0,8).map(row=>this._v59CompactCard(row)).filter(Boolean);
    const meta=this._todayMeta?{
      date:this._todayMeta.date||"",
      filters:this._todayMeta.filters||null,
      catalogLanguagesUsed:this._todayMeta.catalogLanguagesUsed||[],
      offlineCatalog:Boolean(this._todayMeta.offlineCatalog),
      releaseCatalog:this._todayMeta.releaseCatalog||null,
    }:null;
    const shell={version:SHELL_VERSION,savedAt:Date.now(),selectedEntryId:this._entryId||entries[0].entry_id,tab:this._tab,entries,todayByEntry:{}};
    if(this._entryId&&(cards.length||meta))shell.todayByEntry[this._entryId]={cards,meta};
    try{
      let text=JSON.stringify(shell);
      if(text.length>SHELL_LIMIT){shell.todayByEntry={};text=JSON.stringify(shell);}
      localStorage.setItem(this._snapshotKey(),text);
    }catch(_e){}
  }

  _scheduleSnapshotPersist(){
    if(this._v59PersistHandle!==null)return;
    const run=()=>{this._v59PersistHandle=null;this._persistUiSnapshot();};
    if(typeof requestIdleCallback==="function")this._v59PersistHandle=requestIdleCallback(run,{timeout:1000});
    else this._v59PersistHandle=setTimeout(run,250);
  }

  _v59ScheduleLegacyCleanup(){
    if(this._v59LegacyCleanupScheduled)return;
    this._v59LegacyCleanupScheduled=true;
    const run=()=>{try{localStorage.removeItem(this._v59LegacySnapshotKey());}catch(_e){}};
    if(typeof requestIdleCallback==="function")requestIdleCallback(run,{timeout:2000});else setTimeout(run,500);
  }

  async _loadServerSeed(){
    const result=await super._loadServerSeed();
    queueMicrotask(()=>void this._v59LoadTodayState(false));
    return result;
  }

  async _v59LoadTodayState(rerender=true){
    const entryId=String(this._entryId||"");
    if(!entryId)return null;
    if(this._v59TodayStateEntry===entryId&&this._v59TodayStatePromise)return this._v59TodayStatePromise;
    this._v59TodayStateEntry=entryId;
    const task=(async()=>{
      try{
        const state=await this._api("cook4me/v30/today_state",{entry_id:entryId});
        if(Array.isArray(state?.items)&&state.items.length){
          this._todayResults=state.items;
          this._todayMeta=state;
          this._scheduleSnapshotPersist();
          if(rerender&&this._tab==="today")this._renderTab();
        }
        return state;
      }catch(_e){return null;}
    })();
    this._v59TodayStatePromise=task;
    return task;
  }

  _selectV52Tab(tab){
    const result=super._selectV52Tab(tab);
    if(String(tab)==="today")void this._v59LoadTodayState(true);
    return result;
  }

  _v59ProgressCapable(type){return PROGRESS_CAPABLE.has(type);}

  async _api(type,data={}){
    const mapped={
      "cook4me/v28/ui_seed":"cook4me/v30/ui_seed",
      "cook4me/v11/ingredient_catalog":"cook4me/v30/ingredient_catalog",
      "cook4me/v28/ingredient_catalog":"cook4me/v30/ingredient_catalog",
      "cook4me/v22/official_search":"cook4me/v30/official_search",
      "cook4me/recipe_detail":"cook4me/v30/recipe_detail",
      "cook4me/v24/recipe_detail":"cook4me/v30/recipe_detail",
      "cook4me/v20/recipe_cost":"cook4me/v30/recipe_cost",
      "cook4me/v23/recipe_cost":"cook4me/v30/recipe_cost",
      "cook4me/v18/today_suggest":"cook4me/v30/today_suggest",
      "cook4me/v29/today_suggest":"cook4me/v30/today_suggest",
    }[String(type)]||String(type);
    const payload={...(data||{})};
    if(this._v59ProgressCapable(mapped)&&this._process?.operationId&&!payload.client_operation_id)payload.client_operation_id=this._process.operationId;
    return super._api(mapped,payload);
  }

  _v59EnsureStyles(){
    if(this.shadowRoot?.getElementById("cook4meV59Styles"))return;
    const style=document.createElement("style");style.id="cook4meV59Styles";style.textContent=`
      .rx-v59-progress-stack{position:fixed;right:18px;bottom:18px;z-index:10020;width:min(390px,calc(100vw - 28px));display:flex;flex-direction:column;gap:9px;pointer-events:none}
      .rx-v59-progress-card{pointer-events:auto;background:var(--card-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:14px;padding:12px 13px;box-shadow:0 10px 34px rgba(0,0,0,.28)}
      .rx-v59-progress-title{font-weight:700;margin-bottom:4px}.rx-v59-progress-detail{font-size:13px;color:var(--secondary-text-color);min-height:18px}.rx-v59-progress-line{height:7px;border-radius:999px;overflow:hidden;background:var(--secondary-background-color);margin-top:9px}.rx-v59-progress-line>div{height:100%;background:var(--primary-color);width:32%;animation:rxV59Indeterminate 1.2s ease-in-out infinite alternate}.rx-v59-progress-line.determinate>div{animation:none;transform:none}.rx-v59-progress-meta{display:flex;justify-content:space-between;gap:8px;margin-top:5px;font-size:12px;color:var(--secondary-text-color)}
      .rx-v59-progress-card.error{border-color:var(--error-color,#db4437)}.rx-v59-progress-card.done{border-color:var(--success-color,#43a047)}
      .rx-v59-nutrition{margin:2px 0 4px;font-size:12px;color:var(--secondary-text-color);display:flex;gap:7px;flex-wrap:wrap}.rx-v59-nutrition strong{color:var(--primary-text-color)}
      .rx-v59-nutrition-detail{margin-top:14px;border-top:1px solid var(--divider-color);padding-top:12px}.rx-v59-nutrition-table{display:grid;grid-template-columns:minmax(125px,1fr) auto auto;gap:5px 10px;align-items:baseline}.rx-v59-nutrition-table>div{padding:3px 0}.rx-v59-official-row{padding:5px 0;border-bottom:1px solid color-mix(in srgb,var(--divider-color) 65%,transparent)}
      @keyframes rxV59Indeterminate{from{transform:translateX(-80%)}to{transform:translateX(260%)}}
    `;this.shadowRoot.appendChild(style);
  }

  _v59ProgressStack(){
    this._v59EnsureStyles();
    let stack=this.shadowRoot?.querySelector(".rx-v59-progress-stack");
    if(!stack&&this.shadowRoot){stack=document.createElement("div");stack.className="rx-v59-progress-stack";stack.setAttribute("aria-live","polite");stack.setAttribute("aria-atomic","false");this.shadowRoot.appendChild(stack);}
    return stack;
  }

  _processStart(title,detail=""){
    const token={cancelled:false,finished:false,operationId:`ui-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,9)}`,overlay:null,card:null};
    const stack=this._v59ProgressStack();
    if(stack){
      const card=document.createElement("div");card.className="rx-v59-progress-card";card.dataset.operationId=token.operationId;card.innerHTML=`<div class="rx-v59-progress-title">${this._escape(title||"Cook4Me")}</div><div class="rx-v59-progress-detail">${this._escape(detail||"")}</div><div class="rx-v59-progress-line"><div></div></div><div class="rx-v59-progress-meta"><span data-progress-count></span><span data-progress-percent></span></div>`;stack.appendChild(card);token.card=card;
    }
    this._v59Operations.set(token.operationId,token);
    this._process=token;
    return token;
  }

  _processUpdate(token,detail,done=null,total=null){
    if(!token||token.cancelled||token.finished||!token.card?.isConnected)return;
    const d=token.card.querySelector(".rx-v59-progress-detail");if(d)d.textContent=String(detail||"");
    const determinate=Number.isFinite(Number(done))&&Number.isFinite(Number(total))&&Number(total)>0;
    const line=token.card.querySelector(".rx-v59-progress-line"),bar=line?.querySelector("div"),count=token.card.querySelector("[data-progress-count]"),percent=token.card.querySelector("[data-progress-percent]");
    if(determinate){const p=Math.max(0,Math.min(100,Math.round(Number(done)/Number(total)*100)));line?.classList.add("determinate");if(bar)bar.style.width=`${p}%`;if(count)count.textContent=`${done} / ${total}`;if(percent)percent.textContent=`${p}%`;}
  }

  _v59FinishToken(token,{error="",delay=1500}={}){
    if(!token||token.finished)return;
    token.finished=true;
    const card=token.card;
    if(card?.isConnected){card.classList.add(error?"error":"done");const line=card.querySelector(".rx-v59-progress-line"),bar=line?.querySelector("div"),percent=card.querySelector("[data-progress-percent]");line?.classList.add("determinate");if(bar)bar.style.width="100%";if(!error&&percent&&!percent.textContent)percent.textContent="100%";setTimeout(()=>card.remove(),delay);}
    this._v59Operations.delete(token.operationId);
    if(this._process===token)this._process=null;
  }

  _processEnd(token){this._v59FinishToken(token);}

  _v59ApplyProgress(data){
    if(!data||!data.operationId)return;
    const operationId=String(data.operationId);
    let token=this._v59Operations.get(operationId);
    if(!token){
      token=this._processStart("Cook4Me",String(data.message||data.phase||""));
      this._v59Operations.delete(token.operationId);
      token.operationId=operationId;
      if(token.card)token.card.dataset.operationId=operationId;
      this._v59Operations.set(operationId,token);
    }
    if(data.message)this._processUpdate(token,String(data.message),data.completed,data.total);
    else this._processUpdate(token,String(data.phase||""),data.completed,data.total);
    if(data.error){const d=token.card?.querySelector(".rx-v59-progress-detail");if(d)d.textContent=String(data.error);this._v59FinishToken(token,{error:String(data.error),delay:3500});}
    else if(data.done)this._v59FinishToken(token,{delay:1800});
  }

  _v59EnsureProgressSubscription(){
    if(this._v59ProgressUnsub||this._v59ProgressSubLoading||!this._hass?.connection?.subscribeEvents)return;
    const loading=Promise.resolve(this._hass.connection.subscribeEvents(event=>this._v59ApplyProgress(event?.data||event),PROGRESS_EVENT)).then(unsub=>{this._v59ProgressUnsub=unsub;return unsub;}).catch(()=>null).finally(()=>{this._v59ProgressSubLoading=null;});
    this._v59ProgressSubLoading=loading;
  }

  _v59Number(value,digits=1){const n=Number(value);if(!Number.isFinite(n))return"";return n.toLocaleString(undefined,{maximumFractionDigits:digits});}
  _v59NutritionValues(recipe){const nutrition=recipe?.nutrition;if(!nutrition||typeof nutrition!=="object")return null;const values=nutrition.perServing&&Object.keys(nutrition.perServing).length?nutrition.perServing:nutrition.totals;return values&&Object.keys(values).length?{nutrition,values}:null;}

  _v59NutritionLine(recipe){
    const found=this._v59NutritionValues(recipe);if(!found)return"";const {nutrition,values}=found;const parts=[];
    if(Number.isFinite(Number(values.energyKcal)))parts.push(`🔥 <strong>${this._v59Number(values.energyKcal,0)} kcal</strong>`);
    if(Number.isFinite(Number(values.protein)))parts.push(`P ${this._v59Number(values.protein)}g`);
    if(Number.isFinite(Number(values.carbohydrates)))parts.push(`C ${this._v59Number(values.carbohydrates)}g`);
    if(Number.isFinite(Number(values.fat)))parts.push(`F ${this._v59Number(values.fat)}g`);
    if(Number.isFinite(Number(values.fiber)))parts.push(`🌾 ${this._v59Number(values.fiber)}g`);
    const coverage=Number(nutrition.coverage);if(Number.isFinite(coverage))parts.push(`${this._escape(this._t("nutritionCoverage"))} ${Math.round(coverage*100)}%${nutrition.estimated?` · ${this._escape(this._t("estimatedNutrition"))}`:""}`);
    return parts.length?`<div class="rx-v59-nutrition">${parts.map(part=>`<span>${part}</span>`).join("")}</div>`:"";
  }

  _recipeCard(recipe,custom=false){
    let html=super._recipeCard(recipe,custom);const line=this._v59NutritionLine(recipe);if(!line)return html;const marker='<div class="actions">';const pos=html.lastIndexOf(marker);return pos>=0?`${html.slice(0,pos)}${line}${html.slice(pos)}`:`${html}${line}`;
  }

  _v59NutrientLabel(key){return {energyKcal:"Energy kcal",energyKJ:"Energy kJ",protein:"Protein",carbohydrates:"Carbohydrates",sugars:"Sugars",fat:"Fat",saturatedFat:"Saturated fat",fiber:"Fiber",salt:"Salt",sodium:"Sodium"}[key]||key;}
  _v59NutrientUnit(key){return key==="energyKcal"?"kcal":key==="energyKJ"?"kJ":"g";}

  _v59CalculatedDetail(recipe){
    const nutrition=recipe?.nutrition;if(!nutrition||typeof nutrition!=="object")return"";const totals=nutrition.totals||{},per=nutrition.perServing||{};const keys=["energyKcal","energyKJ","protein","carbohydrates","sugars","fat","saturatedFat","fiber","salt","sodium"].filter(key=>Number.isFinite(Number(totals[key]))||Number.isFinite(Number(per[key])));if(!keys.length)return"";
    const rows=keys.map(key=>`<div>${this._escape(this._v59NutrientLabel(key))}</div><div>${Number.isFinite(Number(per[key]))?`${this._v59Number(per[key],2)} ${this._v59NutrientUnit(key)}`:"—"}</div><div>${Number.isFinite(Number(totals[key]))?`${this._v59Number(totals[key],2)} ${this._v59NutrientUnit(key)}`:"—"}</div>`).join("");
    const coverage=Number(nutrition.coverage);return `<section class="rx-v59-nutrition-detail"><h3>${this._escape(this._t("calculatedNutrition"))}</h3><div class="muted">${Number.isFinite(coverage)?`${this._escape(this._t("nutritionCoverage"))}: ${Math.round(coverage*100)}%`:""}${nutrition.estimated?` · ${this._escape(this._t("estimatedNutrition"))}`:""}</div><div class="rx-v59-nutrition-table" style="margin-top:8px"><div></div><strong>${this._escape(this._t("perServing"))}</strong><strong>${this._escape(this._t("wholeRecipe"))}</strong>${rows}</div></section>`;
  }

  _v59OfficialDetail(recipe){
    const official=recipe?.officialNutrition;if(!official||typeof official!=="object")return"";const rows=[];
    if(Number.isFinite(Number(official.energyPer100gValue)))rows.push(`<div class="rx-v59-official-row"><strong>Energy</strong>: ${this._escape(this._v59Number(official.energyPer100gValue,2))} · ${this._escape(this._t("per100g"))}</div>`);
    for(const nutrient of official.hierarchicalNutrients||[]){if(!nutrient||!Number.isFinite(Number(nutrient.valuePer100g)))continue;const unit=nutrient.unit?.abbreviation||nutrient.unit?.symbol||nutrient.unit?.name||"";const name=nutrient.name||(nutrient.path||[]).join(" › ")||"Nutrient";rows.push(`<div class="rx-v59-official-row"><strong>${this._escape(name)}</strong>: ${this._escape(this._v59Number(nutrient.valuePer100g,3))}${unit?` ${this._escape(unit)}`:""} · ${this._escape(this._t("per100g"))}</div>`);}
    for(const nutrient of official.nutrients||[]){if(!nutrient||!Number.isFinite(Number(nutrient.quantity)))continue;const unit=nutrient.unit?.abbreviation||nutrient.unit?.symbol||nutrient.unit?.name||"";rows.push(`<div class="rx-v59-official-row"><strong>${this._escape(nutrient.name||nutrient.key||"Nutrient")}</strong>: ${this._escape(this._v59Number(nutrient.quantity,3))}${unit?` ${this._escape(unit)}`:""} · <span class="warn">${this._escape(this._t("basisUnknown"))}</span></div>`);}
    const meta=[];if(official.nutritionalScore!==undefined)meta.push(`${this._t("nutritionalScore")}: ${official.nutritionalScore}`);if(official.ecologicalScore)meta.push(`${this._t("ecologicalScore")}: ${official.ecologicalScore}`);if(Number.isFinite(Number(official.partWeight)))meta.push(`${this._t("partWeight")}: ${this._v59Number(official.partWeight,2)} g`);if(official.nutritionalIndicator?.name)meta.push(String(official.nutritionalIndicator.name));
    if(!rows.length&&!meta.length)return"";return `<section class="rx-v59-nutrition-detail"><h3>${this._escape(this._t("officialNutrition"))}</h3>${meta.length?`<div class="chips">${meta.map(value=>`<span class="chip">${this._escape(value)}</span>`).join("")}</div>`:""}<div style="margin-top:8px">${rows.join("")}</div></section>`;
  }

  _detailHtml(recipe){
    let html=super._detailHtml(recipe);if(!html||!recipe)return html;const nutrition=`${this._v59CalculatedDetail(recipe)}${this._v59OfficialDetail(recipe)}`;if(!nutrition)return html;const pos=html.lastIndexOf("</section>");return pos>=0?`${html.slice(0,pos)}${nutrition}${html.slice(pos)}`:`${html}${nutrition}`;
  }
}

customElements.define("cook4me-recipe-hub-panel-v59",Cook4MeRecipeHubPanelV59);
