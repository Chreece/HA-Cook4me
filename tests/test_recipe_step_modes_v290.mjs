import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
 stepCookingModes, visibleStepCookingModes, MODE_TEXT, SEB_REVIEWED_PROGRAM_NAMES,
 SEB_REVIEWED_LOCALIZED_PROGRAM_NAMES, SEB_ADDITIONAL_REVIEWED_PROGRAM_PAIRS,
 SEB_COMPANION_PROGRAM_NAMES
} from '../custom_components/cook4me/frontend/recipe-step-modes-v290.js';

// Sanitized program-name and key evidence from the user's Oct 17 cache audit.
// Original titles, recipe IDs, instructions, users and credentials are excluded.
// 80 distinct (programKey, programName) pairs; 81 language observations because
// SEB publishes "Keep Warm" for both English and Russian.
const OBSERVED_NAMES=Object.freeze({
 PROGRAM_000004:['Slow cook P1'],
 PROGRAM_000005:['Slow cook P2'],
 PROGRAM_000013:['Manual P'],
 PROGRAM_200009:['Slow cook P1'],
 PROGRAM_200011:['Slow cook P3'],
 PROGRAM_200018:['Manual P'],
 PROGRAM_200063:['Braten bei hoher Hitze','Estofado alto','Magas stir fry'],
 PROGRAM_200156:['Cocción con alta presión','Cottura alta pressione','Cozedura a alta pressão','Cuisson haute pression','Garen unter Druck','Gotowanie pod wysokim ciśnieniem','Gătire la presiune înaltă','High Pressure Cooking','Kuhanje pod visokim pritiskom','Magas nyomású főzés','Varenie pod vysokým tlakom','Vaření pod vysokým tlakem','Yüksek basınçlı pişirme','Готвене под високо налягане','Приготовление под высоким давлением','Приготування під високим тиском','طهي بضغط عالي','圧力調理','고압 조리'],
 PROGRAM_200157:['Cocción con baja presión','Cuisson basse pression','Dampfgaren','Gotowanie pod niskim ciśnieniem','Kuhanje na nizkem pritisku','Low Pressure Cooking','Varenie pod nízkym tlakom','Vaření pod nízkým tlakem','Готвене под ниско налягане','Приготовление под низким давлением','低壓烹飪','저압 조리'],
 PROGRAM_200159:['Alourar','Anbraten','Browning','Dorage','Dorar','Mühürleme','Opékání','Pečenje','Pirítás','Prženje','Rosolare','Rumenire','Smażenie','Запечатване','تحمير','炒める'],
 PROGRAM_200160:['Mijotage','Варка на слабом огне','غليان','煮燉'],
 PROGRAM_200161:['Keep Warm','Maintien au chaud','Mantener en caliente','Mantenimento in caldo','Manter quente','Menţinere la cald','Održavanje topline','Ohranjanje toplote','Sıcak tutma','Tartsa melegen','Udržať teplé','Udržování teploty','Utrzymywanie ciepła','Warmhalten','Поддържане на топлината','Підтримання тепла','الاحتفاظ بالحرارة','保温','保溫','보온'],
});
const companion=Object.keys(SEB_COMPANION_PROGRAM_NAMES);
const observed=Object.entries(OBSERVED_NAMES).flatMap(([key,names])=>names.map(name=>({key,name})));
const expectedMode=(key,name)=>{
 if(companion.includes(key))return null;
 if(key==='PROGRAM_200157'&&name==='Dampfgaren')return 'steam';
 if(key==='PROGRAM_200160'&&name==='غليان')return 'boiling';
 if(key==='PROGRAM_200063')return 'high_browning';
 return ({PROGRAM_200156:'high_pressure',PROGRAM_200157:'low_pressure',
 PROGRAM_200159:'browning',PROGRAM_200160:'simmering',PROGRAM_200161:'keep_warm'})[key]||null;
};

test('all 80 observed SEB key/name pairs translate correctly into each UI language',()=>{
 assert.equal(observed.length,80);
 for(const {key,name} of observed){
  const mode=expectedMode(key,name);
  for(const lang of ['en','de','el','fr']){
   const got=stepCookingModes({programKey:key,programName:name,applianceGroup:'APPLIANCE_GROUP_15'},lang)[0];
   assert.equal(got.mode,mode,key+' '+name+' '+lang);
   assert.equal(got.kind,mode?'program':'companion',key+' '+name+' '+lang);
   assert.equal(got.label,mode?MODE_TEXT[lang][mode]:MODE_TEXT[lang].companion+': '+name);
   assert.equal(got.sourceName,name);
   assert.equal(got.programKey,key);
  }
 }
});

test('new Slovenian names share canonical SEB keys across all recipe languages',()=>{
 for(const [key,name,mode,greek] of [
  ['PROGRAM_200157','Kuhanje na nizkem pritisku','low_pressure','Μαγείρεμα σε χαμηλή πίεση'],
  ['PROGRAM_200159','Pečenje','browning','Ρόδισμα / σοτάρισμα'],
  ['PROGRAM_200161','Ohranjanje toplote','keep_warm','Διατήρηση θερμοκρασίας'],
 ]){
  assert.ok(SEB_REVIEWED_PROGRAM_NAMES[key].names.includes(name),name);
  const got=stepCookingModes({programKey:key,programName:name},'el-GR')[0];
  assert.equal(got.mode,mode);
  assert.equal(got.label,greek);
 }
 assert.equal(Object.values(SEB_REVIEWED_PROGRAM_NAMES).reduce((sum,r)=>sum+r.names.length,0),67);
});

test('Croatian and Polish screenshot programs do not fall back to Greek Other mode',()=>{
 for(const [key,name,mode] of [
  ['PROGRAM_200159','Prženje','browning'],
  ['PROGRAM_200156','Kuhanje pod visokim pritiskom','high_pressure'],
  ['PROGRAM_200161','Održavanje topline','keep_warm'],
  ['PROGRAM_200159','Smażenie','browning'],
  ['PROGRAM_200156','Gotowanie pod wysokim ciśnieniem','high_pressure'],
 ]){
  const got=visibleStepCookingModes({programs:[{programKey:key,programName:name}]},'el')[0];
  assert.equal(got.mode,mode,name);
  assert.equal(got.label,MODE_TEXT.el[mode],name);
  assert.notEqual(got.label,MODE_TEXT.el.other,name);
 }
});

test('ambiguous codes and unreviewed names remain protected from false translation',()=>{
 assert.equal(SEB_REVIEWED_LOCALIZED_PROGRAM_NAMES.PROGRAM_200157.mode,'steam');
 assert.equal(stepCookingModes({programKey:'PROGRAM_200157',programName:'Dampfgaren'},'el')[0].mode,'steam');
 assert.ok(SEB_ADDITIONAL_REVIEWED_PROGRAM_PAIRS.some(x=>x.programKey==='PROGRAM_200160'));
 assert.equal(stepCookingModes({programKey:'PROGRAM_200160',programName:'غليان'},'el')[0].mode,'boiling');
 for(const [key,name] of [
  ['PROGRAM_200156','Unreviewed mode name'],['PROGRAM_200157','Unreviewed mode name'],
  ['PROGRAM_200159','Unreviewed mode name'],['PROGRAM_200160','Unreviewed mode name'],
  ['PROGRAM_200161','Unreviewed mode name'],['PROGRAM_200159','Ohranjanje toplote'],
  ['PROGRAM_200161','Pečenje']
 ]){
  const row=stepCookingModes({programKey:key,programName:name},'el')[0];
  assert.equal(row.mode,null,key+' '+name);
  assert.equal(row.label,MODE_TEXT.el.other);
 }
 for(const key of Object.keys(OBSERVED_NAMES))
  assert.equal(stepCookingModes({programKey:key},'el')[0].mode,null,'numeric key only: '+key);
 assert.equal(visibleStepCookingModes({programs:[
  {programKey:'PROGRAM_200159',programName:'Pečenje',applianceGroup:'APPLIANCE_GROUP_1'}
 ]},'el').length,0);
});

test('panel and HA registration activate the new module and element',()=>{
 const read=path=>readFileSync(new URL(path,import.meta.url),'utf8');
 const panel=read('../custom_components/cook4me/frontend/cook4me-panel-v180.js');
 const reg=read('../custom_components/cook4me/panel.py');
 assert.match(panel,/from '\.\/recipe-step-modes-v290\.js'/);
 assert.match(panel,/customElements\.define\('cook4me-recipe-hub-panel-v180-runtime-v290'/);
 assert.match(reg,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v290"/);
 assert.match(reg,/modes=290/);
 assert.doesNotMatch(reg,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v284"/);
});
