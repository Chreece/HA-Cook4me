import "./cook4me-panel-v84.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v84');
const TEXT={
 en:{quantityMissing:'quantity missing',priceMissing:'price missing',estimatedAmount:'Estimated quantity',missing:'Not included in this subtotal',offline_price_missing:'No compatible saved or offline price. Open the recipe to check online.',preview:'Offline cost preview',unknown:'No cost available yet'},
 de:{quantityMissing:'Menge fehlt',priceMissing:'Preis fehlt',estimatedAmount:'Geschätzte Menge',missing:'Nicht in dieser Zwischensumme enthalten',offline_price_missing:'Kein passender gespeicherter oder Offline-Preis. Rezept für die Online-Prüfung öffnen.',preview:'Offline-Kostenvorschau',unknown:'Noch keine Kosten verfügbar'},
 el:{quantityMissing:'λείπει ποσότητα',priceMissing:'λείπει τιμή',estimatedAmount:'Εκτιμώμενη ποσότητα',missing:'Δεν περιλαμβάνονται σε αυτό το μερικό σύνολο',offline_price_missing:'Δεν υπάρχει συμβατή αποθηκευμένη ή offline τιμή. Άνοιξε τη συνταγή για έλεγχο online.',preview:'Προεπισκόπηση κόστους offline',unknown:'Δεν υπάρχει ακόμη διαθέσιμο κόστος'}
};
class Cook4MeRecipeHubPanelV86 extends BasePanel{
 _v86Text(key){return TEXT[this._uiIngredientLanguage()]?.[key]||TEXT.en[key]||key;}
 _v82Text(key){return key==='offline_price_missing'?this._v86Text(key):super._v82Text(key);}
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.16.10');return result;}
 _v79Reference(ref){
  if(ref?.source!=='retail_snapshot')return super._v79Reference(ref);
  const e=value=>this._escape(String(value??'')),url=/^https:\/\/www\.dm\.de\/p\/d\//.test(ref.sourceUrl||'')?ref.sourceUrl:'';
  return `<small data-v86-retail>${e(ref.productName)} · ${e(ref.location)} · ${e(ref.date)} · ${e(this._v79Money({[ref.currency]:ref.amount}))} / ${e(ref.basisQuantity)} ${e(ref.basisUnit)}${url?` · <a href="${e(url)}" target="_blank" rel="noopener noreferrer">dm.de ↗</a>`:''}</small>`;
 }
 _v79CostHtml(recipe,state){
  const html=super._v79CostHtml(recipe,state),cost=state.cost;if(!cost)return html;
  const node=this._v67Dom(html),e=value=>this._escape(String(value??''));
  node.querySelectorAll('.v79-evidence>div').forEach((element,index)=>{
   const estimate=cost.ingredients?.[index]?.quantityEstimate;if(!estimate)return;
   const detail=document.createElement('small');detail.dataset.v86QuantityEstimate='';
   detail.textContent=`${this._v86Text('estimatedAmount')}: ${estimate.sourceQuantity} ${estimate.sourceUnit||''} ≈ ${Number(estimate.quantity.toFixed(2))} ${estimate.unit}. ${estimate.label}`;
   if(/^https:\/\/(fdc\.nal\.usda\.gov|www\.nist\.gov)\//.test(estimate.sourceUrl||'')){const link=document.createElement('a');link.href=estimate.sourceUrl;link.target='_blank';link.rel='noopener noreferrer';link.textContent=' ↗';detail.append(link);}
   element.append(detail);
  });
  const missing=(cost.ingredients||[]).filter(row=>row.coverage<1);
  const explanation=missing.length?`<p class="muted" data-v86-missing><strong>${e(this._v86Text('missing'))}:</strong> ${missing.map(row=>`${e(row.name)} (${e(this._v86Text(row.priceStatus==='recipe_amount_unknown'?'quantityMissing':'priceMissing'))})`).join('; ')}</p>`:'';
  if(explanation)node.querySelector('.v79-price-head')?.insertAdjacentHTML('afterend',explanation);
  return node.innerHTML;
 }
 _v66BindRecipe(container,recipe,...args){
  super._v66BindRecipe(container,recipe,...args);
  if(!container.matches('[data-v66-ref]'))return;
  this._v86Observer??=new IntersectionObserver(entries=>{
   for(const entry of entries){if(!entry.isIntersecting)continue;this._v86Observer.unobserve(entry.target);const recipe=entry.target._v82Recipe;if(recipe)this._v86QueuePreview(recipe,entry.target);}
  },{rootMargin:'100px'});
  this._v86Observer.observe(container);
 }
 _v86QueuePreview(recipe,container){
  const state=this._v79CostState(recipe);if(state.cost||state.loading||state.v86Queued||state.v86Attempted)return;
  state.v86Queued=true;this._v86Queue??=[];this._v86Queue.push({recipe,container,state,context:this._prefKey()});void this._v86Drain();
 }
 async _v86Drain(){
  this._v86Running??=0;
  while(this._v86Running<3&&this._v86Queue?.length){
   const job=this._v86Queue.shift(),{recipe,container,state,context}=job;state.v86Queued=false;
   if(!container.isConnected||context!==this._prefKey()||this._v79CostState(recipe)!==state||state.cost||state.loading)continue;
   this._v86Running++;state.v86Attempted=true;
   void this._api('cook4me/v34/recipe_cost',{entry_id:this._entryId,recipe:this._v79Payload(recipe),offline_only:true}).then(cost=>{
    if(context!==this._prefKey()||this._v79CostState(recipe)!==state||state.loading||state.cost||!Array.isArray(cost?.ingredients))return;
    state.cost=cost;recipe.cost=cost;this._v79PaintRecipe(recipe,state);
   }).catch(()=>{}).finally(()=>{this._v86Running--;void this._v86Drain();});
  }
 }
 _v82PaintCard(recipe){
  super._v82PaintCard(recipe);const cost=this._v79CostState(recipe).cost;
  this.shadowRoot?.querySelectorAll('[data-v66-ref]').forEach(card=>{
   if(card._v82Recipe!==recipe)return;const badge=card.querySelector('[data-v82-card-cost]');if(!badge)return;
   if(cost?.offlinePreview)badge.title=this._v86Text('preview');
   if(cost&&!Object.keys(cost.totalsByCurrency||{}).length)badge.textContent=this._v86Text('unknown');
  });
 }
 disconnectedCallback(){this._v86Observer?.disconnect();this._v86Observer=null;this._v86Queue=[];super.disconnectedCallback();}
}
customElements.define('cook4me-recipe-hub-panel-v86',Cook4MeRecipeHubPanelV86);
