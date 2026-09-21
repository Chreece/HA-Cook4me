const V148='cook4me-recipe-hub-panel-v148';
if(!customElements.get(V148))await import('./cook4me-panel-v148.js?v=2026.9.21.13');
const BasePanel=customElements.get(V148);

class Cook4MeRecipeHubPanelV149 extends BasePanel{
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.21.14');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v149',Cook4MeRecipeHubPanelV149);
