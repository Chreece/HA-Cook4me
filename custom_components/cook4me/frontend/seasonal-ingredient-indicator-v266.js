import {seasonalFilterEnabled,seasonalFilterLabel} from './seasonal-filter-state-v263.js';

const TEXT={
 en:{selected:'selected'},
 de:{selected:'ausgewählt'},
 el:{selected:'επιλεγμένα'},
};
const lang=value=>String(value||'en').toLowerCase().replace('_','-').split('-',1)[0];

export function seasonalIngredientVisualState(filters){
 const manual=new Set(Array.isArray(filters?.ingredients)?filters.ingredients.filter(Boolean):[]);
 return {
  seasonal:seasonalFilterEnabled(filters),
  manualCount:manual.size,
 };
}

export function seasonalIngredientDescription(language,base,filters){
 const {seasonal,manualCount}=seasonalIngredientVisualState(filters);
 if(!seasonal)return '';
 const code=lang(language),seasonalLabel=seasonalFilterLabel(code);
 if(!manualCount)return seasonalLabel;
 return `${seasonalLabel} + ${manualCount} ${(TEXT[code]||TEXT.en).selected}`;
}

export const SeasonalIngredientIndicatorMixin=Base=>class extends Base{
 _v266Language(){return this._uiIngredientLanguage?.()||this._langCode?.()||'en';}

 _v266DecorateIngredientFilter(container){
  const button=container?.querySelector?.('[data-filter="ingredients"]');
  if(!button)return;

  const filters=this._filters?.()||{};
  const {seasonal,manualCount}=seasonalIngredientVisualState(filters);
  const mainIcon=button.querySelector(':scope > ha-icon');
  if(mainIcon)mainIcon.setAttribute('icon',manualCount?'mdi:food-apple':'mdi:food-apple-outline');

  button.querySelectorAll(':scope > [data-v266-seasonal-badge]').forEach(node=>node.remove());
  button.toggleAttribute('data-v266-seasonal',seasonal);
  button.toggleAttribute('data-v266-manual',manualCount>0);

  if(seasonal){
   const badge=document.createElement('span');
   badge.dataset.v266SeasonalBadge='';
   badge.setAttribute('aria-hidden','true');
   const leaf=document.createElement('ha-icon');
   leaf.setAttribute('icon','mdi:leaf');
   leaf.setAttribute('aria-hidden','true');
   badge.append(leaf);
   button.append(badge);

   const description=seasonalIngredientDescription(this._v266Language(),button.dataset.v93Label||'',filters);
   if(description){
    button.title=description;
    button.setAttribute('aria-label',description);
   }
  }

  this._v266Styles();
 }

 _v83MergeToolbar(container){
  const result=super._v83MergeToolbar(container);
  this._v266DecorateIngredientFilter(container);
  return result;
 }

 _renderTab(...args){
  const result=super._renderTab(...args);
  this._v266DecorateIngredientFilter(this.shadowRoot);
  return result;
 }

 _v266Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v266SeasonalIngredientStyles'))return;
  const style=document.createElement('style');
  style.id='v266SeasonalIngredientStyles';
  style.textContent=`
   [data-filter="ingredients"][data-v266-seasonal]{
    position:relative!important;
    border-color:color-mix(in srgb,var(--primary-color) 70%,var(--divider-color))!important;
    background:color-mix(in srgb,var(--primary-color) 12%,var(--card-background-color))!important;
    color:var(--primary-color)!important;
   }
   [data-v266-seasonal-badge]{
    position:absolute;
    right:-6px;
    bottom:-6px;
    z-index:3;
    width:18px;
    height:18px;
    box-sizing:border-box;
    display:grid;
    place-items:center;
    border-radius:50%;
    border:2px solid var(--card-background-color);
    background:var(--primary-color);
    color:var(--text-primary-color,#fff);
    box-shadow:0 1px 4px #0005;
    pointer-events:none;
   }
   [data-v266-seasonal-badge] ha-icon{
    --mdc-icon-size:11px!important;
    color:currentColor!important;
   }
   [data-filter="ingredients"][data-v266-manual] > ha-icon{
    color:var(--primary-color)!important;
   }
  `;
  this.shadowRoot.append(style);
 }
};
