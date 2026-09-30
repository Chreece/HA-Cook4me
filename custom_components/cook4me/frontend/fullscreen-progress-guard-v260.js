export const FullscreenProgressGuardMixin=Base=>class extends Base{
 _v260FullscreenActive(){
  return !!(this._v63RecipeDialog&&this._opened);
 }
 _v260Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v260FullscreenProgressStyles'))return;
  const style=document.createElement('style');
  style.id='v260FullscreenProgressStyles';
  style.textContent=`
   .rx-v59-op{
    contain:layout paint style;
    backface-visibility:hidden;
    transform:translateZ(0);
    transition:opacity .16s ease;
   }
   .rx-v59-op.v260-progress-fade{opacity:0}
   .rx-v59-op.v260-progress-hidden{opacity:0!important;visibility:hidden!important;pointer-events:none!important}
   @media(prefers-reduced-motion:reduce){.rx-v59-op{transition:none!important}}
  `;
  this.shadowRoot.append(style);
 }
 _v260FlushDeferredJobCards(){
  const cards=this._v260DeferredProgressCards;
  if(!cards?.size)return;
  this._v260DeferredProgressCards=null;
  for(const card of cards)card?.remove?.();
 }
 _processEnd(job){
  if(!job||job._v260EndHandled)return super._processEnd(job);
  job._v260EndHandled=true;
  const fullscreen=this._v260FullscreenActive();
  const result=super._processEnd(job);
  if(!fullscreen||!job.card)return result;

  // Removing a fixed compositor layer while the recipe dialog is fullscreen can
  // invalidate the fullscreen/backdrop layer on Chromium and produce a one-frame
  // white/dark flash. Let the card finish normally, fade only that isolated layer,
  // and defer actual DOM removal until fullscreen closes.
  if(job.removeTimer)clearTimeout(job.removeTimer);
  this._v260Styles();
  const delay=job.failed?2600:650;
  job.removeTimer=setTimeout(()=>{
   const card=job.card;
   if(!card?.isConnected)return;
   card.classList.add('v260-progress-fade');
   const hide=()=>{
    if(!card.isConnected)return;
    if(this._v260FullscreenActive()){
     card.classList.add('v260-progress-hidden');
     this._v260DeferredProgressCards??=new Set();
     this._v260DeferredProgressCards.add(card);
    }else{
     card.remove();
    }
   };
   if(globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches)hide();
   else setTimeout(hide,180);
  },delay);
  return result;
 }
 _v258WrapRecipeClose(){
  if(this._v63CloseRecipe?._v260ProgressGuard)return;
  if(super._v258WrapRecipeClose)super._v258WrapRecipeClose();
  const close=this._v63CloseRecipe;
  if(!close||close._v260ProgressGuard)return;
  const wrapped=(...args)=>{
   const result=close(...args);
   queueMicrotask(()=>this._v260FlushDeferredJobCards());
   return result;
  };
  wrapped._v260ProgressGuard=true;
  this._v63CloseRecipe=wrapped;
 }
 _renderRecipeDialog(){
  const result=super._renderRecipeDialog();
  this._v260Styles();
  if(!this._v260FullscreenActive())queueMicrotask(()=>this._v260FlushDeferredJobCards());
  return result;
 }
 disconnectedCallback(){
  this._v260FlushDeferredJobCards();
  if(super.disconnectedCallback)super.disconnectedCallback();
 }
};
