const V151='cook4me-recipe-hub-panel-v151';
if(!customElements.get(V151))await import('./cook4me-panel-v151.js?v=2026.9.21.16');
const BasePanel=customElements.get(V151);

class Cook4MeRecipeHubPanelV152 extends BasePanel{
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.21.17');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v152',Cook4MeRecipeHubPanelV152);
