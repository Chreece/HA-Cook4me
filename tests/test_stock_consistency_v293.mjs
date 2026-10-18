import test from 'node:test';
import assert from 'node:assert/strict';
import {
 physicallyStored, availableLocationIds, unlimitedIngredientCoverage, aggregateIngredientCoverage,
 StockConsistencyMixin
} from '../custom_components/cook4me/frontend/stock-consistency-v293.js';

const text={unlimited:'Απεριόριστο απόθεμα'};
test('genuine unlimited physical stock is sufficient without a source amount',()=>{
 for(const initial of [
  {status:'unknown_requirement',percent:null},
  {status:'incompatible_unit',percent:null},
  {status:'shortage',percent:0},
  {status:'staple',percent:100},
  {status:'enough',percent:100},
 ]){
  const before=structuredClone(initial);
  const resolved=unlimitedIngredientCoverage(initial,[{key:'salt',unlimited:true}],text);
  assert.equal(resolved.percent,100);
  assert.equal(resolved.status,'enough');
  assert.equal(resolved.displayLabel,'∞');
  assert.equal(resolved.displayTitle,'Απεριόριστο απόθεμα');
  assert.equal(resolved.unlimited,true);
  assert.deepEqual(initial,before,'saved recipe coverage is not rewritten');
 }
});

test('unknown/zero finite lots do not masquerade as unlimited',()=>{
 const current={status:'unknown_requirement',percent:null};
 for(const rows of [
  [],[{unlimited:false,quantity:400}],
  [{lots:[{quantity:150}]}],
  [{quantity:500,unlimited:false}],
  [{lots:[{quantity:0}],quantity:200}]
 ]){
  assert.equal(unlimitedIngredientCoverage(current,rows,text),current);
 }
 assert.equal(physicallyStored({lots:[{quantity:0}],quantity:200}),false);
 assert.equal(physicallyStored({lots:[{quantity:20}],quantity:200}),true);
 assert.equal(physicallyStored({quantity:20}),true);
 assert.equal(physicallyStored({unlimited:true}),true);
});

test('all-spice unlimited recipes are complete, never an unknown placeholder',()=>{
 assert.deepEqual(aggregateIngredientCoverage([
  {status:'enough',percent:100,unlimited:true},
  {status:'enough',percent:100,unlimited:true}
 ]),{percent:100,partial:false});
 assert.deepEqual(aggregateIngredientCoverage([
  {status:'staple',percent:100}
 ]),{percent:100,partial:false});
});

test('mixed physical stock keeps true shortages and visibly uncertain portions',()=>{
 assert.deepEqual(aggregateIngredientCoverage([
  {status:'enough',percent:100,unlimited:true},
  {status:'shortage',percent:0},
  {status:'enough',percent:50}
 ]),{percent:50,partial:false});
 assert.deepEqual(aggregateIngredientCoverage([
  {status:'enough',percent:100,unlimited:true},
  {status:'at_home_quantity_unverified',percent:null},
  {status:'shortage',percent:0}
 ]),{percent:50,partial:true});
 assert.deepEqual(aggregateIngredientCoverage([
  {status:'at_home_quantity_unverified',percent:null}
 ]),{percent:null,partial:false});
 assert.deepEqual(aggregateIngredientCoverage([
  {status:'staple',percent:100},{status:'unknown_requirement',percent:null}
 ]),{percent:null,partial:false});
});

class Base{
 constructor(){
  this.inventory=[];
  this.read={status:'unknown_requirement',percent:null};
 }
 _coverage(){return this.read;}
 _v292Stock(item){
  return this.inventory.filter(row=>row.key===item?.key);
 }
 _langCode(){return 'el';}
}
const Panel=StockConsistencyMixin(Base);


test('stored-place lookup excludes depleted lots and preserves real unlimited/legacy stock',()=>{
 assert.deepEqual(availableLocationIds({lots:[
  {quantity:0,storageLocationId:'old-shelf'},
  {quantity:150,storageLocationId:'pantry'},
  {quantity:100,storageLocationId:'pantry'}
 ]}),['pantry','pantry']);
 assert.deepEqual(availableLocationIds({
  unlimited:true,storageLocationId:'spices'}),['spices']);
 assert.deepEqual(availableLocationIds({
  quantity:250,storageLocationId:'legacy-cupboard'}),['legacy-cupboard']);
 assert.deepEqual(availableLocationIds({
  quantity:0,storageLocationId:'ghost'}),[]);
 assert.deepEqual(availableLocationIds({
  quantity:300,lots:[{quantity:0,storageLocationId:'old-shelf'}]}),[]);
 const p=new Panel();
 p.inventory=[{key:'rice',quantity:300,lots:[
  {quantity:0,storageLocationId:'old-shelf'},
  {quantity:150,storageLocationId:'pantry'},
  {quantity:25,storageLocationId:'pantry'}
 ]}];
 p._v78Locations=()=>[
  {id:'old-shelf',name:'Ghost'},
  {id:'pantry',name:'Pantry'}
 ];
 assert.deepEqual(p._v218StorageNames({key:'rice'}),['Pantry']);
});

test('panel scopes infinity to stable IDs, never shared Greek display labels',()=>{
 const p=new Panel();
 p.inventory=[{key:'salt',name:'Αλάτι',unlimited:true}];
 assert.equal(p._coverage({}, {key:'salt',name:'Αλάτι'}).displayLabel,'∞');
 assert.equal(p._coverage({}, {key:'different-spice',name:'Αλάτι'}).percent,null);
});

test('stale positive top-level totals cannot fake a finite lot availability',()=>{
 const p=new Panel();
 p.read={status:'at_home_quantity_unverified',percent:null};
 p.inventory=[{key:'rice',quantity:200,lots:[{quantity:0}]}];
 assert.equal(p._coverage({match:{}},{key:'rice'}).percent,null);
 assert.equal(p._coverage({match:{}},{key:'rice'}).status,'unknown');
});
