import "./cook4me-panel-v106.js";
const BasePanel=customElements.get("cook4me-recipe-hub-panel-v106");
const TEXT={
 en:{changes:"Ingredient changes",choose:"Choose a suitable replacement",note:"Apply these ingredient changes yourself. The device receives the original recipe and cooking program; displayed times and nutrition refer to the original."},
 el:{changes:"Αντικαταστάσεις υλικών",choose:"Επιλέξτε κατάλληλο υποκατάστατο",note:"Εφαρμόστε εσείς τις αντικαταστάσεις υλικών. Η συσκευή λαμβάνει την αρχική συνταγή και το αρχικό πρόγραμμα μαγειρέματος· οι χρόνοι και οι διατροφικές τιμές αφορούν την αρχική συνταγή."},
 de:{changes:"Zutaten ersetzen",choose:"Geeigneten Ersatz auswählen",note:"Die Zutaten selbst wie angegeben ersetzen. Das Gerät erhält das Originalrezept und Garprogramm; angezeigte Zeiten und Nährwerte gelten für das Original."}
};
class Cook4MeRecipeHubPanelV107 extends BasePanel{
 _v107Text(key){return (TEXT[this._uiIngredientLanguage()]||TEXT.en)[key]||key;}
 _v77CanSend(recipe){return !!(recipe.displayVariantId||recipe.sendVariantId||recipe.searchVariantId);}
 _v107Changes(recipe){
  // Older saved recipes may have suggestions without the new row annotations.
  return (recipe.match?.ingredientChanges??recipe.match?.substitutions??[]).filter(row=>Number.isInteger(row.ingredientIndex)&&row.ingredientIndex>=0&&row.ingredientIndex<(recipe.ingredients?.length||0));
 }
 _v107Replacement(row){
  const key=row.replacement?.key,label=key?this._v76Text(key):'';
  return label&&label!==key?label:row.replacement?.name||this._v107Text('choose');
 }
 _v66Body(recipe,custom,state,slot=null){
  const node=this._v67Dom(super._v66Body(recipe,custom,state,slot));
  node.querySelector('[data-v76-substitutions]')?.remove();
  const changes=this._v107Changes(recipe);if(!changes.length)return node.innerHTML;
  const escape=value=>this._escape(String(value??''));
  for(const row of changes){
   const name=node.querySelector(`[data-v66-ingredient="${row.ingredientIndex}"] > span`);if(!name)continue;
   const original=document.createElement('s');original.dataset.v107Original=String(row.ingredientIndex);
   // Strike the name and source label only; retain quantities and prices.
   for(const child of [...name.childNodes]){
    if(child.nodeType===1&&child.matches('.rx-v66-quantity,[data-v79-item]'))continue;
    original.append(child);
   }
   name.prepend(original);
   const replacement=document.createElement('strong');replacement.dataset.v107Replacement=String(row.ingredientIndex);
   replacement.style.cssText='display:block;line-height:1.5;overflow-wrap:anywhere';
   replacement.textContent=`→ ${this._v107Replacement(row)}`;original.after(replacement);
  }
  const note=document.createElement('section');note.dataset.v107Changes='';note.setAttribute('role','note');
  note.style.cssText='margin:12px 0;padding:12px;border:1px solid var(--divider-color,#777);border-radius:10px;overflow-wrap:anywhere';
  const rows=changes.map(row=>{
   const item=recipe.ingredients[row.ingredientIndex],name=item?.displayName||item?.canonicalName||row.original;
   return `<li><s>${escape(name)}</s> → <strong>${escape(this._v107Replacement(row))}</strong></li>`;
  }).join('');
  note.innerHTML=`<strong>${escape(this._v107Text('changes'))}</strong>${state.cooking?`<ul style="padding-inline-start:20px;margin:8px 0">${rows}</ul>`:''}<p style="margin:8px 0 0;font-size:.9em;line-height:1.5">${escape(this._v107Text('note'))}</p>`;
  const section=node.querySelector(`[data-v66-section="${state.cooking?'steps':'ingredients'}"] .rx-v66-section`);
  section?.prepend(note);
  return node.innerHTML;
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.17.11');return result;}
}
customElements.define('cook4me-recipe-hub-panel-v107',Cook4MeRecipeHubPanelV107);
