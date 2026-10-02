import test from 'node:test';
import assert from 'node:assert/strict';
import {depletedShoppingRows,ConsumptionDeductionMixin} from '../custom_components/cook4me/frontend/consumption-deduction-v272.js';
import {readFileSync} from 'node:fs';

test('depleted shopping rows are deduplicated and keep stable catalog keys',()=>{
 const rows=depletedShoppingRows([
  {identity:'k:mint',name:'Mint'},
  {identity:'k:mint',name:'Mint'},
  {identity:'n:paprika',name:'Paprika'},
 ]);
 assert.deepEqual(rows,[{key:'mint',name:'Mint'},{name:'Paprika'}]);
});

test('consumption confirmation is always sent as commit semantics',async()=>{
 class Base{
  constructor(){this.sent=[];this._pendingConsumption={id:'p',ingredients:[]};}
  async _api(type,data){this.sent.push({type,data});return {report:{depleted:[]}};}
  _renderProfile(){}
  _renderTab(){}
 }
 const panel=new (ConsumptionDeductionMixin(Base))();
 await panel._api('cook4me/v14/consumption_confirm',{pending_id:'p',ingredients:[],strict:true});
 assert.equal(panel.sent[0].data.strict,false);
});

test('unlimited pending rows are classified as non-deductible',()=>{
 class Base{_v131StockRow(identity){return identity==='k:salt'?{unlimited:true}:null;}}
 const panel=new (ConsumptionDeductionMixin(Base))();
 assert.equal(panel._v272FinitePendingRow({identity:'k:salt',stockUnlimited:true},null),false);
 assert.equal(panel._v272FinitePendingRow({identity:'k:salt'},{querySelector:()=>({value:'k:salt'})}),false);
 assert.equal(panel._v272FinitePendingRow({identity:'k:mint'},{querySelector:()=>({value:'k:mint'})}),true);
});

test('active runtime registers v272 outside v271 and cache busts registration',()=>{
 const panel=readFileSync(new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),'utf8');
 const registration=readFileSync(new URL('../custom_components/cook4me/panel.py',import.meta.url),'utf8');
 assert.match(panel,/consumption-deduction-v272\.js/);
 assert.match(panel,/runtime-v272/);
 assert.match(registration,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v272"/);
 assert.match(registration,/consumption=272/);
});
