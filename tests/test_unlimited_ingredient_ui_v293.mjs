import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
 explicitlyAssignedToIngredient,hasStoredAmount,
 reconcileStoredIngredient,IngredientsHomeFilterMixin
} from '../custom_components/cook4me/frontend/ingredient-home-filter-v293.js';

const LABELS={
 present:'Στο σπίτι',
 presentTitle:'Υπάρχει αλλά η ποσότητα είναι άγνωστη',
 unlimited:'Απεριόριστο απόθεμα (∞)'
};

test('unlimited stock resolves dash and stale zero to explicit infinity',()=>{
 for(const coverage of [
  {status:'unknown_requirement',percent:null},
  {status:'missing',percent:0},
  {status:'staple',percent:100},
  {status:'enough',percent:100,row:{unlimited:true}},
 ]) {
  const original=structuredClone(coverage);
  const saved=[{key:'salt',name:'Αλάτι',unlimited:true}];
  const result=reconcileStoredIngredient(coverage,saved,LABELS);
  assert.equal(result.percent,100,JSON.stringify(original));
  assert.equal(result.unlimited,true);
  assert.equal(result.displayLabel,'∞');
  assert.equal(result.displayTitle,LABELS.unlimited);
  assert.deepEqual(coverage,original,'no mutation to cached recipe evidence');
 }
});

test('unlimited is a general stock flag, independent of food name or source locale',()=>{
 for(const key of ['salt','black-pepper','water','sugar','olive-oil','rice','salt-ko']) {
  const row=reconcileStoredIngredient(
   {status:'unknown_requirement',percent:null},[{key,unlimited:true}],LABELS
  );
  assert.equal(row.displayLabel,'∞',key);
 }
});

test('unknown finite quantities remain unknown rather than invented infinity',()=>{
 const unknown={status:'incompatible_unit',percent:null};
 const result=reconcileStoredIngredient(unknown,[{key:'salt',quantity:250,lots:[{quantity:250}]}],LABELS);
 assert.equal(result.status,'at_home_quantity_unverified');
 assert.equal(result.percent,null);
 assert.equal(result.displayLabel,'Στο σπίτι');
 assert.equal(reconcileStoredIngredient(unknown,[],LABELS),unknown);
 assert.equal(reconcileStoredIngredient({status:'shortage',percent:0},[{quantity:0}],LABELS).percent,0);
 assert.equal(hasStoredAmount({unlimited:true}),true);
});

test('only explicitly saved catalog identities prove an infinite cross-language match',()=>{
 const item={key:'salt-ko',name:'소금'};
 const row={key:'seasoning-bin',name:'Αλάτι',unlimited:true,
  ingredientLinks:[{key:'salt-ko',name:'소금'}]};
 assert.equal(explicitlyAssignedToIngredient(item,row),true);
 assert.equal(explicitlyAssignedToIngredient({key:'different',name:'Αλάτι'},row),false);
 assert.equal(explicitlyAssignedToIngredient({key:'salt-ko',name:'소금'},
  {key:'another-bin',name:'Αλάτι',unlimited:true}),false);
 assert.equal(explicitlyAssignedToIngredient({key:'salt-ja'},
  {key:'seasoning-bin',unlimited:true,lots:[{
   ingredientLinks:[{key:'salt-ja',name:'塩'}]
  }]}),true);
 assert.equal(explicitlyAssignedToIngredient({key:'salt-ko'},
  {key:'seasoning-bin',unlimited:true,ingredientLinks:[]}),false);
});

class Fixture {
 constructor(){
  this._houseIngredients=[{
   key:'salt-bin',name:'Αλάτι',unlimited:true,
   ingredientLinks:[{key:'salt-ko',name:'소금'}]
  }];
 }
 _langCode(){return 'el';}
 _coverage(){return {status:'unknown_requirement',percent:null};}
 _v218StockMatches(item,row){return item.name===row.name;} // deliberately unsafe
}
const Current=IngredientsHomeFilterMixin(Fixture);

test('active frontend rejects same translated name, accepts explicit source key',()=>{
 const view=new Current();
 const yes=view._coverage({ingredients:[]},{key:'salt-ko',name:'소금'});
 assert.equal(yes.percent,100);
 assert.equal(yes.displayLabel,'∞');
 const no=view._coverage({ingredients:[]},{key:'another',name:'Αλάτι'});
 assert.equal(no.percent,null,'matching UI words cannot grant free unlimited stock');
});

test('active frontend source paths use new module and registered v293 element',()=>{
 const read=path=>readFileSync(new URL(path,import.meta.url),'utf8');
 const panel=read('../custom_components/cook4me/frontend/cook4me-panel-v180.js');
 const reg=read('../custom_components/cook4me/panel.py');
 assert.match(panel,/ingredient-home-filter-v293\.js/);
 assert.match(panel,/runtime-v293/);
 assert.match(reg,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v293"/);
 assert.match(reg,/infinite=293/);
});
