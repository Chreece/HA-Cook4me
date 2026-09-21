const V152='cook4me-recipe-hub-panel-v152';
if(!customElements.get(V152))await import('./cook4me-panel-v152.js?v=2026.9.21.17');
const BasePanel=customElements.get(V152);

class Cook4MeRecipeHubPanelV153 extends BasePanel{
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.21.18');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v153',Cook4MeRecipeHubPanelV153);
