const V180='cook4me-recipe-hub-panel-v180';
if(!customElements.get(V180))await import('./cook4me-panel-v180.js?v=2026.9.22.7');
const BasePanel=customElements.get(V180);

const V181_TEXT={
 en:{
  supermarketHelp:'Ingredient names use the UI language first. The supermarket language is shown in parentheses when different, followed by the recipe/original language when different again.',
  supermarketFallback:'Display order: UI language → supermarket language (if different) → recipe/original language (if different). Duplicate names are collapsed.'
 },
 de:{
  supermarketHelp:'Zutatennamen verwenden zuerst die UI-Sprache. Eine abweichende Supermarktsprache steht in Klammern; danach folgt bei Bedarf die Rezept-/Originalsprache.',
  supermarketFallback:'Reihenfolge: UI-Sprache → Supermarktsprache (falls abweichend) → Rezept-/Originalsprache (falls abweichend). Doppelte Namen werden entfernt.'
 },
 el:{
  supermarketHelp:'Τα ονόματα υλικών εμφανίζονται πρώτα στη γλώσσα του UI. Η γλώσσα σούπερ μάρκετ εμφανίζεται σε παρένθεση όταν διαφέρει και μετά η γλώσσα της συνταγής/το αρχικό όνομα όταν διαφέρει ξανά.',
  supermarketFallback:'Σειρά εμφάνισης: γλώσσα UI → γλώσσα σούπερ μάρκετ (αν διαφέρει) → γλώσσα συνταγής/αρχικό όνομα (αν διαφέρει). Τα διπλότυπα ονόματα αφαιρούνται.'
 }
};

class Cook4MeRecipeHubPanelV181 extends BasePanel{
 _v181Text(key){
  const lang=this._langCode?.()||this._uiIngredientLanguage?.()||'en';
  return (V181_TEXT[lang]||V181_TEXT.en)[key]||V181_TEXT.en[key]||key;
 }
 _v140Text(key){
  if(key==='supermarketHelp'||key==='supermarketFallback')return this._v181Text(key);
  return super._v140Text(key);
 }
 _v181CatalogKey(language){
  return `${this._prefKey()}:${String(language||'').trim().toLowerCase()}`;
 }
 _v181NamesFromCatalog(items){
  const map=new Map();
  for(const row of items||[]){
   if(!row||typeof row!=='object'||!row.name)continue;
   for(const field of ['ingredientId','id','key','foodKey']){
    if(row[field])map.set(String(row[field]),String(row.name));
   }
  }
  return map;
 }
 async _v181LoadUiCatalog(force=false){
  if(!this._entryId||!this._hass?.connection)return;
  const language=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  const key=this._v181CatalogKey(language);
  if(!force&&this._v181UiCatalogKey===key)return;
  if(this._v181UiCatalogLoading?.key===key)return this._v181UiCatalogLoading.promise;
  const request={key};
  request.promise=this._hass.connection.sendMessagePromise({
   type:'cook4me/v31/ingredient_catalog',
   entry_id:this._entryId,
   language
  }).then(result=>{
   if(key!==this._v181CatalogKey(this._uiIngredientLanguage?.()||this._langCode?.()||'en'))return;
   this._v181UiNames=this._v181NamesFromCatalog(result?.items);
   this._v181UiCatalogKey=key;
   this._v181RelocalizeWeekState();
   if(this.shadowRoot?.getElementById('content')){
    this._renderTab();
    if(this._opened)this._renderRecipeDialog();
   }
  }).catch(()=>{}).finally(()=>{
   if(this._v181UiCatalogLoading===request)this._v181UiCatalogLoading=null;
  });
  this._v181UiCatalogLoading=request;
  return request.promise;
 }
 async _v140LoadSupermarketCatalog(force=false){
  await super._v140LoadSupermarketCatalog(force);
  const ui=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  if(ui===this._v140SupermarketLanguage()&&this._v140MarketNames){
   this._v181UiNames=this._v140MarketNames;
   this._v181UiCatalogKey=this._v181CatalogKey(ui);
   this._v181RelocalizeWeekState();
   return;
  }
  await this._v181LoadUiCatalog(force);
 }
 _v181Same(a,b){
  const left=String(a||'').trim(),right=String(b||'').trim();
  if(!left||!right)return false;
  try{return left.localeCompare(right,undefined,{sensitivity:'base'})===0;}catch{return left.casefold?.()===right.casefold?.()||left.toLowerCase()===right.toLowerCase();}
 }
 _v181StackedName(row){
  if(!row||typeof row!=='object')return row;
  const already=String(row.shoppingDisplayName||'').trim();
  const original=String(row.originalName||row.recipeName||row.name||row.foodName||'').trim();
  if(already){
   return {...row,originalName:original||row.originalName,name:already,...('foodName'in row?{foodName:already}:{})};
  }
  const key=this._v140IngredientKey(row);
  const ui=String(this._v181UiNames?.get(key)||original||'').trim();
  const market=String(this._v140MarketNames?.get(key)||ui||original||'').trim();
  const primary=ui||market||original;
  const alternatives=[];
  for(const candidate of [market,original]){
   if(!candidate||this._v181Same(candidate,primary)||alternatives.some(value=>this._v181Same(value,candidate)))continue;
   alternatives.push(candidate);
  }
  const shown=primary+alternatives.map(value=>` (${value})`).join('');
  return {
   ...row,
   originalName:original||row.originalName,
   uiName:ui||primary,
   supermarketName:market||primary,
   name:shown,
   ...('foodName'in row?{foodName:shown}:{})
  };
 }
 _v140LocalizeIngredient(row){
  return this._v181StackedName(row);
 }
 _v181LocalizeRows(rows){
  return Array.isArray(rows)?rows.map(row=>this._v181StackedName(row)):rows;
 }
 _v181RelocalizeWeekState(){
  const state=this._weekState;
  if(!state||typeof state!=='object')return;
  if(Array.isArray(state.shoppingDelta))state.shoppingDelta=this._v181LocalizeRows(state.shoppingDelta);
  const reservations=state.reservations;
  if(reservations&&typeof reservations==='object'){
   for(const key of ['items','shortages','unknown']){
    if(Array.isArray(reservations[key]))reservations[key]=this._v181LocalizeRows(reservations[key]);
   }
  }
 }
 async _api(type,data={}){
  const result=await super._api(type,data);
  if(result?.shoppingDelta)result.shoppingDelta=this._v181LocalizeRows(result.shoppingDelta);
  if(result?.reservations&&typeof result.reservations==='object'){
   for(const key of ['items','shortages','unknown']){
    if(Array.isArray(result.reservations[key]))result.reservations[key]=this._v181LocalizeRows(result.reservations[key]);
   }
  }
  return result;
 }
 _renderTab(){
  const language=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  if(this._entryId&&this._v181UiCatalogKey!==this._v181CatalogKey(language)&&!this._v181UiCatalogLoading){
   queueMicrotask(()=>void this._v181LoadUiCatalog());
  }
  this._v181RelocalizeWeekState();
  const result=super._renderTab();
  this.setAttribute('data-cook4me-build','2026.9.22.8');
  return result;
 }
}
customElements.define('cook4me-recipe-hub-panel-v181',Cook4MeRecipeHubPanelV181);
