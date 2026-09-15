import "./cook4me-panel-v70.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v70");
const BUILD="2026.9.15.13";
const CONTROLS='button,input,select,textarea,a,label,summary,[contenteditable="true"]';

class Cook4MeRecipeHubPanelV71 extends BasePanel{
 _recipeKeyLocal(recipe){
  if(recipe?.bookKey)return String(recipe.bookKey);
  // Keep the frontend key identical to recipe_experience.recipe_storage_key.
  for(const [field,prefix] of [["groupingFunctionalId","g"],["sendGroupingFunctionalId","g"],["id","local"],["recipeFunctionalId","r"],["variantFunctionalId","v"],["displayVariantId","v"],["searchVariantId","v"]]){
   const value=String(recipe?.[field]||"").trim();if(value)return `${prefix}:${value}`;
  }
  const title=String(recipe?.title||"").normalize("NFKD").toLowerCase().replace(/\p{M}/gu,"").replace(/[^\p{L}\p{N}]+/gu," ").trim();
  return `title:${String(recipe?.language||recipe?.sourceLanguage||"").toLowerCase()}:${title}`;
 }
 _renderBook(container){
  this._v71RenderingBook=true;
  try{return super._renderBook(container);}finally{this._v71RenderingBook=false;}
 }
 _recipeCard(recipe,custom=false){
  const html=super._recipeCard(recipe,custom&&!this._isOfficialRecipe(recipe));if(!html)return html;
  const node=this._v67Dom(html),card=node.firstElementChild,title=card.querySelector('h3');
  if(title)title.title=title.textContent;
  card.tabIndex=0;card.setAttribute('role','group');card.setAttribute('aria-haspopup','dialog');
  card.setAttribute('aria-label',`${recipe.title||""}. ${this._t("recipeFullscreen")}`);
  if(this._v71RenderingBook)this._v71CollectionControl(card);
  return node.innerHTML;
 }
 _v71CollectionControl(container,collection=""){
  container.querySelector('[data-v66-action=delete]')?.remove();
  let button=container.querySelector('[data-v71-remove]');
  if(!button){
   button=document.createElement('button');button.type='button';button.className='btn secondary rx-v66-icon';
   button.setAttribute('data-v71-remove','');button.innerHTML='<ha-icon icon="mdi:delete-outline" aria-hidden="true"></ha-icon>';
   container.querySelector('.rx-v66-actions')?.appendChild(button);
  }
  button.title=this._t(collection==='recipeList'?'removeRecipeList':'removeFavorite');button.setAttribute('aria-label',button.title);
  return button;
 }
 _buttonIcon(button){return button.hasAttribute('data-v71-remove')?null:super._buttonIcon(button);}
 async _showRecipe(recipe,custom=false,collection=""){
  this._v71OpenedCollection=collection;
  return super._showRecipe(recipe,custom&&!this._isOfficialRecipe(recipe));
 }
 _v66BindRecipe(container,recipe,custom,slot=null,fullscreen=false){
  custom=custom&&!this._isOfficialRecipe(recipe);
  const collection=fullscreen?this._v71OpenedCollection:container.closest('#favGrid')?'favorites':container.closest('#listGrid')?'recipeList':"";
  if(collection)this._v71CollectionControl(container,collection).addEventListener('click',event=>{
   event.stopPropagation();void this._v71RemoveBook(collection,recipe);
  });
  const open=()=>void this._showRecipe(recipe,custom,collection);
  if(!fullscreen){
   if(collection)container.querySelector('[data-v66-action=cook]')?.addEventListener('click',event=>{
    event.stopImmediatePropagation();event.stopPropagation();
    void this._v71CookCollection(recipe,custom,collection,this._v66State(recipe,slot?.id||""));
   });
   // Own the photo listener before the inherited one; one click opens once.
   container.querySelector('[data-v66-photo]')?.addEventListener('click',event=>{event.stopImmediatePropagation();event.stopPropagation();open();});
   container.addEventListener('click',event=>{
    if(event.defaultPrevented||event.target.closest(CONTROLS))return;
    const selection=window.getSelection?.();if(selection&&!selection.isCollapsed&&container.contains(selection.anchorNode))return;
    open();
   });
   container.addEventListener('keydown',event=>{
    if(event.target===container&&!event.repeat&&['Enter',' '].includes(event.key)){event.preventDefault();open();}
   });
  }
  super._v66BindRecipe(container,recipe,custom,slot,fullscreen);
 }
 async _v71CookCollection(recipe,custom,collection,previous){
  await this._showRecipe(recipe,custom,collection);
  if(!this._opened||this._recipeKey(this._opened)!==this._recipeKey(recipe))return;
  const state=this._v66State(this._opened);state.cooking=true;state.step=previous.step||0;state.device=previous.device;state.sections=new Set(['steps']);
  this._renderRecipeDialog();
 }
 async _v71BookAction(collection,recipe,remove){
  this._v71BookPending??=new Set();const context=this._prefKey(),key=`${context}:${collection}:${this._recipeKeyLocal(recipe)}`;
  if(this._v71BookPending.has(key))return;this._v71BookPending.add(key);
  try{
   const result=await this._api('cook4me/v19/book_toggle',{entry_id:this._entryId,collection,recipe,remove});
   if(context!==this._prefKey())return;
   this._bookState={...(this._bookState||{}),...result};
   if(remove&&this._opened&&this._v71OpenedCollection===collection&&this._recipeKeyLocal(this._opened)===this._recipeKeyLocal(recipe))this._v63CloseRecipe?.();
   this._renderTab();
  }catch(error){this._message(`${this._t('error')}: ${error.message||error}`,true);}
  finally{this._v71BookPending.delete(key);}
 }
 _v71RemoveBook(collection,recipe){return this._v71BookAction(collection,recipe,true);}
 _toggleBook(collection,recipe){
  const key=this._recipeKeyLocal(recipe),saved=(this._bookState?.[collection]||[]).find(row=>this._recipeKeyLocal(row)===key);
  return this._v71BookAction(collection,saved||recipe,Boolean(saved));
 }
 async _deleteRecipe(recipe){
  if(this._v71DeletePending)return;this._v71DeletePending=true;
  const context=this._prefKey(),id=String(recipe.id||"");
  try{
   if(!id||this._isOfficialRecipe(recipe))throw new Error(this._t('recipeUnavailable'));
   const result=await this._api('cook4me/recipe_delete',{entry_id:this._entryId,recipe_id:id});
   if(context!==this._prefKey())return;
   if(!result?.deleted)throw new Error(this._t('recipeUnavailable'));
   if(result.book)this._bookState={...(this._bookState||{}),...result.book};
   const entry=this._entry();if(entry)entry.recipes=(entry.recipes||[]).filter(row=>String(row.id)!==id);
   if(this._opened&&String(this._opened.id)===id)this._v63CloseRecipe?.();
   this._renderTab();await this._loadOverview(true);
  }catch(error){this._message(`${this._t('error')}: ${error.message||error}`,true);}
  finally{this._v71DeletePending=false;}
 }
 _v71FitTitle(title){
  const box=title.parentElement;if(!box?.clientWidth||!box.clientHeight)return;
  // Measure real wrapping rather than estimating from characters/language.
  title.style.removeProperty('-webkit-line-clamp');title.style.display='block';
  let low=12,high=20;title.style.fontSize=`${low}px`;
  while(high-low>.25){const size=(low+high)/2;title.style.fontSize=`${size}px`;
   if(title.scrollHeight>box.clientHeight-28||title.scrollWidth>title.clientWidth)high=size;else low=size;
  }
  title.style.fontSize=`${low}px`;title.style.removeProperty('display');
 }
 _v71FitTitles(){
  this._v71TitleObserver??=new ResizeObserver(entries=>{for(const entry of entries){const title=entry.target.querySelector('h3');if(title)this._v71FitTitle(title);}});
  this._v71TitleObserver.disconnect();
  this.shadowRoot?.querySelectorAll('.rx-v66-recipe>.rx-v66-title').forEach(box=>{this._v71TitleObserver.observe(box);this._v71FitTitle(box.querySelector('h3'));});
 }
 _bindCards(container,items,custom=false){
  super._bindCards(container,items,custom);this._ensureV71Styles();
  cancelAnimationFrame(this._v71FitFrame);this._v71FitFrame=requestAnimationFrame(()=>this._v71FitTitles());
 }
 _renderTab(){
  const result=super._renderTab();this.setAttribute('data-cook4me-build',BUILD);this._ensureV71Styles();
  cancelAnimationFrame(this._v71FitFrame);this._v71FitFrame=requestAnimationFrame(()=>this._v71FitTitles());
  return result;
 }
 disconnectedCallback(){this._v71TitleObserver?.disconnect();cancelAnimationFrame(this._v71FitFrame);super.disconnectedCallback();}
 _ensureV71Styles(){
  if(!this.shadowRoot||this.shadowRoot.getElementById('cook4meV71Styles'))return;
  const style=document.createElement('style');style.id='cook4meV71Styles';style.textContent=`
   .rx-v69-media>.rx-v69-overlay{justify-content:center}.rx-v69-overlay select{flex:0 1 140px}
   article.rx-v66-recipe{box-sizing:border-box;width:100%;height:310px;display:flex;flex-direction:column;cursor:pointer}
   article.rx-v66-recipe>.rx-v66-title{box-sizing:border-box;height:88px;min-height:88px;flex:0 0 88px;padding:14px!important;overflow:hidden}
   article.rx-v66-recipe>.rx-v66-title h3{font-size:20px;line-height:1.25;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:4;overflow:hidden;max-height:60px;width:100%}
   article.rx-v66-recipe>.rx-v66-title h3 span{display:inline;font-size:.82em}
   article.rx-v66-recipe>.rx-v69-media{height:220px;min-height:220px;flex:0 0 220px}
   article.rx-v66-recipe .rx-v66-photo,article.rx-v66-recipe .rx-v66-photo .media,article.rx-v66-recipe .rx-v66-photo img.cover{height:220px!important;min-height:220px!important;max-height:220px!important;width:100%;object-fit:cover}
   article.rx-v66-recipe:has(>.rx-v66-body){height:600px}
   article.rx-v66-recipe>.rx-v66-body{flex:1;min-height:0;overflow:auto;cursor:auto}
   article.rx-v66-recipe:focus-visible{outline:2px solid var(--primary-color);outline-offset:3px}
  `;this.shadowRoot.appendChild(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v71',Cook4MeRecipeHubPanelV71);
