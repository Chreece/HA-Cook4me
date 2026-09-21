const V140='cook4me-recipe-hub-panel-v140';
if(!customElements.get(V140))await import('./cook4me-panel-v140.js?v=2026.9.21.5');
const BasePanel=customElements.get(V140);

const TEXT={
 en:{
  noExpiry:'This product does not expire',noStorage:'No storage place',storageOptional:'Storage place is optional.',
  amountNeeded:'Enter a positive amount, unit and at least one Cook4Me ingredient.',fixFields:'Check the highlighted product details.',
  startingCamera:'Starting camera…',lookingUp:'Looking up product…',readingLabel:'Reading the label…',savingStock:'Saving product to stock…',
  loadingCatalog:'Loading Cook4Me ingredients…',checkingPrice:'Checking price information…',loadingScanner:'Loading scanner settings…',
  loadingNames:'Preparing ingredient names…',processing:'Processing scan…'
 },
 de:{
  noExpiry:'Dieses Produkt hat kein Ablaufdatum',noStorage:'Kein Lagerort',storageOptional:'Der Lagerort ist optional.',
  amountNeeded:'Positive Menge, Einheit und mindestens eine Cook4Me-Zutat eingeben.',fixFields:'Prüfe die markierten Produktangaben.',
  startingCamera:'Kamera wird gestartet…',lookingUp:'Produkt wird gesucht…',readingLabel:'Etikett wird gelesen…',savingStock:'Produkt wird im Vorrat gespeichert…',
  loadingCatalog:'Cook4Me-Zutaten werden geladen…',checkingPrice:'Preisinformationen werden geprüft…',loadingScanner:'Scanner-Einstellungen werden geladen…',
  loadingNames:'Zutatennamen werden vorbereitet…',processing:'Scan wird verarbeitet…'
 },
 el:{
  noExpiry:'Αυτό το προϊόν δεν έχει ημερομηνία λήξης',noStorage:'Χωρίς χώρο αποθήκευσης',storageOptional:'Ο χώρος αποθήκευσης είναι προαιρετικός.',
  amountNeeded:'Συμπλήρωσε θετική ποσότητα, μονάδα και τουλάχιστον ένα υλικό Cook4Me.',fixFields:'Έλεγξε τα επισημασμένα στοιχεία του προϊόντος.',
  startingCamera:'Εκκίνηση κάμερας…',lookingUp:'Αναζήτηση προϊόντος…',readingLabel:'Ανάγνωση ετικέτας…',savingStock:'Αποθήκευση προϊόντος στο απόθεμα…',
  loadingCatalog:'Φόρτωση υλικών Cook4Me…',checkingPrice:'Έλεγχος πληροφοριών τιμής…',loadingScanner:'Φόρτωση ρυθμίσεων scanner…',
  loadingNames:'Προετοιμασία ονομάτων υλικών…',processing:'Επεξεργασία σάρωσης…'
 }
};

class Cook4MeRecipeHubPanelV141 extends BasePanel{
 _v141Text(key){return (TEXT[this._langCode?.()||this._uiIngredientLanguage?.()||'en']||TEXT.en)[key]||TEXT.en[key]||key;}
 _v78Text(key){
  if(key==='choosePlace')return this._v141Text('noStorage');
  if(key==='emptyPlaces')return this._v141Text('storageOptional');
  if(key==='amountNeeded')return this._v141Text('amountNeeded');
  return super._v78Text(key);
 }
 _v78Fresh(mode){return {...super._v78Fresh(mode),noExpiry:false};}

 async _v78Open(mode='barcode'){
  const result=await super._v78Open(mode);
  if(this._v78Dialog){
   document.removeEventListener('visibilitychange',this._v78Visibility);
   this._v78Visibility=()=>{
    if(!this._v78Dialog)return;
    if(document.hidden){
     this._v141CameraWasHidden=true;
     this._v78StopCamera();
    }else if(this._v141CameraWasHidden){
     this._v141CameraWasHidden=false;
     this._v141CameraBlocked=false;
     this._v141KeepCameraWarm();
    }
   };
   document.addEventListener('visibilitychange',this._v78Visibility);
   this._v141KeepCameraWarm();
  }
  return result;
 }
 async _v78Camera(...args){
  const d=this._v78Draft;
  await super._v78Camera(...args);
  if(d&&d===this._v78Draft){
   const live=!!this._v78Stream?.getVideoTracks?.().some(track=>track.readyState==='live');
   if(live)this._v141CameraBlocked=false;
   else if(d.scanPhase==='error')this._v141CameraBlocked=true;
  }
  this._v141PaintBusy();
 }
 async _v113Restart(...args){this._v141CameraBlocked=false;return super._v113Restart(...args);}
 _v141KeepCameraWarm(){
  const c=this._v78Dialog,d=this._v78Draft;
  if(!c||!d||d.mode==='manual'||document.hidden||this._v141CameraBlocked||this._v80CameraPending)return;
  if(this._v78Stream?.getVideoTracks?.().some(track=>track.readyState==='live'))return;
  queueMicrotask(()=>{
   if(this._v78Dialog===c&&this._v78Draft===d&&!document.hidden&&!this._v141CameraBlocked&&!this._v80CameraPending)
    void this._v78Camera();
  });
 }
 _v121ArrangeCameraControls(frame){
  super._v121ArrangeCameraControls(frame);
  for(const node of [frame?.querySelector('[data-v111-power]'),frame?.querySelector('[data-v78-camera]')]){
   if(!node)continue;node.hidden=true;node.setAttribute('aria-hidden','true');node.tabIndex=-1;
  }
 }

 _v141BusyState(){
  const d=this._v78Draft;
  if(!d)return null;
  if(d.scanPhase==='saving')return this._v141Text('savingStock');
  if(d.scanPhase==='looking')return this._v141Text('lookingUp');
  if(d.scanPhase==='reading')return this._v141Text('readingLabel');
  if(this._v80CameraPending)return this._v141Text('startingCamera');
  if(this._ingredientCatalogLoading)return this._v141Text('loadingCatalog');
  if(d.priceLoading)return this._v141Text('checkingPrice');
  if(this._v78Loading)return this._v141Text('loadingScanner');
  if(this._v140MarketCatalogLoading)return this._v141Text('loadingNames');
  if(this._v78Busy)return this._v141Text('processing');
  return null;
 }
 _v141EnsureBusyOverlay(){
  const frame=this._v78Dialog?.querySelector('[data-v111-frame]');if(!frame)return null;
  let overlay=frame.querySelector('[data-v141-busy]');
  if(!overlay){
   overlay=document.createElement('div');overlay.className='v141-busy';overlay.dataset.v141Busy='';overlay.hidden=true;
   overlay.setAttribute('role','status');overlay.setAttribute('aria-live','polite');
   overlay.innerHTML='<span class="v141-ring" aria-hidden="true"></span><strong data-v141-busy-text></strong>';
   frame.append(overlay);
  }
  return overlay;
 }
 _v141PaintBusy(){
  const overlay=this._v141EnsureBusyOverlay(),frame=this._v78Dialog?.querySelector('[data-v111-frame]');if(!overlay||!frame)return;
  const state=this._v141BusyState();overlay.hidden=!state;frame.classList.toggle('v141-processing',!!state);
  overlay.querySelector('[data-v141-busy-text]').textContent=state||'';
 }

 _v141DecorateOptionalFields(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  const place=c.querySelector('main [data-draft="storageLocationId"]');
  if(place){
   place.required=false;
   const label=place.closest('label');
   if(label&&!label.querySelector('[data-v141-storage-note]')){
    const note=document.createElement('small');note.dataset.v141StorageNote='';note.className='v141-optional-note';note.textContent=this._v141Text('storageOptional');label.append(note);
   }
  }
  const date=c.querySelector('main [data-draft="bestBefore"]');
  if(date){
   const label=date.closest('label');let option=c.querySelector('[data-v141-no-expiry]');
   if(label&&!option){
    option=document.createElement('label');option.className='v141-no-expiry';option.dataset.v141NoExpiry='';
    option.innerHTML='<input type="checkbox"><span></span>';label.after(option);
   }
   if(option){
    const box=option.querySelector('input'),text=option.querySelector('span');text.textContent=this._v141Text('noExpiry');
    box.checked=!!d.noExpiry;box.disabled=!!this._v78Submitted||!!this._v78Busy;date.disabled=!!d.noExpiry||!!this._v78Submitted;
    box.onchange=()=>{
     if(this._v78Submitted)return;d.noExpiry=box.checked;
     if(d.noExpiry){d.bestBefore='';date.value='';}else date.disabled=false;
     this._v78Dirty=true;this._v111Paint();if(!d.noExpiry)date.focus();
    };
   }
  }
 }
 _v141SelectedIngredientIds(){
  const rows=this._v114Links?.()||[this._v78Draft?.ingredient].filter(Boolean);
  return new Set(rows.map(row=>this._scanIngredientIdentity(row)));
 }
 _v141DecorateSuggestions(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  const selected=this._v141SelectedIngredientIds();
  c.querySelectorAll('[data-v78-suggestions] [data-suggest]').forEach(button=>{
   const row=d.suggestions?.[Number(button.dataset.suggest)]?.ingredient,id=row?this._scanIngredientIdentity(row):'';
   const picked=!!id&&selected.has(id);button.classList.toggle('v141-selected',picked);button.setAttribute('aria-pressed',String(picked));
  });
 }
 _v141NeedsAssignment(){
  const d=this._v78Draft;if(!d||!(d.productName||d.scanRecognized))return false;
  return this._v141SelectedIngredientIds().size===0;
 }
 _v141FocusAssignment(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d||!this._v141NeedsAssignment())return;
  this._v111CancelRead();d.editorOpen=true;this._v111Paint();
  requestAnimationFrame(()=>{
   if(this._v78Dialog!==c||this._v78Draft!==d)return;
   const target=c.querySelector('[data-v114-links]')||c.querySelector('[data-v78-suggestions]')||c.querySelector('[data-v78-search]');
   const section=target?.closest('.v78-review-section')||target;section?.scrollIntoView?.({block:'start',behavior:'smooth'});
   const focus=c.querySelector('[data-v78-suggestions] [data-suggest]')||c.querySelector('[data-v114-links] input:not(:disabled)')||c.querySelector('[data-v78-search]');
   focus?.focus?.({preventScroll:true});
  });
 }
 async _v78Lookup(code){await super._v78Lookup(code);this._v141FocusAssignment();}
 async _v78Recognize(image){await super._v78Recognize(image);this._v141FocusAssignment();}

 _v141DecorateError(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  c.querySelector('[data-v111-result]')?.classList.remove('v141-error-panel');
  c.querySelector('[data-v141-error]')?.remove();
  if(d.scanPhase!=='error'){this._v141ErrorSignature='';return;}
  const message=String(d.scanNote||this._v111Text('error'));
  let node;
  if(d.editorOpen){
   const editor=c.querySelector('[data-v112-editor]');if(!editor)return;
   node=editor.querySelector('[data-v141-error]');
   if(!node){node=document.createElement('div');node.dataset.v141Error='';node.className='v141-editor-error';node.setAttribute('role','alert');node.tabIndex=-1;const back=editor.querySelector('[data-v112-back]');back?.after(node);if(!back)editor.prepend(node);}
   node.textContent=message;
  }else{
   node=c.querySelector('[data-v111-result]');if(!node)return;
   node.classList.add('v141-error-panel');node.setAttribute('role','alert');node.tabIndex=-1;
  }
  const signature=`${d.editorOpen?'editor':'result'}:${message}`;
  if(this._v141ErrorSignature===signature)return;this._v141ErrorSignature=signature;
  requestAnimationFrame(()=>{if(node?.isConnected){node.scrollIntoView?.({block:'center',behavior:'smooth'});node.focus?.({preventScroll:true});}});
 }
 _v141SetValidationError(message){
  const d=this._v78Draft;if(!d)return;d.scanPhase='error';d.scanNote=String(message||this._v141Text('fixFields'));d.editorOpen=true;this._v141ErrorSignature='';this._v111Paint();
 }

 _v78RenderCapture(){
  super._v78RenderCapture();this._v141Styles();this._v141DecorateOptionalFields();this._v141DecorateSuggestions();this._v141PaintBusy();this._v141DecorateError();this._v141KeepCameraWarm();
 }
 _v111Paint(){
  super._v111Paint();this._v141Styles();this._v141DecorateOptionalFields();this._v141DecorateSuggestions();
  const d=this._v78Draft,c=this._v78Dialog;if(d?.noExpiry&&c){const facts=c.querySelector('[data-v111-result] .v111-facts');if(facts&&!facts.querySelector('[data-v141-no-expiry-fact]')){const fact=document.createElement('div');fact.dataset.v141NoExpiryFact='';fact.textContent=this._v141Text('noExpiry');facts.prepend(fact);}}
  this._v141PaintBusy();this._v141DecorateError();this._v141KeepCameraWarm();
 }
 _v112PaintTotal(){
  super._v112PaintTotal();const d=this._v78Draft,place=this._v78Dialog?.querySelector('[data-v112-details]>span:last-of-type');
  if(d&&place)place.textContent=this._v78Locations().find(row=>row.id===d.storageLocationId)?.name||this._v141Text('noStorage');
 }

 async _v78Save(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d||this._v78Busy)return;
  if(!this._v78Submitted){
   if(!d.ingredient||!(Number(d.quantity)>0)||!String(d.unit||'').trim()){
    this._v141SetValidationError(this._v141Text('amountNeeded'));return;
   }
   const form=c.querySelector('[data-v78-form]');
   if(form?.checkValidity?.()===false){form.reportValidity?.();this._v141SetValidationError(this._v141Text('fixFields'));return;}
   if(!Number.isInteger(Number(d.packageCount))||Number(d.packageCount)<1||Number(d.packageCount)>100){
    c.querySelector('[data-v112-count-edit]')?.reportValidity?.();this._v141SetValidationError(this._v141Text('fixFields'));return;
   }
   const values={};for(const [key,value] of Object.entries(d.nutrition?.values||{}))if(value!==''&&value!==null)values[key]=Number(value);
   if(Object.keys(values).length&&!['g','ml'].includes(d.nutrition?.basisUnit)){this._v141SetValidationError(this._t('labelNeedBasis'));return;}
   if(d.paidAmount!==''&&!/^[A-Z]{3}$/.test(d.paidCurrency)){this._v141SetValidationError(this._v79Text('currency'));return;}
   const ingredientKey=d.ingredient.key||d.ingredient.ingredientId||d.ingredient.id;
   this._v78Submitted={
    ...(this._v78ProductExtras?.()||{}),entry_id:this._entryId,request_id:d.requestId,
    ingredient:{key:ingredientKey,name:d.ingredient.name},quantity:d.quantity,unit:String(d.unit).trim(),best_before:d.noExpiry?'':d.bestBefore,
    language:this._uiIngredientLanguage(),
    lot_metadata:Object.fromEntries(['productName','brand','barcode','storageLocationId','purchaseDate','openedAt','useWithinDays','noExpiry'].map(key=>[key,d[key]])),
    ...(Object.keys(values).length?{nutrition:{basisQuantity:100,basisUnit:d.nutrition.basisUnit,values}}:{})
   };
  }
  this._v111CancelRead();d.scanPhase='saving';d.scanNote='';d.editorOpen=false;this._v141ErrorSignature='';this._v78SetBusy(true);const context=this._prefKey();
  try{
   const result=await this._api('cook4me/v33/product_add',this._v78Submitted);if(context!==this._prefKey())return;
   this._v78AcceptState(result);this._foodState=null;
   if(this._v78Alive(c)&&this._v78Draft===d){
    if(result.warnings?.length){d.scanPhase='error';d.scanNote=result.warnings.join(' ');}
    else{d.scanApplied=true;d.scanPhase='saved';this._v78Dirty=false;}
   }
   if(this._tab==='profile')this._renderTab();
  }catch(error){
   if(this._v78Alive(c)&&this._v78Draft===d){d.scanPhase='error';d.scanNote=String(error.message||error);this._v141ErrorSignature='';if(error.code==='product_validation'){this._v78Submitted=null;d.editorOpen=true;}}
  }finally{if(this._v78Alive(c)&&this._v78Draft===d){this._v78Busy=false;this._v78RenderCapture();}}
  if(d!==this._v78Draft||!d.scanApplied)return;
  if(d.editLotId){this._v78Close(true);this._message(this._v112Text('updated'));return;}
  this._v112SkipBarcode=d.barcode;this._v112LastSaved=this._v112Text('saved');this._v111NewDraft('barcode');await this._v80Scan('barcode');
 }

 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.21.6');this._v141Styles();return result;}
 _v141Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v141Styles'))return;
  const style=document.createElement('style');style.id='v141Styles';style.textContent=`
   .v141-busy{position:absolute;inset:0;z-index:9;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;padding:24px;box-sizing:border-box;text-align:center;background:#071016b8;backdrop-filter:blur(4px);color:#fff;pointer-events:all}
   .v141-busy[hidden]{display:none!important}.v141-ring{width:52px;height:52px;border:5px solid #ffffff42;border-top-color:#fff;border-radius:50%;animation:v141spin .8s linear infinite}.v141-busy strong{max-width:min(380px,90%);font-size:1rem;line-height:1.35}
   .v141-processing [data-v111-result]{visibility:hidden!important}.v141-processing [data-v78-status]{display:none!important}.v141-processing .v111-spinner{display:none!important}
   [data-v78-suggestions] [data-suggest].v141-selected{background:var(--primary-color)!important;border-color:#fff!important;color:#fff!important;box-shadow:0 0 0 2px color-mix(in srgb,var(--primary-color) 45%,transparent)}
   .v141-no-expiry{display:flex!important;flex-direction:row!important;align-items:center;gap:9px;min-height:46px;padding:8px 10px;border:1px solid #ffffff35;border-radius:10px}.v141-no-expiry input{width:20px!important;min-height:20px!important;flex:0 0 20px}.v141-optional-note{display:block;margin-top:4px;color:var(--secondary-text-color);font-size:.78rem}
   .v141-error-panel,.v141-editor-error{border:2px solid #ff4d4f!important;background:color-mix(in srgb,#ff4d4f 18%,#101f26)!important;color:#fff!important;box-shadow:0 0 0 3px #ff4d4f30!important}.v141-error-panel .v111-warning,.v141-error-panel strong{color:#ff6b6d!important}.v141-editor-error{position:sticky;top:52px;z-index:4;margin:8px 0 12px;padding:12px 14px;border-radius:10px;font-weight:650;line-height:1.4}
   @keyframes v141spin{to{transform:rotate(360deg)}}@media(prefers-reduced-motion:reduce){.v141-ring{animation-duration:2s}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v141',Cook4MeRecipeHubPanelV141);
