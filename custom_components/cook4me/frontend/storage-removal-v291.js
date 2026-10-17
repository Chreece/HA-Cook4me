// Remove stored products at their actual persistence boundary, never just hide
// a card. Expiry rows represent one stable physical lot; the grouped at-home
// list represents all inventory rows belonging to that displayed ingredient.
// Reuse existing authenticated, durable WebSocket mutations.
export const expiryStorageTarget=row=>{
 const lotId=typeof row?.lotId==='string'?row.lotId.trim():'';
 if(lotId)return {kind:'lot',lotId};
 const identity=typeof row?.identity==='string'?row.identity.trim():'';
 return identity?{kind:'ingredient',identities:[identity]}:null;
};
export const stockGroupIdentities=(rows,groupKey,getGroupKey,getIdentity)=>{
 if(!groupKey||!Array.isArray(rows))return [];
 const ids=new Set();
 for(const row of rows){
  if(getGroupKey(row)!==groupKey)continue;
  const id=getIdentity(row);
  if(typeof id==='string'&&id.trim())ids.add(id.trim());
 }
 return [...ids];
};

// Product-name groups from the actual v114 renderer are made of physical
// lots, not necessarily the ingredient's canonical inventory identity.
// Always resolve the exact rendered package IDs first. Legacy unlimited
// stock groups expose data-stock-row indices and delete whole identities.
export const stockGroupTarget=(group,rows,getGroupKey,getIdentity)=>{
 if(!group||!Array.isArray(rows))return null;
 const lotIds=[...new Set([...group.querySelectorAll('[data-v112-edit-lot]')]
  .map(el=>String(el.dataset.v112EditLot||'').trim()).filter(Boolean))];
 if(lotIds.length){
  const present=new Set(rows.flatMap(row=>Array.isArray(row?.lots)?row.lots:[])
   .map(lot=>String(lot?.id||'').trim()).filter(Boolean));
  // A stale package ID must never be silently redirected to a whole
  // ingredient or to another product group.
  if(lotIds.some(id=>!present.has(id)))return null;
  return {kind:'lots',scope:'group',lotIds};
 }
 const indexes=[...new Set([...group.querySelectorAll('[data-stock-row]')]
  .map(el=>Number(el.dataset.stockRow)).filter(i=>Number.isInteger(i)&&i>=0&&i<rows.length))];
 const identities=indexes.length?
  [...new Set(indexes.map(i=>getIdentity(rows[i])).filter(id=>typeof id==='string'&&id.trim()))]:
  stockGroupIdentities(rows,String(group.dataset.v112Group||''),getGroupKey,getIdentity);
 return identities.length?{kind:'ingredient',scope:'group',identities}:null;
};

export const STORAGE_REMOVE_TEXT={
 en:{
  removeLot:'Remove this package completely from storage',
  removeGroup:'Remove all stored stock for this item',
  confirmLot:'Permanently remove the stored package "{name}"? Other packages of the ingredient will remain.',
  confirmGroup:'Permanently remove "{name}" and ALL its packages from storage?',
  confirmIngredient:'Permanently remove "{name}" from storage?',
  removed:'Removed from storage',
  failed:'Could not remove from storage',
  changed:'The stored package changed. Reload and try again.',
  item:'this item'
 },
 de:{
  removeLot:'Diese Packung vollständig aus dem Vorrat entfernen',
  removeGroup:'Diesen Artikel samt allen Packungen aus dem Vorrat entfernen',
  confirmLot:'Die Packung "{name}" dauerhaft aus dem Vorrat entfernen? Andere Packungen bleiben erhalten.',
  confirmGroup:'"{name}" und ALLE zugehörigen Packungen dauerhaft aus dem Vorrat entfernen?',
  confirmIngredient:'"{name}" dauerhaft aus dem Vorrat entfernen?',
  removed:'Aus dem Vorrat entfernt',
  failed:'Entfernen aus dem Vorrat fehlgeschlagen',
  changed:'Die Packung wurde geändert. Bitte neu laden und erneut versuchen.',
  item:'Diesen Artikel'
 },
 el:{
  removeLot:'Οριστική αφαίρεση αυτής της συσκευασίας από το απόθεμα',
  removeGroup:'Οριστική αφαίρεση του είδους και όλων των συσκευασιών του',
  confirmLot:'Να αφαιρεθεί οριστικά η συσκευασία «{name}» από το απόθεμα; Οι άλλες συσκευασίες του είδους θα παραμείνουν.',
  confirmGroup:'Να αφαιρεθεί οριστικά το «{name}» και ΟΛΕΣ οι συσκευασίες του από το απόθεμα;',
  confirmIngredient:'Να αφαιρεθεί οριστικά το «{name}» από το απόθεμα;',
  removed:'Αφαιρέθηκε από το απόθεμα',
  failed:'Δεν ήταν δυνατή η αφαίρεση από το απόθεμα',
  changed:'Η συσκευασία έχει αλλάξει. Φόρτωσέ την ξανά και δοκίμασε.',
  item:'το είδος'
 }
};
export const StorageRemovalMixin=Base=>class extends Base{
 constructor(){super();this._v291Removing=false;}
 _v291Text(key){
  const lang=String(this._langCode?.()||this._uiIngredientLanguage?.()||'en').toLowerCase().split(/[-_]/)[0];
  return (STORAGE_REMOVE_TEXT[lang]||STORAGE_REMOVE_TEXT.en)[key]||STORAGE_REMOVE_TEXT.en[key]||key;
 }
 _v291Confirm(target,name){
  const key=target.kind==='lot'?'confirmLot':target.scope==='group'?'confirmGroup':'confirmIngredient';
  const message=this._v291Text(key).replace('{name}',String(name||this._v291Text('item')));
  // Fail closed in environments without an interactive confirmation dialog.
  return typeof globalThis.confirm==='function'&&globalThis.confirm(message)===true;
 }
 _v142ExpiryRow(row,index){
  const original=super._v142ExpiryRow(row,index);
  if(!expiryStorageTarget(row))return original;
  const e=value=>this._escape(String(value??''));
  const label=e(this._v291Text(row?.lotId?'removeLot':'removeGroup'));
  return '<div class="v291-expiry-wrap">'+original+
   '<button class="v291-remove-btn" type="button" data-v291-expiry-index="'+e(index)+
   '" aria-label="'+label+'" title="'+label+'" '+(this._v291Removing?'disabled':'')+
   '><ha-icon icon="mdi:delete-outline" aria-hidden="true"></ha-icon></button></div>';
 }
 _v142PaintStockSummary(root=this.shadowRoot){
  const result=super._v142PaintStockSummary(root);
  this._v291Styles();
  const panel=root?.querySelector?.('[data-v142-expiry]');
  panel?.querySelectorAll('[data-v291-expiry-index]').forEach(button=>{
   button.disabled=!!this._v291Removing;
   button.onclick=event=>{
    event.preventDefault();event.stopPropagation();
    const index=Number(button.dataset.v291ExpiryIndex);
    if(!Number.isInteger(index)||index<0)return;
    const row=this._v142StockSummary?.expiring?.[index],target=expiryStorageTarget(row);
    if(!target)return;
    void this._v291Remove(target,row.productName||row.ingredientName||this._v291Text('item'));
   };
  });
  return result;
 }
 _v291DecorateHomeStock(root){
  const groups=root?.querySelectorAll?.('#houseInventoryRows > .v112-stock-group')||[];
  for(const group of groups){
   const key=String(group.dataset.v112Group||'');
   if(!key||group.querySelector(':scope > summary [data-v291-remove-group]'))continue;
   const name=group.querySelector(':scope > summary strong')?.textContent?.trim()||this._v291Text('item');
   group.classList.add('v291-stock-group');
   const button=document.createElement('button');
   button.type='button';button.className='v291-remove-btn';
   button.dataset.v291RemoveGroup=key;
   button.disabled=!!this._v291Removing;
   button.title=button.ariaLabel=this._v291Text('removeGroup')+': '+name;
   const glyph=document.createElement('ha-icon');
   glyph.setAttribute('icon','mdi:delete-outline');glyph.setAttribute('aria-hidden','true');
   button.append(glyph);group.querySelector(':scope > summary')?.append(button);
   button.onclick=event=>{
    event.preventDefault();event.stopPropagation();
    const target=stockGroupTarget(
     group,this._houseIngredients,row=>this._v112GroupKey(row),row=>this._stockIdentity(row)
    );
    if(!target)return;
    void this._v291Remove(target,name);
   };
  }
 }
 _renderInventoryOnly(root){
  const result=super._renderInventoryOnly(root);
  this._v291DecorateHomeStock(root);this._v291Styles();
  return result;
 }
 _renderProfile(root){
  const result=super._renderProfile(root);
  this._v291DecorateHomeStock(root);this._v291Styles();
  return result;
 }
 _renderTab(){
  const result=super._renderTab();
  this._v291Styles();return result;
 }
 _v291ToggleButtons(disabled){
  this.shadowRoot?.querySelectorAll('[data-v291-expiry-index],[data-v291-remove-group]').forEach(button=>{
   button.disabled=disabled;
  });
 }
 _v291AcceptState(state){
  if(!Array.isArray(state?.houseIngredients))throw new Error('Missing updated inventory state');
  this._houseIngredients=state.houseIngredients;
  this._syncEntryProfile?.();
  this._foodState=null;
  this._v79Revision=(this._v79Revision||0)+1;
 }
 async _v291Refresh(entryId,context){
  if(context!==this._prefKey())return;
  const kitchen=this.shadowRoot?.querySelector('[data-v78-kitchen]');
  if(kitchen){
   const open=new Set([...kitchen.querySelectorAll('#houseInventoryRows > .v112-stock-group[open]')].map(row=>row.dataset.v112Group));
   this._renderInventoryOnly(kitchen);
   kitchen.querySelectorAll('#houseInventoryRows > .v112-stock-group').forEach(row=>{
    if(open.has(row.dataset.v112Group))row.open=true;
   });
   const places=kitchen.querySelector('[data-v78-section="places"]');
   if(places)this._v78RenderPlaces?.(places);
   const count=kitchen.querySelector('.v78-count');
   if(count?.firstChild?.nodeType===3)count.firstChild.nodeValue=String(this._houseIngredients.length);
  }
  if(!kitchen?.querySelector('[data-v142-expiry]'))return;
  // Fetch the real server totals instead of optimistically filtering the card.
  // Both the expiry list and the stock value/nutrition must reflect the write.
  try{
   const summary=await this._api('cook4me/v39/stock_summary',{entry_id:entryId});
   if(context!==this._prefKey())return;
   this._v142StockSummary=summary;
   this._v142StockSummaryFingerprint=this._v142StockFingerprint?.();
   this._v142StockSummaryAt=Date.now();
   this._v142StockSummaryError='';
   this._v142PaintStockSummary();
  }catch(error){
   this._v142StockSummaryAt=0;
   this._v142StockSummaryError=String(error?.message||error);
   this._v142PaintStockSummary();
  }
 }
 async _v291Remove(target,name){
  if(this._v291Removing||!this._entryId||!target)return;
  if(target.kind==='ingredient'&&!(target.identities||[]).length)return;
  if(target.kind==='lots'&&!(target.lotIds||[]).length)return;
  if(!this._v291Confirm(target,name))return;
  const entryId=this._entryId,context=this._prefKey();
  this._v291Removing=true;this._v291ToggleButtons(true);
  try{
   if(target.kind==='lot'||target.kind==='lots'){
    const lotIds=target.kind==='lot'?[target.lotId]:[...new Set(target.lotIds)];
    for(const lotId of lotIds){
     if(context!==this._prefKey())return;
     const details=await this._api('cook4me/v33/product_details',{
      entry_id:entryId,lot_id:lotId,language:this._uiIngredientLanguage?.()||'en'
     });
     if(context!==this._prefKey())return;
     if(String(details?.lot?.id||'')!==lotId||!details?.version)throw Error(this._v291Text('changed'));
     const state=await this._api('cook4me/v33/product_remove',{
      entry_id:entryId,lot_id:lotId,expected_version:details.version
     });
     if(context!==this._prefKey())return;
     this._v291AcceptState(state);
    }
   }else{
    for(const identity of [...new Set(target.identities)]){
     if(context!==this._prefKey())return;
     const state=await this._api('cook4me/v14/inventory_remove',{entry_id:entryId,identity});
     if(context!==this._prefKey())return;
     this._v291AcceptState(state);
    }
   }
   await this._v291Refresh(entryId,context);
   if(context===this._prefKey())this._message?.(this._v291Text('removed'));
  }catch(error){
   if(context===this._prefKey()){
    // A multi-ingredient group could have been partly changed before a failure.
    // Always reload the persisted server state, never display guessed stock.
    try{
     const state=await this._api('cook4me/v14/inventory_state',{entry_id:entryId});
     if(context===this._prefKey())this._v291AcceptState(state);
    }catch(_ignored){}
    await this._v291Refresh(entryId,context);
    this._message?.(this._v291Text('failed')+': '+String(error?.message||error),true);
   }
  }finally{
   this._v291Removing=false;this._v291ToggleButtons(false);
  }
 }
 _v291Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v291Styles'))return;
  const style=document.createElement('style');style.id='v291Styles';
  style.textContent='\
.v291-expiry-wrap{display:grid;grid-template-columns:minmax(0,1fr) 44px;align-items:stretch;gap:8px;min-width:0}\
.v291-expiry-wrap>.v142-expiry-row{width:100%;min-width:0}\
.v291-remove-btn{display:inline-flex;align-items:center;justify-content:center;width:44px;min-width:44px;min-height:42px;padding:0;box-sizing:border-box;border:1px solid var(--divider-color);border-radius:12px;background:var(--card-background-color);color:var(--error-color,#df706b);cursor:pointer;font:inherit}\
.v291-remove-btn:hover:not(:disabled){border-color:var(--error-color,#df706b);background:color-mix(in srgb,var(--error-color,#df706b) 11%,var(--card-background-color))}\
.v291-remove-btn:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}\
.v291-remove-btn:disabled{cursor:wait;opacity:.45}\
.v291-remove-btn ha-icon{--mdc-icon-size:21px}\
.v291-stock-group{position:relative}\
.v291-stock-group>summary{padding-inline-end:70px!important;min-height:36px}\
.v291-stock-group>summary>[data-v291-remove-group]{position:absolute;inset-inline-end:12px;top:10px;width:40px;min-width:40px;min-height:40px}\
@media(max-width:620px){.v291-expiry-wrap{grid-template-columns:minmax(0,1fr) 40px;gap:5px}.v291-expiry-wrap>.v291-remove-btn{width:40px;min-width:40px}}';
  this.shadowRoot.append(style);
 }
};