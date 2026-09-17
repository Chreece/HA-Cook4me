import "./cook4me-panel-v96.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v96');
class Cook4MeRecipeHubPanelV97 extends BasePanel{
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.17.1');return result;}
 _v94Amount(quantity,unit){
  const units={en:{sheet:['sheet','sheets'],pod:['pod','pods']},de:{sheet:['Blatt','Blätter'],pod:['Schote','Schoten']},el:{sheet:['φύλλο','φύλλα'],pod:['λοβός','λοβοί']}};
  const language=this._uiIngredientLanguage(),forms=units[language]?.[unit];
  return super._v94Amount(quantity,forms?forms[new Intl.PluralRules(language).select(quantity)==='one'?0:1]:unit);
 }
}
customElements.define('cook4me-recipe-hub-panel-v97',Cook4MeRecipeHubPanelV97);
