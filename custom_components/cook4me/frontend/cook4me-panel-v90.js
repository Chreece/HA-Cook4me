import "./cook4me-panel-v89.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v89');
const TEXT={
 en:{failed:'Cost unavailable',retry:'Retry',noFood:'No food prices available',water:'Only water is priced; food costs are still missing.'},
 de:{failed:'Kosten nicht verfügbar',retry:'Erneut versuchen',noFood:'Keine Lebensmittelpreise verfügbar',water:'Nur Wasser ist bepreist; die Lebensmittelkosten fehlen noch.'},
 el:{failed:'Το κόστος δεν είναι διαθέσιμο',retry:'Δοκίμασε ξανά',noFood:'Δεν υπάρχουν τιμές τροφίμων',water:'Έχει κοστολογηθεί μόνο το νερό· λείπει ακόμη το κόστος των τροφίμων.'}
};
class Cook4MeRecipeHubPanelV90 extends BasePanel{
 _v90Text(key){return TEXT[this._uiIngredientLanguage()]?.[key]||TEXT.en[key]||key;}
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.16.14');return result;}
 _v90Scope(){return JSON.stringify([this._hass?.user?.id||'',this._entryId||'',this._prefKey()]);}
 _v90AcceptToken(token){
  if(typeof token!=='string'||!token)return null;
  const scope=this._v90Scope(),key='cook4me:price-preview:v90:'+scope;
  if(this._v90Cache?.scope===scope&&this._v90Cache.token===token)return this._v90Cache;
  let entries={};try{const saved=JSON.parse(localStorage.getItem(key));if(saved?.token===token&&saved.entries&&typeof saved.entries==='object')entries=saved.entries;}catch{}
  return this._v90Cache={scope,key,token,entries};
 }
 async _v90EnsureCache(){
  const scope=this._v90Scope(),epoch=this._v90Epoch||0,revision=this._v79Revision||0,day=new Date().toISOString().slice(0,10);
  const key=JSON.stringify([scope,epoch,revision,day]);
  if(this._v90Validation?.key===key&&Date.now()-this._v90Validation.at<60000)return this._v90Validation.promise.then(()=>this._v90Cache?.scope===scope?this._v90Cache:null);
  const validation={key,at:Date.now()};this._v90Validation=validation;
  validation.promise=this._api('cook4me/v34/price_settings',{entry_id:this._entryId}).then(result=>{
   if(this._v90Validation!==validation||scope!==this._v90Scope()||epoch!==(this._v90Epoch||0))return null;
   return this._v90AcceptToken(result.priceCacheToken);
  }).catch(()=>{if(this._v90Validation===validation)this._v90Cache=null;return null;});
  return validation.promise;
 }
 _v90Remember(recipe,state){
  const cache=this._v90Cache,cost=state.cost;
  if(!cache||cache.scope!==this._v90Scope()||!cost||cost.priceLookupPending||this._v79CostState(recipe)!==state)return;
  const key=JSON.stringify(this._v79Payload(recipe));delete cache.entries[key];
  cache.entries[key]={cost,at:Date.now()};
  while(Object.keys(cache.entries).length>100)delete cache.entries[Object.keys(cache.entries)[0]];
  try{let json=JSON.stringify({token:cache.token,entries:cache.entries});while(json.length>1500000&&Object.keys(cache.entries).length>1){delete cache.entries[Object.keys(cache.entries)[0]];json=JSON.stringify({token:cache.token,entries:cache.entries});}localStorage.setItem(cache.key,json);}catch{}
 }
 async _api(type,data={}){
  const scope=this._v90Scope(),result=await super._api(type,data);
  if(scope!==this._v90Scope())return result;
  if(result?.priceCacheToken)this._v90AcceptToken(result.priceCacheToken);
  if(/\/(product_add|inventory_add|inventory_update|inventory_remove|lot_cost_set|price_reference_set|cost_settings_set|recipe_cost_refresh)$/.test(type)||type.endsWith('/price_settings')&&['country','currency','auto_global_prices'].some(key=>key in data)){
   this._v90Validation=null;if(!result?.priceCacheToken)this._v90Cache=null;
  }
  return result;
 }
 _v79PaintRecipe(recipe,state){this._v90Remember(recipe,state);super._v79PaintRecipe(recipe,state);}
 async _v79LoadCost(recipe,force=false){
  if(force)return super._v79LoadCost(recipe,true);
  const context=this._v90Scope(),epoch=this._v90Epoch||0,cache=await this._v90EnsureCache();
  if(context!==this._v90Scope()||epoch!==(this._v90Epoch||0))return;
  const state=this._v79CostState(recipe),saved=cache?.entries[JSON.stringify(this._v79Payload(recipe))];
  if(!state.loading&&saved?.cost&&Date.now()-saved.at<86400000){state.cost=structuredClone(saved.cost);recipe.cost=state.cost;this._v79PaintRecipe(recipe,state);return;}
  return super._v79LoadCost(recipe,false);
 }
 _v90Cards(recipe){return [...(this.shadowRoot?.querySelectorAll('[data-v66-ref]')||[])].filter(card=>card.isConnected&&card._v82Recipe===recipe);}
 async _v86QueuePreview(recipe,container){
  const context=this._v90Scope(),epoch=this._v90Epoch||0,cache=await this._v90EnsureCache();
  if(context!==this._v90Scope()||epoch!==(this._v90Epoch||0))return;
  const state=this._v79CostState(recipe);
  if(!this.isConnected||!container?.isConnected||state.cost||state.loading||state.v86Queued||state.v90Pending||state.v90Retry||state.v90Failed)return;
  const saved=cache?.entries[JSON.stringify(this._v79Payload(recipe))];
  if(saved?.cost&&Date.now()-saved.at<86400000){state.cost=structuredClone(saved.cost);recipe.cost=state.cost;this._v79PaintRecipe(recipe,state);return;}
  state.v86Queued=true;this._v86Queue??=[];this._v86Queue.push({recipe,state,context:this._prefKey(),epoch:this._v90Epoch||0});
  this._v82PaintCard(recipe);void this._v86Drain();
 }
 async _v86Drain(){
  this._v86Running??=0;
  while(this._v86Running<3&&this._v86Queue?.length){
   const {recipe,state,context,epoch}=this._v86Queue.shift();state.v86Queued=false;
   const current=()=>this.isConnected&&epoch===(this._v90Epoch||0)&&context===this._prefKey()&&this._v79CostState(recipe)===state;
   if(!current()||!this._v90Cards(recipe).length||state.cost||state.loading)continue;
   this._v86Running++;state.v90Pending=true;state.v90Attempts=(state.v90Attempts||0)+1;this._v82PaintCard(recipe);
   // Three active requests maximum. Failed requests retry twice; a permanent
   // failure remains visible and can be retried explicitly without opening a card.
   void Promise.resolve().then(()=>this._api('cook4me/v34/recipe_cost',{entry_id:this._entryId,recipe:this._v79Payload(recipe),offline_only:true})).then(cost=>{
    if(!current()||state.loading||state.cost)return;
    if(!Array.isArray(cost?.ingredients))throw new Error('Invalid recipe cost');
    state.cost=cost;recipe.cost=cost;state.v90Failed=false;this._v90Remember(recipe,state);this._v79PaintRecipe(recipe,state);
   }).catch(()=>{
    if(!current()||state.loading||state.cost)return;
    if(state.v90Attempts<3){
     const timer=setTimeout(()=>{this._v90Timers?.delete(timer);state.v90Retry=null;if(current())this._v86QueuePreview(recipe,this._v90Cards(recipe)[0]);},500*state.v90Attempts);
     state.v90Retry=timer;this._v90Timers??=new Set();this._v90Timers.add(timer);
    }else state.v90Failed=true;
   }).finally(()=>{
    this._v86Running--;state.v90Pending=false;
    if(current())this._v82PaintCard(recipe);
    // A serving/payload change may have replaced the state while the old request
    // was pending. The observer already fired, so enqueue the current card here.
    if(this.isConnected&&epoch===(this._v90Epoch||0)&&context===this._prefKey()&&this._v79CostState(recipe)!==state)this._v86QueuePreview(recipe,this._v90Cards(recipe)[0]);
    void this._v86Drain();
   });
  }
 }
 _v82PaintCard(recipe){
  super._v82PaintCard(recipe);const state=this._v79CostState(recipe),cost=state.cost;
  for(const card of this._v90Cards(recipe)){
   const badge=card.querySelector('[data-v82-card-cost]');if(!badge)continue;
   if(cost?.waterOnlyEstimate&&!state.loading){
    const count=cost.ingredients.filter(row=>row.coverage===1).length;
    badge.textContent=`${this._v90Text('noFood')} · ${count}/${cost.ingredients.length} ${this._v87Text('priced')}`;
    badge.title=this._v90Text('water');badge.setAttribute('aria-label',`${badge.textContent}. ${badge.title}`);
   }else if(!cost&&!state.loading){
    badge.textContent=state.v90Failed?this._v90Text('failed'):this._v79Text('loading');badge.title='';
    if(state.v90Failed){
     const button=document.createElement('button');button.type='button';button.dataset.v90Retry='';button.textContent=this._v90Text('retry');
     button.style.cssText='margin-inline-start:.5em;color:inherit;background:transparent;border:1px solid currentColor;border-radius:4px;cursor:pointer';
     button.onclick=event=>{event.stopPropagation();state.v90Failed=false;state.v90Attempts=0;this._v86QueuePreview(recipe,card);};badge.append(button);
    }
    badge.setAttribute('aria-label',badge.textContent);
   }
  }
 }
 _v79CostHtml(recipe,state){
  const node=this._v67Dom(super._v79CostHtml(recipe,state));
  if(state.cost?.waterOnlyEstimate){const head=node.querySelector('.v79-price-head');if(head)head.textContent=this._v90Text('water');}
  return node.innerHTML;
 }
 _v79Reference(ref){
  const node=this._v67Dom(super._v79Reference(ref)),detail=node.querySelector('[data-v87-reference]');
  try{const url=new URL(ref?.sourceUrl);if(ref.source==='retail_snapshot'&&detail&&!detail.querySelector('a')&&url.protocol==='https:'&&!url.username&&!url.password&&!url.port&&['ludwigs.shop','www.gourmet-versand.com'].includes(url.hostname)){
   const link=document.createElement('a');link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';link.textContent=` ${url.hostname} ↗`;detail.append(link);
  }}catch{}
  return node.innerHTML;
 }
 _v90Clear(){this._v90Validation=null;this._v90Cache=null;this._v90Epoch=(this._v90Epoch||0)+1;for(const timer of this._v90Timers||[])clearTimeout(timer);this._v90Timers?.clear();this._v86Queue=[];}
 _v79Reset(){this._v90Clear();super._v79Reset();}
 disconnectedCallback(){this._v90Clear();this._v79Costs=new WeakMap();super.disconnectedCallback();}
}
customElements.define('cook4me-recipe-hub-panel-v90',Cook4MeRecipeHubPanelV90);
