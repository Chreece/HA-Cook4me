import "./cook4me-panel-v98.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v98');
const TEXT={
 en:{personal:'Based on your saved prices',reference:'Estimate from price references',assumed:'Estimate with budgeting assumptions',partial:'Incomplete subtotal',unavailable:'Price unavailable',zero:'Unmeasured basic · assumed zero cost',explain:'No amount is given for these basics, so their budget allowance is zero. This is an optimistic assumption, not a confirmed free ingredient.',subtotal:'Subtotal',legend:'Price colours describe the evidence, not how expensive the recipe is.'},
 de:{personal:'Auf Basis deiner gespeicherten Preise',reference:'Schätzung aus Preisreferenzen',assumed:'Schätzung mit Planungsannahmen',partial:'Unvollständige Zwischensumme',unavailable:'Preis nicht verfügbar',zero:'Grundzutat ohne Mengenangabe · Kosten mit null angesetzt',explain:'Für diese Grundzutaten fehlt die Mengenangabe; im Budget werden sie mit null angesetzt. Das ist eine optimistische Annahme, kein bestätigter Gratispreis.',subtotal:'Zwischensumme',legend:'Die Preisfarben beschreiben die Beleglage, nicht wie teuer das Rezept ist.'},
 el:{personal:'Με βάση τις αποθηκευμένες τιμές σου',reference:'Εκτίμηση από τιμές αναφοράς',assumed:'Εκτίμηση με παραδοχές προϋπολογισμού',partial:'Ελλιπές μερικό σύνολο',unavailable:'Η τιμή δεν είναι διαθέσιμη',zero:'Βασικό υλικό χωρίς ποσότητα · θεωρούμενο μηδενικό κόστος',explain:'Δεν δίνεται ποσότητα για αυτά τα βασικά υλικά, οπότε στον προϋπολογισμό υπολογίζονται με μηδενικό κόστος. Πρόκειται για αισιόδοξη παραδοχή, όχι για επιβεβαιωμένα δωρεάν υλικά.',subtotal:'Μερικό σύνολο',legend:'Τα χρώματα δείχνουν την τεκμηρίωση της τιμής, όχι πόσο ακριβή είναι η συνταγή.'}
};
const ICON={personal:'✓',reference:'≈',assumed:'≈',partial:'!',unavailable:'—'};
class Cook4MeRecipeHubPanelV99 extends BasePanel{
 _v99Text(key){return TEXT[this._uiIngredientLanguage()]?.[key]||TEXT.en[key]||key;}
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.17.3');this._v99Styles();return result;}
 _v99Confidence(cost){
  if(!cost)return 'unavailable';
  if(cost.priceConfidence in ICON)return cost.priceConfidence;
  const totals=cost.budgetTotalsByCurrency||cost.totalsByCurrency||{};
  if(!Object.keys(totals).length)return 'unavailable';
  if(!(cost.budgetComplete||cost.complete))return 'partial';
  if(cost.zeroCostIngredientCount||cost.fallbackIngredientCount)return 'assumed';
  return cost.ingredients?.length&&cost.ingredients.every(row=>!row.quantityEstimate&&row.sourceKinds?.length&&row.sourceKinds.every(kind=>['exact_purchase','manual_reference'].includes(kind)))?'personal':'reference';
 }
 _v82PaintCard(recipe){
  super._v82PaintCard(recipe);this._v99Styles();const state=this._v79CostState(recipe),cost=state.cost;
  for(const card of this._v90Cards(recipe)){
   const badge=card.querySelector('[data-v82-card-cost]');if(!badge)continue;
   const level=state.loading?'unavailable':this._v99Confidence(cost);badge.dataset.v99Confidence=level;
   if(!cost||state.loading)continue; // Preserve the existing loading and retry controls.
   const money=this._v79Money(cost.budgetTotalsByCurrency||cost.totalsByCurrency);
   badge.textContent=level==='unavailable'?this._v99Text(level):`${ICON[level]} ${level==='partial'?this._v99Text('subtotal')+' ':''}${money}`;
   const missing=cost.ingredients.filter(row=>row.coverage<1&&row.budgetCoverage!==1);
   badge.title=`${this._v99Text(level)}${cost.zeroCostIngredientCount?'. '+this._v99Text('explain'):''}${missing.length?'. '+this._v91Text('missing')+': '+missing.map(row=>row.name).join('; '):''}`;
   badge.setAttribute('aria-label',`${badge.textContent}. ${badge.title}`);
  }
 }
 _v79PaintItem(node,state){
  super._v79PaintItem(node,state);const row=state.cost?.ingredients?.[Number(node.dataset.v79Item)];
  delete node.dataset.v99Zero;
  if(row?.zeroCostAllowance){node.textContent=`${this._v79Money({[row.zeroCostAllowance.currency]:0})} · ${this._v99Text('zero')}`;node.dataset.v99Zero='';}
 }
 _v79CostHtml(recipe,state){
  const node=this._v67Dom(super._v79CostHtml(recipe,state)),cost=state.cost;if(!cost)return node.innerHTML;
  this._v99Styles();const e=value=>this._escape(String(value??'')),level=this._v99Confidence(cost),head=node.querySelector('.v79-price-head');
  if(head){
   if(cost.zeroCostIngredientCount&&!cost.fallbackIngredientCount)head.innerHTML=`<div><span>${e(this._v91Text(cost.budgetComplete?'budget':'partial'))}</span><strong>≈ ${e(this._v79Money(cost.budgetTotalsByCurrency))}</strong></div><div><strong>${e(this._v79Money(cost.budgetPerServingByCurrency))}</strong><span>${e(this._v79Text('perServing'))}</span></div>`;
   head.insertAdjacentHTML('afterend',`<p data-v99-confidence="${level}" class="v99-price-evidence">${ICON[level]} ${e(this._v99Text(level))}</p><details class="v99-price-legend"><summary>${e(this._v99Text('legend'))}</summary>${Object.keys(ICON).map(key=>`<p data-v99-confidence="${key}" class="v99-price-evidence">${ICON[key]} ${e(this._v99Text(key))}</p>`).join('')}</details>`);
   if(cost.zeroCostIngredientCount)head.insertAdjacentHTML('afterend',`<p data-v99-zero-note>${e(this._v99Text('explain'))}<br>${e(cost.ingredients.filter(row=>row.zeroCostAllowance).map(row=>row.name).join('; '))}</p>`);
  }
  const missing=cost.ingredients.filter(row=>row.coverage<1&&row.budgetCoverage!==1),note=node.querySelector('[data-v86-missing]');
  if(note){if(!missing.length)note.remove();else note.textContent=`${this._v91Text('missing')}: ${missing.map(row=>row.name).join('; ')}`;}
  node.querySelectorAll('.v79-evidence>div').forEach((element,index)=>{
   const row=cost.ingredients[index];if(!row?.zeroCostAllowance)return;
   const amount=element.querySelector('span');if(amount)amount.textContent=`${this._v79Money({[row.zeroCostAllowance.currency]:0})} · ${this._v99Text('zero')}`;
   element.querySelector('.v82-price-reasons')?.remove();element.dataset.v99Zero='';
  });return node.innerHTML;
 }
 _v99Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v99Styles'))return;
  const style=document.createElement('style');style.id='v99Styles';style.textContent=`
   [data-v99-confidence="personal"]{--v99-price-bg:#dcfce7;--v99-price-fg:#14532d;--v99-price-border:#15803d}
   [data-v99-confidence="reference"]{--v99-price-bg:#dbeafe;--v99-price-fg:#1e3a8a;--v99-price-border:#2563eb}
   [data-v99-confidence="assumed"]{--v99-price-bg:#fef3c7;--v99-price-fg:#78350f;--v99-price-border:#b45309}
   [data-v99-confidence="partial"]{--v99-price-bg:#fee2e2;--v99-price-fg:#7f1d1d;--v99-price-border:#dc2626}
   [data-v99-confidence="unavailable"]{--v99-price-bg:#f1f5f9;--v99-price-fg:#334155;--v99-price-border:#64748b}
   .v82-card-cost[data-v99-confidence]{top:10px!important;left:10px!important;right:auto!important;position:absolute;max-width:calc(100% - 20px);box-sizing:border-box;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding:5px 9px;border-radius:9px;font-size:12px;line-height:18px;font-weight:650;z-index:3;background:var(--v99-price-bg);color:var(--v99-price-fg);border:1px solid var(--v99-price-border);box-shadow:0 1px 5px #0003}
   .rx-v69-media:has([data-v82-card-cost]) [data-v76-diet-badge]{top:48px!important}
   .v99-price-evidence{display:table;padding:5px 9px;border-radius:7px;background:var(--v99-price-bg);color:var(--v99-price-fg);border:1px solid var(--v99-price-border);font-size:13px;line-height:1.5}.v99-price-legend{margin:10px 0}.v99-price-legend summary{cursor:pointer;font-size:13px}[data-v99-zero-note]{font-size:13px;line-height:1.5}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v99',Cook4MeRecipeHubPanelV99);
