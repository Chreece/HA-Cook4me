import {
  DietSubstitutionGuardMixin as DietSubstitutionGuardMixinV251,
  dietAdaptation,
  dietReplacementLabel as dietReplacementLabelV251,
} from './diet-substitution-guard-v251.js';

export {dietAdaptation};

const LABELS={
 en:{
  vegetable_stock:'Vegetable stock',vegetable_stock_cube:'Vegetable stock cube',water:'Water',
  unsweetened_soy_milk:'Unsweetened soy milk',olive_oil:'Olive oil',coconut_oil:'Coconut oil',
  maple_syrup:'Maple syrup',agave_syrup:'Agave syrup',sugar:'Sugar',pectin:'Pectin',
  cornstarch:'Cornstarch',lemon_juice:'Lemon juice',citric_acid:'Citric acid',
  ground_flaxseed_water:'Ground flaxseed + water',cornstarch_water:'Cornstarch + water',
  tofu_lemon:'Tofu + lemon juice',coconut_cream_lemon:'Coconut cream + lemon juice',
  plant_cheese:'Plant-based cheese',plant_yogurt:'Plant-based yogurt'
 },
 de:{
  vegetable_stock:'Gemüsebrühe',vegetable_stock_cube:'Gemüsebrühwürfel',water:'Wasser',
  unsweetened_soy_milk:'Ungesüßte Sojamilch',olive_oil:'Olivenöl',coconut_oil:'Kokosöl',
  maple_syrup:'Ahornsirup',agave_syrup:'Agavendicksaft',sugar:'Zucker',pectin:'Pektin',
  cornstarch:'Maisstärke',lemon_juice:'Zitronensaft',citric_acid:'Zitronensäure',
  ground_flaxseed_water:'Gemahlene Leinsamen + Wasser',cornstarch_water:'Maisstärke + Wasser',
  tofu_lemon:'Tofu + Zitronensaft',coconut_cream_lemon:'Kokoscreme + Zitronensaft',
  plant_cheese:'Pflanzlicher Käse',plant_yogurt:'Pflanzlicher Joghurt'
 },
 el:{
  vegetable_stock:'Ζωμός λαχανικών',vegetable_stock_cube:'Κύβος ζωμού λαχανικών',water:'Νερό',
  unsweetened_soy_milk:'Γάλα σόγιας χωρίς ζάχαρη',olive_oil:'Ελαιόλαδο',coconut_oil:'Λάδι καρύδας',
  maple_syrup:'Σιρόπι σφενδάμου',agave_syrup:'Σιρόπι αγαύης',sugar:'Ζάχαρη',pectin:'Πηκτίνη',
  cornstarch:'Κορν φλάουρ',lemon_juice:'Χυμός λεμονιού',citric_acid:'Κιτρικό οξύ',
  ground_flaxseed_water:'Αλεσμένος λιναρόσπορος + νερό',cornstarch_water:'Κορν φλάουρ + νερό',
  tofu_lemon:'Τόφου + χυμός λεμονιού',coconut_cream_lemon:'Κρέμα καρύδας + χυμός λεμονιού',
  plant_cheese:'Φυτικό τυρί',plant_yogurt:'Φυτικό γιαούρτι'
 }
};

export function dietReplacementLabel(key,language='en',fallback=''){
 const code=String(language||'en').toLowerCase().replace('_','-').split('-',1)[0];
 return (LABELS[code]||LABELS.en)[key]||dietReplacementLabelV251(key,code,fallback)||fallback||'';
}

export function dietAlternativeLabels(row,language='en'){
 const candidates=Array.isArray(row?.alternatives)&&row.alternatives.length?row.alternatives:[row?.replacement].filter(Boolean);
 return candidates.map(candidate=>dietReplacementLabel(candidate?.key,language,candidate?.name||candidate?.key||'')).filter(Boolean);
}

export const DietSubstitutionGuardMixin=Base=>class extends DietSubstitutionGuardMixinV251(Base){
 _v76Text(key){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return dietReplacementLabel(key,lang)||super._v76Text(key);
 }
 _v253Alternatives(row){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return dietAlternativeLabels(row,lang);
 }
 _recipeCard(recipe,custom=false){
  const html=super._recipeCard(recipe,custom);if(!html)return html;
  const state=this._v250DietState?.(recipe);if(!state?.adapted)return html;
  const node=this._v67Dom(html);
  for(const row of state.substitutions||[]){
   const chip=node.querySelector(`[data-v250-substitution="${String(row.ingredientIndex)}"]`);if(!chip)continue;
   const original=recipe?.ingredients?.[row.ingredientIndex]?.displayName||
    recipe?.ingredients?.[row.ingredientIndex]?.foodName||
    recipe?.ingredients?.[row.ingredientIndex]?.name||row.original||'';
   chip.textContent=`${original} → ${this._v253Alternatives(row).join(' / ')}`;
   chip.dataset.v253Candidates=String(this._v253Alternatives(row).length);
  }
  return node.innerHTML;
 }
 _v66Body(recipe,custom,state,slot=null){
  const html=super._v66Body(recipe,custom,state,slot);
  if(!recipe?.match?.requiresSubstitutions)return html;
  const node=this._v67Dom(html);
  for(const row of recipe.match.substitutions||[]){
   const item=node.querySelector(`[data-v76-substitution="${String(row.ingredientIndex)}"]`);if(!item)continue;
   const original=recipe?.ingredients?.[row.ingredientIndex]?.displayName||
    recipe?.ingredients?.[row.ingredientIndex]?.foodName||
    recipe?.ingredients?.[row.ingredientIndex]?.name||row.original||'';
   item.textContent=`${original} → ${this._v253Alternatives(row).join(' / ')}`;
   item.dataset.v253Candidates=String(this._v253Alternatives(row).length);
  }
  return node.innerHTML;
 }
};
