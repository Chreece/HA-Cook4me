import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {SeasonalFilterBadgeMixin} from '../custom_components/cook4me/frontend/seasonal-filter-badge-v266.js';

test('seasonal ingredient labels distinguish seasonal-only from mixed filters',()=>{
 class Base{_uiIngredientLanguage(){return 'el';}}
 const panel=new (SeasonalFilterBadgeMixin(Base))();
 assert.equal(panel._v266SeasonalLabel(0),'Υλικά εποχής');
 assert.equal(panel._v266SeasonalLabel(2),'Υλικά εποχής + 2 επιλεγμένα');
});

test('seasonal marker is separate from the existing manual-count badge',()=>{
 const source=readFileSync(
  new URL('../custom_components/cook4me/frontend/seasonal-filter-badge-v266.js',import.meta.url),
  'utf8',
 );
 assert.match(source,/v266-seasonal-marker/);
 assert.match(source,/filters\.seasonalIngredients===true/);
 assert.match(source,/new Set\(Array\.isArray\(filters\.ingredients\)/);
 assert.doesNotMatch(source,/v98-filter-count.*remove/);
 assert.match(source,/button\.append\(marker\)/);
 assert.match(source,/right:-5px/);
 assert.match(source,/bottom:-5px/);
});

test('active panel cache-busts v266 without changing the v265 element contract',()=>{
 const active=readFileSync(
  new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),
  'utf8',
 );
 const registration=readFileSync(
  new URL('../custom_components/cook4me/panel.py',import.meta.url),
  'utf8',
 );
 assert.match(active,/seasonal-filter-badge-v266\.js/);
 assert.match(active,/SeasonalFilterBadgeMixin\(RecipeActionRowMixin/);
 assert.match(registration,/seasonalbadge=266/);
 assert.match(registration,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v265"/);
});
