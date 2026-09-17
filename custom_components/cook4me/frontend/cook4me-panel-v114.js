import './cook4me-panel-v113.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v113');
const WORDS={
 en:{restart:'Restart scan',links:'Linked catalogue ingredients',help:'Select every catalogue ingredient this product can supply. The package amount is shared.'},
 de:{restart:'Scan neu starten',links:'Verknüpfte Katalogzutaten',help:'Alle Katalogzutaten wählen, für die dieses Produkt verwendet werden kann. Die Packungsmenge wird gemeinsam genutzt.'},
 el:{restart:'Επανεκκίνηση σάρωσης',links:'Συνδεδεμένα υλικά καταλόγου',help:'Επίλεξε όλα τα υλικά καταλόγου που μπορεί να καλύψει αυτό το προϊόν. Η ποσότητα της συσκευασίας είναι κοινή.'}
};
class Cook4MeRecipeHubPanelV114 extends BasePanel{
 _v114Text(key){return (WORDS[this._uiIngredientLanguage()]||WORDS.en)[key];}
 _v78Fresh(mode){return {...super._v78Fresh(mode),ingredientLinks:[]};}
 _v114Links(){
  const d=this._v78Draft;if(!d)return [];
  const rows=[d.ingredient,...(d.ingredientLinks||[])].filter(Boolean).map(row=>this._v112Local(row));
  return [...new Map(rows.map(row=>[this._scanIngredientIdentity(row),row])).values()];
 }
 async _api(type,payload){
  const d=this._v78Draft,token=this._v111ReadToken,result=await super._api(type,payload);
  if(type==='cook4me/v33/barcode_lookup'&&d&&d===this._v78Draft&&token===this._v111ReadToken)d.ingredientLinks=result.mapping?.ingredientLinks||[];
  return result;
 }
 _v78ProductExtras(){return {...super._v78ProductExtras(),ingredient_links:this._v114Links().map(row=>({key:row.key||row.ingredientId||row.id,name:row.name}))};}
 _v113CanRestart(){return !!this._v78Draft&&this._v78Draft.scanPhase!=='saving';}
 async _v113Restart(){
  if(!this._v113CanRestart())return;
  // Finish an uncertain committed save before advancing to a new scan.
  if(this._v78Submitted){await this._v78Save();return;}
  this._v78Discard=false;this._v112SkipBarcode='';this._v112LastSaved='';
  this._v111NewDraft('barcode');await this._v80Scan('barcode');
 }
 _v111Paint(){
  super._v111Paint();const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  const restart=c.querySelector('[data-v113-restart]');if(restart){restart.hidden=false;restart.disabled=!this._v113CanRestart();restart.title=restart.ariaLabel=this._v114Text('restart');}
  const title=c.querySelector('[data-v112-details] strong');
  if(title){const names=this._v114Links().map(row=>row.name).join(', ');title.textContent=[d.productName||d.ingredient?.name||'',names?`(${names})`:''].filter(Boolean).join(' ');}
  this._v114Picker();
 }
 _v78IngredientOptions(){super._v78IngredientOptions();this._v114Picker();}
 _v114Picker(){
  const c=this._v78Dialog,d=this._v78Draft,select=c?.querySelector('[data-v78-ingredient]');if(!select||!d)return;
  select.closest('label').hidden=true;select.required=false;
  let holder=c.querySelector('[data-v114-links]');if(!holder){holder=document.createElement('div');holder.dataset.v114Links='';select.closest('label').after(holder);}
  d.ingredientLinks=this._v114Links();
  c.querySelector('[data-v111-catalog]')?.setAttribute('hidden','');
  const signature=JSON.stringify([this._uiIngredientLanguage(),d.query,d.ingredientLinks,!!this._v78Submitted,!!this._v78Busy]);
  if(holder._v114Catalog===this._ingredientCatalog&&holder._v114Signature===signature)return;
  holder._v114Catalog=this._ingredientCatalog;holder._v114Signature=signature;
  const picked=new Set(d.ingredientLinks.map(row=>this._scanIngredientIdentity(row))),all=new Map();
  for(const row of [...(this._ingredientCatalog||[]),...d.ingredientLinks])all.set(this._scanIngredientIdentity(row),row);
  const rows=[...all.values()].filter(row=>picked.has(this._scanIngredientIdentity(row))||!d.query||this._ingredientQueryMatches(row,d.query)).sort((a,b)=>Number(picked.has(this._scanIngredientIdentity(b)))-Number(picked.has(this._scanIngredientIdentity(a)))||a.name.localeCompare(b.name,this._uiIngredientLanguage()));
  const e=value=>this._escape(String(value??''));
  holder.innerHTML=`<strong>${e(this._v114Text('links'))}</strong><p>${e(this._v114Text('help'))}</p><div class="v114-link-list">${rows.map((row,i)=>`<label><input type="checkbox" data-v114-link="${i}" ${picked.has(this._scanIngredientIdentity(row))?'checked':''} ${this._v78Submitted||this._v78Busy?'disabled':''}><span>${e(row.name)}</span></label>`).join('')}</div><small>${rows.length} / ${all.size}</small>`;
  holder.querySelectorAll('[data-v114-link]').forEach(input=>input.onchange=()=>{
   if(this._v78Submitted)return;
   const row=rows[Number(input.dataset.v114Link)],key=this._scanIngredientIdentity(row);
   d.ingredientLinks=d.ingredientLinks.filter(item=>this._scanIngredientIdentity(item)!==key);
   if(input.checked)d.ingredientLinks.push(row);
   if(!d.ingredientLinks.some(item=>this._scanIngredientIdentity(item)===this._scanIngredientIdentity(d.ingredient||{})))d.ingredient=d.ingredientLinks[0]||null;
   d.productLocked=true;this._v78Dirty=true;this._v78IngredientOptions();
  });
  if(!this.shadowRoot.querySelector('#v114Styles')){const style=document.createElement('style');style.id='v114Styles';style.textContent='.v114-link-list{max-height:230px;overflow:auto;border:1px solid #ffffff60;border-radius:10px;padding:8px}.v114-link-list label{display:flex;gap:10px;align-items:center;padding:8px;cursor:pointer}.v114-link-list input[type=checkbox]{flex:0 0 20px;width:20px;height:20px;min-height:20px}.v114-link-list span{overflow-wrap:anywhere}[data-v114-links]>p{font-size:.85rem}';this.shadowRoot.append(style);}
 }
 _v112StockRows(ingredient){
  if(!ingredient)return [];const wanted=this._v112GroupKey(ingredient);
  return (this._houseIngredients||[]).flatMap(row=>{
   if(this._v112GroupKey(row)===wanted)return [row];
   const lots=(row.lots||[]).filter(lot=>(lot.ingredientLinks||[]).some(link=>this._v112GroupKey(link)===wanted));
   return lots.length?[{...row,lots,quantity:lots.reduce((sum,lot)=>sum+Number(lot.quantity||0),0)}]:[];
  });
 }
 _inventoryRowsHtml(){
  if(!this._houseIngredients?.length)return super._inventoryRowsHtml();
  const e=value=>this._escape(String(value??'')),groups=new Map(),legacy=document.createElement('div');legacy.innerHTML=super._inventoryRowsHtml();
  for(const row of this._houseIngredients){
   if(!row.lots?.length||row.unlimited)continue;
   for(const lot of row.lots){
    const name=lot.productName||this._v112Local(row).name,key=name.normalize('NFKC').toLocaleLowerCase().trim();
    if(!groups.has(key))groups.set(key,{name,rows:[],packages:[],links:new Map()});
    const group=groups.get(key);group.rows.push({...row,quantity:lot.quantity,lots:[lot]});group.packages.push({row,lot});
    for(const link of lot.ingredientLinks?.length?lot.ingredientLinks:[row]){const local=this._v112Local(link);group.links.set(this._v112GroupKey(local),local.name);}
   }
  }
  const html=[...groups].map(([key,group])=>`<details class="v112-stock-group" data-v112-group="${e(key)}"><summary><strong>${e(group.name)} (${e([...group.links.values()].join(', '))})</strong><span>${e(this._v112Total(group.rows))}</span></summary><div class="v112-packages">${group.packages.map(({row,lot})=>`<button type="button" class="v112-package" data-v112-edit-lot="${e(lot.id)}" title="${e(this._v112Text('edit'))}"><ha-icon icon="mdi:package-variant-closed"></ha-icon><span><strong>${e(lot.productName||group.name)} (${e((lot.ingredientLinks?.length?lot.ingredientLinks:[row]).map(link=>this._v112Local(link).name).join(', '))})</strong><span>${e(this._displayAmount(lot.quantity,row.unit))}</span><small>${e(this._v78Locations().find(place=>place.id===lot.storageLocationId)?.name||this._v78Text('choosePlace'))}${lot.bestBefore?` · ${e(this._v78Text('date'))}: ${e(lot.bestBefore)}`:''}</small></span><ha-icon icon="mdi:pencil-outline"></ha-icon></button>`).join('')}</div></details>`).join('');
  // Legacy unknown/unlimited stock retains its existing editing controls.
  legacy.querySelectorAll('.v112-package').forEach(node=>node.remove());
  legacy.querySelectorAll('.v112-stock-group').forEach(group=>{if(!group.querySelector('[data-stock-row]'))group.remove();});
  return html+legacy.innerHTML;
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.17.18');return result;}
}
customElements.define('cook4me-recipe-hub-panel-v114',Cook4MeRecipeHubPanelV114);
