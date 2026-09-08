import "./cook4me-panel-v52.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v52");
const FULL_OVERVIEW_SECTIONS=new Set(["today","recommend","mine","profile","shopping","ai","week"]);

const TEXT={
  en:{loadBootstrap:"Cook4Me device status",loadFullOverview:"profile, saved recipes and history"},
  de:{loadBootstrap:"Cook4Me-Gerätestatus",loadFullOverview:"Profil, gespeicherte Rezepte und Verlauf"},
  el:{loadBootstrap:"κατάστασης συσκευών Cook4Me",loadFullOverview:"προφίλ, αποθηκευμένων συνταγών και ιστορικού"},
};

class Cook4MeRecipeHubPanelV53 extends BasePanel{
  constructor(){
    super();
    this._v53BootstrapDone=false;
    this._v53FullOverviewDone=false;
    this._v53FullOverviewLoading=false;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _loadLabel(type){
    const value=String(type||"");
    if(value==="cook4me/v27/bootstrap")return this._t("loadBootstrap");
    if(value==="cook4me/overview")return this._t("loadFullOverview");
    return super._loadLabel(type);
  }

  async _loadOverview(silent=false,rerender=true){
    if(this._resourceAllowed("fullOverview")){
      return this._loadFullOverview(silent,rerender,true);
    }
    return this._loadBootstrap(silent,rerender);
  }

  async _loadBootstrap(silent=false,rerender=true){
    if(this._overviewLoading||this._v53BootstrapDone)return;
    this._v51OverviewStarted=true;
    this._overviewLoading=true;
    try{
      const res=await this._api("cook4me/v27/bootstrap");
      this._entries=Array.isArray(res?.entries)?res.entries:[];
      if(!this._entryId||!this._entries.some(entry=>entry.entry_id===this._entryId))this._entryId=this._entries[0]?.entry_id||null;
      this._lastOverviewRefresh=Date.now();
      this._v53BootstrapDone=true;
      this._v51OverviewDone=true;
      this._renderEntrySelect();
      this._updateHeader();
      if(rerender)this._renderTab();
      if(!silent)this._message("");
    }catch(e){
      this._v53BootstrapDone=true;
      this._v51OverviewDone=true;
      if(!silent)this._message(`${this._t("error")}: ${e.message||e}`,true);
      if(rerender)this._renderTab();
    }finally{
      this._overviewLoading=false;
    }
  }

  async _loadFullOverview(silent=true,rerender=false,force=false){
    if(this._v53FullOverviewLoading)return;
    if(this._v53FullOverviewDone&&!force)return;
    this._v53FullOverviewLoading=true;
    try{
      const res=await this._api("cook4me/overview");
      const entries=Array.isArray(res?.entries)?res.entries:[];
      this._entries=entries;
      if(!this._entryId||!entries.some(entry=>entry.entry_id===this._entryId))this._entryId=entries[0]?.entry_id||null;
      this._v53FullOverviewDone=true;
      this._lastOverviewRefresh=Date.now();
      this._renderEntrySelect();
      this._updateHeader();
      if(rerender)this._renderTab();
      if(!silent)this._message("");
    }catch(e){
      if(!silent)this._message(`${this._t("error")}: ${e.message||e}`,true);
      throw e;
    }finally{
      this._v53FullOverviewLoading=false;
    }
  }

  _renderEntrySelect(){
    const before=String(this._entryId||"");
    super._renderEntrySelect();
    const select=this.shadowRoot?.getElementById("entrySelect");
    if(!select||select.dataset.cook4meV53EntryBound==="1")return;
    select.dataset.cook4meV53EntryBound="1";
    select.addEventListener("change",()=>{
      const now=String(select.value||this._entryId||"");
      if(now===before)return;
      this._v53FullOverviewDone=false;
    },true);
  }

  async _prepareSection(tab){
    const value=String(tab||"");
    if(FULL_OVERVIEW_SECTIONS.has(value)){
      this._allowResource("fullOverview");
      await this._loadFullOverview(true,false,false);
    }
    return super._prepareSection(tab);
  }
}

customElements.define("cook4me-recipe-hub-panel-v53",Cook4MeRecipeHubPanelV53);
