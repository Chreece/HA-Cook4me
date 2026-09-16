import assert from 'node:assert/strict';
import {parseHTML} from 'linkedom';
const {window}=parseHTML('<!doctype html><html><body></body></html>');
for(const key of ['document','customElements','HTMLElement','Node','Event','CustomEvent','MutationObserver','Element','ShadowRoot'])if(window[key])globalThis[key]=window[key];
globalThis.window=window;globalThis.requestAnimationFrame=fn=>setTimeout(fn,0);globalThis.cancelAnimationFrame=clearTimeout;
globalThis.ResizeObserver=class{observe(){} disconnect(){}};globalThis.CSS={escape:String};
const storage=new Map();globalThis.localStorage={getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)};
const version=process.env.COOK4ME_TEST_PANEL_VERSION||'74';
await import(`../custom_components/cook4me/frontend/cook4me-panel-v${version}-bundle.js`);
const tick=()=>new Promise(resolve=>setTimeout(resolve,5));
const create=()=>{
 const panel=document.createElement(`cook4me-recipe-hub-panel-v${version}`);
 panel._entryId='one';panel._hass={user:{id:'alice'},language:'el',connection:{sendMessagePromise:async()=>({})}};
 panel._entries=[{entry_id:'one',profile:{},recipes:[]},{entry_id:'two',profile:{},recipes:[]}];
 panel._tab='week';panel._capabilities={};
 for(const name of ['_renderTab','_renderTabs','_updateBackgroundStatus','_decorateElementLoadingStates','_scheduleSnapshotPersist','_persistPreferences','_cachePreferences','_message'])panel[name]=()=>{};
 for(const name of ['_loadFullOverview','_loadBookState','_loadTodayOptions','_loadIngredientCatalog','_loadWeekState','_loadCurrencyState','_loadShoppingList','_loadInventoryState','_loadNutritionSettings'])panel[name]=async()=>{};
 return panel;
};

for(const initial of ['week','official']){
 const panel=create();panel._tab=initial;
 let release;panel._loadCapabilities=()=>new Promise(resolve=>{release=resolve;});
 const request=panel._requestSection(initial,{force:true});
 while(!release)await tick();
 // Use the actual navigation action while the previous section is refreshing.
 panel._requestSection=async()=>{};
 panel._selectV52Tab('shopping');
 assert.equal(panel._tab,'shopping');release();await request;
 assert.equal(panel._tab,'shopping',`${initial}: slow capability loading must preserve newer navigation`);
 panel.disconnectedCallback();
}

const panel=create();const calls=[];let rejectOld;
panel._hass.connection.sendMessagePromise=msg=>{
 calls.push(structuredClone(msg));
 if(msg.entry_id==='one')return new Promise((_,reject)=>{rejectOld=reject;});
 return Promise.resolve({});
};
panel._v63Dirty={lastTab:'week'};const first=panel._flushPreferences();
panel._entryId='two';panel._v63Dirty={lastTab:'shopping'};await panel._flushPreferences();
rejectOld(new Error('old device request failed'));await first;await tick();
assert.equal(calls.length,2,'Failed old-context save must not strand the new device preferences');
assert.equal(calls[1].entry_id,'two');assert.deepEqual(calls[1].preferences,{lastTab:'shopping'});
assert.equal(panel._v63Dirty,null);

let attempts=0;panel._hass.connection.sendMessagePromise=async()=>{attempts++;throw new Error('offline');};
panel._v63Dirty={lastTab:'today'};await panel._flushPreferences();await tick();
assert.equal(attempts,1,'Current offline context must wait for reconnect instead of retrying forever');
assert.deepEqual(panel._v63Dirty,{lastTab:'today'});
panel.disconnectedCallback();

const switched=create();switched._tab='official';let finishOld;let capabilityCalls=0;
switched._loadCapabilities=()=>{
 capabilityCalls++;
 return capabilityCalls===1?new Promise(resolve=>{finishOld=resolve;}):Promise.resolve();
};
const oldRequest=switched._requestSection('official');
switched._entryId='two';await switched._requestSection('official');
assert.equal(capabilityCalls,2,'Switching devices must not reuse the previous device section request');
finishOld();await oldRequest;switched.disconnectedCallback();

const loading=create();let finishSection;
loading._loadCapabilities=()=>new Promise(resolve=>{finishSection=resolve;});
const loadingRequest=loading._requestSection('official');
assert.ok(loading._v54RefreshingSections.has('official'));
loading._entryId='two';loading._resetEntryScopedUiState();
assert.equal(loading._v54RefreshingSections.size,0,'Changing devices must clear the old loading indicator');
finishSection();await loadingRequest;
assert.equal(loading._v54RefreshingSections.size,0,'An old request must not leave a loading indicator stuck');
loading.disconnectedCallback();

const concurrent=create();const finishes=[];
concurrent._loadCapabilities=()=>new Promise(resolve=>finishes.push(resolve));
const requests=[concurrent._requestSection('official'),concurrent._requestSection('official',{force:true})];
finishes[0]();await requests[0];
assert.ok(concurrent._v54RefreshingSections.has('official'),'Loading remains active while another refresh is pending');
finishes[1]();await requests[1];
assert.equal(concurrent._v54RefreshingSections.size,0);
concurrent.disconnectedCallback();
console.log('v74: slow refresh preserves navigation, cross-device saves drain, offline saves remain pending');
process.exit(0);
