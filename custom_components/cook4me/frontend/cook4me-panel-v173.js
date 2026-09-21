const V172='cook4me-recipe-hub-panel-v172';
if(!customElements.get(V172))await import('./cook4me-panel-v172.js?v=2026.9.21.37');
const BasePanel=customElements.get(V172);

class Cook4MeRecipeHubPanelV173 extends BasePanel{
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.21.38');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v173',Cook4MeRecipeHubPanelV173);
