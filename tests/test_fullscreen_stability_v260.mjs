import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {FullscreenStabilityMixin} from '../custom_components/cook4me/frontend/fullscreen-stability-v260.js';

class Base{
 constructor(){this.dialogRenders=0;this.pageRenders=0;this.shadowRoot={querySelector:()=>null,append:()=>{}};}
 _v66State(){return {cooking:false,step:0,device:'',sections:new Set(['info'])};}
 _isFavorite(){return false;}
 _renderRecipeDialog(){this.dialogRenders+=1;return this._v63RecipeDialog;}
 _renderTab(){this.pageRenders+=1;this._renderRecipeDialog();return 'page';}
}
class Panel extends FullscreenStabilityMixin(Base){}

test('background page refresh does not rebuild unchanged fullscreen recipe',()=>{
 const panel=new Panel();
 panel._opened={id:'r1',title:'Meal',ingredients:[{name:'Rice'}],steps:[{text:'Cook'}]};
 panel._v63RecipeDialog={isConnected:true};
 panel._renderRecipeDialog();
 assert.equal(panel.dialogRenders,1);

 panel._renderTab();
 assert.equal(panel.pageRenders,1);
 assert.equal(panel.dialogRenders,1,'unchanged fullscreen was rebuilt during page refresh');

 panel._opened.title='Meal updated';
 panel._renderTab();
 assert.equal(panel.dialogRenders,2,'changed visible recipe state must still repaint');
});

test('explicit fullscreen render still repaints even when signature is unchanged',()=>{
 const panel=new Panel();
 panel._opened={id:'r1',title:'Meal'};
 panel._v63RecipeDialog={isConnected:true};
 panel._renderRecipeDialog();
 panel._renderRecipeDialog();
 assert.equal(panel.dialogRenders,2);
});

test('progress-card completion is paint-contained away from fullscreen layer',()=>{
 const source=readFileSync(
  new URL('../custom_components/cook4me/frontend/fullscreen-stability-v260.js',import.meta.url),
  'utf8',
 );
 assert.match(source,/\.rx-v63-progress\{contain:layout paint;isolation:isolate\}/);
});

test('active runtime layers v260 stability outside existing fullscreen guard',()=>{
 const active=readFileSync(
  new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),
  'utf8',
 );
 const panel=readFileSync(
  new URL('../custom_components/cook4me/panel.py',import.meta.url),
  'utf8',
 );
 assert.match(active,/fullscreen-stability-v260\.js/);
 assert.match(active,/FullscreenStabilityMixin\(RecipeFullscreenGuardMixin/);
 assert.match(active,/data-cook4me-ui-revision','260'/);
 assert.match(active,/runtime-v260/);
 assert.match(panel,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v260"/);
 assert.match(panel,/modes=259&stability=260/);
});
