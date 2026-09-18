import "./cook4me-panel-v64.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v64");
const TEXT={
  en:{publicationVersion:"Version",regionalRecipeHelp:"Language editions can differ in ingredients and quantities. The selected edition's ingredients, nutrition and steps are shown."},
  el:{publicationVersion:"Εκδοχή",regionalRecipeHelp:"Οι γλωσσικές εκδόσεις μπορεί να διαφέρουν σε υλικά και ποσότητες. Εμφανίζονται τα υλικά, τα διατροφικά στοιχεία και τα βήματα της επιλεγμένης έκδοσης."},
  de:{publicationVersion:"Variante",regionalRecipeHelp:"Sprachfassungen können sich bei Zutaten und Mengen unterscheiden. Angezeigt werden Zutaten, Nährwerte und Schritte der ausgewählten Fassung."},
};

class Cook4MeRecipeHubPanelV65 extends BasePanel{
  _t(key){return TEXT[this._uiIngredientLanguage()]?.[key]||TEXT.en[key]||super._t(key);}
  _renderTab(){const result=super._renderTab();this.setAttribute("data-cook4me-build","2026.9.15.7");return result;}
  _discardOldCatalog(){
    super._discardOldCatalog();
    if((this._ingredientCatalog||[]).some(row=>!Array.isArray(row.searchAliases)))this._ingredientCatalog=[];
  }
  _resourceHasData(resource){
    if(resource==="catalog"&&(this._ingredientCatalog||[]).some(row=>!Array.isArray(row.searchAliases)))return false;
    return super._resourceHasData(resource);
  }
  _ingredientQueryMatches(row,query){
    const fold=value=>String(value||"").normalize("NFKD").replace(/\p{M}/gu,"").toLowerCase().replaceAll("ς","σ");
    const words=fold(query).split(/\s+/).filter(Boolean),aliases=[row.name,row.canonicalName,...(row.searchAliases||[])].map(fold);
    return words.every(word=>aliases.some(alias=>alias.includes(word)));
  }
  _renderHouseChoices(container){
    const catalog=this._ingredientCatalog,query=this._houseFilter;
    this._ingredientCatalog=(catalog||[]).filter(row=>this._ingredientQueryMatches(row,query));this._houseFilter="";
    try{return super._renderHouseChoices(container);}finally{this._ingredientCatalog=catalog;this._houseFilter=query;}
  }
  _showFilter(key){
    const result=super._showFilter(key);
    if(key==="ingredients"){
      const overlay=this.shadowRoot.querySelector('[data-filter-dialog="ingredients"]');
      const rows=new Map(this._todayIngredientRows().map(row=>[this._todayIngredientIdentity(row),row]));
      overlay?.querySelector("[data-ingredient-search]")?.addEventListener("input",event=>{
        overlay.querySelectorAll("[data-ingredient-choices] label").forEach(label=>{
          const row=rows.get(label.querySelector("input")?.value);
          label.style.display=row&&this._ingredientQueryMatches(row,event.target.value)?"":"none";
        });
      });
    }
    return result;
  }
  _ensureServingSelection(recipe){
    // A display-only edition has no send ID. Matching empty send IDs used to
    // select the first serving and silently change the displayed publication.
    if(recipe?.displayVariantId||recipe?.searchVariantId)return this._ensureRecipeSelections(recipe);
    return super._ensureServingSelection(recipe);
  }
  _servingSelectHtml(recipe,detail=false){
    const options=this._servingOptions(recipe);
    if(options.length<=1)return "";
    const selected=this._ensureServingSelection(recipe),id=String(selected?.displayVariantId||selected?.sendVariantId||"");
    const choices=options.map(option=>{
      const value=String(option.displayVariantId||option.sendVariantId||"");
      const label=`${option.label??option.servings??"—"}${option.publicationNumber?` · ${this._t("publicationVersion")} ${option.publicationNumber}`:""}`;
      return `<option value="${this._escape(value)}" ${id===value?"selected":""}>${this._escape(label)}</option>`;
    }).join("");
    const note=recipe.regionalPublications&&detail?`<small class="muted">${this._escape(this._t("regionalRecipeHelp"))}</small>`:"";
    return `<div class="field serving-choice" style="min-width:${detail?"180":"140"}px"><label>${this._escape(this._t("servings"))}</label><select data-action="servings">${choices}</select>${note}</div>`;
  }
  _selectServing(recipe,variant,fromDetail=false){
    const option=this._servingOptions(recipe).find(row=>String(row.displayVariantId||row.sendVariantId)===String(variant))
      ||this._servingOptions(recipe).find(row=>row.sendVariantId&&String(row.sendVariantId)===String(variant));
    if(option)return this._changeRecipeVariant(recipe,option,recipe.selectedLanguage||recipe.language,fromDetail);
  }
}

customElements.define("cook4me-recipe-hub-panel-v65",Cook4MeRecipeHubPanelV65);
