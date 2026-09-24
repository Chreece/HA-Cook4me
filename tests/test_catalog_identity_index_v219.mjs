import assert from 'node:assert/strict';
import test from 'node:test';
import {UXFixesMixin} from '../custom_components/cook4me/frontend/ux-fixes-v218.js';

const Panel=UXFixesMixin(class {});

test('reviewed aliases remain transitive and preserve the first localized row',()=>{
 const p=new Panel();
 p._ingredientCatalog=[
  {key:'rice',name:'Ρύζι',sourceIngredientIds:['provider-a']},
  {key:'other-rice',ingredientId:'provider-a',sourceIngredientIds:['provider-b'],name:'Second'},
  {key:'flour',name:'Rice',sourceIngredientIds:['provider-flour']}
 ];
 assert.deepEqual([...p._v218ExpandedIds({ingredientId:'i:provider-b'})].sort(),['other-rice','provider-a','provider-b','rice']);
 assert.equal(p._v218LocalUnresolvedName({identity:'k:provider-b'}),'Ρύζι');
 assert.equal(p._v218LocalUnresolvedName({identity:'k:missing',name:'Fallback'}),'Fallback');
 assert.equal(p._v218StockMatches({key:'rice'},{key:'flour',name:'Rice'}),false);
 assert.equal(p._v218StockMatches({key:'rice'},{key:'package',lots:[{ingredientLinks:[{ingredientId:'provider-b'}]}]}),true);
});

test('catalog replacement, growth, and household changes cannot retain old names',()=>{
 const p=new Panel();
 p._entryId='first';p._ingredientCatalog=[{key:'rice',name:'Rice'}];
 assert.equal(p._v218LocalUnresolvedName({identity:'k:rice'}),'Rice');
 p._ingredientCatalog=[{key:'rice',name:'Ρύζι'}];
 assert.equal(p._v218LocalUnresolvedName({identity:'k:rice'}),'Ρύζι');
 p._ingredientCatalog.push({key:'flour',name:'Αλεύρι'});
 assert.equal(p._v218LocalUnresolvedName({identity:'k:flour'}),'Αλεύρι');
 p._entryId='second';p._ingredientCatalog=[];
 assert.equal(p._v218LocalUnresolvedName({identity:'k:rice',name:'Unknown'}),'Unknown');
});

test('returned alias sets cannot corrupt the next lookup',()=>{
 const p=new Panel();p._ingredientCatalog=[{key:'rice',sourceIngredientIds:['source']}];
 const ids=p._v218ExpandedIds({key:'rice'});ids.clear();ids.add('unrelated');
 assert.equal(p._v218StockMatches({key:'source'},{key:'rice'}),true);
 assert.equal(p._v218StockMatches({key:'unrelated'},{key:'rice'}),false);
});

test('3293 ingredients and 80 review labels require one catalog pass, not nested scans',()=>{
 const p=new Panel();let reads=0;
 p._ingredientCatalog=Array.from({length:3293},(_,i)=>({
  get key(){
   assert.ok(++reads<3293*8,'Catalog metadata repeatedly scanned while rendering review labels');
   return 'ingredient-'+i;
  },
  name:'Food '+i,sourceIngredientIds:['provider-'+i]
 }));
 for(let i=0;i<80;i++)assert.equal(p._v218LocalUnresolvedName({identity:'k:provider-'+(3292-i)}),'Food '+(3292-i));
 const readsAfterLabels=reads;
 p._houseIngredients=Array.from({length:42},(_,i)=>({key:'ingredient-'+i,lots:[{storageLocationId:'pantry'}]}));
 p._v78Locations=()=>[{id:'pantry',name:'Pantry'}];
 assert.deepEqual(p._v218StorageNames({ingredientId:'provider-41'}),['Pantry']);
 assert.equal(reads,readsAfterLabels,'Stock matching should reuse the existing index');
});
