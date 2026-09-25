import test from 'node:test';
import assert from 'node:assert/strict';
import {IngredientSeasonMixin,seasonChoiceVisible,seasonMonth} from '../custom_components/cook4me/frontend/ingredient-season-v223.js';

const fresh={key:'asparagus',lifecycle:{seasonality:{status:'reviewed',regions:[
 {country:'DE',months:[4,5,6],coverage:'listed_months_only'},
 {country:'GR',months:[2,3,4,5],coverage:'listed_months_only'}
]}}};

test('reviewed calendars use the shopping country, including different seasons for the same food',()=>{
 assert.equal(seasonChoiceVisible(fresh,'de',6),true);
 assert.equal(seasonChoiceVisible(fresh,'GR',6),false);
 assert.equal(seasonChoiceVisible(fresh,'DE',12),false);
 assert.equal(seasonChoiceVisible(fresh,'AU',12),true);
 assert.equal(seasonChoiceVisible(fresh,'',12),true);
});
test('unknown, preserved, not applicable, malformed and year-round ingredients remain visible',()=>{
 for(const row of [{name:'Frozen asparagus'},{lifecycle:{seasonality:{status:'unknown'}}},
  {lifecycle:{seasonality:{status:'not_applicable'}}},
  {lifecycle:{seasonality:{status:'reviewed',regions:[{country:'DE',months:[]}]}}},
  {lifecycle:{seasonality:{status:'reviewed',regions:[{country:'DE',months:['5']}]}}},
  {lifecycle:{seasonality:{status:'reviewed',regions:[{country:'DE',months:Array.from({length:12},(_,i)=>i+1)}]}}}]){
  for(let month=1;month<=12;month++)assert.equal(seasonChoiceVisible(row,'DE',month),true);
 }
 for(const month of [0,13,NaN,'6'])assert.equal(seasonChoiceVisible(fresh,'DE',month),true);
});
test('month rollover uses Home Assistant time zone',()=>{
 const now=new Date('2026-05-31T23:30:00Z');
 assert.equal(seasonMonth(now,'Europe/Berlin'),6);
 assert.equal(seasonMonth(now,'America/Los_Angeles'),5);
 assert.equal(seasonMonth(now,'invalid'),now.getMonth()+1);
});
test('disabled filtering leaves the catalog intact; selected ingredients survive and source objects never mutate',()=>{
 const Panel=IngredientSeasonMixin(class{}),p=new Panel(),rows=[fresh,{key:'unknown'}],before=structuredClone(rows);
 p._filters=()=>({seasonalIngredients:false});p._v223Context=()=>({country:'DE',month:12});
 p._todayIngredientIdentity=row=>row.key;
 assert.equal(p._v223SeasonRows(rows),rows);
 p._filters=()=>({seasonalIngredients:true});
 assert.deepEqual(p._v223SeasonRows(rows),[rows[1]]);
 assert.deepEqual(p._v223SeasonRows(rows,new Set(['asparagus'])),rows);
 assert.deepEqual(rows,before);
});
test('market country is independent of Greek UI and German supermarket labels',()=>{
 const Panel=IngredientSeasonMixin(class{}),p=new Panel();
 p._hass={config:{country:'GR',time_zone:'Europe/Athens'}};
 p._v79Settings={country:'DE',supermarketLanguage:'el'};
 p._uiIngredientLanguage=()=> 'el';p._v140SupermarketLanguage=()=> 'de';
 assert.equal(p._v223Context().country,'DE');
 p._v79Settings={country:'AU',supermarketLanguage:'de'};
 assert.equal(p._v223Context().country,'AU');
});
