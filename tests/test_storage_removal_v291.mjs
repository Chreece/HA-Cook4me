import test from 'node:test';
import assert from 'node:assert/strict';
import {
 expiryStorageTarget, stockGroupIdentities, stockGroupTarget, StorageRemovalMixin, STORAGE_REMOVE_TEXT
} from '../custom_components/cook4me/frontend/storage-removal-v291.js';

test('expiring item always selects its single stable package; fallback is explicit whole ingredient',()=>{
 assert.deepEqual(expiryStorageTarget({lotId:'lot-abc',identity:'k:milk'}),{kind:'lot',lotId:'lot-abc'});
 assert.deepEqual(expiryStorageTarget({lotId:'',identity:'k:salt'}),{kind:'ingredient',identities:['k:salt']});
 assert.equal(expiryStorageTarget({lotId:'',identity:''}),null);
});

test('a grouped stock row resolves ALL underlying inventory identities without duplicates',()=>{
 const rows=[{id:'k:rice',group:'rice'},{id:'k:rice-2',group:'rice'},{id:'k:rice',group:'rice'},{id:'k:beans',group:'beans'}];
 assert.deepEqual(stockGroupIdentities(rows,'rice',r=>r.group,r=>r.id),['k:rice','k:rice-2']);
 assert.deepEqual(stockGroupIdentities(rows,'none',r=>r.group,r=>r.id),[]);
 assert.deepEqual(stockGroupIdentities(rows,'rice',r=>r.group,()=>''),[]);
});


test('product-name group deletes exactly its displayed lots, not all of the ingredient',()=>{
 const rows=[
  {key:'rice',lots:[{id:'lot-old',productName:'Old rice'},{id:'lot-new',productName:'New rice'}]},
  {key:'carrot',lots:[{id:'lot-carrot',productName:'Carrot'}]}
 ];
 const group={
  dataset:{v112Group:'new rice'},
  querySelectorAll(selector){
   if(selector==='[data-v112-edit-lot]')return [{dataset:{v112EditLot:'lot-new'}}];
   return [];
  }
 };
 const target=stockGroupTarget(group,rows,()=> 'k:rice',row=>'k:'+row.key);
 assert.deepEqual(target,{kind:'lots',scope:'group',lotIds:['lot-new']});
 assert.equal(stockGroupTarget(
  {...group,querySelectorAll:selector=>selector==='[data-v112-edit-lot]'?[{dataset:{v112EditLot:'stale-lot'}}]:[]},
  rows,()=> 'k:rice',row=>'k:'+row.key
 ),null,'stale product grouping must fail closed rather than deleting whole ingredient');
});

test('legacy unlimited stock groups use stable row indexes to delete one whole ingredient',()=>{
 const rows=[{key:'rice',lots:[{id:'lot-a'}]},{key:'salt',unlimited:true}];
 const group={
  dataset:{v112Group:'salt'},
  querySelectorAll(selector){
   if(selector==='[data-stock-row]')return [{dataset:{stockRow:'1'}}];
   return [];
  }
 };
 assert.deepEqual(stockGroupTarget(group,rows,row=>'k:'+row.key,row=>'k:'+row.key),
  {kind:'ingredient',scope:'group',identities:['k:salt']});
});

class FixtureBase {
 constructor(){
  this._entryId='fixture';
  this.shadowRoot=null;
  this._houseIngredients=[
   {key:'rice',name:'Rice',lots:[{id:'lot-old'},{id:'lot-new'}]},
   {key:'salt',name:'Salt',unlimited:true}
  ];
  this.calls=[];this.messages=[];this.syncCount=0;
 }
 _langCode(){return 'el';}
 _escape(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');}
 _prefKey(){return 'fixture-person';}
 _stockIdentity(row){return 'k:'+row.key;}
 _v112GroupKey(row){return 'k:'+row.key;}
 _syncEntryProfile(){this.syncCount++;}
 _message(message,error=false){this.messages.push({message,error});}
 async _api(type,data){
  this.calls.push({type,data});
  if(type==='cook4me/v33/product_details')return {lot:{id:data.lot_id},version:'server-v1'};
  if(type==='cook4me/v33/product_remove'){
   const rows=structuredClone(this._houseIngredients);
   const row=rows.find(x=>x.lots?.some(l=>l.id===data.lot_id));
   if(!row)throw Error('Missing package');
   row.lots=row.lots.filter(l=>l.id!==data.lot_id);
   return {houseIngredients:rows};
  }
  if(type==='cook4me/v14/inventory_remove')return {houseIngredients:this._houseIngredients.filter(x=>'k:'+x.key!==data.identity)};
  if(type==='cook4me/v14/inventory_state')return {houseIngredients:this._houseIngredients};
  throw Error('Unexpected API '+type);
 }
 _v142ExpiryRow(row){return '<button type="button" class="v142-expiry-row" data-v142-expiry-lot="'+row.lotId+'">edit</button>';}
}
const Fixture=StorageRemovalMixin(FixtureBase);

test('expiry action is a sibling button (not a nested button) and labels are Greek',()=>{
 const instance=new Fixture();
 const html=instance._v142ExpiryRow({lotId:'lot-old',identity:'k:rice',productName:'Rice'},0);
 assert.match(html,/<div class="v291-expiry-wrap"><button type="button" class="v142-expiry-row"/);
 assert.match(html,/<\/button><button class="v291-remove-btn"/);
 assert.match(html,/data-v291-expiry-index="0"/);
 assert.match(html,/Οριστική αφαίρεση αυτής της συσκευασίας/);
 assert.equal(instance._v142ExpiryRow({lotId:'',identity:''},1).startsWith('<div'),false);
});

test('confirmation refusal never touches the server and preserves stock',async()=>{
 const original=globalThis.confirm;globalThis.confirm=()=>false;
 try{
  const instance=new Fixture();
  await instance._v291Remove({kind:'ingredient',scope:'group',identities:['k:salt']},'Salt');
  assert.deepEqual(instance.calls,[]);
  assert.equal(instance._houseIngredients.length,2);
  assert.equal(instance._v291Removing,false);
 }finally{globalThis.confirm=original;}
});

test('delete one expiring lot with optimistic version and retain sibling package',async()=>{
 const original=globalThis.confirm,prompts=[];
 globalThis.confirm=message=>{prompts.push(message);return true;};
 try{
  const instance=new Fixture();
  await instance._v291Remove({kind:'lot',lotId:'lot-old'},'Rice');
  assert.deepEqual(instance.calls.map(x=>x.type),[
   'cook4me/v33/product_details','cook4me/v33/product_remove'
  ]);
  assert.deepEqual(instance.calls[1].data,{entry_id:'fixture',lot_id:'lot-old',expected_version:'server-v1'});
  assert.deepEqual(instance._houseIngredients[0].lots.map(l=>l.id),['lot-new']);
  assert.equal(instance._houseIngredients[1].key,'salt');
  assert.equal(instance.messages.at(-1).message,STORAGE_REMOVE_TEXT.el.removed);
  assert.match(prompts[0],/άλλες συσκευασίες/);
 }finally{globalThis.confirm=original;}
});

test('At home removal deletes all inventory from one group and retains other ingredients',async()=>{
 const original=globalThis.confirm;globalThis.confirm=()=>true;
 try{
  const instance=new Fixture();
  await instance._v291Remove({kind:'ingredient',scope:'group',identities:['k:rice']},'Rice');
  assert.equal(instance.calls[0].type,'cook4me/v14/inventory_remove');
  assert.equal(instance.calls[0].data.identity,'k:rice');
  assert.deepEqual(instance._houseIngredients.map(x=>x.key),['salt']);
  assert.equal(instance.syncCount,1);
  assert.equal(instance._v291Removing,false);
 }finally{globalThis.confirm=original;}
});


test('At home removes the entire displayed product group via individual versioned lots',async()=>{
 const original=globalThis.confirm;globalThis.confirm=()=>true;
 try{
  const instance=new Fixture();
  await instance._v291Remove({kind:'lots',scope:'group',lotIds:['lot-new']},'New rice');
  assert.deepEqual(instance.calls.map(x=>x.type),[
   'cook4me/v33/product_details','cook4me/v33/product_remove'
  ]);
  assert.deepEqual(instance._houseIngredients.find(x=>x.key==='rice').lots.map(l=>l.id),['lot-old']);
  assert.equal(instance._houseIngredients.find(x=>x.key==='salt').unlimited,true);
 }finally{globalThis.confirm=original;}
});

test('multi-package product group confirms once and removes all matching lots',async()=>{
 const original=globalThis.confirm;let prompts=0;
 globalThis.confirm=()=>{prompts++;return true;};
 try{
  const instance=new Fixture();
  await instance._v291Remove({kind:'lots',scope:'group',lotIds:['lot-old','lot-new']},'Rice product');
  assert.equal(prompts,1);
  assert.equal(instance.calls.filter(x=>x.type==='cook4me/v33/product_remove').length,2);
  assert.deepEqual(instance._houseIngredients.find(x=>x.key==='rice').lots,[]);
  assert.equal(instance._houseIngredients.some(x=>x.key==='salt'),true);
 }finally{globalThis.confirm=original;}
});

test('a failed version lookup never issues destructive mutation',async()=>{
 const original=globalThis.confirm;globalThis.confirm=()=>true;
 try{
  const instance=new Fixture();
  instance._api=async function(type,data){
   this.calls.push({type,data});
   if(type==='cook4me/v33/product_details')return {lot:{id:'wrong-lot'},version:'server-v1'};
   if(type==='cook4me/v14/inventory_state')return {houseIngredients:this._houseIngredients};
   throw Error('Must not write after mismatched version');
  };
  await instance._v291Remove({kind:'lot',lotId:'lot-old'},'Rice');
  assert.equal(instance.calls.filter(x=>x.type.includes('remove')).length,0);
  assert.equal(instance.messages.at(-1).error,true);
  assert.deepEqual(instance._houseIngredients[0].lots.map(x=>x.id),['lot-old','lot-new']);
 }finally{globalThis.confirm=original;}
});
