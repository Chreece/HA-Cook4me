import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const actionRow=readFileSync(
 new URL('../custom_components/cook4me/frontend/recipe-action-row-v265.js',import.meta.url),
 'utf8',
);
const active=readFileSync(
 new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),
 'utf8',
);
const registration=readFileSync(
 new URL('../custom_components/cook4me/panel.py',import.meta.url),
 'utf8',
);

test('recipe actions flatten the old More disclosure into one icon-only row',()=>{
 assert.match(actionRow,/querySelectorAll\(':scope > details\.ui203-more'\)/);
 assert.match(actionRow,/dock\.insertBefore\(control,more\)/);
 assert.match(actionRow,/ui203-action-label/);
 assert.match(actionRow,/label=>label\.remove\(\)/);
 assert.match(actionRow,/flex-wrap:nowrap!important/);
 assert.match(actionRow,/flex:1 1 0!important/);
 assert.match(actionRow,/max-width:44px!important/);
});

test('blacklist action is present in the dock and removed from fullscreen header',()=>{
 assert.match(actionRow,/header \[data-v264-blacklist\]/);
 assert.match(actionRow,/button=>button\.remove\(\)/);
 assert.match(actionRow,/dock\.querySelector\('\[data-v264-blacklist\]'\)/);
 assert.match(actionRow,/dock\.append\(button\)/);
 assert.match(actionRow,/_v264Blacklist\?\.\(recipe\)/);
});

test('active runtime keeps v265 action row under the v266 seasonal indicator',()=>{
 assert.match(active,/recipe-action-row-v265\.js/);
 assert.match(active,/RecipeActionRowMixin\(RecipeBlacklistMixin/);
 assert.match(active,/data-cook4me-ui-revision','266'/);
 assert.match(active,/runtime-v266/);
 assert.match(registration,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v266"/);
 assert.match(registration,/actionrow=265/);
});
