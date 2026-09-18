import './cook4me-panel-v118.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v118');

class Cook4MeRecipeHubPanelV119 extends BasePanel{
 _v119AiMode(){
  const mode=this._v78Draft?.mode==='manual'?'product':this._v78Draft?.mode;
  return ['product','date','nutrition'].includes(mode)?mode:'';
 }
 _v119IsMassUnit(unit){
  return this._v116Grams(1,unit)!==null;
 }
 _v119FitInput(input,minChars){
  if(!input)return;
  const value=String(input.value??'');
  const chars=Math.max(minChars,value.length||minChars);
  input.style.setProperty('width',`calc(${chars}ch + 2.65rem)`,'important');
  input.style.setProperty('max-width','100%','important');
  const label=input.closest('label');
  if(label){
   label.classList.add('v119-compact-field');
   label.classList.toggle('v119-count-field',input.hasAttribute('data-v112-count')||input.hasAttribute('data-v112-count-edit'));
   label.classList.toggle('v119-quantity-field',input.hasAttribute('data-v111-amount')||input.matches('main [data-draft="quantity"]'));
  }
  if(!input.dataset.v119FitBound){
   input.dataset.v119FitBound='1';
   input.addEventListener('input',()=>this._v119FitInput(input,minChars));
  }
 }
 _v119PolishCapture(){
  const c=this._v78Dialog,d=this._v78Draft,frame=c?.querySelector('[data-v111-frame]');if(!c||!d||!frame)return;
  this._v119Styles();

  this._v119FitInput(frame.querySelector('[data-v112-count]'),2);
  this._v119FitInput(c.querySelector('[data-v112-count-edit]'),2);
  this._v119FitInput(frame.querySelector('[data-v111-amount]'),4);
  this._v119FitInput(c.querySelector('main [data-draft="quantity"]'),4);

  const mass=this._v119IsMassUnit(d.unit);
  for(const button of c.querySelectorAll('[data-v116-weight]')){
   button.hidden=!mass;
   button.classList.add('v119-weight-icon');
   button.title=this._v116Text('use');
   button.setAttribute('aria-label',this._v116Text('use'));
   button.innerHTML='<ha-icon icon="mdi:scale-balance" aria-hidden="true"></ha-icon>';
  }

  const restart=frame.querySelector('[data-v113-restart]');if(restart)restart.disabled=!!this._v78Busy;

  for(const unit of c.querySelectorAll('[data-v111-unit],main [data-draft="unit"]')){
   if(unit.dataset.v119WeightBound)continue;
   unit.dataset.v119WeightBound='1';
   unit.addEventListener('change',()=>queueMicrotask(()=>this._v119PolishCapture()));
   unit.addEventListener('input',()=>queueMicrotask(()=>this._v119PolishCapture()));
  }
 }
 _v111Paint(){
  super._v111Paint();
  this._v119PolishCapture();
 }
 _v78RenderCapture(){
  super._v78RenderCapture();
  this._v119PolishCapture();
 }
 _v111BuildFrame(video){
  super._v111BuildFrame(video);
  const frame=this._v78Dialog?.querySelector('[data-v111-frame]');if(!frame)return;
  frame.onclick=event=>{
   if(event.target.closest('button,input,select,label,a'))return;
   const mode=this._v119AiMode(),guideWrap=frame.querySelector('[data-v111-guide-wrap]');
   if(mode&&!guideWrap?.hidden){
    if(event.target.closest('[data-v111-guide]')){
     event.stopPropagation();
     void this._v119CaptureAi(mode);
    }else{
     event.stopPropagation();
     this._v112Editor(true,mode);
    }
    return;
   }
   void this._v111Resume();
  };
 }
 async _v119CaptureAi(mode){
  const d=this._v78Draft,c=this._v78Dialog;if(!d||!c||this._v78Busy||this._v78Submitted)return;
  d.mode=mode;d.editorOpen=false;d.scanPhase='scanning';d.scanNote='';
  this._v111Paint();
  if(!this._v78Stream?.getVideoTracks?.().some(track=>track.readyState==='live'))await this._v78Camera();
  if(d!==this._v78Draft||!this._v78Alive(c)||this._v78Busy||this._v78Submitted)return;
  await this._v78CaptureFrame();
 }
 _v113CanRestart(){
  return !!this._v78Draft;
 }
 async _v113Restart(){
  const old=this._v78Draft;if(!old||this._v78Busy)return;
  const mode=old.mode==='manual'?'product':old.mode;
  const editLotId=old.editLotId;

  this._v112SkipBarcode='';this._v112LastSaved='';
  this._v111CancelRead();
  this._v78Submitted=null;this._v78Saved=false;this._v78Dirty=false;this._v78Status='';

  if(editLotId){
   this._v78Close(true);
   await this._v112EditLot(editLotId);
   return;
  }

  const keepProduct=['date','nutrition'].includes(mode)?{
   productName:old.productName,
   brand:old.brand,
   barcode:old.barcode,
   quantity:old.quantity,
   unit:old.unit,
   ingredient:old.ingredient?structuredClone(old.ingredient):null,
   storageLocationId:old.storageLocationId,
   packageCount:old.packageCount,
   productLocked:!!(old.productLocked||old.productName||old.ingredient),
   scanRecognized:!!(old.scanRecognized||old.productName||old.ingredient),
   paidAmount:old.paidAmount,
   paidCurrency:old.paidCurrency,
   paidShop:old.paidShop,
   paidBasisQuantity:old.paidBasisQuantity,
   paidBasisUnit:old.paidBasisUnit,
  }:null;

  const fresh=this._v111NewDraft(mode);
  if(keepProduct)Object.assign(fresh,keepProduct);
  if(mode==='date'){
   fresh.bestBefore='';
   fresh.nutrition=old.nutrition?structuredClone(old.nutrition):fresh.nutrition;
   fresh.labelNutrition=old.labelNutrition;
  }else if(mode==='nutrition'){
   fresh.bestBefore=old.bestBefore||'';
   fresh.nutrition={basisUnit:'',values:{}};
   fresh.labelNutrition=false;
  }
  fresh.mode=mode;
  fresh.editorOpen=false;
  fresh.scanPhase='scanning';
  fresh.scanNote='';
  this._v78RenderCapture();

  if(mode==='barcode'){
   await this._v80Scan('barcode');
   return;
  }
  await this._v78Camera();
  this._v111Paint();
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.18.5');return result;}
 _v119Styles(){
  if(this.shadowRoot?.querySelector('#v119Styles'))return;
  const style=document.createElement('style');style.id='v119Styles';style.textContent=`
   .v119-weight-icon{display:inline-flex!important;align-items:center;justify-content:center;flex:0 0 48px!important;width:48px!important;min-width:48px!important;max-width:48px!important;padding:8px!important}
   .v119-weight-icon[hidden]{display:none!important}
   .v119-weight-icon ha-icon{--mdc-icon-size:22px}
   .v111-amount{align-items:flex-end}
   .v111-amount .v119-compact-field{flex:0 0 auto!important;min-width:0!important}
   .v111-amount .v119-count-field{width:auto!important}
   .v111-amount .v119-quantity-field{width:auto!important}
   .v111-amount [data-v112-count],.v111-amount [data-v111-amount]{box-sizing:border-box!important;min-width:0!important;max-width:100%!important}
   .v112-editor [data-v112-count-edit],.v112-editor [data-draft="quantity"]{box-sizing:border-box!important;min-width:0!important;max-width:100%!important}
   [data-v111-guide]{cursor:pointer}
   [data-v111-guide-wrap]{cursor:default}
   @media(max-width:430px){.v111-amount{flex-wrap:wrap}.v119-weight-icon{flex-basis:46px!important;width:46px!important;min-width:46px!important;max-width:46px!important}}
  `;
  this.shadowRoot?.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v119',Cook4MeRecipeHubPanelV119);
