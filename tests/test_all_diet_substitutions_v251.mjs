import assert from 'node:assert/strict';
import {
  dietAdaptation,
  dietReplacementLabel,
} from '../custom_components/cook4me/frontend/diet-substitution-guard-v251.js';

const keys=[
 'mushroom_stock','oat_cream','soy_cream','coconut_cream',
 'oat_milk','soy_milk','rice_milk','soy_yogurt','coconut_yogurt',
 'soy_sauce','coconut_aminos','agar','microbial_rennet','bentonite',
 'soy_cheese','cashew_cheese','nutritional_yeast','flax_egg',
 'aquafaba','pea_protein',
];
for(const lang of ['en','de','el']){
 for(const key of keys){
  const label=dietReplacementLabel(key,lang);
  assert.equal(typeof label,'string');
  assert.ok(label.trim(), `${lang} missing ${key}`);
  assert.notEqual(label,key, `${lang} exposed raw key ${key}`);
 }
}

for(const diet of ['pescatarian','vegetarian','vegan']){
 const recipe={
  ingredients:[{name:'Conflict'}],
  match:{
   dietCheckVersion:76,
   diet,
   safe:false,
   requiresSubstitutions:true,
   eligibleWithSubstitutions:true,
   substitutionCoverageComplete:true,
   substitutions:[{ingredientIndex:0,original:'Conflict',replacement:{key:'agar',name:'Agar-agar'}}],
  },
 };
 const state=dietAdaptation(recipe,diet);
 assert.equal(state.allowed,true);
 assert.equal(state.adapted,true);
 const stale=structuredClone(recipe);
 delete stale.match.substitutionCoverageComplete;
 assert.equal(dietAdaptation(stale,diet).allowed,false);
}

const omnivore={
 match:{dietCheckVersion:76,diet:'omnivore',safe:true,substitutions:[]}
};
assert.equal(dietAdaptation(omnivore,'omnivore').allowed,true);

console.log('ALL_DIET_SUBSTITUTIONS_V251_FRONTEND=PASS');
