const V133='cook4me-recipe-hub-panel-v133';
if(!customElements.get(V133))await import('./cook4me-panel-v133.js?v=2026.9.20.7');
const BasePanel=customElements.get(V133);
const DEVICE_ASSET_V134=new URL('./assets/device-v134.webp?v=2026.9.20.8',import.meta.url).href;

class Cook4MeRecipeHubPanelV134 extends BasePanel{
 _v132FixDeviceAsset(){
  const root=this.shadowRoot;
  const image=root?.querySelector('.v130-model-photo');
  if(!image)return;
  const model=image.closest('.v130-model');
  if(image.getAttribute('src')!==DEVICE_ASSET_V134){
   image.dataset.v134Loaded='';
   image.src=DEVICE_ASSET_V134;
  }
  const loaded=()=>{
   image.dataset.v134Loaded='true';
   model?.classList.remove('v132-model-image-error','v133-model-image-error','v134-model-image-error');
  };
  const failed=()=>{
   image.dataset.v134Loaded='false';
   model?.classList.add('v134-model-image-error');
  };
  if(image.complete){
   if(image.naturalWidth>0)loaded();
   else failed();
  }else{
   image.addEventListener('load',loaded,{once:true});
   image.addEventListener('error',failed,{once:true});
  }
 }
 _updateHeader(){
  super._updateHeader();
  this._v132FixDeviceAsset();
  this._v134Styles();
 }
 _renderShell(){
  super._renderShell();
  this._v132FixDeviceAsset();
  this._v134Styles();
 }
 _renderTab(){
  const result=super._renderTab();
  this._v132FixDeviceAsset();
  this._v134Styles();
  this.setAttribute('data-cook4me-build','2026.9.20.8');
  return result;
 }
 _v134Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v134Styles'))return;
  const style=document.createElement('style');
  style.id='v134Styles';
  style.textContent=`
   .v130-model{
    background:transparent!important;
    box-shadow:none!important;
    filter:none!important;
    border-radius:0!important;
    overflow:visible!important;
   }
   .v130-model-photo{
    border-radius:0!important;
    background:transparent!important;
    mix-blend-mode:normal!important;
    filter:drop-shadow(0 8px 12px rgba(0,0,0,.34))!important;
    opacity:1!important;
   }
   .v130-model.v134-model-image-error .v130-model-photo{opacity:0!important}

   /* Cover only the baked-in display content, not the physical bezel. */
   .v130-brand-mask{
    left:36.1%!important;
    top:52.5%!important;
    width:27.4%!important;
    height:19.2%!important;
    border-radius:12%!important;
    background:#070909!important;
    box-shadow:none!important;
   }

   /* The live display sits exactly on the generated cooker's screen. */
   .v130-live-screen{
    left:36.1%!important;
    top:52.5%!important;
    width:27.4%!important;
    height:19.2%!important;
    border-radius:12%!important;
    padding:3.2% 4.2% 4%!important;
   }
   .v130-recipe-photo{height:60%!important}
   .v130-screen-symbol{font-size:15px!important;margin-bottom:2px!important}
   .v130-screen-copy strong{font-size:6.2px!important}
   .v130-screen-copy span{font-size:4.8px!important}
   .v130-screen-progress{height:1.5px!important;margin-top:3px!important}

   @media(max-width:700px){
    .v130-screen-symbol{font-size:11px!important}
    .v130-screen-copy strong{font-size:4.7px!important}
    .v130-screen-copy span{font-size:3.8px!important}
   }
  `;
  this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v134',Cook4MeRecipeHubPanelV134);
