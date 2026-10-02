// Presentation-only inventory ordering, and post-acknowledgement scan continuation.
// Never reorder the backing stock array: legacy controls address its original indices.
const TEXT={
 en:{search:'Search ingredients at home',clear:'Clear search',empty:'No matching ingredients at home.',saved:'Product saved. Ready to scan the next product.'},
 de:{search:'Vorrat durchsuchen',clear:'Suche löschen',empty:'Keine passenden Zutaten im Vorrat.',saved:'Produkt gespeichert. Bereit für das nächste Produkt.'},
 el:{search:'Αναζήτηση στο απόθεμα του σπιτιού',clear:'Καθαρισμός αναζήτησης',empty:'Δεν βρέθηκαν αντίστοιχα υλικά στο απόθεμα.',saved:'Το προϊόν αποθηκεύτηκε. Έτοιμο για σάρωση του επόμενου προϊόντος.'}
};
export const stockSearchText=value=>String(value??'').normalize('NFKD').replace(/\p{M}/gu,'').toLowerCase().replace(/ς/g,'σ').replace(/ß/g,'ss').replace(/\s+/g,' ').trim();
export function stockMatches(text,query){return stockSearchText(query).split(/\s+/).filter(Boolean).every(word=>stockSearchText(text).includes(word));}
export function stockNameCompare(language='en'){
 try{return new Intl.Collator(language.replace('_','-'),{usage:'sort',sensitivity:'base',numeric:true}).compare;}
 catch(_error){return new Intl.Collator('en',{sensitivity:'base',numeric:true}).compare;}
}
const setText=(node,value)=>{if(node.textContent!==value)node.textContent=value;};
export const KitchenStockScanMixin=Base=>class extends Base{
 _v271Text(key){const lang=String(this._langCode?.()||this._uiIngredientLanguage?.()||'en').split(/[-_]/)[0];return (TEXT[lang]||TEXT.en)[key];}
 _v271StockState(){
  const context=this._prefKey();
  if(this._v271StockSearch?.context!==context)this._v271StockSearch={context,query:''};
  return this._v271StockSearch;
 }
 _bindInventoryRows(container){
  const result=super._bindInventoryRows(container);
  this._v271StockControls(container);return result;
 }
 _v271StockControls(container){
  const list=container?.querySelector('#houseInventoryRows');if(!list)return;
  const state=this._v271StockState(),compare=stockNameCompare(this._langCode?.()||this._uiIngredientLanguage?.()||'en');
  // Sort the existing group nodes after their original handlers are attached.
  // Search only product/ingredient labels; dates, amounts and hidden editor
  // catalogs must not produce unrelated hits or trigger catalog-wide work.
  const rows=[...list.children].filter(node=>node.matches('.v112-stock-group,[data-stock-row]')).map((node,index)=>{
   const heading=node.querySelector(':scope > summary > strong, :scope > strong, :scope > .stock-head strong')||node.querySelector('strong');
   const name=(heading?.textContent||'').trim();
   const labels=[name,...[...node.querySelectorAll('.v112-package > span > strong')].map(label=>label.textContent)];
   return {node,name,index,text:stockSearchText(labels.join(' '))};
  }).sort((a,b)=>compare(a.name,b.name)||a.index-b.index);
  rows.forEach(({node},index)=>{if(list.children[index]!==node)list.insertBefore(node,list.children[index]||null);});
  let toolbar=list.parentElement.querySelector(':scope > [data-v271-stock-search]');
  if(!toolbar){
   toolbar=document.createElement('div');toolbar.dataset.v271StockSearch='';toolbar.className='v271-stock-search';
   const label=document.createElement('label'),title=document.createElement('span'),line=document.createElement('div');
   const input=document.createElement('input'),clear=document.createElement('button'),status=document.createElement('small');
   input.type='search';input.id='v271StockQuery';label.htmlFor=input.id;input.dataset.v271StockQuery='';input.autocomplete='off';input.setAttribute('aria-controls','houseInventoryRows');
   clear.type='button';clear.className='btn secondary';clear.dataset.v271StockClear='';clear.textContent='✕';
   status.dataset.v271StockStatus='';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
   line.className='v271-stock-line';line.append(input,clear);label.append(title);toolbar.append(label,line,status);list.before(toolbar);
   toolbar._v271={title,input,clear,status};
   input.addEventListener('input',()=>{
    const current=this._v271StockState();if(!list.isConnected||toolbar._v271.state!==current)return;
    current.query=input.value;this._v271FilterStock(list,toolbar);
   });
   input.addEventListener('search',()=>input.dispatchEvent(new Event('input')));
   input.addEventListener('keydown',event=>{
    if(event.key==='Enter')event.preventDefault();
    if(event.key==='Escape'&&input.value){event.preventDefault();event.stopPropagation();clear.click();}
   });
   clear.onclick=()=>{input.value='';input.dispatchEvent(new Event('input'));input.focus({preventScroll:true});};
  }
  toolbar._v271.rows=rows;toolbar._v271.state=state;
  const {title,input,clear}=toolbar._v271;
  setText(title,this._v271Text('search'));input.placeholder=this._v271Text('search');
  if(input.value!==state.query)input.value=state.query;
  clear.title=this._v271Text('clear');clear.setAttribute('aria-label',clear.title);
  this._v271FilterStock(list,toolbar);
  if(!this.shadowRoot.querySelector('#v271StockStyles')){
   const style=document.createElement('style');style.id='v271StockStyles';style.textContent=`
    .v271-stock-search{margin:14px 0;min-width:0}.v271-stock-search label{display:block;font-size:.9rem;font-weight:600}
    .v271-stock-search .v271-stock-line{display:flex;gap:8px;margin-top:7px;align-items:center}
    .v271-stock-search input{flex:1;min-width:0;width:100%;box-sizing:border-box;min-height:44px;font:inherit;padding:10px 12px;border:1px solid var(--divider-color);border-radius:10px;color:var(--primary-text-color);background:var(--card-background-color)}
    .v271-stock-search button{min-width:44px;min-height:44px}.v271-stock-search small{display:block;margin-top:6px;color:var(--secondary-text-color)}
    #houseInventoryRows>.v112-stock-group[hidden],#houseInventoryRows>[data-stock-row][hidden]{display:none!important}
   `;this.shadowRoot.append(style);
  }
 }
 _v271FilterStock(list,toolbar){
  const {rows,input,clear,status}=toolbar._v271;
  const words=stockSearchText(input.value).split(/\s+/).filter(Boolean);let visible=0;
  for(const {node,text} of rows){const show=words.every(word=>text.includes(word));if(node.hidden===show)node.hidden=!show;if(show)visible++;}
  clear.disabled=!input.value;
  setText(status,visible?`${visible} / ${rows.length}`:rows.length?this._v271Text('empty'):this._t('houseEmpty'));
 }
 // Record the primary product scan only once the scan actually dispatches.
 // Manual barcode lookup keeps editorOpen=true; date/nutrition reads do not
 // replace the previous barcode/AI mode. This flag never enters save metadata.
 _v78SetBusy(busy){
  const d=this._v78Draft;
  if(busy&&d&&!this._r195Session&&!d.editLotId&&!d.editorOpen&&
     ((d.mode==='barcode'&&d.scanPhase==='looking')||(d.mode==='product'&&d.scanPhase==='reading'))){
   this._v271ScanOrigins??=new WeakMap();this._v271ScanOrigins.set(d,d.mode);
  }
  return super._v78SetBusy(busy);
 }
 _v111NewDraft(mode){
  const previous=this._v271ScanOrigins?.get(this._v78Draft),result=super._v111NewDraft(mode);
  // Retrying an auxiliary label scan replaces the draft but retains its product.
  if(previous&&['date','nutrition'].includes(mode)&&!this._r195Session&&this._v78Draft)this._v271ScanOrigins.set(this._v78Draft,previous);
  return result;
 }
 _v271ReturnMode(){
  const d=this._v78Draft;
  return !this._r195Session&&!d?.editLotId?this._v271ScanOrigins?.get(d):null;
 }
 _v78Save(){
  // Use the existing durable editor transaction even when Save was pressed on
  // the collapsed camera result. This prevents the old unconditional barcode
  // reset and preserves identical retries/validation for both scan modes.
  if(this._v271ReturnMode()&&!this._v78Busy)this._v196SavingDraft=this._v78Draft;
  return super._v78Save();
 }
 _v196Reset(message){
  const mode=message==='saved'&&this._v271ReturnMode();
  if(!mode)return super._v196Reset(message);
  const old=this._v78Draft,c=this._v78Dialog;
  this._v111CancelRead?.();this._v78StopCamera?.();this._v270CancelQuery?.();
  this._v196LookupToken=null;this._v196ClearErrors();
  this._v196FocusEpoch=(this._v196FocusEpoch||0)+1;
  this._v78Draft=this._v78Fresh(mode);
  Object.assign(this._v78Draft,{storageLocationId:old.storageLocationId||'',editorOpen:false,scanPhase:'scanning',scanNote:''});
  this._v78Submitted=null;this._v78Saved=false;this._v78Dirty=false;this._v78Discard=false;this._v78Busy=false;
  this._v196SavingDraft=null;this._v196BarcodeScanDraft=null;this._v196LastField='';this._v78Status='';
  // Do not immediately recognize the barcode of the product still in frame.
  this._v112SkipBarcode=mode==='barcode'?String(old.barcode||''):'';
  this._v112LastSaved=this._v271Text('saved');this._v196Message='';
  this._v78RenderCapture();c?.scrollTo?.({top:0,left:0,behavior:'instant'});
  c?.querySelector(`[data-v80-scan="${mode}"]`)?.focus({preventScroll:true});
  // Warm, do not call _v80Scan: on an already-live AI camera that method takes
  // another photo. The next AI capture must remain an explicit user action.
  this._v141KeepCameraWarm?.();
 }
 _resetUserScopedUiState(...args){this._v271StockSearch=null;return super._resetUserScopedUiState(...args);}
 _resetEntryScopedUiState(...args){this._v271StockSearch=null;return super._resetEntryScopedUiState(...args);}
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-ui-revision','271');return result;}
};
