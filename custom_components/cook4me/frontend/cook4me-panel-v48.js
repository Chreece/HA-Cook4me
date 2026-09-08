import "./cook4me-panel-v47.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v47");

class Cook4MeRecipeHubPanelV48 extends BasePanel{
  _guardPulse(kind){
    // The safety circuit may disable optional DOM decoration, but it must never
    // block core rendering or user navigation. v47 gated _renderShell,
    // _renderTabs and _renderTab on the same tripped flag, which could leave a
    // visually live panel whose tabs no longer changed the content.
    if(kind==="render")return true;
    return super._guardPulse(kind);
  }

  _tripUiGuard(reason){
    if(this._cook4meUiGuardTripped)return;
    this._cook4meUiGuardTripped=true;
    this._cook4meUiGuardReason=String(reason||"ui-loop");
    this._modernObserver?.disconnect?.();
    this._modernObserver=null;
    this.dataset.cook4meUiGuard="tripped";
    this.dataset.cook4meUiGuardReason=this._cook4meUiGuardReason;
    console.error(`[Cook4Me] optional UI decoration disabled after ${this._cook4meUiGuardReason}`);
    const message=this.shadowRoot?.getElementById("message");
    if(message&&!message.querySelector("[data-cook4me-loop-guard]")){
      const notice=document.createElement("div");
      notice.className="notice error";
      notice.dataset.cook4meLoopGuard="1";
      notice.textContent="Cook4Me disabled optional UI decoration after abnormal DOM activity. Navigation and core controls remain available.";
      message.replaceChildren(notice);
    }
  }

  _compactTodayPlanner(c){
    const planner=c.querySelector(".rx-today-planner");
    if(!planner||planner.dataset.cook4meV36Compact)return super._compactTodayPlanner(c);

    // v36 located the Catalog languages section through the first language
    // checkbox. During the first Today render the async today_options request
    // may not have returned yet, so there is no checkbox even though the
    // language section itself exists. Give the compactor a temporary anchor so
    // the Catalog languages picker is always present from the first frame.
    let anchor=null;
    if(!planner.querySelector("[data-today-language]")){
      const bulk=planner.querySelector('[data-today-bulk="languages"]');
      const block=this._todayTopChild?.(planner,bulk);
      if(block){
        anchor=document.createElement("span");
        anchor.hidden=true;
        anchor.dataset.todayLanguage="";
        anchor.dataset.cook4meCatalogLanguageAnchor="1";
        block.appendChild(anchor);
      }
    }

    const result=super._compactTodayPlanner(c);
    anchor?.remove();

    const languagePicker=planner.querySelector('[data-rx-picker="languages"]');
    if(languagePicker&&!languagePicker.querySelector("[data-today-language]")){
      const body=languagePicker.querySelector(".rx-today-picker-body");
      if(body&&!body.querySelector("[data-cook4me-catalog-language-state]")){
        const state=document.createElement("div");
        state.className="muted";
        state.dataset.cook4meCatalogLanguageState="1";
        state.textContent=(!this._todayOptions||this._todayOptionsLoading)?this._t("loading"):this._t("noResults");
        body.appendChild(state);
      }
    }
    this._updateTodayPickerCounts?.(c);
    return result;
  }
}

customElements.define("cook4me-recipe-hub-panel-v48",Cook4MeRecipeHubPanelV48);
