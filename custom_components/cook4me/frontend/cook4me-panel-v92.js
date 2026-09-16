import "./cook4me-panel-v91.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v91');
const LABELS={en:['Estimate','Partial estimate'],de:['Schätzung','Teilschätzung'],el:['Εκτίμηση','Μερική εκτίμηση']};
class Cook4MeRecipeHubPanelV92 extends BasePanel{
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.16.16');return result;}
 _v82PaintCard(recipe){
  super._v82PaintCard(recipe);
  const state=this._v79CostState(recipe),cost=state.cost;
  if(!cost?.fallbackIngredientCount||state.loading)return;
  const words=LABELS[this._uiIngredientLanguage()]||LABELS.en;
  const label=`${words[cost.budgetComplete?0:1]} ≈ ${this._v79Money(cost.budgetTotalsByCurrency)} · ${cost.budgetIngredientCount}/${cost.ingredients.length}`;
  for(const card of this._v90Cards(recipe)){
   const badge=card.querySelector('[data-v82-card-cost]');if(!badge)continue;
   badge.textContent=label;
   badge.title=`${cost.fallbackIngredientCount} ${this._v91Text('rough')}. ${badge.title}`;
   badge.setAttribute('aria-label',`${label}. ${cost.budgetIngredientCount}/${cost.ingredients.length} ${this._v91Text('covered')}. ${badge.title}`);
  }
 }
}
customElements.define('cook4me-recipe-hub-panel-v92',Cook4MeRecipeHubPanelV92);
