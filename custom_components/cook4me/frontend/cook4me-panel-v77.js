import "./cook4me-panel-v76.js";
const BasePanel=customElements.get("cook4me-recipe-hub-panel-v76");
const BUILD="2026.9.16.2";
const NOTES={
 en:"Use every replacement below. Send delivers the original recipe and cooking program to the cooker; follow these ingredient replacements yourself. The cooker’s instructions, cooking times and nutrition shown remain those of the original recipe. Adding the original ingredients to shopping remains disabled.",
 el:"Χρησιμοποιήστε όλες τις παρακάτω αντικαταστάσεις. Η Αποστολή στέλνει την αρχική συνταγή και το αρχικό πρόγραμμα μαγειρέματος στη συσκευή· εφαρμόστε εσείς τις αντικαταστάσεις υλικών. Οι οδηγίες της συσκευής, οι χρόνοι μαγειρέματος και οι διατροφικές τιμές παραμένουν της αρχικής συνταγής. Η προσθήκη των αρχικών υλικών στα ψώνια παραμένει απενεργοποιημένη.",
 de:"Alle folgenden Zutaten ersetzen. Senden überträgt das Originalrezept und das ursprüngliche Garprogramm an den Cook4Me; die Zutaten selbst wie vorgeschlagen ersetzen. Die Anweisungen am Gerät, Garzeiten und angezeigten Nährwerte gelten weiterhin für das Originalrezept. Die ursprünglichen Zutaten können weiterhin nicht zur Einkaufsliste hinzugefügt werden.",
};
class Cook4MeRecipeHubPanelV77 extends BasePanel{
 _v76Text(key){return key==="note"?(NOTES[this._uiIngredientLanguage()]||NOTES.en):super._v76Text(key);}
 _v77CanSend(recipe,target=this._entryId){
  if(!(recipe.displayVariantId||recipe.sendVariantId))return false;
  const match=recipe.match||{};
  if(match.safe===true)return true;
  const selected=this._filters()?.diet||"profile";
  const diet=selected==="profile"?(this._entries||[]).find(row=>row.entry_id===target)?.profile?.diet||"omnivore":selected;
  return match.dietCheckVersion===76&&match.diet===diet&&match.requiresSubstitutions===true&&match.eligibleWithSubstitutions===true&&match.substitutions?.length>0;
 }
 _v66Body(recipe,custom,state,slot=null){
  const node=this._v67Dom(super._v66Body(recipe,custom,state,slot));
  const send=node.querySelector('[data-v66-action="send"]');
  if(send)send.disabled=custom||!this._v77CanSend(recipe,state.device||this._entryId);
  return node.innerHTML;
 }
 async _v66Send(recipe,target){
  const context=this._prefKey(),diet=this._filters()?.diet||"profile";
  const variant=recipe.displayVariantId||recipe.searchVariantId;
  const job=this._processStart(this._t("send"),recipe.title||"");
  try{
   if(!variant)throw new Error(this._t("deviceSendUnavailable"));
   const original=await this._api("cook4me/v31/recipe_detail",{entry_id:target,variant_id:String(variant),language:recipe.language,include_instructions:false});
   if(context!==this._prefKey()||diet!==(this._filters()?.diet||"profile")||variant!==(recipe.displayVariantId||recipe.searchVariantId))throw new Error(this._v76Text("changed"));
   if(!original.sendVariantId||!this._v77CanSend(original,target))throw new Error(this._t("deviceSendUnavailable"));
   // Show the freshly checked replacements for the selected device. Preserve
   // the displayed edition and its translated instructions.
   recipe.match=original.match;
   this._renderTab();this._renderRecipeDialog();
   const result=await this._api("cook4me/v25/send_multi",{entry_id:target,entry_ids:[target],recipe:{...original,sendDiet:diet}});
   if(!result?.sentCount&&!result?.queuedCount)throw new Error(result?.results?.[0]?.error||this._t("deviceSendUnavailable"));
   this._message(this._t(result.queuedCount?"sendQueued":"recipeSent"));await this._loadOverview(true);
  }catch(error){this._v59FailProcess(job,`${this._t("error")}: ${error.message||error}`);}finally{this._processEnd(job);}
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build',BUILD);return result;}
}
customElements.define("cook4me-recipe-hub-panel-v77",Cook4MeRecipeHubPanelV77);
