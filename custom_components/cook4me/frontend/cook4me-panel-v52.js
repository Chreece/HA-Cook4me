import "./cook4me-panel-v51.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v51");

class Cook4MeRecipeHubPanelV52 extends BasePanel{
  get hass(){return this._hass;}

  set hass(value){
    const user=String(value?.user?.id||"anonymous");
    if(user!==this._restoredSectionUser){
      this._restoredSectionUser=user;
      const saved=this._loadLastSection?.(user);
      if(saved)this._tab=saved;
    }

    this._hass=value;

    // Strict runtime contract: Home Assistant assigns `hass` for every state
    // update. Those assignments are data propagation, not a reason to poll,
    // rebuild the header, run decorators, or touch the dashboard DOM. Only the
    // very first assignment may build the shell; loaded Cook4Me data is updated
    // by explicit Cook4Me requests/actions.
    if(!this.shadowRoot.innerHTML)this._renderShell();

    // The only automatic request allowed for a newly-mounted panel is overview.
    if(this.isConnected&&!this._v51OverviewStarted){
      queueMicrotask(()=>void this._loadOverview(false,true));
    }
  }

  _bindV51TabIntent(){
    // v52 binds directly to the buttons after the inherited tab renderer has
    // finished. Mark the parent as handled so v51 does not add a second
    // activation-only delegated listener.
    const tabs=this.shadowRoot?.getElementById("tabs");
    if(tabs)tabs.dataset.cook4meV51Intent="1";
  }

  _selectV52Tab(tab){
    const value=String(tab||"");
    if(!value)return;
    this._activateSection(value);
    this._tab=value;
    this._opened=null;
    this._rememberSection?.(value);
    this._renderTabs();
    this._renderTab();
  }

  _renderTabs(){
    super._renderTabs();
    const tabs=this.shadowRoot?.getElementById("tabs");
    if(!tabs)return;
    tabs.querySelectorAll("[data-tab]").forEach(button=>{
      if(button.dataset.cook4meV52Bound==="1")return;
      button.dataset.cook4meV52Bound="1";
      button.addEventListener("click",event=>{
        event.preventDefault();
        event.stopImmediatePropagation();
        this._selectV52Tab(button.dataset.tab);
      },true);
    });
  }

  async _prepareSection(tab){
    // Keep one section-level status token alive across every serialized
    // dependency. Individual API calls add their own detail tokens, but the
    // user must continuously see that the requested section is still loading
    // even during the tiny gaps between those calls.
    const token=this._beginLoad(this._sectionTitle(tab));
    try{
      return await super._prepareSection(tab);
    }finally{
      this._endLoad(token);
    }
  }
}

customElements.define("cook4me-recipe-hub-panel-v52",Cook4MeRecipeHubPanelV52);
