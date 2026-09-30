// Keep lower-right background-job notifications on their own compositor layer.
// Removing an animated/fixed progress card used to invalidate the fullscreen
// recipe overlay and could produce a visible whole-screen flash.
export const JobNotificationStabilityMixin=Base=>class extends Base{
 _v260JobStyles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v260JobStabilityStyles'))return;
  const style=document.createElement('style');
  style.id='v260JobStabilityStyles';
  style.textContent=`
   .rx-v63-progress{
    contain:layout paint style!important;
    isolation:isolate!important;
    overflow:hidden!important;
    transform:translateZ(0);
    backface-visibility:hidden;
   }
   .rx-v63-progress .rx-v59-op{
    contain:layout paint!important;
    transform:translateZ(0);
    backface-visibility:hidden;
    will-change:opacity,transform;
    transition:opacity .18s ease,transform .18s ease!important;
   }
   .rx-v63-progress .rx-v59-op.v260-retiring{
    opacity:0!important;
    transform:translate3d(0,6px,0)!important;
    pointer-events:none!important;
   }
   @media(prefers-reduced-motion:reduce){
    .rx-v63-progress .rx-v59-op{transition:none!important}
   }
  `;
  this.shadowRoot.append(style);
 }
 _processStart(...args){
  this._v260JobStyles();
  const job=super._processStart(...args);
  if(job?.card){
   job.card.classList.remove('v260-retiring');
   job.card.style.removeProperty('visibility');
   job.card.style.removeProperty('opacity');
  }
  return job;
 }
 _v260RemoveJobCard(job){
  const card=job?.card;
  if(!card?.isConnected)return;
  card.classList.add('v260-retiring');
  const finish=()=>{
   if(!card.isConnected)return;
   // Remove only after the card is already invisible. This keeps the fullscreen
   // recipe compositor untouched when the progress-stack DOM changes.
   card.style.setProperty('visibility','hidden');
   requestAnimationFrame(()=>card.remove());
  };
  if(globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches){
   finish();
   return;
  }
  let finished=false;
  const done=()=>{if(finished)return;finished=true;card.removeEventListener('transitionend',done);finish();};
  card.addEventListener('transitionend',done,{once:true});
  setTimeout(done,260);
 }
 _processEnd(job){
  if(!job||job._v260EndHandled)return;
  job._v260EndHandled=true;
  const failed=!!job.failed,cancelled=!!job.cancelled;
  const result=super._processEnd(job);
  if(job.removeTimer)clearTimeout(job.removeTimer);
  const delay=failed?2600:cancelled?1800:650;
  job.removeTimer=setTimeout(()=>this._v260RemoveJobCard(job),delay);
  return result;
 }
 _renderShell(){
  const result=super._renderShell();
  this._v260JobStyles();
  return result;
 }
};
