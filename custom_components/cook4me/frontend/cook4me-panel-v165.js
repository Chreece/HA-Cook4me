const V164='cook4me-recipe-hub-panel-v164';
if(!customElements.get(V164))await import('./cook4me-panel-v164.js?v=2026.9.21.29');
const BasePanel=customElements.get(V164);

class Cook4MeRecipeHubPanelV165 extends BasePanel{
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.21.30');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v165',Cook4MeRecipeHubPanelV165);
