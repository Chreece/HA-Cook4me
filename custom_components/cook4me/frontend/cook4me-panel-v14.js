import "./cook4me-panel-v13.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v13");

class Cook4MeRecipeHubPanelV14 extends BasePanel {
  _recommendHouseRows(){
    const q=String(this._houseFilter||"").trim().toLocaleLowerCase();
    const selected=new Set(this._houseIngredients.map(row=>this._houseKey(row)));
    return this._ingredientCatalog.filter(row=>
      !selected.has(this._houseKey(row))&&
      (!q||String(row.name||"").toLocaleLowerCase().includes(q))
    );
  }

  _renderHouseChoices(c){
    const select=c.querySelector("#houseCatalog");
    if(!select)return;
    const q=String(this._houseFilter||"").trim().toLocaleLowerCase();
    const selected=new Set(this._houseIngredients.map(row=>this._houseKey(row)));
    const rows=this._ingredientCatalog.filter(row=>
      !selected.has(this._houseKey(row))&&
      (!q||String(row.name||"").toLocaleLowerCase().includes(q))
    );
    select.innerHTML=rows.map((row,index)=>`<option value="${index}" data-key="${this._escape(row.key||"")}" data-name="${this._escape(row.name||"")}">${this._escape(row.name||"")}</option>`).join("");
    select._cook4meRows=rows;
  }
}

customElements.define("cook4me-recipe-hub-panel-v14",Cook4MeRecipeHubPanelV14);
