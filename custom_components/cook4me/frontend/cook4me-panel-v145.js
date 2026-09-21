const V144='cook4me-recipe-hub-panel-v144';
if(!customElements.get(V144))await import('./cook4me-panel-v144.js?v=2026.9.21.9');
const BasePanel=customElements.get(V144);

const V145_MEALS=['breakfast','morningSnack','lunch','afternoonSnack','dinner','lateSnack'];

const V145_TEXT={
 en:{collapseHint:'Choose meals for each weekday',noMeals:'No meals'},
 de:{collapseHint:'Mahlzeiten für jeden Wochentag auswählen',noMeals:'Keine Mahlzeiten'},
 el:{collapseHint:'Επιλογή γευμάτων για κάθε ημέρα',noMeals:'Χωρίς γεύματα'}
};

class Cook4MeRecipeHubPanelV145 extends BasePanel{
 _v145Text(key){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return (V145_TEXT[lang]||V145_TEXT.en)[key]||V145_TEXT.en[key]||key;
 }
 _v145MealLabel(meal){
  return this._v93Text?.(meal)||this._t(meal);
 }

 // Week uses exactly the same canonical dayparts as Today.
 _v144MealRank(type){
  const index=V145_MEALS.indexOf(String(type||''));return index<0?V145_MEALS.length:index;
 }
 _v144WeekdaySchedule(settings,key){
  const raw=settings?.weekdayMealTypes?.[key];
  if(Array.isArray(raw))return V145_MEALS.filter(meal=>raw.includes(meal));
  const fallback=Array.isArray(settings?.mealTypes)?settings.mealTypes:['breakfast','lunch','dinner'];
  return V145_MEALS.filter(meal=>fallback.includes(meal));
 }
 _v144PatternHtml(days,settings){
  const e=v=>this._escape(String(v??'')),locale=this._hass?.language||this._uiIngredientLanguage?.()||'en';
  const rows=days.map(stamp=>{
   const key=this._v144WeekdayKey(stamp),selected=new Set(this._v144WeekdaySchedule(settings,key));
   const label=new Intl.DateTimeFormat(locale,{weekday:'long',day:'2-digit',month:'2-digit',timeZone:'UTC'}).format(new Date(stamp+'T12:00:00Z'));
   return `<div class="v144-day-pattern v145-day-pattern" data-v144-day="${e(key)}"><strong>${e(label)}</strong><div class="v144-day-meals v145-day-meals">${V145_MEALS.map(meal=>`<label class="v144-meal-toggle v145-meal-toggle"><input type="checkbox" data-v144-meal="${e(meal)}" ${selected.has(meal)?'checked':''}><span>${e(this._v145MealLabel(meal))}</span></label>`).join('')}</div><button type="button" class="btn secondary v144-no-meals v145-no-meals" data-v144-none>${e(this._v145Text('noMeals'))}</button></div>`;
  }).join('');
  return `<details class="card v144-week-pattern v145-week-pattern" data-v144-week-pattern><summary class="v145-pattern-summary"><span class="v145-pattern-summary-main"><ha-icon icon="mdi:calendar-week-outline" aria-hidden="true"></ha-icon><span><strong>${e(this._v144Text('weekdayPattern'))}</strong><small>${e(this._v145Text('collapseHint'))}</small></span></span><ha-icon class="v145-fold-chevron" icon="mdi:chevron-down" aria-hidden="true"></ha-icon></summary><div class="v145-pattern-body"><p class="muted">${e(this._v144Text('weekdayPatternHelp'))}</p><div class="v144-pattern-grid">${rows}</div><button type="button" class="btn" data-v144-save-pattern>${e(this._v144Text('savePattern'))}</button></div></details>`;
 }
 async _v144SaveWeekPattern(section){
  if(!section||!this._entryId)return;
  const schedule={},union=new Set();
  section.querySelectorAll('[data-v144-day]').forEach(row=>{
   const key=row.dataset.v144Day,meals=[...row.querySelectorAll('[data-v144-meal]:checked')].map(input=>input.dataset.v144Meal).filter(meal=>V145_MEALS.includes(meal));
   schedule[key]=V145_MEALS.filter(meal=>meals.includes(meal));for(const meal of schedule[key])union.add(meal);
  });
  const button=section.querySelector('[data-v144-save-pattern]');if(button)button.disabled=true;
  try{
   const payload={entry_id:this._entryId,weekday_meal_types:schedule};
   if(union.size)payload.meal_types=V145_MEALS.filter(meal=>union.has(meal));
   await this._api('cook4me/v20/week_settings_set',payload);
   this._v109FailedKey=null;await this._loadWeekState(true);this._message(this._v144Text('patternSaved'));
  }catch(error){this._message(`${this._t('error')}: ${error.message||error}`,true);}
  finally{if(button?.isConnected)button.disabled=false;}
 }

 _renderWeek(c){
  const result=super._renderWeek(c);
  this._v145Styles();
  const section=c?.querySelector?.('[data-v144-week-pattern]');
  if(section){section.open=false;section.removeAttribute('open');}
  return result;
 }
 _renderTab(){const result=super._renderTab();this._v145Styles();this.setAttribute('data-cook4me-build','2026.9.21.10');return result;}

 _v145Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v145Styles'))return;
  const style=document.createElement('style');style.id='v145Styles';style.textContent=`
   .v145-week-pattern{padding:0!important;overflow:hidden}.v145-pattern-summary{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:18px 20px;cursor:pointer;list-style:none;user-select:none}.v145-pattern-summary::-webkit-details-marker{display:none}.v145-pattern-summary-main{display:flex;align-items:center;gap:12px;min-width:0}.v145-pattern-summary-main>ha-icon{color:var(--primary-color);--mdc-icon-size:28px;flex:0 0 auto}.v145-pattern-summary-main>span{display:flex;flex-direction:column;gap:3px;min-width:0}.v145-pattern-summary-main strong{font-size:1.05rem}.v145-pattern-summary-main small{color:var(--secondary-text-color);font-size:.82rem;font-weight:400}.v145-fold-chevron{transition:transform .18s ease;color:var(--secondary-text-color)}.v145-week-pattern[open] .v145-fold-chevron{transform:rotate(180deg)}.v145-pattern-body{padding:0 20px 18px;border-top:1px solid var(--divider-color)}.v145-pattern-body>p{margin:14px 0 0}
   .v145-day-meals{grid-template-columns:repeat(6,minmax(100px,1fr))!important}.v145-day-pattern{grid-template-columns:minmax(145px,.7fr) minmax(700px,3fr) auto!important}.v145-meal-toggle{min-width:0}.v145-meal-toggle span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
   @media(max-width:1300px){.v145-day-pattern{grid-template-columns:1fr!important}.v145-day-meals{grid-template-columns:repeat(3,minmax(0,1fr))!important}.v145-no-meals{justify-self:start}}@media(max-width:700px){.v145-pattern-summary{padding:15px}.v145-pattern-body{padding:0 15px 15px}.v145-day-meals{grid-template-columns:repeat(2,minmax(0,1fr))!important}}@media(max-width:430px){.v145-day-meals{grid-template-columns:1fr!important}.v145-pattern-summary-main small{display:none}}@media(prefers-reduced-motion:reduce){.v145-fold-chevron{transition:none}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v145',Cook4MeRecipeHubPanelV145);
