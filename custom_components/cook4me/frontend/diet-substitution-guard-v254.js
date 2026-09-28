import {
  DietSubstitutionGuardMixin as DietSubstitutionGuardMixinV253,
  dietAlternativeLabels as dietAlternativeLabelsV253,
  dietReplacementLabel as dietReplacementLabelV253,
} from './diet-substitution-guard-v253.js';

const LABELS={
 en:{rice_flour:'Rice flour',sunflower_seed_butter:'Sunflower seed butter'},
 de:{rice_flour:'Reismehl',sunflower_seed_butter:'Sonnenblumenkernmus'},
 el:{rice_flour:'Ρυζάλευρο',sunflower_seed_butter:'Βούτυρο ηλιόσπορου'}
};

export function dietReplacementLabel(key,language='en',fallback=''){
 const code=String(language||'en').toLowerCase().replace('_','-').split('-',1)[0];
 return (LABELS[code]||LABELS.en)[key]||dietReplacementLabelV253(key,code,fallback)||fallback||'';
}

export function dietAlternativeLabels(row,language='en'){
 const candidates=Array.isArray(row?.alternatives)&&row.alternatives.length?row.alternatives:[row?.replacement].filter(Boolean);
 return candidates.map(candidate=>dietReplacementLabel(candidate?.key,language,candidate?.name||candidate?.key||'')).filter(Boolean);
}

export function substitutionAdaptation(recipe,diet){
 const selected=String(diet||'omnivore').toLowerCase();
 const match=recipe?.match||{};
 if(match.safe===true)return {allowed:true,adapted:false,substitutions:[]};
 if(match.dietCheckVersion!==76||String(match.diet||'').toLowerCase()!==selected)
  return {allowed:false,adapted:false,substitutions:[]};
 const substitutions=Array.isArray(match.substitutions)?match.substitutions:[];
 const valid=match.requiresSubstitutions===true&&
  match.eligibleWithSubstitutions===true&&
  match.substitutionCoverageComplete===true&&
  substitutions.length>0&&
  substitutions.every(row=>
   row&&Number.isInteger(row.ingredientIndex)&&row.ingredientIndex>=0&&
   row.replacement&&typeof row.replacement==='object'&&
   String(row.replacement.name||row.replacement.key||'').trim()&&
   Array.isArray(row.alternatives)&&row.alternatives.length>0
  );
 return {allowed:valid,adapted:valid,substitutions:valid?substitutions:[]};
}

// Backwards-compatible export name for callers that still import the diet helper.
export const dietAdaptation=substitutionAdaptation;

export const DietSubstitutionGuardMixin=Base=>class extends DietSubstitutionGuardMixinV253(Base){
 _v250DietState(recipe){
  return substitutionAdaptation(recipe,this._v76Diet?.()||'omnivore');
 }
 _v76Text(key){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return dietReplacementLabel(key,lang)||super._v76Text(key);
 }
 _v253Alternatives(row){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return dietAlternativeLabels(row,lang);
 }
};
