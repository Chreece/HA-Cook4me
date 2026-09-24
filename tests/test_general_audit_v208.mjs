import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {ProductEditGuardMixin} from '../custom_components/cook4me/frontend/product-edit-guard-v208.js';
import {ProductEditorMixin} from '../custom_components/cook4me/frontend/scanner-editor-v196.js';
import {ViewFiltersMixin} from '../custom_components/cook4me/frontend/view-filters-v199.js';
const storage=new Map();
globalThis.localStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)};
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const tick=async()=>{for(let n=0;n<10;n++)await Promise.resolve();};
class PreferencesBoundary{
 constructor(){this._entryId='entry';this._tab='today';this.sent=[];this._hass={user:{id:crypto.randomUUID()},connection:{sendMessagePromise:msg=>{this.sent.push(structuredClone(msg));return this.respond(msg);}}};}
 _prefKey(){return this._hass.user.id+'.'+this._entryId;}
 _filters(){if(this.filterKey!==this._prefKey()){this.filterKey=this._prefKey();this._v63Filters={ingredients:[],languages:['el'],maxCost:2};this._v63Dirty=null;}return this._v63Filters;}
 _persistPreferences(patch){this._v63PrefRevision=(this._v63PrefRevision||0)+1;this._v63Dirty={...this._v63Dirty,...patch};this._cachePreferences();void this._flushPreferences();}
 _renderTabs(){}_renderTab(){}_message(){}_t(k){return k;}
}
const Preferences=ViewFiltersMixin(PreferencesBoundary);
for(const finishEarly of [false,true])test(`restore cannot overwrite a filter save ${finishEarly?'acknowledged during':'still pending after'} the read`,async()=>{
 const p=new Preferences(),write=deferred(),read=deferred();p.respond=msg=>msg.preferences?write.promise:read.promise;
 p._persistPreferences({filters:{...p._filters(),maxCost:7,ingredients:['k:rice']},lastTab:'today'});
 const restoring=p._restorePreferences();
 if(finishEarly){write.resolve({});await tick();}
 read.resolve({lastTab:'week',filtersByView:{today:{maxCost:99,ingredients:[]},week:{maxCost:10}}});await restoring;
 assert.equal(p._tab,'today');assert.equal(p._filters().maxCost,7);assert.deepEqual(p._filters().ingredients,['k:rice']);
 p._tab='week';assert.equal(p._filters().maxCost,10);
 write.resolve({});await tick();
});
test('restore merges queued and in-flight view patches without losing the newest same-view change',async()=>{
 const p=new Preferences(),write=deferred();p.respond=msg=>msg.preferences?write.promise:Promise.resolve({filtersByView:{today:{maxCost:99},week:{maxCost:99}}});
 p._persistPreferences({filters:{...p._filters(),maxCost:4}});p._tab='week';p._persistPreferences({filters:{...p._filters(),maxCost:8}});
 await p._restorePreferences();assert.equal(p._filters().maxCost,8);p._tab='today';assert.equal(p._filters().maxCost,4);
 write.resolve({});await tick();
});
test('a reconnect can restore on the new connection without waiting for an abandoned read',async()=>{
 const p=new Preferences(),old=deferred();p.respond=()=>old.promise;const abandoned=p._restorePreferences();let reads=0;
 p._hass.connection={sendMessagePromise:async()=>{reads++;return {filtersByView:{today:{maxCost:8}}};}};
 await p._restorePreferences();assert.equal(reads,1);assert.equal(p._filters().maxCost,8);
 old.resolve({filtersByView:{today:{maxCost:99}}});await abandoned;assert.equal(p._filters().maxCost,8);
});
test('an old restore failure cannot mark a replacement connection as loaded',async()=>{
 const p=new Preferences(),old=deferred();p.respond=()=>old.promise;const abandoned=p._restorePreferences();
 p._hass.connection={sendMessagePromise:async()=>({filtersByView:{today:{maxCost:8}}})};old.reject(new Error('old connection closed'));await abandoned;
 assert.notEqual(p._v63PrefsLoaded,p._prefKey());await p._restorePreferences();assert.equal(p._filters().maxCost,8);
});
test('preferences from a different user are still rejected',async()=>{
 const p=new Preferences(),read=deferred();p.respond=()=>read.promise;const pending=p._restorePreferences();p._hass.user.id='other-user';p._filters();read.resolve({filtersByView:{today:{maxCost:99}}});await pending;assert.equal(p._filters().maxCost,2);
});

// Load the entire production v112 class. Only its inherited HA/DOM boundary is
// replaced, so the async method under test is not a handwritten approximation.
class PackageBoundary{
 constructor(){this.isConnected=true;this._tab='profile';this.context='one';this.calls=[];this.messages=[];this._v78Dialog=null;this._v78Draft=null;}
 _prefKey(){return this.context;}_uiIngredientLanguage(){return 'el';}
 _api(type,data){this.calls.push([type,data]);return this.lookup(data.lot_id);}
 _v78Open(){this._v78Busy=false;this._v78Submitted=null;this._v78Dialog={};this._v78Draft={};this._v78Dirty=false;return this.openWait||Promise.resolve();}
 _v78RenderCapture(){}_message(text){this.messages.push(text);}
}
const registry=new Map([['cook4me-recipe-hub-panel-v111',PackageBoundary]]);
globalThis.customElements={get:name=>registry.get(name),define:(name,ctor)=>registry.set(name,ctor)};
const source=await readFile(new URL('../custom_components/cook4me/frontend/cook4me-panel-v112.js',import.meta.url),'utf8');
assert.ok(source.startsWith("import './cook4me-panel-v111.js';"));
await import('data:text/javascript;base64,'+Buffer.from(source.replace("import './cook4me-panel-v111.js';",'')).toString('base64'));
class Packages extends ProductEditGuardMixin(ProductEditorMixin(registry.get('cook4me-recipe-hub-panel-v112'))){_v196Focus(){} _v196Decorate(){}}
const details=id=>({lot:{id,quantity:500},unit:'g',ingredient:{key:'rice',name:'Ρύζι'},version:'rev-'+id});
test('rapid package clicks use the latest request, not whichever response finishes last',async()=>{
 const p=new Packages(),a=deferred(),b=deferred();p.lookup=id=>(id==='a'?a:b).promise;
 const first=p._v112EditLot('a'),second=p._v112EditLot('b');b.resolve(details('b'));await second;a.resolve(details('a'));await first;
 assert.equal(p._v78Draft.editLotId,'b');assert.equal(p._v78Draft.expectedVersion,'rev-b');
});
test('navigating away while package details load does not open a stale editor',async()=>{
 const p=new Packages(),read=deferred();p.lookup=()=>read.promise;const pending=p._v112EditLot('a');p._tab='week';read.resolve(details('a'));await pending;assert.equal(p._v78Dialog,null);
});
test('a manual draft opened during package lookup cannot be overwritten',async()=>{
 const p=new Packages(),read=deferred();p.lookup=()=>read.promise;const pending=p._v112EditLot('a');await p._v78Open();p._v78Draft.productName='My unsaved product';p._v78Dirty=true;const draft=p._v78Draft;read.resolve(details('a'));await pending;assert.equal(p._v78Draft,draft);assert.equal(draft.productName,'My unsaved product');assert.equal(draft.editLotId,undefined);
});
test('replaced editor during asynchronous opening is not populated by the old package',async()=>{
 const p=new Packages(),opening=deferred();p.openWait=opening.promise;p.lookup=async()=>details('a');const pending=p._v112EditLot('a');await tick();const replacement=p._v78Draft={productName:'Replacement'};p._v78Dialog={};opening.resolve();await pending;assert.equal(p._v78Draft,replacement);assert.equal(replacement.editLotId,undefined);
});
test('edits made while the editor finishes loading stay intact',async()=>{
 const p=new Packages(),opening=deferred();p.openWait=opening.promise;p.lookup=async()=>details('a');const pending=p._v112EditLot('a');await tick();p._v78Draft.productName='Typed while loading';p._v78Dirty=true;opening.resolve();await pending;assert.equal(p._v78Draft.productName,'Typed while loading');assert.equal(p._v78Draft.editLotId,undefined);
});
for(const field of ['_v78Busy','_v78Submitted'])test(`cannot start another edit while ${field} is set`,async()=>{
 const p=new Packages();p._v78Dialog={};p[field]=true;p.lookup=async()=>details('a');await p._v112EditLot('a');assert.equal(p.calls.length,0);
});
test('old package errors cannot leak into another user or view',async()=>{
 const p=new Packages(),read=deferred();p.lookup=()=>read.promise;const pending=p._v112EditLot('a');p.context='other';read.reject(new Error('Private package detail'));await pending;assert.equal(p.messages.length,0);
});
test('a successful ordinary package edit retains target, amount and optimistic revision',async()=>{
 const p=new Packages();p.lookup=async()=>details('a');await p._v112EditLot('a');assert.equal(p._v78Draft.editLotId,'a');assert.equal(p._v78Draft.quantity,500);assert.equal(p._v78Draft.expectedVersion,'rev-a');
});

test('stale busy flags from a closed old context do not lock a new package editor',async()=>{
 const p=new Packages();p._v78Busy=true;p._v78Submitted={};p.lookup=async()=>details('a');await p._v112EditLot('a');assert.equal(p._v78Draft.editLotId,'a');
});
test('late package error does not interrupt a different manual form',async()=>{
 const p=new Packages(),read=deferred();p.lookup=()=>read.promise;const pending=p._v112EditLot('a');await p._v78Open();read.reject(new Error('old error'));await pending;assert.equal(p.messages.length,0);
});
