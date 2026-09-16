import "./cook4me-panel-v90.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v90');
const TEXT={
 en:{budget:'Estimated total',partial:'Estimated subtotal',rough:'rough estimates',covered:'ingredients covered',known:'Known cost',fallback:'Rough budget estimate',group:'Similar food group',basket:'Broad food basket',spread:'Comparison range',explain:'These are budgeting assumptions, not observed prices for the missing ingredients. The range shows the source products’ spread; the actual ingredient price may fall outside it.',sources:'Comparison prices',missing:'Still missing quantities or usable prices'},
 de:{budget:'Geschätzte Gesamtkosten',partial:'Geschätzte Zwischensumme',rough:'grobe Schätzungen',covered:'Zutaten berücksichtigt',known:'Bekannte Kosten',fallback:'Grobe Kostenschätzung',group:'Ähnliche Lebensmittelgruppe',basket:'Breiter Lebensmittelvergleich',spread:'Vergleichsspanne',explain:'Dies sind Planungsannahmen, keine beobachteten Preise der fehlenden Zutaten. Die Spanne zeigt die Vergleichspreise; der tatsächliche Zutatenpreis kann außerhalb liegen.',sources:'Vergleichspreise',missing:'Mengen oder nutzbare Preise fehlen noch'},
 el:{budget:'Εκτιμώμενο σύνολο',partial:'Εκτιμώμενο μερικό σύνολο',rough:'πρόχειρες εκτιμήσεις',covered:'υλικά καλύπτονται',known:'Γνωστό κόστος',fallback:'Πρόχειρη εκτίμηση κόστους',group:'Παρόμοια ομάδα τροφίμων',basket:'Γενικό δείγμα τροφίμων',spread:'Εύρος σύγκρισης',explain:'Πρόκειται για παραδοχές προϋπολογισμού, όχι καταγεγραμμένες τιμές των υλικών που λείπουν. Το εύρος δείχνει τις τιμές σύγκρισης· η πραγματική τιμή μπορεί να βρίσκεται εκτός αυτού.',sources:'Τιμές σύγκρισης',missing:'Εκκρεμούν ποσότητες ή διαθέσιμες τιμές'}
};
class Cook4MeRecipeHubPanelV91 extends BasePanel{
 _v91Text(key){return TEXT[this._uiIngredientLanguage()]?.[key]||TEXT.en[key]||key;}
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.16.15');return result;}
 _v91Range(cost){return Object.entries(cost.budgetRangeByCurrency||{}).map(([currency,r])=>`${this._v79Money({[currency]:r.low})}–${this._v79Money({[currency]:r.high})}`).join(' + ');}
 _v82PaintCard(recipe){
  super._v82PaintCard(recipe);const state=this._v79CostState(recipe),cost=state.cost;if(!cost?.fallbackIngredientCount||state.loading)return;
  const label=`${this._v91Text(cost.budgetComplete?'budget':'partial')} ≈ ${this._v79Money(cost.budgetTotalsByCurrency)} · ${cost.budgetIngredientCount}/${cost.ingredients.length} ${this._v91Text('covered')} · ${cost.fallbackIngredientCount} ${this._v91Text('rough')}`;
  for(const card of this._v90Cards(recipe)){const badge=card.querySelector('[data-v82-card-cost]');if(!badge)continue;badge.textContent=label;badge.title=`${this._v91Text('known')}: ${this._v79Money(cost.totalsByCurrency)}. ${this._v91Text('spread')}: ${this._v91Range(cost)}. ${this._v91Text('explain')}`;badge.setAttribute('aria-label',label+'. '+badge.title);}
 }
 _v79PaintItem(node,state){
  super._v79PaintItem(node,state);const row=state.cost?.ingredients?.[Number(node.dataset.v79Item)],fallback=row?.fallbackEstimate;
  if(fallback){const amounts={...row.costsByCurrency};amounts[fallback.currency]=(amounts[fallback.currency]||0)+fallback.amount;node.textContent=`≈ ${this._v79Money(amounts)} · ${this._v91Text('fallback')}`;}
 }
 _v79CostHtml(recipe,state){
  const html=super._v79CostHtml(recipe,state),cost=state.cost;if(!cost?.fallbackIngredientCount)return html;
  const node=this._v67Dom(html),e=value=>this._escape(String(value??'')),t=key=>e(this._v91Text(key));
  const head=node.querySelector('.v79-price-head');if(head){
   head.innerHTML=`<div><span>${t(cost.budgetComplete?'budget':'partial')}</span><strong>≈ ${e(this._v79Money(cost.budgetTotalsByCurrency))}</strong></div><div><strong>${e(this._v79Money(cost.budgetPerServingByCurrency))}</strong><span>${e(this._v79Text('perServing'))}</span></div>`;
   head.insertAdjacentHTML('afterend',`<p data-v91-budget>${t('known')}: ${e(this._v79Money(cost.totalsByCurrency))} · ${cost.fallbackIngredientCount} ${t('rough')}<br>${t('spread')}: ${e(this._v91Range(cost))}<br>${t('explain')}</p>`);
  }
  // The original known-price count remains visible. Only genuinely unresolved
  // rows belong in the still-missing explanation once the budget is shown.
  const missing=cost.ingredients.filter(row=>row.coverage<1&&!row.fallbackEstimate),note=node.querySelector('[data-v86-missing]');
  if(note){if(!missing.length)note.remove();else note.textContent=`${this._v91Text('missing')}: ${missing.map(row=>row.name).join('; ')}`;}
  node.querySelectorAll('.v79-evidence>div').forEach((element,index)=>{
   const row=cost.ingredients[index],estimate=row?.fallbackEstimate;if(!estimate)return;
   const amounts={...row.costsByCurrency};amounts[estimate.currency]=(amounts[estimate.currency]||0)+estimate.amount;
   const amount=element.querySelector('span');if(amount)amount.textContent=`≈ ${this._v79Money(amounts)} · ${this._v91Text('fallback')}`;
   element.querySelector('.v82-price-reasons')?.remove();
   const detail=document.createElement('p');detail.dataset.v91Fallback='';
   detail.textContent=`${this._v91Text(estimate.level==='food_group'?'group':'basket')}: ${estimate.groupLabel} · ${estimate.sampleCount} ${this._v91Text('sources')} · ${estimate.quantity.toFixed(2)} ${estimate.unit}. ${this._v91Text('spread')}: ${this._v79Money({[estimate.currency]:estimate.low})}–${this._v79Money({[estimate.currency]:estimate.high})}.`;
   element.append(detail);
   if(estimate.quantityEstimate){const q=document.createElement('small');q.textContent=`${this._v86Text('estimatedAmount')}: ${estimate.quantityEstimate.label}`;element.append(q);}
   const sources=document.createElement('details'),summary=document.createElement('summary');summary.textContent=`${this._v91Text('sources')} (${estimate.sources?.length||0}/${estimate.sampleCount})`;sources.append(summary);
   for(const source of estimate.sources||[]){const line=document.createElement('div');line.textContent=`${source.name} · ${source.date} · ${this._v79Money({[estimate.currency]:source.rate*(source.unit==='pcs'?1:1000)})} / ${source.unit==='pcs'?'pcs':source.unit==='g'?'kg':'l'}`;
    try{const url=new URL(source.sourceUrl);if(url.protocol==='https:'&&!url.username&&!url.password&&!url.port&&['prices.openfoodfacts.org','www.dm.de','www.aldi-sued.de','www.knuspr.de','ludwigs.shop','www.gourmet-versand.com','www.dallmayr-versand.de','www.africshopping.com'].includes(url.hostname)){const a=document.createElement('a');a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';a.textContent=' ↗';line.append(a);}}catch{}
    sources.append(line);
   }element.append(sources);
  });
  return node.innerHTML;
 }
}
customElements.define('cook4me-recipe-hub-panel-v91',Cook4MeRecipeHubPanelV91);
