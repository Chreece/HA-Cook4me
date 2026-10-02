const TEXT={
 en:{seasonal:'Seasonal ingredients',combined:n=>`Seasonal ingredients + ${n} selected`},
 de:{seasonal:'Saisonale Zutaten',combined:n=>`Saisonale Zutaten + ${n} ausgewählt`},
 el:{seasonal:'Υλικά εποχής',combined:n=>`Υλικά εποχής + ${n} επιλεγμένα`},
};
const lang=value=>String(value||'en').toLowerCase().replace('_','-').split('-',1)[0];

export const SeasonalFilterBadgeMixin=Base=>class extends Base{
 _v266SeasonalLabel(count=0){
  const code=lang(this._uiIngredientLanguage?.()||this._langCode?.()||'en');
  const row=TEXT[code]||TEXT.en;
  return count>0?row.combined(count):row.seasonal;
 }
 _v263SeasonalIndicator(container){
  // v263 rendered seasonal as a second standalone leaf control. v266 makes
  // seasonal a state of the real Ingredients button instead, so there is only
  // one control to understand and no misleading extra active-filter button.
  container?.querySelector?.(':scope > [data-v263-active-filters]')?.remove();
 }
 _v266DecorateSeasonalIngredientButton(root=this.shadowRoot){
  const button=root?.querySelector?.('.rx-shared-filters [data-filter="ingredients"],.v100-filter-slot [data-filter="ingredients"]');
  if(!button)return;
  const filters=this._filters?.()||{};
  const seasonal=filters.seasonalIngredients===true;
  const manualCount=new Set(Array.isArray(filters.ingredients)?filters.ingredients:[]).size;

  button.querySelectorAll(':scope > .v266-seasonal-marker').forEach(node=>node.remove());
  button.toggleAttribute('data-v266-seasonal',seasonal);

  if(!seasonal)return;

  const marker=document.createElement('span');
  marker.className='v266-seasonal-marker';
  marker.setAttribute('aria-hidden','true');
  const icon=document.createElement('ha-icon');
  icon.setAttribute('icon','mdi:leaf');
  icon.setAttribute('aria-hidden','true');
  marker.append(icon);
  button.append(marker);

  const label=this._v266SeasonalLabel(manualCount);
  button.title=label;
  button.setAttribute('aria-label',label);
  this._v266Styles();
 }
 _mountFilters(container,...args){
  const result=super._mountFilters(container,...args);
  this._v266DecorateSeasonalIngredientButton(container);
  return result;
 }
 _v83MergeToolbar(container,...args){
  const result=super._v83MergeToolbar(container,...args);
  this._v266DecorateSeasonalIngredientButton(container);
  return result;
 }
 _v100Layout(...args){
  const result=super._v100Layout(...args);
  this._v266DecorateSeasonalIngredientButton(this.shadowRoot);
  return result;
 }
 _renderTab(...args){
  const result=super._renderTab(...args);
  this._v266DecorateSeasonalIngredientButton(this.shadowRoot);
  return result;
 }
 _v266Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v266SeasonalFilterBadgeStyles'))return;
  const style=document.createElement('style');
  style.id='v266SeasonalFilterBadgeStyles';
  style.textContent=`
   .rx-shared-filters [data-filter="ingredients"][data-v266-seasonal],
   .v100-filter-slot [data-filter="ingredients"][data-v266-seasonal]{
    position:relative!important;
    border-color:color-mix(in srgb,var(--primary-color) 72%,var(--divider-color))!important;
    box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--primary-color) 24%,transparent);
   }
   .rx-shared-filters [data-filter="ingredients"]>.v266-seasonal-marker,
   .v100-filter-slot [data-filter="ingredients"]>.v266-seasonal-marker{
    position:absolute;
    right:-5px;
    bottom:-5px;
    z-index:3;
    width:18px;
    height:18px;
    display:grid;
    place-items:center;
    box-sizing:border-box;
    border-radius:999px;
    border:2px solid var(--card-background-color);
    background:var(--primary-color);
    color:var(--text-primary-color,#fff);
    pointer-events:none;
    box-shadow:0 1px 4px #0005;
   }
   .rx-shared-filters [data-filter="ingredients"]>.v266-seasonal-marker ha-icon,
   .v100-filter-slot [data-filter="ingredients"]>.v266-seasonal-marker ha-icon{
    --mdc-icon-size:11px!important;
    position:absolute!important;
    left:50%!important;
    top:50%!important;
    width:11px!important;
    height:11px!important;
    margin:0!important;
    padding:0!important;
    line-height:0!important;
    display:block!important;
    color:currentColor!important;
    transform:translate(calc(-50% - .5px),calc(-50% - .75px))!important;
    transform-origin:center!important;
   }
  `;
  this.shadowRoot.append(style);
 }
};
