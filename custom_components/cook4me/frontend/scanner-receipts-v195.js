// Receipt review is a session over the existing product editor, not duplicate stock.
export const RECEIPT_TEXT = {
 en:{scan:'Scan receipt',saved:'Saved receipts',upload:'Receipt photo',frame:'Frame the entire receipt, then take a photo',reading:'Reading receipt…',review:'Review receipt',save:'Save whole scan for later',savedOk:'Receipt draft saved; no stock was added.',discard:'Discard this item',discardAll:'Discard whole scan',discardQuestion:'Discard this receipt draft? Products already added to stock will not be removed.',leave:'Leave this receipt? Unsaved edits will be lost. Use Save whole scan for later to keep them.',previous:'Previous item',next:'Next item',items:'Receipt items',merchant:'Purchase place / shop',date:'Purchase date',currency:'Receipt currency',total:'Printed receipt total',line:'Paid total for this line (all packages)',lineHelp:'Enter the total paid for all packages in this receipt line. Package amount below is the content of one package. Discounts/deposits are separate lines; review totals before applying.',apply:'Apply this item to stock',retry:'Retry this item',pending:'Needs review',applied:'Added to stock',applying:'Save needs retry',discarded:'Discarded',empty:'No saved receipts',new:'New receipt scan',product:'Product',discount:'Discount',deposit:'Deposit',tax:'Tax',payment:'Payment',other:'Other / non-food',kind:'Receipt line type',unknown:'Not read — enter manually',hint:'Map each product to compatible catalog ingredients. You can save incomplete items and finish later. No stock is added until Apply.',nonProduct:'This line is not a stock product. Review it or discard it.',busy:'Finish the current operation first.',photoPrivacy:'The receipt photo is sent to your selected Home Assistant AI Task. Only reviewed draft data is saved locally.',resume:'Open draft',noMore:'All receipt items have been reviewed.',switch:'Save or discard this receipt before starting another product scan.',confirmNew:'Start a new scan? Unsaved receipt edits will be lost.',sum:'Sum of product/discount/deposit lines',different:'The line sum differs from the printed total. Check discounts, deposits and unreadable lines.',unclear:'Some line amounts are unreadable. Check the receipt before applying.',note:'Receipt notes'},
 de:{scan:'Kassenbon scannen',saved:'Gespeicherte Kassenbons',upload:'Kassenbon-Foto',frame:'Den gesamten Kassenbon einrahmen und fotografieren',reading:'Kassenbon wird gelesen…',review:'Kassenbon prüfen',save:'Gesamten Scan für später speichern',savedOk:'Entwurf gespeichert; kein Vorrat hinzugefügt.',discard:'Diesen Artikel verwerfen',discardAll:'Gesamten Scan verwerfen',discardQuestion:'Diesen Kassenbon-Entwurf verwerfen? Bereits hinzugefügte Vorräte bleiben erhalten.',leave:'Kassenbon verlassen? Ungespeicherte Änderungen gehen verloren. Zum Behalten den gesamten Scan speichern.',previous:'Vorheriger Artikel',next:'Nächster Artikel',items:'Artikel des Kassenbons',merchant:'Einkaufsort / Geschäft',date:'Kaufdatum',currency:'Währung des Kassenbons',total:'Gedruckte Gesamtsumme',line:'Bezahlte Zeilensumme (alle Packungen)',lineHelp:'Den Gesamtpreis aller Packungen dieser Zeile eingeben. Die Packungsmenge unten beschreibt eine Packung. Rabatte/Pfand stehen separat; Beträge vor dem Übernehmen prüfen.',apply:'Diesen Artikel zum Vorrat hinzufügen',retry:'Diesen Artikel erneut speichern',pending:'Zu prüfen',applied:'Zum Vorrat hinzugefügt',applying:'Speichern erneut versuchen',discarded:'Verworfen',empty:'Keine gespeicherten Kassenbons',new:'Neuen Kassenbon scannen',product:'Produkt',discount:'Rabatt',deposit:'Pfand',tax:'Steuer',payment:'Zahlung',other:'Sonstiges / kein Lebensmittel',kind:'Art der Bonzeile',unknown:'Nicht lesbar — manuell eingeben',hint:'Jedes Produkt passenden Katalogzutaten zuordnen. Unvollständige Artikel können für später gespeichert werden. Vorrat wird erst mit Übernehmen hinzugefügt.',nonProduct:'Diese Zeile ist kein Vorratsprodukt. Prüfen oder verwerfen.',busy:'Zuerst den laufenden Vorgang abschließen.',photoPrivacy:'Das Kassenbon-Foto wird an die ausgewählte Home-Assistant-KI-Aufgabe gesendet. Nur die geprüften Entwurfsdaten werden lokal gespeichert.',resume:'Entwurf öffnen',noMore:'Alle Artikel wurden geprüft.',switch:'Diesen Kassenbon speichern oder verwerfen, bevor ein neues Produkt gescannt wird.',confirmNew:'Neuen Scan starten? Ungespeicherte Änderungen gehen verloren.',sum:'Summe der Produkt-, Rabatt- und Pfandzeilen',different:'Die Zeilensumme weicht von der gedruckten Summe ab. Rabatte, Pfand und unlesbare Zeilen prüfen.',unclear:'Einige Beträge sind unlesbar. Kassenbon vor dem Übernehmen prüfen.',note:'Notizen zum Kassenbon'},
 el:{scan:'Σάρωση απόδειξης',saved:'Αποθηκευμένες αποδείξεις',upload:'Φωτογραφία απόδειξης',frame:'Βάλε ολόκληρη την απόδειξη στο πλαίσιο και φωτογράφισέ την',reading:'Ανάγνωση απόδειξης…',review:'Έλεγχος απόδειξης',save:'Αποθήκευση όλης της σάρωσης για αργότερα',savedOk:'Η απόδειξη αποθηκεύτηκε ως πρόχειρο· δεν προστέθηκε απόθεμα.',discard:'Απόρριψη αυτού του προϊόντος',discardAll:'Απόρριψη όλης της σάρωσης',discardQuestion:'Να διαγραφεί το πρόχειρο της απόδειξης; Τα προϊόντα που έχουν ήδη προστεθεί στο απόθεμα δεν θα αφαιρεθούν.',leave:'Να κλείσει η απόδειξη; Οι μη αποθηκευμένες αλλαγές θα χαθούν. Αποθήκευσε όλη τη σάρωση για να συνεχίσεις αργότερα.',previous:'Προηγούμενο προϊόν',next:'Επόμενο προϊόν',items:'Προϊόντα απόδειξης',merchant:'Τόπος αγοράς / κατάστημα',date:'Ημερομηνία αγοράς',currency:'Νόμισμα απόδειξης',total:'Σύνολο που αναγράφεται στην απόδειξη',line:'Πληρωμένο σύνολο γραμμής (όλες οι συσκευασίες)',lineHelp:'Συμπλήρωσε το συνολικό ποσό για όλες τις συσκευασίες αυτής της γραμμής. Η ποσότητα παρακάτω αφορά μία συσκευασία. Οι εκπτώσεις και οι εγγυοδοσίες είναι ξεχωριστές γραμμές· έλεγξε τα ποσά πριν την εφαρμογή.',apply:'Προσθήκη αυτού του προϊόντος στο απόθεμα',retry:'Επανάληψη αποθήκευσης προϊόντος',pending:'Χρειάζεται έλεγχο',applied:'Προστέθηκε στο απόθεμα',applying:'Χρειάζεται επανάληψη αποθήκευσης',discarded:'Απορρίφθηκε',empty:'Δεν υπάρχουν αποθηκευμένες αποδείξεις',new:'Νέα σάρωση απόδειξης',product:'Προϊόν',discount:'Έκπτωση',deposit:'Εγγυοδοσία συσκευασίας',tax:'Φόρος',payment:'Πληρωμή',other:'Άλλο / μη τρόφιμο',kind:'Είδος γραμμής απόδειξης',unknown:'Δεν διαβάστηκε — συμπλήρωσε χειροκίνητα',hint:'Σύνδεσε κάθε προϊόν με συμβατά υλικά καταλόγου. Μπορείς να αποθηκεύσεις ελλιπή στοιχεία και να συνεχίσεις αργότερα. Απόθεμα προστίθεται μόνο με την Εφαρμογή.',nonProduct:'Αυτή η γραμμή δεν είναι προϊόν αποθέματος. Έλεγξέ την ή απόρριψέ την.',busy:'Ολοκλήρωσε πρώτα την τρέχουσα ενέργεια.',photoPrivacy:'Η φωτογραφία αποστέλλεται στην επιλεγμένη εργασία AI του Home Assistant. Τοπικά αποθηκεύονται μόνο τα στοιχεία του πρόχειρου.',resume:'Άνοιγμα πρόχειρου',noMore:'Ελέγχθηκαν όλα τα προϊόντα της απόδειξης.',switch:'Αποθήκευσε ή απόρριψε την απόδειξη πριν σαρώσεις νέο προϊόν.',confirmNew:'Να ξεκινήσει νέα σάρωση; Οι μη αποθηκευμένες αλλαγές θα χαθούν.',sum:'Άθροισμα προϊόντων, εκπτώσεων και εγγυοδοσιών',different:'Το άθροισμα διαφέρει από το σύνολο της απόδειξης. Έλεγξε εκπτώσεις, εγγυοδοσίες και δυσανάγνωστες γραμμές.',unclear:'Ορισμένα ποσά δεν διαβάστηκαν. Έλεγξε την απόδειξη πριν την εφαρμογή.',note:'Σημειώσεις απόδειξης'}
};
const clone=value=>structuredClone(value);
export function receiptPosition(items,index,offset){return Math.max(0,Math.min(items.length-1,index+offset));}
export function receiptTotals(receipt){
 const rows=(receipt?.items||[]).filter(row=>['product','discount','deposit'].includes(row.kind));
 const known=rows.every(row=>row.lineTotal!==null&&row.lineTotal!==''&&Number.isFinite(Number(row.lineTotal)));
 const amount=rows.reduce((sum,row)=>sum+(Number(row.lineTotal)||0),0);
 const printed=receipt?.total;
 return {amount,known,different:known&&printed!==null&&printed!==''&&Number.isFinite(Number(printed))&&Math.abs(amount-Number(printed))>0.011};
}
export function removeWeeklyReceiptSections(root){
 for(const key of ['reservedStock','leftovers','priceInventory','completedPurchases']){
  for(const node of root?.querySelectorAll?.(`[data-v179-fold="${key}"]`)||[])node.remove();
 }
 // Older Week renderers already wrapped these cards before v179 sees them.
 // Remove their stable keys too; translated heading text is not an identifier.
 for(const key of ['leftovers','prices']){
  for(const node of root?.querySelectorAll?.(`[data-v137-week-panel="${key}"]`)||[])node.remove();
 }
 for(const pair of root?.querySelectorAll?.('.two')||[]){
  if(pair.children.length===1)pair.style.gridTemplateColumns='minmax(0,1fr)';
 }
}
export const ReceiptScannerMixin=Base=>class extends Base{
 _r195Text(key){const lang=String(this._uiIngredientLanguage?.()||'en').split(/[-_]/)[0];return (RECEIPT_TEXT[lang]||RECEIPT_TEXT.en)[key]||key;}
 _v179DecorateWeek(root){const value=super._v179DecorateWeek(root);removeWeeklyReceiptSections(root);return value;}
 _r195Current(){return this._r195Session?.receipt?.items?.[this._r195Session.index];}
 _r195Flush(){
  const session=this._r195Session,item=this._r195Current(),d=this._v78Draft;
  if(!session||!item||!d||d.receiptItemId!==item.id||item.status!=='pending')return;
  if(item.productName!==d.productName){item.ingredientName='';session.suggestions.delete(item.id);d.suggestions=[];}
  for(const key of ['productName','brand','quantity','unit','packageCount','bestBefore','storageLocationId','barcode','noExpiry','containerId','openedAt','useWithinDays'])item[key]=d[key]??'';
  item.lineTotal=d.paidAmount===''?null:d.paidAmount;
  item.nutrition=clone(d.nutrition||{basisQuantity:100,basisUnit:'',values:{}});
  item.ingredientLinks=clone(this._v114Links?.()||[d.ingredient].filter(Boolean));
  Object.assign(session.receipt,{purchaseDate:d.purchaseDate||'',currency:d.paidCurrency||'',merchant:d.paidShop||''});
  session.dirty=session.dirty||this._v78Dirty;
 }
 _r195SetReceipt(receipt,index=0){
  const old=this._r195Session;
  this._r195Session={receipt:clone(receipt),index:receiptPosition(receipt.items,index,0),dirty:!receipt.id,listOpen:old?.listOpen??true,metaOpen:old?.metaOpen??(!receipt.purchaseDate||!receipt.currency),suggestions:old?.suggestions||new Map()};
  this._r195LoadItem(false);
 }
 _r195LoadItem(flush=true){
  if(flush)this._r195Flush();const session=this._r195Session,item=this._r195Current();if(!item)return;
  this._v111CancelRead?.();this._v78Submitted=null;this._v78Busy=false;this._v78Discard=false;
  const d=this._v78Fresh('manual');
  for(const key of ['productName','brand','quantity','unit','packageCount','bestBefore','storageLocationId','barcode','noExpiry','containerId','openedAt','useWithinDays'])d[key]=item[key]??'';
  Object.assign(d,{receiptItemId:item.id,productLocked:true,editorOpen:true,scanPhase:'recognized',scanNote:item.note||'',
   ingredientLinks:clone(item.ingredientLinks||[]),ingredient:clone(item.ingredientLinks?.[0]||null),suggestions:session.suggestions.get(item.id)||[],
   nutrition:clone(item.nutrition||{basisQuantity:100,basisUnit:'',values:{}}),paidAmount:item.lineTotal??'',paidCurrency:session.receipt.currency||'',
   paidShop:session.receipt.merchant||'',purchaseDate:session.receipt.purchaseDate||'',unlimited:false});
  this._v78Draft=d;this._v78Dirty=session.dirty;this._v78RenderCapture();
  void this._r195Suggestions(item,d,session);
 }
 async _r195Suggestions(item,d,session){
  if(item.kind!=='product'||item.status!=='pending'||session.suggestions.has(item.id))return;
  const signature=JSON.stringify([item.productName,item.ingredientName,item.brand]);
  try{
   const result=await this._api('cook4me/receipts/suggestions',{entry_id:this._entryId,product:{productName:item.productName,ingredientName:item.ingredientName,brand:item.brand},language:this._uiIngredientLanguage()});
   if(session!==this._r195Session||d!==this._v78Draft||signature!==JSON.stringify([item.productName,item.ingredientName,item.brand])||d.productName!==item.productName||!this._v78Alive(this._v78Dialog))return;
   session.suggestions.set(item.id,result.suggestions||[]);d.suggestions=result.suggestions||[];this._v78IngredientOptions();
  }catch(error){if(session===this._r195Session&&d===this._v78Draft)this._v78SetStatus(String(error.message||error));}
 }
 _r195Move(offset,index=null){
  if(this._v78Busy||!this._r195Session)return;
  this._r195Flush();const s=this._r195Session;s.index=index===null?receiptPosition(s.receipt.items,s.index,offset):receiptPosition(s.receipt.items,index,0);this._r195LoadItem(false);
 }
 async _r195SaveData(){
  this._r195Flush();const s=this._r195Session;if(!s)return null;
  const result=await this._api('cook4me/receipts/drafts',{entry_id:this._entryId,action:'save',receipt:clone(s.receipt),receipt_id:s.receipt.id||'',revision:s.receipt.revision||0,language:this._uiIngredientLanguage()});
  if(s!==this._r195Session)return null;
  s.receipt=result.receipt;s.dirty=false;this._v78Dirty=false;return result.receipt;
 }
 async _r195Action(action){
  if(this._v78Busy||!this._r195Session)return;
  if(action==='discardAll'&&!globalThis.confirm(this._r195Text('discardQuestion')))return;
  if(action==='discardAll'&&!this._r195Session.receipt.id){this._r195Session=null;this._v78Dirty=false;await this._r195Start(true,false);return;}
  if(action==='discard'&&!this._r195Session.receipt.id){this._r195Flush();this._r195Current().status='discarded';this._r195Session.dirty=true;this._r195Move(1);return;}
  const c=this._v78Dialog,s=this._r195Session,index=s.index;this._r195Flush();this._v78SetBusy(true);this._r195Paint();
  const alive=()=>this._v78Alive(c)&&this._r195Session===s;
  try{
   let receipt=s.receipt;
   if(action==='save'||action==='apply'&&this._r195Current().status==='pending'||!receipt.id||s.dirty&&action!=='discardAll')receipt=await this._r195SaveData();
   if(!receipt||!alive())return;
   if(action==='save'){this._r195Message=this._r195Text('savedOk');}
   else{
    const result=await this._api('cook4me/receipts/drafts',{entry_id:this._entryId,action:action==='apply'?'apply':'discard',receipt_id:receipt.id,revision:receipt.revision,
     item_id:action==='discardAll'?'':receipt.items[index].id,language:this._uiIngredientLanguage()});
    if(!alive())return;
    if(result.result?.houseIngredients)this._v78AcceptState(result.result);
    this._foodState=null;this._r195Message=(result.result?.warnings||[]).join(' ');
    if(!result.receipt){this._r195Session=null;this._v78Dirty=false;this._v78Busy=false;await this._r195Start(true);return;}
    receipt=result.receipt;
    if(action!=='apply'||receipt.items[index].status==='applied')s.index=receiptPosition(receipt.items,index,1);
   }
   s.receipt=receipt;s.dirty=false;this._v78Dirty=false;
  }catch(error){
   if(!alive())return;this._r195Message=String(error.message||error);
   // The inventory operation might have committed before the connection failed.
   // Reload frozen state for retry; never create another request ID.
   if(action==='apply'&&s.receipt.id){try{const latest=await this._api('cook4me/receipts/drafts',{entry_id:this._entryId,action:'get',receipt_id:s.receipt.id});if(alive()){s.receipt=latest.receipt;s.dirty=false;}}catch{}}
  }finally{if(alive()){this._v78Busy=false;this._r195LoadItem(false);}}
 }
 async _r195Start(force=false,camera=true){
  if(this._v78Busy)return;this._r195Flush();
  if(!force&&(this._r195Session?.dirty||this._v78Dirty)&&!globalThis.confirm(this._r195Text('confirmNew')))return;
  this._r195Session=null;this._r195Message='';this._v78Dirty=false;this._v78Submitted=null;this._r195UploadOnly=!camera;
  this._v111CancelRead?.();this._v78Draft=this._v78Fresh('receipt');
  Object.assign(this._v78Draft,{mode:'receipt',editorOpen:false,scanPhase:'scanning'});this._v78RenderCapture();
  if(camera&&!this._v180CameraUnavailable)await this._v78Camera();
 }
 async _r195List(){
  if(this._v78Busy)return;this._r195Flush();
  if(this._r195Session?.dirty&&!globalThis.confirm(this._r195Text('leave')))return;
  const c=this._v78Dialog;this._v78SetBusy(true);
  try{
   const data=await this._api('cook4me/receipts/drafts',{entry_id:this._entryId,action:'list'});if(!this._v78Alive(c))return;
   const area=c.querySelector('[data-r195-drafts]');if(!area)return;area.hidden=false;area.replaceChildren();
   if(!data.drafts?.length)area.textContent=this._r195Text('empty');
   for(const draft of data.drafts||[]){
    const button=document.createElement('button');button.type='button';button.className='btn secondary';
    button.textContent=`${draft.merchant||this._r195Text('unknown')} · ${draft.purchaseDate||'—'} · ${draft.pendingCount}/${draft.itemCount}`;
    button.title=this._r195Text('resume');
    button.onclick=async()=>{if(this._v78Busy)return;this._v78SetBusy(true);try{const data=await this._api('cook4me/receipts/drafts',{entry_id:this._entryId,action:'get',receipt_id:draft.id});if(this._v78Alive(c)){this._r195Message='';this._r195SetReceipt(data.receipt);}}catch(error){if(this._v78Alive(c))this._v78SetStatus(String(error.message||error));}finally{if(this._v78Alive(c)){this._v78Busy=false;this._r195Paint();}}};area.append(button);
   }
  }catch(error){if(this._v78Alive(c))this._v78SetStatus(String(error.message||error));}
  finally{if(this._v78Alive(c)){this._v78SetBusy(false);this._r195Paint();}}
 }
 async _v78Recognize(image){
  const c=this._v78Dialog,d=this._v78Draft;if(!d||this._v78Busy)return;
  if(d.mode!=='receipt'){
   const result=await super._v78Recognize(image);
   if(this._r195Session&&d===this._v78Draft){this._r195Flush();d.editorOpen=true;this._v78RenderCapture();}return result;
  }
  this._v111CancelRead?.();const token={};this._r195ReadToken=token;d.scanPhase='reading';this._v78SetBusy(true);this._v111Paint();
  const alive=()=>this._v78Alive(c)&&this._v78Draft===d&&this._r195ReadToken===token;
  try{
   const result=await this._api('cook4me/receipts/recognize',{entry_id:this._entryId,image,language:this._uiIngredientLanguage()});
   if(alive()){this._v78Busy=false;this._r195SetReceipt(result.receipt);}
  }catch(error){if(alive()){d.scanPhase='error';d.scanNote=String(error.message||error);this._v78SetStatus(d.scanNote);}}
  finally{if(alive()){this._v78SetBusy(false);this._v78RenderCapture();}}
 }
 async _v78CaptureFrame(){if(this._v78Draft?.mode!=='receipt')return super._v78CaptureFrame();if(this._v78Busy)return;const canvas=this._v111Canvas(false);if(canvas)await this._v78Recognize(canvas.toDataURL('image/jpeg',.9));}
 async _v80Scan(mode){if(mode==='receipt')return this._r195Start();if(this._r195Session&&['barcode','product'].includes(mode)){this._v78SetStatus(this._r195Text('switch'));return;}return super._v80Scan(mode);}
 async _v78Save(){if(this._r195Session)return this._r195Action('apply');return super._v78Save();}
 async _v113Restart(){if(this._r195Session||this._v78Draft?.mode==='receipt')return this._r195Start();return super._v113Restart();}
 _v141KeepCameraWarm(){if(this._v78Draft?.mode==='receipt'&&this._r195UploadOnly)return;return super._v141KeepCameraWarm();}
 _v79SchedulePrice(){if(this._r195Session||this._v78Draft?.mode==='receipt'){clearTimeout(this._v79PriceTimer);return;}return super._v79SchedulePrice();}
 async _v79PriceProduct(){if(this._r195Session||this._v78Draft?.mode==='receipt')return;return super._v79PriceProduct();}
 _v78Close(force=false){
  if(this._r195Session){this._r195Flush();if(!force&&this._v78Busy)return;if(!force&&this._r195Session.dirty&&!globalThis.confirm(this._r195Text('leave')))return;this._v78Dirty=false;}
  const result=super._v78Close(force);if(!this._v78Dialog){this._r195Session=null;this._r195ReadToken={};this._r195Message='';}return result;
 }
 _v78RenderCapture(){const value=super._v78RenderCapture();this._r195Build();return value;}
 _v111Paint(){const value=super._v111Paint();this._r195Paint();return value;}
 _r195Build(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d||!c.querySelector('.v78-capture-body'))return;
  this._r195Styles();
  const modes=c.querySelector('.v111-modes');
  if(modes&&!modes.querySelector('[data-v80-scan=receipt]')){
   const button=document.createElement('button');button.type='button';button.className='v111-icon';button.dataset.v80Scan='receipt';button.title=button.ariaLabel=this._r195Text('scan');button.innerHTML='<ha-icon icon="mdi:receipt-text-scan" aria-hidden="true"></ha-icon>';button.onclick=()=>void this._v80Scan('receipt');const nutrients=modes.querySelector('[data-v80-scan=nutrition]');if(nutrients)nutrients.after(button);else modes.append(button);
  }
  const e=v=>this._escape(String(v??'')),t=k=>e(this._r195Text(k));
  // Product editing has no receipt toolbar or saved/photo shortcuts. Receipt
  // review controls exist only while reviewing an actual receipt session.
  let tools=c.querySelector('[data-r195-tools]');
  if(!this._r195Session){tools?.remove();this._r195Paint();return;}
  if(!tools){tools=document.createElement('section');tools.dataset.r195Tools='';tools.className='r195-tools';
   tools.innerHTML='<div data-r195-review></div>';
   c.querySelector('.v78-capture-body').before(tools);
  }
  const s=this._r195Session,area=tools.querySelector('[data-r195-review]');if(s){const r=s.receipt,item=this._r195Current();
   const field=(key,label,type='text')=>`<label class="field">${t(label)}<input data-r195-global="${key}" type="${type}" value="${e(r[key]??'')}" ${key==='currency'?'maxlength="3"':''}></label>`;
   area.innerHTML=`<h3>${t('review')}</h3><p>${t('hint')}</p><details class="r195-meta" ${s.metaOpen?'open':''}><summary>${e(r.merchant||this._r195Text('merchant'))} · ${e(r.purchaseDate||'—')} · ${e(r.currency)}</summary><div class="r195-globals">${field('merchant','merchant')}${field('purchaseDate','date','date')}${field('currency','currency')}${field('total','total','number')}</div></details><details class="r195-list" ${s.listOpen?'open':''}><summary>${t('items')} (${r.items.length})</summary><div>${r.items.map((row,i)=>`<button type="button" class="btn secondary" data-r195-index="${i}" aria-current="${i===s.index?'true':'false'}">${i+1}. ${e(row.productName||this._r195Text('unknown'))} · ${e(row.lineTotal??'—')} ${e(r.currency)} · ${t(row.status||'pending')}</button>`).join('')}</div></details><div class="r195-actions"><button type="button" class="btn secondary" data-r195-prev aria-label="${t('previous')}" title="${t('previous')}">←</button><strong>${s.index+1} / ${r.items.length} · ${t(item.status||'pending')}</strong><button type="button" class="btn secondary" data-r195-next aria-label="${t('next')}" title="${t('next')}">→</button><button type="button" class="btn" data-r195-apply>${t(item.status==='applying'?'retry':'apply')}</button></div><div class="r195-actions"><button type="button" class="btn secondary" data-r195-save>${t('save')}</button><button type="button" class="btn secondary" data-r195-discard>${t('discard')}</button><button type="button" class="btn secondary" data-r195-discard-all>${t('discardAll')}</button></div><label class="field">${t('kind')}<select data-r195-kind>${['product','discount','deposit','tax','total','payment','other'].map(kind=>`<option value="${kind}" ${item.kind===kind?'selected':''}>${t(kind)}</option>`).join('')}</select></label><div data-r195-total role="status"></div><p data-r195-note></p><p data-r195-message role="status" aria-live="polite">${e(this._r195Message||'')}</p>`;
   area.querySelector('.r195-list').ontoggle=event=>{s.listOpen=event.target.open;};area.querySelector('.r195-meta').ontoggle=event=>{s.metaOpen=event.target.open;};
   for(const input of area.querySelectorAll('[data-r195-global]'))input.oninput=event=>{const key=input.dataset.r195Global,value=key==='currency'?event.target.value.toUpperCase():event.target.value;r[key]=value;s.dirty=true;this._v78Dirty=true;const draftKey={merchant:'paidShop',purchaseDate:'purchaseDate',currency:'paidCurrency'}[key];if(draftKey){d[draftKey]=value;const related=c.querySelector(draftKey==='paidShop'?'[data-v79-shop]':draftKey==='paidCurrency'?'[data-v79-paid-currency]':'main [data-draft=purchaseDate]');if(related)related.value=value;}this._r195Paint();};
   area.querySelector('[data-r195-kind]').onchange=event=>{item.kind=event.target.value;s.dirty=true;this._r195Paint();};
   area.querySelector('[data-r195-prev]').onclick=()=>this._r195Move(-1);area.querySelector('[data-r195-next]').onclick=()=>this._r195Move(1);
   area.querySelectorAll('[data-r195-index]').forEach(b=>b.onclick=()=>this._r195Move(0,Number(b.dataset.r195Index)));
   for(const [selector,action] of [['save','save'],['apply','apply'],['discard','discard'],['discard-all','discardAll']])area.querySelector(`[data-r195-${selector}]`).onclick=()=>void this._r195Action(action);
   const paid=c.querySelector('[data-v79-paid]');if(paid?.parentElement?.firstChild)paid.parentElement.firstChild.textContent=this._r195Text('line');
   if(paid)paid.min=item.kind==='product'?'0':'';
   const help=c.querySelector('.v79-product-price > p.muted');if(help)help.textContent=this._r195Text('lineHelp');
   const estimate=c.querySelector('[data-v79-estimate]');if(estimate)estimate.hidden=true;
   for(const control of c.querySelectorAll('[data-v144-unlimited-control]'))control.hidden=true;
  }else area.replaceChildren();
  if(!c._r195Navigation){c._r195Navigation=true;let start=null;
   const editable=target=>target.closest?.('input,select,textarea,button,a,[contenteditable]');
   c.addEventListener('change',event=>{if(this._r195Session&&event.target.matches?.('[data-draft=productName]')){this._r195Flush();void this._r195Suggestions(this._r195Current(),this._v78Draft,this._r195Session);}});
   c.addEventListener('input',event=>{if(this._r195Session&&event.target.closest?.('[data-v78-form]')){this._r195Flush();this._r195Paint();}});
   c.addEventListener('keydown',event=>{if(!this._r195Session||editable(event.target)||event.altKey||event.ctrlKey||event.metaKey)return;if(['ArrowLeft','ArrowRight'].includes(event.key)){event.preventDefault();event.stopPropagation();this._r195Move(event.key==='ArrowLeft'?-1:1);}});
   c.addEventListener('touchstart',event=>{start=this._r195Session&&!editable(event.target)&&event.touches.length===1?{x:event.touches[0].clientX,y:event.touches[0].clientY}:null;},{passive:true});
   c.addEventListener('touchend',event=>{if(!start||!event.changedTouches?.[0])return;const dx=event.changedTouches[0].clientX-start.x,dy=event.changedTouches[0].clientY-start.y;start=null;if(Math.abs(dx)>70&&Math.abs(dx)>Math.abs(dy)*2)this._r195Move(dx<0?1:-1);},{passive:true});
  }
  this._r195Paint();
 }
 _r195Paint(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;const s=this._r195Session,item=this._r195Current(),busy=!!this._v78Busy;
  c.classList.toggle('r195-receipt',!!s||d.mode==='receipt');
  if(d.mode==='receipt'){
   const instruction=c.querySelector('[data-v111-instruction]');if(instruction)instruction.textContent=this._r195Text('frame');
   const heading=c.querySelector('[data-v111-result] strong');if(heading&&d.scanPhase==='reading')heading.textContent=this._r195Text('reading');
   const apply=c.querySelector('[data-v112-apply]');if(apply)apply.hidden=true;
  }
  const tools=c.querySelector('[data-r195-tools]');if(!tools)return;
  tools.querySelectorAll('button,input,select').forEach(node=>node.disabled=busy);
  if(!s)return;
  const locked=item?.status!=='pending';const form=c.querySelector('[data-v78-form] fieldset');if(form)form.disabled=busy||locked;
  const apply=tools.querySelector('[data-r195-apply]');if(apply)apply.disabled=busy||!['pending','applying'].includes(item.status)||item.kind!=='product';
  const discard=tools.querySelector('[data-r195-discard]');if(discard)discard.disabled=busy||item.status!=='pending';
  const kind=tools.querySelector('[data-r195-kind]');if(kind)kind.disabled=busy||locked;
  const prev=tools.querySelector('[data-r195-prev]'),next=tools.querySelector('[data-r195-next]');if(prev)prev.disabled=busy||s.index===0;if(next)next.disabled=busy||s.index===s.receipt.items.length-1;
  for(const button of c.querySelectorAll('[data-v80-scan="product"],[data-v80-scan="barcode"],[data-v78-mode="product"],[data-v78-mode="barcode"],[data-v78-native]'))button.disabled=true;
  if(locked)for(const button of c.querySelectorAll('[data-v80-scan],[data-v78-file],[data-v78-take]'))button.disabled=true;
  for(const selector of ['[data-v112-apply]','[data-v113-restart]']){const button=c.querySelector(selector);if(button)button.hidden=true;}
  const note=tools.querySelector('[data-r195-note]');if(note)note.textContent=[item.originalName!==item.productName?item.originalName:'',s.receipt.note,item.note,...(item.warnings||[]),item.kind!=='product'?this._r195Text('nonProduct'):''].filter(Boolean).join(' · ');
  const totals=receiptTotals(s.receipt),total=tools.querySelector('[data-r195-total]');if(total)total.textContent=`${this._r195Text('sum')}: ${totals.amount.toFixed(2)} ${s.receipt.currency||''}${!totals.known?' · '+this._r195Text('unclear'):totals.different?' · '+this._r195Text('different'):''}`;
 }
 _r195Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#r195Styles'))return;
  const style=document.createElement('style');style.id='r195Styles';style.textContent=`
   .r195-tools{padding:12px 16px;border-block:1px solid var(--divider-color);display:grid;gap:10px;background:var(--card-background-color)}
   .r195-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.r195-actions .btn{white-space:normal!important;overflow-wrap:anywhere;min-height:44px}
   .r195-meta summary,.r195-list summary{cursor:pointer;padding:9px 0;overflow-wrap:anywhere}.r195-globals{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.r195-globals input{width:100%;box-sizing:border-box;min-height:42px}
   .r195-list>div,.r195-drafts{display:flex;flex-direction:column;gap:6px;max-height:220px;overflow:auto}.r195-list button{text-align:start;white-space:normal!important}.r195-list [aria-current=true]{border:2px solid var(--primary-color)}
   .r195-upload{position:relative;overflow:hidden}.r195-upload input{position:absolute;inset:0;opacity:0;width:100%;cursor:pointer}
   .r195-receipt .v79-product-price [data-v79-estimate],.r195-receipt [data-v144-unlimited-control]{display:none!important}
   .r195-receipt .v180-manual-only .v111-guide-wrap{display:flex!important}
   .r195-tools [hidden]{display:none!important}.r195-tools h3,.r195-tools p{margin:0}.r195-tools small{color:var(--secondary-text-color)}
   @media(max-width:500px){.r195-globals{grid-template-columns:1fr}.r195-actions .btn{flex:1 1 auto}.r195-actions [data-r195-prev],.r195-actions [data-r195-next]{flex:0 0 44px}}
  `;this.shadowRoot.append(style);
 }
};
