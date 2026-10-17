import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
  stepCookingModes,
  MODE_TEXT,
  SEB_REVIEWED_PROGRAM_NAMES,
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

test('active panel keeps v259 step modes under v269 runtime without changing global static runtime',()=>{
  const panel=readFileSync(
    new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),
    'utf8',
  );
  const registration=readFileSync(
    new URL('../custom_components/cook4me/panel.py',import.meta.url),
    'utf8',
  );
  assert.match(panel,/recipe-step-modes-v259\.js/);
  assert.match(panel,/data-cook4me-ui-revision','268'/);
  assert.match(panel,/runtime-v259/);
  assert.match(registration,/_URL_BASE = "\/cook4me_static\/2026\.9\.27\.2\/runtime-v249"/);
  assert.match(registration,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v284"/);
  assert.match(registration,/modes=259/);
  assert.match(registration,/progress=260/);
  assert.match(registration,/today=261/);
  assert.match(registration,/stability=262/);
  assert.match(registration,/seasonal=263/);
});


test('exact observed SEB program IDs AND multilingual names resolve 61 reviewed pairs',()=>{
 const expected={PROGRAM_200156:'high_pressure',PROGRAM_200157:'low_pressure',
   PROGRAM_200159:'browning',PROGRAM_200161:'keep_warm'};
 assert.deepEqual(Object.keys(SEB_REVIEWED_PROGRAM_NAMES).sort(),Object.keys(expected).sort());
 const count=Object.values(SEB_REVIEWED_PROGRAM_NAMES).reduce((sum,row)=>sum+row.names.length,0);
 assert.equal(count,61);
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

test('confirmed German SEB pair is high pressure, but generic source without ID remains generic pressure',()=>{
 assert.equal(stepCookingModes({programKey:'PROGRAM_200156',programName:'Garen unter Druck'},'en')[0].mode,'high_pressure');
 assert.equal(stepCookingModes({programName:'Garen unter Druck'},'de')[0].mode,'pressure');
 assert.equal(stepCookingModes({programKey:'PROGRAM_200159',programName:'Garen unter Druck'},'en')[0].mode,'pressure');
});

test('unknown key/name combinations cannot inherit unrelated reviewed meanings',()=>{
 for(const [programKey,programName] of [
  ['PROGRAM_200156','Unknown bespoke step'],['PROGRAM_200159','Unknown bespoke step'],
  ['PROGRAM_200160','煮燉'],['PROGRAM_200063','Estofado alto'],
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

test('the SEB translation matrix renders correctly in all supported UI languages',()=>{
 const pressure={programKey:'PROGRAM_200156',programName:'High Pressure Cooking'};
 const warmer={programKey:'PROGRAM_200161',programName:'Sıcak tutma'};
 for(const lang of ['en','de','el','fr']){
  assert.equal(stepCookingModes(pressure,lang)[0].label,MODE_TEXT[lang].high_pressure);
  assert.equal(stepCookingModes(warmer,lang)[0].label,MODE_TEXT[lang].keep_warm);
 }
});
