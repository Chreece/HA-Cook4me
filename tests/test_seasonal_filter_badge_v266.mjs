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
 assert.match(source,/_v263SeasonalIndicator\(container\)/);
 assert.match(source,/data-v263-active-filters/);
 assert.match(source,/right:-5px/);
 assert.match(source,/bottom:-5px/);
});
