import "./cook4me-panel-v107.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v107');
const TEXT={
 en:{waiting:'Waiting for Cook4Me to confirm the recipe (up to 90 seconds)…',unconfirmed:'The cloud accepted the recipe. Cook4Me has not confirmed loading it within 90 seconds; it may still appear. Check the cooker screen before sending again. No automatic retry is scheduled.'},
 de:{waiting:'Warten auf die Rezeptbestätigung von Cook4Me (bis zu 90 Sekunden)…',unconfirmed:'Die Cloud hat das Rezept angenommen. Cook4Me hat das Laden innerhalb von 90 Sekunden nicht bestätigt; es kann noch erscheinen. Vor erneutem Senden das Gerätedisplay prüfen. Es erfolgt kein automatischer Neuversuch.'},
 el:{waiting:'Αναμονή επιβεβαίωσης της συνταγής από το Cook4Me (έως 90 δευτερόλεπτα)…',unconfirmed:'Το cloud δέχτηκε τη συνταγή. Το Cook4Me δεν επιβεβαίωσε τη φόρτωση εντός 90 δευτερολέπτων· μπορεί να εμφανιστεί αργότερα. Ελέγξτε την οθόνη πριν την ξαναστείλετε. Δεν έχει προγραμματιστεί αυτόματη επανάληψη.'}
};
class Cook4MeRecipeHubPanelV108 extends BasePanel{
 _v108Text(key){return (TEXT[this._uiIngredientLanguage()]||TEXT.en)[key]||key;}
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.17.12');return result;}
 _processEnd(token){
  if(!token?.unconfirmed||token.cancelled||token.failed)return super._processEnd(token);
  if(token.ended)return;
  super._processEnd(token);
  if(token.removeTimer)clearTimeout(token.removeTimer);
  this._v59RenderProcess(token,token.detail,null,null);
  token.card?.classList.remove('bad','indeterminate');
  if(token.card)token.card.style.borderColor='var(--warning-color,#f0a000)';
  token.card?.querySelector('ha-icon')?.setAttribute('icon','mdi:clock-outline');
  const bar=token.card?.querySelector('.rx-v59-op-bar');if(bar){bar.style.width='100%';bar.style.background='var(--warning-color,#f0a000)';}
  token.removeTimer=setTimeout(()=>{token.card?.remove();if(this._process===token)this._process=null;},12000);
 }
 async _v66Send(recipe,target){
  const context=this._prefKey(),diet=this._filters()?.diet||'profile';
  const variant=recipe.displayVariantId||recipe.searchVariantId;
  const job=this._processStart(this._t('send'),recipe.title||'');
  try{
   if(!variant)throw new Error(this._t('deviceSendUnavailable'));
   const original=await this._api('cook4me/v31/recipe_detail',{entry_id:target,variant_id:String(variant),language:recipe.language,include_instructions:false});
   if(context!==this._prefKey()||diet!==(this._filters()?.diet||'profile')||variant!==(recipe.displayVariantId||recipe.searchVariantId))throw new Error(this._v76Text('changed'));
   if(!this._v77CanSend(original,target))throw new Error(this._t('deviceSendUnavailable'));
   const fallback=!original.sendVariantId;
   let delivery=original;
   if(fallback){
    // Only an exact official source publication may bypass the local language
    // preference. The server resolves its IDs and refreshes dietary guidance.
    const exact=String(original.displayVariantId||original.searchVariantId||'');
    if(exact!==String(variant)||!original.groupingFunctionalId||!original.recipeFunctionalId)throw new Error(this._t('deviceSendUnavailable'));
    delivery={...original,sendVariantId:exact,sendOriginalLanguage:true};
    this._message(this._v108Text('waiting'));
   }
   recipe.match=original.match;
   this._renderTab();this._renderRecipeDialog();
   this._processUpdate(job,this._v108Text('waiting'));
   const result=await this._api('cook4me/v25/send_multi',{entry_id:target,entry_ids:[target],recipe:{...delivery,sendDiet:diet}});
   if(result?.acceptedCount||result?.results?.some(row=>row.accepted&&row.reason==='device_confirmation_unavailable')){
    job.unconfirmed=true;job.detail=this._v108Text('unconfirmed');
    this._message(job.detail);await this._loadOverview(true);return;
   }
   if(!result?.sentCount&&!result?.queuedCount){
    const row=result?.results?.[0]||{};
    const key={original_language_offline:'offline',original_language_not_loaded:'notLoaded',original_language_send_failed:'failed'}[row.reason];
    throw new Error(key?this._v106Text(key)+(row.error?` (${row.error})`:''):row.error||this._t('deviceSendUnavailable'));
   }
   this._message(fallback?this._v106Text('loaded'):this._t(result.queuedCount?'sendQueued':'recipeSent'));
   await this._loadOverview(true);
  }catch(error){this._v59FailProcess(job,`${this._t('error')}: ${error.message||error}`);}finally{this._processEnd(job);}
 }
}
customElements.define('cook4me-recipe-hub-panel-v108',Cook4MeRecipeHubPanelV108);
