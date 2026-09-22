const V173='cook4me-recipe-hub-panel-v173';
if(!customElements.get(V173))await import('./cook4me-panel-v173.js?v=2026.9.21.38');
const BasePanel=customElements.get(V173);

class Cook4MeRecipeHubPanelV174 extends BasePanel{
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.22.1');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v174',Cook4MeRecipeHubPanelV174);
