const TEXT={
 en:{links:'Assigned catalog ingredients',help:'Select every ingredient this unlimited item can supply. Save with Update.',search:'Search catalog ingredients',primary:'Main ingredient',empty:'No matching ingredients'},
 de:{links:'Zugeordnete Katalogzutaten',help:'Wähle alle Zutaten, die dieser unbegrenzte Vorrat abdecken kann. Mit Aktualisieren speichern.',search:'Katalogzutaten suchen',primary:'Hauptzutat',empty:'Keine passenden Zutaten'},
 el:{links:'Αντιστοιχισμένα υλικά καταλόγου',help:'Επίλεξε όλα τα υλικά που μπορεί να καλύψει αυτό το απεριόριστο απόθεμα. Πάτησε Ενημέρωση για αποθήκευση.',search:'Αναζήτηση υλικών καταλόγου',primary:'Κύριο υλικό',empty:'Δεν βρέθηκαν υλικά'}
};
const key=row=>String(row?.key||row?.ingredientId||row?.id||'');
export const UnlimitedStockLinksMixin=Base=>class extends Base{
 _v242Text(name){const lang=String(this._uiIngredientLanguage?.()||this._langCode?.()||'en').split(/[-_]/)[0];return (TEXT[lang]||TEXT.en)[name];}
 _v242State(row){
  const id=JSON.stringify([this._prefKey(),this._stockIdentity(row)]);
  this._v242Edits??=new Map();
  if(!this._v242Edits.has(id))this._v242Edits.set(id,{selected:[...(row.ingredientLinks||[])],query:'',open:false});
  const state=this._v242Edits.get(id),primary=this._v112Local(row);
  state.primary=(this._ingredientCatalog||[]).includes(primary)?key(primary):'';
  state.selected=[...new Map([...(state.primary?[primary]:[]),...state.selected.map(item=>this._v112Local(item))].map(item=>[key(item),item])).values()];
  return {id,state};
 }
 _bindInventoryRows(container){
  super._bindInventoryRows(container);
  for(const element of container.querySelectorAll('[data-stock-row]')){
   if(element.querySelector('[data-v242-links]'))continue;
   const row=this._houseIngredients?.[Number(element.dataset.stockRow)],toggle=element.querySelector('[data-stock-unlimited]');
   if(!row||!toggle)continue;
   const {state}=this._v242State(row),fold=document.createElement('details');
   fold.dataset.v242Links='';fold.className='v242-stock-links';fold.hidden=!toggle.checked;fold.open=state.open;
   const summary=document.createElement('summary'),body=document.createElement('div');
   const update=()=>{summary.textContent=`${this._v242Text('links')} (${state.selected.length})`;};update();
   fold.append(summary,body);element.querySelector('[data-stock-save]')?.parentElement.before(fold);
   toggle.addEventListener('change',()=>{fold.hidden=!toggle.checked;});
   const render=()=>{
    if(!fold.isConnected||!fold.open)return;
    if(!body.children.length){
     const help=document.createElement('p');help.textContent=this._v242Text('help');
     const search=document.createElement('input');search.type='search';search.dataset.v242Search='';search.placeholder=this._v242Text('search');search.setAttribute('aria-label',search.placeholder);search.value=state.query;
     const list=document.createElement('div');list.className='v242-link-list';list.dataset.v242List='';
     body.append(help,search,list);search.addEventListener('input',()=>{state.query=search.value;paint();});
    }
    paint();
   };
   const paint=()=>{
    const list=body.querySelector('[data-v242-list]');if(!list)return;
    const picked=new Set(state.selected.map(key)),all=new Map([...(this._ingredientCatalog||[]),...state.selected].map(item=>[key(item),item]));
    const rows=[...all.values()].filter(item=>picked.has(key(item))||!state.query||this._ingredientQueryMatches(item,state.query)).sort((a,b)=>Number(picked.has(key(b)))-Number(picked.has(key(a)))||String(a.name).localeCompare(String(b.name),this._uiIngredientLanguage()));
    list.replaceChildren();
    for(const item of rows){
     const label=document.createElement('label'),input=document.createElement('input'),name=document.createElement('span');
     input.type='checkbox';input.dataset.v242Link=key(item);input.checked=picked.has(key(item));input.disabled=key(item)===state.primary||!!state.pending;
     name.textContent=this._v221IngredientNames?.(item)?.label||item.name||'';
     if(key(item)===state.primary){const hint=document.createElement('small');hint.textContent=this._v242Text('primary');name.append(' ',hint);}
     input.addEventListener('change',()=>{
      if(state.pending)return;
      state.selected=state.selected.filter(link=>key(link)!==key(item));if(input.checked)state.selected.push(item);
      // Keep the checkbox and scroll position in place during multi-selection.
      update();
     });label.append(input,name);list.append(label);
    }
    if(!rows.length)list.textContent=this._v242Text('empty');
   };
   fold.addEventListener('toggle',async()=>{
    state.open=fold.open;if(!fold.open)return;
    if(!this._ingredientCatalog?.length)await this._loadIngredientCatalog(this._uiIngredientLanguage());
    if(fold.isConnected){this._v242State(row);update();render();}
   });
   if(fold.open)render();
  }
  if(!this.shadowRoot.querySelector('#v242StockLinksStyle')){
   const style=document.createElement('style');style.id='v242StockLinksStyle';style.textContent=`
    .v242-stock-links{margin:12px 0;border:1px solid var(--divider-color);border-radius:12px;overflow:hidden}.v242-stock-links[hidden]{display:none!important}.v242-stock-links>summary{cursor:pointer;padding:12px;font-weight:650}.v242-stock-links>div{padding:0 12px 12px}.v242-stock-links p{color:var(--secondary-text-color);font-size:.9rem;line-height:1.4}.v242-stock-links input[type=search]{width:100%;min-width:0;box-sizing:border-box;margin-bottom:8px}.v242-link-list{max-height:250px;overflow:auto;overflow-anchor:none}.v242-link-list label{display:flex;align-items:center;gap:10px;min-height:44px;padding:6px;box-sizing:border-box;cursor:pointer}.v242-link-list input{flex:0 0 20px;width:20px;height:20px;min-height:20px}.v242-link-list span{min-width:0;overflow-wrap:anywhere}.v242-link-list small{color:var(--secondary-text-color)}
   `;this.shadowRoot.append(style);
  }
 }
 async _api(type,payload={}){
  if(type==='cook4me/v14/inventory_remove'||type==='cook4me/v14/inventory_update'&&!payload.unlimited){
   const context=this._prefKey(),id=JSON.stringify([context,payload.identity]);
   const result=await super._api(type,payload);if(context===this._prefKey())this._v242Edits?.delete(id);return result;
  }
  if(type!=='cook4me/v14/inventory_update'||!payload.unlimited)return super._api(type,payload);
  const row=(this._houseIngredients||[]).find(item=>this._stockIdentity(item)===payload.identity);
  if(!row)return super._api(type,payload);
  const context=this._prefKey(),{id,state}=this._v242State(row);
  if(state.pending)return state.pending;
  const request={...payload,language:this._uiIngredientLanguage(),ingredient_links:state.selected.map(item=>({key:key(item),name:item.name}))};
  const elements=[...this.shadowRoot.querySelectorAll('[data-stock-row]')].filter(el=>this._stockIdentity(this._houseIngredients[Number(el.dataset.stockRow)]||{})===payload.identity);
  const controls=elements.flatMap(el=>[...el.querySelectorAll('input,select,button')]).map(node=>({node,disabled:node.disabled}));
  for(const {node} of controls)node.disabled=true;
  state.pending=super._api(type,request);
  try{const result=await state.pending;if(context===this._prefKey())this._v242Edits.delete(id);return result;}
  finally{state.pending=null;for(const {node,disabled} of controls)if(node.isConnected)node.disabled=disabled;}
 }
 _v112StockRows(ingredient){
  const rows=super._v112StockRows(ingredient),wanted=this._v112GroupKey(ingredient);
  for(const row of this._houseIngredients||[])if(row.unlimited&&!rows.includes(row)&&(row.ingredientLinks||[]).some(link=>this._v112GroupKey(link)===wanted))rows.push(row);
  return rows;
 }
};
