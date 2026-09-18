import "./cook4me-panel-v103.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v103');
const SYMBOL={personal:'✓',reference:'≈',assumed:'≈',partial:'!',unavailable:'—'};
class Cook4MeRecipeHubPanelV104 extends BasePanel{
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.17.8');this._v104Styles();return result;}
 _v104PriceRefreshIcon(){return 'mdi:cash-sync';}
 _buttonIcon(button){return button.hasAttribute('data-v79-recost')?null:super._buttonIcon(button);}
 _v82PaintCard(recipe){
  super._v82PaintCard(recipe);const state=this._v79CostState(recipe),cost=state.cost;
  for(const card of this._v90Cards(recipe)){
   const badge=card.querySelector('[data-v82-card-cost]');if(!badge)continue;
   const retry=badge.querySelector('[data-v90-retry]');
   if(retry){
    // Preserve the existing retry listener and accessible explanation.
    retry.title=this._v90Text('retry');retry.setAttribute('aria-label',retry.title);
    retry.innerHTML='<ha-icon icon="mdi:cash-sync" aria-hidden="true"></ha-icon>';
    for(const child of [...badge.childNodes])if(child!==retry)child.remove();
   }else if(state.loading){
    badge.innerHTML='<ha-icon icon="mdi:progress-clock" aria-hidden="true"></ha-icon>';
    badge.setAttribute('aria-label',this._v79Text('loading'));
   }else{
    const level=this._v99Confidence(cost);
    badge.textContent=level==='unavailable'?'—':`${SYMBOL[level]} ${this._v79Money(cost.budgetTotalsByCurrency||cost.totalsByCurrency)}`;
    badge.setAttribute('aria-label',`${badge.textContent}. ${badge.title||this._v99Text(level)}`);
   }
  }
 }
 _v79CostHtml(recipe,state){
  this._v104Styles();
  const node=this._v67Dom(super._v79CostHtml(recipe,state)),cost=state.cost;
  const e=value=>this._escape(String(value??'')),level=this._v99Confidence(cost);
  const total=cost&&(cost.budgetTotalsByCurrency||cost.totalsByCurrency);
  const perServing=cost&&(cost.budgetPerServingByCurrency||cost.perServingByCurrency);
  const amount=level==='unavailable'?'—':`${SYMBOL[level]} ${this._v79Money(total)}`;
  const totalLabel=`${this._v79Text(cost?.budgetComplete||cost?.complete?'total':'partial')}: ${amount}. ${this._v99Text(level)}`;
  const refresh=this._v82Text(state.loading?'refreshing':'refresh');
  const evidence=this._v79Text('source');
  // Evidence remains available on demand, without prose in the overview.
  node.querySelector('.v79-price-head')?.remove();
  node.querySelectorAll('[data-v79-recost]').forEach(button=>button.remove());
  return `<div class="v104-price-overview" aria-busy="${!!state.loading}">
   <div class="v79-price-head">
    <div class="v104-total">
     <strong data-v104-total data-v99-confidence="${level}" title="${e(totalLabel)}" aria-label="${e(totalLabel)}">${e(amount)}</strong>
     <button type="button" class="btn secondary v104-price-refresh" data-v79-recost title="${e(refresh)}" aria-label="${e(refresh)}" ${state.loading||!recipe.ingredients?.length?'disabled':''}><ha-icon icon="mdi:cash-sync" aria-hidden="true"></ha-icon></button>
    </div>
    ${perServing&&Object.keys(perServing).length?`<div class="v104-serving" title="${e(this._v79Text('perServing'))}" aria-label="${e(this._v79Text('perServing')+': '+this._v79Money(perServing))}"><ha-icon icon="mdi:account" aria-hidden="true"></ha-icon><strong>${e(this._v79Money(perServing))}</strong></div>`:''}
   </div>
   <details class="v104-price-info"><summary title="${e(evidence)}" aria-label="${e(evidence)}"><ha-icon icon="${state.error?'mdi:alert-circle-outline':'mdi:information-outline'}" aria-hidden="true"></ha-icon></summary><div class="v104-price-evidence">${node.innerHTML}</div></details>
  </div>`;
 }
 _renderRecipeDialog(){
  super._renderRecipeDialog();this._v104Styles();
  this._v63RecipeDialog?.querySelector('header [data-v82-refresh-prices]')?.remove();
 }
 _v104Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v104Styles'))return;
  const style=document.createElement('style');style.id='v104Styles';style.textContent=`
   [data-ingredient-dialog]{position:fixed!important;inset:0!important;z-index:10060!important}
   .v104-price-overview{position:relative;min-height:44px}
   .v104-price-overview .v79-price-head{align-items:center;gap:10px;padding-right:52px;min-height:44px}
   .v104-price-overview .v79-price-head>div{flex-direction:row;align-items:center;gap:8px;min-width:0}
   [data-v104-total]{padding:5px 9px;border-radius:9px;border:1px solid var(--v99-price-border);background:var(--v99-price-bg);color:var(--v99-price-fg);white-space:nowrap}
   .v104-price-overview .v104-serving{margin-left:auto;white-space:nowrap;color:var(--secondary-text-color)}
   .v104-price-overview .v104-serving strong{font-size:18px}
   .v104-price-refresh,.v104-price-info>summary{box-sizing:border-box;display:inline-flex!important;align-items:center;justify-content:center;width:44px;height:44px;min-width:44px;padding:8px!important;border:1px solid var(--divider-color);border-radius:12px;background:var(--card-background-color);color:var(--primary-text-color);cursor:pointer}
   .v104-price-info>summary{position:absolute;top:0;right:0;list-style:none}
   .v104-price-info>summary::-webkit-details-marker{display:none}
   .v104-price-info>summary:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}
   .v104-price-evidence{margin-top:12px;padding-top:12px;border-top:1px solid var(--divider-color)}
   .v104-price-overview[aria-busy="true"] .v104-price-refresh{opacity:.6}
   [data-v82-card-cost] ha-icon{--mdc-icon-size:18px;display:block}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v104',Cook4MeRecipeHubPanelV104);
