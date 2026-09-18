import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const root=new URL("../",import.meta.url);
const source=readFileSync(new URL("custom_components/cook4me/frontend/cook4me-panel-v119.js",root),"utf8");
const bundle=readFileSync(new URL("custom_components/cook4me/frontend/cook4me-panel-v119-bundle.js",root),"utf8");

assert.match(source,/cook4me-recipe-hub-panel-v119/);
assert.match(source,/button\.hidden=!mass/);
assert.match(source,/mdi:scale-balance/);
assert.match(source,/_v119FitInput\(frame\.querySelector\('\[data-v112-count\]'\),2\)/);
assert.match(source,/_v119FitInput\(frame\.querySelector\('\[data-v111-amount\]'\),4\)/);
assert.match(source,/event\.target\.closest\('\[data-v111-guide\]'\)/);
assert.match(source,/_v112Editor\(true,mode\)/);
assert.match(source,/_v119CaptureAi\(mode\)/);
assert.match(source,/_v113CanRestart\(\)/);
assert.match(source,/await this\._v112EditLot\(editLotId\)/);
assert.match(bundle,/cook4me-recipe-hub-panel-v119/);

console.log("minimal v119 capture UX contract passed");
