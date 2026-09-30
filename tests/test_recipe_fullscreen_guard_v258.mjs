import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {RecipeFullscreenGuardMixin} from '../custom_components/cook4me/frontend/recipe-fullscreen-guard-v258.js';

class FakeStyle{
 constructor(){this.values=new Map();this.priorities=new Map();}
 getPropertyValue(key){return this.values.get(key)||'';}
 getPropertyPriority(key){return this.priorities.get(key)||'';}
 setProperty(key,value,priority=''){this.values.set(key,String(value));this.priorities.set(key,String(priority));}
 removeProperty(key){this.values.delete(key);this.priorities.delete(key);}
}
const fakeNode=(top=0,left=0)=>{
 const style=new FakeStyle();
 style.setProperty('overflow-y','auto');
 style.setProperty('overscroll-behavior-y','contain');
 return {style,scrollTop:top,scrollLeft:left};
};

class Base{}
class Panel extends RecipeFullscreenGuardMixin(Base){
 constructor(targets=[]){super();this.targets=targets;}
 _v258BackgroundScrollTargets(){return this.targets;}
 _v66State(){return this.state||{cooking:false};}
}

const source=readFileSync(new URL('../custom_components/cook4me/frontend/recipe-fullscreen-guard-v258.js',import.meta.url),'utf8');
const active=readFileSync(new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),'utf8');
const panelConfig=readFileSync(new URL('../custom_components/cook4me/panel.py',import.meta.url),'utf8');

test('fullscreen lock disables background scrolling and restores exact state',()=>{
 const node=fakeNode(137,9),panel=new Panel([node]);
 panel._v258LockBackgroundScroll();
 assert.equal(node.style.getPropertyValue('overflow-y'),'hidden');
 assert.equal(node.style.getPropertyPriority('overflow-y'),'important');
 assert.equal(node.style.getPropertyValue('overscroll-behavior-y'),'none');
 assert.equal(node.style.getPropertyValue('scrollbar-gutter'),'stable');
 node.scrollTop=500;node.scrollLeft=50;
 panel._v258UnlockBackgroundScroll();
 assert.equal(node.style.getPropertyValue('overflow-y'),'auto');
 assert.equal(node.style.getPropertyValue('overscroll-behavior-y'),'contain');
 assert.equal(node.style.getPropertyValue('scrollbar-gutter'),'');
 assert.equal(node.scrollTop,137);
 assert.equal(node.scrollLeft,9);
});

test('wake lock is desired only for cooking mode inside fullscreen recipe',()=>{
 const panel=new Panel();
 panel._opened={id:'recipe'};
 panel._v63RecipeDialog={};
 panel.state={cooking:false};
 assert.equal(panel._v258CookingFullscreen(),false);
 panel.state.cooking=true;
 assert.equal(panel._v258CookingFullscreen(),true);
 panel._v63RecipeDialog=null;
 assert.equal(panel._v258CookingFullscreen(),false);
});

test('background lock includes Cook4Me content and outer document/HA scrollers',()=>{
 assert.match(source,/getElementById\('content'\)/);
 assert.match(source,/computed\?\.overflowY/);
 assert.match(source,/doc\?\.scrollingElement/);
 assert.match(source,/doc\?\.documentElement/);
 assert.match(source,/doc\?\.body/);
 assert.match(source,/setProperty\('overflow-y','hidden','important'\)/);
});

test('fullscreen recipe owns scroll and cannot chain to the background',()=>{
 assert.match(source,/\[data-recipe-dialog\]\{overflow:hidden!important;overscroll-behavior:none!important\}/);
 assert.match(source,/\.rx-v66-fullscreen\{overscroll-behavior-y:contain!important\}/);
});

test('screen wake lock uses the standard screen API and releases safely',()=>{
 assert.match(source,/navigator\?\.wakeLock/);
 assert.match(source,/api\.request\('screen'\)/);
 assert.match(source,/_v258ReleaseWakeLock/);
 assert.match(source,/visibilityState==='visible'/);
 assert.match(source,/visibilitychange/);
 assert.match(source,/sentinel\.release\(\)/);
});

test('closing fullscreen unlocks background and releases wake lock',()=>{
 assert.match(source,/_v258WrapRecipeClose/);
 assert.match(source,/this\._v258UnlockBackgroundScroll\(\)/);
 assert.match(source,/void this\._v258ReleaseWakeLock\(\)/);
});

test('active panel applies v258 outside the v257 price and weighing mixin',()=>{
 assert.match(active,/recipe-fullscreen-guard-v258\.js/);
 assert.match(active,/RecipeFullscreenGuardMixin\(RecipeIngredientWeighingMixin/);
 assert.match(active,/runtime-v258/);
 assert.match(active,/data-cook4me-ui-revision','\d+'/);
 assert.match(panelConfig,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v\d+"/);
 assert.match(panelConfig,/runtime-v249/);
 assert.match(panelConfig,/weigh=257&fullscreen=258/);
});
