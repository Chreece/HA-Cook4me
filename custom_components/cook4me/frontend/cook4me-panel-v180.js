const V179='cook4me-recipe-hub-panel-v179';
if(!customElements.get(V179))await import('./cook4me-panel-v179.js?v=2026.9.22.6');
const BasePanel=customElements.get(V179);

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
  d.mode='manual';
  d.editorOpen=true;
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
   if(!d.editorOpen){d.mode='manual';d.editorOpen=true;this._v111Paint?.();}
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
 _v180IngredientLabel(row){
  if(!row||typeof row!=='object')return String(row??'');
  const clean=value=>String(value??'').trim();
  const same=(a,b)=>clean(a)&&clean(b)&&clean(a).localeCompare(clean(b),undefined,{sensitivity:'base'})===0;
  const key=this._v140IngredientKey?.(row)||clean(row.key||row.ingredientId||row.id||row.foodKey)||(clean(row.identity).startsWith('k:')?clean(row.identity).slice(2):'');
  const uiRow=this._v112Local?.({...row,...(key?{key}:{})})||row;
  const ui=clean(row.uiName||uiRow?.name||uiRow?.foodName||row.name||row.foodName||row.identity);
  const uiLanguage=clean(this._uiIngredientLanguage?.()||this._langCode?.()||'en').toLowerCase();
  const marketLanguage=clean(this._v140SupermarketLanguage?.()||'').toLowerCase();
  const market=marketLanguage&&marketLanguage!==uiLanguage?clean(row.supermarketName||this._v140MarketNames?.get(key)||''):'';
  const original=clean(row.originalName||row.recipeName||row.sourceName||row.name||row.foodName||row.identity);
  const parts=[ui||market||original];
  for(const candidate of [market,original]){
   if(!candidate||parts.some(value=>same(value,candidate)))continue;
   parts.push(candidate);
  }
  return parts[0]+parts.slice(1).map(value=>` (${value})`).join('');
 }
 _v110Disclosure(kind,rows,empty,extra=''){
  const e=value=>this._escape(String(value));
  return `<details data-week-disclosure="${kind}"><summary>${e(this._v110Text(kind==='stock'?'covered':'buy'))} (${rows.length})</summary>${rows.length?rows.map(row=>`<div class="rx-list-row"><strong>${e(this._v180IngredientLabel(row))}</strong> · ${e(this._displayAmount(row.quantity,row.unit))}${kind==='stock'?` ${e(this._t('required'))} · ${row.unlimited?'∞':e(this._displayAmount(row.available,row.unit))} ${e(this._t('available'))}`:''}</div>`).join(''):`<p class="muted">${e(this._v110Text(empty))}</p>`}${extra}</details>`;
 }
 _shoppingDeltaHtml(){
  const rows=this._weekState?.shoppingDelta||[],unknown=this._weekState?.reservations?.unknown||[],e=value=>this._escape(String(value));
  const extra=unknown.length?`<p class="muted">${e(this._v110Text('unknown'))}</p>${unknown.map(row=>`<div class="rx-list-row" data-week-stock-unknown><strong>${e(this._v180IngredientLabel(row))}</strong> · ${e(this._displayAmount(row.quantity,row.unit))} ${e(this._t('required'))}</div>`).join('')}`:'';
  return this._v110Disclosure('shopping',rows,'emptyBuy',extra);
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
  this.setAttribute('data-cook4me-build','2026.9.22.8');
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
customElements.define('cook4me-recipe-hub-panel-v180',Cook4MeRecipeHubPanelV180);
