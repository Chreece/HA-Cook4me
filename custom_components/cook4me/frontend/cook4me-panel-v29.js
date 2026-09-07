import "./cook4me-panel-v28.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v28");

class Cook4MeRecipeHubPanelV29 extends BasePanel{
  constructor(){
    super();
    this._manualMeta={title:"",servings:"",steps:"",notes:""};
  }

  _renderMineV28(c){
    super._renderMineV28(c);
    const fields={
      manualTitle:"title",
      manualServings:"servings",
      manualSteps:"steps",
      manualNotes:"notes",
    };
    for(const [id,key] of Object.entries(fields)){
      const input=c.querySelector(`#${id}`);
      if(!input)continue;
      input.value=this._manualMeta[key]??"";
      input.addEventListener("input",()=>{this._manualMeta[key]=String(input.value??"");});
    }
  }

  async _saveManualV28(c){
    await super._saveManualV28(c);
    if(this._manualDraftIngredients.length===0&&this._opened){
      this._manualMeta={title:"",servings:"",steps:"",notes:""};
      this._renderMineV28(c);
    }
  }
}

customElements.define("cook4me-recipe-hub-panel-v29",Cook4MeRecipeHubPanelV29);
