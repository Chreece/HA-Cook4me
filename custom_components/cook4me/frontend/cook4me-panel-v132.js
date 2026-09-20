const V131='cook4me-recipe-hub-panel-v131';
if(!customElements.get(V131))await import('./cook4me-panel-v131.js?v=2026.9.20.5');
const BasePanel=customElements.get(V131);
const DEVICE_ASSET_V132=new URL('./assets/device-v132.jpg?v=2026.9.20.6',import.meta.url).href;

class Cook4MeRecipeHubPanelV132 extends BasePanel{
 _v132UpgradeProperty(name){
  if(!Object.prototype.hasOwnProperty.call(this,name))return false;
  const value=this[name];
  delete this[name];
  this[name]=value;
  return true;
 }
 connectedCallback(){
  // HA may create <cook4me-...> and assign properties before this module
  // finishes loading. In that upgrade path the own properties shadow the
  // prototype setters, leaving the panel connected with an empty shadow root.
  this._v132UpgradeProperty('panel');
  this._v132UpgradeProperty('hass');
  super.connectedCallback();
  // Defensive recovery for any host ordering where the inherited callback ran
  // before the recovered setter populated the shell.
  if(this._hass&&this.shadowRoot&&!this.shadowRoot.innerHTML){
   this._renderShell();
   void this._loadOverview();
  }
 }
 _v132FixDeviceAsset(){
  const root=this.shadowRoot;
  const image=root?.querySelector('.v130-model-photo');
  if(!image)return;
  if(image.getAttribute('src')!==DEVICE_ASSET_V132){
   image.src=DEVICE_ASSET_V132;
  }
  image.addEventListener('load',()=>{
   image.dataset.v132Loaded='true';
   image.closest('.v130-model')?.classList.remove('v132-model-image-error');
  },{once:true});
  image.addEventListener('error',()=>{
   image.dataset.v132Loaded='false';
   image.closest('.v130-model')?.classList.add('v132-model-image-error');
  },{once:true});
 }
 _updateHeader(){
  super._updateHeader();
  this._v132FixDeviceAsset();
 }
 _renderShell(){
  super._renderShell();
  this._v132FixDeviceAsset();
  this._v132Styles();
 }
 _renderTab(){
  const result=super._renderTab();
  this._v132FixDeviceAsset();
  this._v132Styles();
  this.setAttribute('data-cook4me-build','2026.9.20.6');
  return result;
 }
 _v132Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v132Styles'))return;
  const style=document.createElement('style');
  style.id='v132Styles';
  style.textContent=`
   .v130-model.v132-model-image-error{
    border-radius:24px;
    background:
     radial-gradient(circle at 50% 24%,rgba(255,255,255,.12),transparent 34%),
     linear-gradient(180deg,#242729,#111415 58%,#090b0c);
   }
   .v130-model.v132-model-image-error .v130-model-photo{opacity:0}
  `;
  this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v132',Cook4MeRecipeHubPanelV132);
