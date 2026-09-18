import './cook4me-panel-v122.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v122');

class Cook4MeRecipeHubPanelV123 extends BasePanel{
 _v120TorchSupported(track=this._v120LiveTrack()){
  if(!track?.applyConstraints||!track?.getCapabilities)return false;
  try{
   return track.getCapabilities()?.torch===true;
  }catch(_error){
   return false;
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
   await track.applyConstraints({advanced:[{torch:next}]});
   if(track!==this._v120LiveTrack())return;
   this._v120TorchOn=next;
  }catch(_error){
   this._v120TorchBlocked=true;
   this._v120TorchOn=false;
  }finally{
   this._v120TorchPending=false;
   this._v120SyncTorch();
  }
 }
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.19.2');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v123',Cook4MeRecipeHubPanelV123);
