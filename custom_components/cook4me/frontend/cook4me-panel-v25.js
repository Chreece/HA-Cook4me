import "./cook4me-panel-v24.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v24");

class Cook4MeRecipeHubPanelV25 extends BasePanel {
  _todayIso(){
    const d=new Date();
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
  }

  _missingIngredientObjects(recipe){
    const base=super._missingIngredientObjects(recipe)||[];
    const shortages=recipe?.match?.quantityShortages;
    if(!Array.isArray(shortages)||!shortages.length)return base;
    const exact=shortages.map(row=>({
      ...(row?.key?{key:String(row.key)}:{}),
      name:String(row?.name||""),
      quantity:row?.missingQuantity,
      unit:String(row?.missingUnit||""),
      shortageOnly:true,
    })).filter(row=>row.name&&Number(row.quantity)>0);
    const identities=new Set(exact.map(row=>row.key?`k:${row.key}`:`n:${row.name.trim().toLocaleLowerCase()}`));
    // Keep base missing ingredients whose required amount is unknown. We can add
    // exact shortages to HA Shopping List without silently dropping an unknown item.
    const unknown=base.filter(row=>{
      const key=String(row?.foodKey||row?.key||"");
      const name=this._ingredientName(row).trim().toLocaleLowerCase();
      return !identities.has(key?`k:${key}`:`n:${name}`);
    });
    return [...exact,...unknown];
  }
}

customElements.define("cook4me-recipe-hub-panel-v25",Cook4MeRecipeHubPanelV25);
