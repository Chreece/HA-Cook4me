function flattenActionDock(dock){
 if(!dock)return dock;
 dock.classList.add('v265-action-row');

 // Preserve the original action nodes/listeners. The old design placed secondary
 // actions inside a "More" <details>; move those exact nodes back into the dock.
 for(const more of [...dock.querySelectorAll(':scope > details.ui203-more')]){
  const grid=more.querySelector('.ui203-more-grid');
  const controls=grid?[...grid.children]:[];
  for(const control of controls){
   control.querySelectorAll?.('.ui203-action-label').forEach(label=>label.remove());
   dock.insertBefore(control,more);
  }
  more.remove();
 }

 // Old expanded menus appended text labels to icon buttons. The compact row is
 // deliberately icon-only; aria-label/title remain for accessibility/tooltips.
 dock.querySelectorAll('.ui203-action-label').forEach(label=>label.remove());
 return dock;
}

export const RecipeActionRowMixin=Base=>class extends Base{
 _v265BlacklistButton(recipe){
  return typeof this._v264BlacklistButton==='function'?this._v264BlacklistButton(recipe):null;
 }
 _v265BindBlacklist(button,recipe){
  if(!button||button._v265Bound)return;
  button._v265Bound=true;
  button.addEventListener('click',event=>{
   event.preventDefault();
   event.stopImmediatePropagation();
   event.stopPropagation();
   void this._v264Blacklist?.(recipe);
  });
 }
 _v265Prepare(root,recipe,{bind=false,removeHeader=false}={}){
  if(!root)return;
  if(removeHeader){
   root.querySelectorAll('header [data-v264-blacklist]').forEach(button=>button.remove());
  }
  const dock=root.matches?.('.ui203-action-dock')?root:root.querySelector?.('.ui203-action-dock');
  if(!dock)return;
  flattenActionDock(dock);

  if(recipe&&!this._v264IsBlacklisted?.(recipe)&&!dock.querySelector('[data-v264-blacklist]')){
   const button=this._v265BlacklistButton(recipe);
   if(button)dock.append(button);
  }
  if(bind&&recipe){
   dock.querySelectorAll('[data-v264-blacklist]').forEach(button=>this._v265BindBlacklist(button,recipe));
  }
  this._v265Styles();
 }
 _recipeCard(recipe,...args){
  const html=super._recipeCard(recipe,...args);if(!html)return html;
  const holder=this._v67Dom?.(html)||(()=>{const node=document.createElement('div');node.innerHTML=html;return node;})();
  const card=holder.firstElementChild;
  if(card)this._v265Prepare(card,recipe);
  return holder.innerHTML;
 }
 _v66BindRecipe(container,recipe,...args){
  const result=super._v66BindRecipe(container,recipe,...args);
  this._v265Prepare(container,recipe,{bind:true});
  return result;
 }
 _renderRecipeDialog(...args){
  const result=super._renderRecipeDialog(...args);
  const overlay=this._v63RecipeDialog;
  if(overlay&&this._opened)this._v265Prepare(overlay,this._opened,{bind:true,removeHeader:true});
  return result;
 }
 _renderTab(...args){
  const result=super._renderTab(...args);
  this._v265Styles();
  return result;
 }
 _v265Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v265RecipeActionRowStyles'))return;
  const style=document.createElement('style');
  style.id='v265RecipeActionRowStyles';
  style.textContent=`
   :host(.ui203) .ui203-action-dock.v265-action-row{
    display:flex!important;
    flex-wrap:nowrap!important;
    align-items:center!important;
    justify-content:flex-start!important;
    gap:6px!important;
    overflow:hidden!important;
    max-width:100%!important;
   }
   :host(.ui203) .ui203-action-dock.v265-action-row .rx-v66-icon{
    flex:1 1 0!important;
    width:auto!important;
    min-width:0!important;
    max-width:44px!important;
    height:40px!important;
    min-height:40px!important;
    padding:6px 2px!important;
   }
   :host(.ui203) .ui203-action-dock.v265-action-row select{
    flex:1 1 82px!important;
    width:auto!important;
    min-width:62px!important;
    max-width:125px!important;
    height:40px!important;
    min-height:40px!important;
   }
   :host(.ui203) .ui203-action-dock.v265-action-row .ui203-action-label,
   :host(.ui203) .ui203-action-dock.v265-action-row details.ui203-more{
    display:none!important;
   }
   :host(.ui203) .ui203-action-dock.v265-action-row [data-v264-blacklist]{
    color:var(--error-color,var(--ui203-ink))!important;
   }
   @media(max-width:480px){
    :host(.ui203) .ui203-action-dock.v265-action-row{gap:4px!important;padding-inline:9px!important}
    :host(.ui203) .ui203-action-dock.v265-action-row .rx-v66-icon{height:38px!important;min-height:38px!important;padding-inline:1px!important}
    :host(.ui203) .ui203-action-dock.v265-action-row select{min-width:54px!important;height:38px!important;min-height:38px!important}
   }
  `;
  this.shadowRoot.append(style);
 }
};

export {flattenActionDock};
