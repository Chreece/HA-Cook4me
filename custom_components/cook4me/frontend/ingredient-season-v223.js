// An optional catalog view, not a restriction on stock, recipes or purchases.
const TEXT={
 en:{label:'Seasonal ingredients',help:'Use the seasonal calendar for your shopping country. Ingredients without a reviewed calendar and selected ingredients stay visible.',country:'Choose your shopping country in Integration settings.'},
 de:{label:'Saisonale Zutaten',help:'Saisonkalender für dein Einkaufsland verwenden. Zutaten ohne geprüften Kalender und ausgewählte Zutaten bleiben sichtbar.',country:'Wähle dein Einkaufsland in den Integrationseinstellungen.'},
 el:{label:'Υλικά εποχής',help:'Χρήση του ημερολογίου εποχικότητας για τη χώρα αγορών. Τα υλικά χωρίς ελεγμένο ημερολόγιο και τα επιλεγμένα υλικά παραμένουν ορατά.',country:'Επίλεξε τη χώρα αγορών στις ρυθμίσεις ενσωμάτωσης.'}
};
const language=value=>String(value||'en').toLowerCase().split(/[-_]/)[0];

export function seasonMonth(now=new Date(),timeZone){
 try{return Number(new Intl.DateTimeFormat('en',{month:'numeric',timeZone}).format(now));}
 catch{return now.getMonth()+1;}
}

export function seasonChoiceVisible(row,country,month){
 const season=row?.lifecycle?.seasonality;
 if(season?.status!=='reviewed'||!Number.isInteger(month)||month<1||month>12)return true;
 const region=(Array.isArray(season.regions)?season.regions:[]).find(item=>item.country===String(country||'').trim().toUpperCase());
 const months=region?.months;
 if(!Array.isArray(months)||!months.length||months.some(value=>!Number.isInteger(value)||value<1||value>12))return true;
 // Calendars may only list monthly highlights. Outside this list means hidden
 // by this opt-in view; it must not change the advisory backend's unknown state.
 return months.includes(month);
}

export const IngredientSeasonMixin=Base=>class extends Base{
 _v223Context(){
  const settings=this._v79Settings||this._weekState?.costSettings||{};
  return {country:String(settings.country||this._hass?.config?.country||'').trim().toUpperCase(),
   month:seasonMonth(new Date(),this._hass?.config?.time_zone)};
 }
 _v223Name(row){return this._v221IngredientNames?.(row)?.label||row.name||'';}
 _v223SeasonRows(rows,selected=new Set(),identity=row=>this._todayIngredientIdentity(row),enabled=this._filters().seasonalIngredients===true){
  if(!enabled)return rows;
  const {country,month}=this._v223Context();
  return rows.filter(row=>selected.has(identity(row))||seasonChoiceVisible(row,country,month));
 }
 _v223Control(parent,before,refresh,{draft=false}={}){
  if(!parent)return;
  let holder=parent.querySelector(':scope > [data-v223-season]');
  if(!holder){
   holder=document.createElement('div');holder.dataset.v223Season='';
   const label=document.createElement('label'),input=document.createElement('input'),name=document.createElement('span'),help=document.createElement('small');
   input.type='checkbox';input.dataset.v223Toggle='';input.checked=this._filters().seasonalIngredients===true;
   if(draft)input.dataset.field='seasonalIngredients';
   label.append(input,name);holder.append(label,help);parent.insertBefore(holder,before||null);
   input.onchange=()=>{
    if(!draft){
     this._persistPreferences({filters:{...this._filters(),seasonalIngredients:input.checked}});
     for(const catalog of this.shadowRoot.querySelectorAll('[data-v84-catalog]'))if(catalog!==parent)this._v84CatalogRows(catalog);
    }
    refresh();
   };
  }
  const ui=language(this._uiIngredientLanguage()),market=language(this._v140SupermarketLanguage()),t=TEXT[ui]||TEXT.en;
  const marketLabel=TEXT[market]?.label;
  holder.querySelector('span').textContent=t.label+(market!==ui&&marketLabel&&marketLabel!==t.label?` (${marketLabel})`:'');
  const {country,month}=this._v223Context();let context='';
  if(country){
   try{context=`${new Intl.DisplayNames([market],{type:'region'}).of(country)} · ${new Intl.DateTimeFormat(market,{month:'long',timeZone:'UTC'}).format(new Date(Date.UTC(2026,month-1,15)))}`;}
   catch{context=`${country} · ${month}`;}
  }
  holder.querySelector('small').textContent=(context?`${context}. `:t.country+' ')+t.help;
  if(!draft)holder.querySelector('input').checked=this._filters().seasonalIngredients===true;
  if(!this.shadowRoot.querySelector('#v223SeasonStyle')){
   const style=document.createElement('style');style.id='v223SeasonStyle';
   style.textContent='[data-v223-season]{margin:10px 0;min-width:0}[data-v223-season]>label{display:flex;align-items:center;gap:8px;cursor:pointer}[data-v223-season] input[type=checkbox]{width:20px;min-height:20px;flex:0 0 20px}[data-v223-season] small{display:block;opacity:.8;margin-top:5px;overflow-wrap:anywhere}';
   this.shadowRoot.append(style);
  }
  return holder;
 }
 _v84CatalogRows(c){return this._v220KeepPosition(()=>this._v223CatalogRows(c));}
 _v223CatalogRows(c){
  const select=c.querySelector('[data-v105-select]');if(!select)return super._v84CatalogRows(c);
  const state=this._v84Catalog;
  const rows=this._v223SeasonRows(this._ingredientCatalog||[],new Set([state.selected]),row=>this._houseKey(row))
   .filter(row=>this._ingredientQueryMatches(row,state.query));
  select._cook4meRows=rows;select.replaceChildren(new Option(this._v78Text('choose'),''));
  const fragment=document.createDocumentFragment();let selected='';
  rows.forEach((row,index)=>{fragment.append(new Option(this._v223Name(row),String(index)));if(this._houseKey(row)===state.selected)selected=String(index);});
  select.append(fragment);select.value=selected;if(selected==='')state.selected='';
  select.disabled=this._ingredientCatalogLoading||!rows.length;
  const failed=this._v63CatalogFailure===`${this._entryId}:${this._uiIngredientLanguage()}`;
  c.querySelector('[data-v84-status]').textContent=this._ingredientCatalogLoading?this._t('catalogLoading'):failed&&!rows.length?this._v84Text('failed'):rows.length?`${rows.length} ${this._v84Text('catalog').toLocaleLowerCase()}`:this._v84Text('empty');
  c.querySelector('[data-v84-retry]').hidden=!failed;this._v105CatalogActions(c);
  this._v223Control(c,c.querySelector('.v105-catalog-controls'),()=>this._v84CatalogRows(c));
 }
 _v114Picker(){
  const result=super._v114Picker(),holder=this._v78Dialog?.querySelector('[data-v114-links]');
  this._v223Control(holder,holder?.querySelector('.v114-link-list'),()=>this._v78IngredientOptions());
  return result;
 }
 _v223FilterChoices(overlay){
  const list=overlay?.querySelector('[data-ingredient-choices]');if(!list)return;
  const rows=this._todayIngredientRows(),ids=new Map(rows.map(row=>[this._todayIngredientIdentity(row),row]));
  const enabled=overlay.querySelector('[data-v223-toggle]')?.checked===true;
  const allowed=new Set(this._v223SeasonRows(rows,new Set(),row=>this._todayIngredientIdentity(row),enabled).map(row=>this._todayIngredientIdentity(row)));
  const query=overlay.querySelector('[data-ingredient-search]')?.value||'';
  for(const label of list.querySelectorAll('label')){
   const input=label.querySelector('input[data-list]');if(!input)continue;
   const row=ids.get(input.value);if(!row)continue;
   label.hidden=!input.checked&&(!allowed.has(input.value)||!this._ingredientQueryMatches(row,query));
   label.style.display=label.hidden?'none':'';
   let name=label.querySelector('[data-v223-name]');
   if(!name){
    // Retain the actual checkbox and its inherited handlers.
    for(const node of [...label.childNodes])if(node!==input)node.remove();
    name=document.createElement('span');name.dataset.v223Name='';label.append(name);
   }
   name.textContent=this._v223Name(row);
  }
 }
 _showFilter(key){
  const result=super._showFilter(key);if(key!=='ingredients')return result;
  const overlay=this.shadowRoot.querySelector('[data-filter-dialog="ingredients"]'),list=overlay?.querySelector('[data-ingredient-choices]');
  if(!list)return result;
  const refresh=()=>this._v223FilterChoices(overlay);
  this._v223Control(list.parentElement,overlay.querySelector('[data-ingredient-search]'),refresh,{draft:true});
  overlay.addEventListener('input',refresh);overlay.addEventListener('change',refresh);refresh();
  return result;
 }
 _v124SetGroup(inputs,checked){
  if(!inputs.length||inputs.some(input=>input.dataset.list!=='ingredients'))return super._v124SetGroup(inputs,checked);
  // Take the visible set before selected-first reordering. Dispatch once so a
  // full catalog does not trigger thousands of complete list refreshes.
  const targets=checked?inputs.filter(input=>!input.closest('label')?.hidden&&input.closest('label')?.style.display!=='none'):inputs;
  let changed;
  for(const input of targets)if(input.checked!==checked){input.checked=checked;changed=input;}
  changed?.dispatchEvent(new Event('change',{bubbles:true}));
 }
 async _v140LoadSupermarketCatalog(...args){
  const result=await super._v140LoadSupermarketCatalog(...args);
  if(this._v78Dialog?.isConnected)this._v78IngredientOptions();
  const overlay=this.shadowRoot?.querySelector('[data-filter-dialog="ingredients"]');
  if(overlay){
   const list=overlay.querySelector('[data-ingredient-choices]');
   this._v223Control(list?.parentElement,overlay.querySelector('[data-ingredient-search]'),()=>this._v223FilterChoices(overlay),{draft:true});
   this._v223FilterChoices(overlay);
  }
  return result;
 }
};
