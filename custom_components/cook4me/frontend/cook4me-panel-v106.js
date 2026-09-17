import "./cook4me-panel-v105.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v105');
const TEXT={
 en:{sending:'Sending the original edition and checking whether Cook4Me loads it…',loaded:'Cook4Me loaded the original edition. The appliance may show the recipe in its original language.',offline:'Connect Cook4Me before sending an original-language edition. Delivery must be checked on the device.',notLoaded:'The cloud accepted the recipe, but Cook4Me has not confirmed loading it. Check the cooker screen. If it rejected this edition, use Cooking mode here and follow the recipe on the appliance manually.',failed:'The original edition could not be sent. Check that Cook4Me is online and has no active cooking session, then retry.'},
 de:{sending:'Die Originalausgabe wird gesendet und das Laden auf Cook4Me geprüft…',loaded:'Cook4Me hat die Originalausgabe geladen. Das Gerät zeigt das Rezept möglicherweise in der Originalsprache.',offline:'Cook4Me vor dem Senden einer fremdsprachigen Ausgabe verbinden. Das Laden muss am Gerät geprüft werden.',notLoaded:'Die Cloud hat das Rezept angenommen, aber Cook4Me hat das Laden nicht bestätigt. Prüfen Sie das Display. Falls das Gerät diese Ausgabe ablehnt, nutzen Sie hier den Kochmodus und führen Sie das Rezept am Gerät manuell aus.',failed:'Die Originalausgabe konnte nicht gesendet werden. Prüfen Sie die Verbindung und beenden Sie einen aktiven Kochvorgang, bevor Sie es erneut versuchen.'},
 el:{sending:'Αποστολή της αρχικής έκδοσης και έλεγχος φόρτωσης στο Cook4Me…',loaded:'Το Cook4Me φόρτωσε την αρχική έκδοση. Η συσκευή ενδέχεται να εμφανίζει τη συνταγή στην αρχική της γλώσσα.',offline:'Συνδέστε το Cook4Me πριν στείλετε έκδοση σε άλλη γλώσσα. Η φόρτωση πρέπει να επιβεβαιωθεί από τη συσκευή.',notLoaded:'Το cloud δέχτηκε τη συνταγή, αλλά το Cook4Me δεν επιβεβαίωσε τη φόρτωσή της. Ελέγξτε την οθόνη της συσκευής. Αν απέρριψε αυτή την έκδοση, χρησιμοποιήστε εδώ τη Λειτουργία μαγειρέματος και ακολουθήστε τη συνταγή χειροκίνητα στη συσκευή.',failed:'Δεν ήταν δυνατή η αποστολή της αρχικής έκδοσης. Ελέγξτε ότι το Cook4Me είναι συνδεδεμένο και δεν μαγειρεύει ήδη, και δοκιμάστε ξανά.'}
};
class Cook4MeRecipeHubPanelV106 extends BasePanel{
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.17.10');return result;}
 _v106Text(key){return (TEXT[this._uiIngredientLanguage()]||TEXT.en)[key]||key;}
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
    // preference. The server resolves its IDs and rechecks all dietary rules.
    const exact=String(original.displayVariantId||original.searchVariantId||'');
    if(exact!==String(variant)||!original.groupingFunctionalId||!original.recipeFunctionalId)throw new Error(this._t('deviceSendUnavailable'));
    delivery={...original,sendVariantId:exact,sendOriginalLanguage:true};
    this._message(this._v106Text('sending'));
   }
   recipe.match=original.match;
   this._renderTab();this._renderRecipeDialog();
   const result=await this._api('cook4me/v25/send_multi',{entry_id:target,entry_ids:[target],recipe:{...delivery,sendDiet:diet}});
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
customElements.define('cook4me-recipe-hub-panel-v106',Cook4MeRecipeHubPanelV106);
