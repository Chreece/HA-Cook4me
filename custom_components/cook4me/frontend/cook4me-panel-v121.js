import './cook4me-panel-v120.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v120');

class Cook4MeRecipeHubPanelV121 extends BasePanel{
 _v121DisarmBack(){
  if(this._v121PopState)globalThis.removeEventListener?.('popstate',this._v121PopState,true);
  this._v121PopState=null;
  this._v121HistoryArmed=false;
  this._v121HistoryToken='';
  this._v121HistoryClosing=false;
 }
 _v121ArmBack(){
  if(this._v121HistoryArmed||!globalThis.history?.pushState)return;
  const token=globalThis.crypto?.randomUUID?.()||`cook4me-scanner-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  this._v121HistoryToken=token;
  this._v121PopState=event=>{
   if(!this._v121HistoryArmed)return;
   event?.stopImmediatePropagation?.();
   event?.stopPropagation?.();
   const closing=!!this._v121HistoryClosing;
   this._v121DisarmBack();
   if(closing)return;
   if(!this._v78Dialog)return;
   this._v121ClosingFromBack=true;
   try{
    this._v78Close(true);
   }finally{
    this._v121ClosingFromBack=false;
   }
  };
  globalThis.addEventListener?.('popstate',this._v121PopState,true);
  try{
   const current=globalThis.history.state;
   const state=current&&typeof current==='object'?{...current}:{};
   state.__cook4meScannerV121=token;
   globalThis.history.pushState(state,'',globalThis.location?.href);
   this._v121HistoryArmed=true;
  }catch(_error){
   this._v121DisarmBack();
  }
 }
 async _v78Open(mode='barcode'){
  this._v121Opening=true;
  try{
   const opening=super._v78Open(mode);
   if(this._v78Dialog)this._v121ArmBack();
   return await opening;
  }finally{
   this._v121Opening=false;
  }
 }
 _v78Close(force=false){
  const before=this._v78Dialog;
  const armed=!!this._v121HistoryArmed;
  super._v78Close(force);
  const closed=!!before&&!this._v78Dialog;
  if(!closed||!armed||this._v121ClosingFromBack||this._v121Opening)return;
  this._v121HistoryClosing=true;
  try{
   globalThis.history?.back?.();
  }catch(_error){
   this._v121DisarmBack();
  }
 }
 disconnectedCallback(){
  this._v121DisarmBack();
  super.disconnectedCallback();
 }
 _v121ArrangeCameraControls(frame){
  if(!frame)return;
  const power=frame.querySelector('[data-v111-power]');
  if(power){
   power.hidden=true;
   power.setAttribute('aria-hidden','true');
   power.tabIndex=-1;
  }
  const bottom=frame.querySelector('.v111-bottom');
  const camera=frame.querySelector('[data-v78-camera]');
  if(!bottom||!camera)return;
  if(bottom.firstElementChild!==camera)bottom.prepend(camera);
  const torch=frame.querySelector('[data-v120-torch]');
  if(torch&&camera.nextElementSibling!==torch)camera.after(torch);
  camera.onclick=event=>{
   event.preventDefault();
   event.stopPropagation();
   if(this._v120LiveTrack()||this._v80CameraPending)this._v78StopCamera();
   else void this._v111Resume();
  };
  const active=!!this._v120LiveTrack()||!!this._v80CameraPending;
  const label=this._v111Text(active?'stop':'camera');
  camera.hidden=false;
  camera.title=label;
  camera.setAttribute('aria-label',label);
  camera.setAttribute('aria-pressed',String(active));
  camera.querySelector('ha-icon')?.setAttribute('icon',`mdi:${active?'camera-off-outline':'camera-outline'}`);
  camera.disabled=!active&&(!!this._v78Busy||!!this._v78Submitted&&!this._v78Draft?.scanApplied);
 }
 _v111BuildFrame(video){
  super._v111BuildFrame(video);
  this._v121ArrangeCameraControls(this._v78Dialog?.querySelector('[data-v111-frame]'));
 }
 _v111Paint(){
  super._v111Paint();
  this._v121ArrangeCameraControls(this._v78Dialog?.querySelector('[data-v111-frame]'));
 }
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.18.7');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v121',Cook4MeRecipeHubPanelV121);
