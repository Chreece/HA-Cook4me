export const RecipeFullscreenGuardMixin=Base=>class extends Base{
 connectedCallback(){
  super.connectedCallback?.();
  if(!this._v258VisibilityHandler){
   this._v258VisibilityHandler=()=>{
    if(globalThis.document?.visibilityState==='visible')void this._v258SyncWakeLock();
    else void this._v258ReleaseWakeLock();
   };
   globalThis.document?.addEventListener?.('visibilitychange',this._v258VisibilityHandler);
  }
 }
 disconnectedCallback(){
  this._v258UnlockBackgroundScroll();
  void this._v258ReleaseWakeLock();
  if(this._v258VisibilityHandler){
   globalThis.document?.removeEventListener?.('visibilitychange',this._v258VisibilityHandler);
   this._v258VisibilityHandler=null;
  }
  super.disconnectedCallback?.();
 }
 _v258StyleState(node,property){
  return {
   value:node.style.getPropertyValue(property),
   priority:node.style.getPropertyPriority(property),
  };
 }
 _v258RestoreStyle(node,property,state){
  if(state?.value)node.style.setProperty(property,state.value,state.priority||'');
  else node.style.removeProperty(property);
 }
 _v258BackgroundScrollTargets(){
  const result=[],seen=new Set(),add=node=>{if(node&&node.style&&!seen.has(node)){seen.add(node);result.push(node);}};
  add(this.shadowRoot?.getElementById('content'));

  let node=this;
  while(node){
   let parent=node.parentElement||null;
   if(!parent){
    const root=node.getRootNode?.();
    parent=root&&root.host?root.host:null;
   }
   if(!parent||parent===node)break;
   const computed=globalThis.getComputedStyle?.(parent);
   if(/auto|scroll|overlay/.test(`${computed?.overflowY||''} ${computed?.overflow||''}`))add(parent);
   node=parent;
  }

  const doc=this.ownerDocument||globalThis.document;
  add(doc?.scrollingElement);
  add(doc?.documentElement);
  add(doc?.body);
  return result;
 }
 _v258LockBackgroundScroll(){
  if(this._v258ScrollLocks?.length)return;
  const locks=[];
  for(const node of this._v258BackgroundScrollTargets()){
   locks.push({
    node,
    top:Number(node.scrollTop||0),
    left:Number(node.scrollLeft||0),
    overflowY:this._v258StyleState(node,'overflow-y'),
    overscrollY:this._v258StyleState(node,'overscroll-behavior-y'),
    gutter:this._v258StyleState(node,'scrollbar-gutter'),
   });
   node.style.setProperty('overflow-y','hidden','important');
   node.style.setProperty('overscroll-behavior-y','none','important');
   node.style.setProperty('scrollbar-gutter','stable','important');
  }
  this._v258ScrollLocks=locks;
 }
 _v258UnlockBackgroundScroll(){
  const locks=this._v258ScrollLocks||[];
  this._v258ScrollLocks=null;
  for(const lock of locks){
   const {node}=lock;
   if(!node?.style)continue;
   this._v258RestoreStyle(node,'overflow-y',lock.overflowY);
   this._v258RestoreStyle(node,'overscroll-behavior-y',lock.overscrollY);
   this._v258RestoreStyle(node,'scrollbar-gutter',lock.gutter);
   try{node.scrollTop=lock.top;node.scrollLeft=lock.left;}catch(_error){}
  }
 }
 _v258CookingFullscreen(){
  const recipe=this._opened;
  return !!(
   recipe&&
   this._v63RecipeDialog&&
   this._v66State?.(recipe)?.cooking===true
  );
 }
 async _v258ReleaseWakeLock(){
  const sentinel=this._v258WakeLock;
  this._v258WakeLock=null;
  if(!sentinel||sentinel.released)return;
  try{await sentinel.release();}catch(_error){}
 }
 async _v258SyncWakeLock(){
  const desired=this._v258CookingFullscreen();
  if(!desired){
   await this._v258ReleaseWakeLock();
   return;
  }
  if(globalThis.document?.visibilityState!=='visible')return;
  const api=globalThis.navigator?.wakeLock;
  if(!api?.request)return;
  if(this._v258WakeLock&&!this._v258WakeLock.released)return;
  if(this._v258WakeRequest)return this._v258WakeRequest;

  const request=(async()=>{
   try{
    const sentinel=await api.request('screen');
    if(!this._v258CookingFullscreen()){
     try{await sentinel.release();}catch(_error){}
     return;
    }
    this._v258WakeLock=sentinel;
    sentinel.addEventListener?.('release',()=>{
     if(this._v258WakeLock===sentinel)this._v258WakeLock=null;
    });
   }catch(_error){
    // Unsupported/blocked wake lock is a graceful no-op.
   }finally{
    if(this._v258WakeRequest===request)this._v258WakeRequest=null;
   }
  })();
  this._v258WakeRequest=request;
  return request;
 }
 _v258WrapRecipeClose(){
  const close=this._v63CloseRecipe;
  if(!close||close._v258FullscreenGuard)return;
  const wrapped=(...args)=>{
   const result=close(...args);
   this._v258UnlockBackgroundScroll();
   void this._v258ReleaseWakeLock();
   return result;
  };
  wrapped._v258FullscreenGuard=true;
  this._v63CloseRecipe=wrapped;
 }
 async _showRecipe(...args){
  const result=await super._showRecipe(...args);
  if(this._v63RecipeDialog&&this._opened){
   this._v258LockBackgroundScroll();
   this._v258WrapRecipeClose();
   void this._v258SyncWakeLock();
  }
  return result;
 }
 _renderRecipeDialog(){
  const result=super._renderRecipeDialog();
  if(this._v63RecipeDialog&&this._opened){
   this._v258LockBackgroundScroll();
   this._v258Styles();
   queueMicrotask(()=>void this._v258SyncWakeLock());
  }else{
   this._v258UnlockBackgroundScroll();
   void this._v258ReleaseWakeLock();
  }
  return result;
 }
 _v258Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v258FullscreenGuardStyles'))return;
  const style=document.createElement('style');
  style.id='v258FullscreenGuardStyles';
  style.textContent=`
   [data-recipe-dialog]{overflow:hidden!important;overscroll-behavior:none!important}
   [data-recipe-dialog] .rx-v66-fullscreen{overscroll-behavior-y:contain!important}
  `;
  this.shadowRoot.append(style);
 }
};
