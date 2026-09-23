import test from 'node:test';
import assert from 'node:assert/strict';
import {recipeCoverage} from '../custom_components/cook4me/frontend/recipe-coverage-v198.js';
import {removeWeeklyReceiptSections} from '../custom_components/cook4me/frontend/scanner-receipts-v195.js';
const ingredient={ingredientId:'rice',name:'Ρύζι'};
const recipe=row=>({ingredients:[ingredient],match:{quantityAvailability:[{key:'rice',name:'Reis',status:'enough',...row}]}});
for(const value of [null,undefined,'',false,' ','NaN','Infinity'])test(`unknown coverage ${JSON.stringify(value)} never shows zero`,()=>assert.equal(recipeCoverage(recipe({coverage:value}),ingredient).percent,null));
for(const [value,wanted] of [[0,0],[.25,25],[1,100],['0.5',50],[-1,0],[2,100]])test(`numeric coverage ${value}`,()=>assert.equal(recipeCoverage(recipe({coverage:value}),ingredient).percent,wanted));
test('ingredientId matches different UI/source names',()=>assert.equal(recipeCoverage(recipe({coverage:1}),ingredient).percent,100));
test('different food IDs with same Greek label never borrow coverage',()=>{const r=recipe({key:'milk',name:'Ρύζι',coverage:1});assert.equal(recipeCoverage(r,ingredient).percent,null);});
test('key takes precedence over stale alternate ID',()=>{const item={...ingredient,key:'milk'};assert.equal(recipeCoverage(recipe({coverage:1}),item).percent,null);});
test('explicit aliases match keyed coverage rows',()=>assert.equal(recipeCoverage(recipe({key:'rice-de',coverage:.4}),{...ingredient,identities:['k:rice-de']}).percent,40));
test('duplicate same-food requirements keep distinct allocated percentages',()=>{const other={...ingredient};const r={ingredients:[ingredient,other],match:{quantityAvailability:[{key:'rice',ingredientIndex:0,coverage:1},{key:'rice',ingredientIndex:1,coverage:.2}]}};assert.equal(recipeCoverage(r,ingredient).percent,100);assert.equal(recipeCoverage(r,other).percent,20);});
test('quantity unknown wins over simple at-home presence',()=>{const r=recipe({coverage:null,status:'incompatible_unit'});r.match.ingredientAvailability=[{key:'rice',status:'at_home'}];assert.equal(recipeCoverage(r,ingredient).percent,null);});
test('name-only legacy coverage remains available',()=>assert.equal(recipeCoverage({match:{quantityAvailability:[{name:'Ρύζι',coverage:.5}]}},ingredient).percent,50));
test('weekly cleanup removes both folding generations, not nutrition or shopping',()=>{
 const nodes=new Map();
 for(const [attribute,keys] of [['data-v179-fold',['reservedStock','leftovers','priceInventory','completedPurchases','shoppingDelta','summary']],['data-v137-week-panel',['prices','leftovers','nutrition']]])for(const key of keys){const selector=`[${attribute}="${key}"]`;nodes.set(selector,{removed:false,remove(){this.removed=true;}});}
 const root={querySelectorAll:selector=>nodes.has(selector)?[nodes.get(selector)]:[]};removeWeeklyReceiptSections(root);removeWeeklyReceiptSections(root);
 for(const [selector,node] of nodes)assert.equal(node.removed,!selector.match(/shoppingDelta|summary|nutrition/),selector);
});
