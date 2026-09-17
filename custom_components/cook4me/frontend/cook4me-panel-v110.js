import './cook4me-panel-v109.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v109');
const TEXT={
 en:{select:'Include in plan',day:'Include all meals for this day',all:'Select all recipes',none:'Unselect all recipes',regenSelected:'Regenerate selected recipes',regenUnselected:'Regenerate unselected recipes',kept:'Recipes kept because no different match was available',covered:'Ingredients fully covered by stock',buy:'Ingredients to purchase',emptyStock:'No ingredients are fully covered by known stock.',emptyBuy:'No measured shortages for the selected recipes.',unknown:'Check stock: required quantities below have an unknown stock amount or incompatible unit.',basis:'Totals for selected recipes and their original ingredient quantities. ≈ Estimated or incomplete values; — unavailable.',selected:'selected',choose:'Selection is saved. Regeneration keeps each recipe’s checkbox state.'},
 de:{select:'In den Plan aufnehmen',day:'Alle Mahlzeiten dieses Tages aufnehmen',all:'Alle Rezepte auswählen',none:'Alle Rezepte abwählen',regenSelected:'Ausgewählte Rezepte neu planen',regenUnselected:'Abgewählte Rezepte neu planen',kept:'Rezepte beibehalten, weil keine andere passende Auswahl verfügbar war',covered:'Vollständig durch Vorrat gedeckte Zutaten',buy:'Einzukaufende Zutaten',emptyStock:'Keine Zutaten sind durch einen bekannten Vorrat vollständig gedeckt.',emptyBuy:'Keine messbaren Fehlmengen für die ausgewählten Rezepte.',unknown:'Vorrat prüfen: Für diese benötigten Mengen ist die Vorratsmenge oder Einheit unklar.',basis:'Summen für ausgewählte Rezepte und ihre ursprünglichen Zutatenmengen. ≈ Geschätzte oder unvollständige Werte; — nicht verfügbar.',selected:'ausgewählt',choose:'Die Auswahl wird gespeichert. Beim Neuplanen bleibt sie erhalten.'},
 el:{select:'Συμπερίληψη στο πλάνο',day:'Επιλογή όλων των γευμάτων της ημέρας',all:'Επιλογή όλων των συνταγών',none:'Αποεπιλογή όλων των συνταγών',regenSelected:'Ανανέωση επιλεγμένων συνταγών',regenUnselected:'Ανανέωση μη επιλεγμένων συνταγών',kept:'Συνταγές που διατηρήθηκαν επειδή δεν βρέθηκε διαφορετική κατάλληλη επιλογή',covered:'Υλικά που καλύπτονται πλήρως από το απόθεμα',buy:'Υλικά για αγορά',emptyStock:'Κανένα υλικό δεν καλύπτεται πλήρως από γνωστό απόθεμα.',emptyBuy:'Δεν υπάρχουν μετρημένες ελλείψεις για τις επιλεγμένες συνταγές.',unknown:'Ελέγξτε το απόθεμα: για τις παρακάτω απαιτούμενες ποσότητες η ποσότητα ή η μονάδα αποθέματος είναι άγνωστη.',basis:'Σύνολα για τις επιλεγμένες συνταγές και τις αρχικές ποσότητες υλικών τους. ≈ Εκτιμώμενες ή ελλιπείς τιμές· — μη διαθέσιμη τιμή.',selected:'επιλεγμένες',choose:'Η επιλογή αποθηκεύεται. Η ανανέωση διατηρεί την επιλογή κάθε συνταγής.'}
};
class Cook4MeRecipeHubPanelV110 extends BasePanel{
 _v110Text(key){return (TEXT[this._uiIngredientLanguage()]||TEXT.en)[key]||key;}
 _v109Text(key){return key==='basis'?this._v110Text('basis'):super._v109Text(key);}
 _v110Rows(){return super._v109Rows(true);}
 _v109Rows(visible=false){return super._v109Rows(visible).filter(slot=>slot.selected!==false);}
 _v109Totals(slots){
  const totals=super._v109Totals(slots);
  if(!slots.length){totals.values.forEach(cell=>cell.known=1);totals.priced=1;totals.cost={[this._currencyState?.currency||this._currencyState?.defaultCurrency||'EUR']:0};}
  return totals;
 }
 async _api(type,data={}){
  if(!type.endsWith('/week_select'))return super._api(type,data);
  const key=this._v109Key(),entry=this._entryId;
  const result=await super._api(type,{...data,shared_filters:structuredClone(this._filters()),ui_language:this._uiIngredientLanguage()});
  if(key!==this._v109Key()||entry!==this._entryId)throw new Error(this._v83Text('changed'));
  if(!Array.isArray(result?.slots))throw new Error(this._v109Text('failed'));
  result._v109Key=key;
  for(const slot of result.slots)if(!slot.leftoverId&&slot.recipe?.cost)this._v79CostState(slot.recipe).cost=slot.recipe.cost;
  return result;
 }
 _buttonIcon(button){return button.id==='generateWeek'||button.hasAttribute('data-week-action')?null:super._buttonIcon(button);}
 _v110Icon(button,icon,label){button.classList.add('v110-action');button.title=label;button.setAttribute('aria-label',label);button.innerHTML=`<ha-icon icon="${icon}" aria-hidden="true"></ha-icon>`;}
 _renderWeek(c){
  const open=new Set([...c.querySelectorAll('details[data-week-disclosure][open]')].map(node=>node.dataset.weekDisclosure));
  super._renderWeek(c);this._v110Styles();
  for(const node of c.querySelectorAll('details[data-week-disclosure]'))node.open=open.has(node.dataset.weekDisclosure);
  const ready=this._weekState?._v109Key===this._v109Key(),rows=ready?this._v110Rows():[];
  for(const node of c.querySelectorAll('.rx-week-slot[data-slot-id]')){
   const slot=rows.find(row=>String(row.id)===node.dataset.slotId);if(!slot)continue;
   const label=document.createElement('label');label.className='v110-selection';
   const box=document.createElement('input');box.type='checkbox';box.dataset.weekSelect=slot.id;box.checked=slot.selected!==false;
   box.setAttribute('aria-label',`${this._v110Text('select')}: ${this._slotTitle(slot)}`);
   box.onchange=()=>void this._v110Select([slot.id],box.checked);
   label.append(box);label.title=this._v110Text('select');label.onclick=event=>event.stopPropagation();label.onkeydown=event=>event.stopPropagation();
   (node.querySelector('.rx-v66-title')||node).prepend(label);node.classList.toggle('v110-unselected',!box.checked);
  }
  for(const day of c.querySelectorAll('[data-week-date]')){
   const slots=rows.filter(row=>row.date===day.dataset.weekDate),heading=day.querySelector('h3');if(!heading)continue;
   const box=document.createElement('input');box.type='checkbox';box.dataset.weekDaySelect=day.dataset.weekDate;
   box.checked=!!slots.length&&slots.every(row=>row.selected!==false);box.indeterminate=!box.checked&&slots.some(row=>row.selected!==false);
   box.setAttribute('aria-label',`${this._v110Text('day')}: ${heading.textContent}`);box.dataset.empty=String(!slots.length);
   box.onchange=()=>void this._v110Select(slots.map(row=>row.id),box.checked);
   const label=document.createElement('label');label.className='v110-day-selection';label.append(box,...heading.childNodes);heading.append(label);
  }
  const generate=this.shadowRoot.querySelector('#generateWeek');
  if(generate){
   this._v110Icon(generate,'mdi:calendar-plus',this._t('generateWeek'));
   const toolbar=document.createElement('div');toolbar.className='v110-week-actions';toolbar.setAttribute('role','group');toolbar.setAttribute('aria-label',this._t('weeklyPlanner'));
   for(const [action,icon,fn] of [
    ['all','mdi:checkbox-multiple-marked-outline',()=>this._v110Select(this._v110Rows().map(row=>row.id),true)],
    ['regenSelected','mdi:refresh',()=>this._v110Regenerate(true)],
    ['none','mdi:checkbox-multiple-blank-outline',()=>this._v110Select(this._v110Rows().map(row=>row.id),false)],
    ['regenUnselected','mdi:refresh',()=>this._v110Regenerate(false)]]){
    const button=document.createElement('button');button.className='btn secondary';button.dataset.weekAction=action;
    this._v110Icon(button,icon,this._v110Text(action));
    if(action.startsWith('regen')){const mark=document.createElement('span');mark.className='v110-action-mark';mark.textContent=action==='regenSelected'?'☑':'☐';mark.setAttribute('aria-hidden','true');button.append(mark);}
    button.onclick=()=>void fn();toolbar.append(button);
   }
   generate.after(toolbar);toolbar.prepend(generate);
   const count=document.createElement('span');count.className='muted v110-selection-count';count.dataset.weekSelectionCount='';count.setAttribute('aria-live','polite');count.title=this._v110Text('choose');count.textContent=`${rows.filter(row=>row.selected!==false).length}/${rows.length} ${this._v110Text('selected')}`;toolbar.append(count);
  }
  this._v110Disable();
 }
 _v110Disable(){
  const root=this.shadowRoot,rows=this._v110Rows(),busy=!!this._v110Busy||this._weekLoading||this._weekState?._v109Key!==this._v109Key();
  for(const box of root.querySelectorAll('[data-week-select],[data-week-day-select]'))box.disabled=busy||box.dataset.empty==='true';
  for(const button of root.querySelectorAll('[data-week-action]')){
   const action=button.dataset.weekAction,wanted=action==='all'||action==='regenUnselected'?false:true;
   button.disabled=busy||!rows.some(row=>(row.selected!==false)===wanted);
  }
  for(const button of root.querySelectorAll('#generateWeek,[data-week-regenerate],[data-week-clear]'))button.disabled=busy;
  const shopping=root.querySelector('#addPlanShopping');if(shopping)shopping.disabled=busy||!this._weekState?.shoppingDelta?.length;
 }
 async _v110Change(type,data){
  if(this._v110Busy||this._weekLoading||!this._entryId)return;
  const entry=this._entryId,key=this._v109Key();this._v110Busy=true;this._v110Disable();
  const focused=this.shadowRoot.activeElement,focusSlot=focused?.dataset.weekSelect,focusDay=focused?.dataset.weekDaySelect,focusAction=focused?.dataset.weekAction;
  try{
   if(type.endsWith('/week_generate')&&!this._filters().languages?.length)throw new Error(this._t('chooseCatalog'));
   const result=await this._api(type,{entry_id:entry,...data});
   if(entry!==this._entryId||key!==this._v109Key())return;
   this._weekState=result;this._weekStateEntry=entry;
   const unchanged=result.unchangedSlotIds?.length||0;this._message(unchanged?`${this._v110Text('kept')}: ${unchanged}`:'');
  }catch(error){this._message(`${this._t('error')}: ${error.message||error}`,true);}
  finally{
   this._v110Busy=false;if(this._tab==='week')this._renderTab();
   const target=[...this.shadowRoot.querySelectorAll('[data-week-select],[data-week-day-select],[data-week-action]')].find(node=>focusSlot&&node.dataset.weekSelect===focusSlot||focusDay&&node.dataset.weekDaySelect===focusDay||focusAction&&node.dataset.weekAction===focusAction);target?.focus({preventScroll:true});
  }
 }
 _v110Select(ids,selected){if(ids.length)return this._v110Change('cook4me/v20/week_select',{slot_ids:ids,selected});}
 _v110Regenerate(selected){const ids=this._v110Rows().filter(row=>(row.selected!==false)===selected).map(row=>row.id);if(ids.length)return this._v110Change('cook4me/v20/week_generate',{replace_slot_ids:ids});}
 _generateWeek(replace=''){return this._v110Change('cook4me/v20/week_generate',{replace_slot_id:replace||''});}
 _weekClear(id){return this._v110Change('cook4me/v20/week_slot_clear',{slot_id:id});}
 _v110Disclosure(kind,rows,empty,extra=''){
  const e=value=>this._escape(String(value));
  return `<details data-week-disclosure="${kind}"><summary>${e(this._v110Text(kind==='stock'?'covered':'buy'))} (${rows.length})</summary>${rows.length?rows.map(row=>`<div class="rx-list-row"><strong>${e(row.name||row.identity)}</strong> · ${e(this._displayAmount(row.quantity,row.unit))}${kind==='stock'?` ${e(this._t('required'))} · ${row.unlimited?'∞':e(this._displayAmount(row.available,row.unit))} ${e(this._t('available'))}`:''}</div>`).join(''):`<p class="muted">${e(this._v110Text(empty))}</p>`}${extra}</details>`;
 }
 _reservationHtml(){
  const rows=(this._weekState?.reservations?.items||[]).filter(row=>row.available!==null&&row.available!==undefined&&row.shortage!==null&&row.shortage!==undefined&&row.shortage<=1e-9);
  return this._v110Disclosure('stock',rows,'emptyStock');
 }
 _shoppingDeltaHtml(){
  const rows=this._weekState?.shoppingDelta||[],unknown=this._weekState?.reservations?.unknown||[],e=value=>this._escape(String(value));
  const extra=unknown.length?`<p class="muted">${e(this._v110Text('unknown'))}</p>${unknown.map(row=>`<div class="rx-list-row" data-week-stock-unknown><strong>${e(row.name||row.identity)}</strong> · ${e(this._displayAmount(row.quantity,row.unit))} ${e(this._t('required'))}</div>`).join('')}`:'';
  return this._v110Disclosure('shopping',rows,'emptyBuy',extra);
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.17.14');return result;}
 _v110Styles(){
  if(this.shadowRoot.querySelector('#v110Styles'))return;
  const style=document.createElement('style');style.id='v110Styles';style.textContent=`
   .v110-week-actions{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.v110-action{position:relative;min-width:48px;width:48px;height:48px;padding:10px!important;display:inline-flex!important;align-items:center;justify-content:center}.v110-action-mark{position:absolute;bottom:2px;right:3px;font-size:15px;line-height:1;background:var(--card-background-color);border-radius:3px}.v110-week-actions [data-week-action=none]{margin-inline-start:8px}.v110-selection-count{white-space:nowrap;font-size:.8rem;padding:4px}.v110-selection{display:flex;align-items:center;gap:6px;min-height:36px;font-size:.8rem;color:var(--secondary-text-color);cursor:pointer}.v110-day-selection{display:flex;gap:7px;align-items:center;cursor:pointer}.v110-selection input,.v110-day-selection input{width:20px!important;height:20px!important;min-width:20px;margin:0;accent-color:var(--primary-color);cursor:pointer}.v110-unselected .rx-v66-photo{opacity:.55}.v110-unselected .rx-v66-title h3{color:var(--secondary-text-color)}details[data-week-disclosure] summary{cursor:pointer;min-height:40px;line-height:1.5;padding:8px 0;box-sizing:border-box}details[data-week-disclosure] .rx-list-row{overflow-wrap:anywhere}#generateWeek.v110-action{width:48px;min-width:48px}.v110-action:focus-visible,.v110-selection input:focus-visible,.v110-day-selection input:focus-visible{outline:2px solid var(--primary-color);outline-offset:3px}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v110',Cook4MeRecipeHubPanelV110);
