import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const root=new URL("../",import.meta.url);
const source=readFileSync(new URL("custom_components/cook4me/frontend/cook4me-panel-v117.js",root),"utf8");
const bundle=readFileSync(new URL("custom_components/cook4me/frontend/cook4me-panel-v117-bundle.js",root),"utf8");
const panel=readFileSync(new URL("custom_components/cook4me/panel.py",root),"utf8");

assert.match(source,/import '\.\/cook4me-panel-v116\.js'/);
assert.match(source,/cook4me-recipe-hub-panel-v117/);
assert.match(source,/data-v78-pane="places"/);
assert.match(source,/data-v78-pane="scale"/);
assert.match(source,/data-v78-section="scale"/);
assert.match(source,/places\.after\(button\)/);
assert.match(source,/data-v117-container/);
assert.match(source,/data-use/);
assert.match(source,/data-edit/);
assert.match(source,/data-delete/);
assert.match(source,/v117ReadWeight/);
assert.match(source,/v117ContainerName/);
assert.match(source,/v117ContainerWeight/);
assert.match(source,/container_id:editing/);
assert.doesNotMatch(source,/id="v116Container"/);
assert.doesNotMatch(source,/id="v116ContainerName"/);
assert.match(bundle,/cook4me-recipe-hub-panel-v117/);
assert.match(panel,/cook4me-recipe-hub-panel-v117/);
assert.match(panel,/cook4me-panel-v117-bundle\.js/);

console.log("minimal v117 Smart scale menu/container contract passed");
