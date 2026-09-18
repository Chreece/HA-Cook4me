import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const root=new URL("../",import.meta.url);
const source=readFileSync(new URL("custom_components/cook4me/frontend/cook4me-panel-v121.js",root),"utf8");
const bundle=readFileSync(new URL("custom_components/cook4me/frontend/cook4me-panel-v121-bundle.js",root),"utf8");

assert.match(source,/history\.pushState/);
assert.match(source,/addEventListener\?\.\('popstate'/);
assert.match(source,/_v78Close\(true\)/);
assert.match(source,/power\.hidden=true/);
assert.match(source,/bottom\.prepend\(camera\)/);
assert.match(source,/camera\.hidden=false/);
assert.match(source,/camera-off-outline/);
assert.match(source,/_v120LiveTrack\(\)\|\|this\._v80CameraPending/);
assert.match(bundle,/cook4me-recipe-hub-panel-v121/);

console.log("minimal v121 mobile back/camera contract passed");
