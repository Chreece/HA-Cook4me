import "./cook4me-panel-v93.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v93');
const TEXT={
 en:{source:'Source recipe',allowance:'Salt and pepper: source allowance',estimate:'Estimated quantity',quantityMissing:'Recipe quantity missing',priceMissing:'No compatible price',pantry:'In your pantry'},
 de:{source:'Originalrezept',allowance:'Salz und Pfeffer: Richtmenge aus dem Rezept',estimate:'Geschätzte Menge',quantityMissing:'Rezeptmenge fehlt',priceMissing:'Kein passender Preis',pantry:'Im Vorrat'},
 el:{source:'Αρχική συνταγή',allowance:'Αλάτι και πιπέρι: ποσότητα αναφοράς',estimate:'Εκτιμώμενη ποσότητα',quantityMissing:'Λείπει ποσότητα στη συνταγή',priceMissing:'Δεν υπάρχει συμβατή τιμή',pantry:'Στο ντουλάπι'},
};
function sourceUrl(value){try{const url=new URL(value);return url.protocol==='https:'&&!url.username&&!url.password&&!url.port&&['www.tefal.pl','www.alnatura.de','fdc.nal.usda.gov','www.fao.org','www.nist.gov','www.clubhouseforchefs.ca'].includes(url.hostname)?url:null;}catch{return null;}}
class Cook4MeRecipeHubPanelV94 extends BasePanel{
 _v94Text(key){return TEXT[this._uiIngredientLanguage()]?.[key]||TEXT.en[key]||key;}
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.16.18');return result;}
 _v94Amount(quantity,unit){
  const language=this._uiIngredientLanguage(),units={en:{piece:'piece',pcs:'pcs'},de:{piece:'Stück',pcs:'Stück'},el:{piece:'τεμ.',pcs:'τεμ.',tsp:'κ.γ.',tbsp:'κ.σ.'}};
  return `${new Intl.NumberFormat(language,{maximumFractionDigits:2}).format(quantity)} ${units[language]?.[unit]||unit||''}`.trim();
 }
 _v94QuantityText(estimate){
  if(estimate.kind==='source_recipe_quantity')return `${this._v94Text('allowance')}: ${this._v94Amount(estimate.quantity,estimate.unit)}`;
  const before=estimate.sourceQuantity==null?'':`${this._v94Amount(estimate.sourceQuantity,estimate.sourceUnit)} ≈ `;
  return `${this._v94Text('estimate')}: ${before}${this._v94Amount(estimate.quantity,estimate.unit)}`;
 }
 _v79PaintItem(node,state){
  super._v79PaintItem(node,state);const row=state.cost?.ingredients?.[Number(node.dataset.v79Item)];if(!row)return;
  const estimate=row.quantityEstimate||row.fallbackEstimate?.quantityEstimate;
  if(estimate){
   if(!row.fallbackEstimate&&!node.textContent.startsWith('≈'))node.prepend('≈ ');
   const detail=document.createElement('small');detail.dataset.v94Quantity='';detail.style.cssText='display:block;line-height:1.4;margin-top:3px';detail.textContent=this._v94QuantityText(estimate);detail.title=estimate.label||'';node.append(detail);
  }else if(row.coverage<1&&!row.fallbackEstimate){
   node.textContent=`${this._v79Money(row.costsByCurrency)} · ${this._v94Text(row.priceStatus==='recipe_amount_unknown'?'quantityMissing':'priceMissing')}`;
  }
 }
 _v79CostHtml(recipe,state){
  const node=this._v67Dom(super._v79CostHtml(recipe,state));
  node.querySelectorAll('.v79-evidence>div').forEach((element,index)=>{
   const row=state.cost?.ingredients?.[index],estimate=row?.quantityEstimate||row?.fallbackEstimate?.quantityEstimate;if(!estimate)return;
   let detail=element.querySelector('[data-v86-quantity-estimate]');
   if(!detail&&row.fallbackEstimate)detail=[...element.querySelectorAll(':scope > small')].find(small=>small.textContent.includes(estimate.label));
   if(!detail){detail=document.createElement('small');element.append(detail);}
   detail.dataset.v94Quantity='';detail.textContent=this._v94QuantityText(estimate);detail.title=estimate.label||'';
   for(const evidence of [estimate,estimate.recipeSource]){
    const url=sourceUrl(evidence?.sourceUrl);if(!url)continue;
    const link=document.createElement('a');link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';link.textContent=` · ${evidence.kind==='source_recipe_quantity'?this._v94Text('source'):url.hostname} ↗`;detail.append(link);
   }
  });return node.innerHTML;
 }
 _v66Body(...args){
  const node=this._v67Dom(super._v66Body(...args));
  node.querySelectorAll('[data-v66-ingredient] > .chip').forEach(chip=>{
   const label=`${this._v94Text('pantry')}: ${chip.textContent}`;chip.title=label;chip.setAttribute('aria-label',label);
   const icon=document.createElement('ha-icon');icon.setAttribute('icon','mdi:home-outline');icon.setAttribute('aria-hidden','true');icon.style.cssText='--mdc-icon-size:16px;margin-right:4px';chip.prepend(icon);
  });return node.innerHTML;
 }
}
customElements.define('cook4me-recipe-hub-panel-v94',Cook4MeRecipeHubPanelV94);
