import "./cook4me-panel-v94.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v94');
class Cook4MeRecipeHubPanelV95 extends BasePanel{
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.16.19');return result;}
 _v94Amount(quantity,unit){
  const units={en:{leaf:['leaf','leaves'],sprig:['sprig','sprigs']},de:{leaf:['Blatt','Blätter'],sprig:['Zweig','Zweige']},el:{leaf:['φύλλο','φύλλα'],sprig:['κλωνάρι','κλωνάρια']}};
  const language=this._uiIngredientLanguage(),forms=units[language]?.[unit];
  return super._v94Amount(quantity,forms?forms[new Intl.PluralRules(language).select(quantity)==='one'?0:1]:unit);
 }
}
customElements.define('cook4me-recipe-hub-panel-v95',Cook4MeRecipeHubPanelV95);
