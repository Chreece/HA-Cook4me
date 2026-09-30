// Keep an open fullscreen recipe stable while the page behind it refreshes.
export const FullscreenStabilityMixin=Base=>class extends Base{
 _v260FullscreenOpen(){
  return !!(this._opened&&this._v63RecipeDialog?.isConnected);
 }
 _v260RecipeRenderSignature(){
  const recipe=this._opened;
  if(!recipe)return '';
  const state=this._v66State?.(recipe)||null;
  const visibleState=state?{
   cooking:Boolean(state.cooking),
   step:Number(state.step||0),
   device:String(state.device||''),
   sections:[...(state.sections||[])],
  }:null;
  const favorite=this._isFavorite?.(recipe);
  try{
   return JSON.stringify([
    recipe.title,
    recipe.canonicalName,
    recipe.displayVariantId,
    recipe.searchVariantId,
    recipe.sendVariantId,
    recipe.selectedLanguage,
    recipe.translatedTo,
    recipe.selectedServings,
    recipe.servings,
    recipe.groupSize,
    recipe.yield,
    recipe.ingredients,
    recipe.steps,
    recipe.mealTypes,
    recipe.dietary,
    recipe.match,
    recipe.nutrition,
    recipe.cost,
    visibleState,
    favorite,
   ]);
  }catch(_error){
   return String(recipe.displayVariantId||recipe.id||recipe.title||'');
  }
 }
 _renderTab(...args){
  const preserve=this._v260FullscreenOpen();
  if(!preserve){
   const result=super._renderTab(...args);
   this._v260Styles();
   return result;
  }
  this._v260PageRenderDepth=(this._v260PageRenderDepth||0)+1;
  try{
   const result=super._renderTab(...args);
   this._v260Styles();
   return result;
  }finally{
   this._v260PageRenderDepth=Math.max(0,(this._v260PageRenderDepth||1)-1);
  }
 }
 _renderRecipeDialog(...args){
  const signature=this._v260RecipeRenderSignature();
  if(
   this._v260PageRenderDepth>0&&
   this._v260FullscreenOpen()&&
   this._v260FullscreenSignature===signature
  ){
   // v63 redraws the fullscreen dialog after every page render. Background
   // completions also redraw the page, which replaced the whole fullscreen DOM
   // and produced a visible flash. Keep the existing dialog when its visible
   // recipe state has not changed.
   this._v260Styles();
   return this._v63RecipeDialog;
  }
  const result=super._renderRecipeDialog(...args);
  if(this._v260FullscreenOpen())this._v260FullscreenSignature=this._v260RecipeRenderSignature();
  else this._v260FullscreenSignature='';
  this._v260Styles();
  return result;
 }
 _v260Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#fullscreenStabilityV260'))return;
  const doc=this.ownerDocument||globalThis.document;
  if(!doc?.createElement)return;
  const style=doc.createElement('style');
  style.id='fullscreenStabilityV260';
  style.textContent=`
   /* Removing/completing a progress card must repaint only the progress stack,
      not invalidate the fullscreen recipe layer behind it. */
   .rx-v63-progress{contain:layout paint;isolation:isolate}
  `;
  this.shadowRoot.append(style);
 }
};
