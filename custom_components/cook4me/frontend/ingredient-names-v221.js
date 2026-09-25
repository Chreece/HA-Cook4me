// Presentation only: never change ingredient identity, recipe text or quantities.
const text=value=>String(value??'').trim();
const language=value=>text(value).toLowerCase().replaceAll('_','-').split('-')[0];
const same=value=>text(value).normalize('NFC').replace(/\s+/g,' ').toLocaleLowerCase();

export function ingredientNameParts(uiName,marketName,recipeName){
 const primary=text(uiName)||text(recipeName)||text(marketName),alternatives=[];
 const seen=new Set([same(primary)]);
 for(const candidate of [marketName,recipeName]){
  const name=text(candidate),key=same(name);
  if(name&&!seen.has(key)){alternatives.push(name);seen.add(key);}
 }
 return {primary,alternatives,label:primary+(alternatives.length?` (${alternatives.join(', ')})`:'')};
}

export const IngredientNamesMixin=Base=>class extends Base{
 _v221Source(item,recipe){
  if(item&&typeof item==='object')return item;
  const displayed=recipe?.ingredients,originals=recipe?._nutritionIngredients;
  const index=Array.isArray(displayed)?displayed.indexOf(item):-1;
  // Translated text may carry its original stable identity in a parallel list.
  if(index>=0&&index===displayed.lastIndexOf(item)&&originals?.length===displayed.length
    &&originals[index]&&typeof originals[index]==='object')return originals[index];
  return {name:text(item)};
 }
 _v221IngredientNames(item,recipe,info=null){
  const source=this._v221Source(item,recipe),ui=language(this._uiIngredientLanguage());
  const identity=text(source.identity),key=/^[ki]:/.test(identity)?identity.slice(2):identity;
  const lookup=key&&!source.key&&!source.ingredientId&&!source.foodKey?{...source,key}:source;
  let ids=this._v218ExpandedIds(lookup);
  if(!ids.size&&info?.ingredient)ids=this._v218ExpandedIds(info.ingredient);
  const currentCatalog=language(this._ingredientCatalogLanguage)===ui;
  const index=currentCatalog?this._v219IdentityIndex().localizedRows:null;
  let catalogRow;
  if(index)for(const id of ids){if(index.has(id)){catalogRow=index.get(id);break;}}
  const original=text(source.originalName||source.name||source.foodName||source.applicationDescription||source.applianceDescription);
  const presented=language(source.displayLanguage)===ui?source.displayName:'';
  const uiName=presented||(info?.language===ui?info.name:'')||catalogRow?.name||original;
  const marketKey=`${this._prefKey()}:${this._v140SupermarketLanguage()}`;
  let marketName='';
  if(this._v140MarketCatalogKey===marketKey){
   for(const id of ids){const name=this._v140MarketNames?.get(id);if(name){marketName=name;break;}}
  }
  return ingredientNameParts(uiName,marketName,original);
 }
 _v221DecorateIngredients(container,recipe){
  const buttons=container?.querySelectorAll?.('[data-v66-ingredient]')||[];
  for(const button of buttons){
   const item=recipe?.ingredients?.[Number(button.dataset.v66Ingredient)];
   if(item===undefined)continue;
   const holder=button.querySelector(':scope > span:first-child');if(!holder)continue;
   const parts=this._v221IngredientNames(item,recipe);
   if(holder.querySelector('[data-v221-ingredient-name]')?.textContent===parts.label)continue;
   const retained=[...holder.querySelectorAll('.rx-v66-quantity,.v218-stored-at')];
   const name=document.createElement('span');name.dataset.v221IngredientName='';
   name.append(document.createTextNode(parts.primary));
   if(parts.alternatives.length){
    const extra=document.createElement('small');extra.textContent=` (${parts.alternatives.join(', ')})`;name.append(extra);
   }
   holder.replaceChildren(name,...retained);
  }
 }
 _v66BindRecipe(container,recipe,...args){
  const result=super._v66BindRecipe(container,recipe,...args);
  this._v221DecorateIngredients(container,recipe);
  const key=`${this._prefKey()}:${this._uiIngredientLanguage()}`;
  if(container?.querySelector('[data-v66-ingredient]')&&this._v221CatalogRequested!==key){
   this._v221CatalogRequested=key;queueMicrotask(()=>void this._loadIngredientCatalog());
  }
  return result;
 }
 _v221RefreshNames(){
  for(const card of this.shadowRoot?.querySelectorAll?.('[data-v66-ref]')||[]){
   const recipe=this._v66Refs?.get(card.dataset.v66Ref)?.recipe;
   if(recipe)this._v221DecorateIngredients(card,recipe);
  }
  if(this._v63RecipeDialog?.isConnected&&this._opened)this._v221DecorateIngredients(this._v63RecipeDialog,this._opened);
  const current=this._v221IngredientInfo;
  if(current?.overlay.isConnected&&current.context===this._prefKey()){
   const heading=current.overlay.querySelector('.detail-head h2');
   if(heading)heading.textContent=`🥕 ${this._v221IngredientNames(current.item,current.recipe,current.info).label}`;
  }
 }
 async _showIngredientInfo(item,recipe){
  const context=this._prefKey(),ui=language(this._uiIngredientLanguage());
  const before=this.shadowRoot?.querySelector('[data-ingredient-dialog]');
  const request={};this._v221InfoRequest=request;
  const result=await super._showIngredientInfo(item,recipe);
  if(this._v221InfoRequest!==request||context!==this._prefKey())return result;
  const overlay=this.shadowRoot?.querySelector('[data-ingredient-dialog]');
  if(!overlay||overlay===before)return result;
  const ingredient=this._v66IngredientInfo?.ingredient;
  this._v221IngredientInfo={context,overlay,item,recipe,info:{language:ui,name:ingredient?.name,ingredient}};
  this._v221RefreshNames();
  // Both reads use the existing deduplicated, offline HA catalog loaders.
  void this._loadIngredientCatalog();void this._v140LoadSupermarketCatalog();
  return result;
 }
 async _loadIngredientCatalog(...args){
  const result=await super._loadIngredientCatalog(...args);
  this._v221RefreshNames();return result;
 }
 async _v140LoadSupermarketCatalog(...args){
  const result=await super._v140LoadSupermarketCatalog(...args);
  this._v221RefreshNames();return result;
 }
};
