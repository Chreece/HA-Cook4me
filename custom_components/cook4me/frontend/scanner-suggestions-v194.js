// Review-only scanner suggestions. Camera, saving and package accounting stay inherited.
const TEXT={
 en:{title:'Possible matching ingredients',help:'Select the ingredients this product can supply. Check its food form; the package amount is shared.',empty:'No compatible match could be established. Search the full catalog below.',name:'Name match',category:'Category evidence',preparation:'Preparation variant'},
 de:{title:'Mögliche passende Zutaten',help:'Wähle die Zutaten, die dieses Produkt abdecken kann. Zubereitungsform prüfen; die Packungsmenge wird gemeinsam genutzt.',empty:'Keine passende Zutat sicher ermittelt. Suche unten im vollständigen Katalog.',name:'Namensübereinstimmung',category:'Kategoriehinweis',preparation:'Zubereitungsvariante'},
 el:{title:'Πιθανά συμβατά υλικά',help:'Επίλεξε τα υλικά που μπορεί να καλύψει το προϊόν. Έλεγξε τη μορφή του· η ποσότητα της συσκευασίας είναι κοινή.',empty:'Δεν εντοπίστηκε τεκμηριωμένη αντιστοίχιση. Αναζήτησε παρακάτω στον πλήρη κατάλογο.',name:'Αντιστοίχιση ονόματος',category:'Ένδειξη κατηγορίας',preparation:'Παραλλαγή προετοιμασίας'}
};
export function scannerSuggestionRows(suggestions, identity){
 const found=new Map();
 for(const item of Array.isArray(suggestions)?suggestions:[]){
  if(!item?.ingredient?.name)continue;
  const id=identity(item.ingredient);if(!id||found.has(id))continue;
  found.set(id,item);
 }
 return [...found.values()];
}
export function toggleScannerLink(links,row,identity){
 const id=identity(row),picked=links.some(item=>identity(item)===id);
 return picked?links.filter(item=>identity(item)!==id):[...links,row];
}
export const ScannerSuggestionsMixin=Base=>class extends Base{
 _v78IngredientOptions(){
  const c=this._v78Dialog,d=this._v78Draft,holder=c?.querySelector('[data-v78-suggestions]');
  const scroll=holder?.querySelector('[data-v194-list]')?.scrollTop;
  const focused=holder?.contains?.(this.shadowRoot?.activeElement)?this.shadowRoot.activeElement?.dataset?.v194Ingredient:null;
  const result=super._v78IngredientOptions();this._v194Suggestions();
  if(c===this._v78Dialog&&d===this._v78Draft){
   const list=holder?.querySelector('[data-v194-list]');if(list&&scroll!==undefined)list.scrollTop=scroll;
   if(focused)for(const button of holder?.querySelectorAll('[data-v194-index]')||[])if(button.dataset.v194Ingredient===focused)button.focus?.({preventScroll:true});
  }
  return result;
 }
 _v114Picker(){
  const result=super._v114Picker();this._v194Suggestions();return result;
 }
 _v194Suggestions(){
  const c=this._v78Dialog,d=this._v78Draft,holder=c?.querySelector('[data-v78-suggestions]');
  if(!holder||!d)return;
  const lang=String(this._uiIngredientLanguage?.()||this._langCode?.()||'en').split(/[-_]/)[0];
  const t=TEXT[lang]||TEXT.en,id=row=>this._scanIngredientIdentity(row);
  const sourceSuggestions=d.suggestions;
  const localized=(Array.isArray(sourceSuggestions)?sourceSuggestions:[]).map(item=>item?.ingredient?{...item,ingredient:this._v112Local?.(item.ingredient)||item.ingredient}:item);
  const rows=scannerSuggestionRows(localized,id),links=this._v114Links?.()||[d.ingredient].filter(Boolean);
  const picked=new Set(links.map(id)),busy=!!this._v78Busy||!!this._v78Submitted;
  const query=String(d.query||'').trim();
  const seasonal=new Set(this._v223SeasonRows?.(rows.map(item=>item.ingredient),picked,id)||rows.map(item=>item.ingredient));
  const visible=rows.filter(item=>seasonal.has(item.ingredient)).filter(item=>picked.has(id(item.ingredient))||!query||
    (this._ingredientQueryMatches?this._ingredientQueryMatches(item.ingredient,query):item.ingredient.name.toLocaleLowerCase().includes(query.toLocaleLowerCase())));
  const signature=JSON.stringify([lang,rows,query,[...picked],busy,visible.map(item=>id(item.ingredient)),this._v140MarketCatalogKey]);
  if(holder._v194Signature===signature&&holder._v194Source===sourceSuggestions&&holder.querySelector('[data-v194-list]'))return;
  holder._v194Source=sourceSuggestions;
  holder._v194Signature=signature;
  const previous=holder.querySelector('[data-v194-list]'),scroll=previous?.scrollTop||0;
  const focused=holder.contains?.(this.shadowRoot?.activeElement)?this.shadowRoot.activeElement?.dataset?.v194Ingredient:null;
  const e=value=>this._escape(String(value??''));
  holder.innerHTML=`<strong>${e(t.title)} (${visible.length} / ${rows.length})</strong><p>${e(rows.length?t.help:t.empty)}</p><div data-v194-list style="max-height:260px;overflow:auto;display:flex;flex-wrap:wrap;gap:8px;padding:4px">${visible.map((item,i)=>{
   const key=id(item.ingredient),selected=picked.has(key),reason=item.reason==='preparation_variant'?t.preparation:item.reason==='category_exact'?t.category:t.name;
   return `<button type="button" class="btn secondary ${selected?'v141-selected':''}" data-v194-ingredient="${e(key)}" data-v194-index="${i}" aria-pressed="${selected}" ${busy?'disabled':''} title="${e(reason)}">${selected?'✓ ':''}${e(this._v223Name?.(item.ingredient)||item.ingredient.name)}</button>`;
  }).join('')}</div>`;
  const list=holder.querySelector('[data-v194-list]');if(list)list.scrollTop=scroll;
  holder.querySelectorAll('[data-v194-index]').forEach(button=>{
   button.onclick=()=>{
    if(this._v78Draft!==d||this._v78Dialog!==c||d.suggestions!==sourceSuggestions||this._v78Busy||this._v78Submitted)return;
    const row=visible[Number(button.dataset.v194Index)]?.ingredient;if(!row)return;
    const local=this._v112Local?.(row)||row,current=this._v114Links?.()||[d.ingredient].filter(Boolean);
    d.ingredientLinks=toggleScannerLink(current,local,id);
    if(!d.ingredientLinks.some(item=>id(item)===id(d.ingredient||{})))d.ingredient=d.ingredientLinks[0]||null;
    d.productLocked=true;this._v78Dirty=true;
    this._v78IngredientOptions();this._v111Paint?.();
   };
   if(focused&&button.dataset.v194Ingredient===focused)button.focus?.({preventScroll:true});
  });
 }
};
