import test from 'node:test';
import assert from 'node:assert/strict';
import {
 homeControlsCount,ingredientControlsCount,hasStoredAmount,
 reconcileStoredIngredient,IngredientsHomeFilterMixin
} from '../custom_components/cook4me/frontend/ingredient-home-filter-v292.js';

const greek={present:'Στο σπίτι',presentTitle:'Υπάρχει, ελέγξτε την ποσότητα'};

test('merges the existing Home controls into one Ingredients badge',()=>{
 assert.equal(homeControlsCount({}),0);
 assert.equal(homeControlsCount({onlyHome:true,preferExpiring:false,maxMissing:'1',avoidRecentDays:10}),4);
 assert.equal(ingredientControlsCount({ingredients:['rice','rice'],onlyHome:true}),2);
 assert.equal(ingredientControlsCount({seasonalIngredients:true,ingredients:[]}),0);
 assert.equal(homeControlsCount({maxMissing:'0',avoidRecentDays:7}),1);
});

test('only positive packages or unlimited stock show as physically present',()=>{
 assert.equal(hasStoredAmount({quantity:0,lots:[]}),false);
 assert.equal(hasStoredAmount({lots:[{quantity:0}]}),false);
 assert.equal(hasStoredAmount({lots:[{quantity:500}]}),true);
 assert.equal(hasStoredAmount({quantity:200}),true);
 assert.equal(hasStoredAmount({unlimited:true}),true);
});

test('stale zero or unknown backend coverage never means absent when linked stock exists',()=>{
 const row={status:'shortage',percent:0,row:{coverage:0,availableQuantity:0}};
 const found=reconcileStoredIngredient(row,[{lots:[{quantity:500}]}],greek);
 assert.equal(found.percent,null);
 assert.equal(found.status,'at_home_quantity_unverified');
 assert.equal(found.displayLabel,'Στο σπίτι');
 assert.equal(row.percent,0,'recipe match source is never mutated');
 assert.equal(reconcileStoredIngredient({status:'incompatible_unit',percent:null},
 [{lots:[{quantity:500}]}],greek).displayLabel,'Στο σπίτι');
 assert.equal(reconcileStoredIngredient(row,[{unlimited:true}],greek).percent,100);
});

test('known amount calculations and absent stock must not be overruled by labels',()=>{
 const zero={status:'shortage',percent:0};
 assert.equal(reconcileStoredIngredient(zero,[{lots:[{quantity:0}]}],greek),zero);
 assert.equal(reconcileStoredIngredient(zero,[],greek),zero);
 assert.equal(reconcileStoredIngredient({status:'shortage',percent:40},[{quantity:200}],greek).percent,40);
 assert.equal(reconcileStoredIngredient({status:'staple',percent:100},[{quantity:100}],greek).percent,100);
});

class Fixture {
 constructor(){this._houseIngredients=[{key:'dry-rice',name:'Ρύζι',lots:[{quantity:500}],ingredientLinks:[{key:'rice-jp'}]}];this._filter={ingredients:[],onlyHome:true,preferExpiring:true,maxMissing:'',avoidRecentDays:7};}
 _filters(){return this._filter;}
 _filterActive(key){return key==='ingredients'?!!this._filter.ingredients.length:key==='home'?!!this._filter.onlyHome:false;}
 _v98FilterCount(){return 0;}
 _v93FilterSummary(){return '0';}
 _langCode(){return 'el';}
 _coverage(){return {status:'shortage',percent:0};}
 _v218StockMatches(item,row){return row.ingredientLinks?.some(link=>link.key===item.key);}
}
const Current=IngredientsHomeFilterMixin(Fixture);

test('Home button disappears but its settings activate the preferred Ingredients button',()=>{
 const view=new Current();
 assert.equal(view._filterActive('home'),false);
 assert.equal(view._filterActive('ingredients'),true);
 assert.equal(view._v98FilterCount('ingredients'),1);
 assert.equal(view._v93FilterSummary('ingredients'),'Διαθέσιμα στο σπίτι');
 assert.equal(view._coverage({}, {key:'rice-jp',name:'米'}).displayLabel,'Στο σπίτι');
 assert.equal(view._coverage({}, {key:'unrelated',name:'Ρύζι'}).percent,0,
   'identical Greek display name is not proof of a stock match');
});
