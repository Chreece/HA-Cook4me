import "./cook4me-panel-v79.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v79');
const TEXT={
 en:{scanner:'Scan this product',help:'Use the same camera for each part of the package. All results go into the form below.',ready:'Point the camera at the package, then press the matching scan button.',again:'Frame the label or product, then press the same button to capture.',photo:'Choose a photo',photoFor:'Photo scan',manual:'Product details · manual entry',manualHelp:'Scan or enter the details here, then choose an ingredient and storage place.',barcode:'Scan barcode',date:'Scan best before',nutrition:'Scan nutrients',product:'Recognise product · AI',barcodeHelp:'Live barcode scanning is unavailable here. Use your phone scanner or enter the barcode.',starting:'Opening camera…'},
 de:{scanner:'Dieses Produkt scannen',help:'Dieselbe Kamera für alle Angaben auf der Verpackung verwenden. Alle Ergebnisse landen im Formular darunter.',ready:'Kamera auf die Verpackung richten und die passende Scan-Taste drücken.',again:'Etikett oder Produkt ins Bild nehmen und dieselbe Taste zur Aufnahme drücken.',photo:'Foto auswählen',photoFor:'Foto-Scan',manual:'Produktdetails · manuelle Eingabe',manualHelp:'Angaben scannen oder hier eingeben, dann Zutat und Lagerort wählen.',barcode:'Barcode scannen',date:'Mindesthaltbarkeit scannen',nutrition:'Nährwerte scannen',product:'Produkt erkennen · KI',barcodeHelp:'Live-Barcode-Scan ist hier nicht verfügbar. Handy-Scanner nutzen oder Barcode eingeben.',starting:'Kamera wird geöffnet…'},
 el:{scanner:'Σάρωση αυτού του προϊόντος',help:'Χρησιμοποίησε την ίδια κάμερα για κάθε στοιχείο της συσκευασίας. Όλα τα αποτελέσματα μπαίνουν στην παρακάτω φόρμα.',ready:'Στρέψε την κάμερα στη συσκευασία και πάτησε το αντίστοιχο κουμπί σάρωσης.',again:'Βάλε την ετικέτα ή το προϊόν στο κάδρο και πάτησε ξανά το ίδιο κουμπί για λήψη.',photo:'Επιλογή φωτογραφίας',photoFor:'Σάρωση φωτογραφίας',manual:'Στοιχεία προϊόντος · χειροκίνητη εισαγωγή',manualHelp:'Σάρωσε ή συμπλήρωσε εδώ τα στοιχεία και επίλεξε υλικό και χώρο αποθήκευσης.',barcode:'Σάρωση barcode',date:'Σάρωση λήξης',nutrition:'Σάρωση θρεπτικών',product:'Αναγνώριση προϊόντος · AI',barcodeHelp:'Η ζωντανή σάρωση barcode δεν είναι διαθέσιμη εδώ. Χρησιμοποίησε τον scanner κινητού ή γράψε τον barcode.',starting:'Άνοιγμα κάμερας…'}
};
const SCANS=[['barcode','barcode-scan'],['date','calendar-clock'],['nutrition','nutrition'],['product','creation']];
class Cook4MeRecipeHubPanelV80 extends BasePanel{
 _v80Text(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||key;}
 _renderProfile(c){super._renderProfile(c);c.querySelector('.v78-advanced')?.remove();}
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.16.5');this._v80Styles();return result;}
 _v78RenderCapture(){
  super._v78RenderCapture();const c=this._v78Dialog,d=this._v78Draft;if(!c||!d||this._v78Saved)return;
  this._v80Styles();c.querySelector('.v78-modes')?.remove();
  const e=v=>this._escape(v??''),t=k=>e(this._v80Text(k)),tools=c.querySelector('.v78-capture-tools');
  tools.innerHTML=`<h3>${t('scanner')}</h3><p class="muted">${t('help')}</p><div class="v78-viewfinder"><video autoplay playsinline muted></video><div class="v78-view-hint"><ha-icon icon="mdi:camera-outline"></ha-icon><span>${t('ready')}</span></div></div><div class="v80-scan-actions">${SCANS.map(([key,icon])=>`<button type="button" class="btn secondary" data-v80-scan="${key}" aria-pressed="${d.mode===key}"><ha-icon icon="mdi:${icon}"></ha-icon><span>${t(key)}</span></button>`).join('')}</div><div class="v78-actions"><button type="button" class="btn secondary" data-v78-camera>${e(this._v78Text('camera'))}</button><button type="button" class="btn secondary" data-v78-stop hidden>${e(this._v78Text('stop'))}</button><label class="v78-file btn secondary">${t('photo')}<input data-v78-file type="file" accept="image/*" capture="environment"></label></div><small data-v80-photo-mode></small><p class="muted">${e(this._v78Text('photoHelp'))}</p>${this._nativeBarcodeScannerAvailable?.()?`<button type="button" class="btn secondary" data-v78-native>${e(this._v78Text('native'))}</button>`:''}<label class="field">${e(this._v78Text('barcode'))}<input data-draft="barcode" type="text" inputmode="numeric" autocomplete="off" value="${e(d.barcode)}"></label><button type="button" class="btn secondary" data-v78-lookup>${e(this._v78Text('lookup'))}</button>`;
  c.querySelector('main>h2').textContent=this._v80Text('manual');c.querySelector('main>p').textContent=this._v80Text('manualHelp');
  tools.querySelectorAll('[data-v80-scan]').forEach(b=>b.onclick=()=>void this._v80Scan(b.dataset.v80Scan));
  tools.querySelector('[data-v78-camera]').onclick=()=>void this._v78Camera();
  tools.querySelector('[data-v78-stop]').onclick=()=>{this._v78StopCamera();this._v78RenderCapture();};
  tools.querySelector('[data-v78-file]').onchange=event=>{const file=event.target.files?.[0];event.target.value='';if(file){if(d.mode==='manual')d.mode='product';this._v80PaintScan();void this._v78Photo(file);}};
  tools.querySelector('[data-v78-native]')?.addEventListener('click',()=>{d.mode='barcode';this._v80PaintScan();this._v78StopCamera();this._scannerOpen=true;void this._startNativeBarcodeScanner(c);});
  tools.querySelector('[data-draft=barcode]').oninput=event=>{d.barcode=event.target.value;this._v78Dirty=true;this._v79SchedulePrice();};
  tools.querySelector('[data-v78-lookup]').onclick=()=>void this._v78Lookup(d.barcode);
  this._v80PaintScan();this._v78SetBusy(Boolean(this._v78Busy));
 }
 _v80PaintScan(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  c.querySelectorAll('[data-v80-scan]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.v80Scan===d.mode)));
  const hint=c.querySelector('[data-v80-photo-mode]');if(hint)hint.textContent=`${this._v80Text('photoFor')}: ${this._v78Text(d.mode==='manual'?'product':d.mode)}`;
  if(d.mode==='nutrition')c.querySelector('[data-v78-basis]')?.closest('details')?.setAttribute('open','');
 }
 async _v78Lookup(code){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||this._v78Busy||this._v78Submitted)return;
  this._v78StopCamera();this._v78SetBusy(true);this._v78SetStatus(this._v78Text('working'));
  try{
   const result=await this._api('cook4me/v33/barcode_lookup',{entry_id:this._entryId,barcode:String(code||'').trim(),language:this._uiIngredientLanguage()});if(!this._v78Alive(c))return;
   const p=result.product||{},m=result.mapping||{};d.barcode=result.barcode;
   for(const key of ['productName','brand','quantity','unit']){const value=p[key]??(key==='productName'?p.name:undefined)??m[key];if(value!==undefined&&value!==null&&value!=='')d[key]=value;}
   if(m.ingredient)d.ingredient=m.ingredient;d.suggestions=result.suggestions||[];d.query='';
   // A barcode may omit label data. Keep values already scanned or entered.
   const nutrition=p.nutrition||m.nutrition;
   if(nutrition?.basisUnit&&Object.keys(nutrition.values||{}).length){
    const previous=d.nutrition;
    if(!Object.keys(previous.values||{}).length)d.nutrition=structuredClone(nutrition);
    else if(previous.basisUnit===nutrition.basisUnit)d.nutrition={...structuredClone(nutrition),values:{...nutrition.values,...previous.values}};
   }
   this._v78Dirty=true;this._v78Status=d.productName?this._v78Text('reviewHelp'):this._v78Text('unknown');
  }catch(error){if(this._v78Alive(c))this._v78Status=String(error.message||error);}
  finally{if(this._v78Alive(c)){this._v78Busy=false;this._v78RenderCapture();}}
 }
 _v78StopCamera(){this._v80ScanToken={};this._v80CameraPending=false;super._v78StopCamera();}
 async _v78Camera(){
  const c=this._v78Dialog;if(!c||this._v78Busy||this._v78Submitted||this._v80CameraPending)return;
  if(this._v78Stream)return;
  this._v78StopCamera();const token={};this._v78CameraToken=token;this._v80CameraPending=true;this._v78SetStatus(this._v80Text('starting'));
  try{
   if(!navigator.mediaDevices?.getUserMedia)throw new Error(this._v78Text('cameraHelp'));
   const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});
   if(!this._v78Alive(c)||this._v78CameraToken!==token){stream.getTracks().forEach(t=>t.stop());return;}
   this._v78Stream=stream;const video=c.querySelector('video');video.srcObject=stream;await video.play();
   if(!this._v78Alive(c)||this._v78CameraToken!==token)return;
   c.querySelector('.v78-view-hint').hidden=true;c.querySelector('[data-v78-stop]').hidden=false;c.querySelector('[data-v78-camera]').hidden=true;this._v78SetStatus(this._v80Text('ready'));
  }catch(error){if(this._v78Alive(c)&&this._v78CameraToken===token){this._v78StopCamera();this._v78SetStatus(`${this._v78Text('cameraHelp')} ${error.message||error}`);}}
  finally{if(this._v78CameraToken===token)this._v80CameraPending=false;}
 }
 async _v80Scan(mode){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d||this._v78Busy||this._v78Submitted||this._v80CameraPending||!SCANS.some(([key])=>key===mode))return;
  clearTimeout(this._v78CameraTimer);this._v80ScanToken={};d.mode=mode;this._v80PaintScan();
  if(mode==='barcode'&&typeof globalThis.BarcodeDetector!=='function'){
   if(this._nativeBarcodeScannerAvailable?.()){this._v78StopCamera();this._scannerOpen=true;await this._startNativeBarcodeScanner(c);}else this._v78SetStatus(this._v80Text('barcodeHelp'));
   return;
  }
  const wasLive=Boolean(this._v78Stream);await this._v78Camera();if(!this._v78Alive(c)||!this._v78Stream)return;
  if(mode==='barcode'){this._v80BarcodeLoop(c);return;}
  if(!wasLive||!c.querySelector('video')?.videoWidth){this._v78SetStatus(this._v80Text('again'));return;}
  await this._v78CaptureFrame();
 }
 _v80BarcodeLoop(c){
  const token={};this._v80ScanToken=token;let detector;
  try{detector=new BarcodeDetector({formats:['ean_13','ean_8','upc_a','upc_e','itf']});}catch(error){this._v78SetStatus(`${this._v80Text('barcodeHelp')} ${error.message||error}`);return;}
  const loop=async()=>{
   if(!this._v78Alive(c)||this._v80ScanToken!==token||!this._v78Stream)return;
   try{const codes=await detector.detect(c.querySelector('video'));if(!this._v78Alive(c)||this._v80ScanToken!==token)return;if(codes?.[0]?.rawValue){this._v78StopCamera();await this._v78Lookup(codes[0].rawValue);return;}}catch{}
   if(this._v78Alive(c)&&this._v80ScanToken===token)this._v78CameraTimer=setTimeout(loop,250);
  };void loop();
 }
 _v80Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v80Styles'))return;const style=document.createElement('style');style.id='v80Styles';
  style.textContent=`.v80-scan-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.v80-scan-actions .btn{display:flex;align-items:center;justify-content:flex-start;gap:10px;white-space:normal;text-align:left;min-height:60px;padding:12px}.v80-scan-actions .btn[aria-pressed=true]{border-color:var(--primary-color);background:color-mix(in srgb,var(--primary-color) 10%,var(--card-background-color));color:var(--primary-color)}.v80-scan-actions ha-icon{flex:none}.v78-capture-tools>p{margin:0}.v78-capture-tools>small{color:var(--secondary-text-color)}@media(max-width:700px){.v80-scan-actions .btn{font-size:13px;padding:10px;gap:7px}.v78-capture-body{padding-top:18px}}`;
  this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v80',Cook4MeRecipeHubPanelV80);
