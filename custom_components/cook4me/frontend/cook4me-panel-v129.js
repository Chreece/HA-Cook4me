const V128='cook4me-recipe-hub-panel-v128';
if(!customElements.get(V128))await import('./cook4me-panel-v128.js?v=2026.9.20.2');
const BasePanel=customElements.get(V128);

const V129_WORDS={
 en:{
  pendingRecipe:'Sending to Cook4Me',
  pendingSending:'Sending to the appliance…',
  pendingWaiting:'Sent — waiting for Cook4Me to receive it',
  pendingOffline:'Cook4Me is offline — it will be sent automatically',
  pendingBusy:'Cook4Me is busy — it will be sent automatically',
  pendingRetry:'Waiting to retry delivery'
 },
 de:{
  pendingRecipe:'Wird an Cook4Me gesendet',
  pendingSending:'Wird an das Gerät gesendet…',
  pendingWaiting:'Gesendet — warte auf Empfang durch Cook4Me',
  pendingOffline:'Cook4Me ist offline — wird automatisch gesendet',
  pendingBusy:'Cook4Me ist beschäftigt — wird automatisch gesendet',
  pendingRetry:'Warte auf erneuten Sendeversuch'
 },
 el:{
  pendingRecipe:'Αποστολή στο Cook4Me',
  pendingSending:'Αποστολή στη συσκευή…',
  pendingWaiting:'Στάλθηκε — αναμονή να το παραλάβει το Cook4Me',
  pendingOffline:'Το Cook4Me είναι offline — θα σταλεί αυτόματα',
  pendingBusy:'Το Cook4Me είναι απασχολημένο — θα σταλεί αυτόματα',
  pendingRetry:'Αναμονή για νέα προσπάθεια αποστολής'
 }
};

class Cook4MeRecipeHubPanelV129 extends BasePanel{
 constructor(){
  super();
  this._v129QueueTimer=null;
 }
 _v129Text(key){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return (V129_WORDS[lang]||V129_WORDS.en)[key]||V129_WORDS.en[key]||key;
 }
 _v129QueueReason(queue){
  const reason=String(queue?.reason||'');
  if(reason==='sending')return this._v129Text('pendingSending');
  if(reason==='waiting_for_device')return this._v129Text('pendingWaiting');
  if(reason==='device_offline')return this._v129Text('pendingOffline');
  if(reason==='device_busy')return this._v129Text('pendingBusy');
  return this._v129Text('pendingRetry');
 }
 _v129DecorateQueueBanner(root){
  const queue=this._bookState?.queuedSend;
  const banner=root?.querySelector?.('.queue-banner');
  if(!queue||!banner)return;
  const strong=banner.querySelector('strong');
  const muted=banner.querySelector('.muted');
  if(strong)strong.textContent=`⏳ ${this._v129Text('pendingRecipe')}: ${queue.title||queue.variantId||''}`;
  if(muted)muted.textContent=this._v129QueueReason(queue);
 }
 _v129ScheduleQueueRefresh(){
  const queue=this._bookState?.queuedSend;
  if(!queue||!this._entryId){
   if(this._v129QueueTimer)clearTimeout(this._v129QueueTimer);
   this._v129QueueTimer=null;
   return;
  }
  if(this._v129QueueTimer)return;
  this._v129QueueTimer=setTimeout(async()=>{
   this._v129QueueTimer=null;
   await this._loadBookState(true);
   this._v129ScheduleQueueRefresh();
  },1000);
 }
 async _loadBookState(...args){
  const result=await super._loadBookState(...args);
  this._v129ScheduleQueueRefresh();
  return result;
 }
 async _send(recipe){
  const p=this._processStart(
   this._t('backgroundWork'),
   this._v129Text('pendingSending')
  );
  try{
   const result=await this._api('cook4me/v19/send_or_queue',{entry_id:this._entryId,recipe});
   if(result?.queued){
    if(!this._bookState)this._bookState={};
    this._bookState.queuedSend=result.queued;
    this._updateHeader();
    if(this._tab==='book')this._renderTab();
    this._v129ScheduleQueueRefresh();
    this._message(this._v129QueueReason(result.queued));
   }else if(result?.sendable===false){
    this._message(this._t('customCannotSend'),true);
   }else if(result?.sent){
    this._message(`${this._t('send')}: ${this._clean(recipe.title||'')}`);
    await this._loadOverview(true);
   }
  }catch(error){
   this._message(`${this._t('error')}: ${error.message||error}`,true);
  }finally{
   this._processEnd(p);
  }
 }
 _updateHeader(){
  super._updateHeader();
  this._v129DecorateQueueBanner(this.shadowRoot?.getElementById('status'));
  this._v129ScheduleQueueRefresh();
 }
 _renderBook(container){
  super._renderBook(container);
  this._v129DecorateQueueBanner(container);
  this._v129ScheduleQueueRefresh();
 }
 _resetV51EntryState(...args){
  if(this._v129QueueTimer)clearTimeout(this._v129QueueTimer);
  this._v129QueueTimer=null;
  return super._resetV51EntryState(...args);
 }
 _renderTab(){
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.20.3');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v129',Cook4MeRecipeHubPanelV129);
