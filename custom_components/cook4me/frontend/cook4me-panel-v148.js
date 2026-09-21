const V147='cook4me-recipe-hub-panel-v147';
if(!customElements.get(V147))await import('./cook4me-panel-v147.js?v=2026.9.21.12');
const BasePanel=customElements.get(V147);

class Cook4MeRecipeHubPanelV148 extends BasePanel{
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.21.13');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v148',Cook4MeRecipeHubPanelV148);
