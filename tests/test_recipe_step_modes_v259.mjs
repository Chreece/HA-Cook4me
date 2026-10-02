import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
  stepCookingModes,
  MODE_TEXT,
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
  assert.match(registration,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v272"/);
  assert.match(registration,/modes=259/);
  assert.match(registration,/progress=260/);
  assert.match(registration,/today=261/);
  assert.match(registration,/stability=262/);
  assert.match(registration,/seasonal=263/);
});
