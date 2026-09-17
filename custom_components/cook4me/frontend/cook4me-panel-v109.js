import './cook4me-panel-v108.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v108');
const NUTRIENTS=[['energy',['energyKcal','calories'],'kcal'],['protein',['proteinG','protein'],'g'],['carbs',['carbohydrateG','carbohydrates','carbs'],'g'],['fat',['fatG','fat'],'g'],['saturatedFat',['saturatedFatG','saturatedFat'],'g'],['sugars',['sugarsG','sugarG','sugars'],'g'],['fiber',['fiberG','fiber'],'g'],['salt',['saltG','salt'],'g'],['nutrientSodium',['sodiumG','sodium'],'g']];
const TEXT={
 en:{summary:'Planned nutrition & cost',date:'Date',meals:'Meals',total:'Week total',basis:'Totals for the quantities in the displayed recipes, using their original ingredients. ≈ Estimated or incomplete values; — unavailable.',hidden:'Saved meals hidden by the current filters',failed:'Could not refresh the weekly plan.',retry:'Retry'},
 de:{summary:'Geplante Nährwerte & Kosten',date:'Datum',meals:'Mahlzeiten',total:'Wochensumme',basis:'Summen für die Mengen der angezeigten Rezepte und ihre Originalzutaten. ≈ Geschätzte oder unvollständige Werte; — nicht verfügbar.',hidden:'Durch die aktuellen Filter ausgeblendete gespeicherte Mahlzeiten',failed:'Der Wochenplan konnte nicht aktualisiert werden.',retry:'Erneut versuchen'},
 el:{summary:'Θρεπτικά & κόστος πλάνου',date:'Ημερομηνία',meals:'Γεύματα',total:'Σύνολο εβδομάδας',basis:'Σύνολα για τις ποσότητες των εμφανιζόμενων συνταγών, με τα αρχικά υλικά τους. ≈ Εκτιμώμενες ή ελλιπείς τιμές· — μη διαθέσιμη τιμή.',hidden:'Αποθηκευμένα γεύματα που κρύβονται από τα τωρινά φίλτρα',failed:'Δεν ήταν δυνατή η ανανέωση του εβδομαδιαίου πλάνου.',retry:'Δοκίμασε ξανά'}
};
const number=value=>value!==null&&value!==undefined&&value!==''&&typeof value!=='boolean'&&Number.isFinite(Number(value))&&Number(value)>=0?Number(value):null;
const first=(values,keys)=>{for(const key of keys){const value=number(values?.[key]);if(value!==null)return value;}return null;};
class Cook4MeRecipeHubPanelV109 extends BasePanel{
 _v109Text(key){return (TEXT[this._uiIngredientLanguage()]||TEXT.en)[key]||key;}
 _v109Key(){return JSON.stringify([this._prefKey(),this._v67Today(),this._uiIngredientLanguage(),this._filters(),this._currencyState?.currency,this._v79Revision||0]);}
 async _api(type,data={}){
  const week=/\/(week_state|week_generate|week_add_shopping)$/.test(type),key=this._v109Key();
  if(week)data={...data,shared_filters:structuredClone(this._filters()),ui_language:this._uiIngredientLanguage()};
  let result=await super._api(type,data);
  if(/\/(week_state|week_generate)$/.test(type)&&!Array.isArray(result?.slots))throw new Error(this._v109Text('failed'));
  if(/\/(week_slot_clear|leftover_consume|cost_settings_set)$/.test(type)&&result?.slots){
   if(key!==this._v109Key()||data.entry_id&&data.entry_id!==this._entryId)throw new Error(this._v83Text('changed'));
   const fresh=await this._api('cook4me/v20/week_state',{entry_id:data.entry_id||this._entryId});result={...result,...fresh};
  }
  if(week&&result?.slots){
   if(key!==this._v109Key()||data.entry_id&&data.entry_id!==this._entryId)throw new Error(this._v83Text('changed'));
   result._v109Key=key;
   // Seed the same price state the cards use; old browser previews cannot win.
   for(const slot of result.slots)if(!slot.leftoverId&&slot.recipe?.cost){const state=this._v79CostState(slot.recipe);state.cost=slot.recipe.cost;}
  }
  return result;
 }
 async _loadWeekState(force=false){
  if(this._weekLoading||!this._entryId||(!force&&this._v109FailedKey===this._v109Key()))return;
  const key=this._v109Key(),entry=this._entryId;this._weekLoading=true;this._v109FailedKey=null;
  this._v67WeekLoaded=`${this._prefKey()}:${this._v67Today()}`;
  try{const result=await this._api('cook4me/v20/week_state',{entry_id:entry,history_days:30});if(key===this._v109Key()){this._weekState=result;this._weekStateEntry=entry;}}
  catch(error){if(key===this._v109Key()){this._v109FailedKey=key;this._message(`${this._v109Text('failed')} ${error.message||error}`,true);}}
  finally{this._weekLoading=false;if(this._tab==='week')this._renderTab();}
 }
 _renderWeek(c){
  this._v109Styles();
  const original=this._weekState,key=this._v109Key(),current=original?._v109Key===key;
  if(!current)this._weekState={weekStart:this._v67Today(),slots:[],settings:{}};
  try{super._renderWeek(c);}finally{this._weekState=original;}
  const summary=c.querySelector('[data-week-summary]');if(summary)summary.querySelector('h3').textContent=this._v109Text('summary');
  if(!current&&summary){
   summary.querySelector('[data-week-totals]')?.replaceChildren(document.createTextNode(this._t('loading')));
   if(this._v109FailedKey===key){const retry=document.createElement('button');retry.className='btn secondary';retry.dataset.weekRetry='';retry.textContent=this._v109Text('retry');retry.onclick=()=>void this._loadWeekState(true);summary.append(retry);}
  }
  if(current&&original.filteredSlotCount){const note=document.createElement('p');note.className='muted';note.dataset.weekFiltered='';note.textContent=`${this._v109Text('hidden')}: ${original.filteredSlotCount}`;c.querySelector('.rx-week-grid')?.before(note);}
  this._v109RefreshSummary();
  if(this._entryId&&!current&&!this._weekLoading&&this._v109FailedKey!==key)queueMicrotask(()=>void this._loadWeekState());
 }
 _v66PreferredLanguage(recipe){
  if(this._tab!=='week')return super._v66PreferredLanguage(recipe);
  const allowed=this._filters().languages||[],preferred=super._v66PreferredLanguage(recipe);
  return allowed.includes(preferred)?preferred:recipe.language;
 }
 _v109Rows(visible=false){
  const days=this._v67Days(),ids=visible?new Set([...this.shadowRoot.querySelectorAll('.rx-week-grid [data-slot-id]')].map(node=>node.dataset.slotId)):null;
  return (this._weekState?.slots||[]).filter(slot=>days.includes(slot.date)&&(!ids||ids.has(String(slot.id))));
 }
 _v109Totals(slots){
  const result={count:slots.length,values:NUTRIENTS.map(()=>({value:0,known:0,estimated:false})),cost:{},priced:0,partial:false,estimated:false};
  for(const slot of slots){
   const recipe=slot.recipe||this._leftoverById(slot.leftoverId)?.recipe||{};
   const n=slot.leftoverId?slot.nutrition||{}:recipe.catalogNutrition||recipe.nutrition||slot.nutrition||{};
   const servings=first(recipe,['servings','groupSize'])??first(recipe.yield,['quantity','quantityDisplay'])??number(n.servings);
   const rawCoverage=typeof n.coverage==='object'?number(n.coverage?.coveragePercent):number(n.coverage);
   const coverage=rawCoverage===null?null:typeof n.coverage==='object'?rawCoverage/100:rawCoverage;
   NUTRIENTS.forEach(([,aliases],i)=>{
    let value=first(n.totals,aliases);if(value===null&&servings>0){const perServing=first(n.perServing,aliases);if(perServing!==null)value=perServing*servings;}
    if(value===null||n.available===false)return;
    const cell=result.values[i];cell.value+=value;cell.known++;cell.estimated ||= n.estimated===true||n.fullyCovered===false||(coverage!==null&&coverage<1);
   });
   const cost=slot.leftoverId?slot.cost:this._v79CostState(recipe).cost||{};
   const values=cost?.budgetTotalsByCurrency??cost?.totalsByCurrency??{};
   let priced=false;
   for(const [currency,raw] of Object.entries(values)){const value=number(raw);if(value===null)continue;result.cost[currency]=(result.cost[currency]||0)+value;priced=true;}
   if(priced)result.priced++;
   result.partial ||= !priced||!(cost?.budgetComplete??cost?.complete??false);
   result.estimated ||= this._v99Confidence(cost)!=='personal';
  }
  return result;
 }
 _v109Money(totals){
  if(!totals.priced)return '—';
  return `${totals.partial?'! ':totals.estimated?'≈ ':''}${this._v79Money(totals.cost)}`;
 }
 _v109Table(slots){
  const e=value=>this._escape(String(value)),format=(value,digits=1)=>new Intl.NumberFormat(this._hass?.language||'en',{maximumFractionDigits:digits}).format(value);
  const labels=[this._v109Text('meals'),...NUTRIENTS.map(([key,,unit])=>`${this._t(key)} (${unit})`),this._t('mealCost')];
  const cells=totals=>`<td data-label="${e(labels[0])}">${totals.count}</td>${totals.values.map((cell,i)=>`<td data-label="${e(labels[i+1])}">${cell.known?`${cell.estimated||cell.known<totals.count?'≈ ':''}${format(cell.value,i===0?0:2)}`:'—'}</td>`).join('')}<td data-week-cost data-label="${e(labels.at(-1))}">${e(this._v109Money(totals))}</td>`;
  return `<p class="muted">${e(this._v109Text('basis'))}</p><div style="overflow:auto"><table class="rx-week-table v109-summary-table"><thead><tr><th>${e(this._v109Text('date'))}</th>${labels.map(label=>`<th>${e(label)}</th>`).join('')}</tr></thead><tbody>${this._v67Days().map(day=>{const totals=this._v109Totals(slots.filter(slot=>slot.date===day));return `<tr data-week-summary-date="${day}" ${totals.count?'':'data-week-empty'}><th scope="row">${e(new Intl.DateTimeFormat(this._hass?.language||'en',{day:'2-digit',month:'2-digit',timeZone:'UTC'}).format(new Date(day+'T12:00:00Z')))}</th>${cells(totals)}</tr>`;}).join('')}</tbody><tfoot><tr data-week-total><th scope="row">${e(this._v109Text('total'))}</th>${cells(this._v109Totals(slots))}</tr></tfoot></table></div>`;
 }
 _dashboardHtml(){return `<div data-week-totals>${this._v109Table(this._v109Rows())}</div>`;}
 _v109RefreshSummary(){
  if(this._tab!=='week'||this._weekState?._v109Key!==this._v109Key())return;
  const holder=this.shadowRoot.querySelector('[data-week-totals]');if(!holder)return;
  const slots=this._v109Rows(true);holder.innerHTML=this._v109Table(slots);
  const days=this._v67Days(),cost=this.shadowRoot.querySelector('#generateWeek')?.closest('.toolbar')?.querySelector('.muted');
  if(cost)cost.textContent=`${days[0]} – ${days[6]} · ${this._t('weeklyCost')}: ${this._v109Money(this._v109Totals(slots))}`;
 }
 _v109ScheduleSummary(){if(this._v109SummaryQueued||this._tab!=='week')return;this._v109SummaryQueued=true;queueMicrotask(()=>{this._v109SummaryQueued=false;this._v109RefreshSummary();});}
 _v79PaintRecipe(recipe,state){super._v79PaintRecipe(recipe,state);this._v109ScheduleSummary();}
 _renderRecipeDialog(){super._renderRecipeDialog();this._v109ScheduleSummary();}
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.17.13');return result;}
 _v109Styles(){
  if(this.shadowRoot.querySelector('#v109Styles'))return;
  const style=document.createElement('style');style.id='v109Styles';style.textContent=`
   .v109-summary-table thead th{white-space:normal;font-size:.85rem;line-height:1.4}.v109-summary-table tfoot{font-weight:700}.v109-summary-table td::before{display:none}
   @media(max-width:700px){.v109-summary-table,.v109-summary-table tbody,.v109-summary-table tfoot{display:block}.v109-summary-table thead{display:none}.v109-summary-table tr{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 12px;margin-top:12px;padding:10px;border:1px solid var(--divider-color);border-radius:12px}.v109-summary-table th[scope=row]{grid-column:1/-1;white-space:normal;padding:6px 0}.v109-summary-table td{display:flex;justify-content:space-between;align-items:center;gap:8px;min-width:0;white-space:normal;overflow-wrap:anywhere;padding:8px 0;font-size:.85rem}.v109-summary-table td::before{display:block;content:attr(data-label);font-size:.75rem;color:var(--secondary-text-color);font-weight:400}.v109-summary-table [data-week-cost]{grid-column:1/-1}.v109-summary-table [data-week-empty] td:nth-child(n+3):not([data-week-cost]){display:none}.v109-summary-table [data-week-empty] [data-week-cost]{grid-column:auto}.v109-summary-table tfoot tr{border-color:var(--primary-color)}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v109',Cook4MeRecipeHubPanelV109);
