import "./cook4me-panel-v74.js";
const BasePanel=customElements.get("cook4me-recipe-hub-panel-v74");
const BUILD="2026.9.16.1";
const TEXT={
 en:{changes:"Requires ingredient replacements",note:"Use every replacement below. Cooking times and nutrition shown belong to the original recipe. Sending the original recipe and adding its ingredients to shopping are disabled.",refresh:"Refresh these recipes to check them against the selected diet.",changed:"The diet changed. Open the recipe again.",tofu:"Firm tofu",mushrooms:"Mushrooms",chickpeas:"Chickpeas",stock:"Vegetable stock",cream:"Oat cream",milk:"Oat milk",oil:"Olive oil",yogurt:"Soy yogurt",sauce:"Soy sauce",sweetener:"Maple syrup"},
 el:{changes:"Απαιτούνται αντικαταστάσεις υλικών",note:"Χρησιμοποιήστε όλες τις παρακάτω αντικαταστάσεις. Οι χρόνοι μαγειρέματος και οι διατροφικές τιμές αφορούν την αρχική συνταγή. Η αποστολή της και η προσθήκη των αρχικών υλικών στα ψώνια είναι απενεργοποιημένες.",refresh:"Ανανεώστε τις συνταγές για έλεγχο με την επιλεγμένη διατροφή.",changed:"Η διατροφή άλλαξε. Ανοίξτε ξανά τη συνταγή.",tofu:"Σφιχτό τόφου",mushrooms:"Μανιτάρια",chickpeas:"Ρεβίθια",stock:"Ζωμός λαχανικών",cream:"Κρέμα βρώμης",milk:"Γάλα βρώμης",oil:"Ελαιόλαδο",yogurt:"Γιαούρτι σόγιας",sauce:"Σάλτσα σόγιας",sweetener:"Σιρόπι σφενδάμου"},
 de:{changes:"Zutaten müssen ersetzt werden",note:"Alle folgenden Zutaten ersetzen. Garzeiten und Nährwerte gelten für das Originalrezept. Das Senden und die Übernahme der ursprünglichen Zutaten in die Einkaufsliste sind deaktiviert.",refresh:"Rezepte aktualisieren, um sie mit der gewählten Ernährung zu prüfen.",changed:"Die Ernährung wurde geändert. Rezept erneut öffnen.",tofu:"Fester Tofu",mushrooms:"Pilze",chickpeas:"Kichererbsen",stock:"Gemüsebrühe",cream:"Hafercreme",milk:"Hafermilch",oil:"Olivenöl",yogurt:"Sojajoghurt",sauce:"Sojasauce",sweetener:"Ahornsirup"},
};
class Cook4MeRecipeHubPanelV76 extends BasePanel{
 _v76Text(key){return (TEXT[this._uiIngredientLanguage()]||TEXT.en)[key]||TEXT.en[key]||key;}
 _v76Diet(){const diet=this._filters()?.diet;return diet&&diet!=="profile"?diet:(this._entries||[]).find(row=>row.entry_id===this._entryId)?.profile?.diet||"omnivore";}
 _v76Allowed(recipe){
  const diet=this._v76Diet();if(!["vegetarian","vegan","pescatarian"].includes(diet))return true;
  const match=recipe.match||{};
  return match.dietCheckVersion===76&&match.diet===diet&&(match.safe===true||(match.eligibleWithSubstitutions===true&&match.substitutions?.length>0));
 }
 _recipeCard(recipe,custom=false){
  if(["official","today","week","recommend"].includes(this._tab)&&!this._v76Allowed(recipe))return "";
  const html=super._recipeCard(recipe,custom);if(!html||!recipe.match?.requiresSubstitutions)return html;
  const node=this._v67Dom(html),media=node.querySelector('.rx-v69-media')||node.firstElementChild;
  const badge=document.createElement('span');badge.dataset.v76DietBadge="";badge.textContent=this._v76Text('changes');
  badge.style.cssText='position:absolute;left:8px;right:8px;top:8px;z-index:2;background:var(--card-background-color,#fff);color:var(--primary-text-color,#222);border:1px solid var(--divider-color,#bbb);border-radius:8px;padding:5px 8px;font-size:12px;line-height:1.3;pointer-events:none';
  media.style.position='relative';media.appendChild(badge);return node.innerHTML;
 }
 _v66Body(recipe,custom,state,slot=null){
  let html=super._v66Body(recipe,custom,state,slot);
  const match=recipe.match||{};if(!match.requiresSubstitutions)return html;
  const escape=value=>this._escape(String(value??""));
  const rows=(match.substitutions||[]).map(row=>{
   const item=recipe.ingredients?.[row.ingredientIndex];
   const name=item?.displayName||row.original;
   return `<li data-v76-substitution="${escape(row.ingredientIndex)}"><strong>${escape(name)}</strong> → ${escape(this._v76Text(row.replacement.key)||row.replacement.name)}</li>`;
  }).join('');
  const node=this._v67Dom(html);for(const button of node.querySelectorAll('[data-v66-action="send"],[data-v66-action="shopping"]'))button.disabled=true;
  return `<section data-v76-substitutions role="note"><h4>${escape(this._v76Text('changes'))}</h4><ul>${rows}</ul><p>${escape(this._v76Text('note'))}</p></section>${node.innerHTML}`;
 }
 _v66PassesTag(recipe){
  const tags=this._v66Tags?.get(this._v66PageKey(this._tab));
  if(tags?.signature===JSON.stringify(this._filters())&&tags.diet===recipe.match?.diet&&recipe.match?.eligibleWithSubstitutions){
   return !tags.meal||(recipe.mealTypes||[recipe.todayMealType]).includes(tags.meal);
  }
  return super._v66PassesTag(recipe);
 }
 async _v66PreferLanguages(rows){
  const context=this._prefKey(),diet=this._v76Diet();
  await Promise.all(rows.slice(0,8).map(async recipe=>{
   const language=this._v66PreferredLanguage(recipe);if(!language||language===recipe.language)return;
   const options=recipe.languageVariants?.find(row=>row.language===language)?.servingVariants||[];
   const option=options.find(row=>row.servings===recipe.selectedServings)||options[0];if(!option)return;
   const original=recipe.displayVariantId;
   try{
    const detail=await this._api('cook4me/v31/recipe_detail',{entry_id:this._entryId,variant_id:String(option.displayVariantId),language,include_instructions:false});
    if(context!==this._prefKey()||diet!==this._v76Diet()||original!==recipe.displayVariantId||!this._v76Allowed(detail))return;
    const editions=this._v66Editions(recipe);Object.assign(recipe,detail);this._v66RestoreEditions(recipe,editions);this._ensureRecipeSelections(recipe);
   }catch(_error){/* Retain the checked source edition when another cannot load. */}
  }));return rows;
 }
 async _api(type,data={}){
  const detail=/\/(recipe_detail|recipe_presentation)$/.test(type),diet=this._filters()?.diet||"profile";
  if(detail)data={...data,diet};
  const result=await super._api(type,data);
  if(detail&&diet!==(this._filters()?.diet||"profile"))throw new Error(this._v76Text('changed'));
  return result;
 }
 _renderTab(){
  const result=super._renderTab();this.setAttribute('data-cook4me-build',BUILD);
  const content=this.shadowRoot?.getElementById('content');
  if(content&&["official","today","week","recommend"].includes(this._tab)&&["vegetarian","vegan","pescatarian"].includes(this._v76Diet())&&!content.querySelector('[data-v66-ref]')){
   const note=document.createElement('p');note.dataset.v76Refresh="";note.className='muted';note.textContent=this._v76Text('refresh');content.appendChild(note);
  }
  return result;
 }
}
customElements.define("cook4me-recipe-hub-panel-v76",Cook4MeRecipeHubPanelV76);
