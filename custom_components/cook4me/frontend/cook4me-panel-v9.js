import "./cook4me-panel-v8.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v8");

class Cook4MeRecipeHubPanelV9 extends BasePanel {
  constructor(){
    super();
    this._searchDraft="";
  }

  async _api(type,data={}){
    const mapped={
      "cook4me/v8/capabilities":"cook4me/v9/capabilities",
      "cook4me/v8/preferences_set":"cook4me/v9/preferences_set",
      "cook4me/v8/search":"cook4me/v9/search",
      "cook4me/v8/recommend":"cook4me/v9/recommend",
      "cook4me/v7/recipe_detail":"cook4me/v9/recipe_detail",
    }[type]||type;
    return super._api(mapped,data);
  }

  async _loadCapabilities(){
    await super._loadCapabilities();
    const saved=this._uiPreferences?.searchDraft;
    if(saved!==undefined&&saved!==null)this._searchDraft=String(saved).slice(0,500);
    else if(!this._searchDraft)this._searchDraft=String(this._searchQuery||"");
    this._renderTab();
  }

  _captureSearchDraft(schedule=true){
    const input=this.shadowRoot?.getElementById("searchQ");
    if(!input)return;
    const value=String(input.value??"").slice(0,500);
    if(value===this._searchDraft)return;
    this._searchDraft=value;
    this._uiPreferences.searchDraft=value;
    if(schedule)this._schedulePreferenceSave();
  }

  _renderTab(){
    // Capture the actual text box before any language/translation/tab rerender
    // destroys it. This is intentionally independent from _searchQuery, which
    // represents only the last submitted search.
    this._captureSearchDraft(false);
    super._renderTab();
  }

  _renderOfficial(container){
    super._renderOfficial(container);
    const input=container.querySelector("#searchQ");
    if(!input)return;
    const value=this._searchDraft!==undefined&&this._searchDraft!==null
      ?String(this._searchDraft)
      :String(this._searchQuery||"");
    input.value=value;
    input.addEventListener("input",()=>{
      this._searchDraft=String(input.value??"").slice(0,500);
      this._uiPreferences.searchDraft=this._searchDraft;
      this._schedulePreferenceSave();
    });
  }

  async _search(query){
    const raw=String(query??"");
    const submitted=raw.trim();
    const live=this.shadowRoot?.getElementById("searchQ");
    const liveValue=live?String(live.value??"").slice(0,500):null;

    // Base locale/translation controls rerun the last submitted query so the
    // existing results can be rebuilt in the new mode. If the user has already
    // typed a different next query, preserve that draft rather than replacing
    // it with the old submitted query during the rerender.
    const automaticRerun=(
      liveValue!==null
      && submitted===String(this._searchQuery||"").trim()
      && liveValue.trim()!==submitted
    );
    if(automaticRerun){
      this._searchDraft=liveValue;
    }else{
      this._searchDraft=raw.slice(0,500);
    }
    this._uiPreferences.searchDraft=this._searchDraft;
    this._schedulePreferenceSave();

    await super._search(submitted);
  }
}

customElements.define("cook4me-recipe-hub-panel-v9",Cook4MeRecipeHubPanelV9);
