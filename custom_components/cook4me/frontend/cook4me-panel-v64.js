import "./cook4me-panel-v63.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v63");
const TEXT={
  en:{noFilteredRecipes:"No recipes match the selected filters. Adjust the filters and try again.",emptyMealCategories:"No matching recipe for",showingResults:"Displaying recipes"},
  el:{noFilteredRecipes:"Δεν βρέθηκαν συνταγές με τα επιλεγμένα φίλτρα. Προσαρμόστε τα φίλτρα και δοκιμάστε ξανά.",emptyMealCategories:"Δεν βρέθηκε κατάλληλη συνταγή για",showingResults:"Εμφάνιση συνταγών"},
  de:{noFilteredRecipes:"Keine Rezepte passen zu den ausgewählten Filtern. Passe die Filter an und versuche es erneut.",emptyMealCategories:"Kein passendes Rezept für",showingResults:"Rezepte werden angezeigt"},
};

class Cook4MeRecipeHubPanelV64 extends BasePanel{
  _t(key){return TEXT[this._uiIngredientLanguage()]?.[key]||TEXT.en[key]||super._t(key);}
  _refreshLoadStatus(){this.shadowRoot?.querySelector("#cook4meLoadStatus")?.replaceChildren();}
  _renderTab(){const result=super._renderTab();this.setAttribute("data-cook4me-build","2026.9.15.6");return result;}
  _renderToday(c){
    super._renderToday(c);
    if(!this._todayBusy&&this._todayMeta){
      const empty=this._todayMeta.emptyMealTypes||[];
      if(!this._todayResults?.length||empty.length){
        const note=document.createElement("p");note.className="muted";note.dataset.todayOutcome="";
        note.textContent=!this._todayResults?.length?this._t("noFilteredRecipes"):`${this._t("emptyMealCategories")}: ${empty.map(key=>this._t(key)).join(", ")}`;
        c.querySelector("#todayGrid").before(note);
      }
    }
  }
  _v59CompactTodayRecipe(recipe){
    const out=super._v59CompactTodayRecipe(recipe);
    if(out)for(const key of ["todayMealType","displayFamilyId","mealTypeSource"])if(recipe[key])out[key]=recipe[key];
    return out;
  }
  _v59CompactTodayMeta(meta){
    const out=super._v59CompactTodayMeta(meta);
    if(out)for(const key of ["emptyMealTypes","categoryCounts"])if(meta[key])out[key]=structuredClone(meta[key]);
    return out;
  }
  async _suggestTodayV34(c){
    if(this._todayBusy)return;
    const settings=structuredClone(this._collectTodayV34());
    if(!settings.mealTypes?.length){this._message(this._t("needMealType"),true);return;}
    if(!settings.languages?.length){this._message(this._t("needLanguage"),true);return;}
    const request={entry:this._entryId,user:this._hass?.user?.id};this._v64TodayRequest=request;
    const current=()=>this._v64TodayRequest===request&&this._entryId===request.entry&&this._hass?.user?.id===request.user;
    this._todaySettings=settings;this._saveTodaySettings();this._todayBusy=true;this._renderToday(c);
    const job=this._processStart(this._t("today"),this._t("buildingToday"));
    try{
      const result=await this._api("cook4me/v30/today_suggest",{entry_id:request.entry,languages:settings.languages,meal_types:settings.mealTypes,shared_filters:settings,group_by_meal_type:true,meal_count:settings.mealTypes.length});
      if(!current()||job.cancelled)return;
      if(!Array.isArray(result?.items))throw new Error(this._t("recipeUnavailable"));
      this._todayResults=result.items;this._todayResults.forEach(recipe=>this._ensureRecipeSelections(recipe));this._todayMeta=result;
      this._captureEntrySnapshot?.();
    }catch(error){this._v59FailProcess(job,`${this._t("error")}: ${error.message||error}`);}
    finally{
      if(this._v64TodayRequest===request)this._todayBusy=false;
      if(current())this._renderTab();
      this._processEnd(job);
    }
  }
  async _api(type,data={}){
    const created=!this._process,job=this._process||this._processStart(this._t("backgroundWork"),this._loadLabel(type)||this._t("loading"));
    const mapped=this._v59MapApi(type);
    if(mapped.startsWith("cook4me/v30/")||mapped==="cook4me/v31/official_search")data={...data,client_operation_id:data.client_operation_id||job.id};
    try{return await super._api(type,data);}
    catch(error){this._v59FailProcess(job,`${this._t("error")}: ${error.message||error}`);throw error;}
    finally{if(created)this._processEnd(job);}
  }
  _v59HandleProgress(event){
    const data=event?.data||event||{},token=this._v63Jobs?.get(String(data.operationId||""));if(!token)return;
    if(data.error){this._v59FailProcess(token,data.message||data.error);return;}
    // The request owner ends the card after receiving AND rendering its result.
    // Coordinator completion can arrive before the WebSocket response, and a
    // single UI action can own several server requests.
    if(data.done){this._processUpdate(token,this._t("showingResults"));return;}
    this._processUpdate(token,this._v59PhaseLabel(data.phase),data.completed,data.total);
  }
  _updateBackgroundStatus(){
    this.shadowRoot?.querySelectorAll("[data-v54-background]").forEach(node=>node.remove());
    const active=this._v54RefreshingSections?.size>0;
    if(active&&!this._process&&!this._v63RefreshJob)this._v63RefreshJob=this._processStart(this._t("backgroundWork"),this._t("cacheUpdating"));
    if(!active&&this._v63RefreshJob){this._processEnd(this._v63RefreshJob);this._v63RefreshJob=null;}
  }
}

customElements.define("cook4me-recipe-hub-panel-v64",Cook4MeRecipeHubPanelV64);
