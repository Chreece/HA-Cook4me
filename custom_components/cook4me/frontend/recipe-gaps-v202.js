// Placeholders describe missing work; they are never recipes, inventory or costs.
export const GAP_TEXT={
 en:{title:'Recipe unavailable',processing_error:'This recipe could not be read or prepared. Reload the results to try again.',recipe_unavailable:'The saved recipe is unavailable. Reload it or replace this meal.',filtered:'This meal is hidden by the current filters. Review the filters to show it.',not_planned:'No recipe is planned for this meal. Generate the menu or add a recipe.',no_match:'No suitable recipe was returned for this meal. Review the filters and available variety.',incomplete:'Some recipe slots are unavailable. Totals and shopping requirements cover the loaded recipes only.'},
 de:{title:'Rezept nicht verfügbar',processing_error:'Dieses Rezept konnte nicht gelesen oder aufbereitet werden. Lade die Ergebnisse erneut.',recipe_unavailable:'Das gespeicherte Rezept ist nicht verfügbar. Lade es erneut oder ersetze diese Mahlzeit.',filtered:'Diese Mahlzeit wird durch die aktuellen Filter ausgeblendet. Prüfe die Filter.',not_planned:'Für diese Mahlzeit ist kein Rezept geplant. Erstelle das Menü oder füge ein Rezept hinzu.',no_match:'Für diese Mahlzeit wurde kein passendes Rezept gefunden. Prüfe die Filter und die verfügbare Auswahl.',incomplete:'Einige Rezeptplätze sind nicht verfügbar. Summen und Einkaufsmengen beziehen sich nur auf geladene Rezepte.'},
 el:{title:'Μη διαθέσιμη συνταγή',processing_error:'Δεν ήταν δυνατή η ανάγνωση ή η επεξεργασία αυτής της συνταγής. Φόρτωσε ξανά τα αποτελέσματα.',recipe_unavailable:'Η αποθηκευμένη συνταγή δεν είναι διαθέσιμη. Φόρτωσέ την ξανά ή αντικατάστησε αυτό το γεύμα.',filtered:'Αυτό το γεύμα κρύβεται από τα τρέχοντα φίλτρα. Έλεγξε τα φίλτρα για να εμφανιστεί.',not_planned:'Δεν έχει προγραμματιστεί συνταγή για αυτό το γεύμα. Δημιούργησε το μενού ή πρόσθεσε συνταγή.',no_match:'Δεν επιστράφηκε κατάλληλη συνταγή για αυτό το γεύμα. Έλεγξε τα φίλτρα και τη διαθέσιμη ποικιλία.',incomplete:'Ορισμένες θέσεις συνταγών δεν είναι διαθέσιμες. Τα σύνολα και οι αγορές αφορούν μόνο τις συνταγές που φορτώθηκαν.'}
};
const object=value=>!!value&&typeof value==='object'&&!Array.isArray(value);
export const isRecipeRow=row=>!!(object(row)&&!row._v202Gap&&(typeof row.title==='string'&&row.title.trim()||typeof row.canonicalName==='string'&&row.canonicalName.trim()));
export function recipeRows(rows){
 return Array.isArray(rows)?rows.map((row,index)=>isRecipeRow(row)?row:{_v202Gap:'processing_error',id:`unreadable-${index}`,todayMealType:typeof row?.todayMealType==='string'?row.todayMealType:'',title:''}):[];
}
export function missingDayMeals(meta,rows){
 const present=new Set((rows||[]).map(row=>row?.todayMealType).filter(Boolean));
 return [...new Set(Array.isArray(meta?.emptyMealTypes)?meta.emptyMealTypes:[])].filter(value=>typeof value==='string'&&!present.has(value));
}
export const RecipeGapsMixin=Base=>class extends Base {
 _v202GapText(key){const lang=String(this._uiIngredientLanguage?.()||'en').split(/[-_]/)[0];return (GAP_TEXT[lang]||GAP_TEXT.en)[key]||GAP_TEXT.en.recipe_unavailable;}
 _v202GapHtml(reason='recipe_unavailable',title=''){
  const e=v=>this._escape(String(v??''));
  return `<article class="card recipe v202-recipe-gap" data-v202-recipe-gap="${e(reason)}"><h3>${e(title||this._v202GapText('title'))}</h3><p>${e(this._v202GapText(reason))}</p></article>`;
 }
 _v202GapsStyles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v202GapStyles'))return;
  const style=document.createElement('style');style.id='v202GapStyles';style.textContent=`
   .v202-recipe-gap{min-height:175px;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center;gap:10px;border:1px dashed var(--divider-color);box-shadow:none}
   .v202-recipe-gap h3,.v202-recipe-gap p{margin:0;line-height:1.45;overflow-wrap:break-word}.v202-recipe-gap p{color:var(--secondary-text-color)}
   .v202-week-gap{margin:12px 0}.v202-week-gap>h4{margin:0 0 8px}[data-v202-gap-info]{padding:12px;border:1px solid var(--divider-color);border-radius:12px;line-height:1.45}
  `;this.shadowRoot.append(style);
 }
 _recipeCard(recipe,custom=false){
  this._v202GapsStyles();
  if(!isRecipeRow(recipe)){
   const context=this._v66Context;if(context&&++context.total>context.limit)return '';
   return this._v202GapHtml(recipe?._v202Gap||'processing_error');
  }
  const firstRef=this._v66NextRef||0;
  try{return super._recipeCard(recipe,custom);}
  catch(error){
   // Keep siblings visible when a single malformed recipe breaks rendering.
   // Do not expose provider data or mistake a deliberately filtered/paged row
   // (a normal empty return) for a parsing error.
   for(const ref of this._v66Refs?.keys()||[])if(Number(ref)>firstRef)this._v66Refs.delete(ref);
   this._v202RenderErrors=(this._v202RenderErrors||0)+1;
   return this._v202GapHtml('processing_error',recipe.title);
  }
 }
 async _v66PreferLanguages(rows){const safe=recipeRows(rows);await super._v66PreferLanguages(safe.filter(isRecipeRow));return safe;}
 _ensureRecipeSelections(recipe){if(!isRecipeRow(recipe))return;return super._ensureRecipeSelections(recipe);}
 _v66Render(section,container,render){
  const field={today:'_todayResults',official:'_results',recommend:'_recommendations'}[section];
  const previous=field?this[field]:null;
  if(field&&Array.isArray(previous)&&previous.some(row=>!isRecipeRow(row)))this[field]=recipeRows(previous);
  try{return super._v66Render(section,container,render);}
  finally{if(field&&previous!==null)this[field]=previous;}
 }
 _renderToday(c){
  const result=super._renderToday(c);this._v202GapsStyles();
  const grid=c.querySelector('#todayGrid');if(!grid||this._todayBusy||!this._todayMeta)return result;
  for(const node of grid.querySelectorAll('[data-v202-day-gap]'))node.remove();
  for(const meal of missingDayMeals(this._todayMeta,this._todayResults)){
   const section=document.createElement('section');section.className='rx-category-result';section.dataset.v202DayGap=meal;
   section.innerHTML=this._v202GapHtml('no_match',this._t(meal));grid.append(section);
  }
  return result;
 }
 _weekDayHtml(stamp){
  let html=super._weekDayHtml(stamp);const state=this._weekState;
  if(!state)return html;
  const holder=document.createElement('div');holder.innerHTML=html;
  const day=holder.querySelector('[data-week-date]');if(!day)return html;
  const gaps=(state.unavailableSlots||[]).filter(row=>row.date===stamp);
  // Legacy/local saved slots may reach the UI without passing refresh_plan.
  for(const slot of state.slots||[]){
   if(slot?.date!==stamp)continue;
   const recipe=slot.recipe||this._leftoverById?.(slot.leftoverId)?.recipe;
   if(!recipe&&!gaps.some(row=>row.id===slot.id))gaps.push({...slot,reason:'recipe_unavailable'});
  }
  const recorded=new Set((state.slots||[]).filter(row=>row?.date===stamp).map(row=>row.mealType));
  for(const gap of gaps)recorded.add(gap.mealType);
  for(const expected of state.expectedMealSlots||[]){
   if(expected.date===stamp&&!recorded.has(expected.mealType)){
    gaps.push({...expected,reason:(state.slots||[]).length?'no_match':'not_planned'});recorded.add(expected.mealType);
   }
  }
  for(const gap of gaps){
   const section=document.createElement('section');section.className='v202-week-gap';
   section.dataset.v202WeekGap=String(gap.id||`${stamp}:${gap.mealType}`);
   section.dataset.v202MealType=String(gap.mealType||'');
   section.innerHTML=this._v202GapHtml(gap.reason,this._v145MealLabel?.(gap.mealType)||this._t(gap.mealType||'dinner'));
   const rank=this._v144MealRank?.(gap.mealType)??99;
   const before=[...day.children].find(node=>{
    const id=node.dataset?.slotId;
    const meal=node.dataset?.v202MealType||(state.slots||[]).find(row=>String(row?.id)===id)?.mealType;
    return meal&&(this._v144MealRank?.(meal)??99)>rank;
   });
   day.insertBefore(section,before||null);
  }
  if(gaps.length)day.querySelector('.rx-v67-empty-day')?.remove();
  return holder.innerHTML;
 }
 _renderWeek(c){
  const result=super._renderWeek(c);this._v202GapsStyles();
  for(const slot of c.querySelectorAll('[data-slot-id]'))if(slot.querySelector('[data-v202-recipe-gap]')){
   slot.removeAttribute('role');slot.removeAttribute('tabindex');
   slot.addEventListener('click',event=>event.stopImmediatePropagation(),true);
   slot.addEventListener('keydown',event=>event.stopImmediatePropagation(),true);
  }
  if(c.querySelector('[data-v202-recipe-gap]')){
   const note=document.createElement('p');note.dataset.v202GapInfo='';note.textContent=this._v202GapText('incomplete');
   c.querySelector('.rx-week-grid')?.before(note);
  }
  return result;
 }
};
