import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
 recipeBlacklistIdentities,
 recipeIsBlacklisted,
} from '../custom_components/cook4me/frontend/recipe-blacklist-v264.js';

test('recipe blacklist identity follows stable family aliases before title',()=>{
 const ids=recipeBlacklistIdentities({
  displayFamilyId:'family-1',
  groupingFunctionalId:'group-1',
  variantFunctionalId:'variant-1',
  title:'Translated title',
 });
 assert.deepEqual(ids,[
  'displayFamilyId:family-1',
  'groupingFunctionalId:group-1',
  'variantFunctionalId:variant-1',
 ]);
});

test('blacklist matches another recipe edition through shared grouping identity',()=>{
 const rows=[{
  identity:'displayFamilyId:family-1',
  identities:['displayFamilyId:family-1','groupingFunctionalId:group-1'],
  title:'Original title',
 }];
 assert.equal(recipeIsBlacklisted({
  groupingFunctionalId:'group-1',
  variantFunctionalId:'variant-2',
  title:'Άλλος τίτλος',
 },rows),true);
 assert.equal(recipeIsBlacklisted({
  groupingFunctionalId:'group-2',
  title:'Other recipe',
 },rows),false);
});

test('title fallback is deterministic only when stable ids are absent',()=>{
 assert.deepEqual(
  recipeBlacklistIdentities({title:'Crème  Brûlée!'}),
  ['title:creme brulee'],
 );
});

test('active runtime exposes blacklist button and Diet undo list',()=>{
 const mixin=readFileSync(
  new URL('../custom_components/cook4me/frontend/recipe-blacklist-v264.js',import.meta.url),
  'utf8',
 );
 const panel=readFileSync(
  new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),
  'utf8',
 );
 const registration=readFileSync(
  new URL('../custom_components/cook4me/panel.py',import.meta.url),
  'utf8',
 );
 assert.match(mixin,/dataset\.v264Blacklist/);
 assert.match(mixin,/cook4me\/recipe_blacklist_add/);
 assert.match(mixin,/cook4me\/recipe_blacklist_remove/);
 assert.match(mixin,/_v83RenderProfiles\(container,state\)/);
 assert.match(mixin,/dataset\.v264Undo/);
 assert.match(panel,/recipe-blacklist-v264\.js/);
 assert.match(panel,/RecipeBlacklistMixin\(SeasonalFilterStateMixin/);
 assert.match(panel,/data-cook4me-ui-revision','266'/);
 assert.match(panel,/runtime-v266/);
 assert.match(registration,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v266"/);
 assert.match(registration,/blacklist=264/);
});
