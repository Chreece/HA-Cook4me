import "./cook4me-panel-v95.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v95');
class Cook4MeRecipeHubPanelV96 extends BasePanel{
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.16.20');return result;}
}
customElements.define('cook4me-recipe-hub-panel-v96',Cook4MeRecipeHubPanelV96);
