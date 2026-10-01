import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {FullscreenStabilityMixin} from '../custom_components/cook4me/frontend/fullscreen-stability-v262.js';

class Base{
 constructor(){
  this.dialogRenders=0;
  this.pageRenders=0;
  this._language='el';
 }
 _uiIngredientLanguage(){return this._language;}
 _v66State(){return {cooking:false,step:0,device:'entry-1',sections:new Set(['info'])};}
 _isFavorite(){return false;}
 _renderRecipeDialog(){this.dialogRenders+=1;return this._v63RecipeDialog;}
 _renderTab(){this.pageRenders+=1;this._renderRecipeDialog();return 'page';}
}

class Panel extends FullscreenStabilityMixin(Base){}

function open(panel){
 panel._opened={
  id:'r1',
  title:'Hummus',
  displayVariantId:'variant-1',
  selectedServings:4,
  ingredients:[{name:'Chickpeas'}],
  steps:[{text:'Blend'}],
  match:{safe:true},
 };
 panel._v63RecipeDialog={isConnected:true,marker:'same-dialog'};
 panel._renderRecipeDialog();
}

test('visibility-return page redraw keeps unchanged fullscreen DOM mounted',()=>{
 const panel=new Panel();
 open(panel);
 assert.equal(panel.dialogRenders,1);

 // v63 visibilitychange -> _restorePreferences() -> _renderTab().
 panel._renderTab();

 assert.equal(panel.pageRenders,1);
 assert.equal(
  panel.dialogRenders,
  1,
  'resume redraw rebuilt the fullscreen recipe and would visibly blink',
 );
 assert.equal(panel._v63RecipeDialog.marker,'same-dialog');
});

test('page redraw still repaints when visible fullscreen state actually changes',()=>{
 const panel=new Panel();
 open(panel);
 panel._opened.selectedServings=6;
 panel._renderTab();
 assert.equal(panel.dialogRenders,2);
});

test('explicit fullscreen render still repaints unchanged recipe',()=>{
 const panel=new Panel();
 open(panel);
 panel._renderRecipeDialog();
 assert.equal(panel.dialogRenders,2);
});

test('UI language change invalidates fullscreen signature',()=>{
 const panel=new Panel();
 open(panel);
 panel._language='de';
 panel._renderTab();
 assert.equal(panel.dialogRenders,2);
});

test('active runtime layers stability outside the existing fullscreen guards',()=>{
 const active=readFileSync(
  new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),
  'utf8',
 );
 const registration=readFileSync(
  new URL('../custom_components/cook4me/panel.py',import.meta.url),
  'utf8',
 );
 assert.match(active,/fullscreen-stability-v262\.js/);
 assert.match(
  active,
  /FullscreenStabilityMixin\(TodaySubstitutionPersistenceMixin\(FullscreenProgressGuardMixin\(RecipeFullscreenGuardMixin/,
 );
 assert.match(active,/data-cook4me-ui-revision','266'/);
 assert.match(active,/runtime-v266/);
 assert.match(registration,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v266"/);
 assert.match(registration,/stability=262/);
 assert.match(registration,/seasonal=263/);
});
