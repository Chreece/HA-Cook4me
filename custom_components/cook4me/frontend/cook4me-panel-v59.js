import "./cook4me-panel-v58.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v58");
const SHELL_VERSION=2;
const VALID_TABS=new Set(["today","week","book","official","recommend","mine","profile","ai","shopping"]);

const TEXT={
  en:{
    energyKJ:"Energy",sodium:"Sodium",officialEnergy:"SEB energy value",officialUnspecified:"SEB values with unspecified basis",basisUnspecified:"Basis not specified by SEB",partWeight:"Part weight",nutritionScore:"Nutrition score",ecoScore:"Ecological score",nutritionIndicator:"Nutrition indicator",mealCost:"Meal cost",costCoverage:"Cost coverage",exactCostCoverage:"Exact purchase coverage",estimated:"estimated",progressWaiting:"Waiting for earlier Cook4Me work",referenceCatalog:"Bundled catalog"
  },
  de:{
    energyKJ:"Energie",sodium:"Natrium",officialEnergy:"SEB-Energiewert",officialUnspecified:"SEB-Werte mit nicht angegebener Bezugsbasis",basisUnspecified:"Bezugsbasis von SEB nicht angegeben",partWeight:"Portionsgewicht",nutritionScore:"Nährwert-Score",ecoScore:"Ökologischer Score",nutritionIndicator:"Nährwertindikator",mealCost:"Gerichtskosten",costCoverage:"Kostenabdeckung",exactCostCoverage:"Abdeckung exakter Kaufpreise",estimated:"geschätzt",progressWaiting:"Wartet auf vorherige Cook4Me-Arbeit",referenceCatalog:"Mitgelieferter Katalog"
  },
  el:{
    energyKJ:"Ενέργεια",sodium:"Νάτριο",officialEnergy:"Τιμή ενέργειας SEB",officialUnspecified:"Τιμές SEB χωρίς καθορισμένη βάση",basisUnspecified:"Η βάση δεν προσδιορίζεται από τη SEB",partWeight:"Βάρος μερίδας",nutritionScore:"Διατροφική βαθμολογία",ecoScore:"Οικολογική βαθμολογία",nutritionIndicator:"Διατροφικός δείκτης",mealCost:"Κόστος γεύματος",costCoverage:"Κάλυψη κόστους",exactCostCoverage:"Κάλυψη ακριβούς τιμής αγοράς",estimated:"εκτίμηση",progressWaiting:"Αναμονή για προηγούμενη εργασία Cook4Me",referenceCatalog:"Ενσωματωμένος κατάλογος"
  },
};

function clone(value){
  if(value===undefined)return undefined;
  try{return typeof structuredClone==="function"?structuredClone(value):JSON.parse(JSON.stringify(value));}
  catch(_e){return value;}
}

function compactNutrition(value){
  if(!value||typeof value!=="object")return null;
  return {
    totals:clone(value.totals||{}),perServing:clone(value.perServing||{}),servings:value.servings,
    coverage:value.coverage,fullyCovered:value.fullyCovered,estimated:value.estimated,sourceKinds:clone(value.sourceKinds||[]),
  };
}

function compactCost(value){
  if(!value||typeof value!=="object")return null;
  return {
    totalsByCurrency:clone(value.totalsByCurrency||{}),perServingByCurrency:clone(value.perServingByCurrency||{}),servings:value.servings,
    coverage:value.coverage,exactPurchaseCoverage:value.exactPurchaseCoverage,estimated:value.estimated,priceRevision:value.priceRevision,
  };
}

function compactRecipe(recipe){
  if(!recipe||typeof recipe!=="object")return null;
  const out={};
  for(const key of ["id","groupingFunctionalId","recipeFunctionalId","variantFunctionalId","searchVariantId","sendVariantId","sendGroupingFunctionalId","sendRecipeFunctionalId","referenceRecipeId","title","cover","language","market","todayCatalogLanguage","officialCatalogLanguage","source","sendable","deviceCanAccept","groupSize","yield"]){
    if(recipe[key]!==undefined&&recipe[key]!==null&&recipe[key]!=="")out[key]=clone(recipe[key]);
  }
  if(Array.isArray(recipe.ingredients))out.ingredients=recipe.ingredients.slice(0,8).map(row=>{
    if(!row||typeof row!=="object")return row;
    const item={};for(const key of ["foodKey","key","foodName","name","quantity","unit"])if(row[key]!==undefined&&row[key]!==null&&row[key]!=="")item[key]=row[key];return item;
  });
  if(recipe.match&&typeof recipe.match==="object"){
    out.match={};for(const key of ["score","pantryCoverage","safe","dietary","missingIngredients","calorieTarget","caloriePerServing","calorieDelta","nutritionGoal","nutritionGoalCoverage"]){
      if(recipe.match[key]!==undefined)out.match[key]=clone(key==="missingIngredients"&&Array.isArray(recipe.match[key])?recipe.match[key].slice(0,8):recipe.match[key]);
    }
  }
  const n=compactNutrition(recipe.nutrition);if(n)out.nutrition=n;
  const c=compactCost(recipe.cost);if(c)out.cost=c;
  return out;
}

class Cook4MeRecipeHubPanelV59 extends BasePanel{
  constructor(){
    super();
    this._v59ReferenceCatalog=null;
    this._v59PersistHandle=null;
    this._v59ProgressTimers=new Map();
    this._v59SeedApplied=false;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _snapshotKey(user=this._v54CacheUser||String(this._hass?.user?.id||"anonymous")){
    return `cook4me.ui.shell.v59.${String(user||"anonymous")}`;
  }

  _hydrateUiSnapshot(user){
    this._v54CacheUser=String(user||"anonymous");this._v54CacheHydrated=true;
    let cached=null;
    try{cached=JSON.parse(globalThis.localStorage?.getItem(this._snapshotKey(this._v54CacheUser))||"null");}catch(_e){}
    if(!cached||cached.version!==SHELL_VERSION||typeof cached!=="object"){
      this._v54Cache={version:SHELL_VERSION,savedAt:0,selectedEntryId:"",entries:[],perEntry:{},fullOverviewCached:false};
      this._v54HadUiCache=false;this._v54HasCachedFullOverview=false;this._v53FullOverviewDone=false;return;
    }
    this._v54Cache=cached;
    this._entries=Array.isArray(cached.entries)?cached.entries:[];
    const wanted=String(cached.selectedEntryId||"");
    this._entryId=this._entries.some(row=>String(row?.entry_id||"")===wanted)?wanted:String(this._entries[0]?.entry_id||"")||null;
    this._v54HadUiCache=this._entries.length>0;
    this._v54HasCachedFullOverview=false;this._v53FullOverviewDone=false;
    if(VALID_TABS.has(String(cached.lastTab||"")))this._tab=String(cached.lastTab);
    if(cached.referenceCatalog&&typeof cached.referenceCatalog==="object")this._v59ReferenceCatalog=cached.referenceCatalog;
    if(this._entryId)this._applyEntrySnapshot(this._entryId);
  }

  _applyTodayPlan(plan){
    if(!plan||typeof plan!=="object")return;
    if(Array.isArray(plan.items))this._todayResults=plan.items;
    if(plan.meta&&typeof plan.meta==="object")this._todayMeta={...plan.meta,date:plan.date||plan.meta.date};
    const filters=plan.filters&&typeof plan.filters==="object"?plan.filters:null;
    if(filters){
      const current=this._todaySettings||this._loadTodaySettings?.()||{};
      this._todaySettings={...current,...filters,
        mealTypes:Array.isArray(filters.mealTypes)?filters.mealTypes:current.mealTypes,
        languages:Array.isArray(filters.languages)?filters.languages:current.languages,
        calorieTolerance:filters.calorieTolerancePercent??filters.calorieTolerance??current.calorieTolerance,
        maxMissing:filters.maxMissing??current.maxMissing,
        avoidRecentDays:filters.avoidRecentDays??current.avoidRecentDays,
      };
    }
  }

  _applyEntrySnapshot(entryId){
    super._applyEntrySnapshot(entryId);
    const row=this._entrySnapshot(entryId);if(!row)return;
    if(row.todayPlan)this._applyTodayPlan(row.todayPlan);
    if(row.referenceCatalog&&typeof row.referenceCatalog==="object")this._v59ReferenceCatalog=row.referenceCatalog;
    const last=String(row.uiPreferences?.lastTab||"");
    if(!this._v54HadUiCache&&VALID_TABS.has(last))this._tab=last;
  }

  _captureEntrySnapshot(entryId=this._entryId){
    const id=String(entryId||"");if(!id)return;
    const plan=(this._todayResults?.length||this._todayMeta)?{
      date:String(this._todayMeta?.date||""),savedAt:new Date().toISOString(),items:(this._todayResults||[]).slice(0,8).map(compactRecipe).filter(Boolean),
      filters:clone(this._todaySettings||{}),meta:clone(this._todayMeta||{}),compact:true,
    }:this._entrySnapshot(id)?.todayPlan||null;
    this._v54Cache.perEntry={...(this._v54Cache.perEntry||{}),[id]:{
      uiPreferences:clone(this._uiPreferences||{}),todayOptions:clone(this._todayOptions),todayPlan:plan,referenceCatalog:clone(this._v59ReferenceCatalog),savedAt:Date.now(),
    }};
  }

  _compactEntries(){
    return (this._entries||[]).map(row=>({
      entry_id:row?.entry_id,title:row?.title,connected:Boolean(row?.connected),canAcceptRecipe:Boolean(row?.canAcceptRecipe),
      loadedRecipe:clone(row?.loadedRecipe),state:clone(row?.state||{}),
      profile:row?.profile?{diet:row.profile.diet,allergies:clone(row.profile.allergies||[]),avoid:clone(row.profile.avoid||[]),preferences:clone(row.profile.preferences||[])}:undefined,
    }));
  }

  _persistUiSnapshot(){
    if(!this._v54CacheUser)return;
    this._captureEntrySnapshot();
    const payload={version:SHELL_VERSION,savedAt:Date.now(),selectedEntryId:String(this._entryId||""),lastTab:String(this._tab||"official"),entries:this._compactEntries(),perEntry:clone(this._v54Cache.perEntry||{}),referenceCatalog:clone(this._v59ReferenceCatalog),fullOverviewCached:false};
    try{globalThis.localStorage?.setItem(this._snapshotKey(),JSON.stringify(payload));this._v54Cache=payload;}catch(_e){}
  }

  _scheduleSnapshotPersist(){
    if(this._v59PersistHandle!==null)return;
    const run=()=>{this._v59PersistHandle=null;this._persistUiSnapshot();};
    if(typeof globalThis.requestIdleCallback==="function")this._v59PersistHandle=globalThis.requestIdleCallback(run,{timeout:1800});
    else this._v59PersistHandle=setTimeout(run,700);
  }

  _resetUserScopedUiState(){
    if(this._v59PersistHandle!==null){
      try{if(typeof globalThis.cancelIdleCallback==="function")globalThis.cancelIdleCallback(this._v59PersistHandle);else clearTimeout(this._v59PersistHandle);}catch(_e){}
      this._v59PersistHandle=null;
    }
    this._v59ReferenceCatalog=null;this._v59SeedApplied=false;
    super._resetUserScopedUiState();
  }

  _applyServerSeed(result){
    const applied=super._applyServerSeed(result);
    if(!applied)return false;
    this._v59ReferenceCatalog=result?.referenceCatalog||this._entrySnapshot(this._entryId)?.referenceCatalog||this._v59ReferenceCatalog;
    const row=this._entrySnapshot(this._entryId);if(row?.todayPlan)this._applyTodayPlan(row.todayPlan);
    this._v54HasCachedFullOverview=false;this._v53FullOverviewDone=false;this._v59SeedApplied=true;
    this._renderTabs();this._renderTab();this._scheduleSnapshotPersist();
    return true;
  }

  async _loadBootstrap(silent=false,rerender=true,force=false){
    if(this._overviewLoading)return;
    if(!force&&!this._v54HadUiCache&&!this._v57ServerSeedDone){
      await this._loadServerSeed();return;
    }
    if(!force&&this._v53BootstrapDone)return;
    this._overviewLoading=true;this._v51OverviewStarted=true;
    try{
      const res=await this._api("cook4me/v27/bootstrap");
      const live=Array.isArray(res?.entries)?res.entries:[];const old=new Map((this._entries||[]).map(row=>[String(row?.entry_id||""),row]));
      this._entries=live.map(row=>{const prior=old.get(String(row?.entry_id||""));return prior?{...prior,...row,state:{...(prior.state||{}),...(row.state||{})}}:{...row};});
      if(!this._entryId||!this._entries.some(row=>row.entry_id===this._entryId))this._entryId=this._entries[0]?.entry_id||null;
      this._v53BootstrapDone=true;this._v51OverviewDone=true;this._lastOverviewRefresh=Date.now();
      this._renderEntrySelect();this._updateHeader();if(rerender)this._renderTab();if(!silent)this._message("");
    }catch(e){this._v53BootstrapDone=true;this._v51OverviewDone=true;if(!silent)this._message(`${this._t("error")}: ${e.message||e}`,true);}
    finally{this._overviewLoading=false;this._scheduleSnapshotPersist();}
  }

  _resourceHasData(resource){
    if(resource==="fullOverview")return Boolean(this._v53FullOverviewDone||this._v54HasCachedFullOverview);
    if(resource==="catalog"&&Number(this._v59ReferenceCatalog?.ingredientCount||0)>0)return Boolean(this._ingredientCatalog?.length);
    return super._resourceHasData(resource);
  }

  async _api(type,data={}){
    const original=String(type||"");let mapped=original;const payload={...(data||{})};
    if(original==="cook4me/v28/ui_seed")mapped="cook4me/v30/ui_seed";
    else if(["cook4me/v18/today_suggest","cook4me/v29/today_suggest"].includes(original)){mapped="cook4me/v33/today_suggest";payload.ui_language=this._langCode();}
    else if(["cook4me/recipe_detail","cook4me/v7/recipe_detail","cook4me/v9/recipe_detail","cook4me/v24/recipe_detail"].includes(original))mapped="cook4me/v31/recipe_detail";
    else if(["cook4me/v22/send_multi","cook4me/v25/send_multi"].includes(original))mapped="cook4me/v31/send_multi";
    else if(original==="cook4me/v22/official_search"){mapped="cook4me/v32/official_search";payload.ui_language=this._langCode();}
    else if(Number(this._v59ReferenceCatalog?.recipeCount||0)>0&&["cook4me/v7/search","cook4me/v8/search","cook4me/v9/search","cook4me/v10/search"].includes(original)){
      mapped="cook4me/v32/official_search";payload.languages=payload.languages||[String(payload.language||this._selectedLanguage?.()||"de")];payload.ui_language=this._langCode();delete payload.language;
    }else if(Number(this._v59ReferenceCatalog?.recipeCount||0)>0&&["cook4me/v7/recommend","cook4me/v8/recommend","cook4me/v9/recommend","cook4me/v10/recommend"].includes(original)){
      mapped="cook4me/v32/reference_recommend";payload.languages=payload.languages||[String(payload.language||this._selectedLanguage?.()||"de")];payload.language=this._langCode();payload.diet=payload.diet||"profile";
    }else if(Number(this._v59ReferenceCatalog?.ingredientCount||0)>0&&original==="cook4me/v11/ingredient_catalog"){
      mapped="cook4me/v30/reference_ingredients";payload.language=this._langCode();
    }
    return super._api(mapped,payload);
  }

  async _loadIngredientCatalog(language=null,refresh=false){
    if(Number(this._v59ReferenceCatalog?.ingredientCount||0)<=0)return super._loadIngredientCatalog(language,refresh);
    if(this._ingredientCatalogLoading||!this._entryId)return;
    this._ingredientCatalogLoading=true;
    const job=this._processStart(this._t("ingredientCatalog"),this._t("loadingCatalog"),{icon:"food-apple-outline",delay:160});
    try{
      const result=await this._api("cook4me/v30/reference_ingredients",{language:this._langCode(),limit:5000});
      this._ingredientCatalog=Array.isArray(result?.items)?result.items:[];this._ingredientCatalogLanguage=this._langCode();this._v59ReferenceCatalog=result?.referenceCatalog||this._v59ReferenceCatalog;
      this._dedupeIngredientCatalog?.();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    finally{this._ingredientCatalogLoading=false;this._processEnd(job);if(["profile","recommend","ai"].includes(this._tab))this._renderTab();this._scheduleSnapshotPersist();}
  }

  async _hydrateVisibleNutrition(_items){return;}

  async _loadRecipeNutrition(recipe,resolveMissing=true){
    const n=recipe?.nutrition;if(n&&((n.totals&&Object.keys(n.totals).length)||(n.perServing&&Object.keys(n.perServing).length)))return;
    return super._loadRecipeNutrition(recipe,resolveMissing);
  }

  _metric(value,key,unit="g"){
    if(key==="energyKJ")return super._metric(value,key,"kJ");
    return super._metric(value,key,unit);
  }

  _nutritionChips(values,_compact=false){
    if(!values||typeof values!=="object")return"";
    const rows=[
      ["energyKcal",this._t("calories"),"kcal","fire","orange"],["energyKJ",this._t("energyKJ"),"kJ","lightning-bolt-outline","amber"],
      ["protein",this._t("protein"),"g","arm-flex-outline","violet"],["carbohydrates",this._t("carbs"),"g","grain","blue"],
      ["sugars",this._t("sugars"),"g","cube-outline","amber"],["fat",this._t("fat"),"g","water-outline","pink"],
      ["saturatedFat",this._t("saturatedFat"),"g","heart-pulse","red"],["fiber",this._t("fiber"),"g","sprout","green"],
      ["salt",this._t("salt"),"g","shaker-outline","slate"],["sodium",this._t("sodium"),"g","chemical-weapon","slate"],
    ];
    return rows.filter(([key])=>Number.isFinite(Number(values[key]))).map(([key,label,unit,icon,tone])=>`<span class="chip rx-nutrition-chip tone-${tone}" data-nutrition-key="${key}"><ha-icon icon="mdi:${icon}"></ha-icon><span>${this._escape(label)}</span><strong>${this._escape(this._metric(values[key],key,unit))}</strong></span>`).join("");
  }

  _officialUnitLabel(unit){return super._officialUnitLabel(unit);}

  _officialNutritionBlock(recipe){
    const official=recipe?.officialNutrition;if(!official||typeof official!=="object")return"";
    const per100=[];
    if(Number.isFinite(Number(official.energyPer100gValue)))per100.push(`<span class="chip">${this._escape(this._t("officialEnergy"))}: ${this._escape(Number(official.energyPer100gValue))} / 100 g</span>`);
    for(const row of official.hierarchicalNutrients||[]){
      const value=Number(row?.valuePer100g),name=String(row?.name||row?.path?.at?.(-1)||"").trim();if(!Number.isFinite(value)||!name)continue;
      const unit=this._officialUnitLabel(row.unit);per100.push(`<span class="chip">${this._escape(name)}: ${this._escape(Number(value.toFixed(2)))}${unit?` ${this._escape(unit)}`:""} / 100 g</span>`);
    }
    const flat=[];
    for(const row of official.nutrients||[]){
      const value=Number(row?.quantity),name=String(row?.name||row?.key||"").trim();if(!Number.isFinite(value)||!name)continue;
      const unit=this._officialUnitLabel(row.unit);flat.push(`<span class="chip">${this._escape(name)}: ${this._escape(Number(value.toFixed(2)))}${unit?` ${this._escape(unit)}`:""}</span>`);
    }
    const meta=[];
    if(official.nutritionalScore!==undefined)meta.push(`${this._t("nutritionScore")}: ${official.nutritionalScore}`);
    if(official.ecologicalScore)meta.push(`${this._t("ecoScore")}: ${official.ecologicalScore}`);
    if(official.partWeight!==undefined)meta.push(`${this._t("partWeight")}: ${official.partWeight}`);
    if(official.nutritionalIndicator?.name||official.nutritionalIndicator?.key)meta.push(`${this._t("nutritionIndicator")}: ${official.nutritionalIndicator.name||official.nutritionalIndicator.key}`);
    if(!per100.length&&!flat.length&&!meta.length)return"";
    return `<section class="card" data-cook4me-official-nutrition style="margin:12px 0"><h3 style="margin-top:0">${this._escape(this._t("officialNutrition"))}</h3>${per100.length?`<div class="muted" style="margin-bottom:7px">${this._escape(this._t("officialPer100g"))}</div><div class="chips">${per100.join("")}</div>`:""}${flat.length?`<div class="muted" style="margin:10px 0 7px"><strong>${this._escape(this._t("officialUnspecified"))}</strong> · ${this._escape(this._t("basisUnspecified"))}</div><div class="chips">${flat.join("")}</div>`:""}${meta.length?`<div class="muted" style="margin-top:9px">${this._escape(meta.join(" · "))}</div>`:""}</section>`;
  }

  _costChips(cost,perServing=true){
    if(!cost||typeof cost!=="object")return"";const values=perServing&&Object.keys(cost.perServingByCurrency||{}).length?cost.perServingByCurrency:cost.totalsByCurrency;
    if(!values||!Object.keys(values).length)return"";
    const shown=typeof this._money==="function"?this._money(values):Object.entries(values).map(([currency,amount])=>`${Number(amount).toFixed(2)} ${currency}`).join(" · ");
    return shown?`<span class="chip" data-recipe-cost>💶 ${this._escape(shown)}${perServing&&Object.keys(cost.perServingByCurrency||{}).length?` · ${this._escape(this._t("perServingNutrition"))}`:""}</span>`:"";
  }

  _recipeCard(recipe,custom=false){
    let html=super._recipeCard(recipe,custom);const cost=this._costChips(recipe?.cost,true);if(cost)html=html.replace('<div class="chips">',`<div class="chips">${cost}`);return html;
  }

  _detailHtml(recipe){
    let html=super._detailHtml(recipe);if(!html||!recipe?.cost)return html;
    const cost=recipe.cost,coverage=Math.round(Number(cost.coverage||0)*100),exact=Math.round(Number(cost.exactPurchaseCoverage||0)*100);
    const totals=this._costChips({...cost,perServingByCurrency:{}},false),perServing=this._costChips(cost,true);
    if(!totals&&!perServing)return html;
    const block=`<section class="card" data-recipe-cost-detail style="margin:12px 0"><h3 style="margin-top:0">${this._escape(this._t("mealCost"))}</h3><div class="chips">${totals}${perServing}</div><div class="muted" style="margin-top:7px">${this._escape(this._t("costCoverage"))}: ${coverage}% · ${this._escape(this._t("exactCostCoverage"))}: ${exact}%${cost.estimated?` · ${this._escape(this._t("estimated"))}`:""}</div></section>`;
    const marker='<div class="detail-layout"',pos=html.indexOf(marker);return pos>=0?`${html.slice(0,pos)}${block}${html.slice(pos)}`:`${block}${html}`;
  }

  _processStart(title,detail="",options={}){
    const token=super._processStart(title,detail,{...options,onCancel:null});
    token.card?.querySelector(".rx-job-cancel")?.remove();
    this._v59StartProgressPolling(token);return token;
  }

  _v59StartProgressPolling(token){
    if(!token||this._v59ProgressTimers.has(token.id))return;
    const poll=async()=>{
      if(token.done||!token.card?.isConnected){this._v59StopProgressPolling(token);return;}
      try{
        const state=await this._hass?.connection?.sendMessagePromise?.({type:"cook4me/v30/progress_state"});
        const running=state?.running,progress=running?.progress;
        if(progress?.determinate&&Number.isFinite(Number(progress.completed))&&Number.isFinite(Number(progress.total))){
          this._processUpdate(token,progress.message||running?.title||"",Number(progress.completed),Number(progress.total));
        }else if(running){
          this._processUpdate(token,progress?.message||running.title||detail);
        }else if(Number(state?.waitingCount||0)>0){
          this._processUpdate(token,this._t("progressWaiting"));
        }
      }catch(_e){}
    };
    const id=setInterval(()=>void poll(),350);this._v59ProgressTimers.set(token.id,id);void poll();
  }

  _v59StopProgressPolling(token){const id=this._v59ProgressTimers.get(token?.id);if(id){clearInterval(id);this._v59ProgressTimers.delete(token.id);}}

  _processEnd(token){this._v59StopProgressPolling(token);return super._processEnd(token);}

  _message(text,err=false){
    const active=this._process&&!this._process.done&&this._process.card?.isConnected;
    if(active&&!err){if(text)this._processUpdate(this._process,String(text));const inline=this.shadowRoot?.getElementById("message");if(inline)inline.innerHTML="";return;}
    return super._message(text,err);
  }

  async _search(query){
    const job=this._processStart(this._t("backgroundWork"),this._t("searchingRecipes"),{icon:"magnify",delay:100});
    try{return await super._search(query);}finally{this._processEnd(job);}
  }

  disconnectedCallback(){
    for(const id of this._v59ProgressTimers.values())clearInterval(id);this._v59ProgressTimers.clear();
    if(this._v59PersistHandle!==null){try{if(typeof globalThis.cancelIdleCallback==="function")globalThis.cancelIdleCallback(this._v59PersistHandle);else clearTimeout(this._v59PersistHandle);}catch(_e){}this._v59PersistHandle=null;}
    super.disconnectedCallback?.();
  }
}

customElements.define("cook4me-recipe-hub-panel-v59",Cook4MeRecipeHubPanelV59);
