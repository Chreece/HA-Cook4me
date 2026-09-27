const TEXT={
 en:{title:'Assign to stock ingredient',help:'Use this catalog ingredient as another name/food identity for an existing stock ingredient. Stock amounts and packages are not changed.',choose:'Choose a stock ingredient',assign:'Assign',assigned:'Already assigned',saved:'Ingredient assigned to stock.',empty:'There are no stock ingredients to assign.'},
 de:{title:'Einem Vorratsartikel zuordnen',help:'Dieses Katalogmaterial als weitere Bezeichnung/Lebensmittelidentität für einen vorhandenen Vorratsartikel verwenden. Mengen und Packungen werden nicht verändert.',choose:'Vorratsartikel auswählen',assign:'Zuordnen',assigned:'Bereits zugeordnet',saved:'Zutat wurde dem Vorrat zugeordnet.',empty:'Es gibt keine Vorratsartikel zum Zuordnen.'},
 el:{title:'Αντιστοίχιση σε υλικό αποθέματος',help:'Χρησιμοποίησε αυτό το υλικό καταλόγου ως επιπλέον ονομασία/ταυτότητα τροφίμου για ένα υπάρχον υλικό αποθέματος. Οι ποσότητες και οι συσκευασίες δεν αλλάζουν.',choose:'Επίλεξε υλικό αποθέματος',assign:'Αντιστοίχιση',assigned:'Ήδη αντιστοιχισμένο',saved:'Το υλικό αντιστοιχίστηκε στο απόθεμα.',empty:'Δεν υπάρχουν υλικά αποθέματος για αντιστοίχιση.'}
};
const catalogKey=row=>String(row?.key||row?.ingredientId||row?.id||'');
export const IngredientStockAssignmentMixin=Base=>class extends Base{
 _v249Text(key){const lang=String(this._uiIngredientLanguage?.()||this._langCode?.()||'en').split(/[-_]/)[0];return (TEXT[lang]||TEXT.en)[key]||TEXT.en[key]||key;}
 _v249GroupKey(row){return this._v112GroupKey?.(row)||this._stockIdentity?.({...row,key:catalogKey(row)})||catalogKey(row);}
 _v249StockHas(row,ingredient){
  const wanted=this._v249GroupKey(ingredient);if(!wanted)return false;
  if(this._v249GroupKey(row)===wanted)return true;
  const links=[...(row?.ingredientLinks||[]),...(row?.lots||[]).flatMap(lot=>lot?.ingredientLinks||[])];
  return links.some(link=>this._v249GroupKey(link)===wanted);
 }
 _v112StockRows(ingredient){
  const rows=super._v112StockRows(ingredient),found=new Set(rows);
  for(const row of this._houseIngredients||[])if(!found.has(row)&&this._v249StockHas(row,ingredient)){rows.push(row);found.add(row);}
  return rows;
 }
 _v249StockLabel(row){
  const product=String(row?.productName||'').trim(),name=String(row?.name||'').trim();
  const title=product&&product!==name?`${product} · ${name}`:name||product;
  const amount=row?.unlimited?'∞':row?.quantity!==undefined&&row?.quantity!==null?this._displayAmount(row.quantity,row.unit):'—';
  return `${title} · ${amount}`;
 }
 _v249DecorateIngredientInfo(ingredient){
  const overlay=this.shadowRoot?.querySelector?.('[data-ingredient-dialog]'),dialog=overlay?.querySelector?.('.rx-dialog');
  const source=this._v66IngredientInfo?.ingredient||ingredient;if(!dialog||!source||dialog.querySelector('[data-v249-stock-assignment]'))return;
  const section=document.createElement('section');section.dataset.v249StockAssignment='';
  section.innerHTML=`<h3></h3><p class="muted" data-v249-help></p><div class="v249-stock-assign"><select data-v249-stock></select><button type="button" class="btn" data-v249-assign></button></div><p role="status" aria-live="polite" data-v249-status></p>`;
  section.querySelector('h3').textContent=this._v249Text('title');section.querySelector('[data-v249-help]').textContent=this._v249Text('help');
  const usage=overlay.querySelector('[data-use]')?.closest('section');dialog.insertBefore(section,usage||null);
  const select=section.querySelector('[data-v249-stock]'),button=section.querySelector('[data-v249-assign]'),status=section.querySelector('[data-v249-status]');
  let busy=false;
  const paint=()=>{
   const previous=select.value,rows=this._houseIngredients||[];select.replaceChildren(new Option(this._v249Text(rows.length?'choose':'empty'),''));
   for(const row of rows){
    const identity=this._stockIdentity(row);if(!identity)continue;
    const assigned=this._v249StockHas(row,source),option=new Option(`${assigned?'✓ ':''}${this._v249StockLabel(row)}`,identity);
    option.dataset.assigned=String(assigned);select.append(option);
   }
   if([...select.options].some(option=>option.value===previous))select.value=previous;
   else select.value=[...select.options].find(option=>option.value&&option.dataset.assigned!=='true')?.value||'';
   const selected=select.selectedOptions?.[0],assigned=selected?.dataset.assigned==='true';
   button.textContent=assigned?this._v249Text('assigned'):this._v249Text('assign');
   button.disabled=busy||!select.value||assigned;
  };
  select.addEventListener('change',()=>{status.textContent='';paint();});
  button.addEventListener('click',async()=>{
   const identity=select.value;if(!identity||busy)return;busy=true;status.textContent='';paint();
   try{
    const request={key:catalogKey(source),name:source.name||''};
    const result=await this._api('cook4me/v14/inventory_assign_ingredient',{entry_id:this._entryId,identity,ingredient:request,language:this._uiIngredientLanguage()});
    this._v78AcceptState?.(result);this._foodState=null;status.textContent=this._v249Text('saved');paint();
   }catch(error){status.textContent=String(error.message||error);}
   finally{busy=false;paint();}
  });
  paint();this._v249Styles();
 }
 async _showIngredientInfo(ingredient,recipe){
  const result=await super._showIngredientInfo(ingredient,recipe);this._v249DecorateIngredientInfo(ingredient);return result;
 }
 _v249Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v249StockAssignmentStyles'))return;
  const style=document.createElement('style');style.id='v249StockAssignmentStyles';style.textContent=`
   [data-v249-stock-assignment]{border-top:1px solid var(--divider-color);padding-top:12px}
   .v249-stock-assign{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:end}
   .v249-stock-assign select{width:100%;min-width:0;min-height:44px;box-sizing:border-box}
   .v249-stock-assign .btn{min-height:44px}
   [data-v249-status]{min-height:1.3em;color:var(--secondary-text-color)}
   @media(max-width:520px){.v249-stock-assign{grid-template-columns:1fr}.v249-stock-assign .btn{width:100%}}
  `;this.shadowRoot.append(style);
 }
};
