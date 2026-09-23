// Receipt photo import belongs to the product launcher, not product editing.
export function receiptPhotoAvailable(state,hass){
 const selected=state?.aiEntityId||state?.defaultAiEntityId;
 if(!selected||!Array.isArray(state?.aiChoices)||!state.aiChoices.some(row=>row.id===selected))return false;
 // The server list is permission-filtered. Check live availability when present;
 // the recognition endpoint rechecks permissions before sending any photo.
 return !['unavailable','unknown'].includes(hass?.states?.[selected]?.state);
}
export const ReceiptLauncherMixin=Base=>class extends Base{
 _r199CanPhoto(){return receiptPhotoAvailable(this._v78State,this._hass);}
 _r199Launch(root=this.shadowRoot?.querySelector('[data-v78-kitchen]')){
  if(!root)return;
  let label=root.querySelector('[data-r199-receipt-photo]');
  const add=root.querySelector('.v78-launch [data-v78-open="barcode"]')||root.querySelector('[data-v78-open="barcode"]');
  if(!add||!this._r199CanPhoto()){label?.remove();return;}
  if(!label){
   label=document.createElement('label');label.dataset.r199ReceiptPhoto='';label.className='btn secondary r199-receipt-photo';
   const text=document.createElement('span'),input=document.createElement('input');
   text.textContent=this._r195Text('upload');input.type='file';input.accept='image/*';input.dataset.r199ReceiptFile='';
   input.setAttribute('aria-label',this._r195Text('upload'));input.title=this._r195Text('photoPrivacy');
   label.append(text,input);add.after(label);
   const context=this._prefKey();
   input.onchange=event=>{const file=event.target.files?.[0];event.target.value='';if(file&&context===this._prefKey())void this._r199ReceiptPhoto(file);};
  }
  label.querySelector('span').textContent=this._r195Text('upload');
  label.querySelector('input').disabled=!!this._r199Uploading||!!this._v78Busy;
  if(!this.shadowRoot.querySelector('#r199Styles')){
   const style=document.createElement('style');style.id='r199Styles';style.textContent=`
    .r199-receipt-photo{position:relative;display:inline-flex;align-items:center;justify-content:center;overflow:hidden;cursor:pointer;min-height:44px;box-sizing:border-box;max-width:100%;white-space:normal!important;word-break:normal;overflow-wrap:break-word}
    .r199-receipt-photo input{position:absolute;inset:0;opacity:0;width:100%;height:100%;cursor:pointer}.r199-receipt-photo:focus-within{outline:2px solid var(--primary-color);outline-offset:3px}
    [data-r199-photo-privacy]{display:block;font-size:.8rem;line-height:1.4;padding:8px;max-width:100%;white-space:normal;word-break:normal}
   `;this.shadowRoot.append(style);
  }
 }
 async _r199ReceiptPhoto(file){
  if(!file||this._r199Uploading||this._v78Busy||this._v78Submitted)return;
  if(!this._r199CanPhoto()){this._message(this._v78Text('noAi'),true);return;}
  const context=this._prefKey();this._r199Uploading=true;
  try{
   await this._v78Open('manual');
   if(context!==this._prefKey()||!this._v78Dialog||!this._r199CanPhoto())return;
   await this._r195Start(true,false);
   if(context===this._prefKey()&&this._v78Draft?.mode==='receipt')await this._v78Photo(file);
  }catch(error){if(context===this._prefKey())this._message(String(error.message||error),true);}
  finally{this._r199Uploading=false;this._r199Launch();}
 }
 _r199CameraReceipt(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  const button=c.querySelector('[data-v80-scan="receipt"]'),nutrients=c.querySelector('[data-v80-scan="nutrition"]');
  if(button){
   if(nutrients&&nutrients.nextElementSibling!==button)nutrients.after(button);
   button.hidden=!this._r199CanPhoto()||!!this._v180CameraUnavailable;
   button.disabled=!!this._v78Busy||!!this._v78Submitted||!!(this._r195Session&&this._r195Current()?.status!=='pending');
   button.setAttribute('aria-pressed',String(d.mode==='receipt'));
  }
  let note=c.querySelector('[data-r199-photo-privacy]');
  if(d.mode==='receipt'){
   if(!note){note=document.createElement('small');note.dataset.r199PhotoPrivacy='';c.querySelector('[data-v111-guide-wrap]')?.append(note);}
   note.textContent=this._r195Text('photoPrivacy');
  }else note?.remove();
 }
 async _v80Scan(mode){
  if(mode==='receipt'){
   if(!this._r199CanPhoto()){this._v78SetStatus(this._v78Text('noAi'));return;}
   if(this._v78Busy||this._v78Submitted)return;
   if(this._v78Draft?.mode==='receipt'&&this._v78Draft?.scanPhase==='scanning'&&this._v78Stream)return this._v78CaptureFrame();
  }
  return super._v80Scan(mode);
 }
 _renderProfile(c){const result=super._renderProfile(c);this._r199Launch(c);return result;}
 _v78AcceptState(state){const result=super._v78AcceptState(state);this._r199Launch();this._r199CameraReceipt();return result;}
 _updateHeader(){const result=super._updateHeader();this._r199Launch();this._r199CameraReceipt();return result;}
 _v78RenderCapture(){const result=super._v78RenderCapture();this._r199CameraReceipt();return result;}
 _v111Paint(){const result=super._v111Paint();this._r199CameraReceipt();return result;}
};
