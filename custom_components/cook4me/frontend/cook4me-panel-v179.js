const V178='cook4me-recipe-hub-panel-v178';
if(!customElements.get(V178))await import('./cook4me-panel-v178.js?v=2026.9.22.5');
const BasePanel=customElements.get(V178);

class Cook4MeRecipeHubPanelV179 extends BasePanel{
 _v179StateKey(){
  const user=String(this._hass?.user?.id||this._hass?.user?.name||'anonymous');
  const entry=String(this._entryId||'none');
  return `cook4me.weekUi.v1.${user}.${entry}`;
 }
 _v179LoadState(){
  const key=this._v179StateKey();
  if(this._v179UiKey===key&&this._v179UiState)return this._v179UiState;
  let value={folds:{},openRecipe:null,scrollTop:0};
  try{
   const raw=JSON.parse(globalThis.localStorage?.getItem(key)||'{}');
   if(raw&&typeof raw==='object')value={...value,...raw,folds:raw.folds&&typeof raw.folds==='object'?raw.folds:{}};
  }catch(_error){}
  this._v179UiKey=key;this._v179UiState=value;return value;
 }
 _v179SaveState(){
  const state=this._v179LoadState();
  try{globalThis.localStorage?.setItem(this._v179StateKey(),JSON.stringify(state));}catch(_error){}
 }
 _v179SetFold(key,open){
  const state=this._v179LoadState();state.folds={...(state.folds||{}),[key]:Boolean(open)};this._v179SaveState();
 }
 _v179FoldOpen(key){return this._v179LoadState().folds?.[key]===true;}
 _v179FoldSection(section,key){
  if(!section||section.dataset.v179Fold)return;
  const heading=[...section.children].find(node=>node.matches?.('h2,h3'));
  if(!heading)return;
  const body=document.createElement('div');body.className='v179-fold-body';
  for(const node of [...section.childNodes])if(node!==heading)body.append(node);
  const button=document.createElement('button');button.type='button';button.className='v179-fold-head';button.dataset.v179FoldButton=key;
  const title=document.createElement('span');title.className='v179-fold-title';title.textContent=heading.textContent||'';
  const icon=document.createElement('ha-icon');icon.setAttribute('icon','mdi:chevron-down');icon.setAttribute('aria-hidden','true');
  button.append(title,icon);heading.remove();section.prepend(button,body);section.dataset.v179Fold=key;
  const apply=open=>{body.hidden=!open;button.setAttribute('aria-expanded',String(open));section.classList.toggle('v179-open',open);};
  apply(this._v179FoldOpen(key));
  button.addEventListener('click',()=>{const open=button.getAttribute('aria-expanded')!=='true';apply(open);this._v179SetFold(key,open);});
 }
 _v179FoldMealSlots(c){
  const grid=c?.querySelector?.('.rx-week-grid');if(!grid||grid.closest('[data-v179-fold="mealSlots"]'))return;
  const headings=[...c.children].filter(node=>node.tagName==='H2');
  const heading=headings.find(node=>String(node.textContent||'').trim()===String(this._t('mealSlots')||'').trim())||headings[0];
  if(!heading)return;
  const section=document.createElement('section');section.className='card v179-meal-fold';c.insertBefore(section,heading);
  const body=document.createElement('div');body.className='v179-fold-body';
  let node=heading.nextSibling;const between=[];
  while(node){const next=node.nextSibling;between.push(node);if(node===grid)break;node=next;}
  for(const item of between)body.append(item);
  const button=document.createElement('button');button.type='button';button.className='v179-fold-head';button.dataset.v179FoldButton='mealSlots';
  const title=document.createElement('span');title.className='v179-fold-title';title.textContent=heading.textContent||this._t('mealSlots');
  const icon=document.createElement('ha-icon');icon.setAttribute('icon','mdi:chevron-down');icon.setAttribute('aria-hidden','true');
  button.append(title,icon);heading.remove();section.append(button,body);section.dataset.v179Fold='mealSlots';
  const apply=open=>{body.hidden=!open;button.setAttribute('aria-expanded',String(open));section.classList.toggle('v179-open',open);};
  apply(this._v179FoldOpen('mealSlots'));
  button.addEventListener('click',()=>{const open=button.getAttribute('aria-expanded')!=='true';apply(open);this._v179SetFold('mealSlots',open);});
 }
 _v179DecorateWeek(c){
  if(!c)return;
  this._v179Styles();

  const pattern=c.querySelector('[data-v144-week-pattern]');
  if(pattern){
   pattern.open=this._v179FoldOpen('weekdayPattern');
   if(!pattern.dataset.v179Persist){
    pattern.dataset.v179Persist='1';
    pattern.addEventListener('toggle',()=>this._v179SetFold('weekdayPattern',pattern.open));
   }
  }
  this._v179FoldMealSlots(c);

  const pair=c.querySelector('.two');
  if(pair){
   const cards=[...pair.children].filter(node=>node.matches?.('section.card'));
   this._v179FoldSection(cards[0],'reservedStock');
   this._v179FoldSection(cards[1],'shoppingDelta');
  }
  const summary=c.querySelector('[data-week-summary]');this._v179FoldSection(summary,'summary');
  for(const section of [...c.children].filter(node=>node.matches?.('section.card'))){
   if(section.dataset.v179Fold||section.querySelector(':scope > h2'))continue;
   const title=String(section.querySelector(':scope > h3')?.textContent||'').trim();
   if(!title)continue;
   if(title===String(this._t('leftovers')).trim())this._v179FoldSection(section,'leftovers');
   else if(title===String(this._t('priceInventory')).trim())this._v179FoldSection(section,'priceInventory');
   else if(title===String(this._t('completedPurchases')).trim())this._v179FoldSection(section,'completedPurchases');
  }
 }
 _v179RecipeToken(recipe){
  return String(recipe?.displayVariantId||recipe?.searchVariantId||recipe?.variantFunctionalId||recipe?.recipeFunctionalId||recipe?.id||recipe?.title||'');
 }
 _v179FindWeekRecipe(saved){
  if(!saved)return null;
  const slots=this._weekState?.slots||[];
  const slot=slots.find(row=>String(row?.id||'')===String(saved.slotId||''));
  if(slot?.recipe)return slot.recipe;
  const wanted=String(saved.token||'');
  for(const row of slots){
   const recipe=row?.recipe||this._leftoverById?.(row?.leftoverId)?.recipe;
   if(recipe&&this._v179RecipeToken(recipe)===wanted)return recipe;
  }
  return null;
 }
 _v179StoreOpenRecipe(recipe,custom=false){
  if(this._tab!=='week'||!recipe)return;
  const token=this._v179RecipeToken(recipe);
  const slot=(this._weekState?.slots||[]).find(row=>this._v179RecipeToken(row?.recipe||this._leftoverById?.(row?.leftoverId)?.recipe)===token);
  const state=this._v179LoadState();state.openRecipe={token,slotId:String(slot?.id||''),custom:Boolean(custom)};this._v179SaveState();
 }
 _v179ClearOpenRecipe(){
  const state=this._v179LoadState();state.openRecipe=null;this._v179SaveState();
 }
 _v179WatchExplicitRecipeClose(dialog){
  if(!dialog||dialog.dataset.v179CloseWatch)return;dialog.dataset.v179CloseWatch='1';
  const clear=()=>this._v179ClearOpenRecipe();
  dialog.querySelector('[data-modal-close]')?.addEventListener('click',clear,{capture:true});
  dialog.addEventListener('click',event=>{if(event.target===dialog)clear();},{capture:true});
  const keydown=event=>{if(event.key==='Escape'&&dialog.isConnected)clear();};
  document.addEventListener('keydown',keydown,true);
  const observer=new MutationObserver(()=>{if(!dialog.isConnected){document.removeEventListener('keydown',keydown,true);observer.disconnect();}});
  observer.observe(this.shadowRoot,{childList:true,subtree:true});
 }
 async _showRecipe(recipe,custom=false){
  const result=await super._showRecipe(recipe,custom);
  if(this._tab==='week'&&this._v63RecipeDialog?.isConnected){
   this._v179StoreOpenRecipe(recipe,custom);this._v179WatchExplicitRecipeClose(this._v63RecipeDialog);
  }
  return result;
 }
 _v179RestoreRecipe(){
  if(this._tab!=='week'||this._v63RecipeDialog?.isConnected||this._v179RestoringRecipe)return;
  const saved=this._v179LoadState().openRecipe;if(!saved)return;
  const recipe=this._v179FindWeekRecipe(saved);
  if(!recipe){this._v179ClearOpenRecipe();return;}
  this._v179RestoringRecipe=true;
  queueMicrotask(async()=>{try{await this._showRecipe(recipe,Boolean(saved.custom));}finally{this._v179RestoringRecipe=false;}});
 }
 _v179CaptureScroll(){
  if(this._v179RenderedTab!=='week')return;
  const content=this.shadowRoot?.getElementById('content');if(!content)return;
  const state=this._v179LoadState();state.scrollTop=Number(content.scrollTop||0);this._v179SaveState();
 }
 _v179RestoreScroll(){
  if(this._tab!=='week')return;
  const top=Number(this._v179LoadState().scrollTop||0),content=this.shadowRoot?.getElementById('content');if(!content)return;
  requestAnimationFrame(()=>{if(this._tab==='week'&&content.isConnected)content.scrollTop=top;});
 }
 async _api(type,data={}){
  const shopping=type.endsWith('/shopping_add')||type.endsWith('/week_add_shopping');
  if(shopping)data={...data,display_language:this._uiIngredientLanguage?.()||this._langCode?.()||'en',supermarket_language:this._v140SupermarketLanguage?.()||''};
  const result=await super._api(type,data);
  if(Array.isArray(result?.shoppingDelta)){
   result.shoppingDelta=result.shoppingDelta.map(row=>row&&typeof row==='object'&&row.shoppingDisplayName?{...row,name:row.shoppingDisplayName}:row);
  }
  return result;
 }
 _renderWeek(c){
  const result=super._renderWeek(c);this._v179DecorateWeek(c);queueMicrotask(()=>{this._v179RestoreScroll();this._v179RestoreRecipe();});return result;
 }
 _renderTab(){
  this._v179CaptureScroll();
  const result=super._renderTab();
  this._v179RenderedTab=this._tab;
  if(this._tab==='week')queueMicrotask(()=>{const c=this.shadowRoot?.getElementById('content');if(c){this._v179DecorateWeek(c);this._v179RestoreScroll();this._v179RestoreRecipe();}});
  this._v179Styles();this.setAttribute('data-cook4me-build','2026.9.22.6');return result;
 }
 _v179Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v179Styles'))return;
  const style=document.createElement('style');style.id='v179Styles';style.textContent=`
   .v179-fold-head{width:100%;display:flex;align-items:center;justify-content:space-between;gap:12px;border:0;background:transparent;color:var(--primary-text-color);padding:2px 0 10px;cursor:pointer;text-align:left;font:inherit}.v179-fold-title{font-size:1.17em;font-weight:700}.v179-fold-head ha-icon{transition:transform .18s ease;color:var(--secondary-text-color)}[data-v179-fold].v179-open>.v179-fold-head ha-icon{transform:rotate(180deg)}.v179-fold-body[hidden]{display:none!important}.v179-meal-fold{margin-top:12px}.v179-meal-fold>.v179-fold-body{padding-top:2px}.v145-week-pattern{margin-top:12px!important}
   @media(prefers-reduced-motion:reduce){.v179-fold-head ha-icon{transition:none}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v179',Cook4MeRecipeHubPanelV179);
