import "./cook4me-panel-v83.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v83');
const TEXT={
 en:{lookup_pending:'Checking remaining ingredient prices…',catalog:'Ingredient list',help:'Browse all ingredients, view their details, or add a product to your kitchen.',details:'Ingredient details',add:'Add product',previous:'Previous',next:'Next',empty:'No ingredients match your search.',failed:'The ingredient list could not be loaded.',retry:'Retry',search_limited:'No compatible local price found within the search limit. A purchase price or linked product can fill this gap.'},
 el:{lookup_pending:'Έλεγχος τιμών για τα υπόλοιπα υλικά…',catalog:'Λίστα υλικών',help:'Δες όλα τα υλικά, τις πληροφορίες τους ή πρόσθεσε προϊόν στην κουζίνα σου.',details:'Πληροφορίες υλικού',add:'Προσθήκη προϊόντος',previous:'Προηγούμενα',next:'Επόμενα',empty:'Δεν βρέθηκαν υλικά για την αναζήτηση.',failed:'Δεν ήταν δυνατή η φόρτωση της λίστας υλικών.',retry:'Δοκιμή ξανά',search_limited:'Δεν βρέθηκε συμβατή τοπική τιμή εντός του ορίου αναζήτησης. Συμπλήρωσε τιμή αγοράς ή σύνδεσε προϊόν.'},
 de:{lookup_pending:'Weitere Zutatenpreise werden geprüft…',catalog:'Zutatenliste',help:'Alle Zutaten durchsuchen, Details ansehen oder ein Produkt zur Küche hinzufügen.',details:'Zutatendetails',add:'Produkt hinzufügen',previous:'Zurück',next:'Weiter',empty:'Keine passenden Zutaten gefunden.',failed:'Die Zutatenliste konnte nicht geladen werden.',retry:'Erneut versuchen',search_limited:'Innerhalb des Suchlimits wurde kein passender lokaler Preis gefunden. Kaufpreis eingeben oder ein Produkt verknüpfen.'}
};
const fold=value=>String(value||'').normalize('NFD').replace(/\p{M}/gu,'').toLocaleLowerCase();
class Cook4MeRecipeHubPanelV84 extends BasePanel{
 _v84Text(key){return TEXT[this._uiIngredientLanguage()]?.[key]||TEXT.en[key]||key;}
 _v82Text(key){return ['search_limited','lookup_pending'].includes(key)?this._v84Text(key):super._v82Text(key);}
 _loadIngredientCatalog(_language=null,refresh=false){
  if(!this._entryId)return Promise.resolve();
  const context=this._prefKey(),entry=this._entryId,language=this._uiIngredientLanguage(),key=`${context}:${language}`;
  if(this._v84CatalogLoad?.key===key)return this._v84CatalogLoad.promise;
  if(!refresh&&this._resourceHasData('catalog'))return Promise.resolve();
  if(!refresh&&this._v63CatalogFailure===`${entry}:${language}`)return Promise.resolve();
  const load={key};this._v84CatalogLoad=load;this._ingredientCatalogLoading=true;
  const current=()=>this._v84CatalogLoad===load&&context===this._prefKey()&&language===this._uiIngredientLanguage();
  load.promise=(async()=>{
   try{
    const result=await this._api('cook4me/v31/ingredient_catalog',{entry_id:entry,language,refresh:Boolean(refresh)});
    if(!current())return;
    if(result.presentationVersion!==63||!Array.isArray(result.items)||!result.items.length)throw new Error(this._v84Text('failed'));
    this._ingredientCatalog=result.items.sort((a,b)=>String(a.name).localeCompare(String(b.name),language));this._ingredientCatalogLanguage=language;this._v63CatalogFailure=null;
   }catch(error){if(current()){this._v63CatalogFailure=`${entry}:${language}`;this._message(`${this._t('error')}: ${error.message||error}`,true);}}
   finally{if(this._v84CatalogLoad===load){this._ingredientCatalogLoading=false;this._v84CatalogLoad=null;if(context===this._prefKey()&&language===this._uiIngredientLanguage()){this._renderTab();if(this._v78Dialog)this._v78IngredientOptions();}}}
  })();
  return load.promise;
 }
 _v79CostHtml(recipe,state){const html=super._v79CostHtml(recipe,state);return html+(state.cost?.priceLookupPending?`<p role="status" data-v84-price-pending>${this._escape(this._v84Text('lookup_pending'))}</p>`:'');}
 _v79PaintRecipe(recipe,state){
  super._v79PaintRecipe(recipe,state);
  if(!state.cost?.priceLookupPending){state.v84PollStart=null;return;}
  if(state.loading||state.v84Poll)return;
  const context=this._prefKey();state.v84PollStart??=Date.now();if(Date.now()-state.v84PollStart>180000)return;
  this._v84Polls??=new Set();
  const timer=setTimeout(()=>{
   this._v84Polls.delete(timer);state.v84Poll=null;
   if(!this.isConnected||context!==this._prefKey()||this._v79CostState(recipe)!==state||!this._v82ShownRecipes().includes(recipe))return;
   state.checkedAt=0;void this._v79LoadCost(recipe);
  },3000);state.v84Poll=timer;this._v84Polls.add(timer);
 }
 _v79Reset(){this._v84ClearPolls();return super._v79Reset();}
 _v84ClearPolls(){for(const timer of this._v84Polls||[])clearTimeout(timer);this._v84Polls?.clear();}
 disconnectedCallback(){this._v84ClearPolls();super.disconnectedCallback();}
 _renderProfile(c){
  super._renderProfile(c);
  const stock=c.querySelector('[data-v78-section=stock]');if(!stock)return;
  // Stock is visible immediately; only individual lot editors remain expandable.
  const inventory=c.querySelector('#houseInventoryRows')?.closest('details');if(inventory)inventory.open=true;
  const context=this._prefKey();if(this._v84Catalog?.context!==context)this._v84Catalog={context,query:'',page:0};
  const section=document.createElement('section');section.className='card v84-catalog';section.dataset.v84Catalog='';stock.querySelector('[data-v78-inventory]')?.after(section);
  const e=v=>this._escape(String(v??''));
  section.innerHTML=`<h2>${e(this._v84Text('catalog'))}</h2><p class="muted">${e(this._v84Text('help'))}</p><label class="field">${e(this._t('ingredientSearch'))}<input type="search" data-v84-search value="${e(this._v84Catalog.query)}"></label><p role="status" data-v84-status></p><div data-v84-rows></div><div class="v84-pages"><button type="button" class="btn secondary" data-v84-previous>${e(this._v84Text('previous'))}</button><span data-v84-page></span><button type="button" class="btn secondary" data-v84-next>${e(this._v84Text('next'))}</button><button type="button" class="btn secondary" data-v84-retry hidden>${e(this._v84Text('retry'))}</button></div>`;
  section.querySelector('[data-v84-search]').oninput=event=>{this._v84Catalog.query=event.target.value;this._v84Catalog.page=0;this._v84CatalogRows(section);};
  for(const [key,delta] of [['previous',-1],['next',1]])section.querySelector(`[data-v84-${key}]`).onclick=()=>{this._v84Catalog.page+=delta;this._v84CatalogRows(section);};
  section.querySelector('[data-v84-retry]').onclick=()=>void this._loadIngredientCatalog(null,true);
  this._v84CatalogRows(section);this._v84Styles();
 }
 _v84CatalogRows(c){
  const state=this._v84Catalog,query=fold(state.query),rows=(this._ingredientCatalog||[]).filter(row=>fold(`${row.name} ${row.canonicalName||''}`).includes(query));
  const size=60,pages=Math.max(1,Math.ceil(rows.length/size));state.page=Math.max(0,Math.min(state.page,pages-1));
  const failed=this._v63CatalogFailure===`${this._entryId}:${this._uiIngredientLanguage()}`;
  c.querySelector('[data-v84-status]').textContent=this._ingredientCatalogLoading?this._t('catalogLoading'):failed&&!rows.length?this._v84Text('failed'):rows.length?`${rows.length} ${this._v84Text('catalog').toLocaleLowerCase()}`:this._v84Text('empty');
  c.querySelector('[data-v84-retry]').hidden=!failed;c.querySelector('[data-v84-page]').textContent=`${state.page+1} / ${pages}`;
  c.querySelector('[data-v84-previous]').disabled=state.page===0;c.querySelector('[data-v84-next]').disabled=state.page>=pages-1;
  const list=c.querySelector('[data-v84-rows]');list.replaceChildren();
  for(const row of rows.slice(state.page*size,(state.page+1)*size)){
   const line=document.createElement('div');line.className='v84-ingredient';
   const details=document.createElement('button');details.type='button';details.className='btn secondary';details.textContent=row.name;details.title=this._v84Text('details');details.onclick=()=>void this._showIngredientInfo(row);
   const add=document.createElement('button');add.type='button';add.className='btn secondary';add.textContent='+';add.setAttribute('aria-label',`${this._v84Text('add')}: ${row.name}`);
   add.onclick=async()=>{const context=this._prefKey();await this._v78Open('manual');if(context!==this._prefKey()||!this._v78Draft)return;this._v78Draft.ingredient=structuredClone(row);this._v78RenderCapture();};
   line.append(details,add);list.append(line);
  }
 }
 _v83ExclusionPicker(c,...args){
  super._v83ExclusionPicker(c,...args);
  // Catalog failures must leave an explicit retry, rather than a blank select.
  if(this._v63CatalogFailure===`${this._entryId}:${this._uiIngredientLanguage()}`){const retry=document.createElement('button');retry.type='button';retry.className='btn secondary';retry.textContent=this._v84Text('retry');retry.onclick=()=>void this._loadIngredientCatalog(null,true);c.querySelector('.v83-picker-body').append(retry);}
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.16.9');return result;}
 _v84Styles(){if(this.shadowRoot.querySelector('#v84Styles'))return;const style=document.createElement('style');style.id='v84Styles';style.textContent=`.v84-catalog{margin-top:16px}.v84-catalog .field{display:flex;flex-direction:column;gap:6px}.v84-catalog input{max-width:100%;box-sizing:border-box}.v84-catalog [data-v84-rows]{max-height:620px;overflow:auto;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.v84-ingredient{display:flex;gap:4px;min-width:0}.v84-ingredient button:first-child{flex:1;text-align:left;overflow:hidden;text-overflow:ellipsis}.v84-ingredient button:last-child{flex:none;min-width:44px}.v84-pages{display:flex;align-items:center;justify-content:center;gap:12px;margin-top:16px}@media(max-width:700px){.v84-catalog [data-v84-rows]{grid-template-columns:1fr}.v84-pages{flex-wrap:wrap}}`;this.shadowRoot.append(style);}
}
customElements.define('cook4me-recipe-hub-panel-v84',Cook4MeRecipeHubPanelV84);
