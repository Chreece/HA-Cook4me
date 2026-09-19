import './cook4me-panel-v125.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v125');

class Cook4MeRecipeHubPanelV126 extends BasePanel{
 _renderTab(){
  const result=super._renderTab();
  this._v126Styles();
  this.setAttribute('data-cook4me-build','2026.9.19.5');
  return result;
 }
 _v126Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v126Styles'))return;
  const style=document.createElement('style');
  style.id='v126Styles';
  style.textContent=`
   .rx-overlay>.rx-dialog{--c4m-dialog-footer-pad:18px}
   .rx-overlay>.rx-dialog:has(>footer),
   .rx-overlay>.rx-dialog:has(>form>footer){
    padding-bottom:0!important;
   }
   .rx-overlay>.rx-dialog>footer,
   .rx-overlay>.rx-dialog>form>footer{
    position:sticky;
    bottom:0;
    z-index:4;
    box-sizing:border-box;
    margin:12px calc(-1 * var(--c4m-dialog-footer-pad)) 0!important;
    padding:10px var(--c4m-dialog-footer-pad) max(12px,env(safe-area-inset-bottom))!important;
    background:var(--card-background-color);
    border-top:1px solid var(--divider-color);
    border-radius:0 0 19px 19px;
   }
   [data-filter-dialog] .rx-dialog{--c4m-dialog-footer-pad:18px}
   [data-device-settings] .rx-dialog{--c4m-dialog-footer-pad:24px}
   @media(max-width:520px){
    [data-device-settings] .rx-dialog{--c4m-dialog-footer-pad:16px}
   }
  `;
  this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v126',Cook4MeRecipeHubPanelV126);
