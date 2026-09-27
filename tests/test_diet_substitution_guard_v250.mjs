import assert from 'node:assert/strict';
import {dietAdaptation} from '../custom_components/cook4me/frontend/diet-substitution-guard-v250.js';

const valid={
 ingredients:[{name:'Cod'}],
 match:{
  dietCheckVersion:76,
  diet:'vegetarian',
  safe:false,
  requiresSubstitutions:true,
  eligibleWithSubstitutions:true,
  substitutionCoverageComplete:true,
  substitutions:[{ingredientIndex:0,original:'Cod',replacement:{key:'tofu',name:'Firm tofu'}}],
 }
};

assert.equal(dietAdaptation(valid,'vegetarian').allowed,true);
assert.equal(dietAdaptation(valid,'vegetarian').adapted,true);
assert.equal(dietAdaptation(valid,'vegetarian').substitutions.length,1);

for(const mutate of [
 recipe=>{delete recipe.match.substitutionCoverageComplete;},
 recipe=>{recipe.match.substitutions=[];},
 recipe=>{recipe.match.substitutions=[{ingredientIndex:0,replacement:{}}];},
 recipe=>{recipe.match.diet='vegan';},
]){
 const recipe=structuredClone(valid);
 mutate(recipe);
 assert.equal(dietAdaptation(recipe,'vegetarian').allowed,false);
}

const safe=structuredClone(valid);
safe.match.safe=true;
safe.match.requiresSubstitutions=false;
safe.match.eligibleWithSubstitutions=false;
safe.match.substitutionCoverageComplete=false;
safe.match.substitutions=[];
assert.equal(dietAdaptation(safe,'vegetarian').allowed,true);
assert.equal(dietAdaptation(safe,'vegetarian').adapted,false);

console.log('DIET_SUBSTITUTION_GUARD_V250=PASS');
