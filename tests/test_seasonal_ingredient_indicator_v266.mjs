import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
 seasonalIngredientVisualState,
 seasonalIngredientDescription,
} from '../custom_components/cook4me/frontend/seasonal-ingredient-indicator-v266.js';

test('seasonal visual state separates seasonal mode from manual ingredient count',()=>{
 assert.deepEqual(
  seasonalIngredientVisualState({seasonalIngredients:true,ingredients:[]}),
  {seasonal:true,manualCount:0},
 );
 assert.deepEqual(
  seasonalIngredientVisualState({seasonalIngredients:true,ingredients:['a','b','a']}),
  {seasonal:true,manualCount:2},
 );
 assert.deepEqual(
  seasonalIngredientVisualState({seasonalIngredients:false,ingredients:['a']}),
  {seasonal:false,manualCount:1},
 );
});

test('seasonal ingredient accessible labels explain the active reason',()=>{
 assert.equal(
  seasonalIngredientDescription('el-GR','Υλικά',{seasonalIngredients:true,ingredients:[]}),
  'Υλικά εποχής',
 );
 assert.equal(
  seasonalIngredientDescription('el-GR','Υλικά',{seasonalIngredients:true,ingredients:['a','b','a']}),
  'Υλικά εποχής + 2 επιλεγμένα',
 );
 assert.equal(
  seasonalIngredientDescription('de-DE','Zutaten',{seasonalIngredients:true,ingredients:['a']}),
  'Saisonale Zutaten + 1 ausgewählt',
 );
 assert.equal(
  seasonalIngredientDescription('en','Ingredients',{seasonalIngredients:false,ingredients:['a']}),
  '',
 );
});

test('toolbar decoration uses apple state, leaf badge and keeps numeric manual badge separate',()=>{
 const source=readFileSync(
  new URL('../custom_components/cook4me/frontend/seasonal-ingredient-indicator-v266.js',import.meta.url),
  'utf8',
 );
 assert.match(source,/\[data-filter="ingredients"\]/);
 assert.match(source,/manualCount\?'mdi:food-apple':'mdi:food-apple-outline'/);
 assert.match(source,/dataset\.v266SeasonalBadge=''/);
 assert.match(source,/leaf\.setAttribute\('icon','mdi:leaf'\)/);
 assert.match(source,/right:-6px/);
 assert.match(source,/bottom:-6px/);
 assert.match(source,/button\.toggleAttribute\('data-v266-manual',manualCount>0\)/);
 assert.doesNotMatch(source,/badge\.textContent\s*=\s*['"]1['"]/);
});

test('active runtime mounts the v266 seasonal indicator outside prior UI layers',()=>{
 const active=readFileSync(
  new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),
  'utf8',
 );
 const registration=readFileSync(
  new URL('../custom_components/cook4me/panel.py',import.meta.url),
  'utf8',
 );
 assert.match(active,/seasonal-ingredient-indicator-v266\.js/);
 assert.match(active,/SeasonalIngredientIndicatorMixin\(RecipeActionRowMixin/);
 assert.match(active,/data-cook4me-ui-revision','266'/);
 assert.match(active,/runtime-v266/);
 assert.match(registration,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v266"/);
 assert.match(registration,/seasonalbadge=266/);
});
