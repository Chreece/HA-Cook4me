import test from 'node:test';
import assert from 'node:assert/strict';
import {ViewFiltersMixin,viewFilterMap,mergePreferencePatches,FILTER_VIEWS} from '../custom_components/cook4me/frontend/view-filters-v199.js';
import {ReceiptLauncherMixin,receiptPhotoAvailable} from '../custom_components/cook4me/frontend/receipt-launcher-v199.js';
const storage=new Map();globalThis.localStorage={getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)};
const clone=structuredClone;
class Legacy {
 constructor(){this._entryId='entry';this._tab='today';this.sent=[];this._hass={user:{id:crypto.randomUUID()},connection:{sendMessagePromise:async msg=>{this.sent.push(clone(msg));return this.respond?.(msg)||{};}}};}
 _prefKey(){return this._hass.user.id+'.'+this._entryId;}
 _filters(){if(this._v63FilterKey!==this._prefKey()){
  this._v63FilterKey=this._prefKey();let saved={};try{saved=JSON.parse(localStorage.getItem(this._prefKey())||'{}')||{};}catch{}
  this._v63Filters={diet:'vegetarian',languages:['de'],ingredients:[],nutrientTargets:{daily:{proteinTarget:60}},...saved.filters};
  this._v63Dirty=saved.pending||null;if(saved.lastTab)this._tab=saved.lastTab;
 }return this._v63Filters;}
 _persistPreferences(patch){this._v63PrefRevision=(this._v63PrefRevision||0)+1;this._v63Dirty={...this._v63Dirty,...patch};this._cachePreferences();void this._flushPreferences();}
 _v179ClearOpenRecipe(view){this.cleared=view;}
 _v63CloseRecipe(){this.closed=true;}
 _t(key){return key;}_message(){}_renderTabs(){}_renderTab(){}
}
const Panel=ViewFiltersMixin(Legacy);
const idle=async()=>{for(let i=0;i<8;i++)await Promise.resolve();};
test('all views get independent deep copies of the migrated filters',()=>{
 const h=new Panel(),today=h._filters();today.languages.push('el');today.nutrientTargets.daily.proteinTarget=90;
 h._tab='week';const week=h._filters();assert.deepEqual(week.languages,['de']);assert.equal(week.nutrientTargets.daily.proteinTarget,60);
 h._tab='today';assert.equal(h._filters(),today);assert.equal(h._filters().nutrientTargets.daily.proteinTarget,90);assert.equal(Object.keys(h._v199Filters).length,FILTER_VIEWS.length);
});
test('replaced filter objects remain in their owning view',()=>{
 const h=new Panel();h._filters();h._v63Filters={...h._v63Filters,maxCost:3};assert.equal(h._filters().maxCost,3);
 h._tab='week';assert.equal(h._filters().maxCost,undefined);h._tab='today';assert.equal(h._filters().maxCost,3);
});
test('view filters persist through a new browser component',()=>{
 const h=new Panel();h._filters().maxCost=4;h._tab='week';h._filters().onlyHome=true;h._cachePreferences();
 const other=new Panel();other._hass.user.id=h._hass.user.id;assert.equal(other._filters().onlyHome,true);other._tab='today';assert.equal(other._filters().maxCost,4);assert.equal(other._filters().onlyHome,undefined);
});
test('user and integration entry boundaries never share filters',()=>{
 const h=new Panel();h._filters().maxCost=4;h._cachePreferences();h._entryId='other';assert.equal(h._filters().maxCost,undefined);h._entryId='entry';assert.equal(h._filters().maxCost,4);
 h._hass.user.id='new-user';assert.equal(h._filters().maxCost,undefined);
});
test('malformed cache is ignored safely and view names are allowlisted',()=>{
 const h=new Panel();localStorage.setItem(h._prefKey(),'{broken');assert.equal(h._filters().diet,'vegetarian');
 assert.deepEqual(viewFilterMap({today:[],unknown:{},week:{maxCost:2}}),{week:{maxCost:2}});
});
test('saving a filter sends its owning view and clears stale open recipe',async()=>{
 const h=new Panel();h._filters();h._tab='week';h._persistPreferences({filters:{...h._filters(),maxCost:2}});await idle();
 assert.equal(h.sent[0].preferences.filtersByView.week.maxCost,2);assert.equal(h.cleared,'week');assert.ok(h.closed);
});
test('navigation-only persistence does not clear recipe state',async()=>{
 const h=new Panel();h._persistPreferences({lastTab:'week'});await idle();assert.equal(h.cleared,undefined);
});
test('server filters restore independently including nutrient and diet-profile settings',async()=>{
 const h=new Panel();h.respond=()=>({lastTab:'week',filtersByView:{today:{maxCost:2},week:{maxCost:8,dietProfile:'member:1',nutrientTargets:{daily:{proteinTarget:100}}}}});
 await h._restorePreferences();assert.equal(h._filters().maxCost,8);assert.equal(h._filters().dietProfile,'member:1');h._tab='today';assert.equal(h._filters().maxCost,2);
});
test('old server shared filters cannot overwrite saved per-view filters',async()=>{
 const h=new Panel();localStorage.setItem(h._prefKey(),JSON.stringify({lastTab:'week',filtersByView:{week:{maxCost:8},today:{maxCost:2}}}));
 h.respond=()=>({filters:{maxCost:99}});await h._restorePreferences();assert.equal(h._filters().maxCost,8);h._tab='today';assert.equal(h._filters().maxCost,2);
});
test('legacy server selection seeds separate views only once',async()=>{
 const h=new Panel();h.respond=()=>({filters:{maxCost:9}});await h._restorePreferences();assert.equal(h._filters().maxCost,9);h._tab='week';h._filters().maxCost=4;
 h._v63PrefsLoaded='';await h._restorePreferences();assert.equal(h._filters().maxCost,4);
});
test('user editing or navigating during restore wins over late server response',async()=>{
 const h=new Panel();let finish;h.respond=msg=>msg.preferences?{}:new Promise(resolve=>finish=resolve);
 const restoring=h._restorePreferences();h._persistPreferences({filters:{...h._filters(),maxCost:3},lastTab:'today'});finish({lastTab:'week',filtersByView:{today:{maxCost:99}}});await restoring;await idle();assert.equal(h._tab,'today');assert.equal(h._filters().maxCost,3);
});
test('late restore from a previous user is ignored',async()=>{
 const h=new Panel();let finish;h.respond=()=>new Promise(resolve=>finish=resolve);const pending=h._restorePreferences();h._hass.user.id='other';h._filters();finish({filtersByView:{today:{maxCost:99}}});await pending;assert.equal(h._filters().maxCost,undefined);
});
test('failed in-flight writes retain all view edits and retry without an offline loop',async()=>{
 const h=new Panel();let reject;h.respond=()=>new Promise((resolve,r)=>reject=r);h._persistPreferences({filters:{...h._filters(),maxCost:2}});
 h._tab='week';h._persistPreferences({filters:{...h._filters(),maxCost:8}});reject(new Error('offline'));await idle();
 assert.equal(h.sent.length,1);assert.equal(h._v63Dirty.filtersByView.today.maxCost,2);assert.equal(h._v63Dirty.filtersByView.week.maxCost,8);
 h.respond=()=>({});await h._flushPreferences();assert.equal(h.sent.length,2);assert.equal(h._v63Dirty,null);
});
test('caching during navigation retains the in-flight request for reload recovery',async()=>{
 const h=new Panel();let finish;h.respond=()=>new Promise(resolve=>finish=resolve);h._persistPreferences({filters:{...h._filters(),maxCost:4}});h._tab='week';h._filters();h._cachePreferences();
 assert.equal(JSON.parse(localStorage.getItem(h._prefKey())).pending.filtersByView.today.maxCost,4);finish({});await idle();assert.equal(JSON.parse(localStorage.getItem(h._prefKey())).pending,null);
});
test('retry merge keeps newest same-view changes and unrelated views',()=>{
 const old={filtersByView:{today:{maxCost:2},week:{maxCost:8}}},newer={filtersByView:{today:{maxCost:4}}};
 const result=mergePreferencePatches(old,newer);assert.equal(result.filtersByView.today.maxCost,4);assert.equal(result.filtersByView.week.maxCost,8);result.filtersByView.today.maxCost=10;assert.equal(newer.filtersByView.today.maxCost,4);
});
const available={aiEntityId:'',defaultAiEntityId:'ai_task.vision',aiChoices:[{id:'ai_task.vision'}]};
for(const [description,state,hass,expected] of [
 ['no metadata',null,{},false],['default selected',available,{},true],['explicit selected',{...available,aiEntityId:'ai_task.vision'},{},true],
 ['text-only not in permitted list',{...available,aiChoices:[]},{},false],['invalid override',{...available,aiEntityId:'ai_task.other'},{},false],
 ['no default',{...available,defaultAiEntityId:''},{},false],['unavailable',available,{states:{'ai_task.vision':{state:'unavailable'}}},false],
 ['unknown',available,{states:{'ai_task.vision':{state:'unknown'}}},false],['online',available,{states:{'ai_task.vision':{state:'ok'}}},true]
])test('receipt AI availability: '+description,()=>assert.equal(receiptPhotoAvailable(state,hass),expected));
class ScanBoundary{
 constructor(){this._v78State=available;this.context='a';this.calls=[];}
 _prefKey(){return this.context;}_message(text){this.message=text;}_v78Text(key){return key;}
 async _v78Open(mode){this.calls.push(['open',mode]);this._v78Dialog={};this._v78Draft={mode};await this.delay?.();}
 async _r195Start(force,camera){this.calls.push(['start',camera]);this._v78Draft.mode='receipt';}
 async _v78Photo(file){this.calls.push(['photo',file]);}
 async _v80Scan(mode){this.calls.push(['scan',mode]);}
 async _v78CaptureFrame(){this.calls.push(['capture']);}
 _v78SetStatus(text){this.message=text;}
}
class Scanner extends ReceiptLauncherMixin(ScanBoundary){_r199Launch(){}}
test('selected device photo uses manual opening and never starts the camera',async()=>{
 const h=new Scanner(),file={name:'receipt.jpg'};await h._r199ReceiptPhoto(file);assert.deepEqual(h.calls,[['open','manual'],['start',false],['photo',file]]);
});
test('cancelled file picker and unavailable AI do not open or upload',async()=>{
 const h=new Scanner();await h._r199ReceiptPhoto(null);h._v78State={};await h._r199ReceiptPhoto({});assert.equal(h.calls.length,0);assert.equal(h.message,'noAi');
});
test('uncertain stock save prevents photo import',async()=>{const h=new Scanner();h._v78Submitted={request_id:'pending'};await h._r199ReceiptPhoto({});assert.equal(h.calls.length,0);});
test('receipt photo double invocation is serialized',async()=>{
 const h=new Scanner();let finish;h.delay=()=>new Promise(resolve=>finish=resolve);const p=h._r199ReceiptPhoto({});await h._r199ReceiptPhoto({});assert.equal(h.calls.length,1);finish();await p;
});
test('account change during photo opening prevents upload',async()=>{
 const h=new Scanner();h.delay=async()=>{h.context='b';};await h._r199ReceiptPhoto({});assert.deepEqual(h.calls,[['open','manual']]);
});
test('camera receipt control captures on second press without resetting scan',async()=>{
 const h=new Scanner();h._v78Draft={mode:'receipt',scanPhase:'scanning'};h._v78Stream={};await h._v80Scan('receipt');assert.deepEqual(h.calls,[['capture']]);
});
test('camera receipt control refuses unavailable AI but nutrient mode delegates',async()=>{
 const h=new Scanner();h._v78State={};await h._v80Scan('receipt');assert.equal(h.calls.length,0);await h._v80Scan('nutrition');assert.deepEqual(h.calls,[['scan','nutrition']]);
});
