import test from 'node:test';
import assert from 'node:assert/strict';
import {compactDeviceHeader} from '../custom_components/cook4me/frontend/device-header-v207.js';
import {visibleStepCookingModes} from '../custom_components/cook4me/frontend/recipe-step-modes-v204.js';

for(const step of [null,{},'Pressure cooking', {instruction:'Chop and serve'}, {typeName:'Préparation'}, {typeName:'Serving'}, {programs:[],programName:'Browning'}, {programs:[{applianceGroup:'APPLIANCE_GROUP_1',programName:'Steaming'}]}]){
 test('no badge without a device operation: '+JSON.stringify(step),()=>assert.deepEqual(visibleStepCookingModes(step),[]));
}
test('real operation during a preparation step stays visible',()=>assert.equal(visibleStepCookingModes({typeName:'Preparation',programName:'Dorer'},'el')[0].mode,'browning'));
test('unknown program ID is still actual evidence, without guessing a mode',()=>{
 const modes=visibleStepCookingModes({programKey:'PROGRAM_999'});assert.equal(modes.length,1);assert.equal(modes[0].mode,null);
});
test('multiple operations retain order without empty badges',()=>assert.deepEqual(visibleStepCookingModes({programs:[{}, {programName:'Steaming'},null,{programName:'Keep warm'}]}).map(x=>x.mode),['steam','keep_warm']));
test('header uses actual HA name, not translated device type or entry title',()=>{
 const h=compactDeviceHeader({title:'Configuration',state:{deviceName:'Χύτρα κουζίνας'}},{phase:'cooking',label:'Μαγείρεμα'});
 assert.equal(h.name,'Χύτρα κουζίνας');assert.equal(h.label,'Μαγείρεμα');assert.equal(h.icon,'mdi:pot-steam');
});
test('header name falls back before first authorized snapshot',()=>{
 assert.equal(compactDeviceHeader({title:'My cooker'},{}).name,'My cooker');
 assert.equal(compactDeviceHeader({},{}).name,'Cook4Me');
});
test('revoked device does not retain its custom HA name',()=>assert.equal(compactDeviceHeader({accessible:false,title:'Cook4Me',state:{deviceName:'Private name'}},{phase:'unavailable'}).name,'Cook4Me'));
for(const [phase,icon] of [['offline','mdi:cloud-off-outline'],['waiting','mdi:sync'],['unavailable','mdi:alert-circle-outline'],['unknown','mdi:help-circle-outline'],['idle','mdi:check-circle-outline'],['warming','mdi:thermometer'],['paused','mdi:pause-circle-outline'],['done','mdi:check-circle-outline']]){
 test('status icon: '+phase,()=>assert.equal(compactDeviceHeader({}, {phase,label:phase}).icon,icon));
}
test('unknown telemetry cannot look ready',()=>{
 const h=compactDeviceHeader({}, {phase:'future_unknown',label:'Unknown'});assert.equal(h.icon,'mdi:help-circle-outline');
});
test('header does not inspect queued recipe, temperature or manufacture live state',()=>{
 const entry={title:'Cooker',state:{deviceName:'Kitchen',phase:'cooking',temperature:120},queuedSend:{}};
 const before=structuredClone(entry);const h=compactDeviceHeader(entry,{phase:'offline',label:'Offline'});
 assert.equal(h.phase,'offline');assert.equal(h.label,'Offline');assert.deepEqual(entry,before);
});
