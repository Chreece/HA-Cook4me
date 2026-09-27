import {layoutDialog} from './app-design-v203.js';
const COPY={
 en:{receipts:'Saved receipts',empty:'No receipts waiting for review.',edit:'Edit',add:'Add',discard:'Discard',close:'Close',back:'Save changes & return',queued:'Waiting to process',barcode:'Finding barcodes',nutrition:'Looking up nutrition',ingredients:'Matching catalog ingredients',ready:'Ready to review',failed:'Processing interrupted',permission:'Access no longer available',retry:'Retry processing',hint:'Saved automatically. Matching continues in the background. Review each product before adding it to stock.',complete:'All lines reviewed.',remove:'Delete receipt',confirm:'Permanently delete this saved receipt?',missing:'Some product details are missing. Open Edit to complete them.',barcode_ambiguous:'Barcode match is uncertain',lookup_failed:'Product lookup unavailable',tax:'VAT added to line prices',taxReview:'Check VAT-inclusive prices before adding products.',taxConfirm:'I confirm this line price includes VAT',processing:'Processing',saved:'Receipt saved',price:'Line price',unknown:'Unknown',reviewed:'Edited',pending:'Waiting for matching',select:'Select product',addSelected:'Add selected',removeSelected:'Remove selected'},
 de:{receipts:'Gespeicherte Kassenbons',empty:'Keine Kassenbons zur Prüfung.',edit:'Bearbeiten',add:'Hinzufügen',discard:'Verwerfen',close:'Schließen',back:'Änderungen speichern & zurück',queued:'Wartet auf Verarbeitung',barcode:'Barcodes suchen',nutrition:'Nährwerte suchen',ingredients:'Katalogzutaten zuordnen',ready:'Bereit zur Prüfung',failed:'Verarbeitung unterbrochen',permission:'Zugriff nicht mehr verfügbar',retry:'Verarbeitung wiederholen',hint:'Automatisch gespeichert. Die Zuordnung läuft im Hintergrund. Jedes Produkt vor dem Hinzufügen zum Vorrat prüfen.',complete:'Alle Zeilen geprüft.',remove:'Kassenbon löschen',confirm:'Diesen gespeicherten Kassenbon endgültig löschen?',missing:'Produktangaben fehlen. Über Bearbeiten vervollständigen.',barcode_ambiguous:'Barcode-Zuordnung unsicher',lookup_failed:'Produktsuche nicht verfügbar',tax:'MwSt. zu den Zeilenpreisen addiert',taxReview:'Preise inklusive MwSt. vor dem Hinzufügen prüfen.',taxConfirm:'Ich bestätige, dass dieser Zeilenpreis die MwSt. enthält',processing:'Verarbeitung',saved:'Kassenbon gespeichert',price:'Zeilenpreis',unknown:'Unbekannt',reviewed:'Bearbeitet',pending:'Wartet auf Zuordnung',select:'Produkt auswählen',addSelected:'Ausgewählte hinzufügen',removeSelected:'Ausgewählte entfernen'},
 el:{receipts:'Αποθηκευμένες αποδείξεις',empty:'Δεν υπάρχουν αποδείξεις για έλεγχο.',edit:'Επεξεργασία',add:'Προσθήκη',discard:'Απόρριψη',close:'Κλείσιμο',back:'Αποθήκευση αλλαγών & επιστροφή',queued:'Αναμονή επεξεργασίας',barcode:'Αναζήτηση barcode',nutrition:'Αναζήτηση θρεπτικών στοιχείων',ingredients:'Αντιστοίχιση υλικών καταλόγου',ready:'Έτοιμη για έλεγχο',failed:'Η επεξεργασία διακόπηκε',permission:'Η πρόσβαση δεν είναι πλέον διαθέσιμη',retry:'Επανάληψη επεξεργασίας',hint:'Αποθηκεύτηκε αυτόματα. Η αντιστοίχιση συνεχίζεται στο παρασκήνιο. Ελέγξτε κάθε προϊόν πριν το προσθέσετε στο απόθεμα.',complete:'Ελέγχθηκαν όλες οι γραμμές.',remove:'Διαγραφή απόδειξης',confirm:'Να διαγραφεί οριστικά αυτή η αποθηκευμένη απόδειξη;',missing:'Λείπουν στοιχεία προϊόντος. Συμπληρώστε τα στην Επεξεργασία.',barcode_ambiguous:'Αβέβαιη αντιστοίχιση barcode',lookup_failed:'Η αναζήτηση προϊόντος δεν είναι διαθέσιμη',tax:'Ο ΦΠΑ προστέθηκε στις τιμές των γραμμών',taxReview:'Ελέγξτε τις τιμές με ΦΠΑ πριν προσθέσετε τα προϊόντα.',taxConfirm:'Επιβεβαιώνω ότι η τιμή αυτής της γραμμής περιλαμβάνει ΦΠΑ',processing:'Επεξεργασία',saved:'Η απόδειξη αποθηκεύτηκε',price:'Τιμή γραμμής',unknown:'Άγνωστο',reviewed:'Επεξεργασμένο',pending:'Αναμονή αντιστοίχισης',select:'Επιλογή προϊόντος',addSelected:'Προσθήκη επιλεγμένων',removeSelected:'Αφαίρεση επιλεγμένων'}
};
const clone=value=>structuredClone(value);
const active=row=>['queued','processing'].includes(row.processing?.state);
export const ReceiptQueueMixin=Base=>class extends Base{
 _r232Text(key){return (COPY[String(this._uiIngredientLanguage?.()||'en').split(/[-_]/)[0]]||COPY.en)[key]||key;}
 _r232Context(){return `${this._entryId||''}:${this._hass?.user?.id||''}:${this._prefKey?.()||''}`;}
 _r232Api(action,data={}){return this._api('cook4me/receipts/drafts',{entry_id:this._entryId,language:this._uiIngredientLanguage(),action,...data});}
 _r232Ensure(){
  const key=this._r232Context();if(this._r232Key!==key){
   clearTimeout(this._r232Timer);this._r232Timer=null;this._r232Flight=null;this._r232Dialog?.remove();this._r232Dialog=null;
   this._r232Key=key;this._r232Rows=[];this._r232Details=new Map();this._r232Expanded=new Set();this._r232Selected=new Map();this._r232Error='';
  }
  this._r232Styles();
 }
 _r232Schedule(delay=15000){if(this.isConnected&&this._entryId&&!this._r232Timer)this._r232Timer=setTimeout(()=>{this._r232Timer=null;void this._r232Poll();},delay);}
 async _r232Poll(){
  this._r232Ensure();if(this._r232Flight||!this.isConnected||!this._entryId)return;
  const token={},key=this._r232Key,connection=this._hass?.connection;this._r232Flight=token;
  const alive=()=>this.isConnected&&key===this._r232Context()&&connection===this._hass?.connection;
  try{
   const result=await this._r232Api('list');if(!alive())return;
   this._r232Rows=result.drafts||[];
   if(this._r232Dialog?.open)await Promise.all(this._r232Rows.filter(r=>this._r232Expanded.has(r.id)).map(async r=>{
    const data=await this._r232Api('get',{receipt_id:r.id});if(alive())this._r232Details.set(r.id,data.receipt);
   }));
   if(alive()){this._r232Error='';this._r232Button();this._r232Paint();}
  }catch(error){if(alive()){this._r232Error=String(error.message||error);this._r232Paint();}}
  finally{if(this._r232Flight===token){this._r232Flight=null;if(alive())this._r232Schedule(this._r232Rows.some(active)?2500:15000);}}
 }
 _r199Launch(root){const result=super._r199Launch(root);this._r232Ensure();this._r232Button(root);this._r232Schedule(this._r232Rows?.length?15000:0);return result;}
 _r232Button(root=this.shadowRoot){
  const add=root?.querySelector('[data-r199-receipt-photo]')||root?.querySelector('[data-v78-open="barcode"]');
  if(!add)return;let button=root.querySelector('[data-r232-open]');
  const count=(this._r232Rows||[]).filter(r=>r.pendingCount>0||active(r)).length;
  if(!this._r232Rows?.length){button?.remove();return;}
  if(!button){button=document.createElement('button');button.type='button';button.className='btn secondary';button.dataset.r232Open='';button.onclick=()=>void this._r232Open();add.after(button);}
  button.textContent=`${this._r232Text('receipts')} (${count})`;
 }
 async _r232Open(receipt=null){
  this._r232Ensure();
  if(receipt)this._r232Details.set(receipt.id,receipt);
  this._r232Expanded.clear();
  // Every entry into Saved receipts starts visually folded, including when the
  // same dialog DOM is reused after editing an item.
  for(const detail of this._r232Dialog?.querySelectorAll('[data-r232-receipt]')||[]){
   detail.open=false;const body=detail.querySelector('[data-r232-lines]');
   if(body){body.replaceChildren();body._signature=null;}
  }
  if(!this._r232Dialog){
   const d=document.createElement('dialog');d.className='r232-dialog';d.dataset.r232Queue='';
   d.innerHTML='<header><h2></h2><button type="button" class="btn secondary" data-r232-close></button></header><p data-r232-hint></p><p role="status" aria-live="polite" data-r232-message></p><div data-r232-list></div>';
   d.querySelector('h2').textContent=this._r232Text('receipts');d.querySelector('[data-r232-hint]').textContent=this._r232Text('hint');
   const close=d.querySelector('[data-r232-close]');close.textContent=this._r232Text('close');close.onclick=()=>d.close();
   this.shadowRoot.append(d);this._r232Dialog=d;
  }
  layoutDialog(this._r232Dialog);this._r232Dialog.showModal();this._r232Paint();await this._r232Poll();
 }
 _r232Progress(row){const p=row.processing||{};return p.state?`${this._r232Text(p.stage||p.state)} · ${p.done||0}/${p.total||0}`:'';}
 _r232Selection(id){
  let selected=this._r232Selected.get(id);if(!selected){selected=new Set();this._r232Selected.set(id,selected);}return selected;
 }
 _r232PaintBulk(detail,id,receipt){
  const selected=this._r232Selection(id),items=receipt?.items||[];
  const selectable=new Set(items.filter(item=>item.kind==='product'&&['pending','applying'].includes(item.status)).map(item=>item.id));
  for(const itemId of [...selected])if(!selectable.has(itemId))selected.delete(itemId);
  for(const input of detail.querySelectorAll('[data-r232-select-item]'))input.checked=selected.has(input.dataset.r232SelectItem);
  const addIds=items.filter(item=>selected.has(item.id)&&item.kind==='product'&&['pending','applying'].includes(item.status)).map(item=>item.id);
  const removeIds=items.filter(item=>selected.has(item.id)&&item.kind==='product'&&item.status==='pending').map(item=>item.id);
  const add=detail.querySelector('[data-r232-bulk="apply"]'),remove=detail.querySelector('[data-r232-bulk="discard"]');
  if(add){add.textContent=`${this._r232Text('addSelected')} (${addIds.length})`;add.disabled=this._r232Working||!addIds.length;}
  if(remove){remove.textContent=`${this._r232Text('removeSelected')} (${removeIds.length})`;remove.disabled=this._r232Working||!removeIds.length;}
 }
 _r232Paint(){
  const d=this._r232Dialog;if(!d?.open)return;const list=d.querySelector('[data-r232-list]');
  d.querySelector('[data-r232-message]').textContent=this._r232Error||'';
  const rows=this._r232Rows||[];
  list.querySelector('[data-r232-empty]')?.remove();
  for(const node of list.querySelectorAll('[data-r232-receipt]'))if(!rows.some(r=>r.id===node.dataset.r232Receipt)){this._r232Selected.delete(node.dataset.r232Receipt);node.remove();}
  if(!rows.length){const p=document.createElement('p');p.dataset.r232Empty='';p.textContent=this._r232Text('empty');list.append(p);}
  const e=v=>this._escape(String(v??'')),t=k=>e(this._r232Text(k));
  for(const row of rows){
   let detail=[...list.children].find(n=>n.dataset.r232Receipt===row.id);
   if(!detail){
    detail=document.createElement('details');detail.dataset.r232Receipt=row.id;
    detail.innerHTML='<summary><span class="r232-summary-main"><strong></strong><span role="status" aria-live="polite"></span><progress></progress></span><button type="button" class="btn secondary r232-receipt-remove" data-r232-receipt-remove></button></summary><div data-r232-lines></div>';
    detail.open=false;list.append(detail);
    detail.ontoggle=()=>{if(detail.open){this._r232Expanded.add(row.id);if(this._r232Details.has(row.id))this._r232Paint();else void this._r232Poll();}else this._r232Expanded.delete(row.id);};
    const removeReceipt=detail.querySelector('[data-r232-receipt-remove]');
    removeReceipt.onclick=event=>{event.preventDefault();event.stopPropagation();void this._r232Action('remove',row.id,'');};
   }
   detail.querySelector('summary strong').textContent=`${row.merchant||this._r232Text('unknown')} · ${row.purchaseDate||'—'} · ${row.pendingCount||0}`;
   detail.querySelector('summary span[role="status"]').textContent=this._r232Progress(row);
   const receiptRemove=detail.querySelector('[data-r232-receipt-remove]');receiptRemove.textContent=this._r232Text('remove');receiptRemove.disabled=!!this._r232Working;
   const progress=detail.querySelector('progress');progress.hidden=!active(row);progress.max=Math.max(1,row.processing?.total||1);progress.value=row.processing?.done||0;progress.setAttribute('aria-label',this._r232Text('processing'));
   const receipt=this._r232Details.get(row.id),body=detail.querySelector('[data-r232-lines]');if(!detail.open||!receipt||this._r232Working)continue;
   const signature=JSON.stringify(receipt);
   if(body._signature!==signature){
    body._signature=signature;
    const lines=receipt.items.filter(i=>['pending','applying'].includes(i.status)),selected=this._r232Selection(row.id);
    const selectable=new Set(lines.filter(i=>i.kind==='product').map(i=>i.id));for(const itemId of [...selected])if(!selectable.has(itemId))selected.delete(itemId);
    body.innerHTML=`${receipt.taxStatus==='allocated'?`<p>${t('tax')}</p>`:receipt.taxStatus==='needs_review'?`<p>${t('taxReview')}</p>`:''}${lines.length?'':`<p>${t('complete')}</p>`}${lines.some(i=>i.kind==='product')?`<div class="r232-bulk"><button type="button" class="btn" data-r232-bulk="apply"></button><button type="button" class="btn secondary" data-r232-bulk="discard"></button></div>`:''}${lines.map(i=>`<article data-r232-item="${e(i.id)}">${i.kind==='product'?`<label class="r232-select"><input type="checkbox" data-r232-select-item="${e(i.id)}" ${selected.has(i.id)?'checked':''}><span>${t('select')}</span></label>`:''}<strong>${e(i.productName||i.originalName)}</strong><div>${e(i.packageCount||1)} × ${e(i.quantity??'—')} ${e(i.unit)} · ${t('price')}: ${e(i.lineTotal??'—')} ${e(receipt.currency)}</div><small>${e([i.barcode,...(i.ingredientLinks||[]).map(x=>x.name),this._r232Text(i.status==='applying'?'processing':i.enrichment?.state==='ready'?'ready':i.enrichment?.state==='reviewed'?'reviewed':'pending'),...(i.enrichment?.notes||[]).map(n=>this._r232Text(n))].filter(Boolean).join(' · '))}</small><div class="r232-actions"><button type="button" class="btn secondary" data-r232-action="edit" ${i.status!=='pending'?'disabled':''}>${t('edit')}</button><button type="button" class="btn secondary" data-r232-action="discard" ${i.status!=='pending'?'disabled':''}>${t('discard')}</button></div></article>`).join('')}<div class="r232-actions">${receipt.processing?.state==='failed'||receipt.items.some(i=>i.status==='pending'&&i.enrichment?.notes?.includes('lookup_failed'))?`<button class="btn secondary" data-r232-action="retry">${t('retry')}</button>`:''}</div>`;
    body.querySelectorAll('[data-r232-select-item]').forEach(input=>input.onchange=()=>{const set=this._r232Selection(row.id);if(input.checked)set.add(input.dataset.r232SelectItem);else set.delete(input.dataset.r232SelectItem);this._r232PaintBulk(detail,row.id,receipt);});
    body.querySelectorAll('[data-r232-action]').forEach(b=>b.onclick=()=>void this._r232Action(b.dataset.r232Action,row.id,b.closest('[data-r232-item]')?.dataset.r232Item||''));
    body.querySelectorAll('[data-r232-bulk]').forEach(b=>b.onclick=()=>void this._r232Bulk(b.dataset.r232Bulk,row.id));
   }
   this._r232PaintBulk(detail,row.id,receipt);
  }
 }
 async _r232Bulk(action,id){
  if(this._r232Working||!['apply','discard'].includes(action))return;
  const selected=this._r232Selection(id),receipt=this._r232Details.get(id);
  const itemIds=(receipt?.items||[]).filter(item=>selected.has(item.id)&&item.kind==='product'&&(action==='apply'?['pending','applying'].includes(item.status):item.status==='pending')).map(item=>item.id);
  if(!itemIds.length)return;
  const key=this._r232Context();this._r232Working=true;this._r232Error='';
  this._r232Dialog?.querySelectorAll('[data-r232-action],[data-r232-bulk],[data-r232-select-item],[data-r232-receipt-remove]').forEach(node=>node.disabled=true);
  try{
   for(const itemId of itemIds){
    const result=await this._r232Latest(action,id,itemId);if(key!==this._r232Context())return;
    selected.delete(itemId);
    if(result.result){this._v78AcceptState(result.result);this._foodState=null;if(result.result.warnings?.length){this._r232Error=result.result.warnings.join(' ');break;}}
    if(result.receipt)this._r232Details.set(id,result.receipt);
   }
  }catch(error){if(key===this._r232Context())this._r232Error=String(error.message||error);}
  finally{
   this._r232Working=false;
   if(key===this._r232Context()){
    for(const body of this._r232Dialog?.querySelectorAll('[data-r232-lines]')||[])body._signature=null;
    const message=this._r232Error;await this._r232Poll();this._r232Error=message;this._r232Paint();
   }
  }
 }
 async _r232Latest(action,id,itemId=''){
  const key=this._r232Context();
  for(let attempt=0;attempt<3;attempt++){
   const {receipt}=await this._r232Api('get',{receipt_id:id});
   if(key!==this._r232Context())throw Error('The active Cook4Me device changed.');
   try{return await this._r232Api(action,{receipt_id:id,item_id:itemId,revision:receipt.revision});}
   catch(error){if(error.code!=='receipt_conflict'||attempt===2)throw error;}
  }
 }
 async _r232Action(action,id,itemId){
  if(this._r232Working)return;if(action==='remove'&&!globalThis.confirm(this._r232Text('confirm')))return;
  const key=this._r232Context();this._r232Working=true;this._r232Error='';
  this._r232Dialog?.querySelectorAll('[data-r232-action],[data-r232-bulk],[data-r232-select-item],[data-r232-receipt-remove]').forEach(b=>b.disabled=true);
  try{
   if(action==='edit'){
    // Claim this line before opening. A lookup already in flight cannot replace
    // the user's draft, while other products continue processing.
    let receipt;
    for(let attempt=0;attempt<3;attempt++){
     ({receipt}=await this._r232Api('get',{receipt_id:id}));const item=receipt.items.find(i=>i.id===itemId);
     if(key!==this._r232Context())return;
     if(!item||item.status!=='pending')throw Error(this._r232Text('complete'));
     try{({receipt}=await this._r232Api('save_item',{receipt_id:id,item_id:itemId,item_revision:item.itemRevision||0,item}));break;}
     catch(error){if(error.code!=='receipt_conflict'||attempt===2)throw error;}
    }
    if(key!==this._r232Context())return;
    this._r232Dialog?.close();await this._v78Open('manual');if(key!==this._r232Context()||!this._v78Dialog)return;
    this._r232Editing=true;this._r195SetReceipt(receipt,receipt.items.findIndex(i=>i.id===itemId));return;
   }
   const result=action==='retry'?await this._r232Api('retry',{receipt_id:id}):await this._r232Latest(action==='remove'?'discard':action,id,itemId);
   if(key!==this._r232Context())return;
   if(result.result){this._v78AcceptState(result.result);this._foodState=null;this._r232Error=(result.result.warnings||[]).join(' ');}
   if(result.receipt)this._r232Details.set(id,result.receipt);else{this._r232Details.delete(id);this._r232Selected.delete(id);}
  }catch(error){if(key===this._r232Context())this._r232Error=String(error.message||error);}
  finally{
   this._r232Working=false;
   if(key===this._r232Context()){
    for(const body of this._r232Dialog?.querySelectorAll('[data-r232-lines]')||[])body._signature=null;
    const message=this._r232Error;await this._r232Poll();this._r232Error=message;this._r232Paint();
   }
  }
 }
 _r195SetReceipt(receipt,index=0){
  if(this._v78Draft?.mode==='receipt'&&receipt.id&&receipt.processing){
   this._v78Busy=false;this._v78Dirty=false;this._r195Session=null;this._v78Close(true);void this._r232Open(receipt);return;
  }
  const result=super._r195SetReceipt(receipt,index);
  if(this._r195Session)this._r195Session.metadata=Object.fromEntries(['merchant','currency','purchaseDate'].map(k=>[k,receipt[k]]));
  return result;
 }
 _r232ReceiptContext(){const d=this._v78Draft;if(!this._r195Session||!d)return null;return Object.fromEntries(['receiptItemId','paidAmount','paidCurrency','paidShop','purchaseDate','packageCount'].map(k=>[k,d[k]]));}
 _v111NewDraft(mode){const context=this._r232ReceiptContext();const result=super._v111NewDraft(mode);if(context)Object.assign(this._v78Draft,context,{editorOpen:true});return result;}
 async _v78Lookup(code){
  const context=this._r232ReceiptContext(),session=this._r195Session,old=clone(this._v78Draft||{});
  const result=await super._v78Lookup(code);
  if(context&&session===this._r195Session&&this._v78Dialog){
   Object.assign(this._v78Draft,context,{editorOpen:true});
   for(const k of ['productName','brand','quantity','unit'])if(!this._v78Draft[k])this._v78Draft[k]=old[k];
   this._r195Flush();this._v78RenderCapture();
  }return result;
 }
 async _v78Recognize(image){
  const context=this._r232ReceiptContext(),session=this._r195Session;const result=await super._v78Recognize(image);
  if(context&&session===this._r195Session&&this._v78Dialog){Object.assign(this._v78Draft,context,{editorOpen:true});this._r195Flush();this._v78RenderCapture();}return result;
 }
 async _r195SaveData(){
  if(!this._r232Editing)return super._r195SaveData();
  this._r195Flush();const s=this._r195Session,item=this._r195Current();
  const metadata=Object.fromEntries(['merchant','currency','purchaseDate'].filter(k=>s.receipt[k]!==s.metadata?.[k]).map(k=>[k,s.receipt[k]]));
  const {receipt}=await this._r232Api('save_item',{receipt_id:s.receipt.id,item_id:item.id,item_revision:item.itemRevision||0,item,receipt:metadata});
  if(s!==this._r195Session)return null;s.receipt=receipt;this._r232Details.set(receipt.id,receipt);s.metadata=Object.fromEntries(['merchant','currency','purchaseDate'].map(k=>[k,receipt[k]]));s.dirty=false;this._v78Dirty=false;return receipt;
 }
 async _r195Action(action){
  if(!this._r232Editing)return super._r195Action(action);if(this._v78Busy)return;
  const s=this._r195Session,item=this._r195Current();this._v78SetBusy(true);
  try{
   if(action!=='discard'&&item.status==='pending')await this._r195SaveData();
   if(action!=='save'){
    const result=await this._r232Latest(action,s.receipt.id,item.id);
    if(s!==this._r195Session)return;
    if(result.result){this._v78AcceptState(result.result);this._foodState=null;if(result.result.warnings?.length)throw Error(result.result.warnings.join(' '));}
   }
   if(s!==this._r195Session)return;
   this._v78Busy=false;this._v78Dirty=false;s.dirty=false;this._v78Close(true);await this._r232Open();
  }catch(error){if(s===this._r195Session){
   this._r195Message=String(error.message||error);this._v78SetStatus(this._r195Message);
   // An interrupted stock request may already have a durable intent. Keep its
   // immutable retry state rather than trying to save it as a new pending line.
   try{const {receipt}=await this._r232Api('get',{receipt_id:s.receipt.id});if(s===this._r195Session&&receipt.items.find(i=>i.id===item.id)?.status!=='pending')s.receipt=receipt;}catch{}
  }}
  finally{if(s===this._r195Session){this._v78SetBusy(false);this._r195Build();}}
 }
 _r195Build(){
  const result=super._r195Build();if(!this._r232Editing||!this._r195Session)return result;
  const tools=this._v78Dialog?.querySelector('[data-r195-tools]');if(!tools)return result;
  for(const selector of ['.r195-list','[data-r195-prev]','[data-r195-next]','[data-r195-apply]','[data-r195-discard-all]','.r195-actions strong'])tools.querySelector(selector)?.setAttribute('hidden','');
  const save=tools.querySelector('[data-r195-save]');if(save)save.textContent=this._r232Text('back');
  tools.querySelector('h3').textContent=this._r232Text('edit');tools.querySelector('h3 + p').textContent=this._r232Text('hint');
  if(this._r195Session.receipt.taxStatus==='needs_review'){
   const label=document.createElement('label');label.className='r232-tax';const input=document.createElement('input');input.type='checkbox';input.dataset.r232Tax='';input.checked=!!this._r195Current().taxReviewed;
   input.onchange=()=>{this._r195Current().taxReviewed=input.checked;this._r195Session.dirty=true;this._v78Dirty=true;};label.append(input,document.createTextNode(this._r232Text('taxConfirm')));tools.querySelector('[data-r195-review]').append(label);
  }
  return result;
 }
 _r195Move(offset,index=null){if(this._r232Editing)return;return super._r195Move(offset,index);}
 _v78Close(force=false){const result=super._v78Close(force);if(!this._v78Dialog)this._r232Editing=false;return result;}
 _v116DecorateInventory(content){
  const result=super._v116DecorateInventory(content);this._r232Styles();
  for(const button of content?.querySelectorAll('[data-v112-edit-lot]')||[]){
   if(button.parentElement.classList.contains('r232-package'))continue;
   const weight=[...button.parentElement.querySelectorAll('[data-v116-lot]')].find(n=>n.dataset.v116Lot===button.dataset.v112EditLot);
   if(!weight)continue;const card=document.createElement('div');card.className='r232-package';button.before(card);card.append(button,weight);
  }return result;
 }
 _r232Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#r232Styles'))return;
  const s=document.createElement('style');s.id='r232Styles';s.textContent=`
   .r232-package{border:1px solid var(--divider-color);border-radius:16px;background:var(--card-background-color);overflow:hidden;margin:8px 0;padding:0 12px 10px}
   .r232-package .v112-package{border:0!important;background:transparent!important;margin:0!important;width:100%;box-shadow:none!important}
   .r232-package .v116-lot-weight{margin:0!important;width:100%;min-height:44px}
   .r232-dialog{color:var(--primary-text-color);background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:20px;width:min(850px,calc(100vw - 32px));max-height:85dvh;box-sizing:border-box;padding:20px;overflow:auto}
   .r232-dialog::backdrop{background:#0009}.r232-dialog header{display:flex;align-items:center;justify-content:space-between;gap:12px}.r232-dialog h2{font-size:1.2rem;margin:0}.r232-dialog p{color:var(--secondary-text-color)}
   .r232-dialog details{border:1px solid var(--divider-color);border-radius:14px;padding:12px;margin:12px 0}.r232-dialog summary{cursor:pointer;overflow-wrap:anywhere;display:flex;align-items:flex-start;gap:10px}.r232-summary-main{display:block;min-width:0;flex:1}.r232-dialog summary .r232-summary-main>span{display:block;font-size:.85rem;color:var(--secondary-text-color);margin-top:8px}.r232-dialog progress{width:100%;accent-color:var(--primary-color);margin-top:8px}.r232-receipt-remove{flex:0 0 auto;min-height:40px!important}.r232-select{display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:.85rem}.r232-select input{width:20px;height:20px;flex:0 0 20px}.r232-bulk{display:flex;flex-wrap:wrap;gap:8px;padding:12px 0;border-bottom:1px solid var(--divider-color)}
   .r232-dialog article{border-top:1px solid var(--divider-color);padding:14px 0;overflow-wrap:anywhere}.r232-dialog article>div,.r232-dialog small{margin-top:8px}.r232-dialog small{display:block;color:var(--secondary-text-color)}
   .r232-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.r232-dialog .btn{min-height:44px;white-space:normal;max-width:100%}.r232-tax{display:flex;gap:10px;align-items:center;margin:12px 0}.r232-tax input{width:22px;height:22px}
   [data-r195-tools] [hidden]{display:none!important}@media(max-width:500px){.r232-dialog{padding:14px}.r232-actions .btn{flex:1 1 auto}}
  `;this.shadowRoot.append(s);
 }
 disconnectedCallback(){clearTimeout(this._r232Timer);this._r232Timer=null;this._r232Dialog?.remove();this._r232Dialog=null;super.disconnectedCallback();}
};
