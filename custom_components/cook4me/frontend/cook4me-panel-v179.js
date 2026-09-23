const V178='cook4me-recipe-hub-panel-v178';
if(!customElements.get(V178))await import('./cook4me-panel-v178.js?v=2026.9.22.5');
const BasePanel=customElements.get(V178);

class Cook4MeRecipeHubPanelV179 extends BasePanel{
 _v179StateKey(){
  const user=String(this._hass?.user?.id||this._hass?.user?.name||'anonymous');
  const entry=String(this._entryId||'none');
  return `cook4me.uiState.v2.${user}.${entry}`;
 }
 _v179LegacyWeekStateKey(){
  const user=String(this._hass?.user?.id||this._hass?.user?.name||'anonymous');
  const entry=String(this._entryId||'none');
  return `cook4me.weekUi.v1.${user}.${entry}`;
 }
 _v179LoadState(){
  const key=this._v179StateKey();
  if(this._v179UiKey===key&&this._v179UiState)return this._v179UiState;
  let value={version:2,tabs:{}},loaded=false;
  try{
   const raw=JSON.parse(globalThis.localStorage?.getItem(key)||'null');
   if(raw&&typeof raw==='object'){
    value={version:2,...raw,tabs:raw.tabs&&typeof raw.tabs==='object'?raw.tabs:{}};
    loaded=true;
   }
  }catch(_error){}
  if(!loaded){
   try{
    const legacy=JSON.parse(globalThis.localStorage?.getItem(this._v179LegacyWeekStateKey())||'null');
    if(legacy&&typeof legacy==='object'){
     value.tabs.week={
      folds:legacy.folds&&typeof legacy.folds==='object'?legacy.folds:{},
      details:{},
      openRecipe:legacy.openRecipe||null,
      openFilter:null,
      scrollTop:Number(legacy.scrollTop||0),
      recipeScrollTop:0,
     };
    }
   }catch(_error){}
  }
  // Old close listeners were lost on dialog redraw. Discard only that stale
  // popup state once, never filters, folds, recipes or inventory data.
  if(value.recipeCloseVersion!==199){
   for(const state of Object.values(value.tabs||{}))if(state&&typeof state==='object'){state.openRecipe=null;state.openFilter=null;}
   value.recipeCloseVersion=199;
  }
  this._v179UiKey=key;this._v179UiState=value;return value;
 }
 _v179TabState(tab=this._tab){
  const root=this._v179LoadState(),key=String(tab||'unknown');
  const current=root.tabs?.[key];
  if(!current||typeof current!=='object'){
   root.tabs={...(root.tabs||{}),[key]:{folds:{},details:{},openRecipe:null,openFilter:null,scrollTop:0,recipeScrollTop:0}};
  }else{
   current.folds=current.folds&&typeof current.folds==='object'?current.folds:{};
   current.details=current.details&&typeof current.details==='object'?current.details:{};
  }
  return root.tabs[key];
 }
 _v179SaveState(){
  const state=this._v179LoadState();
  try{globalThis.localStorage?.setItem(this._v179StateKey(),JSON.stringify(state));}catch(_error){}
 }
 _v179SetFold(key,open,tab=this._tab){
  const state=this._v179TabState(tab);state.folds={...(state.folds||{}),[key]:Boolean(open)};this._v179SaveState();
 }
 _v179FoldOpen(key,tab=this._tab){return this._v179TabState(tab).folds?.[key]===true;}
 _v179DetailsKey(node,index,scope='content'){
  const summary=String(node?.querySelector?.(':scope > summary')?.textContent||'').trim().replace(/\s+/g,' ').slice(0,90);
  const stable=String(node?.id||node?.dataset?.v179StateKey||node?.dataset?.section||node?.dataset?.mode||'').trim();
  return `${scope}:${stable||index}:${summary}`;
 }
 _v179PersistDetails(root,scope='content',tab=this._tab){
  if(!root)return;
  const state=this._v179TabState(tab);
  [...root.querySelectorAll('details')].forEach((node,index)=>{
   if(node.matches?.('[data-v144-week-pattern]'))return;
   const key=this._v179DetailsKey(node,index,scope);
   if(Object.prototype.hasOwnProperty.call(state.details||{},key))node.open=state.details[key]===true;
   if(node.dataset.v179StateWatch===key)return;
   node.dataset.v179StateWatch=key;
   node.addEventListener('toggle',()=>{
    const current=this._v179TabState(tab);
    current.details={...(current.details||{}),[key]:Boolean(node.open)};
    this._v179SaveState();
   });
  });
 }
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
 _v179RecipeSnapshot(recipe,custom=false){
  if(!recipe||typeof recipe!=='object')return null;
  const keys=custom
   ?['id','title','source','language','selectedLanguage','servings','groupSize','yield','ingredients','steps','notes','tags','cover','image','imageUrl','match']
   :['id','title','source','language','selectedLanguage','displayVariantId','searchVariantId','variantFunctionalId','recipeFunctionalId','groupingFunctionalId','sendVariantId','sendGroupingFunctionalId','sendRecipeFunctionalId','cover','image','imageUrl'];
  const out={};for(const key of keys)if(recipe[key]!==undefined&&recipe[key]!==null)out[key]=recipe[key];
  return out;
 }
 _v179RecipeCandidates(){
  const rows=[];
  for(const list of [this._results,this._todayResults,this._recommendations,this._entry?.()?.recipes]){
   if(Array.isArray(list))rows.push(...list);
  }
  for(const slot of this._weekState?.slots||[]){
   const recipe=slot?.recipe||this._leftoverById?.(slot?.leftoverId)?.recipe;
   if(recipe)rows.push(recipe);
  }
  return rows.filter(row=>row&&typeof row==='object');
 }
 _v179FindRecipe(saved){
  if(!saved)return null;
  if(saved.slotId){
   const slot=(this._weekState?.slots||[]).find(row=>String(row?.id||'')===String(saved.slotId));
   const recipe=slot?.recipe||this._leftoverById?.(slot?.leftoverId)?.recipe;
   if(recipe)return recipe;
  }
  const wanted=String(saved.token||'');
  const found=this._v179RecipeCandidates().find(recipe=>this._v179RecipeToken(recipe)===wanted);
  return found||saved.recipe||null;
 }
 _v179StoreOpenRecipe(recipe,custom=false,tab=this._tab){
  if(!recipe)return;
  const token=this._v179RecipeToken(recipe);
  const slot=(this._weekState?.slots||[]).find(row=>this._v179RecipeToken(row?.recipe||this._leftoverById?.(row?.leftoverId)?.recipe)===token);
  const state=this._v179TabState(tab);
  state.openRecipe={token,slotId:String(slot?.id||''),custom:Boolean(custom),recipe:this._v179RecipeSnapshot(recipe,custom)};
  this._v179SaveState();
 }
 _v179ClearOpenRecipe(tab=this._tab){
  this._v179RecipeEpoch=(this._v179RecipeEpoch||0)+1;
  const state=this._v179TabState(tab);state.openRecipe=null;state.recipeScrollTop=0;this._v179SaveState();
 }
 _v179WatchExplicitRecipeClose(dialog,tab=this._tab){
  if(!dialog||dialog.dataset.v179CloseWatch)return;dialog.dataset.v179CloseWatch='1';
  const context=this._v179StateKey();
  const clear=()=>{if(context===this._v179StateKey())this._v179ClearOpenRecipe(tab);};
  // Delegate to the stable overlay: nutrition/price/translation redraws replace
  // the close button. A nested ingredient/filter Escape must not close the recipe.
  dialog.addEventListener('click',event=>{if(event.target===dialog||event.target.closest?.('[data-modal-close]'))clear();},{capture:true});
  const keydown=event=>{if(event.key==='Escape'&&dialog.isConnected&&!this._v62CloseIngredient&&!this._v63CloseFilter)clear();};
  document.addEventListener('keydown',keydown,true);
  const observer=new MutationObserver(()=>{if(!dialog.isConnected){document.removeEventListener('keydown',keydown,true);observer.disconnect();}});
  observer.observe(this.shadowRoot,{childList:true,subtree:true});
 }
 async _showRecipe(recipe,custom=false){
  const tab=String(this._tab||'unknown'),context=this._v179StateKey();
  const epoch=this._v179RecipeEpoch=(this._v179RecipeEpoch||0)+1;
  const result=await super._showRecipe(recipe,custom);
  if(context===this._v179StateKey()&&tab===String(this._tab||'unknown')&&epoch===this._v179RecipeEpoch&&this._v63RecipeDialog?.isConnected){
   this._v179StoreOpenRecipe(this._opened||recipe,custom,tab);
   this._v179WatchExplicitRecipeClose(this._v63RecipeDialog,tab);
   this._v179PersistDetails(this._v63RecipeDialog,`recipe:${this._v179RecipeToken(this._opened||recipe)}`,tab);
  }
  return result;
 }
 _renderRecipeDialog(){
  const result=super._renderRecipeDialog();
  const dialog=this._v63RecipeDialog;
  if(dialog?.isConnected&&this._opened){
   this._v179WatchExplicitRecipeClose(dialog,this._tab);
   this._v179PersistDetails(dialog,`recipe:${this._v179RecipeToken(this._opened)}`,this._tab);
  }
  return result;
 }
 _v179RestoreRecipe(){
  if(this._v63RecipeDialog?.isConnected||this._v179RestoringRecipe)return;
  const tab=String(this._tab||'unknown'),state=this._v179TabState(tab),saved=state.openRecipe;
  if(!saved)return;
  const recipe=this._v179FindRecipe(saved);if(!recipe)return;
  const context=this._v179StateKey(),epoch=this._v179RecipeEpoch||0;
  const ticket={};this._v179RestoringRecipe=ticket;
  queueMicrotask(async()=>{
   try{
    if(context!==this._v179StateKey()||tab!==String(this._tab||'unknown')||epoch!==(this._v179RecipeEpoch||0)||this._v179TabState(tab).openRecipe!==saved||this._v63RecipeDialog?.isConnected)return;
    await this._showRecipe(recipe,Boolean(saved.custom));
    if(context!==this._v179StateKey()||tab!==String(this._tab||'unknown'))return;
    const dialog=this._v63RecipeDialog?.querySelector?.('.rx-dialog');
    if(dialog){const top=Number(state.recipeScrollTop||0);requestAnimationFrame(()=>{if(dialog.isConnected)dialog.scrollTop=top;});}
   }finally{if(this._v179RestoringRecipe===ticket)this._v179RestoringRecipe=false;}
  });
 }
 _v179CaptureViewState(tab=this._v179RenderedTab){
  if(!tab)return;
  const state=this._v179TabState(tab),content=this.shadowRoot?.getElementById('content');
  if(content)state.scrollTop=Number(content.scrollTop||0);
  const dialog=this._v63RecipeDialog?.querySelector?.('.rx-dialog');
  if(dialog?.isConnected)state.recipeScrollTop=Number(dialog.scrollTop||0);
  this._v179SaveState();
 }
 _v179RestoreViewState(){
  const tab=String(this._tab||'unknown'),state=this._v179TabState(tab),content=this.shadowRoot?.getElementById('content');
  if(content){const top=Number(state.scrollTop||0);requestAnimationFrame(()=>{if(this._tab===tab&&content.isConnected)content.scrollTop=top;});}
  this._v179RestoreRecipe();this._v179RestoreFilter();
 }
 _v179WatchExplicitFilterClose(dialog,tab=this._tab){
  if(!dialog||dialog.dataset.v179FilterWatch)return;dialog.dataset.v179FilterWatch='1';
  const context=this._v179StateKey();
  const clear=()=>{if(context!==this._v179StateKey())return;const state=this._v179TabState(tab);state.openFilter=null;this._v179SaveState();};
  dialog.addEventListener('click',event=>{if(event.target===dialog||event.target.closest?.('[data-close],[data-apply]'))clear();},{capture:true});
  const keydown=event=>{if(event.key==='Escape'&&dialog.isConnected)clear();};
  document.addEventListener('keydown',keydown,true);
  const observer=new MutationObserver(()=>{if(!dialog.isConnected){document.removeEventListener('keydown',keydown,true);observer.disconnect();}});
  observer.observe(this.shadowRoot,{childList:true,subtree:true});
 }
 _showFilter(key){
  const tab=String(this._tab||'unknown'),context=this._v179StateKey(),result=super._showFilter(key);
  queueMicrotask(()=>{
   if(context!==this._v179StateKey()||tab!==String(this._tab||'unknown'))return;
   const dialog=this.shadowRoot?.querySelector?.(`[data-filter-dialog="${String(key).replace(/"/g,'')}"]`);
   if(!dialog)return;
   const state=this._v179TabState(tab);state.openFilter=String(key);this._v179SaveState();
   this._v179WatchExplicitFilterClose(dialog,tab);
  });
  return result;
 }
 _v179RestoreFilter(){
  if(this._v63CloseFilter||this._v179RestoringFilter)return;
  const state=this._v179TabState(),key=String(state.openFilter||'');if(!key)return;
  const context=this._v179StateKey(),tab=this._tab,epoch=this._v179RecipeEpoch||0;
  this._v179RestoringFilter=true;
  queueMicrotask(()=>{try{
   if(context===this._v179StateKey()&&tab===this._tab&&epoch===(this._v179RecipeEpoch||0)&&this._v179TabState(tab).openFilter===key&&!this._v63CloseFilter)this._showFilter(key);
  }finally{this._v179RestoringFilter=false;}});
 }
 _v179DecoratePersistentUi(c){
  if(!c)return;
  this._v179PersistDetails(c,'content',this._tab);
 }
 _selectV52Tab(tab){
  this._v179RestoringRecipe=false;
  this._v179RecipeEpoch=(this._v179RecipeEpoch||0)+1;
  this._v179CaptureViewState();
  return super._selectV52Tab(tab);
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
  const result=super._renderWeek(c);this._v179DecorateWeek(c);this._v179DecoratePersistentUi(c);return result;
 }
 _renderTab(){
  this._v179CaptureViewState();
  const result=super._renderTab();
  this._v179RenderedTab=this._tab;
  const tab=this._tab,context=this._v179StateKey();
  const epoch=this._v179RenderEpoch=(this._v179RenderEpoch||0)+1;
  queueMicrotask(()=>{
   if(epoch!==this._v179RenderEpoch||tab!==this._tab||context!==this._v179StateKey())return;
   const c=this.shadowRoot?.getElementById('content');if(!c)return;
   if(this._tab==='week')this._v179DecorateWeek(c);
   this._v179DecoratePersistentUi(c);
   this._v179RestoreViewState();
  });
  this._v179Styles();this.setAttribute('data-cook4me-build','2026.9.22.6');return result;
 }
 disconnectedCallback(){
  this._v179RecipeEpoch=(this._v179RecipeEpoch||0)+1;
  this._v179RenderEpoch=(this._v179RenderEpoch||0)+1;
  this._v179CaptureViewState();
  if(super.disconnectedCallback)super.disconnectedCallback();
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
