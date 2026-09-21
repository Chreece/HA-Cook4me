const V146='cook4me-recipe-hub-panel-v146';
if(!customElements.get(V146))await import('./cook4me-panel-v146.js?v=2026.9.21.11');
const BasePanel=customElements.get(V146);

class Cook4MeRecipeHubPanelV147 extends BasePanel{
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.21.12');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v147',Cook4MeRecipeHubPanelV147);
