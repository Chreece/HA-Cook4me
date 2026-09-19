import './cook4me-panel-v124.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v124');

class Cook4MeRecipeHubPanelV125 extends BasePanel{
 _renderTab(){
  const result=super._renderTab();
  this._v125Styles();
  this.setAttribute('data-cook4me-build','2026.9.19.4');
  return result;
 }
 _v125Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v125Styles'))return;
  const style=document.createElement('style');
  style.id='v125Styles';
  style.textContent=`
   [data-filter-dialog] footer{
    margin:0 -18px -18px!important;
    padding:10px 18px 18px!important;
    border-radius:0 0 19px 19px;
    z-index:3;
   }
  `;
  this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v125',Cook4MeRecipeHubPanelV125);
