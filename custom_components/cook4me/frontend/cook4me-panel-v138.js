const V137='cook4me-recipe-hub-panel-v137';
if(!customElements.get(V137))await import('./cook4me-panel-v137.js?v=2026.9.21.2');
const BasePanel=customElements.get(V137);
const DEVICE_ASSET_V138=new URL('./assets/device-v138.webp?v=2026.9.21.3',import.meta.url).href;

class Cook4MeRecipeHubPanelV138 extends BasePanel{
 _v132FixDeviceAsset(){
  const root=this.shadowRoot;
  const image=root?.querySelector('.v130-model-photo');
  if(!image)return;
  const model=image.closest('.v130-model');

  if(image.getAttribute('src')!==DEVICE_ASSET_V138){
   image.dataset.v138Loaded='';
   image.src=DEVICE_ASSET_V138;
  }

  const loaded=()=>{
   image.dataset.v138Loaded='true';
   model?.classList.remove(
    'v132-model-image-error','v133-model-image-error',
    'v134-model-image-error','v135-model-image-error','v138-model-image-error'
   );
  };
  const failed=()=>{
   image.dataset.v138Loaded='false';
   model?.classList.add('v138-model-image-error');
  };

  if(image.complete){
   if(image.naturalWidth>0)loaded();else failed();
  }else{
   image.addEventListener('load',loaded,{once:true});
   image.addEventListener('error',failed,{once:true});
  }
 }

 _updateHeader(){
  super._updateHeader();
  this._v138Styles();
 }
 _renderShell(){
  super._renderShell();
  this._v138Styles();
 }
 _renderTab(){
  const result=super._renderTab();
  this._v138Styles();
  this.setAttribute('data-cook4me-build','2026.9.21.3');
  return result;
 }

 _v138Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v138Styles'))return;
  const style=document.createElement('style');
  style.id='v138Styles';
  style.textContent=`
   /* The v138 asset is a real transparent cooker shell. Do not crop, blend,
      or mask the body. A small CSS glow keeps it legible on dark themes. */
   .v130-model{
    isolation:auto!important;
    background:transparent!important;
    box-shadow:none!important;
    border-radius:0!important;
    overflow:visible!important;
    filter:
      drop-shadow(0 0 5px rgba(220,230,255,.24))
      drop-shadow(0 8px 12px rgba(0,0,0,.34))!important;
    opacity:1!important;
   }
   .v130-model-photo{
    clip-path:none!important;
    mix-blend-mode:normal!important;
    filter:none!important;
    opacity:1!important;
    background:transparent!important;
    border-radius:0!important;
    object-fit:contain!important;
   }
   .v130-model.v138-model-image-error .v130-model-photo{opacity:0!important}

   /* The shell image intentionally contains an empty glass display.
      All information continues to be rendered by the existing live v130
      screen: recipe photo/title, loading, preheat, cooking, warm, done,
      and offline state. */
   .v130-brand-mask{display:none!important}
   .v130-live-screen{
    z-index:3!important;
    left:30.2%!important;
    top:49.1%!important;
    width:39.6%!important;
    height:27.8%!important;
    border-radius:13%!important;
    padding:5% 5% 6%!important;
    background:radial-gradient(circle at 50% 20%,#21322c,#080c0b 58%,#030404)!important;
    box-shadow:0 0 10px rgba(57,190,137,.14),inset 0 0 0 1px rgba(255,255,255,.07)!important;
   }
   .v130-recipe-photo{height:58%!important}
   .v130-screen-symbol{font-size:19px!important;margin-bottom:3px!important}
   .v130-screen-copy strong{font-size:7px!important}
   .v130-screen-copy span{font-size:5.5px!important}
   .v130-screen-progress{height:2px!important;margin-top:4px!important}

   .v133-offline-screen .v130-live-screen{
    box-shadow:0 0 12px rgba(219,68,55,.25),inset 0 0 0 1px rgba(255,255,255,.07)!important;
   }

   @media(max-width:700px){
    .v130-screen-copy strong{font-size:5.4px!important}
    .v130-screen-copy span{font-size:4.4px!important}
   }
  `;
  this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v138',Cook4MeRecipeHubPanelV138);
