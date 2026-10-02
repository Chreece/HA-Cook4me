// Product interaction lifecycle. Keep the existing save, lookup and tare APIs.
const WORDS={
 en:{manual:'Enter manually',waiting:'You can enter the product manually while the camera starts.'},
 de:{manual:'Manuell eingeben',waiting:'Du kannst das Produkt während des Kamerastarts manuell eingeben.'},
 el:{manual:'Χειροκίνητη εισαγωγή',waiting:'Μπορείς να συμπληρώσεις το προϊόν χειροκίνητα όσο ξεκινά η κάμερα.'}
};
const setText=(node,text)=>{if(node&&node.textContent!==text)node.textContent=text;};
export const MobileProductMixin=Base=>class extends Base{
 _v269Text(key){const lang=String(this._uiIngredientLanguage?.()||this._langCode?.()||'en').split(/[-_]/)[0];return (WORDS[lang]||WORDS.en)[key];}
 // enumerateDevices may wait on mobile. Opening a form must never depend on it;
 // the existing getUserMedia error path handles missing/denied cameras instead.
 _v180CameraCapability(){return Boolean(navigator.mediaDevices?.getUserMedia);}
 _v78Open(...args){
  if(this._v269OpenPromise)return this._v269OpenPromise;
  const pending=super._v78Open(...args);
  const job=Promise.resolve(pending).finally(()=>{if(this._v269OpenPromise===job)this._v269OpenPromise=null;});
  this._v269OpenPromise=job;
  return job;
 }
 async _v78Camera(...args){
  const c=this._v78Dialog,d=this._v78Draft;
  if(!c||!d||d.editorOpen||d.mode==='manual'||this._v180CameraUnavailable)return;
  // Paint after acquisition has marked itself pending, not after it resolves.
  const pending=super._v78Camera(...args);
  this._v141PaintBusy();
  try{return await pending;}
  finally{if(c===this._v78Dialog&&d===this._v78Draft)this._v141PaintBusy();}
 }
 _v141KeepCameraWarm(){
  if(this._v78Draft?.editorOpen||this._v78Draft?.mode==='manual')return;
  return super._v141KeepCameraWarm();
 }
 _v112Editor(open,...args){
  if(open&&!this._v78Busy&&!this._v78Submitted){this._v111CancelRead?.();this._v78StopCamera?.();}
  const result=super._v112Editor(open,...args);
  this._v141PaintBusy();return result;
 }
 _v141PaintBusy(){
  const c=this._v78Dialog,d=this._v78Draft,frame=c?.querySelector('[data-v111-frame]');
  if(!c||!d||!frame)return;
  c.classList.add('v269-responsive');c.classList.toggle('v269-editing',!!d.editorOpen);
  this._v269Styles();
  // The legacy full-frame overlay intercepted every touch during catalog,
  // price and camera loads, including touches on the manual form beneath it.
  const old=frame.querySelector('[data-v141-busy]');if(old)old.hidden=true;
  frame.classList.remove('v141-processing');
  const starting=!d.editorOpen&&d.mode!=='manual'&&!this._v180CameraUnavailable&&
   !this._v141CameraBlocked&&!this._v78Busy&&!this._v78Stream;
  const text=starting?this._v141Text('startingCamera'):(this._v141BusyState?.()||'');
  const header=c.querySelector(':scope > header > div')||c.querySelector(':scope > header');
  if(header){
   let status=header.querySelector('[data-v269-status]');
   if(!status){status=document.createElement('small');status.dataset.v269Status='';status.setAttribute('role','status');status.setAttribute('aria-live','polite');header.append(status);}
   setText(status,text);status.hidden=!text;
  }
  let startup=frame.querySelector('[data-v269-startup]');
  if(starting&&!startup){
   startup=document.createElement('div');startup.dataset.v269Startup='';startup.className='v269-startup';
   const ring=document.createElement('span');ring.className='v141-ring';ring.setAttribute('aria-hidden','true');
   const title=document.createElement('strong');title.dataset.v269Starting='';
   const note=document.createElement('small');note.dataset.v269Waiting='';
   const manual=document.createElement('button');manual.type='button';manual.className='btn';manual.dataset.v269Manual='';
   manual.onclick=event=>{event.stopPropagation();this._v180OpenManualFromFrame();};
   startup.append(ring,title,note,manual);frame.append(startup);
  }
  if(startup){
   startup.hidden=!starting;
   setText(startup.querySelector('[data-v269-starting]'),this._v141Text('startingCamera'));
   setText(startup.querySelector('[data-v269-waiting]'),this._v269Text('waiting'));
   setText(startup.querySelector('[data-v269-manual]'),this._v269Text('manual'));
  }
 }
 _v202CameraDecorate(){
  if(this._v78Draft?.editorOpen){
   // The normal-flow editor does not need video measurements on every input or
   // scale update. Reattach the camera resize observer when returning to scan.
   this._v202CameraDispose?.();this._v78Dialog?.classList.remove('v202-camera-live');return;
  }
  return super._v202CameraDecorate();
 }
 _v154DecorateProductContainer(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  this._v154MaybeLoadScale();this._v269Styles();
  const quantity=c.querySelector('main [data-draft="quantity"]')?.closest('.field, label');
  const unit=c.querySelector('main [data-draft="unit"]')?.closest('.field, label');
  if(!quantity||!unit)return;
  let row=quantity.closest('[data-v269-weight-row]');
  if(!row){
   row=document.createElement('div');row.dataset.v269WeightRow='';row.className='v78-fields v269-weight-row';
   quantity.before(row);row.append(quantity,unit);
  }
  let block=c.querySelector('[data-v154-container-field]');
  if(!block){
   block=document.createElement('div');block.dataset.v154ContainerField='';block.className='v154-container-block v269-scale-container';
   block.innerHTML='<label class="field"><span data-v269-container-label></span><select data-v154-container></select></label><label class="v154-deduct"><input type="checkbox" data-v154-deduct><span><strong data-v269-deduct-label></strong><small data-v269-deduct-help></small></span></label>';
  }
  if(row.nextElementSibling!==block)row.after(block);
  block.classList.add('v269-scale-container');block.hidden=!!d.unlimited;row.hidden=!!d.unlimited;
  const select=block.querySelector('[data-v154-container]'),check=block.querySelector('[data-v154-deduct]');
  const language=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  const signature=JSON.stringify([language,this._v154Containers().map(item=>[item.id,item.name,item.tareGrams]),d.containerId||'']);
  if(block._v269Options!==signature){
   // Change options only when their data changes. Keep the select itself alive
   // so Android's open native picker and keyboard focus are not discarded.
   select.innerHTML=this._v154ContainerOptions(d.containerId);
   block._v269Options=signature;
  }
  if(select.value!==String(d.containerId||''))select.value=String(d.containerId||'');
  check.checked=!!d.deductContainer;check.disabled=!d.containerId||!!this._v78Submitted||!!this._v78Busy;
  select.disabled=!!this._v78Submitted||!!this._v78Busy;
  setText(block.querySelector('[data-v269-container-label]'),this._v154Text('containerOptional'));
  setText(block.querySelector('[data-v269-deduct-label]'),this._v154Text('deduct'));
  setText(block.querySelector('[data-v269-deduct-help]'),this._v154Text('deductHelp'));
  if(block._v269Draft!==d){
   block._v269Draft=d;
   select.onchange=()=>{
    if(d!==this._v78Draft||this._v78Busy||this._v78Submitted)return;
    d.containerId=select.value;if(!d.containerId)d.deductContainer=false;
    d._v154ContainerTouched=true;this._v78Dirty=true;this._v154DecorateProductContainer();
   };
   check.onchange=()=>{if(d!==this._v78Draft||this._v78Busy||this._v78Submitted)return;d.deductContainer=check.checked;this._v78Dirty=true;};
  }
 }
 _v78RenderCapture(){
  const result=super._v78RenderCapture();
  this._v154DecorateProductContainer();this._v141PaintBusy();return result;
 }
 _v111Paint(){const result=super._v111Paint();this._v141PaintBusy();return result;}
 _v78Close(...args){
  const previous=this._v78Dialog,result=super._v78Close(...args);
  if(previous&&!this._v78Dialog)this._v269OpenPromise=null;
  return result;
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-ui-revision','269');return result;}
 _v269Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v269ProductStyles'))return;
  const style=document.createElement('style');style.id='v269ProductStyles';style.textContent=`
   .v269-responsive [data-v141-busy]{display:none!important}
   [data-v269-status]{display:block;margin-top:5px;color:var(--secondary-text-color);font-size:.85rem;line-height:1.35}
   .v269-startup{position:absolute;inset:20% 12px auto;z-index:8;display:flex;flex-direction:column;align-items:center;gap:12px;padding:22px;border-radius:16px;background:var(--card-background-color,#172328);color:var(--primary-text-color,#fff);text-align:center;pointer-events:none}
   .v269-startup small{max-width:38ch;line-height:1.4}.v269-startup button{pointer-events:auto;min-height:46px}
   .v269-startup .v141-ring{width:32px;height:32px;border-width:3px;border-color:var(--divider-color);border-top-color:var(--primary-color)}
   .v112-editor .v269-weight-row{grid-column:1 / -1;grid-template-columns:minmax(0,1fr) minmax(0,1fr);width:100%;min-width:0}
   .v112-editor .v269-scale-container{grid-column:1 / -1;min-width:0;width:100%;box-sizing:border-box;margin:0 0 8px!important;padding:0!important;border:0!important}
   .v112-editor .v269-scale-container .field{margin:0}
   .v269-responsive input,.v269-responsive select,.v269-responsive button{touch-action:manipulation}
  `;this.shadowRoot.append(style);
 }
};
