import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
  stepCookingModes,
  MODE_TEXT,
  SEB_REVIEWED_PROGRAM_NAMES,
  SEB_REVIEWED_LOCALIZED_PROGRAM_NAMES,
  SEB_ADDITIONAL_REVIEWED_PROGRAM_PAIRS,
  SEB_COMPANION_PROGRAM_NAMES,
} from '../custom_components/cook4me/frontend/recipe-step-modes-v259.js';

test('Greek UI localizes known German recipe mode',()=>{
  const row=stepCookingModes(
    {programKey:'PROGRAM_1',programName:'Druckgaren'},
    'el-GR',
  )[0];
  assert.equal(row.mode,'pressure');
  assert.equal(row.label,'Μαγείρεμα υπό πίεση');
  assert.equal(row.sourceName,'Druckgaren');
});

for (const [source,mode,greek] of [
  ['Cottura a pressione','pressure','Μαγείρεμα υπό πίεση'],
  ['Cocción al vapor','steam','Μαγείρεμα στον ατμό'],
  ['Mantener caliente','keep_warm','Διατήρηση θερμοκρασίας'],
  ['Rosolatura','browning','Ρόδισμα / σοτάρισμα'],
  ['Voorverwarmen','preheat','Προθέρμανση'],
  ['Gotowanie na parze','steam','Μαγείρεμα στον ατμό'],
]) {
  test('foreign recipe mode is translated to Greek UI: '+source,()=>{
    const row=stepCookingModes({programName:source},'el')[0];
    assert.equal(row.mode,mode);
    assert.equal(row.label,greek);
  });
}

test('unknown source program never becomes visible recipe-language text',()=>{
  const row=stepCookingModes(
    {programKey:'PROGRAM_999',programName:'Programme très spécial'},
    'el',
  )[0];
  assert.equal(row.mode,null);
  assert.equal(row.kind,'source');
  assert.equal(row.label,'Άλλη λειτουργία μαγειρέματος');
  assert.equal(row.sourceName,'Programme très spécial');
  assert.notEqual(row.label,row.sourceName);
});

test('descriptive key can localize an unknown provider name without overriding a recognized name',()=>{
  const fallback=stepCookingModes(
    {programKey:'PRESSURE_COOKING',programName:'Provider internal label'},
    'de',
  )[0];
  assert.equal(fallback.mode,'pressure');
  assert.equal(fallback.label,'Druckgaren');

  const explicit=stepCookingModes(
    {programKey:'STEAM',programName:'Browning'},
    'el',
  )[0];
  assert.equal(explicit.mode,'browning');
  assert.equal(explicit.label,'Ρόδισμα / σοτάρισμα');
});

test('opaque key without source name stays UI-language unknown',()=>{
  const row=stepCookingModes({programKey:'PROGRAM_999'},'de')[0];
  assert.equal(row.kind,'missing');
  assert.equal(row.label,'Garmodus nicht angegeben');
});

test('unsupported interface language falls back to English, never recipe language',()=>{
  const row=stepCookingModes({programName:'Druckgaren'},'xx')[0];
  assert.equal(row.label,'Pressure cooking');
});

test('all UI languages have the same visible-label keys',()=>{
  for(const lang of ['de','el','fr']){
    assert.deepEqual(Object.keys(MODE_TEXT[lang]).sort(),Object.keys(MODE_TEXT.en).sort());
  }
  assert.ok(MODE_TEXT.el.other);
});

test('active mixin takes cooking-mode language only from actual UI language',()=>{
  const source=readFileSync(
    new URL('../custom_components/cook4me/frontend/recipe-step-modes-v259.js',import.meta.url),
    'utf8',
  );
  assert.match(source,/decorateStepModes\(holder\.content,recipe,this\._langCode\?\.\(\)\|\|'en'\)/);
  const mixin=source.slice(source.indexOf('export const RecipeStepModesMixin'));
  assert.doesNotMatch(mixin,/_uiIngredientLanguage/);
});

test('active panel imports v290 modes with a fresh custom element and module URL',()=>{
  const panel=readFileSync(
    new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),
    'utf8',
  );
  const registration=readFileSync(
    new URL('../custom_components/cook4me/panel.py',import.meta.url),
    'utf8',
  );
  assert.match(panel,/recipe-step-modes-v290\.js/);
  assert.match(panel,/cook4me-recipe-hub-panel-v180-runtime-v290/);
  assert.match(panel,/data-cook4me-ui-revision','268'/);
  assert.match(panel,/runtime-v259/);
  assert.match(registration,/_URL_BASE = "\/cook4me_static\/2026\.9\.27\.2\/runtime-v249"/);
  assert.match(registration,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v292"/);
  assert.match(registration,/modes=290/);
  assert.match(registration,/progress=260/);
  assert.match(registration,/today=261/);
  assert.match(registration,/stability=262/);
  assert.match(registration,/seasonal=263/);
});


test('exact observed SEB program IDs AND multilingual names resolve 64 reviewed standard pairs',()=>{
 const expected={PROGRAM_200156:'high_pressure',PROGRAM_200157:'low_pressure',
   PROGRAM_200159:'browning',PROGRAM_200160:'simmering',PROGRAM_200161:'keep_warm'};
 assert.deepEqual(Object.keys(SEB_REVIEWED_PROGRAM_NAMES).sort(),Object.keys(expected).sort());
 const count=Object.values(SEB_REVIEWED_PROGRAM_NAMES).reduce((sum,row)=>sum+row.names.length,0);
 assert.equal(count,64);
 for(const [key,record] of Object.entries(SEB_REVIEWED_PROGRAM_NAMES)){
  assert.equal(record.mode,expected[key]);
  for(const originalName of record.names){
   const result=stepCookingModes({programKey:key,programName:originalName},'el')[0];
   assert.equal(result.mode,record.mode,key+' / '+originalName);
   assert.equal(result.label,MODE_TEXT.el[record.mode],key+' / '+originalName);
   assert.equal(result.sourceName,originalName,'source evidence remains preserved');
  }
 }
});


test('all 30 exact pairs in October 17 deep SEB sample resolve with source-locale semantics',()=>{
 const observed={
  PROGRAM_200156:['Cocción con alta presión','Cottura alta pressione','Cuisson haute pression','Garen unter Druck','Gotowanie pod wysokim ciśnieniem','High Pressure Cooking','Vaření pod vysokým tlakem','Yüksek basınçlı pişirme'],
  PROGRAM_200157:['Cocción con baja presión','Cuisson basse pression','Dampfgaren','Düşük basınçlı pişirme','Low Pressure Cooking'],
  PROGRAM_200159:['Anbraten','Browning','Dorage','Dorar','Mühürleme','Opékání','Rosolare','Smażenie'],
  PROGRAM_200160:['Gotowanie na wolnym ogniu'],
  PROGRAM_200161:['Keep Warm','Maintien au chaud','Mantener en caliente','Mantenimento in caldo','Sıcak tutma','Udržování teploty','Utrzymywanie ciepła','Warmhalten'],
 };
 assert.equal(Object.values(observed).reduce((n,a)=>n+a.length,0),30);
 assert.deepEqual(Object.keys(observed).sort(),Object.keys(SEB_REVIEWED_PROGRAM_NAMES).sort());
 for(const [key,names] of Object.entries(observed))for(const name of names){
  const mode=key==='PROGRAM_200157'&&name==='Dampfgaren'?'steam':SEB_REVIEWED_PROGRAM_NAMES[key].mode;
  for(const lang of ['en','de','el','fr']){
   const row=stepCookingModes({programKey:key,programName:name},lang)[0];
   assert.equal(row.mode,mode,key+' / '+name+' / '+lang);
   assert.equal(row.label,MODE_TEXT[lang][mode]);
   assert.equal(row.sourceName,name);
  }
 }
 assert.equal(SEB_REVIEWED_LOCALIZED_PROGRAM_NAMES.PROGRAM_200157.mode,'steam');
 assert.deepEqual(SEB_REVIEWED_LOCALIZED_PROGRAM_NAMES.PROGRAM_200157.names,['Dampfgaren']);
});
test('newly observed names do not authorize opaque ID or mismatched-name guessing',()=>{
 for(const [key,name] of [
  ['PROGRAM_200160','Unknown program'],['PROGRAM_200157','Unknown program'],
  ['PROGRAM_200160','Unknown Chinese publisher name'],['PROGRAM_200063','Unknown German publisher name'],
  ['PROGRAM_200160','Düşük basınçlı pişirme'],
 ]){
  assert.equal(stepCookingModes({programKey:key,programName:name},'el')[0].mode,null,key+' / '+name);
 }
 for(const key of ['PROGRAM_200160','PROGRAM_200157'])
  assert.equal(stepCookingModes({programKey:key},'de')[0].mode,null);
 const german=stepCookingModes({programKey:'PROGRAM_200157',programName:'Dampfgaren'},'el')[0];
 assert.equal(german.mode,'steam');
 assert.equal(german.label,MODE_TEXT.el.steam);
});

test('confirmed German SEB pair is high pressure, but generic source without ID remains generic pressure',()=>{
 assert.equal(stepCookingModes({programKey:'PROGRAM_200156',programName:'Garen unter Druck'},'en')[0].mode,'high_pressure');
 assert.equal(stepCookingModes({programName:'Garen unter Druck'},'de')[0].mode,'pressure');
 assert.equal(stepCookingModes({programKey:'PROGRAM_200159',programName:'Garen unter Druck'},'en')[0].mode,'pressure');
});

test('unknown key/name combinations cannot inherit unrelated reviewed meanings',()=>{
 for(const [programKey,programName] of [
  ['PROGRAM_200156','Unknown bespoke step'],['PROGRAM_200159','Unknown bespoke step'],
  ['PROGRAM_200160','Braten bei hoher Hitze'],['PROGRAM_200063','煮燉'],
  ['PROGRAM_200018','Manual P'],['PROGRAM_000005','Slow cook P2'],
 ]){
  assert.equal(stepCookingModes({programKey,programName},'el')[0].mode,null,
    'not reviewed: '+programKey+' / '+programName);
 }
 for(const programKey of Object.keys(SEB_REVIEWED_PROGRAM_NAMES)){
  assert.equal(stepCookingModes({programKey},'el')[0].mode,null,
   'a numeric program key alone is never enough');
 }
});


test('remaining 7 Cook4Me source occurrences use six reviewed pairs, without hiding intensity or boiling',()=>{
 const expected=[
  ['PROGRAM_200160','Варка на слабом огне','simmering',1],
  ['PROGRAM_200160','煮燉','simmering',2],
  ['PROGRAM_200160','غليان','boiling',1],
  ['PROGRAM_200063','Braten bei hoher Hitze','high_browning',1],
  ['PROGRAM_200063','Estofado alto','high_browning',1],
  ['PROGRAM_200063','Magas stir fry','high_browning',1],
 ];
 const observed=SEB_ADDITIONAL_REVIEWED_PROGRAM_PAIRS.flatMap(x=>x.names.map(name=>[x.programKey,name,x.mode]));
 assert.equal(observed.length,6);
 for(const [key,name,mode] of expected){
  assert.ok(observed.some(x=>x[0]===key&&x[1]===name&&x[2]===mode));
  for(const lang of ['en','de','el','fr']){
   const row=stepCookingModes({programKey:key,programName:name},lang)[0];
   assert.equal(row.kind,'program');
   assert.equal(row.mode,mode,key+' / '+name+' / '+lang);
   assert.equal(row.label,MODE_TEXT[lang][mode]);
  }
 }
 assert.equal(expected.reduce((a,row)=>a+row[3],0),7);
 const specimen=stepCookingModes({programKey:'PROGRAM_200063',programName:'Estofado alto'},'el')[0];
 assert.equal(specimen.label,'Δυνατό σοτάρισμα');
 assert.equal(stepCookingModes({programKey:'PROGRAM_200160',programName:'غليان'},'en')[0].label,'Boiling');
 for(const [key,name] of [['PROGRAM_200063','غليان'],['PROGRAM_200160','Magas stir fry']])
  assert.equal(stepCookingModes({programKey:key,programName:name},'en')[0].mode,null);
});

test('Companion Manual P / Slow cook P1-P3 are identified without creating false Cook4Me modes',()=>{
 const expected=[
  ['PROGRAM_200018','Manual P',5],['PROGRAM_000013','Manual P',2],
  ['PROGRAM_200009','Slow cook P1',3],['PROGRAM_000004','Slow cook P1',1],
  ['PROGRAM_000005','Slow cook P2',1],['PROGRAM_200011','Slow cook P3',1],
 ];
 assert.equal(Object.keys(SEB_COMPANION_PROGRAM_NAMES).length,expected.length);
 assert.equal(expected.reduce((sum,row)=>sum+row[2],0),13);
 for(const [key,name] of expected){
  assert.equal(SEB_COMPANION_PROGRAM_NAMES[key],name);
  for(const lang of ['en','de','el','fr']){
   const row=stepCookingModes({programKey:key,programName:name},lang)[0];
   assert.equal(row.kind,'companion');
   assert.equal(row.mode,null);
   assert.equal(row.label,MODE_TEXT[lang].companion+': '+name);
  }
  const wrong=stepCookingModes({programKey:key,programName:'Unrecognized mode name'},'el')[0];
  assert.equal(wrong.kind,'source');
  assert.equal(wrong.mode,null);
  assert.equal(stepCookingModes({programKey:key},'en')[0].kind,'missing');
 }
 const foreign=stepCookingModes({programs:[
  {programKey:'PROGRAM_200018',programName:'Manual P',applianceGroup:'APPLIANCE_GROUP_1'},
 ]},'en')[0];
 assert.equal(foreign.mode,null);
 assert.equal(foreign.kind,'missing');
 const unknown=stepCookingModes({programKey:'PROGRAM_999',programName:'Unexpected vendor name'},'el')[0];
 assert.equal(unknown.kind,'source');
 assert.equal(unknown.label,MODE_TEXT.el.other);
});

test('the SEB translation matrix renders correctly in all supported UI languages',()=>{
 const pressure={programKey:'PROGRAM_200156',programName:'High Pressure Cooking'};
 const warmer={programKey:'PROGRAM_200161',programName:'Sıcak tutma'};
 for(const lang of ['en','de','el','fr']){
  assert.equal(stepCookingModes(pressure,lang)[0].label,MODE_TEXT[lang].high_pressure);
  assert.equal(stepCookingModes(warmer,lang)[0].label,MODE_TEXT[lang].keep_warm);
 }
});
