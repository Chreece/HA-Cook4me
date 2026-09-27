const RESTRICTED_DIETS=new Set(['pescatarian','vegetarian','vegan']);

export function dietAdaptation(recipe,diet){
 const selected=String(diet||'').toLowerCase();
 if(!RESTRICTED_DIETS.has(selected))return {allowed:true,adapted:false,substitutions:[]};
 const match=recipe?.match||{};
 if(match.dietCheckVersion!==76||String(match.diet||'').toLowerCase()!==selected)
  return {allowed:false,adapted:false,substitutions:[]};
 if(match.safe===true)return {allowed:true,adapted:false,substitutions:[]};
 const substitutions=Array.isArray(match.substitutions)?match.substitutions:[];
 const valid=match.requiresSubstitutions===true&&
  match.eligibleWithSubstitutions===true&&
  match.substitutionCoverageComplete===true&&
  substitutions.length>0&&
  substitutions.every(row=>
   row&&Number.isInteger(row.ingredientIndex)&&row.ingredientIndex>=0&&
   row.replacement&&typeof row.replacement==='object'&&
   String(row.replacement.name||row.replacement.key||'').trim()
  );
 return {allowed:valid,adapted:valid,substitutions:valid?substitutions:[]};
}

const TEXT={
 en:{title:'Ingredient replacements'},
 de:{title:'Zutaten ersetzen'},
 el:{title:'Αντικαταστάσεις υλικών'}
};

export const DietSubstitutionGuardMixin=Base=>class extends Base{
 _v250DietState(recipe){
  const diet=this._v76Diet?.()||'omnivore';
  return dietAdaptation(recipe,diet);
 }
 _v76Allowed(recipe){
  const inherited=super._v76Allowed(recipe);
  if(!inherited)return false;
  return this._v250DietState(recipe).allowed;
 }
 _recipeCard(recipe,custom=false){
  const html=super._recipeCard(recipe,custom);
  if(!html)return html;
  const state=this._v250DietState(recipe);
  if(!state.adapted)return html;

  const node=this._v67Dom(html);
  const block=document.createElement('div');
  block.className='v250-diet-replacements';
  block.dataset.v250DietReplacements='';
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  const title=document.createElement('strong');
  title.textContent=(TEXT[lang]||TEXT.en).title;
  block.append(title);

  const list=document.createElement('div');
  list.className='v250-diet-replacement-list';
  for(const row of state.substitutions){
   const original=recipe?.ingredients?.[row.ingredientIndex]?.displayName||
    recipe?.ingredients?.[row.ingredientIndex]?.foodName||
    recipe?.ingredients?.[row.ingredientIndex]?.name||
    row.original||'';
   const replacement=this._v76Text?.(row.replacement.key)||row.replacement.name||row.replacement.key||'';
   const chip=document.createElement('span');
   chip.className='v250-diet-replacement';
   chip.dataset.v250Substitution=String(row.ingredientIndex);
   chip.textContent=`${original} → ${replacement}`;
   list.append(chip);
  }
  block.append(list);
  const media=node.querySelector('.rx-v69-media');
  if(media?.parentNode)media.insertAdjacentElement('afterend',block);
  else node.prepend(block);
  this._v250DietStyles();
  return node.innerHTML;
 }
 _v250DietStyles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v250DietStyles'))return;
  const style=document.createElement('style');
  style.id='v250DietStyles';
  style.textContent=`
   .v250-diet-replacements{margin:8px 10px 0;padding:8px 10px;border:1px solid var(--divider-color);border-radius:10px;background:var(--secondary-background-color,var(--card-background-color));font-size:12px;line-height:1.35}
   .v250-diet-replacements>strong{display:block;margin-bottom:5px}
   .v250-diet-replacement-list{display:flex;flex-wrap:wrap;gap:5px}
   .v250-diet-replacement{display:inline-flex;align-items:center;padding:4px 7px;border-radius:999px;background:var(--card-background-color);border:1px solid var(--divider-color);font-weight:600}
  `;
  this.shadowRoot.append(style);
 }
};
