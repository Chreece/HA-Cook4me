import "./cook4me-panel-v49.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v49");

class Cook4MeRecipeHubPanelV50 extends BasePanel{
  async _api(type,data={}){
    const mapped={
      "cook4me/v21/currency_state":"cook4me/v24/currency_state",
      "cook4me/v21/currency_set":"cook4me/v24/currency_set",
      "cook4me/recipe_detail":"cook4me/v24/recipe_detail",
      "cook4me/v7/recipe_detail":"cook4me/v24/recipe_detail",
      "cook4me/v9/recipe_detail":"cook4me/v24/recipe_detail",
      "cook4me/v22/ai_create":"cook4me/v25/ai_create",
      "cook4me/v22/send_multi":"cook4me/v25/send_multi",
    }[type]||type;
    const payload={...(data||{})};
    if(String(mapped).startsWith("cook4me/v24/"))delete payload.refresh;
    return super._api(mapped,payload);
  }
}

customElements.define("cook4me-recipe-hub-panel-v50",Cook4MeRecipeHubPanelV50);
