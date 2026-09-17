import './cook4me-panel-v110.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v110');
const MODES=[['barcode','barcode-scan'],['date','calendar-clock'],['nutrition','nutrition'],['product','creation']];
const NUTRIENTS=['energyKcal','protein','carbohydrates','fat','saturatedFat','fiber','sugars','salt'];
const WORDS={
 en:{barcode:'Keep the barcode inside the guide',date:'Frame the best-before or use-by date',nutrition:'Frame the nutrition table, including its 100 g / ml heading',product:'Frame the product and its name',capture:'Capture this label',looking:'Looking up product…',reading:'Reading the label…',recognized:'Product recognized',unknown:'Product not recognized',read:'Label recognized',noData:'No readable information found',again:'Tap the camera to scan again',apply:'Apply · add to stock',amount:'Amount',type:'Enter barcode',mapped:'Ingredient',choose:'Choose the matching ingredient below',saved:'Added to stock',saving:'Adding to stock…',retry:'Retry the same save',camera:'Start camera',stop:'Stop camera',photo:'Choose a photo',all:'available ingredients',error:'Could not recognize this scan',review:'Review the product details',needProduct:'These details will be attached to this product',resume:'Return to scanning'},
 de:{barcode:'Barcode innerhalb der Markierung halten',date:'Mindesthaltbarkeits- oder Verbrauchsdatum einrahmen',nutrition:'Nährwerttabelle mit der Angabe pro 100 g / ml einrahmen',product:'Produkt und Produktname einrahmen',capture:'Dieses Etikett aufnehmen',looking:'Produkt wird gesucht…',reading:'Etikett wird gelesen…',recognized:'Produkt erkannt',unknown:'Produkt nicht erkannt',read:'Etikett erkannt',noData:'Keine lesbaren Angaben gefunden',again:'Zum erneuten Scannen auf das Kamerabild tippen',apply:'Übernehmen · zum Vorrat',amount:'Menge',type:'Barcode eingeben',mapped:'Zutat',choose:'Passende Zutat unten auswählen',saved:'Zum Vorrat hinzugefügt',saving:'Wird zum Vorrat hinzugefügt…',retry:'Speichern erneut versuchen',camera:'Kamera starten',stop:'Kamera stoppen',photo:'Foto auswählen',all:'verfügbare Zutaten',error:'Scan konnte nicht erkannt werden',review:'Produktangaben prüfen',needProduct:'Diese Angaben werden diesem Produkt zugeordnet',resume:'Zurück zum Scannen'},
 el:{barcode:'Κράτησε τον barcode μέσα στο πλαίσιο',date:'Βάλε την ημερομηνία λήξης μέσα στο πλαίσιο',nutrition:'Βάλε τον πίνακα θρεπτικών μαζί με την ένδειξη ανά 100 g / ml στο πλαίσιο',product:'Βάλε το προϊόν και την ονομασία του μέσα στο πλαίσιο',capture:'Λήψη αυτής της ετικέτας',looking:'Αναζήτηση προϊόντος…',reading:'Ανάγνωση ετικέτας…',recognized:'Το προϊόν αναγνωρίστηκε',unknown:'Το προϊόν δεν αναγνωρίστηκε',read:'Η ετικέτα αναγνωρίστηκε',noData:'Δεν βρέθηκαν αναγνώσιμα στοιχεία',again:'Πάτησε την κάμερα για νέα σάρωση',apply:'Εφαρμογή · προσθήκη στο απόθεμα',amount:'Ποσότητα',type:'Εισαγωγή barcode',mapped:'Υλικό',choose:'Επίλεξε το αντίστοιχο υλικό παρακάτω',saved:'Προστέθηκε στο απόθεμα',saving:'Προσθήκη στο απόθεμα…',retry:'Επανάληψη της ίδιας αποθήκευσης',camera:'Έναρξη κάμερας',stop:'Διακοπή κάμερας',photo:'Επιλογή φωτογραφίας',all:'διαθέσιμα υλικά',error:'Δεν ήταν δυνατή η αναγνώριση',review:'Έλεγξε τα στοιχεία του προϊόντος',needProduct:'Τα στοιχεία θα συνδεθούν με αυτό το προϊόν',resume:'Επιστροφή στη σάρωση'}
};
class Cook4MeRecipeHubPanelV111 extends BasePanel{
 _v111Text(key){return (WORDS[this._uiIngredientLanguage()]||WORDS.en)[key]||key;}
 _v78Fresh(mode){return {...super._v78Fresh(mode),scanPhase:'idle',scanRecognized:false,scanApplied:false,scanNote:'',scanNewProduct:false,labelNutrition:false};}
 async _v78Open(mode='barcode'){
  const opening=super._v78Open(mode),c=this._v78Dialog;
  if(mode!=='manual')void this._v80Scan(mode);
  await opening;
  if(this._v78Alive(c)&&this._ingredientCatalogLanguage!==this._uiIngredientLanguage())await this._loadIngredientCatalog();
 }
 _v78StopCamera(){
  // Form/price/catalog refreshes must not terminate the capture session.
  if(this._v111Rendering)return;
  this._v111ScanToken={};super._v78StopCamera();
  const d=this._v78Draft;if(d?.scanPhase==='scanning')d.scanPhase='idle';
  this._v111Paint();
 }
 _v78Close(force=false){super._v78Close(force);if(!this._v78Dialog){this._v111ReadToken={};this._v111Video=null;}}
 _v78RenderCapture(){
  const c=this._v78Dialog;if(!c)return;
  const video=c.querySelector('video')||this._v111Video;
  this._v111Rendering=true;
  try{super._v78RenderCapture();}finally{this._v111Rendering=false;}
  if(!this._v78Alive(c)||!this._v78Draft)return;
  this._v111Styles();this._v111BuildFrame(video);
  c.querySelectorAll('main [data-draft],main [data-nutrient],[data-v78-basis],[data-v78-ingredient]').forEach(el=>{const paint=()=>{if(el.matches('[data-nutrient],[data-v78-basis]'))this._v78Draft.labelNutrition=true;this._v111Paint();};el.addEventListener('input',paint);el.addEventListener('change',paint);});
  this._v78IngredientOptions();this._v78SetBusy(!!this._v78Busy);
 }
 _buttonIcon(button){return button.closest?.('.v111-camera')?null:super._buttonIcon(button);}
 _v111Icon(action,icon,label,extra=''){return `<button type="button" class="v111-icon" ${action} title="${this._escape(label)}" aria-label="${this._escape(label)}" ${extra}><ha-icon icon="mdi:${icon}" aria-hidden="true"></ha-icon></button>`;}
 _v111BuildFrame(video){
  const c=this._v78Dialog,d=this._v78Draft,tools=c?.querySelector('.v78-capture-tools');if(!tools||!d)return;
  const e=value=>this._escape(String(value??'')),t=key=>e(this._v111Text(key)),icon=(action,name,key)=>this._v111Icon(action,name,this._v111Text(key));
  tools.innerHTML=`<div class="v78-viewfinder v111-camera" data-v111-frame>
   <video autoplay playsinline muted></video>
   <div class="v111-modes" role="group" aria-label="${e(this._v80Text('scanner'))}">${MODES.map(([mode,name])=>this._v111Icon(`data-v80-scan="${mode}"`,name,this._v80Text(mode),`aria-pressed="${d.mode===mode}"`)).join('')}${icon('data-v111-power','camera-off-outline','stop')}</div>
   <div class="v111-guide-wrap" data-v111-guide-wrap><p data-v111-instruction></p><div class="v111-guide" data-v111-guide><span></span><span></span><span></span><span></span><div class="v111-table-lines" aria-hidden="true"></div></div><small data-v111-target></small></div>
   <div class="v111-result" data-v111-result role="status" aria-live="polite" hidden></div>
   <div class="v111-code" data-v111-code-wrap hidden><label>${e(this._v78Text('barcode'))}<input data-draft="barcode" inputmode="numeric" autocomplete="off" value="${e(d.barcode)}"></label>${this._v111Icon('data-v78-lookup','magnify',this._v78Text('lookup'))}</div>
   <div class="v111-bottom">${icon('data-v111-type','keyboard-outline','type')}<label class="v111-icon v111-file" title="${t('photo')}" aria-label="${t('photo')}"><ha-icon icon="mdi:image-plus" aria-hidden="true"></ha-icon><input data-v78-file type="file" accept="image/*" capture="environment" aria-label="${t('photo')}"></label>${icon('data-v78-take','camera-iris','capture')}${this._nativeBarcodeScannerAvailable?.()?this._v111Icon('data-v78-native','cellphone',this._v78Text('native')):''}${icon('data-v78-camera','camera-outline','camera')}</div>
  </div><p class="muted v111-photo-help">${e(this._v78Text('photoHelp'))}</p>`;
  const frame=tools.querySelector('[data-v111-frame]');
  if(video&&this._v78Stream){frame.querySelector('video').replaceWith(video);video.srcObject=this._v78Stream;void video.play().catch(()=>{});}
  this._v111Video=frame.querySelector('video');
  frame.onclick=event=>{if(!event.target.closest('button,input,select,label,a'))void this._v111Resume();};
  frame.querySelectorAll('[data-v80-scan]').forEach(button=>button.onclick=()=>void this._v80Scan(button.dataset.v80Scan));
  frame.querySelector('[data-v111-power]').onclick=()=>{if(this._v78Stream||this._v80CameraPending)this._v78StopCamera();else void this._v78Camera();};
  frame.querySelector('[data-v78-camera]').onclick=()=>void this._v111Resume();
  frame.querySelector('[data-v78-take]').onclick=()=>void this._v78CaptureFrame();
  frame.querySelector('[data-v111-type]').onclick=()=>{const area=frame.querySelector('[data-v111-code-wrap]');area.hidden=!area.hidden;if(!area.hidden)area.querySelector('input').focus();};
  frame.querySelector('[data-v78-lookup]').onclick=()=>void this._v78Lookup(frame.querySelector('[data-draft=barcode]').value);
  frame.querySelector('[data-draft=barcode]').onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();void this._v78Lookup(event.target.value);}};
  frame.querySelector('[data-v78-file]').onchange=event=>{const file=event.target.files?.[0];event.target.value='';if(file)void this._v78Photo(file);};
  frame.querySelector('[data-v78-native]')?.addEventListener('click',()=>{this._scannerOpen=true;void this._startNativeBarcodeScanner(c);});
  this._v111Paint();
 }
 _v111Paint(){
  const c=this._v78Dialog,d=this._v78Draft,frame=c?.querySelector('[data-v111-frame]');if(!d||!frame)return;
  const mode=MODES.some(([key])=>key===d.mode)?d.mode:'product',phase=d.scanPhase||'idle',live=!!this._v78Stream;
  frame.dataset.mode=mode;frame.dataset.phase=phase;frame.classList.toggle('v111-live',live);
  frame.querySelectorAll('[data-v80-scan]').forEach(b=>{b.setAttribute('aria-pressed',String(b.dataset.v80Scan===mode));b.disabled=!!this._v78Busy||!!this._v78Submitted&&!d.scanApplied;});
  const power=frame.querySelector('[data-v111-power]');power.title=power.ariaLabel=this._v111Text(live?'stop':'camera');power.querySelector('ha-icon').setAttribute('icon',live?'mdi:camera-off-outline':'mdi:camera-outline');
  frame.querySelector('[data-v111-instruction]').textContent=this._v111Text(mode);
  frame.querySelector('[data-v111-target]').textContent=['date','nutrition'].includes(mode)&&d.productName?`${this._v111Text('needProduct')}: ${d.productName}`:'';
  const result=frame.querySelector('[data-v111-result]'),show=['looking','reading','recognized','notfound','error','saving','saved'].includes(phase);
  frame.querySelector('[data-v111-guide-wrap]').hidden=show;result.hidden=!show;
  const e=value=>this._escape(String(value??''));
  if(show){
   const spinning=['looking','reading','saving'].includes(phase),success=['recognized','saved'].includes(phase),title=phase==='recognized'?(mode==='barcode'||mode==='product'?'recognized':'read'):phase==='notfound'?(mode==='barcode'||mode==='product'?'unknown':'noData'):phase;
   const hasProduct=!!(d.scanRecognized||d.productName||d.ingredient);
   const nutrition=d.nutrition||{},values=nutrition.values||{};
   const details=[d.bestBefore?`<div><strong>${e(this._v78Text('date'))}</strong> ${e(d.bestBefore)}</div>`:'',Object.keys(values).length?`<div class="v111-nutrients"><strong>${e(this._v78Text('basis'))} ${e(this._displayUnit(nutrition.basisUnit))}</strong>${NUTRIENTS.filter(key=>values[key]!==undefined&&values[key]!==null&&values[key]!=='').map(key=>`<span>${e(this._t(key==='energyKcal'?'energy':key==='carbohydrates'?'carbs':key))}: ${e(values[key])} ${key==='energyKcal'?'kcal':e(this._displayUnit('g'))}</span>`).join('')}</div>`:''].join('');
   result.innerHTML=`<div class="v111-result-heading">${spinning?'<span class="v111-spinner" aria-hidden="true"></span>':`<ha-icon class="${success?'v111-ok':'v111-warning'}" icon="mdi:${success?'check-circle-outline':'alert-circle-outline'}" aria-hidden="true"></ha-icon>`}<strong>${e(this._v111Text(title))}</strong></div>${d.productName?`<h3>${e(d.productName)}</h3>`:''}${d.scanNote?`<p>${e(d.scanNote)}</p>`:''}${!spinning?`<div class="v111-facts">${details}${hasProduct?`<div>${e(this._v111Text('mapped'))}: ${e(d.ingredient?.name||this._v111Text('choose'))}</div>`:''}</div>`:''}${!spinning&&hasProduct?`<div class="v111-amount"><label>${e(this._v111Text('amount'))}<input data-v111-amount type="number" min="0.000001" step="any" value="${e(d.quantity)}" ${this._v78Submitted?'disabled':''}></label>${this._unitInput(d.unit,'data-v111-unit aria-label="'+e(this._t('unit'))+'" '+(this._v78Submitted?'disabled':''))}${this._v111Icon('data-v111-apply','check',this._v111Text(this._v78Submitted&&!d.scanApplied?'retry':'apply'),d.scanApplied?'disabled':'')}</div><label class="v111-place">${e(this._v78Text('places'))}<select data-v111-place ${this._v78Submitted?'disabled':''}>${this._v78PlaceOptions(d.storageLocationId)}</select></label>`:''}<small>${e(this._v111Text('again'))}</small>`;
   const update=(key,value)=>{d[key]=value;this._v78Dirty=true;const field=c.querySelector(`main [data-draft="${key}"]`);if(field)field.value=value;this._v79SchedulePrice();};
   result.querySelector('[data-v111-amount]')?.addEventListener('input',event=>update('quantity',event.target.value));
   result.querySelector('[data-v111-unit]')?.addEventListener('input',event=>update('unit',event.target.value));
   result.querySelector('[data-v111-place]')?.addEventListener('change',event=>update('storageLocationId',event.target.value));
   result.querySelector('[data-v111-apply]')?.addEventListener('click',()=>void this._v78Save());
  }
  frame.querySelector('[data-v78-camera]').hidden=live;
  const take=frame.querySelector('[data-v78-take]');take.hidden=mode==='barcode'||show;take.disabled=!live||!!this._v78Busy;
  for(const node of frame.querySelectorAll('[data-v78-file],[data-v78-lookup],[data-draft=barcode],[data-v78-native]'))node.disabled=!!this._v78Busy||!!this._v78Submitted&&!d.scanApplied;
  const status=c.querySelector('[data-v78-status]');if(status)status.textContent=this._v78Status||'';
 }
 _v78SetStatus(text){super._v78SetStatus(text);this._v111Paint();}
 _v78SetBusy(busy){
  super._v78SetBusy(busy);const c=this._v78Dialog;if(!c)return;
  const tools=c.querySelector('.v78-capture-tools');if(tools)tools.disabled=false;
  if(this._v78Draft?.scanApplied)c.querySelectorAll('[data-v78-save]').forEach(b=>b.disabled=true);
  this._v111Paint();
 }
 _v111CancelRead(){this._v111ReadToken={};this._v111ScanToken={};this._v80ScanToken={};clearTimeout(this._v78CameraTimer);}
 _v111NewDraft(mode){
  const old=this._v78Draft;this._v111CancelRead();this._v78Draft=this._v78Fresh(mode);this._v78Draft.storageLocationId=old?.storageLocationId||'';
  this._v78Submitted=null;this._v78Saved=false;this._v78Dirty=false;this._v78Status='';this._v78Busy=false;this._v78RenderCapture();return this._v78Draft;
 }
 async _v111Resume(){
  let d=this._v78Draft;if(!d||this._v78Submitted&&!d.scanApplied)return;
  if(d.scanApplied)d=this._v111NewDraft(d.mode);
  this._v111CancelRead();this._v78SetBusy(false);d.scanPhase='scanning';d.scanNote='';
  if(['barcode','product'].includes(d.mode))d.scanNewProduct=!!(d.scanRecognized||d.productName);
  await this._v78Camera();if(this._v78Draft===d&&this._v78Stream&&d.mode==='barcode')this._v80BarcodeLoop(this._v78Dialog);
  this._v111Paint();
 }
 async _v78Camera(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d||this._v80CameraPending)return;
  if(this._v78Stream?.getVideoTracks().some(track=>track.readyState==='live')){this._v111Paint();return;}
  const token={};this._v78CameraToken=token;this._v80CameraPending=true;this._v78SetStatus(this._v80Text('starting'));
  try{
   if(!navigator.mediaDevices?.getUserMedia)throw new Error(this._v78Text('cameraHelp'));
   const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});
   if(!this._v78Alive(c)||this._v78CameraToken!==token){stream.getTracks().forEach(track=>track.stop());return;}
   this._v78Stream=stream;const video=c.querySelector('video');video.srcObject=stream;await video.play();
   if(!this._v78Alive(c)||this._v78CameraToken!==token)return;
   const current=this._v78Draft;if(current?.scanPhase==='idle')current.scanPhase='scanning';this._v78SetStatus('');
   if(current?.mode==='barcode'&&current.scanPhase==='scanning')void this._v80BarcodeLoop(c);
  }catch(error){if(this._v78Alive(c)&&this._v78CameraToken===token){this._v78StopCamera();d.scanNote=`${this._v78Text('cameraHelp')} ${error.message||error}`;d.scanPhase='error';}}
  finally{if(this._v78CameraToken===token)this._v80CameraPending=false;this._v111Paint();}
 }
 async _v80Scan(mode){
  let d=this._v78Draft;const c=this._v78Dialog;if(!c||!d||this._v78Busy||!MODES.some(([key])=>key===mode)||this._v78Submitted&&!d.scanApplied)return;
  if(d.scanApplied)d=this._v111NewDraft(mode);
  const captureAgain=d.mode===mode&&d.scanPhase==='scanning'&&!!this._v78Stream;
  this._v111CancelRead();d.mode=mode;d.scanPhase='scanning';d.scanNote='';
  if(mode==='product'||mode==='barcode')d.scanNewProduct=!!(d.scanRecognized||d.productName);
  this._v111Paint();await this._v78Camera();if(!this._v78Alive(c)||d!==this._v78Draft)return;
  if(mode==='barcode'){this._v80BarcodeLoop(c);return;}
  if(captureAgain)await this._v78CaptureFrame();
 }
 _v111Canvas(crop=true){
  const c=this._v78Dialog,video=c?.querySelector('video');if(!video?.videoWidth)return null;
  let x=0,y=0,w=video.videoWidth,h=video.videoHeight;
  const frame=c.querySelector('[data-v111-frame]')?.getBoundingClientRect(),guide=c.querySelector('[data-v111-guide]')?.getBoundingClientRect();
  if(crop&&frame?.width&&guide?.width){const scale=Math.max(frame.width/w,frame.height/h);x=Math.max(0,(w-frame.width/scale)/2+(guide.left-frame.left)/scale);y=Math.max(0,(h-frame.height/scale)/2+(guide.top-frame.top)/scale);w=Math.min(w-x,guide.width/scale);h=Math.min(h-y,guide.height/scale);}
  const canvas=document.createElement('canvas'),scale=Math.min(1,1600/Math.max(w,h));canvas.width=Math.max(1,Math.round(w*scale));canvas.height=Math.max(1,Math.round(h*scale));canvas.getContext('2d').drawImage(video,x,y,w,h,0,0,canvas.width,canvas.height);return canvas;
 }
 async _v111Detector(){
  if(typeof globalThis.BarcodeDetector!=='function')throw new Error(this._v80Text('barcodeHelp'));
  let formats=['ean_13','ean_8','upc_a','upc_e','itf'];
  if(BarcodeDetector.getSupportedFormats){const supported=await BarcodeDetector.getSupportedFormats();formats=formats.filter(format=>supported.includes(format));}
  if(!formats.length)throw new Error(this._v80Text('barcodeHelp'));
  return new BarcodeDetector({formats});
 }
 async _v80BarcodeLoop(c){
  const d=this._v78Draft,token={};this._v111ScanToken=token;clearTimeout(this._v78CameraTimer);
  const active=()=>this._v78Alive(c)&&this._v78Draft===d&&this._v111ScanToken===token&&this._v78Stream&&d.mode==='barcode'&&d.scanPhase==='scanning';
  let detector;try{detector=await this._v111Detector();}catch(error){if(active()){this._v78SetStatus(String(error.message||error));c.querySelector('[data-v111-code-wrap]').hidden=false;}return;}
  const loop=async()=>{if(!active())return;try{const canvas=this._v111Canvas();const codes=canvas?await detector.detect(canvas):[];if(!active())return;if(codes?.[0]?.rawValue){await this._v78Lookup(codes[0].rawValue);return;}}catch{}if(active())this._v78CameraTimer=setTimeout(loop,300);};void loop();
 }
 async _v78CaptureFrame(){const d=this._v78Draft;if(!d||this._v78Busy||this._v78Submitted||d.mode==='barcode')return;const canvas=this._v111Canvas();if(canvas)await this._v78Recognize(canvas.toDataURL('image/jpeg',.88));}
 async _v78Photo(file){
  const c=this._v78Dialog;if(!c||this._v78Busy||this._v78Submitted)return;const token={};this._v111CancelRead();this._v111ReadToken=token;this._v78SetBusy(true);let bitmap;
  try{
   if(file.size>20_000_000)throw new Error('Choose a photo smaller than 20 MB');bitmap=await createImageBitmap(file);
   if(!this._v78Alive(c)||this._v111ReadToken!==token)return;if(bitmap.width*bitmap.height>40_000_000)throw new Error('Choose a smaller photo');
   if(this._v78Draft.mode==='barcode'){
    const detector=await this._v111Detector(),codes=await detector.detect(bitmap);
    if(!this._v78Alive(c)||this._v111ReadToken!==token)return;if(!codes?.[0]?.rawValue)throw new Error(this._v78Text('barcodeMissing'));
    this._v78SetBusy(false);await this._v78Lookup(codes[0].rawValue);return;
   }
   const canvas=document.createElement('canvas'),scale=Math.min(1,1600/Math.max(bitmap.width,bitmap.height));canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);
   this._v78SetBusy(false);if(this._v78Draft.mode==='manual')this._v78Draft.mode='product';await this._v78Recognize(canvas.toDataURL('image/jpeg',.88));
  }catch(error){if(this._v78Alive(c)&&this._v111ReadToken===token){this._v78Draft.scanPhase='error';this._v78Draft.scanNote=String(error.message||error);}}
  finally{bitmap?.close?.();if(this._v78Alive(c)&&this._v111ReadToken===token)this._v78SetBusy(false);}
 }
 async _v78Lookup(code){
  const c=this._v78Dialog;let d=this._v78Draft;if(!c||!d||this._v78Busy||this._v78Submitted&&!d.scanApplied)return;
  code=String(code||'').trim();if(!code)return;
  if(d.scanApplied||d.scanNewProduct||d.barcode&&d.barcode!==code||d.scanRecognized&&!d.barcode)d=this._v111NewDraft('barcode');
  this._v111CancelRead();const token={};this._v111ReadToken=token;d.mode='barcode';d.barcode=code;d.scanPhase='looking';d.scanNote='';this._v78SetBusy(true);
  const active=()=>this._v78Alive(c)&&this._v78Draft===d&&this._v111ReadToken===token;
  try{
   const result=await this._api('cook4me/v33/barcode_lookup',{entry_id:this._entryId,barcode:code,language:this._uiIngredientLanguage()});if(!active())return;
   const resolved=String(result.barcode||code);d.barcode=resolved;
   const p=result.product||{},m=result.mapping||{},name=p.productName||p.genericName||(p.name!==resolved?p.name:'')||m.productName||m.ingredient?.name||'';
   d.productName=name;d.brand=p.brand||m.brand||'';d.quantity=p.quantity??m.quantity??'';d.unit=p.unit||m.unit||d.unit||'g';
   d.ingredient=m.ingredient||result.match?.ingredient||null;d.suggestions=result.suggestions||[];d.query='';
   const n=p.nutrition||m.nutrition;if(n?.basisUnit&&Object.keys(n.values||{}).length&&!d.labelNutrition)d.nutrition=structuredClone(n);
   d.scanRecognized=!!(name&&(p.found!==false||m.productName||m.ingredient));d.scanPhase=d.scanRecognized?'recognized':'notfound';d.scanNewProduct=false;this._v78Dirty=true;this._v78Status='';
  }catch(error){if(active()){d.scanPhase='error';d.scanNote=String(error.message||error);}}
  finally{if(active()){this._v78Busy=false;this._v78RenderCapture();}}
 }
 async _v78Recognize(image){
  const c=this._v78Dialog;let d=this._v78Draft;if(!c||!d||this._v78Busy||this._v78Submitted)return;
  if(d.mode==='product'&&d.scanNewProduct)d=this._v111NewDraft('product');
  this._v111CancelRead();const token={};this._v111ReadToken=token;const mode=d.mode;d.scanPhase='reading';d.scanNote='';this._v78SetBusy(true);
  const active=()=>this._v78Alive(c)&&this._v78Draft===d&&this._v111ReadToken===token;
  try{
   const result=await this._api('cook4me/v33/recognize_photo',{entry_id:this._entryId,image,mode,language:this._uiIngredientLanguage()});if(!active())return;
   const p=result.product||{};let found=false;
   if(mode==='date'&&p.bestBefore){d.bestBefore=p.bestBefore;found=true;}
   else if(mode==='nutrition'&&p.nutrition?.basisUnit&&Object.keys(p.nutrition.values||{}).length){d.nutrition=structuredClone(p.nutrition);d.labelNutrition=true;found=true;}
   else if(mode==='product'){
    for(const key of ['productName','brand','quantity','unit'])if(p[key]!==undefined&&p[key]!==null&&p[key]!=='')d[key]=p[key];
    d.suggestions=result.suggestions||[];d.ingredient=result.match?.ingredient||null;d.query='';found=!!d.productName;d.scanRecognized=found;d.scanNewProduct=false;
   }
   d.scanPhase=found?'recognized':'notfound';d.scanNote=p.note||'';this._v78Dirty=true;this._v78Status='';
  }catch(error){if(active()){d.scanPhase='error';d.scanNote=String(error.message||error);}}
  finally{if(active()){this._v78Busy=false;this._v78RenderCapture();}}
 }
 _v78IngredientOptions(){
  const c=this._v78Dialog,d=this._v78Draft,select=c?.querySelector('[data-v78-ingredient]');if(!select||!d)return;
  const normalize=row=>row?.name?{...row,key:row.key||row.ingredientId||row.id}:null,map=new Map();
  for(const raw of [...(this._ingredientCatalog||[]),d.ingredient,...(d.suggestions||[]).map(s=>s.ingredient)]){const row=normalize(raw);if(row){const id=this._scanIngredientIdentity(row);if(!map.has(id))map.set(id,row);}}
  if(d.ingredient)d.ingredient=map.get(this._scanIngredientIdentity(normalize(d.ingredient)))||normalize(d.ingredient);
  const selected=d.ingredient?this._scanIngredientIdentity(d.ingredient):'',all=[...map.values()].sort((a,b)=>a.name.localeCompare(b.name,this._uiIngredientLanguage()));
  const rows=all.filter(row=>this._scanIngredientIdentity(row)===selected||!d.query||this._ingredientQueryMatches(row,d.query));
  select._rows=rows;const options=document.createDocumentFragment();options.append(new Option(this._v78Text('choose'),''));
  for(const row of rows){const id=this._scanIngredientIdentity(row);options.append(new Option(row.name,id,false,id===selected));}select.replaceChildren(options);
  let status=c.querySelector('[data-v111-catalog]');if(!status){status=document.createElement('small');status.dataset.v111Catalog='';select.after(status);}
  status.textContent=this._ingredientCatalogLoading?this._t('catalogLoading'):`${rows.length} / ${all.length} ${this._v111Text('all')}`;
  if(this._v63CatalogFailure&&!this._ingredientCatalogLoading){const retry=document.createElement('button');retry.type='button';retry.className='btn secondary';retry.textContent=this._v84Text('retry');retry.onclick=()=>void this._loadIngredientCatalog(null,true);status.append(' ',retry);}
  const holder=c.querySelector('[data-v78-suggestions]');holder.replaceChildren();
  for(const suggestion of (d.suggestions||[]).slice(0,5)){const row=normalize(suggestion.ingredient);if(!row)continue;const button=document.createElement('button');button.type='button';button.className='btn secondary';button.textContent=row.name;button.onclick=()=>{d.ingredient=row;d.query='';this._v78Dirty=true;c.querySelector('[data-v78-search]').value='';this._v78IngredientOptions();};holder.append(button);}
  this._v79SchedulePrice();this._v111Paint();
 }
 async _v78Save(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d||this._v78Busy||d.scanApplied)return;
  if(!this._v78Submitted){
   const form=c.querySelector('[data-v78-form]');
   if(!d.ingredient||!d.storageLocationId||!(Number(d.quantity)>0)||!d.unit.trim()){d.scanPhase='error';d.scanNote=this._v78Text('amountNeeded');this._v111Paint();form.reportValidity?.();return;}
   if(form.reportValidity?.()===false)return;
   const values={};for(const [key,value] of Object.entries(d.nutrition.values))if(value!==''&&value!==null)values[key]=Number(value);
   if(Object.keys(values).length&&!['g','ml'].includes(d.nutrition.basisUnit)){this._v78SetStatus(this._t('labelNeedBasis'));return;}
   if(d.paidAmount!==''&&!/^[A-Z]{3}$/.test(d.paidCurrency)){this._v78SetStatus(this._v79Text('currency'));return;}
   this._v78Submitted={...(this._v78ProductExtras?.()||{}),entry_id:this._entryId,request_id:d.requestId,ingredient:{key:d.ingredient.key,name:d.ingredient.name},quantity:d.quantity,unit:d.unit.trim(),best_before:d.bestBefore,language:this._uiIngredientLanguage(),lot_metadata:Object.fromEntries(['productName','brand','barcode','storageLocationId','purchaseDate','openedAt','useWithinDays'].map(key=>[key,d[key]])),...(Object.keys(values).length?{nutrition:{basisQuantity:100,basisUnit:d.nutrition.basisUnit,values}}:{})};
  }
  this._v111CancelRead();d.scanPhase='saving';d.scanNote='';this._v78SetBusy(true);const context=this._prefKey();
  try{
   const result=await this._api('cook4me/v33/product_add',this._v78Submitted);if(context!==this._prefKey())return;
   this._v78AcceptState(result);this._foodState=null;
   if(this._v78Alive(c)&&this._v78Draft===d){if(result.warnings?.length){d.scanPhase='error';d.scanNote=result.warnings.join(' ');}else{d.scanApplied=true;d.scanPhase='saved';this._v78Dirty=false;}}
   if(this._tab==='profile')this._renderTab();
  }catch(error){if(this._v78Alive(c)&&this._v78Draft===d){d.scanPhase='error';d.scanNote=String(error.message||error);if(error.code==='product_validation')this._v78Submitted=null;}}
  finally{if(this._v78Alive(c)&&this._v78Draft===d){this._v78Busy=false;this._v78RenderCapture();}}
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.17.15');return result;}
 _v111Styles(){
  if(this.shadowRoot.querySelector('#v111Styles'))return;const style=document.createElement('style');style.id='v111Styles';style.textContent=`
   .v78-capture .v111-camera{position:relative;isolation:isolate;--card-background-color:#16272e;--secondary-background-color:#14242b;--primary-text-color:#fff;--divider-color:#ffffff70;width:100%;min-width:0;box-sizing:border-box;aspect-ratio:auto;height:min(620px,calc(100dvh - 150px));min-height:440px;max-height:none;overflow:hidden;border-radius:20px;background:#121719;color:#fff;box-shadow:inset 0 0 0 1px #ffffff30}.v111-camera video{position:absolute!important;inset:0;width:100%!important;height:100%!important;object-fit:cover}.v111-camera [hidden]{display:none!important}.v111-modes,.v111-bottom{position:absolute;left:10px;right:10px;display:flex;align-items:center;justify-content:center;gap:6px;z-index:4;padding:6px;border-radius:14px;background:#071016c9;backdrop-filter:blur(8px)}.v111-modes{top:10px}.v111-bottom{bottom:10px}.v111-icon{position:relative;display:inline-flex!important;align-items:center;justify-content:center;flex:0 0 42px;min-width:42px!important;width:42px;height:44px;min-height:44px;padding:8px!important;box-sizing:border-box;border:1px solid #ffffff55;border-radius:12px;background:#182a30de;color:#fff;cursor:pointer;overflow:hidden;margin:0!important}.v111-icon ha-icon{--mdc-icon-size:24px;pointer-events:none}.v111-icon[aria-pressed=true],.v111-icon[data-v111-apply]{background:var(--primary-color);border-color:#fff;color:#fff}.v111-icon:disabled{opacity:.45;cursor:default}.v111-icon:focus-visible{outline:3px solid #fff;outline-offset:2px}.v111-file input{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer}.v111-guide-wrap{position:absolute;inset:80px 18px 82px;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:14px;pointer-events:none}.v111-guide-wrap p,.v111-guide-wrap small{background:#071016c9;padding:6px 10px;border-radius:8px;text-align:center;font-size:.86rem;margin:0;max-width:100%;overflow-wrap:anywhere}.v111-guide{position:relative;width:94%;height:30%;min-height:90px;flex-shrink:0;border:1px solid #ffffff55;border-radius:10px;box-shadow:0 0 0 300px #0002}.v111-guide>span{position:absolute;width:24px;height:24px;border-color:#fff;border-style:solid;border-width:0}.v111-guide>span:nth-child(1){left:-2px;top:-2px;border-top-width:3px;border-left-width:3px}.v111-guide>span:nth-child(2){right:-2px;top:-2px;border-top-width:3px;border-right-width:3px}.v111-guide>span:nth-child(3){left:-2px;bottom:-2px;border-bottom-width:3px;border-left-width:3px}.v111-guide>span:nth-child(4){right:-2px;bottom:-2px;border-bottom-width:3px;border-right-width:3px}.v111-camera[data-mode=nutrition] .v111-guide{height:62%}.v111-camera[data-mode=product] .v111-guide{height:68%}.v111-camera[data-mode=date] .v111-guide{height:24%}.v111-table-lines{display:none;position:absolute;inset:15%;background:repeating-linear-gradient(transparent 0 27px,#ffffff60 28px 29px)}.v111-camera[data-mode=nutrition] .v111-table-lines{display:block}.v111-result{position:absolute;left:14px;right:14px;top:80px;bottom:82px;z-index:3;overflow:auto;padding:14px;box-sizing:border-box;border-radius:16px;background:#071016df;backdrop-filter:blur(6px);color:#fff;display:flex;flex-direction:column;gap:9px}.v111-result-heading{display:flex;align-items:center;gap:10px}.v111-result-heading ha-icon{--mdc-icon-size:28px;flex-shrink:0}.v111-ok{color:#6ee7a1}.v111-warning{color:#ffca80}.v111-result h3{margin:0!important;color:#fff;font-size:1.15rem;overflow-wrap:anywhere}.v111-result p{margin:0;font-size:.86rem;overflow-wrap:anywhere}.v111-result small{font-size:.76rem;color:#d3e1e5;margin-top:auto}.v111-facts{font-size:.83rem;line-height:1.5;max-height:110px;overflow:auto;min-height:24px;flex-shrink:1}.v111-result-heading,.v111-result h3,.v111-amount,.v111-place,.v111-result>small{flex-shrink:0}.v111-nutrients{display:flex;gap:4px 10px;flex-wrap:wrap}.v111-nutrients strong{flex-basis:100%}.v111-amount{display:flex;align-items:end;gap:7px}.v111-amount label{flex:1;min-width:0;display:flex;flex-direction:column;font-size:.8rem;gap:3px}.v111-amount input{min-width:0!important;width:100%!important}.v111-amount>select,.v111-amount>input{width:80px!important;min-width:65px!important}.v111-result input,.v111-result select,.v111-code input{box-sizing:border-box;height:40px;max-width:100%;border:1px solid #ffffff70;background:#16272e;color:#fff;border-radius:8px;padding:6px}.v111-place{display:flex;flex-direction:column;gap:4px;font-size:.8rem}.v111-place select{width:100%}.v111-code{position:absolute;z-index:5;bottom:76px;left:14px;right:14px;display:flex;align-items:end;gap:6px;background:#071016f5;border-radius:12px;padding:10px}.v111-code label{display:flex;flex:1;min-width:0;flex-direction:column;font-size:.8rem}.v111-code input{width:100%;min-width:0}.v111-spinner{width:26px;height:26px;flex-shrink:0;border:3px solid #ffffff40;border-top-color:#fff;border-radius:50%;animation:v111spin .8s linear infinite}.v111-photo-help{font-size:.8rem}.v78-capture [data-v78-suggestions]{display:flex;flex-wrap:wrap;gap:6px}.v78-capture [data-v111-catalog]{display:block;font-size:.8rem;margin-top:5px;color:var(--secondary-text-color)}@keyframes v111spin{to{transform:rotate(360deg)}}@media(max-width:700px){.v78-capture .v111-camera{aspect-ratio:auto;height:min(560px,calc(100dvh - 140px));min-height:440px}.v111-result{left:10px;right:10px;padding:12px}.v111-modes,.v111-bottom{left:8px;right:8px;gap:5px}}@media(prefers-reduced-motion:reduce){.v111-spinner{animation-duration:2s}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v111',Cook4MeRecipeHubPanelV111);
