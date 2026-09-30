const TEXT={
 en:{seasonal:'Seasonal ingredients',active:'Active recipe filters'},
 de:{seasonal:'Saisonale Zutaten',active:'Aktive Rezeptfilter'},
 el:{seasonal:'Υλικά εποχής',active:'Ενεργά φίλτρα συνταγών'},
};

const lang=value=>String(value||'en').toLowerCase().replace('_','-').split('-',1)[0];

export function seasonalFilterEnabled(filters){
 return filters?.seasonalIngredients===true;
}

export function seasonalFilterLabel(language='en'){
 const code=lang(language);
 return (TEXT[code]||TEXT.en).seasonal;
}

export const SeasonalFilterStateMixin=Base=>class extends Base{
 _v263SeasonalEnabled(){
  return seasonalFilterEnabled(this._filters?.());
 }

 _v263SeasonalText(key){
  const code=lang(this._uiIngredientLanguage?.()||this._langCode?.()||'en');
  return (TEXT[code]||TEXT.en)[key]||TEXT.en[key]||key;
 }

 _filterActive(key){
  if(key==='ingredients'&&this._v263SeasonalEnabled())return true;
  return super._filterActive(key);
 }

 _v263Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v263SeasonalFilterStyles'))return;
  const style=document.createElement('style');
  style.id='v263SeasonalFilterStyles';
  style.textContent=`
   [data-v263-active-filters]{
    display:flex;
    flex-wrap:wrap;
    gap:7px;
    margin:-6px 0 14px;
    min-width:0;
   }
   [data-v263-active-filter]{
    display:inline-flex;
    align-items:center;
    gap:6px;
    min-height:30px;
    max-width:100%;
    padding:4px 9px;
    border:1px solid color-mix(in srgb,var(--primary-color) 55%,var(--divider-color));
    border-radius:999px;
    background:color-mix(in srgb,var(--primary-color) 12%,var(--card-background-color));
    color:var(--primary-text-color);
    font:inherit;
    font-size:12px;
    font-weight:650;
    cursor:pointer;
   }
   [data-v263-active-filter] ha-icon{
    --mdc-icon-size:16px;
    color:var(--primary-color);
    flex:0 0 auto;
   }
   [data-v263-active-filter] span{
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
   }
  `;
  this.shadowRoot.append(style);
 }

 _v263SeasonalIndicator(container){
  if(!container)return;
  container.querySelector(':scope > [data-v263-active-filters]')?.remove();
  if(!this._v263SeasonalEnabled())return;

  const bar=container.querySelector(':scope > .rx-shared-filters');
  if(!bar)return;
  this._v263Styles();

  const summary=document.createElement('div');
  summary.dataset.v263ActiveFilters='';
  summary.setAttribute('role','group');
  summary.setAttribute('aria-label',this._v263SeasonalText('active'));

  const chip=document.createElement('button');
  chip.type='button';
  chip.dataset.v263ActiveFilter='seasonalIngredients';
  chip.className='chip';
  chip.title=this._v263SeasonalText('seasonal');
  chip.setAttribute('aria-label',this._v263SeasonalText('seasonal'));

  const icon=document.createElement('ha-icon');
  icon.setAttribute('icon','mdi:leaf');
  icon.setAttribute('aria-hidden','true');
  const label=document.createElement('span');
  label.textContent=this._v263SeasonalText('seasonal');
  chip.append(icon,label);
  chip.addEventListener('click',()=>this._showFilter('ingredients'));

  summary.append(chip);
  bar.insertAdjacentElement('afterend',summary);
 }

 _mountFilters(container){
  const result=super._mountFilters(container);
  this._v263SeasonalIndicator(container);
  return result;
 }
};
