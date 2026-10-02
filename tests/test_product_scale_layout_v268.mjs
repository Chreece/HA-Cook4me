import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const layout=readFileSync(
 new URL('../custom_components/cook4me/frontend/product-scale-layout-v268.js',import.meta.url),
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

test('container tare controls are moved under the product weight field without being recreated',()=>{
 assert.match(layout,/\[data-v154-container-field\]/);
 assert.match(layout,/main \[data-draft="quantity"\]/);
 assert.match(layout,/closest\?\.\('\.field, label'\)/);
 assert.match(layout,/quantityField\.insertAdjacentElement\('afterend',block\)/);
 assert.doesNotMatch(layout,/innerHTML\s*=/);
 assert.match(layout,/grid-column:1 \/ -1/);
});

test('active frontend uses a new v268 runtime and outer layout mixin',()=>{
 assert.match(active,/product-scale-layout-v268\.js/);
 assert.match(active,/ProductScaleLayoutMixin\(SeasonalFilterBadgeMixin/);
 assert.match(active,/data-cook4me-ui-revision','268'/);
 assert.match(active,/runtime-v268/);
 assert.match(registration,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v268"/);
 assert.match(registration,/productscale=268/);
});
