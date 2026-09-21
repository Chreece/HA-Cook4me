const V153='cook4me-recipe-hub-panel-v153';
if(!customElements.get(V153))await import('./cook4me-panel-v153.js?v=2026.9.21.18');
const BasePanel=customElements.get(V153);

const V154_STORAGE=[
 ['fridge','fridge-outline'],
 ['freezer','snowflake'],
 ['pantry','food-variant'],
 ['cupboard','cupboard-outline'],
 ['shelf','bookshelf'],
 ['drawer','drawer'],
 ['countertop','countertop-outline'],
 ['cellar','home-floor-b'],
 ['other','package-variant']
];
const V154_WORDS={
 en:{
  item:'item stored',items:'items stored',editItems:'Edit items',noItems:'No items stored here',
  containerOptional:'Container (optional)',noContainer:'No container',deduct:'Deduct container from weight',
  deductHelp:'Subtract the saved empty-container weight from this weighing.',weigh:'Weigh item',applyWeight:'Apply weight',
  containerMissing:'Saved container is no longer available',afterContainer:'After container',
  fridge:'Fridge',freezer:'Freezer',pantry:'Pantry',cupboard:'Cupboard',shelf:'Shelf',drawer:'Drawer',
  countertop:'Kitchen counter / worktop',cellar:'Cellar',other:'Other'
 },
 de:{
  item:'Artikel gelagert',items:'Artikel gelagert',editItems:'Artikel bearbeiten',noItems:'Hier sind keine Artikel gelagert',
  containerOptional:'Behälter (optional)',noContainer:'Kein Behälter',deduct:'Behältergewicht abziehen',
  deductHelp:'Das gespeicherte Leergewicht des Behälters von dieser Wägung abziehen.',weigh:'Artikel wiegen',applyWeight:'Gewicht übernehmen',
  containerMissing:'Gespeicherter Behälter ist nicht mehr verfügbar',afterContainer:'Nach Behälterabzug',
  fridge:'Kühlschrank',freezer:'Gefrierschrank',pantry:'Vorratsschrank',cupboard:'Küchenschrank',shelf:'Regal',drawer:'Schublade',
  countertop:'Küchenarbeitsplatte',cellar:'Keller',other:'Andere'
 },
 el:{
  item:'αποθηκευμένο είδος',items:'αποθηκευμένα είδη',editItems:'Επεξεργασία ειδών',noItems:'Δεν υπάρχουν αποθηκευμένα είδη εδώ',
  containerOptional:'Δοχείο (προαιρετικό)',noContainer:'Χωρίς δοχείο',deduct:'Αφαίρεση βάρους δοχείου',
  deductHelp:'Αφαίρεσε το αποθηκευμένο βάρος του άδειου δοχείου από αυτή τη ζύγιση.',weigh:'Ζύγισμα είδους',applyWeight:'Εφαρμογή βάρους',
  containerMissing:'Το αποθηκευμένο δοχείο δεν είναι πλέον διαθέσιμο',afterContainer:'Μετά την αφαίρεση δοχείου',
  fridge:'Ψυγείο',freezer:'Κατάψυξη',pantry:'Ντουλάπι τροφίμων',cupboard:'Ντουλάπι',shelf:'Ράφι',drawer:'Συρτάρι',
  countertop:'Πάγκος κουζίνας',cellar:'Κελάρι',other:'Άλλο'
 }
};

class Cook4MeRecipeHubPanelV154 extends BasePanel{
 constructor(){super();this._v154PlaceOpenId='';this._v154ScaleLoad=false;}
 _v154Text(key){
  const lang=this._langCode?.()||this._uiIngredientLanguage?.()||'en';
  return (V154_WORDS[lang]||V154_WORDS.en)[key]||V154_WORDS.en[key]||key;
 }
 _storageOptions(selected=''){
  const e=v=>this._escape(String(v??''));
  return `<option value="">—</option>`+V154_STORAGE.map(([kind])=>`<option value="${e(kind)}" ${kind===selected?'selected':''}>${e(this._v154Text(kind))}</option>`).join('');
 }
 _v154PlaceIcon(kind){return V154_STORAGE.find(row=>row[0]===kind)?.[1]||'package-variant';}
 _v154PlaceItems(locationId){
  const out=[];
  for(const row of this._houseIngredients||[]){
   for(const lot of row?.lots||[]){
    if(String(lot?.storageLocationId||'')===String(locationId||''))out.push({row,lot});
   }
  }
  return out;
 }
 _v154ItemName(row,lot){
  return String(lot?.productName||this._v112Local?.(row)?.name||row?.name||row?.foodName||'').trim();
 }
 _v154ContainerName(id){
  return (this._v116Scale?.containers||[]).find(row=>String(row.id)===String(id||''))?.name||'';
 }
 _v154PlaceItemsHtml(locationId){
  const e=v=>this._escape(String(v??'')),items=this._v154PlaceItems(locationId);
  if(!items.length)return `<div class="v154-place-empty muted">${e(this._v154Text('noItems'))}</div>`;
  return `<div class="v154-place-items">${items.map(({row,lot})=>{
   const amount=this._displayAmount?.(lot.quantity,row.unit)||[lot.quantity,row.unit].filter(Boolean).join(' ');
   const details=[amount,lot.bestBefore?this._v78Text('date')+': '+lot.bestBefore:'',this._v154ContainerName(lot.containerId)].filter(Boolean).join(' · ');
   return `<button type="button" class="v154-place-item" data-v154-edit-lot="${e(lot.id)}"><ha-icon icon="mdi:package-variant-closed"></ha-icon><span><strong>${e(this._v154ItemName(row,lot))}</strong><small>${e(details)}</small></span><ha-icon icon="mdi:pencil-outline"></ha-icon></button>`;
  }).join('')}</div>`;
 }
 _v78RenderPlaces(c){
  if(!c)return;
  const e=v=>this._escape(String(v??'')),t=k=>e(this._v78Text(k));
  const cards=this._v78Locations().map(row=>{
   const count=this._v154PlaceItems(row.id).length,open=this._v154PlaceOpenId===row.id;
   return `<div class="v154-place-wrap" data-place="${e(row.id)}"><div class="v78-place v154-place"><ha-icon icon="mdi:${e(this._v154PlaceIcon(row.kind))}"></ha-icon><span><strong>${e(row.name)} <em class="v154-place-count">${count}</em></strong><small>${e(this._v154Text(row.kind))} · ${count} ${e(this._v154Text(count===1?'item':'items'))}</small></span><button class="btn secondary" data-items>${e(this._v154Text('editItems'))}</button><button class="btn secondary" data-edit>${t('edit')}</button><button class="btn secondary" data-delete>${t('delete')}</button></div><div class="v154-place-panel" ${open?'':'hidden'}>${open?this._v154PlaceItemsHtml(row.id):''}</div></div>`;
  }).join('');
  c.innerHTML=`<section class="card"><h2>${t('places')}</h2><p class="muted">${t('placeHelp')}</p><div class="v78-places">${cards}</div><form class="v78-place-form"><h3>${t('addPlace')}</h3><div class="v78-fields"><label class="field">${t('placeName')}<input name="name" maxlength="80" required></label><label class="field">${t('placeKind')}<select name="kind">${this._storageOptions('other').replace(/<option value=""[^>]*>.*?<\/option>/,'')}</select></label></div><div class="v78-actions"><button class="btn" type="submit">${e(this._t('save'))}</button><button class="btn secondary" type="button" data-cancel hidden>${t('cancel')}</button></div></form><p role="status"></p></section>`;
  this._v154Styles();
  let editing='',busy=false;const form=c.querySelector('form'),name=form.querySelector('[name=name]'),kind=form.querySelector('[name=kind]');
  const mutate=async change=>{if(busy)return;busy=true;const context=this._prefKey();c.querySelectorAll('button').forEach(b=>b.disabled=true);try{const state=await this._api('cook4me/v33/storage_location',{entry_id:this._entryId,...change});if(context!==this._prefKey())return;this._v78AcceptState(state);this._v78RenderPlaces(c);this._renderInventoryOnly(c.closest('[data-v78-kitchen]'));}catch(error){const status=c.querySelector('[role=status]');if(status)status.textContent=String(error.message||error);}finally{busy=false;c.querySelectorAll('button').forEach(b=>b.disabled=false);}};
  c.querySelectorAll('[data-place]').forEach(el=>{
   const row=this._v78Locations().find(item=>item.id===el.dataset.place);if(!row)return;
   el.querySelector('[data-items]').onclick=()=>{this._v154PlaceOpenId=this._v154PlaceOpenId===row.id?'':row.id;this._v78RenderPlaces(c);};
   el.querySelector('[data-edit]').onclick=()=>{editing=row.id;name.value=row.name;kind.value=row.kind;c.querySelector('[data-cancel]').hidden=false;name.focus();};
   el.querySelector('[data-delete]').onclick=()=>void mutate({action:'delete',identity:row.id});
  });
  c.querySelectorAll('[data-v154-edit-lot]').forEach(button=>button.onclick=()=>void this._v112EditLot(button.dataset.v154EditLot));
  form.onsubmit=event=>{event.preventDefault();if(form.reportValidity?.()===false)return;void mutate({action:'save',identity:editing,name:name.value,kind:kind.value});};
  c.querySelector('[data-cancel]').onclick=()=>this._v78RenderPlaces(c);
 }

 _v78Fresh(mode){return {...super._v78Fresh(mode),containerId:'',deductContainer:false};}
 _v154Containers(){return this._v116Scale?.containers||[];}
 _v154ContainerRow(id){return this._v154Containers().find(row=>String(row.id)===String(id||''))||null;}
 _v154ContainerOptions(selected=''){
  const e=v=>this._escape(String(v??'')),rows=this._v154Containers();
  let html=`<option value="">— ${e(this._v154Text('noContainer'))} —</option>`;
  if(selected&&!rows.some(row=>String(row.id)===String(selected)))html+=`<option value="${e(selected)}" selected>${e(this._v154Text('containerMissing'))}</option>`;
  return html+rows.map(row=>`<option value="${e(row.id)}" ${String(row.id)===String(selected)?'selected':''}>${e(row.name)} · ${e(this._v116Num?.(row.tareGrams)||row.tareGrams)} g</option>`).join('');
 }
 _v154ApplyContainerTare(grams,containerId,deduct){
  let value=Number(grams);if(!Number.isFinite(value)||!deduct||!containerId)return value;
  if(String(this._v117ActiveContainerId||'')===String(containerId)&&Number(this._v116SoftwareTare||0)>0)return value;
  const tare=Number(this._v154ContainerRow(containerId)?.tareGrams);
  return Number.isFinite(tare)?Math.max(0,value-tare):value;
 }
 _v154MaybeLoadScale(){
  if(this._v116Scale||this._v154ScaleLoad||!this._entryId)return;
  this._v154ScaleLoad=true;
  Promise.resolve(this._v116Load?.(null,true)).finally(()=>{this._v154ScaleLoad=false;if(this._v78Dialog)this._v154DecorateProductContainer();});
 }
 _v154DecorateProductContainer(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  this._v154MaybeLoadScale();
  const storage=c.querySelector('main [data-draft="storageLocationId"]')?.closest('label');
  if(!storage)return;
  let field=c.querySelector('[data-v154-container-field]');
  if(!field){
   field=document.createElement('div');field.dataset.v154ContainerField='';field.className='v154-container-block';
   storage.insertAdjacentElement('afterend',field);
  }
  if(d.unlimited){field.hidden=true;return;}field.hidden=false;
  field.innerHTML=`<label class="field">${this._escape(this._v154Text('containerOptional'))}<select data-v154-container>${this._v154ContainerOptions(d.containerId)}</select></label><label class="v154-deduct"><input type="checkbox" data-v154-deduct ${d.deductContainer?'checked':''} ${d.containerId?'':'disabled'}><span><strong>${this._escape(this._v154Text('deduct'))}</strong><small>${this._escape(this._v154Text('deductHelp'))}</small></span></label>`;
  const select=field.querySelector('[data-v154-container]'),check=field.querySelector('[data-v154-deduct]');
  select.onchange=()=>{d.containerId=select.value;if(!d.containerId)d.deductContainer=false;d._v154ContainerTouched=true;d.deductContainer=!!d.deductContainer;this._v78Dirty=true;this._v154DecorateProductContainer();};
  check.onchange=()=>{d.deductContainer=check.checked;this._v78Dirty=true;};
 }
 _v78RenderCapture(){super._v78RenderCapture();this._v154DecorateProductContainer();this._v154Styles();}
 _v111Paint(){super._v111Paint();this._v154DecorateProductContainer();this._v154Styles();}
 _v116UseDraftWeight(){
  const d=this._v78Draft;if(!d)return;
  let grams=this._v116Net({stable:true});if(grams===null)return;
  grams=this._v154ApplyContainerTare(grams,d.containerId,!!d.deductContainer);
  if(!(grams>0)){this._message(this._v116Text('off'),true);return;}
  d.quantity=this._v116Num(grams,3);d.unit='g';this._v78Dirty=true;
  for(const input of this._v78Dialog?.querySelectorAll('[data-v111-amount],main [data-draft="quantity"]')||[])input.value=d.quantity;
  for(const input of this._v78Dialog?.querySelectorAll('[data-v111-unit],main [data-draft="unit"]')||[])input.value='g';
  this._v112PaintTotal?.();this._v79SchedulePrice?.();this._v111Paint?.();
 }

 async _v116Reweigh(row,lotId){return this._v154OpenWeigh(row,lotId);}
 async _v154OpenWeigh(row,lotId){
  if(!this._v116Scale)await this._v116Load?.(null,true);
  const lot=(row?.lots||[]).find(item=>String(item.id)===String(lotId||''))||(row?.lots||[])[0]||{};
  const dialog=document.createElement('dialog');dialog.className='v154-weigh';
  const e=v=>this._escape(String(v??'')),selected=lot.containerId||'';
  dialog.innerHTML=`<header><h3>⚖ ${e(this._v154Text('weigh'))}</h3><button type="button" class="btn secondary" data-close>✕</button></header><div class="v154-weigh-body"><strong data-v116-live>${e(this._v116Text('off'))}</strong><div class="muted" data-v116-meta></div><label class="field">${e(this._v154Text('containerOptional'))}<select data-container>${this._v154ContainerOptions(selected)}</select></label><label class="v154-deduct"><input type="checkbox" data-deduct ${selected?'':'disabled'}><span><strong>${e(this._v154Text('deduct'))}</strong><small>${e(this._v154Text('deductHelp'))}</small></span></label><div class="v154-weigh-preview muted" data-preview></div><div class="toolbar"><button type="button" class="btn" data-apply>${e(this._v154Text('applyWeight'))}</button><button type="button" class="btn secondary" data-close>${e(this._t('cancel'))}</button></div></div>`;
  this.shadowRoot.append(dialog);this._v154Styles();
  const select=dialog.querySelector('[data-container]'),check=dialog.querySelector('[data-deduct]'),preview=dialog.querySelector('[data-preview]');
  const paint=()=>{check.disabled=!select.value;if(!select.value)check.checked=false;const reading=this._v116Reading?.();if(reading){const value=this._v154ApplyContainerTare(reading.net,select.value,check.checked);preview.textContent=`${this._v154Text('afterContainer')}: ${this._v116Num(value)} g`;}else preview.textContent='';};
  select.onchange=paint;check.onchange=paint;
  const close=()=>{dialog.close?.();dialog.remove();};dialog.querySelectorAll('[data-close]').forEach(button=>button.onclick=close);
  dialog.querySelector('[data-apply]').onclick=async()=>{
   let grams=this._v116Net({stable:true});if(grams===null)return;
   grams=this._v154ApplyContainerTare(grams,select.value,check.checked);if(!(grams>0))return;
   try{
    const result=await this._api('cook4me/v37/inventory_reweigh',{entry_id:this._entryId,identity:this._stockIdentity(row),grams,lot_id:lotId||''});
    this._houseIngredients=result.houseIngredients||[];const entry=this._entry?.();if(entry?.profile)entry.profile.houseIngredients=this._houseIngredients;this._syncEntryProfile?.();close();
    const kitchen=this.shadowRoot?.querySelector('[data-v78-kitchen]')||this.shadowRoot?.getElementById('content');if(kitchen){this._renderInventoryOnly?.(kitchen);const places=kitchen.querySelector('[data-v78-section="places"]');if(places)this._v78RenderPlaces(places);}
   }catch(error){this._message(String(error.message||error),true);}
  };
  dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
  if(dialog.showModal)dialog.showModal();else dialog.setAttribute('open','');paint();this._v116Live?.();
 }

 _renderTab(){const result=super._renderTab();this._v154Styles();this.setAttribute('data-cook4me-build','2026.9.21.19');return result;}
 _v154Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v154Styles'))return;
  const style=document.createElement('style');style.id='v154Styles';style.textContent=`
   .v154-place-wrap{border:1px solid var(--divider-color);border-radius:14px;overflow:hidden}.v154-place-wrap>.v78-place{border:0;border-radius:0}.v154-place-count{display:inline-flex;align-items:center;justify-content:center;min-width:25px;height:25px;padding:0 7px;margin-left:7px;border-radius:999px;background:color-mix(in srgb,var(--primary-color) 18%,transparent);color:var(--primary-color);font-style:normal;font-size:.82rem}.v154-place-panel{padding:0 16px 16px}.v154-place-items{display:grid;gap:7px;padding-top:4px}.v154-place-item{display:flex;align-items:center;gap:10px;width:100%;padding:11px 12px;border:1px solid var(--divider-color);border-radius:11px;background:var(--card-background-color);color:var(--primary-text-color);text-align:left;cursor:pointer}.v154-place-item>span{display:flex;flex:1;min-width:0;flex-direction:column;gap:3px}.v154-place-item small{color:var(--secondary-text-color);overflow-wrap:anywhere}.v154-place-empty{padding:12px}
   .v154-container-block{display:grid;gap:8px;margin-top:8px}.v154-deduct{display:flex!important;flex-direction:row!important;align-items:flex-start!important;gap:9px!important;padding:9px 11px;border:1px solid var(--divider-color);border-radius:10px}.v154-deduct input{width:19px!important;min-height:19px!important;flex:0 0 19px;margin-top:2px}.v154-deduct>span{display:flex;flex-direction:column;gap:2px}.v154-deduct small{color:var(--secondary-text-color);line-height:1.35}
   .v154-weigh{width:min(520px,calc(100vw - 24px));border:1px solid var(--divider-color);border-radius:16px;background:var(--card-background-color);color:var(--primary-text-color);padding:0}.v154-weigh::backdrop{background:#0008}.v154-weigh>header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid var(--divider-color)}.v154-weigh>header h3{margin:0}.v154-weigh-body{display:grid;gap:12px;padding:16px}.v154-weigh .field{display:flex;flex-direction:column;gap:6px}.v154-weigh select{width:100%;min-height:44px;background:var(--card-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:9px;padding:8px}
   @media(max-width:850px){.v154-place{flex-wrap:wrap}.v154-place>span{flex-basis:calc(100% - 52px)}.v154-place>.btn{flex:1}}@media(max-width:520px){.v154-place>.btn{flex-basis:100%}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v154',Cook4MeRecipeHubPanelV154);
