// Manual product editing uses the existing scanner/store API, never a second stock path.
export const EDITOR_TEXT = {
 en:{lookup:'Search barcode',save:'Save',discard:'Discard',retry:'Retry save',barcode:'Enter an 8, 12, 13 or 14 digit barcode.',quantity:'Enter a positive package amount.',unit:'Choose a package unit.',ingredient:'Select at least one compatible catalog ingredient.',packages:'Enter a whole number of packages from 1 to 100.',number:'Enter a finite, non-negative number.',currency:'Enter the three-letter currency for the paid price.',basis:'Choose the nutrient basis: per 100 g or per 100 ml.',priceBasis:'Enter a positive paid-price basis and its unit.',date:'Enter a valid date.',days:'Enter a whole number of days from 1 to 3650.',length:'Shorten this value to the permitted length.',saved:'Product saved. A new empty form is ready.',discarded:'Unsaved changes discarded. A new empty form is ready.',found:'Product found. Existing details were kept; review the ingredient suggestions.',notFound:'No product was found. Your entered details were kept; enter the product manually.',busy:'Finish the current operation before leaving.',uncertain:'The save needs a retry. Retry the same request before starting another product.',confirm:'Discard unsaved product changes?',purchaseDate:'Enter the purchase date before applying this receipt item.'},
 de:{lookup:'Barcode suchen',save:'Speichern',discard:'Verwerfen',retry:'Erneut speichern',barcode:'Einen Barcode mit 8, 12, 13 oder 14 Ziffern eingeben.',quantity:'Eine positive Packungsmenge eingeben.',unit:'Eine Packungseinheit auswählen.',ingredient:'Mindestens eine passende Katalogzutat auswählen.',packages:'Eine ganze Packungsanzahl von 1 bis 100 eingeben.',number:'Eine endliche, nicht negative Zahl eingeben.',currency:'Die dreistellige Währung des bezahlten Preises eingeben.',basis:'Die Nährwertbasis auswählen: je 100 g oder 100 ml.',priceBasis:'Eine positive Preisbezugsmenge und ihre Einheit eingeben.',date:'Ein gültiges Datum eingeben.',days:'Eine ganze Anzahl von 1 bis 3650 Tagen eingeben.',length:'Diesen Wert auf die zulässige Länge kürzen.',saved:'Produkt gespeichert. Ein neues leeres Formular ist bereit.',discarded:'Ungespeicherte Änderungen verworfen. Ein neues leeres Formular ist bereit.',found:'Produkt gefunden. Vorhandene Angaben wurden beibehalten; die Zutatenvorschläge prüfen.',notFound:'Kein Produkt gefunden. Deine Angaben wurden beibehalten; das Produkt manuell eingeben.',busy:'Den laufenden Vorgang vor dem Verlassen abschließen.',uncertain:'Das Speichern muss wiederholt werden. Dieselbe Anfrage erneut senden, bevor ein neues Produkt begonnen wird.',confirm:'Ungespeicherte Produktänderungen verwerfen?',purchaseDate:'Vor dem Übernehmen dieses Bonartikels das Kaufdatum eingeben.'},
 el:{lookup:'Αναζήτηση barcode',save:'Αποθήκευση',discard:'Απόρριψη',retry:'Επανάληψη αποθήκευσης',barcode:'Συμπλήρωσε barcode με 8, 12, 13 ή 14 ψηφία.',quantity:'Συμπλήρωσε θετική ποσότητα συσκευασίας.',unit:'Επίλεξε μονάδα συσκευασίας.',ingredient:'Επίλεξε τουλάχιστον ένα συμβατό υλικό καταλόγου.',packages:'Συμπλήρωσε ακέραιο αριθμό συσκευασιών από 1 έως 100.',number:'Συμπλήρωσε έγκυρο, μη αρνητικό αριθμό.',currency:'Συμπλήρωσε τον κωδικό τριών γραμμάτων για το νόμισμα αγοράς.',basis:'Επίλεξε βάση διατροφικών στοιχείων: ανά 100 γρ. ή 100 ml.',priceBasis:'Συμπλήρωσε θετική ποσότητα αναφοράς της τιμής και τη μονάδα της.',date:'Συμπλήρωσε έγκυρη ημερομηνία.',days:'Συμπλήρωσε ακέραιο αριθμό ημερών από 1 έως 3650.',length:'Μείωσε το μήκος αυτού του πεδίου στο επιτρεπόμενο όριο.',saved:'Το προϊόν αποθηκεύτηκε. Η νέα κενή φόρμα είναι έτοιμη.',discarded:'Οι μη αποθηκευμένες αλλαγές απορρίφθηκαν. Η νέα κενή φόρμα είναι έτοιμη.',found:'Το προϊόν βρέθηκε. Τα υπάρχοντα στοιχεία διατηρήθηκαν· έλεγξε τα προτεινόμενα υλικά.',notFound:'Το προϊόν δεν βρέθηκε. Τα στοιχεία σου διατηρήθηκαν· συμπλήρωσε το προϊόν χειροκίνητα.',busy:'Ολοκλήρωσε την τρέχουσα ενέργεια πριν κλείσεις τη φόρμα.',uncertain:'Χρειάζεται επανάληψη αποθήκευσης. Επανάλαβε το ίδιο αίτημα πριν ξεκινήσεις άλλο προϊόν.',confirm:'Να απορριφθούν οι μη αποθηκευμένες αλλαγές του προϊόντος;',purchaseDate:'Συμπλήρωσε την ημερομηνία αγοράς πριν προσθέσεις αυτό το προϊόν της απόδειξης.'}
};
const copy=value=>structuredClone(value);
const blank=value=>value===null||value===undefined||String(value).trim()==='';
export const editorNumber=value=>blank(value)||typeof value==='boolean'?NaN:Number(String(value).trim().replace(',','.'));
export function editorBarcode(value){
 const code=String(value??'').replace(/[\s-]+/g,'');
 return /^(?:[0-9]{8}|[0-9]{12,14})$/.test(code)?code:null;
}
function validDate(value){
 if(!/^\d{4}-\d{2}-\d{2}$/.test(String(value)))return false;
 const date=new Date(`${value}T00:00:00Z`);
 return Number.isFinite(+date)&&date.toISOString().slice(0,10)===value;
}
const keyOf=row=>row?.key||row?.ingredientId||row?.id||'';
export function editorIssues(d,links=[],receipt=false){
 const unlimited=!!d.unlimited&&!d.editLotId&&!receipt;
 const out=[],add=(field,message)=>out.push({field,message});
 for(const field of ['productName','brand','paidShop'])if(String(d[field]??'').length>300)add(field,'length');
 if(!unlimited&&(!Number.isFinite(editorNumber(d.quantity))||editorNumber(d.quantity)<=0))add('quantity','quantity');
 if(!unlimited&&blank(d.unit))add('unit','unit');
 for(const field of ['bestBefore','purchaseDate','openedAt'])if(!(field==='bestBefore'&&d.noExpiry)&&!blank(d[field])&&!validDate(d[field]))add(field,'date');
 if(receipt&&blank(d.purchaseDate))add('purchaseDate','purchaseDate');
 if(!unlimited&&!d.editLotId&&(!Number.isInteger(editorNumber(d.packageCount))||editorNumber(d.packageCount)<1||editorNumber(d.packageCount)>100))add('packageCount','packages');
 if(!blank(d.barcode)&&!editorBarcode(d.barcode))add('barcode','barcode');
 if(!links.length||links.some(row=>!keyOf(row)||blank(row?.name)))add('ingredient','ingredient');
 if(!unlimited&&!blank(d.paidAmount)){
  if(!Number.isFinite(editorNumber(d.paidAmount))||editorNumber(d.paidAmount)<0)add('paidAmount','number');
  if(!/^[A-Z]{3}$/.test(String(d.paidCurrency??'').trim().toUpperCase()))add('paidCurrency','currency');
  if(d.editLotId&&!blank(d.paidBasisQuantity)){
   if(!Number.isFinite(editorNumber(d.paidBasisQuantity))||editorNumber(d.paidBasisQuantity)<=0)add('paidBasisQuantity','priceBasis');
   if(blank(d.paidBasisUnit||d.unit))add('paidBasisUnit','priceBasis');
  }
 }
 const values=Object.entries(unlimited?{}:d.nutrition?.values||{}).filter(([,value])=>!blank(value));
 if(values.length&&!['g','ml'].includes(d.nutrition?.basisUnit))add('nutritionBasis','basis');
 for(const [name,value] of values)if(!Number.isFinite(editorNumber(value))||editorNumber(value)<0)add(`nutrient:${name}`,'number');
 if(!blank(d.useWithinDays)&&(!Number.isInteger(editorNumber(d.useWithinDays))||editorNumber(d.useWithinDays)<1||editorNumber(d.useWithinDays)>3650))add('useWithinDays','days');
 return out;
}
function lookupName(d,result){
 const p=result.product||{},m=result.mapping||{},code=String(result.barcode||d.barcode||'');
 return p.productName||p.genericName||(p.name!==code?p.name:'')||m.productName||m.ingredient?.name||m.ingredientLinks?.[0]?.name||'';
}
export function mergeBarcodeDetails(d,result,links=[]){
 // Fill blanks only. In an edit, quantity may be REMAINING stock, not package size.
 const out=copy(d),p=result.product||{},m=result.mapping||{};
 if(blank(out.productName))out.productName=lookupName(d,result);
 if(blank(out.brand))out.brand=p.brand||m.brand||'';
 if(blank(out.quantity)){
  out.quantity=p.quantity??m.quantity??'';
  if(!blank(out.quantity))out.unit=p.unit||m.unit||out.unit||'';
 }else if(blank(out.unit))out.unit=p.unit||m.unit||'';
 out.ingredientLinks=copy(links.length?links:m.ingredientLinks?.length?m.ingredientLinks:[m.ingredient].filter(Boolean));
 out.ingredient=out.ingredientLinks[0]||null;
 out.suggestions=copy(result.suggestions||[]);
 const nutrition=p.nutrition||m.nutrition;
 // Never put a new mass basis under existing, unqualified nutrient values.
 if(nutrition){
  const current=out.nutrition||{basisUnit:'',values:{}};
  const populated=Object.values(current.values||{}).some(value=>!blank(value));
  if(!populated)out.nutrition=copy(nutrition);
  else if(current.basisUnit===nutrition.basisUnit&&Number(current.basisQuantity||100)===Number(nutrition.basisQuantity||100)){
   out.nutrition=copy(current);
   for(const [key,value] of Object.entries(nutrition.values||{}))if(blank(out.nutrition.values[key]))out.nutrition.values[key]=value;
  }
 }
 return out;
}
export function editorRequest(d,links,extras,entryId,language){
 const ingredient=links[0],values=Object.fromEntries(Object.entries(d.nutrition?.values||{}).filter(([,v])=>!blank(v)).map(([k,v])=>[k,editorNumber(v)]));
 const request={...copy(extras||{}),entry_id:entryId,request_id:d.requestId,language,
  ingredient:{key:keyOf(ingredient),name:ingredient.name},ingredient_links:links.map(row=>({key:keyOf(row),name:row.name})),
  quantity:editorNumber(d.quantity),unit:String(d.unit||'').trim(),package_count:d.editLotId?1:editorNumber(d.packageCount),best_before:d.noExpiry?'':d.bestBefore||'',
  lot_metadata:Object.fromEntries(['productName','brand','barcode','storageLocationId','containerId','purchaseDate','openedAt','useWithinDays','noExpiry','applyOpeningExpiry','openingRuleId','openingConditionsConfirmed'].map(key=>[key,d[key]??'']))};
 if(!blank(d.barcode))request.lot_metadata.barcode=editorBarcode(d.barcode);
 if(Object.keys(values).length)request.nutrition={basisQuantity:100,basisUnit:d.nutrition.basisUnit,values};
 if(!blank(d.paidAmount)){
  request.paid_price={...(request.paid_price||{}),amount:editorNumber(d.paidAmount),currency:String(d.paidCurrency).trim().toUpperCase(),location:d.paidShop||''};
  if(d.editLotId&&!blank(d.paidBasisQuantity))Object.assign(request.paid_price,{basisQuantity:editorNumber(d.paidBasisQuantity),basisUnit:d.paidBasisUnit||d.unit});
 }else delete request.paid_price;
 if(d.editLotId)Object.assign(request,{edit_lot_id:d.editLotId,expected_version:d.expectedVersion});
 if(d.unlimited&&!d.editLotId){request.unlimited=true;request.package_count=1;request.quantity=Number.isFinite(request.quantity)&&request.quantity>0?request.quantity:1;request.unit=request.unit||'pcs';delete request.paid_price;delete request.nutrition;}
 return request;
}
const FIELDS={
 barcode:'[data-v112-barcode-edit]',packageCount:'[data-v112-count-edit]',ingredient:'[data-v78-search]',nutritionBasis:'[data-v78-basis]',
 containerId:'[data-v154-container]',paidAmount:'[data-v79-paid]',paidCurrency:'[data-v79-paid-currency]',paidShop:'[data-v79-shop]',paidBasisQuantity:'[data-v112-price-basis]',paidBasisUnit:'[data-v112-price-unit]'
};
const selector=field=>FIELDS[field]||(field.startsWith('nutrient:')?`[data-nutrient="${field.slice(9)}"]`:`main [data-draft="${field}"]`);
export function editorServerIssue(error){
 const text=String(error?.message||error||'');
 const fields=[['barcode','barcode'],['ingredient','ingredient'],['container','containerId'],['storage','storageLocationId'],['purchase date','purchaseDate'],['best-before','bestBefore'],['opened','openedAt'],['use-within','useWithinDays'],['currency','paidCurrency'],['package count','packageCount'],['nutrition','nutritionBasis'],['paid price','paidAmount'],['price basis','paidBasisQuantity'],['quantity','quantity'],['unit','unit']];
 const field=fields.find(([term])=>text.toLowerCase().includes(term))?.[1];
 return field?{field,text}:null;
}
export const ProductEditorMixin=Base=>class extends Base{
 _v196Text(key){const lang=String(this._uiIngredientLanguage?.()||this._langCode?.()||'en').split(/[-_]/)[0];return (EDITOR_TEXT[lang]||EDITOR_TEXT.en)[key]||EDITOR_TEXT.en[key]||key;}
 _v196Links(){return this._v114Links?.()||[this._v78Draft?.ingredient].filter(Boolean);}
 _v196Notice(message){this._v196Message=String(message||'');this._v196Decorate();}
 _v196Focus(target){
  const c=this._v78Dialog,d=this._v78Draft,epoch=this._v196FocusEpoch=(this._v196FocusEpoch||0)+1;
  requestAnimationFrame(()=>{
   if(epoch!==this._v196FocusEpoch||!this._v78Alive(c)||d!==this._v78Draft)return;
   const node=typeof target==='string'?c.querySelector(target):target;
   if(!node?.isConnected||node.disabled)return;
   for(let parent=node.parentElement;parent&&parent!==c;parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;
   if(node.closest('[hidden]'))return;
   if(!node.matches('input,select,textarea,button,a[href],[tabindex]'))node.tabIndex=-1;
   node.scrollIntoView?.({block:'nearest',behavior:'auto'});node.focus?.({preventScroll:true});
  });
 }
 _v196ClearErrors(){
  const c=this._v78Dialog;
  for(const node of c?.querySelectorAll('[data-v196-invalid]')||[]){
   const id=node.dataset.v196Invalid;node.removeAttribute('aria-invalid');delete node.dataset.v196Invalid;
   const ids=(node.getAttribute('aria-describedby')||'').split(/\s+/).filter(value=>value&&value!==id);
   if(ids.length)node.setAttribute('aria-describedby',ids.join(' '));else node.removeAttribute('aria-describedby');
  }
  for(const node of c?.querySelectorAll('[data-v196-field-error]')||[])node.remove();
  this._v196FieldIssue=null;
 }
 _v196Issue(issue){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  this._v196ClearErrors();this._v196FieldIssue=issue;
  d.editorOpen=true;d.scanPhase='error';d.scanNote=issue.text||this._v196Text(issue.message);
  this._v111Paint();this._v196Notice(d.scanNote);
  const node=c.querySelector(selector(issue.field));
  if(node){
   const note=document.createElement('small'),id='v196-field-error';note.id=id;note.dataset.v196FieldError='';note.className='v196-field-error';note.textContent=d.scanNote;
   node.setAttribute('aria-invalid','true');node.dataset.v196Invalid=id;
   node.setAttribute('aria-describedby',[(node.getAttribute('aria-describedby')||''),id].filter(Boolean).join(' '));
   (node.closest('label')||node).after(note);this._v196Focus(node);
  }else this._v196Focus('[data-v196-status]');
 }
 _v196FirstIssue(receipt=false){
  const d=this._v78Draft,c=this._v78Dialog;if(!d)return null;
  const issues=editorIssues(d,this._v196Links(),receipt),controls=[...c?.querySelectorAll('input,select,textarea')||[]];
  for(const node of controls)if(node.willValidate&&node.validity?.valid===false){
   const field=node.dataset?.draft||Object.keys(FIELDS).find(key=>node.matches(FIELDS[key]))||(node.dataset?.nutrient?`nutrient:${node.dataset.nutrient}`:'');
   if(field&&!issues.some(issue=>issue.field===field))issues.push({field,text:node.validationMessage,message:'number'});
  }
  const index=issue=>{const n=controls.indexOf(c?.querySelector(selector(issue.field)));return n<0?Number.MAX_SAFE_INTEGER:n;};
  return issues.sort((a,b)=>index(a)-index(b))[0]||null;
 }
 _v196FocusNext(){
  if(this._r195Session&&this._r195Current()?.status!=='pending'){this._v196Focus('[data-r195-apply]:not(:disabled), [data-r195-next]:not(:disabled), [data-r195-save]');return;}
  const issue=this._v196FirstIssue(!!this._r195Session);
  this._v196Focus(issue?selector(issue.field):this._r195Session?'main [data-draft="productName"]':'[data-v196-save]');
 }
 _v196Reset(message){
  if(this._r195Session)return;
  this._v111CancelRead?.();this._v78StopCamera?.();this._v196LookupToken=null;this._v196ClearErrors();
  this._v78Draft=this._v78Fresh('manual');
  Object.assign(this._v78Draft,{storageLocationId:'',editorOpen:true,editLotId:'',expectedVersion:'',scanPhase:'idle',scanNote:''});
  this._v78Submitted=null;this._v78Saved=false;this._v78Dirty=false;this._v78Discard=false;this._v78Busy=false;
  this._v196SavingDraft=null;this._v196LastField='';this._v112SkipBarcode='';this._v112LastSaved='';this._v78Status='';this._v196Message=this._v196Text(message);
  this._v78RenderCapture();this._v196Focus('main [data-draft="productName"]');
 }
 _v196Discard(){
  if(this._v78Busy||this._v78Submitted||this._r195Session)return;
  this._v196Reset('discarded');
 }
 async _v196Lookup(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d||this._v78Busy||this._v78Submitted)return;
  if(this._r195Session&&(this._r195Current()?.status!=='pending'||this._r195Current()?.kind!=='product'))return;
  const input=c.querySelector('[data-v112-barcode-edit]');if(input)d.barcode=input.value;
  const code=editorBarcode(d.barcode);if(!code){this._v196Issue({field:'barcode',message:'barcode'});return;}
  this._v196ClearErrors();this._v111CancelRead?.();const token={};this._v196LookupToken=token;
  const snapshot=copy(d),links=copy(this._v196Links());
  d.barcode=code;d.editorOpen=true;d.scanPhase='looking';d.scanNote='';this._v196Message='';this._v78SetBusy(true);
  const alive=()=>this._v78Alive(c)&&this._v78Draft===d&&this._v196LookupToken===token&&d.barcode===code;
  let issue=null;
  try{
   const result=await this._api('cook4me/v33/barcode_lookup',{entry_id:this._entryId,barcode:code,language:this._uiIngredientLanguage()});
   if(!alive())return;
   // Older API decorators may update ingredientLinks. Explicit user choices win.
   Object.assign(d,mergeBarcodeDetails({...snapshot,barcode:code},result,links),{editorOpen:true,scanPhase:'recognized',scanNote:'',productLocked:true});
   d.scanRecognized=!!(lookupName(d,result)&&(result.product?.found!==false||result.mapping?.productName||result.mapping?.ingredient||result.mapping?.ingredientLinks?.length));
   this._v78Dirty=true;
   this._v196Message=this._v196Text(d.scanRecognized?'found':'notFound');
   if(this._r195Session){this._r195Flush();this._r195Session.suggestions.set(d.receiptItemId,d.suggestions);}
  }catch(error){
   if(!alive())return;d.ingredientLinks=links;d.ingredient=snapshot.ingredient;d.scanPhase='error';d.scanNote=String(error.message||error);
   issue={field:'barcode',text:d.scanNote};
  }finally{
   if(alive()){
    this._v78Busy=false;this._v196LookupToken=null;this._v78RenderCapture();
    if(issue)this._v196Issue(issue);
    else if(!d.scanRecognized)this._v196Focus('main [data-draft="productName"]');
    else this._v196FocusNext();
   }
  }
 }
 async _v78Save(){
  if(this._r195Session)return super._v78Save();
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d||this._v78Busy)return;
  if(!(d.editorOpen||d.mode==='manual'||d.editLotId||this._v196SavingDraft===d))return super._v78Save();
  this._v196ClearErrors();
  if(!this._v78Submitted){
   const issue=this._v196FirstIssue();if(issue){this._v196Issue(issue);return;}
   this._v78Submitted=editorRequest(d,this._v196Links(),this._v78ProductExtras?.(),this._entryId,this._uiIngredientLanguage());
  }
  this._v196SavingDraft=d;this._v111CancelRead?.();this._v196Message='';d.scanPhase='saving';d.scanNote='';
  this._v78SetBusy(true);const context=this._prefKey();let success=false,errorMessage='',validation=false;
  try{
   const result=await this._api('cook4me/v33/product_add',this._v78Submitted);
   if(context!==this._prefKey()||!this._v78Alive(c)||d!==this._v78Draft)return;
   this._v78AcceptState(result);this._foodState=null;
   if(result.warnings?.length)errorMessage=result.warnings.join(' ');else success=true;
   if(this._tab==='profile')this._renderTab();
  }catch(error){
   if(context!==this._prefKey()||!this._v78Alive(c)||d!==this._v78Draft)return;
   errorMessage=String(error.message||error);validation=error.code==='product_validation';
   if(validation)this._v78Submitted=null;
  }finally{
   if(context===this._prefKey()&&this._v78Alive(c)&&d===this._v78Draft){
    this._v78Busy=false;
    if(success){this._v196SavingDraft=null;this._v196Reset('saved');}
    else{
     d.editorOpen=true;d.scanPhase='error';d.scanNote=errorMessage;this._v196Message=errorMessage;this._v78RenderCapture();
     const issue=validation?(this._v196FirstIssue()||editorServerIssue({message:errorMessage})):null;
     if(issue)this._v196Issue(issue);else this._v196Focus(validation?'[data-v196-status]':'[data-v196-save]');
    }
   }
  }
 }
 _v78Close(force=false){
  const c=this._v78Dialog,d=this._v78Draft;
  if(c&&!force&&!this._r195Session&&(this._v78Busy||this._v78Submitted)){
   this._v196Notice(this._v196Text(this._v78Busy?'busy':'uncertain'));this._v196Focus(this._v78Busy?'[data-v196-status]':'[data-v196-save]');return;
  }
  const active=this.shadowRoot?.activeElement;
  this._v196ReturnField=active?.dataset?.draft?selector(active.dataset.draft):Object.keys(FIELDS).map(key=>FIELDS[key]).find(value=>active?.matches?.(value))||this._v196LastField||'main [data-draft="productName"]';
  const result=super._v78Close(force);
  if(this._v78Dialog===c&&this._v78Discard){this._v196Decorate();this._v196Focus('[data-v78-keep]');}
  else if(c&&this._v78Dialog===c&&this._r195Session&&!force&&!this._v78Busy)this._v196FocusNext();
  else if(this._v78Dialog!==c){this._v196LookupToken=null;this._v196FocusEpoch=(this._v196FocusEpoch||0)+1;this._v196Message='';this._v196FieldIssue=null;}
  return result;
 }
 async _v78Open(...args){const result=await super._v78Open(...args);if(this._v78Draft?.mode==='manual'&&!this._r195Session)this._v196Focus('main [data-draft="productName"]');return result;}
 async _v112EditLot(...args){const result=await super._v112EditLot(...args);if(this._v78Draft?.editLotId)this._v196Focus('main [data-draft="productName"]');return result;}
 _v112Editor(open,section){if(this._v78Busy||this._v78Submitted)return;const value=super._v112Editor(open,section);if(open)this._v196Focus(selector(section==='date'?'bestBefore':section==='nutrition'?'nutritionBasis':'productName'));return value;}
 _v141DecorateError(){if(this._v196FieldIssue)return;return super._v141DecorateError?.();}
 _r195LoadItem(...args){const result=super._r195LoadItem(...args);this._v196FocusNext();return result;}
 async _r195Action(action){
  if(this._v78Busy)return;
  if(action==='apply'&&this._r195Current()?.status==='pending'&&this._r195Current()?.kind==='product'){
   this._v196ClearErrors();const issue=this._v196FirstIssue(true);if(issue){this._v196Issue(issue);return;}
  }
  const value=await super._r195Action(action);
  if(this._r195Session&&this._r195Message)this._v196Focus('[data-r195-message]');
  return value;
 }
 async _r195List(...args){const value=await super._r195List(...args);this._v196Focus('[data-r195-drafts] button, [data-r195-drafts]');return value;}
 _v78RenderCapture(){const result=super._v78RenderCapture();this._v196Decorate();return result;}
 _v111Paint(){const result=super._v111Paint();this._v196Decorate();return result;}
 _v196Decorate(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  if(!this.shadowRoot.querySelector('#v196Styles')){
   const style=document.createElement('style');style.id='v196Styles';style.textContent=`
    .v196-barcode{display:flex;align-items:stretch;gap:8px;min-width:0}.v196-barcode input{flex:1;min-width:0!important}.v196-barcode button{flex:0 0 auto;white-space:normal;max-width:50%}
    .v78-capture>.v196-actions{position:fixed;inset-inline:0;bottom:0;z-index:30;display:flex;flex-wrap:wrap;justify-content:flex-end;align-items:center;gap:10px;padding:12px max(18px,env(safe-area-inset-right)) calc(12px + env(safe-area-inset-bottom));background:var(--card-background-color,#fff);color:var(--primary-text-color,#222);border-top:1px solid var(--divider-color,#8885);box-shadow:0 -4px 14px #0001}
    .v196-actions [data-v196-status]{flex:1 1 230px;font-size:.9rem;line-height:1.35}.v196-actions .btn{min-height:44px}.v78-capture.v196-editor-actions .v78-capture-body{padding-bottom:145px}.v196-editor-actions [data-v112-apply]{display:none!important}.v196-editor-actions{scroll-padding-block:84px 160px}.v196-editor-actions input,.v196-editor-actions select{scroll-margin-block:84px 160px}
    .v196-field-error{display:block;color:var(--error-color,#e53935);font-weight:650;padding:6px 0;line-height:1.4}[data-v196-invalid]{outline:2px solid var(--error-color,#e53935)!important;outline-offset:2px}.v78-discard button:focus-visible,.v196-actions button:focus-visible{outline:3px solid var(--primary-color);outline-offset:3px}
    @media(max-width:500px){.v196-actions [data-v196-status]{flex-basis:100%}.v196-barcode button{padding-inline:10px!important;font-size:.85rem}}
   `;this.shadowRoot.append(style);
  }
  const input=c.querySelector('[data-v112-barcode-edit]');
  if(input){
   let wrap=input.parentElement;if(!wrap?.classList.contains('v196-barcode')){wrap=document.createElement('span');wrap.className='v196-barcode';input.before(wrap);wrap.append(input);}
   let button=wrap.querySelector('[data-v196-lookup]');
   if(!button){button=document.createElement('button');button.type='button';button.className='btn secondary';button.dataset.v196Lookup='';wrap.append(button);button.onclick=()=>void this._v196Lookup();input.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();event.stopPropagation();void this._v196Lookup();}});}
   button.textContent=this._v196Text('lookup');button.disabled=!!this._v78Busy||!!this._v78Submitted||!!(this._r195Session&&(this._r195Current()?.status!=='pending'||this._r195Current()?.kind!=='product'));
  }
  const show=!!d.editorOpen&&!this._r195Session;
  c.classList.toggle('v196-editor-actions',show);
  let footer=c.querySelector('[data-v196-actions]');
  if(!footer){
   footer=document.createElement('footer');footer.className='v196-actions';footer.dataset.v196Actions='';
   footer.innerHTML='<span data-v196-status role="status" aria-live="polite" tabindex="-1"></span><button type="button" class="btn secondary" data-v196-discard></button><button type="button" class="btn" data-v196-save></button>';c.append(footer);
   footer.querySelector('[data-v196-discard]').onclick=()=>this._v196Discard();footer.querySelector('[data-v196-save]').onclick=()=>void this._v78Save();
  }
  footer.hidden=!show;
  footer.querySelector('[data-v196-status]').textContent=this._v196Message||'';
  const discard=footer.querySelector('[data-v196-discard]'),save=footer.querySelector('[data-v196-save]');
  discard.textContent=this._v196Text('discard');discard.disabled=!!this._v78Busy||!!this._v78Submitted;
  save.textContent=this._v196Text(this._v78Submitted?'retry':'save');save.disabled=!!this._v78Busy;
  const form=c.querySelector('[data-v78-form]');if(form)form.noValidate=true;
  if(!c._v196InputBound){
   c._v196InputBound=true;
   const clear=()=>{if(this._v196FieldIssue){this._v196ClearErrors();this._v196Message='';const current=this._v78Draft;if(current){current.scanNote='';current.scanPhase=current.scanRecognized?'recognized':'idle';}this._v196Decorate();}};
   c.addEventListener('input',clear);c.addEventListener('change',clear);
   c.addEventListener('click',event=>{if(this._v196FieldIssue?.field==='ingredient'&&event.target.closest?.('[data-v194-index],[data-v114-link]')&&this._v196Links().length)clear();});
   c.addEventListener('focusin',event=>{const field=event.target?.dataset?.draft;const match=field?selector(field):Object.values(FIELDS).find(value=>event.target?.matches?.(value));if(match)this._v196LastField=match;});
  }
  const type=c.querySelector('[data-v111-type]');
  if(type&&!type._v196Bound){type._v196Bound=true;type.addEventListener('click',()=>this._v196Focus('[data-v111-code-wrap] input'));}
  const keep=c.querySelector('[data-v78-keep]');
  if(keep&&!keep._v196Bound){
   keep._v196Bound=true;keep.addEventListener('click',()=>this._v196Focus(this._v196ReturnField||'main [data-draft="productName"]'));
   const prompt=keep.closest('.v78-discard');if(prompt){prompt.setAttribute('role','alertdialog');prompt.setAttribute('aria-label',this._v196Text('confirm'));}
  }
 };
};
