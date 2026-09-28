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

test('labels use the correct weigh verb and explicit save cancel actions',()=>{
 assert.match(source,/weigh:'Weigh'/);
 assert.match(source,/save:'Save weight'/);
 assert.match(source,/cancel:'Cancel'/);
 assert.match(source,/weigh:'Wiegen'/);
 assert.match(source,/weigh:'Ζύγισμα'/);
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

test('active panel applies v255 mixin and constructor',()=>{
 assert.match(active,/RecipeIngredientWeighingMixin/);
 assert.match(active,/runtime-v255/);
 assert.match(active,/data-cook4me-ui-revision','255'/);
});
