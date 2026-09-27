import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
  dietAlternativeLabels,
  dietReplacementLabel,
} from '../custom_components/cook4me/frontend/diet-substitution-guard-v253.js';

const row={
 replacement:{key:'tofu',name:'Firm tofu'},
 alternatives:[
  {key:'tofu',name:'Firm tofu'},
  {key:'mushrooms',name:'Mushrooms'},
  {key:'chickpeas',name:'Chickpeas'},
 ],
};

assert.deepEqual(
 dietAlternativeLabels(row,'en'),
 ['Firm tofu','Mushrooms','Chickpeas'],
);
assert.deepEqual(
 dietAlternativeLabels(row,'el'),
 ['Σφιχτό τόφου','Μανιτάρια','Ρεβίθια'],
);
assert.equal(dietReplacementLabel('ground_flaxseed_water','de'),'Gemahlene Leinsamen + Wasser');
assert.equal(dietReplacementLabel('plant_yogurt','el'),'Φυτικό γιαούρτι');

const panel=readFileSync(new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),'utf8');
const registration=readFileSync(new URL('../custom_components/cook4me/panel.py',import.meta.url),'utf8');
assert.match(panel,/diet-substitution-guard-v253\.js/);
assert.match(panel,/runtime-v253/);
assert.match(registration,/runtime-v253/);
assert.match(registration,/diet=253/);

console.log('CATALOG_OWNED_SUBSTITUTIONS_V253_FRONTEND=PASS');
