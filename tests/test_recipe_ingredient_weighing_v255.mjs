import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const source=readFileSync(new URL('../custom_components/cook4me/frontend/recipe-ingredient-weighing-v255.js',import.meta.url),'utf8');
const active=readFileSync(new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),'utf8');

test('per ingredient controls replace the recipe-level weighing section',()=>{
 assert.match(source,/querySelector\('\[data-v118-weighing\]'\)\?\.remove\(\)/);
 assert.match(source,/querySelectorAll\('\[data-v66-ingredient\]'\)/);
 assert.match(source,/data-v255-weigh-control/);
 assert.match(source,/data-v116-live/);
});

test('ingredient amount price stock coverage and weighing share one visual row',()=>{
 assert.match(source,/row\.classList\.add\('v255-ingredient-row'\)/);
 assert.match(source,/button\.classList\.add\('v255-ingredient-main'\)/);
 assert.match(source,/price=button\.querySelector\('\[data-v79-item\]'\)/);
 assert.match(source,/coverage=\[\.\.\.button\.children\]\.find/);
 assert.match(source,/meta\.append\(price\)/);
 assert.match(source,/meta\.append\(coverage\)/);
 assert.match(source,/grid-template-columns:minmax\(0,1fr\) auto auto/);
 assert.match(source,/@media\(max-width:760px\)/);
 assert.match(source,/@media\(max-width:520px\)/);
 assert.match(source,/\.v255-ingredient-price:empty\{display:none!important\}/);
});

test('labels use the correct weigh verb and explicit save cancel actions',()=>{
 assert.match(source,/weigh:'Weigh'/);
 assert.match(source,/save:'Save weight'/);
 assert.match(source,/cancel:'Cancel'/);
 assert.match(source,/weigh:'Wiegen'/);
 assert.match(source,/weigh:'Ζύγισμα'/);
});

test('save and cancel require weighing mode and a live scale reading',()=>{
 assert.match(source,/const scaleOn=!!reading/);
 assert.match(source,/if\(state\.active&&scaleOn\)/);
 assert.match(source,/start\.hidden=true;save\.hidden=false;cancel\.hidden=false/);
 assert.match(source,/start\.hidden=false;save\.hidden=true;cancel\.hidden=true/);
 assert.match(source,/_v116Live\(\)\{/);
 assert.match(source,/querySelectorAll\('\[data-v255-weigh-control\]'\)/);
 assert.match(source,/_v255PaintControl\(control,recipe,index\)/);
});

test('save calls the idempotent ingredient weight commit endpoint',()=>{
 assert.match(source,/cook4me\/v37\/ingredient_weight_commit/);
 assert.match(source,/request_id:state\.requestId/);
 assert.match(source,/ingredient_index:index/);
 assert.match(source,/grams:Number\(grams\)/);
});

test('cancel is local only and returns to weigh without an API call',()=>{
 const start=source.indexOf("querySelector('[data-v255-cancel]')");
 const end=source.indexOf("querySelector('[data-v255-save]')",start);
 const block=source.slice(start,end);
 assert.ok(start>=0&&end>start);
 assert.doesNotMatch(block,/_api\(/);
 assert.match(block,/state\.active=false/);
 assert.match(block,/state\.requestId=''/);
});

test('v255 remains registered while the active panel advances independently',()=>{
 assert.match(active,/RecipeIngredientWeighingMixin/);
 assert.match(active,/runtime-v255/);
 assert.match(active,/runtime-v256/);
 assert.match(active,/runtime-v257/);
 assert.match(active,/recipe-ingredient-weighing-v257\.js/);
 assert.match(active,/data-cook4me-ui-revision','257'/);
});
