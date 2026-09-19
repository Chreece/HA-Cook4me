import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const root=new URL("../",import.meta.url);
const source=readFileSync(new URL("custom_components/cook4me/frontend/cook4me-panel-v120.js",root),"utf8");
const bundle=readFileSync(new URL("custom_components/cook4me/frontend/cook4me-panel-v120-bundle.js",root),"utf8");

assert.match(source,/_nativeBarcodeScannerAvailable\(\)\{[\s\S]*?return false;/);
assert.match(source,/data-v120-torch/);
assert.match(source,/getCapabilities\(\)\?\.torch===true/);
assert.match(source,/applyConstraints\(\{advanced:\[\{torch:next\}\]\}\)/);
assert.match(source,/flashlight-off/);
assert.match(source,/\[data-v78-native\]/);
assert.match(bundle,/cook4me-recipe-hub-panel-v120/);

console.log("minimal v120 camera/torch contract passed");
