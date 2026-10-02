import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {SeasonalFilterBadgeMixin} from '../custom_components/cook4me/frontend/seasonal-filter-badge-v267.js';

test('v267 keeps seasonal labels and marker behavior',()=>{
 class Base{_uiIngredientLanguage(){return 'el';}}
 const panel=new (SeasonalFilterBadgeMixin(Base))();
 assert.equal(panel._v266SeasonalLabel(0),'Υλικά εποχής');
 assert.equal(panel._v266SeasonalLabel(2),'Υλικά εποχής + 2 επιλεγμένα');
});

test('seasonal leaf icon is explicitly centered in the round badge',()=>{
 const source=readFileSync(
  new URL('../custom_components/cook4me/frontend/seasonal-filter-badge-v267.js',import.meta.url),
  'utf8',
 );
 assert.match(source,/left:50%!important/);
 assert.match(source,/top:50%!important/);
 assert.match(source,/position:absolute!important/);
 assert.match(source,/transform:translate\(calc\(-50% - \.5px\),calc\(-50% - \.75px\)\)!important/);
 assert.match(source,/transform-origin:center!important/);
 assert.match(source,/line-height:0!important/);
 assert.match(source,/margin:0!important/);
});

test('active panel cache-busts to v267',()=>{
 const active=readFileSync(
  new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),
  'utf8',
 );
 const registration=readFileSync(
  new URL('../custom_components/cook4me/panel.py',import.meta.url),
  'utf8',
 );
 assert.match(active,/seasonal-filter-badge-v267\.js/);
 assert.match(active,/data-cook4me-ui-revision','267'/);
 assert.match(active,/runtime-v267/);
 assert.match(registration,/seasonalbadge=267/);
 assert.match(registration,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v267"/);
});
