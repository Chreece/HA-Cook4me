const V127='cook4me-recipe-hub-panel-v127';
if(!customElements.get(V127))await import('./cook4me-panel-v127.js?v=2026.9.20.1');
const BasePanel=customElements.get(V127);

const V128_TARGETS=[
 ['calorieTarget','energy','kcal',10000],
 ['proteinTarget','protein','g',1000],
 ['carbsTarget','carbs','g',2000],
 ['fatTarget','fat','g',1000],
 ['saturatedFatTarget','saturatedFat','g',1000],
 ['sugarsTarget','sugars','g',1000],
 ['fiberTarget','fiber','g',1000],
 ['saltTarget','salt','g',100],
 ['sodiumTarget','nutrientSodium','g',100],
];
const V128_MEALS=['breakfast','starter','salad','soup','main','side','dessert','snack'];
const V128_WORDS={
 en:{
  change:'Change',targets:'Nutrient targets',targetFor:'Targets for',daily:'Whole day',
  targetHelp:'Set full-day targets or choose a meal type and set targets for that meal. Empty values are ignored. These targets are used when recipes and plans are filtered or ranked.',
  manageBlocked:'Manage blocked ingredients',
  breakfast:'Breakfast',starter:'Starter',salad:'Salad',soup:'Soup',main:'Main',side:'Side',dessert:'Dessert',snack:'Snack'
 },
 de:{
  change:'Ändern',targets:'Nährwertziele',targetFor:'Ziele für',daily:'Gesamter Tag',
  targetHelp:'Lege Ziele für den ganzen Tag fest oder wähle einen Mahlzeitentyp und dessen Ziele. Leere Werte werden ignoriert. Die Ziele werden beim Filtern und Bewerten von Rezepten und Plänen berücksichtigt.',
  manageBlocked:'Gesperrte Zutaten verwalten',
  breakfast:'Frühstück',starter:'Vorspeise',salad:'Salat',soup:'Suppe',main:'Hauptgericht',side:'Beilage',dessert:'Dessert',snack:'Snack'
 },
 el:{
  change:'Αλλαγή',targets:'Στόχοι θρεπτικών',targetFor:'Στόχοι για',daily:'Ολόκληρη ημέρα',
  targetHelp:'Όρισε στόχους για ολόκληρη την ημέρα ή επίλεξε τύπο γεύματος και όρισε στόχους για αυτόν. Οι κενές τιμές αγνοούνται. Οι στόχοι εφαρμόζονται στο φιλτράρισμα και την κατάταξη συνταγών και πλάνων.',
  manageBlocked:'Διαχείριση αποκλεισμένων υλικών',
  breakfast:'Πρωινό',starter:'Ορεκτικό',salad:'Σαλάτα',soup:'Σούπα',main:'Κυρίως',side:'Συνοδευτικό',dessert:'Επιδόρπιο',snack:'Σνακ'
 }
};

class Cook4MeRecipeHubPanelV128 extends BasePanel{
 _v128Text(key){const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';return (V128_WORDS[lang]||V128_WORDS.en)[key]||V128_WORDS.en[key]||key;}
 _v128BlankTargets(){return Object.fromEntries(V128_TARGETS.map(([key])=>[key,'']));}
 _v128HasLegacy(row){return V128_TARGETS.some(([key])=>row?.[key]!==''&&row?.[key]!=null);}
 _v128ScopedTargets(row={}){
  const raw=row.nutrientTargets;
  if(raw&&typeof raw==='object'&&!Array.isArray(raw)){
   const daily={...this._v128BlankTargets(),...(raw.daily&&typeof raw.daily==='object'?structuredClone(raw.daily):{})};
   const mealTypes={};
   for(const meal of V128_MEALS){
    const values=raw.mealTypes?.[meal];
    if(values&&typeof values==='object')mealTypes[meal]={...this._v128BlankTargets(),...structuredClone(values)};
   }
   return {daily,mealTypes};
  }
  const daily=this._v128BlankTargets(),mealTypes={};
  if(this._v128HasLegacy(row)){
   const legacy=Object.fromEntries(V128_TARGETS.map(([key])=>[key,row[key]??'']));
   for(const meal of V128_MEALS)mealTypes[meal]=structuredClone(legacy);
  }
  return {daily,mealTypes};
 }
 _v83Diet(row={}){
  const result=super._v83Diet(row),scoped=this._v128ScopedTargets(row);
  if(row.nutrientTargets||this._v128HasLegacy(row))result.nutrientTargets=scoped;
  return result;
 }
 _v128TargetInputs(values){
  const e=v=>this._escape(String(v??''));
  return `<div class="v83-targets v128-targets">${V128_TARGETS.map(([key,label,unit,max])=>`<label class="field">${e(this._t(label))} (${unit})<input type="number" min="0" step="any" max="${max}" data-v128-target="${key}" value="${e(values[key])}"></label>`).join('')}</div>`;
 }
 _v128MealLabel(meal){return this._v128Text(meal);}
 _v128RenderTargetSection(details,row,state,id){
  if(!details)return;
  state.v128TargetScopes??=new Map();
  const scoped=this._v128ScopedTargets(row);
  row.nutrientTargets=scoped;
  let scope=state.v128TargetScopes.get(id)||'daily';
  if(scope!=='daily'&&!V128_MEALS.includes(scope))scope='daily';
  const values=scope==='daily'?scoped.daily:(scoped.mealTypes[scope]??=this._v128BlankTargets());
  const e=v=>this._escape(String(v??''));
  details.innerHTML=`
   <summary><span>${e(this._v128Text('targets'))}</span><span class="v128-expand-hint">${e(this._v128Text('change'))}<ha-icon icon="mdi:chevron-down" aria-hidden="true"></ha-icon></span></summary>
   <p class="muted v128-target-help">${e(this._v128Text('targetHelp'))}</p>
   <label class="field v128-nutrition-goal">${e(this._t('nutritionTarget'))}<select data-v128-goal>${this._todayGoalOptions(row.nutritionGoal||'balanced')}</select></label>
   <label class="field v128-target-scope">${e(this._v128Text('targetFor'))}<select data-v128-scope><option value="daily" ${scope==='daily'?'selected':''}>${e(this._v128Text('daily'))}</option>${V128_MEALS.map(meal=>`<option value="${meal}" ${scope===meal?'selected':''}>${e(this._v128MealLabel(meal))}</option>`).join('')}</select></label>
   ${this._v128TargetInputs(values)}
  `;
  details.querySelector('[data-v128-goal]').onchange=event=>{row.nutritionGoal=event.target.value;state.dirty=true;};
  details.querySelector('[data-v128-scope]').onchange=event=>{state.v128TargetScopes.set(id,event.target.value);this._v128RenderTargetSection(details,row,state,id);details.querySelector('[data-v128-scope]')?.focus();};
  details.querySelectorAll('[data-v128-target]').forEach(input=>{input.oninput=()=>{values[input.dataset.v128Target]=input.value;row.nutrientTargets=scoped;state.dirty=true;};});
 }
 _v83RenderProfiles(c,state){
  super._v83RenderProfiles(c,state);
  state.v128TargetScopes??=new Map();
  c.querySelectorAll('[data-v83-profile]').forEach(card=>{
   const id=card.dataset.v83Profile;
   const row=id==='household'?state.value.household:state.value.members.find(item=>item.id===id);
   if(row)this._v128RenderTargetSection(card.querySelector('.v83-target-section'),row,state,id);
  });
  this._v128Styles();
 }
 _v83ExclusionPicker(c,...args){
  super._v83ExclusionPicker(c,...args);
  const summary=c?.querySelector?.('.v83-ingredient-picker>summary');
  if(!summary)return;
  const label=document.createElement('span');label.textContent=this._v128Text('manageBlocked');
  const hint=document.createElement('span');hint.className='v128-expand-hint';hint.append(document.createTextNode(this._v128Text('change')));
  const icon=document.createElement('ha-icon');icon.setAttribute('icon','mdi:chevron-down');icon.setAttribute('aria-hidden','true');hint.append(icon);
  summary.replaceChildren(label,hint);
 }
 _filterActive(key){
  if(key==='nutrition'){
   const f=this._filters(),scoped=f.nutrientTargets;
   if(scoped&&typeof scoped==='object'){
    const rows=[scoped.daily,...Object.values(scoped.mealTypes||{})];
    if(rows.some(row=>row&&V128_TARGETS.some(([name])=>row[name]!==''&&row[name]!=null)))return true;
   }
  }
  return super._filterActive(key);
 }
 _renderTab(){
  const result=super._renderTab();
  this._v128Styles();
  this.setAttribute('data-cook4me-build','2026.9.20.2');
  return result;
 }
 _v128Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v128Styles'))return;
  const style=document.createElement('style');style.id='v128Styles';style.textContent=`
   .v83-target-section{margin:20px 0 30px!important}
   .v83-target-section>summary,.v83-ingredient-picker>summary{gap:10px}
   .v128-expand-hint{margin-left:auto;display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:600;color:var(--secondary-text-color);white-space:nowrap}
   .v128-expand-hint ha-icon{--mdc-icon-size:19px;transition:transform .18s ease}
   details[open]>.v128-expand-hint ha-icon,details[open]>summary>.v128-expand-hint ha-icon{transform:rotate(180deg)}
   .v128-target-help{margin:10px 0 16px}
   .v128-nutrition-goal{margin-bottom:20px!important}
   .v128-target-scope{margin:0 0 18px!important;max-width:420px}
   .v128-targets{margin-top:4px;margin-bottom:4px}
   [data-v83-exclusions]{display:block;margin-top:8px}
   [data-v83-exclusions]>h4{margin-top:0}
   .v83-ingredient-picker>summary{padding:2px 0}
   @media(max-width:680px){.v128-expand-hint{font-size:11px}.v128-nutrition-goal{margin-bottom:18px!important}.v83-target-section{margin-bottom:26px!important}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v128',Cook4MeRecipeHubPanelV128);
