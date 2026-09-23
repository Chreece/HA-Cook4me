import {RecipeCoverageMixin} from './recipe-coverage-v198.js';
import {ProductEditorMixin} from './scanner-editor-v196.js';
import {ReceiptScannerMixin} from './scanner-receipts-v195.js';
import {ScannerSuggestionsMixin} from './scanner-suggestions-v194.js';
const V179='cook4me-recipe-hub-panel-v179';
if(!customElements.get(V179))await import('./cook4me-panel-v179.js?v=2026.9.22.6');
const BasePanel=RecipeCoverageMixin(ProductEditorMixin(ReceiptScannerMixin(ScannerSuggestionsMixin(customElements.get(V179)))));

const V180_TEXT={
 en:{
  manualOutside:'Tap outside the barcode box to enter the product manually.',
  noCamera:'No usable camera is available on this device/browser. Enter the product manually.'
 },
 de:{
  manualOutside:'Tippe außerhalb des Barcode-Rahmens, um das Produkt manuell einzugeben.',
  noCamera:'Auf diesem Gerät/Browser ist keine nutzbare Kamera verfügbar. Gib das Produkt manuell ein.'
 },
 el:{
  manualOutside:'Πάτησε έξω από το πλαίσιο του barcode για να εισαγάγεις το προϊόν χειροκίνητα.',
  noCamera:'Δεν υπάρχει διαθέσιμη ή υποστηριζόμενη κάμερα σε αυτή τη συσκευή/browser. Συμπλήρωσε το προϊόν χειροκίνητα.'
 }
};

class Cook4MeRecipeHubPanelV180 extends BasePanel{
 _v180Text(key){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return (V180_TEXT[lang]||V180_TEXT.en)[key]||V180_TEXT.en[key]||key;
 }
 async _v180CameraCapability(){
  if(!navigator.mediaDevices?.getUserMedia)return false;
  if(typeof navigator.mediaDevices.enumerateDevices!=='function')return true;
  try{
   const devices=await navigator.mediaDevices.enumerateDevices();
   if(Array.isArray(devices)&&devices.length&&!devices.some(device=>device?.kind==='videoinput'))return false;
  }catch(_error){}
  return true;
 }
 _v180SetManualOnly(reason=''){
  const d=this._v78Draft;
  this._v180CameraUnavailable=true;
  this._v141CameraBlocked=true;
  if(!d)return;
  this._v111CancelRead?.();
  if(d.mode!=='receipt'){d.mode='manual';d.editorOpen=true;}
  d.scanPhase='idle';
  d.scanNote='';
  this._v78Status=reason||this._v180Text('noCamera');
  this._v78Busy=false;
  this._v78RenderCapture();
 }
 _v180OpenManualFromFrame(){
  const d=this._v78Draft;if(!d||this._v78Busy||this._v78Submitted)return;
  this._v111CancelRead?.();
  if(this._v78Stream||this._v80CameraPending)this._v78StopCamera?.();
  d.mode='manual';d.scanNote='';d.scanPhase='idle';
  this._v112Editor?.(true,'product');
 }
 async _v78Open(mode='barcode'){
  if(mode!=='manual'){
   const supported=await this._v180CameraCapability();
   if(!supported){
    this._v180CameraUnavailable=true;
    mode='manual';
   }else{
    this._v180CameraUnavailable=false;
   }
  }
  const result=await super._v78Open(mode);
  if(this._v180CameraUnavailable){
   const d=this._v78Draft;
   if(d){
    d.mode='manual';d.editorOpen=true;d.scanPhase='idle';d.scanNote='';
    this._v78Status=this._v180Text('noCamera');
    this._v111Paint?.();
   }
  }
  this._v180DecorateScanner();
  return result;
 }
 async _v78Camera(...args){
  if(this._v180CameraUnavailable)return;
  await super._v78Camera(...args);
  const live=!!this._v78Stream?.getVideoTracks?.().some(track=>track.readyState==='live');
  if(!live&&this._v141CameraBlocked&&this._v78Draft?.scanPhase==='error'){
   this._v180SetManualOnly(this._v180Text('noCamera'));
  }
 }
 _v141KeepCameraWarm(){
  if(this._v180CameraUnavailable)return;
  return super._v141KeepCameraWarm();
 }
 _v180CameraOnlyNodes(frame){
  if(!frame)return [];
  return [
   ...frame.querySelectorAll('[data-v80-scan],[data-v111-power],[data-v78-camera],[data-v78-take],[data-v78-native],[data-v78-file],[data-v111-type],[data-v111-code-wrap]'),
  ];
 }
 _v180DecorateScanner(){
  const c=this._v78Dialog,d=this._v78Draft,frame=c?.querySelector?.('[data-v111-frame]');
  if(!frame||!d)return;
  this._v180Styles();
  frame.classList.toggle('v180-manual-only',!!this._v180CameraUnavailable);
  if(this._v180CameraUnavailable){
   for(const node of this._v180CameraOnlyNodes(frame)){
    node.hidden=true;node.setAttribute?.('aria-hidden','true');
    if('tabIndex'in node)node.tabIndex=-1;
   }
   frame.querySelector('video')?.setAttribute('hidden','');
   frame.querySelector('[data-v112-back]')?.setAttribute('hidden','');
   const editor=frame.querySelector('[data-v112-editor]');
   if(editor&&!editor.querySelector('[data-v180-camera-note]')){
    const note=document.createElement('div');note.dataset.v180CameraNote='';note.className='v180-camera-note';note.setAttribute('role','status');note.textContent=this._v180Text('noCamera');
    editor.prepend(note);
   }
   if(!d.editorOpen&&d.mode!=='receipt'){d.mode='manual';d.editorOpen=true;this._v111Paint?.();}
   return;
  }

  frame.querySelector('[data-v180-camera-note]')?.remove();
  const wrap=frame.querySelector('[data-v111-guide-wrap]');
  let hint=wrap?.querySelector('[data-v180-manual-hint]');
  if(d.mode==='barcode'&&!d.editorOpen){
   if(wrap&&!hint){
    hint=document.createElement('small');hint.dataset.v180ManualHint='';hint.className='v180-manual-hint';wrap.append(hint);
   }
   if(hint)hint.textContent=this._v180Text('manualOutside');
  }else hint?.remove();

  frame.onclick=event=>{
   if(event.target.closest?.('button,input,select,label,a,[data-v112-editor]'))return;
   const current=this._v78Draft;if(!current)return;
   if(current.mode==='barcode'&&!current.editorOpen){
    const guide=frame.querySelector('[data-v111-guide]')?.getBoundingClientRect();
    const x=Number(event.clientX),y=Number(event.clientY);
    const inside=!!guide&&x>=guide.left&&x<=guide.right&&y>=guide.top&&y<=guide.bottom;
    if(!inside){
     this._v180OpenManualFromFrame();
     return;
    }
   }
   void this._v111Resume?.();
  };
 }
 _v78RenderCapture(){
  const result=super._v78RenderCapture();
  this._v180DecorateScanner();
  return result;
 }
 _v111Paint(){
  const result=super._v111Paint();
  this._v180DecorateScanner();
  return result;
 }
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.22.7');
  this.setAttribute('data-cook4me-ui-revision','198');
  this._v180Styles();
  return result;
 }
 _v180Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v180Styles'))return;
  const style=document.createElement('style');style.id='v180Styles';style.textContent=`
   .v180-manual-hint{background:color-mix(in srgb,var(--primary-color) 65%,#071016)!important;color:#fff!important;font-weight:650;line-height:1.35}
   .v180-camera-note{margin:0 0 12px;padding:12px 14px;border:1px solid var(--divider-color);border-radius:12px;background:color-mix(in srgb,var(--primary-color) 12%,var(--card-background-color));font-weight:600;line-height:1.4}
   .v180-manual-only .v111-modes,.v180-manual-only .v111-bottom,.v180-manual-only .v111-guide-wrap,.v180-manual-only video{display:none!important}
   .v180-manual-only [data-v112-editor]{inset:12px!important}
  `;this.shadowRoot.append(style);
 }
}
// A new active element prevents HA's long-lived page from reusing a registered
// pre-editor v180 constructor after the backend integration has been updated.
if(!customElements.get('cook4me-recipe-hub-panel-v180'))customElements.define('cook4me-recipe-hub-panel-v180',Cook4MeRecipeHubPanelV180);
if(!customElements.get('cook4me-recipe-hub-panel-v180-runtime-v198'))customElements.define('cook4me-recipe-hub-panel-v180-runtime-v198',class extends Cook4MeRecipeHubPanelV180{});
