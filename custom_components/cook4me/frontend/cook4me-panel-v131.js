const V130='cook4me-recipe-hub-panel-v130';
if(!customElements.get(V130))await import('./cook4me-panel-v130.js?v=2026.9.20.4');
const BasePanel=customElements.get(V130);

const V131_TEXT={
 en:{
  usedFrom:'Used from storage',batch:'Batch / package',autoBatch:'Automatic (FEFO)',previousStock:'previously used stock',
  reviewConsumption:'Review used ingredients',reviewHelp:'Choose the exact storage ingredient or batch and the amount actually used. Finite amounts are deducted only after confirmation.',
  editMeal:'Edit meal',saveMeal:'Save changes',historyEdited:'Meal history and storage usage updated',
  people:'Who ate it?',servingsEaten:'Servings eaten',ingredientsUsed:'Storage ingredients used',
  addUsage:'Add storage ingredient',remove:'Remove',close:'Close',stockUsageHelp:'Changing these rows restores the previous deduction first, then applies the edited deduction to storage.',
  noLots:'No separate batches',openEditor:'Open consumption editor'
 },
 de:{
  usedFrom:'Aus Vorrat verwendet',batch:'Charge / Packung',autoBatch:'Automatisch (FEFO)',previousStock:'zuvor verwendeter Vorrat',
  reviewConsumption:'Verwendete Zutaten prüfen',reviewHelp:'Wähle die genaue Vorratszutat oder Charge und die tatsächlich verwendete Menge. Endliche Mengen werden erst nach Bestätigung abgezogen.',
  editMeal:'Mahlzeit bearbeiten',saveMeal:'Änderungen speichern',historyEdited:'Mahlzeitenverlauf und Vorratsverbrauch aktualisiert',
  people:'Wer hat davon gegessen?',servingsEaten:'Gegessene Portionen',ingredientsUsed:'Verwendete Vorratszutaten',
  addUsage:'Vorratszutat hinzufügen',remove:'Entfernen',close:'Schließen',stockUsageHelp:'Beim Ändern werden zuerst die bisherigen Abzüge zurückgebucht und danach die neuen Abzüge auf den Vorrat angewendet.',
  noLots:'Keine getrennten Chargen',openEditor:'Verbrauchseditor öffnen'
 },
 el:{
  usedFrom:'Χρησιμοποιήθηκε από το απόθεμα',batch:'Παρτίδα / συσκευασία',autoBatch:'Αυτόματα (FEFO)',previousStock:'απόθεμα που χρησιμοποιήθηκε πριν',
  reviewConsumption:'Έλεγχος υλικών που χρησιμοποιήθηκαν',reviewHelp:'Επίλεξε το ακριβές υλικό ή την παρτίδα από το απόθεμα και την ποσότητα που χρησιμοποιήθηκε. Οι μετρήσιμες ποσότητες αφαιρούνται μόνο μετά την επιβεβαίωση.',
  editMeal:'Επεξεργασία γεύματος',saveMeal:'Αποθήκευση αλλαγών',historyEdited:'Ενημερώθηκαν το ιστορικό γεύματος και οι ποσότητες αποθέματος',
  people:'Ποιος έφαγε;',servingsEaten:'Μερίδες που καταναλώθηκαν',ingredientsUsed:'Υλικά αποθέματος που χρησιμοποιήθηκαν',
  addUsage:'Προσθήκη υλικού αποθέματος',remove:'Αφαίρεση',close:'Κλείσιμο',stockUsageHelp:'Όταν αλλάζεις αυτά τα στοιχεία, επαναφέρεται πρώτα η προηγούμενη αφαίρεση και μετά εφαρμόζεται η νέα αφαίρεση στο απόθεμα.',
  noLots:'Δεν υπάρχουν ξεχωριστές παρτίδες',openEditor:'Άνοιγμα επεξεργασίας κατανάλωσης'
 }
};

class Cook4MeRecipeHubPanelV131 extends BasePanel{
 constructor(){
  super();
  this._v131ConsumptionLink='';
  try{this._v131ConsumptionLink=new URL(globalThis.location.href).searchParams.get('consumption')||'';}catch(_e){}
 }
 _v131Text(key){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return (V131_TEXT[lang]||V131_TEXT.en)[key]||V131_TEXT.en[key]||key;
 }
 _nutritionChips(values,compact=false){
  const html=super._nutritionChips(values,compact);
  return String(html||'').replace(/(<span class="chip"[^>]*>[^<]*?)(-?\d+(?:[.,]\d+)?)/g,'$1<span class="v131-nutrient-gap" aria-hidden="true"></span>$2');
 }
 _v131StockRow(identity){
  return (this._houseIngredients||[]).find(row=>this._stockIdentity(row)===identity)||null;
 }
 _v131StockOptions(selected='',historical=null){
  const rows=this._houseIngredients||[],seen=new Set(),options=[];
  for(const row of rows){
   const identity=this._stockIdentity(row);if(!identity||seen.has(identity))continue;seen.add(identity);
   const label=`${row.name||identity} · ${this._stockText(row)}`;
   options.push(`<option value="${this._escape(identity)}" ${identity===selected?'selected':''}>${this._escape(label)}</option>`);
  }
  if(selected&&!seen.has(selected)){
   const label=`${historical?.name||selected} · ${this._v131Text('previousStock')}`;
   options.unshift(`<option value="${this._escape(selected)}" selected>${this._escape(label)}</option>`);
  }
  return options.join('');
 }
 _v131Lots(identity,historical=null){
  const row=this._v131StockRow(identity),lots=Array.isArray(row?.lots)?row.lots:[];
  const out=lots.map(lot=>({...lot,_historical:false}));
  const historicalId=String(historical?.lotId||'');
  if(historicalId&&!out.some(lot=>String(lot.id||'')===historicalId)){
   out.unshift({...historical,id:historicalId,_historical:true});
  }
  return out;
 }
 _v131LotOptions(identity,selected='',historical=null){
  const lots=this._v131Lots(identity,historical);
  const options=[`<option value="">${this._escape(this._v131Text('autoBatch'))}</option>`];
  for(const lot of lots){
   const id=String(lot.id||'');if(!id)continue;
   const parts=[lot.productName,lot.storage,lot.bestBefore,lot.quantity!=null?`${this._shownNumber(lot.quantity)} ${this._v131StockRow(identity)?.unit||historical?.unit||''}`:null,lot._historical?this._v131Text('previousStock'):null].filter(Boolean);
   options.push(`<option value="${this._escape(id)}" ${id===selected?'selected':''}>${this._escape(parts.join(' · ')||id)}</option>`);
  }
  return options.join('');
 }
 _v131AllocationHtml(values={},servings=null,prefix='pending'){
  const members=this._entry()?.profile?.householdMembers||[];
  const map=new Map((values||[]).filter(row=>row&&row.name).map(row=>[String(row.name),row.servings]));
  if(!members.length)return'';
  return `<div class="v131-allocations"><strong>${this._escape(this._v131Text('people'))}</strong><div class="formgrid v131-allocation-grid">${members.map(name=>`<div class="field"><label>${this._escape(name)} · ${this._escape(this._v131Text('servingsEaten'))}</label><input data-v131-allocation="${this._escape(name)}" data-v131-prefix="${prefix}" type="number" min="0" step="0.25" value="${this._escape(map.get(String(name))??'')}"></div>`).join('')}</div>${servings!=null?`<div class="muted">${this._escape(this._t('unassigned'))}: ${this._escape(servings)}</div>`:''}</div>`;
 }
 _pendingHtml(){
  const pending=this._pendingConsumption;if(!pending?.id)return'';
  const rows=(pending.ingredients||[]).map((row,index)=>{
   const selected=row.identity||'',amount=row.quantity??'',unit=row.unit||row.stockUnit||'';
   return `<div class="v131-consume-row" data-consume-row="${index}">
    <label class="v131-consume-check"><input data-consume-check type="checkbox" checked> ${this._escape(this._t('consume'))}</label>
    <div class="v131-recipe-used"><strong>${this._escape(row.name||'')}</strong><div class="muted">${this._escape(this._t('recipeAmount'))}: ${this._escape(amount)} ${this._escape(unit)}</div></div>
    <div class="field"><label>${this._escape(this._v131Text('usedFrom'))}</label><select data-v131-stock>${this._v131StockOptions(selected,row)}</select></div>
    <div class="field"><label>${this._escape(this._v131Text('batch'))}</label><select data-v131-lot>${this._v131LotOptions(selected,'',row)}</select></div>
    <div class="field"><label>${this._escape(this._t('amount'))}</label><input data-consume-amount type="number" min="0" step="any" value="${this._escape(amount)}"></div>
    <div class="field"><label>${this._escape(this._t('unit'))}</label>${this._unitInput(unit,'data-consume-unit')}</div>
   </div>`;
  }).join('');
  return `<section id="v131ConsumptionEditor" class="card v131-consumption-editor"><h2>${this._escape(this._v131Text('reviewConsumption'))}</h2><div class="muted"><strong>${this._escape(pending.recipeTitle||'')}</strong> · ${this._escape(this._v131Text('reviewHelp'))}</div><div class="v131-consumption-rows">${rows}</div>${this._v131AllocationHtml([],pending.servings,'pending')}<div class="toolbar v131-editor-actions"><button id="confirmConsumption" class="btn">${this._escape(this._t('confirmConsumption'))}</button><button id="clearConsumption" class="btn secondary">${this._escape(this._t('nothingConsumed'))}</button></div></section>`;
 }
 _v131BindStockSelectors(root){
  root.querySelectorAll('[data-v131-stock]').forEach(select=>{
   select.addEventListener('change',()=>{
    const row=select.closest('[data-consume-row],[data-v131-history-usage]'),lot=row?.querySelector('[data-v131-lot]');
    if(lot)lot.innerHTML=this._v131LotOptions(String(select.value||''));
   });
  });
 }
 _bindPending(c){
  const pending=this._pendingConsumption;if(!pending?.id)return;
  this._v131BindStockSelectors(c);
  c.querySelector('#confirmConsumption')?.addEventListener('click',async()=>{
   const ingredients=[];
   c.querySelectorAll('[data-consume-row]').forEach(container=>{
    const index=Number(container.dataset.consumeRow),base=pending.ingredients[index]||{};
    const identity=String(container.querySelector('[data-v131-stock]')?.value||base.identity||'');
    const stock=this._v131StockRow(identity);
    ingredients.push({identity,name:stock?.name||base.name||identity,consume:Boolean(container.querySelector('[data-consume-check]')?.checked),quantity:container.querySelector('[data-consume-amount]')?.value||null,unit:String(container.querySelector('[data-consume-unit]')?.value||''),...(container.querySelector('[data-v131-lot]')?.value?{lotId:String(container.querySelector('[data-v131-lot]').value)}:{})});
   });
   const allocations=[];c.querySelectorAll('[data-v131-allocation][data-v131-prefix="pending"]').forEach(input=>{const servings=Number(input.value);if(Number.isFinite(servings)&&servings>0)allocations.push({name:String(input.dataset.v131Allocation||''),servings});});
   try{
    const result=await this._api('cook4me/v14/consumption_confirm',{entry_id:this._entryId,pending_id:pending.id,ingredients,allocations,strict:true});
    this._houseIngredients=result?.houseIngredients||result?.profile?.houseIngredients||[];this._pendingConsumption=null;this._syncEntryProfile();this._foodState=null;this._v131ClearConsumptionLink();this._message(result?.mealHistoryRecord?this._t('mealRecorded'):this._t('consumptionUpdated'));this._renderProfile(c);
   }catch(error){this._message(`${this._t('error')}: ${error.message||error}`,true);}
  });
  c.querySelector('#clearConsumption')?.addEventListener('click',async()=>{try{await this._api('cook4me/v14/consumption_clear',{entry_id:this._entryId,pending_id:pending.id});this._pendingConsumption=null;this._v131ClearConsumptionLink();this._renderProfile(c);}catch(error){this._message(`${this._t('error')}: ${error.message||error}`,true);}});
 }
 _v131ClearConsumptionLink(){
  this._v131ConsumptionLink='';
  try{const url=new URL(globalThis.location.href);url.searchParams.delete('consumption');globalThis.history.replaceState(globalThis.history.state,'',url.pathname+url.search+url.hash);}catch(_e){}
 }
 _v131FocusPending(){
  if(!this._v131ConsumptionLink)return;
  if(this._tab!=='profile'){this._tab='profile';this._renderTabs();this._renderTab();return;}
  requestAnimationFrame(()=>{const editor=this.shadowRoot?.getElementById('v131ConsumptionEditor');if(editor){editor.classList.add('v131-deep-linked');editor.scrollIntoView({behavior:'smooth',block:'start'});}});
 }
 async _loadInventoryState(...args){
  const result=await super._loadInventoryState(...args);
  this._v131FocusPending();
  return result;
 }
 _v131HistoryUsedText(row){
  const lots=Array.isArray(row?.stockLots)?row.stockLots:[],ingredients=Array.isArray(row?.ingredients)?row.ingredients:[];
  const source=lots.length?lots:ingredients;
  return source.slice(0,6).map(item=>[item.name||item.productName,this._shownNumber(item.quantity),item.unit,item.productName&&item.productName!==item.name?item.productName:null].filter(Boolean).join(' ')).join(' · ');
 }
 _historySummaryHtml(){
  const state=this._foodState;if(!state)return'';
  const boxes=[['today','today'],['week','week'],['month','month']].map(([key,label])=>{const row=state.summary?.[key]||{};return `<div class="card v131-summary-card"><strong>${this._escape(this._t(label))}</strong><div class="v131-nutrient-chips chips">${this._nutritionChips(row.totals||{},true)}</div></div>`;}).join('');
  const recent=(state.history||[]).slice(0,12);
  return `<section class="card v131-history"><h2>${this._escape(this._t('mealHistory'))}</h2><div class="v131-history-summary">${boxes}</div>${recent.length?`<div class="v131-history-list">${recent.map(row=>{const eaten=Number(row.eatenServings),total=Number(row.servings),remaining=Number(row.remainingServings);const portions=Number.isFinite(eaten)&&Number.isFinite(total)?`${this._t('actualConsumed')}: ${this._shownNumber(eaten)} / ${this._shownNumber(total)}${Number.isFinite(remaining)&&remaining>0?` · ${this._shownNumber(remaining)} ${this._t('remainingMeal')}`:''}`:'';const people=(row.allocations||[]).map(item=>`${item.name}: ${this._shownNumber(item.servings)}`).join(' · ');return `<div class="v131-history-row"><div class="v131-history-main"><strong>${this._escape(row.title||'')}</strong><span class="muted">${this._escape(String(row.timestamp||'').slice(0,16).replace('T',' '))}</span>${portions?`<div class="muted">${this._escape(portions)}</div>`:''}${people?`<div class="muted">${this._escape(people)}</div>`:''}<div class="v131-nutrient-chips chips">${this._nutritionChips((row.consumedNutrition||row.nutrition||{}).totals||{},true)}</div>${this._v131HistoryUsedText(row)?`<div class="muted v131-used-history">${this._escape(this._v131HistoryUsedText(row))}</div>`:''}</div><button type="button" class="btn secondary" data-v131-edit-meal="${this._escape(row.id||'')}">${this._escape(this._v131Text('editMeal'))}</button></div>`;}).join('')}</div>`:`<div class="muted">${this._escape(this._t('noMealHistory'))}</div>`}</section>`;
 }
 _v131HistoryUsage(meal){
  const lots=Array.isArray(meal?.stockLots)?meal.stockLots:[];
  if(lots.length)return lots.map(row=>({identity:String(row.identity||''),lotId:String(row.lotId||''),name:String(row.name||row.productName||''),quantity:row.quantity,unit:String(row.unit||'')}));
  return (meal?.ingredients||[]).map(row=>({identity:String(row.identity||''),lotId:'',name:String(row.name||''),quantity:row.quantity,unit:String(row.unit||'')}));
 }
 _v131HistoryUsageRow(row={}){
  const identity=String(row.identity||''),lotId=String(row.lotId||'');
  return `<div class="v131-history-usage" data-v131-history-usage><div class="field"><label>${this._escape(this._v131Text('usedFrom'))}</label><select data-v131-stock>${this._v131StockOptions(identity,row)}</select></div><div class="field"><label>${this._escape(this._v131Text('batch'))}</label><select data-v131-lot>${this._v131LotOptions(identity,lotId,row)}</select></div><div class="field"><label>${this._escape(this._t('amount'))}</label><input data-v131-history-amount type="number" min="0" step="any" value="${this._escape(row.quantity??'')}"></div><div class="field"><label>${this._escape(this._t('unit'))}</label>${this._unitInput(row.unit||'','data-v131-history-unit')}</div><button type="button" class="btn secondary" data-v131-remove-usage>${this._escape(this._v131Text('remove'))}</button></div>`;
 }
 _v131OpenHistoryEditor(meal){
  const overlay=document.createElement('div');overlay.className='rx-overlay v131-history-overlay';
  const usages=this._v131HistoryUsage(meal);
  overlay.innerHTML=`<div class="rx-dialog v131-history-dialog"><div class="detail-head"><div><h2>${this._escape(this._v131Text('editMeal'))}</h2><div class="muted">${this._escape(meal.title||'')}</div></div><button type="button" class="btn secondary" data-v131-close>✕</button></div><section><h3>${this._escape(this._v131Text('ingredientsUsed'))}</h3><div class="muted">${this._escape(this._v131Text('stockUsageHelp'))}</div><div data-v131-history-usages>${usages.map(row=>this._v131HistoryUsageRow(row)).join('')}</div><button type="button" class="btn secondary" data-v131-add-usage>${this._escape(this._v131Text('addUsage'))}</button></section><section class="v131-history-people"><h3>${this._escape(this._v131Text('people'))}</h3>${this._v131AllocationHtml(meal.allocations||[],meal.servings,'history')}</section><footer><button type="button" class="btn" data-v131-save-history>${this._escape(this._v131Text('saveMeal'))}</button><button type="button" class="btn secondary" data-v131-close>${this._escape(this._v131Text('close'))}</button></footer></div>`;
  this.shadowRoot.append(overlay);
  const bindUsage=()=>{this._v131BindStockSelectors(overlay);overlay.querySelectorAll('[data-v131-remove-usage]').forEach(button=>button.onclick=()=>button.closest('[data-v131-history-usage]')?.remove());};
  bindUsage();
  overlay.querySelector('[data-v131-add-usage]').onclick=()=>{const holder=overlay.querySelector('[data-v131-history-usages]');holder?.insertAdjacentHTML('beforeend',this._v131HistoryUsageRow({identity:this._houseIngredients?.[0]?this._stockIdentity(this._houseIngredients[0]):'',unit:this._houseIngredients?.[0]?.unit||''}));bindUsage();};
  overlay.querySelectorAll('[data-v131-close]').forEach(button=>button.onclick=()=>overlay.remove());
  overlay.addEventListener('click',event=>{if(event.target===overlay)overlay.remove();});
  overlay.querySelector('[data-v131-save-history]').onclick=async()=>{
   const ingredients=[];overlay.querySelectorAll('[data-v131-history-usage]').forEach(container=>{const identity=String(container.querySelector('[data-v131-stock]')?.value||'');const stock=this._v131StockRow(identity);const quantity=container.querySelector('[data-v131-history-amount]')?.value;if(!identity||quantity===''||Number(quantity)<=0)return;ingredients.push({identity,name:stock?.name||identity,consume:true,quantity,unit:String(container.querySelector('[data-v131-history-unit]')?.value||''),...(container.querySelector('[data-v131-lot]')?.value?{lotId:String(container.querySelector('[data-v131-lot]').value)}:{})});});
   const allocations=[];overlay.querySelectorAll('[data-v131-allocation][data-v131-prefix="history"]').forEach(input=>{const servings=Number(input.value);if(Number.isFinite(servings)&&servings>0)allocations.push({name:String(input.dataset.v131Allocation||''),servings});});
   try{
    const result=await this._api('cook4me/v38/history_update',{entry_id:this._entryId,meal_id:String(meal.id||''),ingredients,allocations});
    this._houseIngredients=result?.houseIngredients||result?.profile?.houseIngredients||this._houseIngredients||[];this._syncEntryProfile();this._foodState={...(this._foodState||{}),profile:result?.profile||this._foodState?.profile,history:result?.history||this._foodState?.history||[],summary:result?.summary||this._foodState?.summary||{}};overlay.remove();this._message(this._v131Text('historyEdited'));this._renderTab();
   }catch(error){this._message(`${this._t('error')}: ${error.message||error}`,true);}
  };
 }
 _v131BindHistory(c){
  c.querySelectorAll('[data-v131-edit-meal]').forEach(button=>button.addEventListener('click',()=>{const row=(this._foodState?.history||[]).find(item=>String(item.id||'')===String(button.dataset.v131EditMeal||''));if(row)this._v131OpenHistoryEditor(row);}));
 }
 _renderProfile(c){
  super._renderProfile(c);
  this._v131BindHistory(c);
  this._v131FocusPending();
 }
 _renderTab(){
  if(this._v131ConsumptionLink)this._tab='profile';
  const result=super._renderTab();this._v131Styles();this.setAttribute('data-cook4me-build','2026.9.20.5');return result;
 }
 _v131Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v131Styles'))return;
  const style=document.createElement('style');style.id='v131Styles';style.textContent=`
   .v131-nutrient-gap{display:inline-block;width:6px}
   .v131-summary-card .chips,.v131-nutrient-chips{margin-top:7px;gap:8px}
   .v131-consumption-editor{border-left:4px solid var(--primary-color);scroll-margin-top:18px}
   .v131-consumption-editor h2,.v131-history h2{margin-top:0}
   .v131-consumption-rows{margin-top:12px}
   .v131-consume-row{display:grid;grid-template-columns:auto minmax(140px,1.1fr) minmax(170px,1.4fr) minmax(150px,1.2fr) minmax(95px,.65fr) minmax(85px,.55fr);gap:10px;align-items:end;padding:11px 0;border-bottom:1px solid var(--divider-color)}
   .v131-consume-check{display:flex;align-items:center;gap:6px;min-height:42px}.v131-recipe-used{align-self:center}
   .v131-allocations{margin-top:16px;padding-top:14px;border-top:1px solid var(--divider-color)}.v131-allocation-grid{margin-top:9px}.v131-editor-actions{margin-top:14px}
   .v131-deep-linked{animation:v131Highlight 1.8s ease-out 1}
   .v131-history{margin-top:14px}.v131-history-summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}.v131-history-list{margin-top:12px}.v131-history-row{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;padding:12px 0;border-bottom:1px solid var(--divider-color)}.v131-history-main{min-width:0}.v131-used-history{margin-top:5px}.v131-history-row>.btn{flex:0 0 auto}
   .v131-history-dialog{width:min(980px,calc(100vw - 24px));max-height:88vh}.v131-history-dialog section{margin-top:18px}.v131-history-usage{display:grid;grid-template-columns:minmax(180px,1.5fr) minmax(170px,1.35fr) minmax(90px,.55fr) minmax(80px,.5fr) auto;gap:9px;align-items:end;padding:10px 0;border-bottom:1px solid var(--divider-color)}.v131-history-dialog footer{display:flex;gap:8px;justify-content:flex-end;margin-top:18px}
   @keyframes v131Highlight{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--primary-color) 60%,transparent)}45%{box-shadow:0 0 0 7px color-mix(in srgb,var(--primary-color) 18%,transparent)}100%{box-shadow:none}}
   @media(max-width:900px){.v131-consume-row{grid-template-columns:1fr 1fr}.v131-consume-check,.v131-recipe-used{grid-column:1/-1}.v131-history-usage{grid-template-columns:1fr 1fr}.v131-history-usage>.btn{grid-column:1/-1}.v131-history-row{align-items:stretch;flex-direction:column}.v131-history-row>.btn{align-self:flex-start}}
   @media(max-width:560px){.v131-consume-row,.v131-history-usage{grid-template-columns:1fr}.v131-consume-row>*{grid-column:1!important}.v131-history-dialog footer{flex-direction:column}.v131-history-dialog footer .btn{width:100%}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v131',Cook4MeRecipeHubPanelV131);
