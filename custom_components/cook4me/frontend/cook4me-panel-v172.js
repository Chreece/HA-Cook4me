const V171='cook4me-recipe-hub-panel-v171';
if(!customElements.get(V171))await import('./cook4me-panel-v171.js?v=2026.9.21.36');
const BasePanel=customElements.get(V171);

class Cook4MeRecipeHubPanelV172 extends BasePanel{
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.21.37');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v172',Cook4MeRecipeHubPanelV172);
