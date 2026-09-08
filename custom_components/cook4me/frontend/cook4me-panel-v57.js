import "./cook4me-panel-v56.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v56");

const TEXT={
  en:{serverSeed:"saved Cook4Me data"},
  de:{serverSeed:"gespeicherte Cook4Me-Daten"},
  el:{serverSeed:"αποθηκευμένων δεδομένων Cook4Me"},
};

function copy(value){
  if(value===undefined)return undefined;
  try{return typeof structuredClone==="function"?structuredClone(value):JSON.parse(JSON.stringify(value));}
  catch(_e){return value;}
}

class Cook4MeRecipeHubPanelV57 extends BasePanel{
  constructor(){
    super();
    this._v57ServerSeedDone=false;
    this._v57ServerSeedLoading=null;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _loadLabel(type){
    const value=String(type||"");
    if(value==="cook4me/v28/ui_seed")return this._t("serverSeed");
    return super._loadLabel(type);
  }

  async _api(type,data={}){
    const mapped=String(type)==="cook4me/v11/ingredient_catalog"
      ?"cook4me/v28/ingredient_catalog"
      :type;
    return super._api(mapped,data);
  }

  // Absolute safety contract: the active panel may never show the historical
  // whole-section Load wall. If an inherited path somehow reaches it, mark the
  // section ready and immediately render the real tab instead.
  _renderDeferredSection(_preparing=false){
    const tab=String(this._tab||"official");
    this._v51OverviewDone=true;
    this._v51ActivatedSections.add(tab);
    this._v51PreparedSections.add(tab);
    const c=this.shadowRoot?.getElementById("content");
    c?.querySelector("#cook4meLoadSection")?.closest("section")?.remove();
    queueMicrotask(()=>this._renderTab());
  }

  _applyServerSeed(result){
    const entries=Array.isArray(result?.entries)?copy(result.entries):[];
    const perEntry=result?.perEntry&&typeof result.perEntry==="object"?copy(result.perEntry):{};
    if(!entries.length)return false;

    const existing=String(this._entryId||"");
    const selected=entries.some(row=>String(row?.entry_id||"")===existing)
      ?existing
      :String(result?.selectedEntryId||entries[0]?.entry_id||"");

    this._entries=entries;
    this._entryId=selected||null;
    this._v54Cache={
      version:1,
      savedAt:Date.now(),
      selectedEntryId:selected,
      entries:copy(entries),
      perEntry,
      fullOverviewCached:Boolean(result?.fullOverviewCached),
    };
    this._v54HadUiCache=true;
    this._v54HasCachedFullOverview=Boolean(result?.fullOverviewCached);
    this._v53FullOverviewDone=Boolean(result?.fullOverviewCached);
    this._v53BootstrapDone=true;
    this._v51OverviewStarted=true;
    this._v51OverviewDone=true;
    if(this._entryId)this._applyEntrySnapshot(this._entryId);
    this._renderEntrySelect();
    this._updateHeader();
    this._renderTabs();
    this._renderTab();
    this._scheduleSnapshotPersist();
    return true;
  }

  async _loadServerSeed(){
    if(this._v57ServerSeedDone)return true;
    if(this._v57ServerSeedLoading)return this._v57ServerSeedLoading;
    const task=(async()=>{
      try{
        const result=await this._api("cook4me/v28/ui_seed");
        const applied=this._applyServerSeed(result);
        this._v57ServerSeedDone=applied;
        return applied;
      }catch(_e){
        return false;
      }finally{
        this._v57ServerSeedLoading=null;
      }
    })();
    this._v57ServerSeedLoading=task;
    return task;
  }

  async _loadBootstrap(silent=false,rerender=true,force=false){
    // A completely new browser has no localStorage UI snapshot. Seed it from
    // HA's already-persisted local Cook4Me data first. The seed already carries
    // current in-memory device status, so a second bootstrap request is needless.
    if(!force&&!this._v54HadUiCache&&!this._v57ServerSeedDone){
      const seeded=await this._loadServerSeed();
      if(seeded){
        if(!this._v54InitialVisibleRequested&&this._entryId){
          this._v54InitialVisibleRequested=true;
          queueMicrotask(()=>void this._requestSection(String(this._tab||"official"),{missingOnly:true,force:false}));
        }
        return;
      }
    }
    return super._loadBootstrap(silent,rerender,force);
  }
}

customElements.define("cook4me-recipe-hub-panel-v57",Cook4MeRecipeHubPanelV57);
