// Fold ingredient choices while keeping all original inputs/listeners intact.
// Move Home options into this same dialog; the actual filter preference keys
// and backend request contract do not change.
const TEXT={
 en:{stock:'At-home availability',list:'Choose preferred ingredients',selected:n=>`${n} selected`,present:'At home',presentTitle:'Matching stock exists, but its quantity for this recipe needs verification.',incomplete:'Some stored ingredients need quantity verification.'},
 de:{stock:'Vorrat zu Hause',list:'Bevorzugte Zutaten auswählen',selected:n=>`${n} ausgewählt`,present:'Zu Hause',presentTitle:'Passender Vorrat ist vorhanden; die Rezeptmenge muss überprüft werden.',incomplete:'Einige Vorräte müssen mengenmäßig überprüft werden.'},
 el:{stock:'Διαθέσιμα στο σπίτι',list:'Επιλογή προτιμώμενων υλικών',selected:n=>`${n} επιλεγμένα`,present:'Στο σπίτι',presentTitle:'Υπάρχει αντίστοιχο προϊόν στο απόθεμα, αλλά η ποσότητα της συνταγής χρειάζεται επαλήθευση.',incomplete:'Υπάρχουν προϊόντα στο απόθεμα, αλλά ορισμένες ποσότητες χρειάζονται επαλήθευση.'}
};
const filled=x=>x!==''&&x!=null;
export const homeControlsCount=f=>Number(!!f?.onlyHome)+Number(f?.preferExpiring===false)+Number(filled(f?.maxMissing))+Number(f?.avoidRecentDays!=null&&Number(f.avoidRecentDays)!==7);
export const ingredientControlsCount=f=>new Set(Array.isArray(f?.ingredients)?f.ingredients:[]).size+homeControlsCount(f);
const quantity=x=>x!==''&&x!=null&&Number.isFinite(Number(x))?Number(x):null;
export const hasStoredAmount=row=>!!row?.unlimited||Array.isArray(row?.lots)&&row.lots.some(lot=>(quantity(lot?.quantity)??0)>0)||(quantity(row?.quantity)??0)>0;
export function reconcileStoredIngredient(coverage,stock,labels){
 if(!coverage||!stock?.length||coverage.status==='staple'||(Number.isFinite(coverage.percent)&&coverage.percent>0))return coverage;
 const present=stock.filter(hasStoredAmount);
 if(!present.length)return coverage;
 if(present.some(row=>row.unlimited))return {...coverage,status:'staple',percent:100};
 if(coverage.percent!==0&&coverage.percent!==null&&coverage.percent!==undefined)return coverage;
 // Positive linked stock is evidence of presence, NOT proof of enough stock.
 return {...coverage,status:'at_home_quantity_unverified',percent:null,displayLabel:labels.present,displayTitle:labels.presentTitle};
}
export const IngredientsHomeFilterMixin=Base=>class extends Base{
 _v292Text(key){
  const code=String(this._langCode?.()||this._uiIngredientLanguage?.()||this._hass?.language||'en').toLowerCase().split(/[-_]/)[0];
  return (TEXT[code]||TEXT.en)[key]||TEXT.en[key]||key;
 }
 _filterActive(key){
  if(key==='home')return false;
  if(key==='ingredients')return !!(super._filterActive(key)||super._filterActive('home'));
  return super._filterActive(key);
 }
 _v98FilterCount(key){
  if(key==='home')return 0;
  if(key==='ingredients')return ingredientControlsCount(this._filters());
  return super._v98FilterCount(key);
 }
 _v93FilterSummary(key){
  if(key==='ingredients'&&!this._filters()?.ingredients?.length&&homeControlsCount(this._filters())>0)return this._v292Text('stock');
  return super._v93FilterSummary(key);
 }
 _v292RemoveHomeButton(root){root?.querySelectorAll?.('[data-filter="home"]').forEach(button=>button.remove());}
 _mountFilters(container,...args){
  const result=super._mountFilters(container,...args);this._v292RemoveHomeButton(container);return result;
 }
 _v83MergeToolbar(container,...args){
  const result=super._v83MergeToolbar(container,...args);this._v292RemoveHomeButton(container);return result;
 }
 _renderTab(...args){
  const result=super._renderTab(...args);this._v292RemoveHomeButton(this.shadowRoot);this._v292Styles();return result;
 }
 _v292Field(input,label){
  const field=document.createElement('label');field.className=input.type==='checkbox'?'v292-checkbox':'v292-field';
  const name=document.createElement('span');name.textContent=label;
  if(input.type==='checkbox')field.append(input,name);else field.append(name,input);
  return field;
 }
 _v292InsertHome(dialog,f){
  const group=document.createElement('section');group.className='v292-home';group.dataset.v292Home='';
  const heading=document.createElement('h3');heading.textContent=this._v292Text('stock');group.append(heading);
  const check=(key)=>{
   const el=document.createElement('input');el.type='checkbox';el.dataset.field=key;el.checked=!!f[key];
   return this._v292Field(el,this._t(key));
  };
  const number=(key,label)=>{
   const el=document.createElement('input');el.type='number';el.step='1';el.min='0';el.dataset.field=key;
   el.value=filled(f[key])?String(f[key]):'';
   return this._v292Field(el,this._t(label));
  };
  group.append(check('onlyHome'),check('preferExpiring'),number('maxMissing','maxMissing'),number('avoidRecentDays','avoidRecent'));
  const anchor=dialog.querySelector('[data-v223-season]')||dialog.querySelector('[data-ingredient-search]');
  anchor?.before(group);return group;
 }
 _v292Fold(dialog){
  const search=dialog.querySelector('[data-ingredient-search]'),choices=dialog.querySelector('[data-ingredient-choices]'),bulk=dialog.querySelector('[data-v124-bulk="ingredients"]');
  if(!search||!choices)return;
  const control=document.createElement('button');
  control.type='button';control.className='btn secondary v292-fold';control.dataset.v292Fold='';
  choices.id='v292IngredientChoices';control.setAttribute('aria-controls',choices.id);
  control.innerHTML='<ha-icon icon="mdi:chevron-right" aria-hidden="true"></ha-icon><span></span>';
  search.before(control);
  const nodes=[search,bulk,choices].filter(Boolean);let open=false;
  const update=()=>{
   for(const el of nodes){el.hidden=!open;el.toggleAttribute('data-v292-collapsed',!open);}
   control.setAttribute('aria-expanded',String(open));
   const selected=[...choices.querySelectorAll('input[data-list="ingredients"]')].filter(i=>i.checked).length;
   const label=this._v292Text('list')+' ('+this._v292Text('selected')(selected)+')';
   control.querySelector('span').textContent=label;control.setAttribute('aria-label',label);
   control.querySelector('ha-icon')?.setAttribute('icon',open?'mdi:chevron-down':'mdi:chevron-right');
  };
  control.onclick=()=>{open=!open;update();if(open)search.focus();};
  dialog.addEventListener('change',e=>{if(e.target.matches?.('[data-list="ingredients"]'))update();});
  update();
 }
 _showFilter(key){
  const actual=key==='home'?'ingredients':key;const result=super._showFilter(actual);
  if(actual!=='ingredients')return result;
  const dialog=this.shadowRoot?.querySelector('[data-filter-dialog="ingredients"] .rx-dialog');
  if(!dialog||dialog.querySelector('[data-v292-home]'))return result;
  this._v292InsertHome(dialog,this._filters());this._v292Fold(dialog);this._v292Styles();return result;
 }
 _v292Stock(item){
  if(!item||typeof item!=='object'||typeof this._v218StockMatches!=='function')return [];
  try{return (this._houseIngredients||[]).filter(row=>this._v218StockMatches(item,row));}
  catch{return [];}
 }
 _coverage(recipe,item){
  const result=super._coverage(recipe,item);
  const code=String(this._langCode?.()||this._uiIngredientLanguage?.()||'en').toLowerCase().split(/[-_]/)[0];
  return reconcileStoredIngredient(result,this._v292Stock(item),TEXT[code]||TEXT.en);
 }
 _bindCards(container,...args){
  const result=super._bindCards(container,...args);
  for(const card of container?.querySelectorAll?.('[data-v66-ref]')||[]){
   const recipe=this._v66Refs?.get(card.dataset.v66Ref)?.recipe;
   if(!recipe?.ingredients?.some(item=>this._coverage(recipe,item)?.status==='at_home_quantity_unverified'))continue;
   const badge=card.querySelector('[data-v241-stock]');if(!badge)continue;
   badge.dataset.state='partial';badge.title=this._v292Text('incomplete');
   badge.setAttribute('aria-label',badge.title);
   const value=badge.querySelector('span');if(value)value.textContent='—';
  }
  return result;
 }
 _v292Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v292IngredientFilterStyles'))return;
  const style=document.createElement('style');style.id='v292IngredientFilterStyles';
  style.textContent=`
   [data-filter-dialog="ingredients"] .v292-home{display:grid;gap:8px;margin:4px 0 12px}
   [data-filter-dialog="ingredients"] .v292-home h3{margin:0 0 3px;font-size:1rem}
   [data-filter-dialog="ingredients"] .v292-checkbox{display:flex;align-items:center;gap:12px;min-height:48px;padding:12px;border-radius:12px;background:var(--card-background-color)}
   [data-filter-dialog="ingredients"] .v292-checkbox input{flex:0 0 auto}
   [data-filter-dialog="ingredients"] .v292-field{display:grid;gap:5px;margin:0 0 6px;font-weight:600}
   [data-filter-dialog="ingredients"] .v292-field input{box-sizing:border-box;width:100%;min-height:44px;border-radius:10px}
   [data-filter-dialog="ingredients"] .v292-fold{display:flex;align-items:center;justify-content:flex-start;gap:8px;width:100%;min-height:46px;text-align:left;margin:12px 0 6px}
   [data-filter-dialog="ingredients"] .v292-fold ha-icon{--mdc-icon-size:20px}
   [data-filter-dialog="ingredients"] [data-v292-collapsed]{display:none!important}
   [data-filter-dialog="ingredients"] [data-ingredient-choices]{max-height:min(48dvh,450px);overflow-y:auto}
  `;
  this.shadowRoot.append(style);
 }
};
