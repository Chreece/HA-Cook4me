import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const source=readFileSync(new URL('../custom_components/cook4me/frontend/recipe-ingredient-weighing-v256.js',import.meta.url),'utf8');
const active=readFileSync(new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),'utf8');

test('idle row shows only scale icon when scale is live',()=>{
 assert.match(source,/const showStart=idle&&!!reading/);
 assert.match(source,/start\.innerHTML='<ha-icon icon="mdi:scale-balance"/);
 assert.doesNotMatch(source,/start\.textContent=/);
 assert.match(source,/control\.hidden=!\(showStart\|\|showSave\|\|showSaved\|\|showCancel\)/);
});

test('pressing weigh changes the same row to save current amount plus X',()=>{
 assert.match(source,/state\.active=true;state\.requestId=this\._v256RequestId\(\)/);
 assert.match(source,/const activeLive=state\.active&&!!reading/);
 assert.match(source,/const showSave=activeLive/);
 assert.match(source,/saveValue\)saveValue\.textContent=value/);
 assert.match(source,/mdi:content-save/);
 assert.match(source,/mdi:close/);
});

test('hidden actions stay hidden even when generic btn CSS sets display',()=>{
 assert.match(source,/\.v256-weigh-control\[hidden\],\.v256-weigh-control \[hidden\]\{display:none!important\}/);
});

test('live cancel is local and saved cancel calls reversible backend',()=>{
 const cancelStart=source.indexOf("querySelector('[data-v256-cancel]')");
 const saveStart=source.indexOf("querySelector('[data-v256-save]')",cancelStart);
 const block=source.slice(cancelStart,saveStart);
 assert.match(block,/if\(state\.active\)/);
 assert.match(block,/state\.active=false;state\.requestId=''/);
 assert.match(block,/cook4me\/v37\/ingredient_weight_cancel/);
 assert.match(block,/ingredient_index:index/);
});

test('saved state shows amount beside scale icon and X even without a live scale',()=>{
 assert.match(source,/const showSaved=idle&&hasSaved/);
 assert.match(source,/const showCancel=activeLive\|\|showSaved/);
 assert.match(source,/const showStart=idle&&!!reading/);
 assert.match(source,/amount\.textContent=showSaved/);
});

test('scale button requires a live non-disconnected scale',()=>{
 assert.match(source,/const connected=this\._v116Connected\?\.\(\)/);
 assert.match(source,/return reading&&connected!==false\?reading:null/);
});

test('price and storage coverage remain in the same ingredient row',()=>{
 assert.match(source,/price=button\.querySelector\('\[data-v79-item\]'\)/);
 assert.match(source,/meta\.append\(price\)/);
 assert.match(source,/meta\.append\(coverage\)/);
 assert.match(source,/v256-ingredient-price/);
});

test('fullscreen nutrition updates patch content instead of rebuilding whole dialog',()=>{
 const render=source.indexOf('_renderRecipeDialog(){');
 const superRender=source.indexOf('super._renderRecipeDialog()',render);
 const patchGuard=source.indexOf('this._v256NutritionPatchRecipe===recipe',render);
 assert.ok(render>=0&&patchGuard>render&&superRender>patchGuard);
 assert.match(source,/async _loadRecipeNutrition\(recipe\)/);
 assert.match(source,/_v256PatchNutrition\(recipe\)/);
});

test('fullscreen first-open renders are hidden until structure is ready',()=>{
 assert.match(source,/this\._v256OpeningRecipe=true/);
 assert.match(source,/setAttribute\('data-v256-preparing',''\)/);
 assert.match(source,/removeAttribute\('data-v256-preparing'\)/);
 assert.match(source,/\[data-recipe-dialog\]\[data-v256-preparing\]\{visibility:hidden!important\}/);
});

test('fullscreen close restores underlying page scroll position',()=>{
 assert.match(source,/const scrollTop=content\?\.scrollTop\?\?0,scrollLeft=content\?\.scrollLeft\?\?0/);
 assert.match(source,/content\.scrollTop=scrollTop;content\.scrollLeft=scrollLeft/);
 assert.match(source,/requestAnimationFrame\?\.\(restore\)/);
});

test('v256 remains registered while active panel advances through v258',()=>{
 assert.match(active,/runtime-v256/);
 assert.match(active,/runtime-v257/);
 assert.match(active,/runtime-v258/);
 assert.match(active,/recipe-ingredient-weighing-v257\.js/);
 assert.match(active,/recipe-fullscreen-guard-v258\.js/);
 assert.match(active,/data-cook4me-ui-revision','\d+'/);
});
