import "./cook4me-panel-v55.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v55");

const TEXT={
  en:{loadingSaved:"Loading saved Cook4Me data…",loadingSectionData:"Loading this section’s missing data…"},
  de:{loadingSaved:"Gespeicherte Cook4Me-Daten werden geladen…",loadingSectionData:"Fehlende Daten dieses Bereichs werden geladen…"},
  el:{loadingSaved:"Φόρτωση αποθηκευμένων δεδομένων Cook4Me…",loadingSectionData:"Φόρτωση δεδομένων που λείπουν από αυτή την ενότητα…"},
};

class Cook4MeRecipeHubPanelV56 extends BasePanel{
  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  async _refreshSection(tab,options={}){
    // v54 marks the section as refreshing synchronously before its first await.
    // Decorate the already-painted tab immediately, without replacing it.
    const task=super._refreshSection(tab,options);
    this._decorateElementLoadingStates();
    return await task;
  }

  _inlineLoadingNode(label,key){
    const node=document.createElement("div");
    node.dataset.v54ElementLoading=String(key||"data");
    node.className="rx-v54-inline-loading";
    node.setAttribute("role","status");node.setAttribute("aria-live","polite");
    node.innerHTML=`<ha-icon icon="mdi:loading"></ha-icon><span>${this._escape(label)}</span>`;
    return node;
  }

  _decorateElementLoadingStates(){
    super._decorateElementLoadingStates();
    const c=this.shadowRoot?.getElementById("content");if(!c)return;
    const tab=String(this._tab||"");
    const refreshing=this._v54RefreshingSections.has(tab);
    if(!refreshing)return;

    const fullMissing=!this._resourceHasData("fullOverview");
    if(tab==="today"&&fullMissing){
      const planner=c.querySelector(".rx-today-planner")||c.querySelector("section.card");
      if(planner&&!planner.querySelector('[data-v54-element-loading="today-profile"]')){
        planner.prepend(this._inlineLoadingNode(this._t("loadingSaved"),"today-profile"));
      }
    }

    if(tab==="official"&&(!this._resourceHasData("capabilities")||!this._resourceHasData("book"))){
      const section=c.querySelector("section.card");
      if(section&&!section.querySelector('[data-v54-element-loading="official"]'))section.append(this._inlineLoadingNode(this._t("loadingSectionData"),"official"));
    }

    if(tab==="recommend"&&fullMissing){
      const section=c.querySelector("section.card");
      if(section&&!section.querySelector('[data-v54-element-loading="recommend"]'))section.prepend(this._inlineLoadingNode(this._t("loadingSaved"),"recommend"));
    }

    if(tab==="mine"&&fullMissing){
      const grid=c.querySelector("#mineGrid");
      if(grid){grid.replaceChildren(this._inlineLoadingNode(this._t("loadingSaved"),"mine"));}
    }

    if(tab==="profile"){
      if(fullMissing){
        const section=c.querySelector("section.card");
        if(section&&!section.querySelector('[data-v54-element-loading="profile"]'))section.prepend(this._inlineLoadingNode(this._t("loadingSaved"),"profile"));
        const save=c.querySelector("#profileSave");if(save)save.disabled=true;
      }
      if(!this._resourceHasData("inventory")){
        const rows=c.querySelector("#houseInventoryRows");
        if(rows&&!rows.querySelector('[data-v54-element-loading="inventory-missing"]'))rows.prepend(this._inlineLoadingNode(this._t("loadingInventory"),"inventory-missing"));
      }
    }

    if(tab==="shopping"&&!this._resourceHasData("shopping")){
      const section=c.querySelector("section.card");
      if(section&&!section.querySelector('[data-v54-element-loading="shopping-missing"]'))section.append(this._inlineLoadingNode(this._t("loadingShopping"),"shopping-missing"));
    }

    if(tab==="ai"&&(fullMissing||!this._resourceHasData("capabilities"))){
      const section=c.querySelector("section.card");
      if(section){
        const falseUnavailable=section.querySelector(".notice.error");
        falseUnavailable?.remove();
        if(!section.querySelector('[data-v54-element-loading="ai"]'))section.prepend(this._inlineLoadingNode(this._t("loadingSectionData"),"ai"));
      }
    }

    if(tab==="week"&&!this._resourceHasData("week")){
      const empty=c.querySelector(".empty");
      if(empty){empty.replaceChildren(this._inlineLoadingNode(this._t("loadingSectionData"),"week"));}
    }
  }
}

customElements.define("cook4me-recipe-hub-panel-v56",Cook4MeRecipeHubPanelV56);
