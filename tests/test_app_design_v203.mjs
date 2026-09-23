import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DESIGN_TEXT,designText,restyleRecipe,buildActionDock,decorateDay,AppDesignMixin} from '../custom_components/cook4me/frontend/app-design-v203.js';
import {APP_THEME} from '../custom_components/cook4me/frontend/app-theme-v203.js';

test('English German Greek have identical presentation keys',()=>{
 for(const lang of ['de','el'])assert.deepEqual(Object.keys(DESIGN_TEXT[lang]).sort(),Object.keys(DESIGN_TEXT.en).sort());
});
test('locale tags fall back predictably',()=>{
 assert.equal(designText('el-GR','more'),'Περισσότερα');assert.equal(designText('de_DE','more'),'Mehr');assert.equal(designText('unavailable','more'),'More');assert.equal(designText(null,'unknown'),'');
});
test('public helpers tolerate empty render targets',()=>{assert.equal(restyleRecipe(null,{}),null);assert.equal(buildActionDock(null,{}),undefined);assert.equal(decorateDay(null,{}),undefined);});
test('visual module does not introduce network or mutation routes',()=>{
 const source=readFileSync(new URL('../custom_components/cook4me/frontend/app-design-v203.js',import.meta.url),'utf8');
 assert.doesNotMatch(source,/\b(?:fetch|XMLHttpRequest|WebSocket)\s*\(/);
 assert.doesNotMatch(source,/\._api\s*\(|callService\s*\(/);assert.doesNotMatch(source,/localStorage|sessionStorage/);
});
test('styles inherit HA theme and retain reduced motion / forced colors',()=>{
 for(const property of ['--primary-color','--primary-background-color','--primary-text-color','--card-background-color'])assert.ok(APP_THEME.includes(property));
 assert.match(APP_THEME,/prefers-reduced-motion/);assert.match(APP_THEME,/forced-colors/);
 assert.doesNotMatch(APP_THEME,/@import|https?:|font-face/);
});
test('visual mixin does not replace card actions or backend filtering',()=>{
 const keys=Object.getOwnPropertyNames(AppDesignMixin(class{}).prototype);
 for(const name of ['_api','_v78Save','_v196Lookup','_r195Action','_v76Allowed','_filters','_v110Select','_generateWeek','_v111Canvas'])assert.ok(!keys.includes(name),name);
});
test('runtime URL query and custom element match the activated design',()=>{
 const panel=readFileSync(new URL('../custom_components/cook4me/panel.py',import.meta.url),'utf8');
 const active=readFileSync(new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),'utf8');
 const runtime=panel.match(/_URL_BASE = "[^"\n]*\/runtime-v(\d+)"/)[1];assert.ok(Number(runtime)>=203);assert.ok(panel.includes('&runtime='+runtime));
 assert.ok(active.includes('AppDesignMixin('));assert.ok(active.includes('cook4me-recipe-hub-panel-v180-runtime-v'+runtime));
 for(const name of ['SelectedFilterMixin','RecipeGapsMixin','ScannerCameraMixin','WeeklyProgressMixin','ViewFiltersMixin','ReceiptLauncherMixin','RecipeCoverageMixin','ProductEditorMixin','ReceiptScannerMixin','ScannerSuggestionsMixin'])assert.ok(active.includes(name+'('),name);
});
test('editor numbers no longer shrink according to digits but live camera keeps inherited sizing',()=>{
 class Base{_v119FitInput(n,c){this.forwarded=[n,c];}}
 const h=new (AppDesignMixin(Base))(),set=[],classes=[];
 h._v119FitInput({matches:()=>true,style:{setProperty:(...v)=>set.push(v)},closest:()=>({classList:{add:c=>classes.push(c)}})},4);
 assert.equal(set[0][1],'100%');assert.deepEqual(classes,['ui203-number-field']);
 const camera={matches:()=>false};h._v119FitInput(camera,4);assert.deepEqual(h.forwarded,[camera,4]);
});
test('dispose aborts design listeners and footer observer without touching data',()=>{
 const h=new (AppDesignMixin(class{}))(),draft={quantity:37};let events=0,observers=0;
 h._v78Draft=draft;h._ui203Events={abort:()=>events++};h._ui203FooterObserver={disconnect:()=>observers++};h._ui203Footer={};h._ui203Cleanup();h._ui203Cleanup();
 assert.equal(events,1);assert.equal(observers,1);assert.equal(h._v78Draft,draft);assert.equal(h._ui203Footer,null);
});
