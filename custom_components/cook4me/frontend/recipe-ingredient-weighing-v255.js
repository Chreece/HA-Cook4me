const TEXT={
 en:{weigh:'Weigh',save:'Save weight',cancel:'Cancel',saved:'Weight saved',deducted:'Stock deducted',unlimited:'Unlimited stock unchanged',unassigned:'No assigned stock; weight saved',notDeducted:'Weight saved; assigned stock could not be deducted automatically'},
 de:{weigh:'Wiegen',save:'Gewicht speichern',cancel:'Abbrechen',saved:'Gewicht gespeichert',deducted:'Vom Vorrat abgezogen',unlimited:'Unbegrenzter Vorrat bleibt unverändert',unassigned:'Kein Vorrat zugeordnet; Gewicht gespeichert',notDeducted:'Gewicht gespeichert; der zugeordnete Vorrat konnte nicht automatisch abgezogen werden'},
 el:{weigh:'Ζύγισμα',save:'Αποθήκευση βάρους',cancel:'Ακύρωση',saved:'Το βάρος αποθηκεύτηκε',deducted:'Αφαιρέθηκε από το απόθεμα',unlimited:'Το απεριόριστο απόθεμα παραμένει αμετάβλητο',unassigned:'Δεν έχει αντιστοιχιστεί απόθεμα· το βάρος αποθηκεύτηκε',notDeducted:'Το βάρος αποθηκεύτηκε· το αντιστοιχισμένο απόθεμα δεν μπόρεσε να αφαιρεθεί αυτόματα'}
};

export const RecipeIngredientWeighingMixin=Base=>class extends Base{
 _v255Text(key){
  const lang=String(this._uiIngredientLanguage?.()||this._langCode?.()||'en').split(/[-_]/)[0];
  return (TEXT[lang]||TEXT.en)[key]||TEXT.en[key]||key;
 }
 _v255RecipeKey(recipe){
  return String(this._recipeKey?.(recipe)||recipe?.groupingFunctionalId||recipe?.recipeFunctionalId||recipe?.variantFunctionalId||recipe?.id||recipe?.title||'recipe');
 }
 _v255State(recipe,index){
  this._v255States??=new Map();
  const key=`${this._prefKey?.()||this._entryId||''}:${this._v255RecipeKey(recipe)}:${index}`;
  if(!this._v255States.has(key))this._v255States.set(key,{active:false,saving:false,requestId:''});
  return this._v255States.get(key);
 }
 _v255Measurement(index){
  return (this._v116Session?.measurements||[]).find(row=>Number(row?.ingredientIndex)===Number(index))||null;
 }
 _v255RequestId(){
  if(globalThis.crypto?.randomUUID)return globalThis.crypto.randomUUID();
  this._v255RequestCounter=(this._v255RequestCounter||0)+1;
  return `weigh-${Date.now()}-${this._v255RequestCounter}-cook4me`;
 }
 _v255RemoveLegacyWeighing(recipe){
  const overlay=this._v63RecipeDialog;if(!overlay)return;
  overlay.querySelector('[data-v118-weighing]')?.remove();
  overlay.querySelector('[data-v116-recipe]')?.remove();
  this._v66State?.(recipe)?.sections?.delete?.('weighing');
 }
 _v255PaintControl(control,recipe,index){
  const state=this._v255State(recipe,index),measurement=this._v255Measurement(index);
  const amount=control.querySelector('[data-v255-amount]'),start=control.querySelector('[data-v255-start]');
  const save=control.querySelector('[data-v255-save]'),cancel=control.querySelector('[data-v255-cancel]');
  if(state.active){
   amount?.setAttribute('data-v116-live','');
   const reading=this._v116Reading?.();
   if(amount)amount.textContent=reading?`${this._v116Num(reading.net)} g`:(this._v116Text?.('off')||'—');
   start.hidden=true;save.hidden=false;cancel.hidden=false;save.disabled=state.saving;cancel.disabled=state.saving;
  }else{
   amount?.removeAttribute('data-v116-live');
   if(amount)amount.textContent=measurement&&Number.isFinite(Number(measurement.grams))?`${this._v116Num(measurement.grams)} g`:'';
   start.hidden=false;save.hidden=true;cancel.hidden=true;start.disabled=false;
  }
 }
 _v255Message(deduction){
  if(deduction?.deducted){
   return `${this._v255Text('saved')} · ${this._v255Text('deducted')}: ${this._v116Num(deduction.deductedGrams)} g`;
  }
  if(deduction?.assigned&&deduction?.reason==='unlimited')return `${this._v255Text('saved')} · ${this._v255Text('unlimited')}`;
  if(deduction?.assigned)return this._v255Text('notDeducted');
  return this._v255Text('unassigned');
 }
 _v255BindControl(control,recipe,index){
  if(control._v255Bound)return;control._v255Bound=true;
  const state=this._v255State(recipe,index),raw=recipe.ingredients?.[index];
  control.querySelector('[data-v255-start]')?.addEventListener('click',async event=>{
   event.stopPropagation();
   state.active=true;state.saving=false;state.requestId=this._v255RequestId();
   this._v255PaintControl(control,recipe,index);
   await this._v116Load?.(recipe);
   if(this._v63RecipeDialog?.contains(control)){
    this._v255PaintControl(control,recipe,index);
    this._v116Live?.();
   }
  });
  control.querySelector('[data-v255-cancel]')?.addEventListener('click',event=>{
   event.stopPropagation();
   if(state.saving)return;
   state.active=false;state.requestId='';
   this._v255PaintControl(control,recipe,index);
  });
  control.querySelector('[data-v255-save]')?.addEventListener('click',async event=>{
   event.stopPropagation();
   if(state.saving)return;
   const grams=this._v116Net?.({stable:true});
   if(grams===null||grams===undefined||Number(grams)<=0)return;
   state.saving=true;this._v255PaintControl(control,recipe,index);
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
    if(Array.isArray(result?.houseIngredients)){
     this._houseIngredients=result.houseIngredients;
     const entry=this._entry?.();if(entry?.profile)entry.profile.houseIngredients=this._houseIngredients;
     this._syncEntryProfile?.();
     this._foodState=null;
    }
    state.active=false;state.saving=false;state.requestId='';
    this._v255PaintControl(control,recipe,index);
    this._message(this._v255Message(result?.deduction||{}));
   }catch(error){
    state.saving=false;this._v255PaintControl(control,recipe,index);
    this._message(String(error?.message||error),true);
   }
  });
 }
 _v255DecorateIngredients(recipe){
  const overlay=this._v63RecipeDialog;if(!overlay||!recipe?.ingredients?.length)return;
  for(const button of overlay.querySelectorAll('[data-v66-ingredient]')){
   const index=Number(button.dataset.v66Ingredient);if(!Number.isInteger(index))continue;
   const row=button.closest('li');if(!row)continue;
   let control=row.querySelector('[data-v255-weigh-control]');
   if(!control){
    control=document.createElement('div');control.dataset.v255WeighControl='';control.className='v255-weigh-control';
    const amount=document.createElement('strong');amount.dataset.v255Amount='';amount.className='v255-weigh-amount';
    const start=document.createElement('button');start.type='button';start.className='btn secondary';start.dataset.v255Start='';start.textContent=`⚖ ${this._v255Text('weigh')}`;
    const save=document.createElement('button');save.type='button';save.className='btn';save.dataset.v255Save='';save.textContent=this._v255Text('save');
    const cancel=document.createElement('button');cancel.type='button';cancel.className='btn secondary';cancel.dataset.v255Cancel='';cancel.textContent=this._v255Text('cancel');
    control.append(amount,start,save,cancel);row.append(control);
   }
   this._v255BindControl(control,recipe,index);
   this._v255PaintControl(control,recipe,index);
  }
  this._v255Styles();
  this._v116Live?.();
 }
 _renderRecipeDialog(){
  const result=super._renderRecipeDialog();
  const recipe=this._opened;
  if(recipe){
   this._v255RemoveLegacyWeighing(recipe);
   this._v255DecorateIngredients(recipe);
  }
  return result;
 }
 _v255Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v255IngredientWeighingStyles'))return;
  const style=document.createElement('style');style.id='v255IngredientWeighingStyles';style.textContent=`
   .rx-v66-ingredients li{display:grid;grid-template-columns:minmax(0,1fr);gap:6px}
   .v255-weigh-control{display:flex;align-items:center;justify-content:flex-end;gap:7px;flex-wrap:wrap;padding:0 0 6px}
   .v255-weigh-amount{min-width:58px;text-align:right;font-variant-numeric:tabular-nums}
   .v255-weigh-control .btn{min-height:38px;padding:7px 10px}
   @media(max-width:520px){.v255-weigh-control{justify-content:flex-start}.v255-weigh-amount{min-width:0;margin-right:auto}}
  `;this.shadowRoot.append(style);
 }
};
