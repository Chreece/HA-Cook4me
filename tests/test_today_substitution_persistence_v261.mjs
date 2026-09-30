import test from 'node:test';
import assert from 'node:assert/strict';
import {TodaySubstitutionPersistenceMixin} from '../custom_components/cook4me/frontend/today-substitution-persistence-v261.js';

class Base{
 _v59CompactMatch(value){
  return value?.score!==undefined?{score:value.score}:null;
 }
}

test('fast Today shell preserves the complete substitution guard proof',()=>{
 const Panel=TodaySubstitutionPersistenceMixin(Base);
 const panel=new Panel();
 const input={
  score:-100,
  safe:false,
  diet:'vegetarian',
  dietCheckVersion:76,
  dietRulesSignature:'sig',
  requiresSubstitutions:true,
  eligibleWithSubstitutions:true,
  substitutionCoverageComplete:true,
  substitutionCandidateCount:2,
  substitutionSources:['ingredient_catalog'],
  substitutions:[{
   ingredientIndex:0,
   original:'chicken',
   replacement:{key:'tofu',name:'Tofu'},
   alternatives:[{key:'tofu',name:'Tofu'},{key:'seitan',name:'Seitan'}],
  }],
  ingredientChanges:[{ingredientIndex:0}],
  violations:['diet:vegetarian'],
 };
 const compact=panel._v59CompactMatch(input);
 assert.equal(compact.score,-100);
 assert.equal(compact.substitutionCoverageComplete,true);
 assert.equal(compact.requiresSubstitutions,true);
 assert.equal(compact.eligibleWithSubstitutions,true);
 assert.deepEqual(compact.substitutions,input.substitutions);
 assert.deepEqual(compact.substitutionSources,['ingredient_catalog']);
 assert.notEqual(compact.substitutions,input.substitutions);
});

test('v260 live match without stored coverage flag is migrated only for v76 proven flags',()=>{
 const Panel=TodaySubstitutionPersistenceMixin(Base);
 const panel=new Panel();
 const compact=panel._v59CompactMatch({
  safe:false,diet:'vegetarian',dietCheckVersion:76,
  requiresSubstitutions:true,eligibleWithSubstitutions:true,
  substitutions:[{ingredientIndex:0,replacement:{key:'tofu'},alternatives:[{key:'tofu'}]}],
 });
 assert.equal(compact.substitutionCoverageComplete,true);

 const unknown=panel._v59CompactMatch({
  safe:false,diet:'vegetarian',dietCheckVersion:75,
  requiresSubstitutions:true,eligibleWithSubstitutions:true,
 });
 assert.equal(unknown.substitutionCoverageComplete,undefined);
});

test('v261 uses a fresh browser shell namespace so broken v260 cache is not restored',()=>{
 const Panel=TodaySubstitutionPersistenceMixin(Base);
 const panel=new Panel();
 panel._v54CacheUser='user-1';
 assert.equal(panel._snapshotKey(),'cook4me.ui.shell.v261.user-1');
});
