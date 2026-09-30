// Keep an already-open fullscreen recipe mounted while the page behind it redraws.
export const FullscreenStabilityMixin=Base=>class extends Base{
 _v262FullscreenOpen(){
  return !!(this._opened&&this._v63RecipeDialog?.isConnected);
 }

 _v262RecipeRenderSignature(){
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
  const uiLanguage=this._uiIngredientLanguage?.()||this._langCode?.()||'';
  try{
   return JSON.stringify([
    uiLanguage,
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
   return [
    uiLanguage,
    recipe.displayVariantId||recipe.id||recipe.title||'',
    recipe.selectedServings||'',
    state?.cooking?'cooking':'info',
    state?.step||0,
   ].join('|');
  }
 }

 _renderTab(...args){
  const preserve=this._v262FullscreenOpen();
  if(!preserve)return super._renderTab(...args);

  // v63 restores preferences after visibilitychange and then redraws the page.
  // Its _renderTab() also calls _renderRecipeDialog(), which rebuilds the dialog
  // with innerHTML. Chromium visibly shows the backdrop/page for a few frames
  // before the replacement dialog paints. Mark page-owned redraws so the dialog
  // can stay mounted when its visible recipe state did not change.
  this._v262PageRenderDepth=(this._v262PageRenderDepth||0)+1;
  try{
   return super._renderTab(...args);
  }finally{
   this._v262PageRenderDepth=Math.max(0,(this._v262PageRenderDepth||1)-1);
  }
 }

 _renderRecipeDialog(...args){
  const signature=this._v262RecipeRenderSignature();
  if(
   this._v262PageRenderDepth>0&&
   this._v262FullscreenOpen()&&
   this._v262FullscreenSignature===signature
  ){
   return this._v63RecipeDialog;
  }

  const result=super._renderRecipeDialog(...args);
  if(this._v262FullscreenOpen()){
   this._v262FullscreenSignature=this._v262RecipeRenderSignature();
  }else{
   this._v262FullscreenSignature='';
  }
  return result;
 }
};
