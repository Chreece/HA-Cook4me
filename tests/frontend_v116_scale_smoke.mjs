import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const root=new URL("../",import.meta.url);
const source=readFileSync(new URL("custom_components/cook4me/frontend/cook4me-panel-v116.js",root),"utf8");
const bundle=readFileSync(new URL("custom_components/cook4me/frontend/cook4me-panel-v116-bundle.js",root),"utf8");
const panel=readFileSync(new URL("custom_components/cook4me/panel.py",root),"utf8");

assert.match(source,/import '\.\/cook4me-panel-v115\.js'/);
assert.match(source,/cook4me-recipe-hub-panel-v116/);
assert.match(source,/cook4me\/v37\/scale_state/);
assert.match(source,/cook4me\/v37\/inventory_reweigh/);
assert.match(source,/stableEntityId/);
assert.match(source,/tareButtonEntityId/);
assert.match(source,/callService\('button','press'/);
assert.match(source,/_renderRecipeDialog\(\)\{super\._renderRecipeDialog\(\)/);
assert.match(source,/data-v116-recipe/);
assert.match(source,/data-v112-edit-lot/);
assert.match(source,/data-v111-amount/);
assert.doesNotMatch(source,/_detailHtml\(recipe\)\{/);
assert.match(bundle,/cook4me-recipe-hub-panel-v116/);
assert.match(bundle,/cook4me\/v37\/scale_state/);
assert.match(panel,/cook4me-recipe-hub-panel-v116/);
assert.match(panel,/async_register_websocket_v37/);

console.log("minimal v116 smart-scale frontend contract passed");
