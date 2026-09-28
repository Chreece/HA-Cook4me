import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
  dietAlternativeLabels,
  dietReplacementLabel,
  substitutionAdaptation,
} from '../custom_components/cook4me/frontend/diet-substitution-guard-v254.js';

const adapted={
 match:{
  dietCheckVersion:76,
  diet:'omnivore',
  safe:false,
  requiresSubstitutions:true,
  eligibleWithSubstitutions:true,
  substitutionCoverageComplete:true,
  substitutions:[{
   ingredientIndex:0,
   replacement:{key:'rice_flour',name:'Rice flour'},
   alternatives:[
    {key:'rice_flour',name:'Rice flour'},
    {key:'cornstarch',name:'Cornstarch'},
   ],
  }],
 },
};

const state=substitutionAdaptation(adapted,'omnivore');
assert.equal(state.allowed,true);
assert.equal(state.adapted,true);
assert.equal(state.substitutions.length,1);
assert.deepEqual(
 dietAlternativeLabels(adapted.match.substitutions[0],'el'),
 ['Ρυζάλευρο','Κορν φλάουρ'],
);
assert.equal(dietReplacementLabel('sunflower_seed_butter','de'),'Sonnenblumenkernmus');

const unsafe={match:{...adapted.match,substitutionCoverageComplete:false}};
assert.equal(substitutionAdaptation(unsafe,'omnivore').allowed,false);

const panel=readFileSync(new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),'utf8');
const info=readFileSync(new URL('../custom_components/cook4me/frontend/ingredient-substitution-info-v254.js',import.meta.url),'utf8');
const registration=readFileSync(new URL('../custom_components/cook4me/panel.py',import.meta.url),'utf8');
const catalog=readFileSync(new URL('../custom_components/cook4me/catalog/ingredient_allergy_substitutions.v1.json',import.meta.url),'utf8');

assert.match(panel,/diet-substitution-guard-v254\.js/);
assert.match(panel,/ingredient-substitution-info-v254\.js/);
assert.match(panel,/data-cook4me-ui-revision','254/);
assert.match(info,/Diet & allergy substitutions/);
assert.match(info,/cross-contact/);
assert.match(info,/catalogSubstitutionAllergens/);
assert.match(catalog,/"triggerAllergens"/);
assert.match(catalog,/"unsupportedWithoutContext": \[/);
assert.match(registration,/runtime-v254/);
assert.match(registration,/diet=254/);

console.log('ALLERGY_CATALOG_SUBSTITUTIONS_V254_FRONTEND=PASS');
