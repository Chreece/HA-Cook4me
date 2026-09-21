const V138='cook4me-recipe-hub-panel-v138';
if(!customElements.get(V138))await import('./cook4me-panel-v138.js?v=2026.9.21.3');
const BasePanel=customElements.get(V138);
const SOURCE_ASSET_V139=new URL('./assets/device-v133.jpg?v=2026.9.21.4',import.meta.url).href;

class Cook4MeRecipeHubPanelV139 extends BasePanel{
 _v132FixDeviceAsset(){
  const root=this.shadowRoot;
  const model=root?.querySelector('.v130-model');
  const image=root?.querySelector('.v130-model-photo');
  if(!model)return;

  if(image)image.style.setProperty('display','none','important');

  let svg=model.querySelector('.v139-model-svg');
  if(!svg){
   svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
   svg.setAttribute('class','v139-model-svg');
   svg.setAttribute('viewBox','0 0 474 474');
   svg.setAttribute('preserveAspectRatio','xMidYMid meet');
   svg.setAttribute('aria-hidden','true');
   svg.innerHTML=`
    <defs>
     <filter id="v139-white-key" x="-12%" y="-12%" width="124%" height="124%" color-interpolation-filters="sRGB">
      <feColorMatrix type="matrix"
       values="
        1 0 0 0 0
        0 1 0 0 0
        0 0 1 0 0
        -0.333 -0.333 -0.333 0 1"
       result="keyed"/>
      <feComponentTransfer in="keyed">
       <feFuncA type="linear" slope="4.76" intercept="-0.19"/>
      </feComponentTransfer>
     </filter>
    </defs>
    <image href="${this._escape(SOURCE_ASSET_V139)}"
     x="0" y="0" width="474" height="474"
     preserveAspectRatio="xMidYMid meet"
     filter="url(#v139-white-key)"/>
    <rect x="174" y="248" width="127" height="80" rx="12" fill="#060808"/>
    <rect x="218" y="231" width="40" height="15" rx="3" fill="#0b0c0c"/>
    <rect x="219" y="357" width="38" height="13" rx="3" fill="#0b0c0c"/>
   `;
   model.prepend(svg);
  }

  model.classList.remove(
   'v132-model-image-error','v133-model-image-error',
   'v134-model-image-error','v135-model-image-error','v138-model-image-error'
  );
  model.dataset.v139Shell='ready';
 }

 _updateHeader(){
  super._updateHeader();
  this._v132FixDeviceAsset();
  this._v139Styles();
 }
 _renderShell(){
  super._renderShell();
  this._v132FixDeviceAsset();
  this._v139Styles();
 }
 _renderTab(){
  const result=super._renderTab();
  this._v132FixDeviceAsset();
  this._v139Styles();
  this.setAttribute('data-cook4me-build','2026.9.21.4');
  return result;
 }

 _v139Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v139Styles'))return;
  const style=document.createElement('style');
  style.id='v139Styles';
  style.textContent=`
   .v130-model{
    isolation:auto!important;
    background:transparent!important;
    box-shadow:none!important;
    border-radius:0!important;
    overflow:visible!important;
    filter:none!important;
    opacity:1!important;
   }
   .v130-model-photo{display:none!important}

   .v139-model-svg{
    position:absolute;
    inset:0;
    width:100%;
    height:100%;
    z-index:1;
    overflow:visible;
    pointer-events:none;
    filter:
     drop-shadow(0 0 4px rgba(220,230,255,.30))
     drop-shadow(0 0 10px rgba(170,195,255,.12))
     drop-shadow(0 8px 12px rgba(0,0,0,.34));
   }

   .v130-brand-mask{display:none!important}
   .v130-live-screen{
    z-index:3!important;
    left:36.7%!important;
    top:52.3%!important;
    width:26.8%!important;
    height:16.9%!important;
    border-radius:11%!important;
    padding:2.2% 3% 2.8%!important;
    background:radial-gradient(circle at 50% 20%,#21322c,#080c0b 58%,#030404)!important;
    box-shadow:0 0 8px rgba(57,190,137,.13),inset 0 0 0 1px rgba(255,255,255,.07)!important;
   }
   .v130-recipe-photo{height:58%!important}
   .v130-screen-symbol{font-size:13px!important;margin-bottom:2px!important}
   .v130-screen-copy strong{font-size:5.8px!important;line-height:1.05!important}
   .v130-screen-copy span{font-size:4.3px!important;line-height:1.05!important}
   .v130-screen-progress{height:1.5px!important;margin-top:2px!important}

   .v133-offline-screen .v130-live-screen{
    box-shadow:0 0 9px rgba(219,68,55,.24),inset 0 0 0 1px rgba(255,255,255,.07)!important;
   }

   @media(max-width:700px){
    .v130-screen-symbol{font-size:11px!important}
    .v130-screen-copy strong{font-size:4.9px!important}
    .v130-screen-copy span{font-size:3.8px!important}
   }
  `;
  this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v139',Cook4MeRecipeHubPanelV139);
