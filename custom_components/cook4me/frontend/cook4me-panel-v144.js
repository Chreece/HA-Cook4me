const V143='cook4me-recipe-hub-panel-v143';
if(!customElements.get(V143))await import('./cook4me-panel-v143.js?v=2026.9.21.8');
const BasePanel=customElements.get(V143);

const V144_MEALS=['breakfast','lunch','snack','dinner'];
const V144_WEEKDAYS=['monday','tuesday','wednesday','thursday','friday','saturday','sunday'];

const V144_TEXT={
 en:{
  weekdayPattern:'Meals by weekday',weekdayPatternHelp:'Choose which meal slots should exist on each weekday. Full-week generation will skip unchecked slots completely.',
  savePattern:'Save weekday meal pattern',patternSaved:'Weekday meal pattern saved',noMeals:'No meals',
  unlimited:'Unlimited stock',unlimitedHelp:'This ingredient never runs out. Finite package amount and package count are not stored.',
  unlimitedDetails:'Package price and exact package nutrition are not stored for unlimited stock. The barcode-to-ingredient mapping is still remembered.',
  unlimitedBadge:'∞ Unlimited'
 },
 de:{
  weekdayPattern:'Mahlzeiten nach Wochentag',weekdayPatternHelp:'Wähle für jeden Wochentag die gewünschten Mahlzeiten. Beim Erstellen der Woche werden abgewählte Mahlzeiten vollständig ausgelassen.',
  savePattern:'Wochenmuster speichern',patternSaved:'Wochenmuster gespeichert',noMeals:'Keine Mahlzeiten',
  unlimited:'Unbegrenzter Vorrat',unlimitedHelp:'Diese Zutat geht nie aus. Endliche Packungsmenge und Packungsanzahl werden nicht gespeichert.',
  unlimitedDetails:'Packungspreis und exakte Packungs-Nährwerte werden bei unbegrenztem Vorrat nicht gespeichert. Die Barcode-Zuordnung zur Zutat bleibt erhalten.',
  unlimitedBadge:'∞ Unbegrenzt'
 },
 el:{
  weekdayPattern:'Γεύματα ανά ημέρα εβδομάδας',weekdayPatternHelp:'Επίλεξε ποια γεύματα θα υπάρχουν σε κάθε ημέρα. Η δημιουργία ολόκληρης εβδομάδας παραλείπει εντελώς όσα δεν είναι επιλεγμένα.',
  savePattern:'Αποθήκευση μοτίβου εβδομάδας',patternSaved:'Αποθηκεύτηκε το μοτίβο εβδομάδας',noMeals:'Χωρίς γεύματα',
  unlimited:'Απεριόριστο απόθεμα',unlimitedHelp:'Αυτό το υλικό δεν τελειώνει ποτέ. Δεν αποθηκεύεται πεπερασμένη ποσότητα ή αριθμός συσκευασιών.',
  unlimitedDetails:'Η τιμή συσκευασίας και τα ακριβή θρεπτικά στοιχεία συσκευασίας δεν αποθηκεύονται για απεριόριστο απόθεμα. Η αντιστοίχιση barcode → υλικό διατηρείται.',
  unlimitedBadge:'∞ Απεριόριστο'
 }
};

class Cook4MeRecipeHubPanelV144 extends BasePanel{
 _v144Text(key){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return (V144_TEXT[lang]||V144_TEXT.en)[key]||V144_TEXT.en[key]||key;
 }

 // ---------- Weekly chronological order + weekday generation pattern ----------
 _v144MealRank(type){
  const index=V144_MEALS.indexOf(String(type||'').toLowerCase());return index<0?V144_MEALS.length:index;
 }
 _v144SortedSlots(rows){
  return [...(rows||[])].sort((a,b)=>String(a?.date||'').localeCompare(String(b?.date||''))||this._v144MealRank(a?.mealType)-this._v144MealRank(b?.mealType)||String(a?.id||'').localeCompare(String(b?.id||'')));
 }
 _v144WeekdayKey(stamp){
  const date=new Date(String(stamp)+'T12:00:00Z'),day=date.getUTCDay();
  return V144_WEEKDAYS[(day+6)%7];
 }
 _v144WeekdaySchedule(settings,key){
  const raw=settings?.weekdayMealTypes?.[key];
  if(Array.isArray(raw))return V144_MEALS.filter(meal=>raw.includes(meal));
  const fallback=Array.isArray(settings?.mealTypes)?settings.mealTypes:['breakfast','lunch','dinner'];
  return V144_MEALS.filter(meal=>fallback.includes(meal));
 }
 _v144PatternHtml(days,settings){
  const e=v=>this._escape(String(v??'')),locale=this._hass?.language||this._uiIngredientLanguage?.()||'en';
  const rows=days.map(stamp=>{
   const key=this._v144WeekdayKey(stamp),selected=new Set(this._v144WeekdaySchedule(settings,key));
   const label=new Intl.DateTimeFormat(locale,{weekday:'long',day:'2-digit',month:'2-digit',timeZone:'UTC'}).format(new Date(stamp+'T12:00:00Z'));
   return `<div class="v144-day-pattern" data-v144-day="${e(key)}"><strong>${e(label)}</strong><div class="v144-day-meals">${V144_MEALS.map(meal=>`<label class="v144-meal-toggle"><input type="checkbox" data-v144-meal="${e(meal)}" ${selected.has(meal)?'checked':''}><span>${e(this._t(meal))}</span></label>`).join('')}</div><button type="button" class="btn secondary v144-no-meals" data-v144-none>${e(this._v144Text('noMeals'))}</button></div>`;
  }).join('');
  return `<section class="card v144-week-pattern" data-v144-week-pattern><div class="v144-pattern-head"><div><h3>${e(this._v144Text('weekdayPattern'))}</h3><p class="muted">${e(this._v144Text('weekdayPatternHelp'))}</p></div><ha-icon icon="mdi:calendar-week-outline" aria-hidden="true"></ha-icon></div><div class="v144-pattern-grid">${rows}</div><button type="button" class="btn" data-v144-save-pattern>${e(this._v144Text('savePattern'))}</button></section>`;
 }
 _v144InjectWeekPattern(c){
  if(!c||c.querySelector('[data-v144-week-pattern]'))return;
  const days=this._v67Days?.()||[],settings=this._weekState?.settings||{};
  if(!days.length)return;
  const top=c.querySelector('#generateWeek')?.closest('section.card');
  if(!top)return;
  top.insertAdjacentHTML('afterend',this._v144PatternHtml(days,settings));
  const section=c.querySelector('[data-v144-week-pattern]');
  section.querySelectorAll('[data-v144-none]').forEach(button=>button.onclick=()=>button.closest('[data-v144-day]')?.querySelectorAll('[data-v144-meal]').forEach(input=>input.checked=false));
  section.querySelector('[data-v144-save-pattern]').onclick=()=>void this._v144SaveWeekPattern(section);
 }
 async _v144SaveWeekPattern(section){
  if(!section||!this._entryId)return;
  const schedule={},union=new Set();
  section.querySelectorAll('[data-v144-day]').forEach(row=>{
   const key=row.dataset.v144Day,meals=[...row.querySelectorAll('[data-v144-meal]:checked')].map(input=>input.dataset.v144Meal).filter(meal=>V144_MEALS.includes(meal));
   schedule[key]=V144_MEALS.filter(meal=>meals.includes(meal));for(const meal of schedule[key])union.add(meal);
  });
  const button=section.querySelector('[data-v144-save-pattern]');if(button)button.disabled=true;
  try{
   const payload={entry_id:this._entryId,weekday_meal_types:schedule};
   if(union.size)payload.meal_types=V144_MEALS.filter(meal=>union.has(meal));
   await this._api('cook4me/v20/week_settings_set',payload);
   this._v109FailedKey=null;await this._loadWeekState(true);this._message(this._v144Text('patternSaved'));
  }catch(error){this._message(`${this._t('error')}: ${error.message||error}`,true);}
  finally{if(button?.isConnected)button.disabled=false;}
 }
 _renderWeek(c){
  const original=this._weekState;
  if(original?.slots)this._weekState={...original,slots:this._v144SortedSlots(original.slots)};
  let result;
  try{result=super._renderWeek(c);}finally{this._weekState=original;}
  this._v144InjectWeekPattern(c);this._v144Styles();return result;
 }

 // ---------- Scanner unlimited stock ----------
 _v78Fresh(mode){return {...super._v78Fresh(mode),unlimited:false};}
 _v144SetUnlimited(value){
  const d=this._v78Draft;if(!d||d.editLotId)return;
  d.unlimited=!!value;d.packageCount=1;this._v78Dirty=true;
  clearTimeout(this._v79PriceTimer);if(d.unlimited){d.priceLoading=false;d.priceResult=null;d.priceError='';}
  this._v111Paint();
 }
 _v144UnlimitedControl(kind='editor'){
  const d=this._v78Draft,e=v=>this._escape(String(v??''));
  return `<label class="v144-unlimited-toggle" data-v144-unlimited-control="${kind}"><input type="checkbox" data-v144-unlimited ${d?.unlimited?'checked':''}><span><strong>${e(this._v144Text('unlimited'))}</strong><small>${e(this._v144Text('unlimitedHelp'))}</small></span></label>`;
 }
 _v144DecorateUnlimited(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d||d.editLotId)return;
  const main=c.querySelector('main');
  if(main&&!main.querySelector('[data-v144-unlimited-control="editor"]')){
   const qty=main.querySelector('[data-draft="quantity"]')?.closest('label');
   if(qty)qty.insertAdjacentHTML('beforebegin',this._v144UnlimitedControl('editor'));
  }
  const result=c.querySelector('[data-v111-result]');
  if(result&&!result.querySelector('[data-v144-unlimited-control="result"]')){
   const amount=result.querySelector('.v111-amount');
   if(amount)amount.insertAdjacentHTML('beforebegin',this._v144UnlimitedControl('result'));
  }
  c.querySelectorAll('[data-v144-unlimited]').forEach(input=>{
   input.checked=!!d.unlimited;input.disabled=!!this._v78Submitted||!!this._v78Busy;
   input.onchange=()=>this._v144SetUnlimited(input.checked);
  });

  for(const selector of ['main [data-draft="quantity"]','main [data-draft="unit"]','[data-v112-count-edit]','[data-v112-count]','[data-v111-amount]','[data-v111-unit]']){
   const input=c.querySelector(selector);if(!input)continue;
   input.disabled=!!d.unlimited||!!this._v78Submitted;
   if(selector.includes('data-draft'))input.required=!d.unlimited;
  }
  const amount=result?.querySelector('.v111-amount');if(amount)amount.hidden=!!d.unlimited;
  if(result){
   let badge=result.querySelector('[data-v144-unlimited-badge]');
   if(d.unlimited&&!badge){badge=document.createElement('div');badge.dataset.v144UnlimitedBadge='';badge.className='v144-unlimited-badge';badge.textContent=this._v144Text('unlimitedBadge');const facts=result.querySelector('.v111-facts');facts?.after(badge);}
   if(badge)badge.hidden=!d.unlimited;
  }
  const price=c.querySelector('.v79-product-price');
  if(price){
   price.classList.toggle('v144-unlimited-price',!!d.unlimited);
   let note=price.querySelector('[data-v144-unlimited-note]');
   if(!note){note=document.createElement('p');note.dataset.v144UnlimitedNote='';note.className='v144-unlimited-note';note.textContent=this._v144Text('unlimitedDetails');price.append(note);}
   note.hidden=!d.unlimited;
   price.querySelectorAll('[data-v79-paid],[data-v79-paid-currency],[data-v79-shop]').forEach(input=>input.disabled=!!d.unlimited||!!this._v78Submitted);
  }
  const nutrition=main?.querySelector('[data-v78-basis]')?.closest('details');
  if(nutrition){nutrition.classList.toggle('v144-unlimited-disabled',!!d.unlimited);nutrition.querySelectorAll('input,select').forEach(input=>input.disabled=!!d.unlimited||!!this._v78Submitted);}
 }
 _v78RenderCapture(){super._v78RenderCapture();this._v144Styles();this._v144DecorateUnlimited();}
 _v111Paint(){super._v111Paint();this._v144Styles();this._v144DecorateUnlimited();}
 _v78ProductExtras(){
  const result={...(super._v78ProductExtras?.()||{})},d=this._v78Draft;
  if(d?.unlimited&&!d.editLotId){result.unlimited=true;result.package_count=1;delete result.paid_price;}
  return result;
 }
 async _v79PriceProduct(...args){
  const d=this._v78Draft;if(d?.unlimited){d.priceLoading=false;d.priceResult=null;d.priceError='';this._v79PaintProduct();return;}
  return super._v79PriceProduct(...args);
 }
 async _v78Save(){
  const d=this._v78Draft;if(!d?.unlimited||d.editLotId)return super._v78Save();
  const snapshot={quantity:d.quantity,unit:d.unit,packageCount:d.packageCount,nutrition:d.nutrition,paidAmount:d.paidAmount,paidCurrency:d.paidCurrency,paidShop:d.paidShop};
  d.quantity=Number(d.quantity)>0?d.quantity:1;d.unit=String(d.unit||'').trim()||'pcs';d.packageCount=1;d.nutrition={basisUnit:'',values:{}};d.paidAmount='';
  try{return await super._v78Save();}
  finally{
   if(this._v78Draft===d&&!d.scanApplied){Object.assign(d,snapshot);this._v111Paint();}
  }
 }

 _renderTab(){const result=super._renderTab();this._v144Styles();this.setAttribute('data-cook4me-build','2026.9.21.9');return result;}
 _v144Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v144Styles'))return;
  const style=document.createElement('style');style.id='v144Styles';style.textContent=`
   .v144-week-pattern{margin-top:12px!important}.v144-pattern-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}.v144-pattern-head h3{margin:0}.v144-pattern-head p{margin:5px 0 0}.v144-pattern-head>ha-icon{color:var(--primary-color);--mdc-icon-size:30px}.v144-pattern-grid{display:grid;gap:8px;margin:14px 0}.v144-day-pattern{display:grid;grid-template-columns:minmax(150px,.9fr) minmax(340px,2fr) auto;gap:12px;align-items:center;padding:10px 12px;border:1px solid var(--divider-color);border-radius:12px}.v144-day-meals{display:grid;grid-template-columns:repeat(4,minmax(80px,1fr));gap:6px}.v144-meal-toggle{display:flex;align-items:center;gap:6px;padding:7px 9px;border:1px solid var(--divider-color);border-radius:9px;cursor:pointer}.v144-meal-toggle:has(input:checked){border-color:var(--primary-color);background:color-mix(in srgb,var(--primary-color) 10%,transparent)}.v144-meal-toggle input{width:auto;min-height:auto}.v144-no-meals{white-space:nowrap}
   .v144-unlimited-toggle{display:flex!important;flex-direction:row!important;align-items:flex-start!important;gap:10px!important;padding:10px 12px;border:1px solid color-mix(in srgb,var(--primary-color) 45%,var(--divider-color));border-radius:11px;background:color-mix(in srgb,var(--primary-color) 7%,transparent);margin:7px 0}.v144-unlimited-toggle input{width:20px!important;min-height:20px!important;flex:0 0 20px;margin-top:2px}.v144-unlimited-toggle>span{display:flex;flex-direction:column;gap:3px}.v144-unlimited-toggle small{color:var(--secondary-text-color);line-height:1.35}.v144-unlimited-badge{padding:9px 11px;border-radius:10px;background:color-mix(in srgb,var(--primary-color) 14%,transparent);border:1px solid color-mix(in srgb,var(--primary-color) 55%,transparent);font-weight:750}.v144-unlimited-note{padding:9px 11px;border-radius:9px;background:color-mix(in srgb,var(--primary-color) 9%,transparent);border-left:3px solid var(--primary-color);line-height:1.4}.v79-product-price.v144-unlimited-price>[data-v79-estimate],.v79-product-price.v144-unlimited-price>.v78-fields,.v79-product-price.v144-unlimited-price>label.field,.v79-product-price.v144-unlimited-price>p.muted{display:none!important}.v144-unlimited-disabled{opacity:.55}.v144-unlimited-disabled>summary{cursor:default}
   @media(max-width:900px){.v144-day-pattern{grid-template-columns:1fr}.v144-day-meals{grid-template-columns:repeat(2,minmax(0,1fr))}.v144-no-meals{justify-self:start}}@media(max-width:520px){.v144-day-meals{grid-template-columns:1fr 1fr}.v144-meal-toggle{font-size:.85rem}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v144',Cook4MeRecipeHubPanelV144);
