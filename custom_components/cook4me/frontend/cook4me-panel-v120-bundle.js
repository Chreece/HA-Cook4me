
// cook4me-panel-v120.js
(() => {

const BasePanel=customElements.get('cook4me-recipe-hub-panel-v119');

const V120_TEXT={
 en:{torchOn:'Turn flashlight on',torchOff:'Turn flashlight off'},
 de:{torchOn:'Taschenlampe einschalten',torchOff:'Taschenlampe ausschalten'},
 el:{torchOn:'Άναμμα φακού',torchOff:'Σβήσιμο φακού'}
};

class Cook4MeRecipeHubPanelV120 extends BasePanel{
 _v120Text(key){
  const code=String(this._hass?.language||'en').toLowerCase().split(/[-_]/)[0];
  return (V120_TEXT[code]||V120_TEXT.en)[key]||V120_TEXT.en[key]||key;
 }
 _nativeBarcodeScannerAvailable(){
  // Do not hand camera control to the Android/native barcode-scanner activity.
  // The in-panel live scanner, photo picker and manual barcode entry remain available.
  return false;
 }
 _v120LiveTrack(){
  return this._v78Stream?.getVideoTracks?.().find(track=>track.readyState==='live')||null;
 }
 _v120TorchSupported(track=this._v120LiveTrack()){
  if(!track?.getCapabilities)return false;
  try{return track.getCapabilities()?.torch===true;}catch(_error){return false;}
 }
 _v120EnsureTorch(frame){
  if(!frame||frame.querySelector('[data-v120-torch]'))return;
  const camera=frame.querySelector('[data-v78-camera]');
  if(!camera)return;
  camera.insertAdjacentHTML('beforebegin',this._v111Icon(
   'data-v120-torch',
   'flashlight',
   this._v120Text('torchOn'),
   'hidden aria-pressed="false"'
  ));
  frame.querySelector('[data-v120-torch]')?.addEventListener('click',event=>{
   event.preventDefault();
   event.stopPropagation();
   void this._v120ToggleTorch();
  });
 }
 _v120SyncTorch(){
  const frame=this._v78Dialog?.querySelector('[data-v111-frame]');
  if(!frame)return;
  this._v120EnsureTorch(frame);
  const button=frame.querySelector('[data-v120-torch]');
  if(!button)return;
  const track=this._v120LiveTrack();
  const supported=!this._v120TorchBlocked&&this._v120TorchSupported(track);
  if(!supported){
   this._v120TorchOn=false;
   button.hidden=true;
   button.disabled=true;
   button.setAttribute('aria-pressed','false');
   return;
  }
  button.hidden=false;
  button.disabled=!!this._v120TorchPending;
  const on=!!this._v120TorchOn;
  button.setAttribute('aria-pressed',String(on));
  const label=this._v120Text(on?'torchOff':'torchOn');
  button.title=label;
  button.setAttribute('aria-label',label);
  button.querySelector('ha-icon')?.setAttribute('icon',`mdi:${on?'flashlight-off':'flashlight'}`);
 }
 async _v120ToggleTorch(){
  if(this._v120TorchPending)return;
  const track=this._v120LiveTrack();
  if(!this._v120TorchSupported(track)){this._v120SyncTorch();return;}
  const next=!this._v120TorchOn;
  this._v120TorchPending=true;
  this._v120SyncTorch();
  try{
   await track.applyConstraints({advanced:[{torch:next}]});
   if(track!==this._v120LiveTrack())return;
   const setting=track.getSettings?.().torch;
   this._v120TorchOn=typeof setting==='boolean'?setting:next;
  }catch(_error){
   // Some WebViews advertise torch but reject the constraint. Hide it for this camera session.
   this._v120TorchBlocked=true;
   this._v120TorchOn=false;
  }finally{
   this._v120TorchPending=false;
   this._v120SyncTorch();
  }
 }
 _v111BuildFrame(video){
  super._v111BuildFrame(video);
  const frame=this._v78Dialog?.querySelector('[data-v111-frame]');
  frame?.querySelector('[data-v78-native]')?.remove();
  this._v120EnsureTorch(frame);
  this._v120SyncTorch();
 }
 _v111Paint(){
  super._v111Paint();
  this._v120SyncTorch();
 }
 async _v78Camera(){
  const hadLive=!!this._v120LiveTrack();
  if(!hadLive){
   this._v120TorchOn=false;
   this._v120TorchBlocked=false;
   this._v120TorchPending=false;
  }
  await super._v78Camera();
  this._v120SyncTorch();
 }
 _v78StopCamera(){
  const track=this._v120LiveTrack();
  if(this._v120TorchOn&&track?.applyConstraints){
   void track.applyConstraints({advanced:[{torch:false}]}).catch(()=>{});
  }
  this._v120TorchOn=false;
  this._v120TorchBlocked=false;
  this._v120TorchPending=false;
  super._v78StopCamera();
  this._v120SyncTorch();
 }
 _v78Close(force=false){
  const track=this._v120LiveTrack();
  if(this._v120TorchOn&&track?.applyConstraints){
   void track.applyConstraints({advanced:[{torch:false}]}).catch(()=>{});
  }
  this._v120TorchOn=false;
  this._v120TorchBlocked=false;
  this._v120TorchPending=false;
  super._v78Close(force);
 }
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.18.6');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v120',Cook4MeRecipeHubPanelV120);

})();
