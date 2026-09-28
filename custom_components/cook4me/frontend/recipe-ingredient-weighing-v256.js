const TEXT={
 en:{weigh:'Weigh',save:'Save weight',cancel:'Cancel',remove:'Remove saved weight',saved:'Weight saved',removed:'Saved weight removed',deducted:'Stock deducted',restored:'Stock restored',unlimited:'Unlimited stock unchanged',unassigned:'No assigned stock; weight saved',notDeducted:'Weight saved; assigned stock could not be deducted automatically'},
 de:{weigh:'Wiegen',save:'Gewicht speichern',cancel:'Abbrechen',remove:'Gespeichertes Gewicht entfernen',saved:'Gewicht gespeichert',removed:'Gespeichertes Gewicht entfernt',deducted:'Vom Vorrat abgezogen',restored:'Vorrat wiederhergestellt',unlimited:'Unbegrenzter Vorrat bleibt unverändert',unassigned:'Kein Vorrat zugeordnet; Gewicht gespeichert',notDeducted:'Gewicht gespeichert; der zugeordnete Vorrat konnte nicht automatisch abgezogen werden'},
 el:{weigh:'Ζύγισμα',save:'Αποθήκευση βάρους',cancel:'Ακύρωση',remove:'Αφαίρεση αποθηκευμένου βάρους',saved:'Το βάρος αποθηκεύτηκε',removed:'Το αποθηκευμένο βάρος αφαιρέθηκε',deducted:'Αφαιρέθηκε από το απόθεμα',restored:'Το απόθεμα επαναφέρθηκε',unlimited:'Το απεριόριστο απόθεμα παραμένει αμετάβλητο',unassigned:'Δεν έχει αντιστοιχιστεί απόθεμα· το βάρος αποθηκεύτηκε',notDeducted:'Το βάρος αποθηκεύτηκε· το αντιστοιχισμένο απόθεμα δεν μπόρεσε να αφαιρεθεί αυτόματα'}
};

export const RecipeIngredientWeighingMixin=Base=>class extends Base{
 _v256Text(key){
  const lang=String(this._uiIngredientLanguage?.()||this._langCode?.()||'en').split(/[-_]/)[0];
  return (TEXT[lang]||TEXT.en)[key]||TEXT.en[key]||key;
 }
 _v256RecipeKey(recipe){
  return String(this._recipeKey?.(recipe)||recipe?.groupingFunctionalId||recipe?.recipeFunctionalId||recipe?.variantFunctionalId||recipe?.id||recipe?.title||'recipe');
 }
 _v256State(recipe,index){
  this._v256States??=new Map();
  const key=`${this._prefKey?.()||this._entryId||''}:${this._v256RecipeKey(recipe)}:${index}`;
  if(!this._v256States.has(key))this._v256States.set(key,{active:false,busy:false,requestId:''});
  return this._v256States.get(key);
 }
 _v256Measurement(index){
  return (this._v116Session?.measurements||[]).find(row=>Number(row?.ingredientIndex)===Number(index))||null;
 }
 _v256RequestId(){
  if(globalThis.crypto?.randomUUID)return globalThis.crypto.randomUUID();
  this._v256RequestCounter=(this._v256RequestCounter||0)+1;
  return `weigh-${Date.now()}-${this._v256RequestCounter}-cook4me`;
 }
 _v256LiveReading(){
  const reading=this._v116Reading?.()||null;
  const connected=this._v116Connected?.();
  return reading&&connected!==false?reading:null;
 }
 _v256RemoveLegacyWeighing(recipe){
  const overlay=this._v63RecipeDialog;if(!overlay)return;
  overlay.querySelector('[data-v118-weighing]')?.remove();
  overlay.querySelector('[data-v116-recipe]')?.remove();
  this._v66State?.(recipe)?.sections?.delete?.('weighing');
 }
 _v256Show(node,show){
  if(!node)return;
  node.hidden=!show;
  node.setAttribute('aria-hidden',show?'false':'true');
 }
 _v256PaintControl(control,recipe,index){
  const state=this._v256State(recipe,index),measurement=this._v256Measurement(index);
  const reading=this._v256LiveReading();
  const savedGrams=Number(measurement?.grams);
  const hasSaved=Number.isFinite(savedGrams)&&savedGrams>0;
  const activeLive=state.active&&!!reading;
  const idle=!state.active;
  const start=control.querySelector('[data-v256-start]');
  const save=control.querySelector('[data-v256-save]');
  const cancel=control.querySelector('[data-v256-cancel]');
  const amount=control.querySelector('[data-v256-amount]');
  const saveValue=control.querySelector('[data-v256-save-value]');

  const showStart=idle&&!!reading;
  const showSave=activeLive;
  const showSaved=idle&&hasSaved;
  const showCancel=activeLive||showSaved;

  this._v256Show(start,showStart);
  this._v256Show(save,showSave);
  this._v256Show(cancel,showCancel);
  this._v256Show(amount,showSaved);
  control.hidden=!(showStart||showSave||showSaved||showCancel);

  if(showSave){
   const value=`${this._v116Num(reading.net)} g`;
   if(saveValue)saveValue.textContent=value;
   save.setAttribute('aria-label',`${this._v256Text('save')}: ${value}`);
   save.title=`${this._v256Text('save')}: ${value}`;
  }
  if(amount)amount.textContent=showSaved?`${this._v116Num(savedGrams)} g`:'';
  if(start){
   start.disabled=state.busy;
   start.title=this._v256Text('weigh');
   start.setAttribute('aria-label',this._v256Text('weigh'));
  }
  if(save)save.disabled=state.busy;
  if(cancel){
   cancel.disabled=state.busy;
   const label=activeLive?this._v256Text('cancel'):this._v256Text('remove');
   cancel.title=label;cancel.setAttribute('aria-label',label);
  }
 }
 _v116Live(){
  const result=super._v116Live?.();
  const recipe=this._opened;
  if(recipe&&this._v63RecipeDialog){
   this._v63RecipeDialog.querySelectorAll('[data-v256-weigh-control]').forEach(control=>{
    const row=control.closest('li'),button=row?.querySelector('[data-v66-ingredient]');
    const index=Number(button?.dataset?.v66Ingredient);
    if(Number.isInteger(index))this._v256PaintControl(control,recipe,index);
   });
  }
  return result;
 }
 _v256Message(deduction){
  if(deduction?.deducted){
   return `${this._v256Text('saved')} · ${this._v256Text('deducted')}: ${this._v116Num(deduction.deductedGrams)} g`;
  }
  if(deduction?.assigned&&deduction?.reason==='unlimited')return `${this._v256Text('saved')} · ${this._v256Text('unlimited')}`;
  if(deduction?.assigned)return this._v256Text('notDeducted');
  return this._v256Text('unassigned');
 }
 _v256UpdateHouse(result){
  if(!Array.isArray(result?.houseIngredients))return;
  this._houseIngredients=result.houseIngredients;
  const entry=this._entry?.();if(entry?.profile)entry.profile.houseIngredients=this._houseIngredients;
  this._syncEntryProfile?.();
  this._foodState=null;
 }
 _v256BindControl(control,recipe,index){
  if(control._v256Bound)return;control._v256Bound=true;
  const state=this._v256State(recipe,index),raw=recipe.ingredients?.[index];

  control.querySelector('[data-v256-start]')?.addEventListener('click',event=>{
   event.stopPropagation();
   if(state.busy||!this._v256LiveReading())return;
   state.active=true;state.requestId=this._v256RequestId();
   this._v256PaintControl(control,recipe,index);
  });

  control.querySelector('[data-v256-cancel]')?.addEventListener('click',async event=>{
   event.stopPropagation();
   if(state.busy)return;
   if(state.active){
    state.active=false;state.requestId='';
    this._v256PaintControl(control,recipe,index);
    return;
   }
   if(!this._v256Measurement(index))return;
   state.busy=true;this._v256PaintControl(control,recipe,index);
   try{
    const result=await this._api('cook4me/v37/ingredient_weight_cancel',{
     entry_id:this._entryId,
     recipe,
     ingredient_index:index,
    });
    this._v116Session=result?.session||null;
    this._v116Scale={...(this._v116Scale||{}),...(result||{}),session:this._v116Session};
    this._v256UpdateHouse(result);
    state.busy=false;state.active=false;state.requestId='';
    this._v256PaintControl(control,recipe,index);
    const restored=result?.cancellation?.receipt?.cancelRestore?.restored;
    this._message(restored?.length?`${this._v256Text('removed')} · ${this._v256Text('restored')}`:this._v256Text('removed'));
   }catch(error){
    state.busy=false;this._v256PaintControl(control,recipe,index);
    this._message(String(error?.message||error),true);
   }
  });

  control.querySelector('[data-v256-save]')?.addEventListener('click',async event=>{
   event.stopPropagation();
   if(state.busy||!state.active)return;
   const grams=this._v116Net?.({stable:true});
   if(grams===null||grams===undefined||Number(grams)<=0)return;
   state.busy=true;this._v256PaintControl(control,recipe,index);
   try{
    const result=await this._api('cook4me/v37/ingredient_weight_commit',{
     entry_id:this._entryId,
     request_id:state.requestId,
     recipe,
     ingredient_index:index,
     ingredient:raw&&typeof raw==='object'?raw:{name:String(raw||'')},
     grams:Number(grams),
    });
    this._v116Session=result?.session||this._v116Session;
    this._v116Scale={...(this._v116Scale||{}),...(result||{}),session:this._v116Session};
    this._v256UpdateHouse(result);
    state.active=false;state.busy=false;state.requestId='';
    this._v256PaintControl(control,recipe,index);
    this._message(this._v256Message(result?.deduction||{}));
   }catch(error){
    state.busy=false;this._v256PaintControl(control,recipe,index);
    this._message(String(error?.message||error),true);
   }
  });
 }
 _v256DecorateIngredients(recipe){
  const overlay=this._v63RecipeDialog;if(!overlay||!recipe?.ingredients?.length)return;
  for(const button of overlay.querySelectorAll('[data-v66-ingredient]')){
   const index=Number(button.dataset.v66Ingredient);if(!Number.isInteger(index))continue;
   const row=button.closest('li');if(!row)continue;
   row.classList.add('v256-ingredient-row');
   button.classList.add('v256-ingredient-main');

   let meta=row.querySelector('[data-v256-meta]');
   if(!meta){
    meta=document.createElement('div');meta.dataset.v256Meta='';meta.className='v256-ingredient-meta';
    const coverage=[...button.children].find(node=>node.classList?.contains('chip'));
    const price=button.querySelector('[data-v79-item]');
    if(price){price.classList.add('v256-ingredient-price');meta.append(price);}
    if(coverage){coverage.classList.add('v256-ingredient-coverage');meta.append(coverage);}
    button.after(meta);
   }else{
    const price=button.querySelector('[data-v79-item]');
    if(price&&!meta.contains(price)){price.classList.add('v256-ingredient-price');meta.prepend(price);}
   }

   let control=row.querySelector('[data-v256-weigh-control]');
   if(!control){
    control=document.createElement('div');control.dataset.v256WeighControl='';control.className='v256-weigh-control';

    const start=document.createElement('button');
    start.type='button';start.className='btn secondary v256-icon-button';start.dataset.v256Start='';
    start.innerHTML='<ha-icon icon="mdi:scale-balance" aria-hidden="true"></ha-icon>';

    const save=document.createElement('button');
    save.type='button';save.className='btn v256-save-button';save.dataset.v256Save='';
    save.innerHTML='<ha-icon icon="mdi:content-save" aria-hidden="true"></ha-icon><span data-v256-save-value></span>';

    const amount=document.createElement('strong');
    amount.dataset.v256Amount='';amount.className='v256-weigh-amount';

    const cancel=document.createElement('button');
    cancel.type='button';cancel.className='btn secondary v256-icon-button';cancel.dataset.v256Cancel='';
    cancel.innerHTML='<ha-icon icon="mdi:close" aria-hidden="true"></ha-icon>';

    control.append(start,save,amount,cancel);row.append(control);
   }
   this._v256BindControl(control,recipe,index);
   this._v256PaintControl(control,recipe,index);
  }
  this._v256Styles();
  this._v116Live?.();
 }
 _v256PatchNutrition(recipe){
  const info=this._v63RecipeDialog?.querySelector('[data-v66-section="info"] > .rx-v66-section');
  if(!info)return;
  info.querySelectorAll('[data-v60-nutrition]').forEach(node=>node.remove());
  const html=this._v60NutritionChips?.(recipe)||'';
  if(!html)return;
  const holder=document.createElement('div');holder.innerHTML=html;
  const before=[...info.children].find(node=>node.tagName==='P')||null;
  [...holder.children].forEach(node=>info.insertBefore(node,before));
 }
 async _loadRecipeNutrition(recipe){
  const previous=this._v256NutritionPatchRecipe;
  this._v256NutritionPatchRecipe=recipe;
  try{return await super._loadRecipeNutrition(recipe);}
  finally{
   if(this._v256NutritionPatchRecipe===recipe)this._v256NutritionPatchRecipe=previous||null;
   if(this._opened===recipe&&this._v63RecipeDialog){
    this._v256PatchNutrition(recipe);
    this._v256DecorateIngredients(recipe);
   }
  }
 }
 async _showRecipe(...args){
  const content=this.shadowRoot?.getElementById('content')||null;
  const scrollTop=content?.scrollTop??0,scrollLeft=content?.scrollLeft??0;
  this._v256OpeningRecipe=true;
  let result;
  try{result=await super._showRecipe(...args);}
  finally{
   this._v256OpeningRecipe=false;
   this._v63RecipeDialog?.removeAttribute('data-v256-preparing');
  }
  const close=this._v63CloseRecipe;
  if(close&&!close._v256StableClose){
   const restore=()=>{
    if(content?.isConnected){content.scrollTop=scrollTop;content.scrollLeft=scrollLeft;}
   };
   const wrapped=()=>{
    close();
    restore();
    globalThis.requestAnimationFrame?.(restore);
   };
   wrapped._v256StableClose=true;
   this._v63CloseRecipe=wrapped;
  }
  return result;
 }
 _renderRecipeDialog(){
  const recipe=this._opened;
  if(recipe&&this._v256NutritionPatchRecipe===recipe&&this._v63RecipeDialog){
   this._v256PatchNutrition(recipe);
   return;
  }
  const result=super._renderRecipeDialog();
  if(this._v256OpeningRecipe&&this._v63RecipeDialog)this._v63RecipeDialog.setAttribute('data-v256-preparing','');
  if(recipe){
   this._v256RemoveLegacyWeighing(recipe);
   this._v256DecorateIngredients(recipe);
  }
  return result;
 }
 _v256Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v256IngredientWeighingStyles'))return;
  const style=document.createElement('style');style.id='v256IngredientWeighingStyles';style.textContent=`
   [data-recipe-dialog][data-v256-preparing]{visibility:hidden!important}
   .rx-v66-ingredients{display:grid;gap:8px}
   .rx-v66-ingredients .v256-ingredient-row{display:grid;grid-template-columns:minmax(0,1fr) auto auto;align-items:center;gap:9px;padding:8px 9px;border:1px solid var(--divider-color);border-radius:12px;background:color-mix(in srgb,var(--card-background-color) 94%,var(--primary-color) 6%)}
   .rx-v66-ingredients .v256-ingredient-main{min-width:0;width:100%;border:0!important;background:transparent!important;border-radius:8px!important;padding:4px 5px!important;box-shadow:none!important}
   .rx-v66-ingredients .v256-ingredient-main>span:first-child{min-width:0}
   .v256-ingredient-meta{display:flex;align-items:center;justify-content:flex-end;gap:7px;white-space:nowrap}
   .v256-ingredient-price{display:inline-flex!important;align-items:center;margin:0!important;padding:5px 8px;border-radius:999px;background:color-mix(in srgb,var(--primary-color) 10%,transparent);color:var(--primary-color)!important;font-size:12px!important;font-weight:650;line-height:1.2}
   .v256-ingredient-price:empty{display:none!important}
   .v256-ingredient-coverage{margin:0;flex:0 0 auto}
   .v256-weigh-control{display:flex;align-items:center;justify-content:flex-end;gap:6px;flex-wrap:nowrap;padding:0}
   .v256-weigh-control[hidden],.v256-weigh-control [hidden]{display:none!important}
   .v256-weigh-control .btn{min-width:38px;width:auto;min-height:38px;padding:7px 9px;white-space:nowrap}
   .v256-icon-button{width:38px!important;padding:7px!important}
   .v256-weigh-control ha-icon{--mdc-icon-size:20px;display:block}
   .v256-save-button{display:inline-flex;align-items:center;gap:6px}
   .v256-weigh-amount{display:inline-flex;align-items:center;padding:5px 8px;border-radius:999px;background:color-mix(in srgb,var(--primary-color) 9%,transparent);font-variant-numeric:tabular-nums;white-space:nowrap}
   @media(max-width:760px){
    .rx-v66-ingredients .v256-ingredient-row{grid-template-columns:minmax(0,1fr) auto}
    .v256-ingredient-meta{grid-column:2;grid-row:1}
    .v256-weigh-control{grid-column:1/-1;grid-row:2;justify-content:flex-end;padding-top:2px}
   }
   @media(max-width:520px){
    .rx-v66-ingredients .v256-ingredient-row{grid-template-columns:minmax(0,1fr);gap:7px}
    .v256-ingredient-meta{grid-column:1;grid-row:2;justify-content:flex-start;flex-wrap:wrap}
    .v256-weigh-control{grid-column:1;grid-row:3;justify-content:flex-start;flex-wrap:wrap}
   }
  `;this.shadowRoot.append(style);
 }
};
