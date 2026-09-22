const V176='cook4me-recipe-hub-panel-v176';
if(!customElements.get(V176))await import('./cook4me-panel-v176.js?v=2026.9.22.3');
const BasePanel=customElements.get(V176);

class Cook4MeRecipeHubPanelV177 extends BasePanel{
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.22.4');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v177',Cook4MeRecipeHubPanelV177);
