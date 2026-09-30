import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {RecipeIngredientWeighingMixin} from '../custom_components/cook4me/frontend/recipe-ingredient-weighing-v257.js';

class Base {}
class Panel extends RecipeIngredientWeighingMixin(Base){
 _v79Money(values){
  return Object.entries(values||{}).map(([currency,amount])=>`${currency} ${Number(amount).toFixed(2)}`).join(' + ')||'—';
 }
 _v79Text(){return 'Ingredient estimate';}
}

const source=readFileSync(new URL('../custom_components/cook4me/frontend/recipe-ingredient-weighing-v257.js',import.meta.url),'utf8');
const active=readFileSync(new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),'utf8');
const panelConfig=readFileSync(new URL('../custom_components/cook4me/panel.py',import.meta.url),'utf8');

test('row prices match stable ingredient identity rather than backend array index',()=>{
 const panel=new Panel();
 const recipe={ingredients:[
  {key:'chickpeas',name:'Chickpeas'},
  {ingredientId:'butter-id',name:'Butter'},
 ]};
 const cost={ingredients:[
  {identity:'k:butter-id',costsByCurrency:{EUR:0.42},sourceKinds:['global_reference']},
  {identity:'k:chickpeas',costsByCurrency:{EUR:0.63},sourceKinds:['global_reference']},
 ]};
 assert.equal(panel._v257CostRow(recipe,0,cost).identity,'k:chickpeas');
 assert.equal(panel._v257CostRow(recipe,1,cost).identity,'k:butter-id');
});

test('row painter displays the exact amount price when known and hides unknown prices by empty content',()=>{
 const panel=new Panel();
 const nodes=[
  {dataset:{v257Price:'0'},textContent:'',title:''},
  {dataset:{v257Price:'1'},textContent:'stale',title:''},
 ];
 panel._v63RecipeDialog={querySelectorAll:selector=>selector==='[data-v257-price]'?nodes:[]};
 const recipe={ingredients:[{key:'chickpeas'},{key:'unknown'}]};
 const cost={ingredients:[
  {identity:'k:unknown',costsByCurrency:{}},
  {identity:'k:chickpeas',costsByCurrency:{EUR:0.63},sourceKinds:['global_reference']},
 ]};
 panel._v257PaintPrices(recipe,cost);
 assert.equal(nodes[0].textContent,'≈ EUR 0.63');
 assert.equal(nodes[1].textContent,'');
});

test('v257 disconnects the visible price chip from the legacy v79 index painter',()=>{
 assert.match(source,/removeAttribute\('data-v79-item'\)/);
 assert.match(source,/removeAttribute\('data-v79-key'\)/);
 assert.match(source,/price\.dataset\.v257Price=String\(index\)/);
 assert.match(source,/this\._v257PaintPrices\(recipe\)/);
});

test('pending background price hydration gets bounded forced follow-ups',()=>{
 assert.match(source,/cost\?\.priceLookupPending/);
 assert.match(source,/attempts>=3/);
 assert.match(source,/void this\._v79LoadCost\(recipe,true\)/);
 assert.match(source,/1000\+attempts\*750/);
});

test('all v79 cost paints also repaint active v257 ingredient price chips',()=>{
 assert.match(source,/_v79PaintRecipe\(recipe,state\)/);
 assert.match(source,/super\._v79PaintRecipe\(recipe,state\)/);
 assert.match(source,/_v257PaintPrices\(recipe,state\?\.cost\|\|null\)/);
});

test('v257 pricing remains active inside fullscreen guard v258',()=>{
 assert.match(active,/recipe-ingredient-weighing-v257\.js/);
 assert.match(active,/runtime-v257/);
 assert.match(active,/runtime-v258/);
 assert.match(active,/data-cook4me-ui-revision','\d+'/);
 assert.match(panelConfig,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v\d+"/);
 assert.match(panelConfig,/runtime-v249/);
 assert.match(panelConfig,/weigh=257&fullscreen=258/);
});
