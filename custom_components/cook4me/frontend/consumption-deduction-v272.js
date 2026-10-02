// Post-cook deduction semantics: finite stock only, then offer depleted items for shopping.
const TEXT={
 en:{title:'Stock depleted',body:'These ingredients reached zero and were removed from storage. Add them to the shopping list?',add:'Add to shopping list',skip:'Not now',added:'Added depleted ingredients to the shopping list.'},
 de:{title:'Vorrat aufgebraucht',body:'Diese Zutaten haben 0 erreicht und wurden aus dem Vorrat entfernt. Zur Einkaufsliste hinzufügen?',add:'Zur Einkaufsliste hinzufügen',skip:'Nicht jetzt',added:'Aufgebrauchte Zutaten wurden zur Einkaufsliste hinzugefügt.'},
 el:{title:'Το απόθεμα τελείωσε',body:'Αυτά τα υλικά έφτασαν στο 0 και αφαιρέθηκαν από το απόθεμα. Να προστεθούν στη λίστα αγορών;',add:'Προσθήκη στη λίστα αγορών',skip:'Όχι τώρα',added:'Τα υλικά που τελείωσαν προστέθηκαν στη λίστα αγορών.'}
};
const identityOf=row=>String(row?.identity||'');
export function depletedShoppingRows(rows){
 const seen=new Set(),out=[];
 for(const row of Array.isArray(rows)?rows:[]){
  const identity=identityOf(row),name=String(row?.name||'').trim();
  const key=identity.startsWith('k:')?identity.slice(2):String(row?.key||'').trim();
  const token=key?'k:'+key:'n:'+name.toLocaleLowerCase();
  if(!name||seen.has(token))continue;
  seen.add(token);out.push({...(key?{key}:{}),name});
 }
 return out;
}
export const ConsumptionDeductionMixin=Base=>class extends Base{
 _v272Text(key){
  const lang=String(this._uiIngredientLanguage?.()||this._langCode?.()||'en').split(/[-_]/)[0];
  return (TEXT[lang]||TEXT.en)[key]||TEXT.en[key]||key;
 }
 _v272FinitePendingRow(base,container){
  if(base?.stockUnlimited)return false;
  const identity=String(container?.querySelector?.('[data-v131-stock]')?.value||base?.identity||'');
  const stock=this._v131StockRow?.(identity);
  return !stock?.unlimited;
 }
 _bindPending(c){
  const pending=this._pendingConsumption;
  if(pending?.id){
   for(const container of [...c.querySelectorAll('[data-consume-row]')]){
    const index=Number(container.dataset.consumeRow),base=pending.ingredients?.[index]||{};
    if(!this._v272FinitePendingRow(base,container))container.remove();
   }
  }
  return super._bindPending(c);
 }
 async _api(type,data){
  const request=type==='cook4me/v14/consumption_confirm'?{...data,strict:false}:data;
  const result=await super._api(type,request);
  if(type==='cook4me/v14/consumption_confirm'){
   const rows=depletedShoppingRows(result?.report?.depleted);
   this._v272DepletedPrompt=rows.length?rows:null;
  }
  return result;
 }
 _renderProfile(content){
  const result=super._renderProfile(content);
  if(this._v272DepletedPrompt?.length)queueMicrotask(()=>this._v272ShowDepletedPrompt());
  return result;
 }
 _v272ShowDepletedPrompt(){
  const rows=this._v272DepletedPrompt;if(!rows?.length||!this.shadowRoot)return;
  this._v272DepletedPrompt=null;
  this.shadowRoot.querySelector('[data-v272-depleted-overlay]')?.remove();
  const overlay=document.createElement('div');overlay.className='rx-overlay v272-depleted-overlay';overlay.dataset.v272DepletedOverlay='';
  const dialog=document.createElement('div');dialog.className='rx-dialog v272-depleted-dialog';dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');
  const title=document.createElement('h2');title.textContent=this._v272Text('title');
  const body=document.createElement('p');body.textContent=this._v272Text('body');
  const list=document.createElement('ul');list.className='v272-depleted-list';
  for(const row of rows){const item=document.createElement('li');item.textContent=row.name;list.append(item);}
  const status=document.createElement('p');status.className='muted';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  const actions=document.createElement('div');actions.className='toolbar';
  const add=document.createElement('button');add.type='button';add.className='btn';add.dataset.v272ShoppingAdd='';add.textContent=this._v272Text('add');
  const skip=document.createElement('button');skip.type='button';skip.className='btn secondary';skip.dataset.v272ShoppingSkip='';skip.textContent=this._v272Text('skip');
  actions.append(add,skip);dialog.append(title,body,list,status,actions);overlay.append(dialog);this.shadowRoot.append(overlay);
  const close=()=>overlay.remove();
  skip.onclick=close;
  overlay.addEventListener('click',event=>{if(event.target===overlay)close();});
  add.onclick=async()=>{
   if(add.disabled)return;add.disabled=true;skip.disabled=true;status.textContent='';
   try{
    await this._api('cook4me/v11/shopping_add',{entry_id:this._entryId,ingredients:rows,ui_language:this._uiIngredientLanguage?.()||this._langCode?.()||'en'});
    this._message?.(this._v272Text('added'));close();
   }catch(error){status.textContent=String(error?.message||error);add.disabled=false;skip.disabled=false;}
  };
  this._v272Styles();requestAnimationFrame(()=>add.focus({preventScroll:true}));
 }
 _v272Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v272ConsumptionStyles'))return;
  const style=document.createElement('style');style.id='v272ConsumptionStyles';style.textContent=`
   .v272-depleted-overlay{z-index:15050!important;display:flex!important;align-items:center;justify-content:center;padding:18px;box-sizing:border-box}
   .v272-depleted-dialog{width:min(520px,100%);max-height:min(720px,calc(100dvh - 36px));overflow:auto;padding:22px;box-sizing:border-box}
   .v272-depleted-dialog h2{margin-top:0}.v272-depleted-list{margin:14px 0 20px;padding-left:24px}.v272-depleted-list li{margin:7px 0}
   .v272-depleted-dialog .toolbar{display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-end}
   @media(max-width:520px){.v272-depleted-dialog .toolbar{display:grid;grid-template-columns:1fr}.v272-depleted-dialog .btn{width:100%}}
  `;this.shadowRoot.append(style);
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-ui-revision','272');return result;}
};