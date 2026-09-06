import "./cook4me-panel-v12.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v12");

class Cook4MeRecipeHubPanelV13 extends BasePanel {
  _catalogVisualKey(value){
    return String(value||"")
      .normalize("NFKD")
      .replace(/\p{M}/gu,"")
      .toLocaleLowerCase()
      .replace(/[\p{P}\p{Z}\s]+/gu," ")
      .trim();
  }

  _dedupeIngredientCatalog(){
    const rows=Array.isArray(this._ingredientCatalog)?this._ingredientCatalog:[];
    const out=[];
    const byName=new Map();
    for(const row of rows){
      const name=String(row?.name||"").trim();
      const key=this._catalogVisualKey(name);
      if(!name||!key)continue;
      const existingIndex=byName.get(key);
      if(existingIndex===undefined){
        byName.set(key,out.length);
        out.push(row);
        continue;
      }
      const existing=out[existingIndex];
      if(!existing?.key&&row?.key)out[existingIndex]=row;
    }
    this._ingredientCatalog=out;
  }

  async _loadIngredientCatalog(language=null,refresh=false){
    await super._loadIngredientCatalog(language,refresh);
    this._dedupeIngredientCatalog();
    if(this._tab==="recommend"||this._tab==="profile")this._renderTab();
  }

  _renderRecommend(c){
    super._renderRecommend(c);
    const section=c.querySelector("section.card");
    section?.querySelector(".notice")?.remove();
  }
}

customElements.define("cook4me-recipe-hub-panel-v13",Cook4MeRecipeHubPanelV13);
