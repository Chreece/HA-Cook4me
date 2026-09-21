const V135='cook4me-recipe-hub-panel-v135';
if(!customElements.get(V135))await import('./cook4me-panel-v135.js?v=2026.9.20.9');
const BasePanel=customElements.get(V135);

class Cook4MeRecipeHubPanelV136 extends BasePanel{
 _v136FoldWeekSections(container){
  const root=container||this.shadowRoot?.getElementById('content');
  if(!root)return;
  for(const slot of this._weekState?.slots||[]){
   const recipe=slot?.recipe||this._leftoverById?.(slot?.leftoverId)?.recipe;
   if(!recipe)continue;
   const state=this._v66State?.(recipe,String(slot.id||''));
   state?.sections?.clear?.();
  }
  root.querySelectorAll('.rx-week-slot details[data-v66-section]').forEach(details=>{
   details.open=false;
   details.removeAttribute('open');
  });
 }

 _renderWeek(container){
  const result=super._renderWeek(container);
  this._v136FoldWeekSections(container);
  this._v136Styles();
  return result;
 }

 _updateHeader(){
  super._updateHeader();
  this._v136Styles();
 }
 _renderShell(){
  super._renderShell();
  this._v136Styles();
 }
 _renderTab(){
  const result=super._renderTab();
  this._v136Styles();
  if(this._tab==='week')this._v136FoldWeekSections(this.shadowRoot?.getElementById('content'));
  this.setAttribute('data-cook4me-build','2026.9.21.1');
  return result;
 }

 _v136Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v136Styles'))return;
  const style=document.createElement('style');
  style.id='v136Styles';
  style.textContent=`
   /* v133 isolated the cooker into its own stacking context. That prevented the
      v135 multiply blend from seeing the real card background, leaving the flat
      photo rectangle visible. Blend against the card itself instead. */
   .v130-model{
    isolation:auto!important;
    background:transparent!important;
   }
   .v130-model-photo{
    mix-blend-mode:multiply!important;
    background:transparent!important;
   }

   /* Week recipe disclosure sections always start folded. */
   .rx-week-slot details[data-v66-section]:not([open])>.rx-v66-section{display:none}
  `;
  this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v136',Cook4MeRecipeHubPanelV136);
