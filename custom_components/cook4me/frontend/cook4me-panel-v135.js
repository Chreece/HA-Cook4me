const V134='cook4me-recipe-hub-panel-v134';
if(!customElements.get(V134))await import('./cook4me-panel-v134.js?v=2026.9.20.8');
const BasePanel=customElements.get(V134);
const DEVICE_ASSET_V135=new URL('./assets/device-v133.jpg?v=2026.9.20.9',import.meta.url).href;

class Cook4MeRecipeHubPanelV135 extends BasePanel{
 _v132FixDeviceAsset(){
  const root=this.shadowRoot;
  const image=root?.querySelector('.v130-model-photo');
  if(!image)return;
  const model=image.closest('.v130-model');
  if(image.getAttribute('src')!==DEVICE_ASSET_V135){
   image.dataset.v135Loaded='';
   image.src=DEVICE_ASSET_V135;
  }
  const loaded=()=>{
   image.dataset.v135Loaded='true';
   model?.classList.remove('v132-model-image-error','v133-model-image-error','v134-model-image-error','v135-model-image-error');
  };
  const failed=()=>{
   image.dataset.v135Loaded='false';
   model?.classList.add('v135-model-image-error');
  };
  if(image.complete){
   if(image.naturalWidth>0)loaded(); else failed();
  }else{
   image.addEventListener('load',loaded,{once:true});
   image.addEventListener('error',failed,{once:true});
  }
 }

 _v71FitTitle(title){
  const box=title?.closest?.('.rx-v66-title')||title?.parentElement;
  if(!title||!box?.clientWidth||!box.clientHeight)return;

  title.style.setProperty('-webkit-line-clamp','unset');
  title.style.setProperty('-webkit-box-orient','initial');
  title.style.setProperty('display','block');
  title.style.setProperty('max-height','none');
  title.style.setProperty('overflow','visible');
  title.style.setProperty('line-height','1.18');
  title.style.setProperty('padding-bottom','3px');

  const style=getComputedStyle(box);
  const verticalPadding=(parseFloat(style.paddingTop)||0)+(parseFloat(style.paddingBottom)||0);
  const available=Math.max(24,box.clientHeight-verticalPadding-4);

  let low=11,high=20;
  const fits=size=>{
   title.style.fontSize=`${size}px`;
   return title.scrollHeight<=available+0.5;
  };

  if(!fits(low)){
   title.style.fontSize=`${low}px`;
   return;
  }
  while(high-low>0.2){
   const size=(low+high)/2;
   if(fits(size))low=size;else high=size;
  }
  title.style.fontSize=`${Math.floor(low*10)/10}px`;
 }

 _updateHeader(){
  super._updateHeader();
  this._v132FixDeviceAsset();
  this._v135Styles();
 }
 _renderShell(){
  super._renderShell();
  this._v132FixDeviceAsset();
  this._v135Styles();
 }
 _renderTab(){
  const result=super._renderTab();
  this._v132FixDeviceAsset();
  this._v135Styles();
  cancelAnimationFrame(this._v71FitFrame);
  this._v71FitFrame=requestAnimationFrame(()=>this._v71FitTitles?.());
  this.setAttribute('data-cook4me-build','2026.9.20.9');
  return result;
 }
 _v135Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v135Styles'))return;
  const style=document.createElement('style');
  style.id='v135Styles';
  style.textContent=`
   /* Revert the artifact-prone v134 cutout. The clean v133 photo stays intact;
      pure white photo background disappears by multiplying against the card. */
   .v130-model{
    background:transparent!important;
    box-shadow:none!important;
    border-radius:0!important;
    overflow:visible!important;
    filter:drop-shadow(0 8px 12px rgba(0,0,0,.28))!important;
   }
   .v130-model-photo{
    border-radius:0!important;
    background:transparent!important;
    mix-blend-mode:multiply!important;
    filter:brightness(1.12) contrast(1.08)!important;
    opacity:1!important;
    image-rendering:auto;
   }
   .v130-model.v135-model-image-error .v130-model-photo{opacity:0!important}

   /* Restore the display geometry that matches the clean v133/original cooker. */
   .v130-brand-mask{
    left:31.2%!important;top:47.5%!important;width:38.2%!important;height:40.5%!important;
    border-radius:18% 18% 22% 22%!important;
    background:linear-gradient(180deg,#080a0b 0%,#050607 72%,#090a0b 100%)!important;
    box-shadow:inset 0 0 0 1px rgba(255,255,255,.16),inset 0 0 18px rgba(255,255,255,.035)!important;
   }
   .v130-live-screen{
    left:34.2%!important;top:51%!important;width:32.2%!important;height:31%!important;
    border-radius:12%!important;padding:5% 5% 6%!important;
   }
   .v130-recipe-photo{height:58%!important}
   .v130-screen-symbol{font-size:19px!important;margin-bottom:3px!important}
   .v130-screen-copy strong{font-size:7px!important}
   .v130-screen-copy span{font-size:5.5px!important}
   .v130-screen-progress{height:2px!important;margin-top:4px!important}

   /* Never clip descenders. Long titles shrink until the full title fits. */
   article.rx-v66-recipe>.rx-v66-title{align-items:flex-start!important;overflow:hidden!important}
   article.rx-v66-recipe>.rx-v66-title h3{
    line-height:1.18!important;
    max-height:none!important;
    padding-bottom:3px!important;
    -webkit-line-clamp:unset!important;
    -webkit-box-orient:initial!important;
    display:block!important;
    overflow:visible!important;
   }

   @media(max-width:700px){
    .v130-screen-copy strong{font-size:5.4px!important}
    .v130-screen-copy span{font-size:4.4px!important}
   }
  `;
  this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v135',Cook4MeRecipeHubPanelV135);
