import test from 'node:test';
import assert from 'node:assert/strict';
import {stepCookingModes,MODE_TEXT} from '../custom_components/cook4me/frontend/recipe-step-modes-v204.js';

for(const [name,mode] of [
 ['Pressure cooking','pressure'],['CUISSON SOUS PRESSION','pressure'],['Druckgaren','pressure'],
 ['Μαγείρεμα υπό πίεση','pressure'],['Browning','browning'],['Dorer','browning'],
 ['Anbraten','browning'],['Steaming','steam'],['Dampfgaren','steam'],['Cuisson vapeur','steam'],
 ['Simmering','simmering'],['Mijoter','simmering'],['Keep warm','keep_warm'],['Warmhalten','keep_warm'],
 ['Maintien au chaud','keep_warm'],['Reheat','reheat'],['Réchauffer','reheat'],
 ['Gentle cooking','gentle'],['High pressure cooking','high_pressure'],['Low pressure cooking','low_pressure'],
 ['Cuisson rapide','quick'],['Preheating','preheat'],['Slow cooking','slow'],
])test('explicit program name: '+name,()=>assert.equal(stepCookingModes({programName:name},'el')[0].mode,mode));
test('Greek UI independent of German recipe and supermarket language',()=>{
 const row=stepCookingModes({programKey:'PROGRAM_1',programName:'Druckgaren'},'el-GR')[0];
 assert.equal(row.label,'Μαγείρεμα υπό πίεση');assert.equal(row.programKey,'PROGRAM_1');assert.equal(row.sourceName,'Druckgaren');
});
test('program ID is never decoded as pressure, browning or another numeric mode',()=>{
 const row=stepCookingModes({programKey:'PROGRAM_1'},'en')[0];assert.equal(row.mode,null);assert.equal(row.kind,'missing');
 assert.equal(row.programKey,'PROGRAM_1');
});
test('unknown provider name preserved instead of invented translation',()=>{
 const row=stepCookingModes({programKey:'PROGRAM_9',programName:'Uncatalogued mode'},'el')[0];
 assert.equal(row.mode,null);assert.equal(row.label,'Uncatalogued mode');assert.equal(row.kind,'source');
});
test('mode chosen from explicit name not conflicting descriptive key',()=>{
 assert.equal(stepCookingModes({programKey:'STEAM',programName:'Browning'},'en')[0].mode,'browning');
});
test('known symbolic key supported only without a name',()=>assert.equal(stepCookingModes({programKey:'PRESSURE_COOKING'})[0].mode,'pressure'));
test('no keyword inference from instruction, notes or recipe-wide fields',()=>{
 for(const s of ['Pressure cooking',{instruction:'Do not pressure cook.',notes:'browning'},{type:'COOKING',instruction:'Pressure cooking'}]){
  assert.equal(stepCookingModes(s)[0].kind,'missing');
 }
});
test('only explicit preparation type labels are marked preparation',()=>{
 assert.equal(stepCookingModes({typeName:'Préparation'})[0].mode,'preparation');
 assert.equal(stepCookingModes({type:'STEP_TYPE_1'})[0].mode,null);
});
test('multiple operations retain step-specific source order',()=>{
 const step={programs:[{programName:'Browning'},{programName:'Pressure cooking'},{programName:'Keep warm'}]};
 assert.deepEqual(stepCookingModes(step).map(r=>r.mode),['browning','pressure','keep_warm']);
});
test('empty program evidence does not borrow a stale flattened program',()=>{
 assert.equal(stepCookingModes({programs:[],programName:'Pressure cooking'})[0].mode,null);
});
test('explicit foreign-appliance programs are not displayed as Cook4Me modes',()=>{
 const rows=stepCookingModes({programs:[{programName:'Steaming',applianceGroup:'APPLIANCE_GROUP_1'}]});
 assert.equal(rows[0].mode,null);
});
test('malformed source data is harmless',()=>{
 for(const s of [null,undefined,0,[],{},true,{programName:{}},{programs:[null,3,{programName:{}}]}]){
  assert.equal(stepCookingModes(s)[0].kind,'missing');
 }
});
test('source steps are never mutated',()=>{
 const step={programs:[{programName:'Pressure cooking',programKey:'PROGRAM_1'}],instruction:'cook'};
 const before=structuredClone(step);stepCookingModes(step,'el');assert.deepEqual(step,before);
});
test('unicode accents and internal spacing normalize only known full labels',()=>{
 assert.equal(stepCookingModes({programName:' Re\u0301chauffer  '})[0].mode,'reheat');
 assert.equal(stepCookingModes({programName:'pressure cooking lid cleaning'})[0].kind,'source');
});
test('unsupported UI language has a stable English fallback',()=>assert.equal(stepCookingModes({programName:'Dorer'},'xx')[0].label,'Browning'));
test('known program still shown during add-ingredients or preparation stage',()=>{
 assert.equal(stepCookingModes({typeName:'Preparation',programName:'Browning'})[0].mode,'browning');
});
test('localization has equal keys in all supported interface languages',()=>{
 for(const lang of ['de','el','fr'])assert.deepEqual(Object.keys(MODE_TEXT[lang]).sort(),Object.keys(MODE_TEXT.en).sort());
});
