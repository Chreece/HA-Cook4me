import test from 'node:test';
import assert from 'node:assert/strict';
import {recipeStockCoverage} from '../custom_components/cook4me/frontend/recipe-stock-badge-v241.js';
for(const [value,percent] of [[0,0],[.75,75],[1,100],['.25',25],[-1,0],[2,100]])test(`stock fraction ${value}`,()=>assert.deepEqual(recipeStockCoverage({match:{quantityCoverage:value}}),{percent,partial:false}));
for(const value of [null,undefined,'',false,' ','NaN','Infinity'])test(`unknown fraction ${String(value)}`,()=>assert.equal(recipeStockCoverage({match:{quantityCoverage:value}}).percent,null));
test('quantity takes precedence over ingredient presence',()=>assert.equal(recipeStockCoverage({match:{quantityCoverage:.4,pantryCoverage:1}}).percent,40));
test('all-unknown known-only average never shows 100%',()=>{
 assert.equal(recipeStockCoverage({match:{quantityCoverage:1,quantityConfidence:0}}).percent,null);
 assert.equal(recipeStockCoverage({match:{quantityCoverage:1,quantityAvailability:[{coverage:null,status:'unknown_stock_amount'}]}}).percent,null);
});
test('partial quantities mark the reported percentage approximate',()=>assert.deepEqual(recipeStockCoverage({match:{quantityCoverage:.75,quantityConfidence:.5}}),{percent:75,partial:true}));
test('legacy pantry aggregate is supported without turning missing data into zero',()=>assert.equal(recipeStockCoverage({match:{pantryCoverage:.5}}).percent,50));
test('fallback uses ingredient identities and duplicate allocations',()=>{
 const ingredients=[{key:'rice',name:'Rice'},{key:'rice',name:'Rice'},{key:'milk',name:'Rice'}];
 const match={quantityAvailability:[{key:'rice',ingredientIndex:0,coverage:1},{key:'rice',ingredientIndex:1,coverage:.5},{key:'milk',ingredientIndex:2,coverage:0}]};
 assert.deepEqual(recipeStockCoverage({ingredients,match}),{percent:50,partial:false});
});
test('unknown rows do not borrow pantry presence and unrelated keys do not match',()=>{
 const ingredients=[{key:'rice',name:'Rice'}];
 const match={pantryCoverage:1,quantityAvailability:[{key:'other',name:'Rice',coverage:1}]};
 assert.equal(recipeStockCoverage({ingredients,match}).percent,null);
});
test('presence-only rows and incomplete legacy data stay explicit',()=>{
 const ingredients=[{key:'a'},{key:'b'}];
 assert.deepEqual(recipeStockCoverage({ingredients,match:{ingredientAvailability:[{key:'a',status:'at_home'},{key:'b',status:'missing'}]}}),{percent:50,partial:false});
 assert.deepEqual(recipeStockCoverage({ingredients,match:{ingredientAvailability:[{key:'a',status:'at_home'}]}}),{percent:100,partial:true});
});

test('malformed optional availability rows cannot break recipe previews',()=>assert.deepEqual(recipeStockCoverage({match:{quantityAvailability:[null]}}),{percent:null,partial:false}));
