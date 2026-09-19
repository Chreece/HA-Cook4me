import './cook4me-panel-v121.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v121');

const V122_TEXT={
 en:{torchUnavailable:'This browser cannot control the camera flashlight.'},
 de:{torchUnavailable:'Dieser Browser kann die Kamera-Taschenlampe nicht steuern.'},
 el:{torchUnavailable:'Το πρόγραμμα περιήγησης δεν μπορεί να ελέγξει τον φακό της κάμερας.'}
};

class Cook4MeRecipeHubPanelV122 extends BasePanel{
 _v122Text(key){
  const code=String(this._hass?.language||'en').toLowerCase().split(/[-_]/)[0];
  return (V122_TEXT[code]||V122_TEXT.en)[key]||V122_TEXT.en[key]||key;
 }
 _v120TorchSupported(track=this._v120LiveTrack()){
  if(!track?.applyConstraints)return false;
  try{
   const facing=track.getSettings?.().facingMode;
   return facing!=='user';
  }catch(_error){
   return true;
  }
 }
 async _v120ToggleTorch(){
  if(this._v120TorchPending)return;
  const track=this._v120LiveTrack();
  if(!this._v120TorchSupported(track)){this._v120SyncTorch();return;}
  const next=!this._v120TorchOn;
  this._v120TorchPending=true;
  this._v120SyncTorch();
  try{
   let applied=false;
   try{
    await track.applyConstraints({advanced:[{torch:next}]});
    applied=true;
   }catch(_advancedError){
    await track.applyConstraints({torch:next});
    applied=true;
   }
   if(!applied||track!==this._v120LiveTrack())return;
   const setting=track.getSettings?.().torch;
   this._v120TorchOn=typeof setting==='boolean'?setting:next;
  }catch(_error){
   this._v120TorchBlocked=true;
   this._v120TorchOn=false;
   this._v78SetStatus?.(this._v122Text('torchUnavailable'));
  }finally{
   this._v120TorchPending=false;
   this._v120SyncTorch();
  }
 }
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.19.1');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v122',Cook4MeRecipeHubPanelV122);
