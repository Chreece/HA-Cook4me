import "./cook4me-panel-v86.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v86');
const TEXT={
 en:{total:'Total',priced:'ingredients priced',subtotal:'Subtotal',estimate:'Estimate',missing:'Still missing'},
 de:{total:'Gesamt',priced:'Zutaten bepreist',subtotal:'Zwischensumme',estimate:'Schätzung',missing:'Noch fehlend'},
 el:{total:'Σύνολο',priced:'υλικά με κόστος',subtotal:'Μερικό σύνολο',estimate:'Εκτίμηση',missing:'Εκκρεμούν'}
};
function evidenceUrl(value){
 try{const url=new URL(value);return url.protocol==='https:'&&!url.username&&!url.password&&!url.port&&['www.dm.de','www.aldi-sued.de','www.knuspr.de','asia4friends.de','www.piccantino.de','www.greenist.de','www.der-ludwig.de','www.send-a-fish.de','www.naturata-shop.de','shop.vanillekiste.de','fuchsgruppe.shop','www.davert.de','asianbrand.de','frische-kontor.de','www.bwb.de','www.fao.org','fdc.nal.usda.gov','www.nist.gov'].includes(url.hostname)?url:null;}catch{return null;}
}
class Cook4MeRecipeHubPanelV87 extends BasePanel{
 _v87Text(key){return TEXT[this._uiIngredientLanguage()]?.[key]||TEXT.en[key]||key;}
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.16.11');return result;}
 _v79Reference(ref){
  if(!['retail_snapshot','utility_snapshot'].includes(ref?.source))return super._v79Reference(ref);
  const e=value=>this._escape(String(value??'')),url=evidenceUrl(ref.sourceUrl);
  return `<small data-v87-reference>${e(ref.productName)} · ${e(ref.location)} · ${e(ref.date)} · ${e(this._v79Money({[ref.currency]:ref.amount}))} / ${e(this._displayAmount(ref.basisQuantity,ref.basisUnit))}${url?` · <a href="${e(url.href)}" target="_blank" rel="noopener noreferrer">${e(url.hostname)} ↗</a>`:''}${ref.note?`<br>${e(ref.note)}`:''}</small>`;
 }
 _v79CostHtml(recipe,state){
  const node=this._v67Dom(super._v79CostHtml(recipe,state));
  node.querySelectorAll('.v79-evidence>div').forEach((element,index)=>{
   const detail=element.querySelector('[data-v86-quantity-estimate]'),url=evidenceUrl(state.cost?.ingredients?.[index]?.quantityEstimate?.sourceUrl);
   if(!detail||!url||detail.querySelector('a'))return;
   const link=document.createElement('a');link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';link.textContent=' ↗';detail.append(link);
  });
  return node.innerHTML;
 }
 _v82PaintCard(recipe){
  super._v82PaintCard(recipe);const state=this._v79CostState(recipe),cost=state.cost;
  if(!cost||state.loading||!Array.isArray(cost.ingredients))return;
  const missing=cost.ingredients.filter(row=>row.coverage<1),count=cost.ingredients.length-missing.length,total=cost.ingredients.length;
  const coverage=`${count}/${total} ${this._v87Text('priced')}`;
  const label=Object.keys(cost.totalsByCurrency||{}).length?`${this._v87Text(cost.complete?(cost.estimated?'estimate':'total'):'subtotal')} ${this._v79Money(cost.totalsByCurrency)} · ${coverage}`:`${this._v86Text('unknown')} · ${coverage}`;
  const details=missing.map(row=>`${row.name} (${this._v86Text(row.priceStatus==='recipe_amount_unknown'?'quantityMissing':'priceMissing')})`).join('; ');
  this.shadowRoot?.querySelectorAll('[data-v66-ref]').forEach(card=>{
   if(card._v82Recipe!==recipe)return;const badge=card.querySelector('[data-v82-card-cost]');if(!badge)return;
   badge.textContent=label;badge.title=details?`${this._v87Text('missing')}: ${details}`:coverage;
   badge.setAttribute('aria-label',`${label}${details?'. '+badge.title:''}`);
  });
 }
}
customElements.define('cook4me-recipe-hub-panel-v87',Cook4MeRecipeHubPanelV87);
