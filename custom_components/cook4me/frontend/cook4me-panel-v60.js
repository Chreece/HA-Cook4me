import "./cook4me-panel-v59.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v59");

class Cook4MeRecipeHubPanelV60 extends BasePanel{
  async _api(type,data={}){
    const requested=String(type);
    if(requested==="cook4me/v20/recipe_cost"||requested==="cook4me/v23/recipe_cost"||requested==="cook4me/v30/recipe_cost"){
      const payload={...(data||{})};
      if(this._process?.operationId&&!payload.client_operation_id)payload.client_operation_id=this._process.operationId;
      return super._api("cook4me/v31/recipe_cost",payload);
    }
    return super._api(type,data);
  }
}

customElements.define("cook4me-recipe-hub-panel-v60",Cook4MeRecipeHubPanelV60);
