const V145='cook4me-recipe-hub-panel-v145';
if(!customElements.get(V145))await import('./cook4me-panel-v145.js?v=2026.9.21.10');
const BasePanel=customElements.get(V145);

class Cook4MeRecipeHubPanelV146 extends BasePanel{
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.21.11');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v146',Cook4MeRecipeHubPanelV146);
