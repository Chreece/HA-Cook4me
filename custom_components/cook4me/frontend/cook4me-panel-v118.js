import './cook4me-panel-v117.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v117');
const WORDS={
 en:{weighing:'Weighing'},
 de:{weighing:'Wiegen'},
 el:{weighing:'Ζύγισμα'}
};
class Cook4MeRecipeHubPanelV118 extends BasePanel{
 _v118Text(key){return (WORDS[this._uiIngredientLanguage?.()||this._langCode?.()]||WORDS.en)[key]||key;}
 _v118ArrangeFullscreen(){
  const overlay=this._v63RecipeDialog,recipe=this._opened;
  if(!overlay||!recipe)return;

  const info=overlay.querySelector('[data-v66-section="info"]');
  const ingredients=overlay.querySelector('[data-v66-section="ingredients"]');
  const price=overlay.querySelector('.v79-recipe-price');
  const scale=overlay.querySelector('[data-v116-recipe]');

  // Keep the complete current price UI unchanged, but make it part of Information.
  // Moving the existing node preserves its refresh/evidence listeners and live updates.
  const infoBody=info?.querySelector(':scope > .rx-v66-section');
  if(infoBody&&price&&!infoBody.contains(price)){
   infoBody.append(price);
  }

  // Live weighing belongs to the same disclosure stack as Information/Ingredients.
  // It is folded by default and remembers its open state across dialog rerenders.
  if(scale&&!scale.closest('[data-v118-weighing]')){
   const state=this._v66State(recipe);
   const details=document.createElement('details');
   details.dataset.v66Section='weighing';
   details.dataset.v118Weighing='';
   if(state.sections.has('weighing'))details.open=true;

   const summary=document.createElement('summary');
   summary.textContent=this._v118Text('weighing');
   const body=document.createElement('div');
   body.className='rx-v66-section v118-weighing-body';

   scale.classList.remove('card');
   body.append(scale);
   details.append(summary,body);

   if(ingredients)ingredients.after(details);
   else if(info)info.after(details);
   else (overlay.querySelector('.rx-v66-body')||overlay.querySelector('#recipeDetail'))?.prepend(details);

   details.addEventListener('toggle',()=>{
    if(details.open)state.sections.add('weighing');
    else state.sections.delete('weighing');
   });
  }
  this._v118Styles();
 }
 _renderRecipeDialog(){
  super._renderRecipeDialog();
  this._v118ArrangeFullscreen();
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.18.4');return result;}
 _v118Styles(){
  if(this.shadowRoot?.querySelector('#v118Styles'))return;
  const style=document.createElement('style');style.id='v118Styles';style.textContent=`
   [data-v118-weighing]>.rx-v66-section{padding-top:12px}
   [data-v118-weighing] .v116-recipe-scale{margin:0!important;padding:0!important;border:0!important;background:transparent!important;border-radius:0!important}
   [data-v66-section="info"] .v79-recipe-price{margin:18px 0 0}
  `;
  this.shadowRoot?.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v118',Cook4MeRecipeHubPanelV118);
