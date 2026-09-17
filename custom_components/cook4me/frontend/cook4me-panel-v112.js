import './cook4me-panel-v111.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v111');
const WORDS={
 en:{details:'Product details',inStock:'Already in stock',none:'None',edit:'Edit package',packages:'Packages',review:'Review this product, then press Apply to scan the next one',manual:'Tap the box to enter this label manually',back:'Back to camera',apply:'Apply product',updated:'Package updated',basis:'Paid price covers',saved:'Product saved · ready for the next barcode',barcode:'Barcode',unknown:'Unknown amount',new:'Add package'},
 de:{details:'Produktangaben',inStock:'Bereits im Vorrat',none:'Keine',edit:'Packung bearbeiten',packages:'Packungen',review:'Produkt prüfen und Übernehmen drücken, um den nächsten Barcode zu scannen',manual:'Für manuelle Angaben auf das Feld tippen',back:'Zurück zur Kamera',apply:'Produkt übernehmen',updated:'Packung aktualisiert',basis:'Bezahlter Preis gilt für',saved:'Produkt gespeichert · bereit für den nächsten Barcode',barcode:'Barcode',unknown:'Unbekannte Menge',new:'Packung hinzufügen'},
 el:{details:'Στοιχεία προϊόντος',inStock:'Ήδη στο απόθεμα',none:'Κανένα',edit:'Επεξεργασία συσκευασίας',packages:'Συσκευασίες',review:'Έλεγξε το προϊόν και πάτησε Εφαρμογή για τον επόμενο barcode',manual:'Πάτησε το πλαίσιο για χειροκίνητη εισαγωγή',back:'Επιστροφή στην κάμερα',apply:'Εφαρμογή προϊόντος',updated:'Η συσκευασία ενημερώθηκε',basis:'Η τιμή αγοράς αφορά',saved:'Το προϊόν αποθηκεύτηκε · έτοιμο για τον επόμενο barcode',barcode:'Barcode',unknown:'Άγνωστη ποσότητα',new:'Προσθήκη συσκευασίας'}
};
class Cook4MeRecipeHubPanelV112 extends BasePanel{
 _v112Text(key){return (WORDS[this._uiIngredientLanguage()]||WORDS.en)[key]||key;}
 _v78Fresh(mode){return {...super._v78Fresh(mode),productLocked:false,editorOpen:mode==='manual',editLotId:'',expectedVersion:'',paidBasisQuantity:'',paidBasisUnit:'',packageCount:1};}
 _v112Local(row){
  const key=row?.key||row?.ingredientId||row?.id;
  return (this._ingredientCatalog||[]).find(item=>key&&(key===(item.key||item.ingredientId||item.id)||(item.sourceIngredientIds||[]).includes(key)))||row;
 }
 _v112GroupKey(row){const local=this._v112Local(row);return this._stockIdentity({...local,key:local?.key||local?.ingredientId||local?.id});}
 _v112StockRows(ingredient){if(!ingredient)return [];const id=this._v112GroupKey(ingredient);return (this._houseIngredients||[]).filter(row=>this._v112GroupKey(row)===id);}
 _v112Total(rows){
  if(rows.some(row=>row.unlimited))return '∞';
  const totals=new Map();let unknown=false;
  for(const row of rows){if(row.quantity===null||row.quantity===undefined||row.quantity===''){unknown=true;continue;}
   const raw=String(row.unit||'').toLowerCase(),[unit,factor]=({kg:['g',1000],l:['ml',1000]})[raw]||[raw,1];
   totals.set(unit,(totals.get(unit)||0)+Number(row.quantity)*factor);
  }
  return [...totals].map(([unit,amount])=>this._displayAmount(Number(amount.toFixed(9)),unit)).concat(unknown?[this._v112Text('unknown')]:[]).join(' + ')||this._v112Text('none');
 }
 _v112StockText(ingredient){
  const rows=this._v112StockRows(ingredient),places=[...new Set(rows.flatMap(row=>(row.lots||[]).map(lot=>this._v78Locations().find(place=>place.id===lot.storageLocationId)?.name).filter(Boolean)))];
  return [this._v112Total(rows),...places].join(' · ');
 }
 _v78RenderCapture(){
  super._v78RenderCapture();const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  this._v112Styles();const main=c.querySelector('main');if(!main)return;
  main.querySelector('h2').textContent=this._v112Text('details');
  main.querySelector('footer').hidden=true;
  main.querySelectorAll('[data-nutrient]').forEach(input=>{const key=input.dataset.nutrient,label=input.closest('label');label.firstChild.textContent=`${this._t(key==='energyKcal'?'energy':key==='carbohydrates'?'carbs':key)} (${key==='energyKcal'?'kcal':this._displayUnit('g')})`;});
  const basis=main.querySelector('[data-v78-basis]');for(const option of basis?.options||[])if(option.value)option.textContent=this._displayAmount(100,option.value);
  if(!d.editLotId){const count=document.createElement('label');count.className='field';count.innerHTML=`${this._escape(this._v112Text('packages'))}<input data-v112-count-edit type="number" min="1" max="100" step="1" value="${this._escape(d.packageCount)}" required>`;main.querySelector('.v78-fields')?.append(count);count.querySelector('input').oninput=event=>{d.packageCount=event.target.value;this._v78Dirty=true;this._v111Paint();};}
  const extra=document.createElement('div');extra.className='v78-fields';extra.innerHTML=`<label class="field">${this._escape(this._v112Text('barcode'))}<input data-v112-barcode-edit inputmode="numeric" value="${this._escape(d.barcode)}"></label>`;
  main.querySelector('.v78-fields')?.append(extra.firstElementChild);
  main.querySelector('[data-v112-barcode-edit]').oninput=event=>{d.barcode=event.target.value;this._v78Dirty=true;this._v79SchedulePrice();};
  if(d.editLotId){
   const fields=document.createElement('div');fields.className='v78-fields';fields.innerHTML=`<label class="field">${this._escape(this._v112Text('basis'))}<input data-v112-price-basis type="number" min="0.000001" step="any" value="${this._escape(d.paidBasisQuantity)}"></label><label class="field">${this._escape(this._t('unit'))}${this._unitInput(d.paidBasisUnit||d.unit,'data-v112-price-unit')}</label>`;
   main.querySelector('.v79-product-price')?.append(fields);
   fields.querySelector('[data-v112-price-basis]').oninput=event=>{d.paidBasisQuantity=event.target.value;this._v78Dirty=true;};
   fields.querySelector('[data-v112-price-unit]').onchange=event=>{d.paidBasisUnit=event.target.value;this._v78Dirty=true;};
  }
  if(d.editLotId){const remove=document.createElement('button');remove.type='button';remove.className='btn secondary';remove.dataset.v112Remove='';remove.textContent=this._t('removeBatch');main.querySelector('[data-v78-form] fieldset').append(remove);remove.onclick=()=>void this._v112RemoveLot();}
  const frame=c.querySelector('[data-v111-frame]'),bottom=frame.querySelector('.v111-bottom');
  bottom.insertAdjacentHTML('beforeend',this._v111Icon('data-v112-apply','check',this._v112Text('apply')));
  bottom.querySelector('[data-v112-apply]').onclick=()=>void this._v78Save();
  frame.querySelector('[data-v78-camera]').onclick=()=>void this._v80Scan(d.mode==='manual'?'product':d.mode);
  const editor=document.createElement('div');editor.className='v112-editor';editor.dataset.v112Editor='';
  editor.innerHTML=this._v111Icon('data-v112-back','arrow-left',this._v112Text('back'));
  editor.append(main);frame.append(editor);editor.querySelector('[data-v112-back]').onclick=()=>this._v112Editor(false);
  main.addEventListener('input',()=>{if(d.productName||d.ingredient)d.productLocked=true;});
  this._v111Paint();
 }
 _v111Paint(){
  const c=this._v78Dialog,d=this._v78Draft,frame=c?.querySelector('[data-v111-frame]');if(!frame||!d)return;
  const e=value=>this._escape(String(value??'')),mode=d.mode==='manual'?'product':d.mode,phase=d.scanPhase||'idle',busy=!!this._v78Busy;
  frame.dataset.mode=mode;frame.dataset.phase=phase;frame.classList.toggle('v111-live',!!this._v78Stream);
  const submitted=!!this._v78Submitted;
  frame.querySelectorAll('[data-v80-scan]').forEach(button=>{button.setAttribute('aria-pressed',String(button.dataset.v80Scan===mode));button.disabled=busy||submitted;});
  const power=frame.querySelector('[data-v111-power]');power.title=power.ariaLabel=this._v111Text(this._v78Stream?'stop':'camera');power.querySelector('ha-icon').setAttribute('icon',this._v78Stream?'mdi:camera-off-outline':'mdi:camera-outline');
  const local=this._v112Local(d.ingredient),name=local?.name||d.productName||'',labelMode=['date','nutrition'].includes(mode);
  const guide=frame.querySelector('[data-v111-guide-wrap]'),result=frame.querySelector('[data-v111-result]');
  const show=['looking','reading','recognized','notfound','error','saving','saved'].includes(phase);
  guide.hidden=show||d.editorOpen;result.hidden=!show||d.editorOpen;
  frame.querySelector('[data-v111-instruction]').textContent=this._v111Text(mode).replace('100 g / ml',`100 ${this._displayUnit('g')} / ${this._displayUnit('ml')}`);
  frame.querySelector('[data-v111-target]').textContent=labelMode?[name,this._v112Text('manual')].filter(Boolean).join(' · '):this._v112LastSaved||'';
  if(show){
   const spinning=['looking','reading','saving'].includes(phase),success=['recognized','saved'].includes(phase);
   const title=phase==='recognized'?(labelMode?'read':'recognized'):phase==='notfound'?(labelMode?'noData':'unknown'):phase;
   result.innerHTML=`<div class="v111-result-heading">${spinning?'<span class="v111-spinner" aria-hidden="true"></span>':`<ha-icon class="${success?'v111-ok':'v111-warning'}" icon="mdi:${success?'check-circle-outline':'alert-circle-outline'}"></ha-icon>`}<strong>${e(this._v111Text(title))}</strong></div>${name?`<button type="button" class="v112-product" data-v112-details><strong>${e(name)}</strong><span data-v112-total>${!d.editLotId?`${e(d.packageCount)} × `:''}${e(this._displayAmount(d.quantity,d.unit))}${Number(d.packageCount)>1?` = ${e(this._displayAmount(Number(d.quantity)*Number(d.packageCount),d.unit))}`:''}</span><span>${e(this._v112Text('inStock'))}: ${e(this._v112StockText(d.ingredient))}</span><span>${e(this._v78Locations().find(place=>place.id===d.storageLocationId)?.name||this._v78Text('choosePlace'))}</span><small>${e(this._v112Text('details'))}</small></button>`:''}${d.scanNote?`<p>${e(d.scanNote)}</p>`:''}${!spinning?`<div class="v111-facts">${d.bestBefore?`<div>${e(this._v78Text('date'))}: ${e(d.bestBefore)}</div>`:''}${Object.keys(d.nutrition?.values||{}).length?`<div class="v111-nutrients">${e(this._v78Text('nutrition'))} · ${e(this._v78Text('basis'))} ${e(this._displayUnit(d.nutrition.basisUnit))}${Object.entries(d.nutrition.values).map(([key,value])=>`<span>${e(this._t(key==='energyKcal'?'energy':key==='carbohydrates'?'carbs':key))}: ${e(this._shownNumber(value))} ${key==='energyKcal'?'kcal':e(this._displayUnit('g'))}</span>`).join('')}</div>`:''}<div data-v112-price-summary></div></div><div class="v111-amount">${!d.editLotId?`<label class="v112-count">${e(this._v112Text('packages'))}<input data-v112-count type="number" min="1" max="100" step="1" required value="${e(d.packageCount)}" ${submitted?'disabled':''}></label>`:''}<label>${e(this._v111Text('amount'))}<input data-v111-amount type="number" min="0.000001" step="any" value="${e(d.quantity)}" ${submitted?'disabled':''}></label>${this._unitInput(d.unit,'data-v111-unit '+(submitted?'disabled':''))}</div><label class="v111-place">${e(this._v78Text('places'))}<select data-v111-place ${submitted?'disabled':''}>${this._v78PlaceOptions(d.storageLocationId)}</select></label>`:''}<small>${e(this._v112Text('review'))}</small>`;
   result.querySelector('[data-v112-details]')?.addEventListener('click',()=>this._v112Editor(true,'product'));
   const update=(key,value)=>{d[key]=value;this._v78Dirty=true;const input=c.querySelector(`main [data-draft="${key}"]`);if(input)input.value=value;this._v79SchedulePrice();this._v112PaintTotal();};
   result.querySelector('[data-v112-count]')?.addEventListener('input',event=>{d.packageCount=event.target.value;this._v78Dirty=true;const input=c.querySelector('[data-v112-count-edit]');if(input)input.value=event.target.value;this._v112PaintTotal();});
   result.querySelector('[data-v111-amount]')?.addEventListener('input',event=>update('quantity',event.target.value));
   result.querySelector('[data-v111-unit]')?.addEventListener('change',event=>update('unit',event.target.value));
   result.querySelector('[data-v111-place]')?.addEventListener('change',event=>update('storageLocationId',event.target.value));
  }
  frame.querySelector('[data-v78-camera]').hidden=!!this._v78Stream;
  const take=frame.querySelector('[data-v78-take]');take.hidden=mode==='barcode'||d.editorOpen;take.disabled=busy||submitted||!this._v78Stream;
  frame.querySelector('[data-v111-type]').hidden=!!d.productLocked;
  if(d.productLocked)frame.querySelector('[data-v111-code-wrap]').hidden=true;
  for(const node of frame.querySelectorAll('[data-v78-file],[data-v78-lookup],[data-draft=barcode],[data-v78-native]'))node.disabled=busy||submitted||d.productLocked&&mode==='barcode';
  const apply=frame.querySelector('[data-v112-apply]');if(apply){apply.disabled=busy||(!d.productLocked&&!d.ingredient&&!d.productName);apply.title=apply.ariaLabel=this._v111Text(submitted?'retry':d.editLotId?'review':'apply');}
  const editor=frame.querySelector('[data-v112-editor]');if(editor)editor.hidden=!d.editorOpen;
  const status=c.querySelector('[data-v78-status]');if(status)status.textContent=this._v78Status||'';
  this._v112PaintPrice();
 }
 _v112PaintTotal(){const d=this._v78Draft,node=this._v78Dialog?.querySelector('[data-v112-total]');if(d&&node)node.textContent=`${!d.editLotId?`${d.packageCount} × `:''}${this._displayAmount(d.quantity,d.unit)}${Number(d.packageCount)>1?` = ${this._displayAmount(Number(d.quantity)*Number(d.packageCount),d.unit)}`:''}`;}
 _v112PaintPrice(){const d=this._v78Draft,node=this._v78Dialog?.querySelector('[data-v112-price-summary]');if(!node||!d)return;const r=d.priceResult;node.textContent=d.paidAmount!==''?`${this._v79Text('paid')}: ${this._v79Money({[d.paidCurrency]:Number(d.paidAmount)})}`:d.priceLoading?this._v79Text('looking'):r?.estimate!=null&&r.reference?`${this._v79Text('estimate')}: ${this._v79Money({[r.reference.currency]:r.estimate})}`:this._v79Text('none');}
 _v79PaintProduct(){super._v79PaintProduct();this._v112PaintPrice();}
 _v112Editor(open,section=this._v78Draft?.mode){
  const d=this._v78Draft,c=this._v78Dialog;if(!d||!c||d.scanPhase==='saving')return;
  this._v111CancelRead();this._v78Busy=false;d.editorOpen=open;if(d.productLocked)d.scanPhase=d.scanRecognized||d.ingredient||d.productName?'recognized':'notfound';
  this._v78SetBusy(false);this._v111Paint();
  if(open){const field=c.querySelector(section==='date'?'main [data-draft=bestBefore]':section==='nutrition'?'main [data-v78-basis]':'main [data-draft=productName]');field?.closest('details')?.setAttribute('open','');field?.focus({preventScroll:true});field?.scrollIntoView({block:'nearest'});}
 }
 async _v111Resume(){const d=this._v78Draft;if(!d)return;if(d.productLocked||['date','nutrition'].includes(d.mode)||d.mode==='manual'){this._v112Editor(true);return;}await this._v78Camera();if(d.mode==='barcode')void this._v80BarcodeLoop(this._v78Dialog);}
 async _v80Scan(mode){
  const d=this._v78Draft,c=this._v78Dialog;if(!d||!c||this._v78Busy||this._v78Submitted)return;
  const again=d.mode===mode&&d.scanPhase==='scanning'&&!!this._v78Stream;
  this._v111CancelRead();d.mode=mode;d.editorOpen=false;d.scanNewProduct=false;d.scanNote='';
  d.scanPhase=mode==='barcode'&&d.productLocked?(d.scanRecognized?'recognized':'notfound'):'scanning';
  this._v111Paint();await this._v78Camera();if(d!==this._v78Draft)return;
  if(mode==='barcode'&&!d.productLocked)void this._v80BarcodeLoop(c);else if(again&&mode!=='barcode')await this._v78CaptureFrame();
 }
 async _v80BarcodeLoop(c){
  const d=this._v78Draft;if(!d||d.productLocked)return;const token={};this._v111ScanToken=token;clearTimeout(this._v78CameraTimer);
  const active=()=>this._v78Alive(c)&&this._v78Draft===d&&!d.productLocked&&!d.editorOpen&&this._v111ScanToken===token&&this._v78Stream&&d.mode==='barcode'&&d.scanPhase==='scanning';
  let detector;try{detector=await this._v111Detector();}catch(error){if(active()){this._v78SetStatus(String(error.message||error));c.querySelector('[data-v111-code-wrap]').hidden=false;}return;}
  let empty=0;const loop=async()=>{if(!active())return;try{const canvas=this._v111Canvas(),codes=canvas?await detector.detect(canvas):[],code=codes?.[0]?.rawValue;if(!active())return;if(!code){if(++empty>=2)this._v112SkipBarcode='';}else{empty=0;if(code!==this._v112SkipBarcode){this._v112SkipBarcode='';await this._v78Lookup(code);return;}}}catch{}if(active())this._v78CameraTimer=setTimeout(loop,300);};void loop();
 }
 async _v78Lookup(code){
  const d=this._v78Draft;if(!d||this._v78Busy||this._v78Submitted)return;
  code=String(code||'').trim();if(!code)return;
  if(d.productLocked&&(d.scanRecognized||d.barcode!==code)){this._v111Paint();return;}
  d.productLocked=true;d.scanNewProduct=false;d.editorOpen=false;await super._v78Lookup(code);
 }
 async _v78Recognize(image){
  const d=this._v78Draft;if(!d)return;const original=d.ingredient;d.scanNewProduct=false;d.editorOpen=false;
  await super._v78Recognize(image);if(this._v78Draft!==d)return;
  if(d.productName||d.ingredient)d.productLocked=true;
  if(!d.ingredient&&original)d.ingredient=original;
  this._v111Paint();
 }
 _v78ProductExtras(){const d=this._v78Draft,result={...super._v78ProductExtras(),package_count:Number(d?.packageCount||1)};if(d?.editLotId){Object.assign(result,{edit_lot_id:d.editLotId,expected_version:d.expectedVersion});if(result.paid_price&&d.paidBasisQuantity!=='')Object.assign(result.paid_price,{basisQuantity:Number(d.paidBasisQuantity),basisUnit:d.paidBasisUnit||d.unit});}return result;}
 async _v78Save(){
  const d=this._v78Draft;if(!d||this._v78Busy)return;
  if(!this._v78Submitted&&(!d.ingredient||!d.storageLocationId||!(Number(d.quantity)>0)))this._v112Editor(true,'product');
  // Native validity messages must target visible controls in the editor.
  if(!this._v78Submitted&&this._v78Dialog?.querySelector('form')?.checkValidity()===false)this._v112Editor(true,'product');
  if(!this._v78Submitted&&(!Number.isInteger(Number(d.packageCount))||Number(d.packageCount)<1||Number(d.packageCount)>100)){this._v112Editor(true,'product');this._v78Dialog.querySelector('[data-v112-count-edit]')?.reportValidity();return;}
  await super._v78Save();if(d!==this._v78Draft||!d.scanApplied)return;
  if(d.editLotId){this._v78Close(true);this._message(this._v112Text('updated'));return;}
  this._v112SkipBarcode=d.barcode;this._v112LastSaved=this._v112Text('saved');this._v111NewDraft('barcode');
  await this._v80Scan('barcode');
 }
 async _v112RemoveLot(){const d=this._v78Draft,c=this._v78Dialog,context=this._prefKey();if(!d?.editLotId||this._v78Busy||this._v78Submitted)return;this._v78SetBusy(true);try{const result=await this._api('cook4me/v33/product_remove',{entry_id:this._entryId,lot_id:d.editLotId,expected_version:d.expectedVersion});if(context!==this._prefKey())return;this._v78AcceptState(result);this._v79Revision=(this._v79Revision||0)+1;this._foodState=null;this._v78Close(true);this._renderTab();}catch(error){if(this._v78Alive(c)){d.scanNote=String(error.message||error);this._v78SetStatus(d.scanNote);}}finally{if(this._v78Alive(c))this._v78SetBusy(false);}}
 async _v112EditLot(lotId){
  const context=this._prefKey();try{const product=await this._api('cook4me/v33/product_details',{entry_id:this._entryId,lot_id:lotId,language:this._uiIngredientLanguage()});if(context!==this._prefKey())return;
   await this._v78Open('manual');if(context!==this._prefKey()||!this._v78Draft)return;
   const d=this._v78Draft,lot=product.lot,paid=product.paidPrice;
   Object.assign(d,{...lot,quantity:lot.quantity,unit:product.unit,ingredient:product.ingredient,editLotId:lot.id,expectedVersion:product.version,productLocked:true,scanRecognized:true,scanPhase:'recognized',editorOpen:true,
    nutrition:product.nutrition?structuredClone(product.nutrition):{basisUnit:'',values:{}},labelNutrition:true,paidAmount:paid?.amount??'',paidCurrency:paid?.currency||d.paidCurrency,paidShop:paid?.location||'',paidBasisQuantity:paid?.basisQuantity??lot.quantity,paidBasisUnit:paid?.basisUnit||product.unit});
   this._v78Dirty=false;this._v78RenderCapture();
  }catch(error){this._message(String(error.message||error),true);}
 }
 _inventoryRowsHtml(){
  if(!this._houseIngredients?.length)return `<p class="muted">${this._escape(this._t('houseEmpty'))}</p>`;
  const e=value=>this._escape(String(value??'')),groups=new Map(),legacy=document.createElement('div');legacy.innerHTML=super._inventoryRowsHtml();
  for(const [index,row] of this._houseIngredients.entries()){const key=this._v112GroupKey(row);if(!groups.has(key))groups.set(key,[]);groups.get(key).push({row,index});}
  return [...groups].map(([key,items])=>{const local=this._v112Local(items[0].row),rows=items.map(item=>item.row);return `<details class="v112-stock-group" data-v112-group="${e(key)}"><summary><strong>${e(local.name)}</strong><span>${e(this._v112Total(rows))}</span></summary><div class="v112-packages">${items.map(({row,index})=>row.lots?.length&&!row.unlimited?row.lots.map(lot=>`<button type="button" class="v112-package" data-v112-edit-lot="${e(lot.id)}" title="${e(this._v112Text('edit'))}"><ha-icon icon="mdi:package-variant-closed"></ha-icon><span><strong>${e(lot.productName||local.name)}</strong><span>${e(this._displayAmount(lot.quantity,row.unit))}</span><small>${e(this._v78Locations().find(place=>place.id===lot.storageLocationId)?.name||this._v78Text('choosePlace'))}${lot.bestBefore?` · ${e(this._v78Text('date'))}: ${e(lot.bestBefore)}`:''}</small><small>${e(this._v112Text('edit'))}</small></span><ha-icon icon="mdi:pencil-outline"></ha-icon></button>`).join(''):legacy.querySelector(`[data-stock-row="${index}"]`)?.outerHTML||'').join('')}</div></details>`;}).join('');
 }
 _bindInventoryRows(c){super._bindInventoryRows(c);c.querySelectorAll('[data-v112-edit-lot]').forEach(button=>button.onclick=()=>void this._v112EditLot(button.dataset.v112EditLot));}
 _renderProfile(c){super._renderProfile(c);this._v112Styles();const stock=c.querySelector('#houseInventoryRows');if(stock?.parentElement?.tagName==='DETAILS')stock.parentElement.open=true;}
 async _loadIngredientCatalog(...args){await super._loadIngredientCatalog(...args);const c=this.shadowRoot?.querySelector('[data-v78-kitchen]');if(c)this._renderInventoryOnly(c);}
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.17.16');this._v112Styles();return result;}
 _v112Styles(){
  if(this.shadowRoot.querySelector('#v112Styles'))return;const style=document.createElement('style');style.id='v112Styles';style.textContent=`
   .v78-capture .v78-capture-body{display:block}.v78-capture .v78-capture-body>aside{width:100%;min-width:0}.v78-capture:has(.v112-editor){width:min(680px,calc(100vw - 24px))}.v78-capture .v111-camera[data-v111-frame]{min-height:530px;height:min(740px,calc(100dvh - 130px));--secondary-text-color:#b8cbd1}.v111-amount .v112-count{flex:0 0 90px}.v111-amount label{overflow-wrap:anywhere}.v112-product{flex-shrink:0;display:flex;flex-direction:column;gap:7px;text-align:left;width:100%;background:#152c34;color:#fff;border:1px solid #ffffff50;border-radius:12px;padding:12px;cursor:pointer}.v112-product strong{font-size:1.1rem}.v112-product small{color:#b8eaff}.v111-bottom{justify-content:flex-start}.v111-bottom [data-v112-apply]{margin-left:auto!important;background:var(--primary-color);border-color:#fff}.v112-editor{position:absolute;inset:76px 10px 72px;z-index:6;overflow:auto;border-radius:16px;background:#101f26;padding:12px;box-sizing:border-box;color:#fff}.v112-editor main{padding:0!important;min-width:0!important}.v112-editor main>p{display:none}.v112-editor main h2{font-size:1.1rem;color:#fff}.v112-editor .v78-fields{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.v112-editor input,.v112-editor select{box-sizing:border-box;max-width:100%;width:100%;min-width:0!important;color:#fff}.v112-editor label,.v112-editor .field{min-width:0}.v112-editor [data-v112-back]{position:sticky;top:0;z-index:2}.v112-editor .v78-review-section{margin:12px 0;padding:10px}.v112-stock-group{border:1px solid var(--divider-color);border-radius:15px;margin:10px 0;overflow:hidden}.v112-stock-group>summary{padding:16px;cursor:pointer;list-style:inside}.v112-stock-group>summary>span{float:right;margin-left:12px}.v112-packages{padding:0 12px 12px;display:grid;gap:8px}.v112-package{display:flex;align-items:center;gap:12px;width:100%;padding:14px;border:1px solid var(--divider-color);border-radius:12px;background:var(--card-background-color);color:var(--primary-text-color);text-align:left;cursor:pointer}.v112-package>span{display:flex;flex:1;flex-direction:column;gap:5px;min-width:0;overflow-wrap:anywhere}.v112-package small{color:var(--secondary-text-color)}.v112-package ha-icon{flex-shrink:0}.v112-stock-group [data-stock-row]{padding:12px}.v112-stock-group [data-stock-row] input,.v112-stock-group [data-stock-row] select{min-width:0;max-width:100%}@media(max-width:500px){.v78-capture .v111-camera[data-v111-frame]{min-height:520px}.v112-editor .v78-fields{grid-template-columns:minmax(0,1fr)}.v112-stock-group>summary>span{float:none;display:block;margin:6px 0 0}.v111-bottom{gap:4px;padding:5px}.v111-icon{flex-basis:40px;min-width:40px!important;width:40px}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v112',Cook4MeRecipeHubPanelV112);
