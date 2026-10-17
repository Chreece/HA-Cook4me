import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
 loadedRecipeTarget, loadedRecipeStep, liveModeForRecipeStep, LoadedDeviceRecipeMixin,
} from '../custom_components/cook4me/frontend/loaded-device-recipe-v284.js';
import {stepCookingModes} from '../custom_components/cook4me/frontend/recipe-step-modes-v259.js';

const live=(overrides={})=>({
 accessible:true,connected:true,
 state:{
  recipeTitle:'Risotto',variantFunctionalId:'VARIANT_B',
  stepFunctionalId:'STEP_PRESSURE',stepIndex:1,
  programName:'High pressure cooking',
  ...overrides,
 }
});
const recipe={
 title:'Risotto',displayVariantId:'VARIANT_B',
 steps:[
  {functionalId:'STEP_PREP',stepIndex:0,programs:[]},
  {functionalId:'STEP_PRESSURE',stepIndex:1,programs:[{programKey:'PROGRAM_777',programName:'Other cooking mode'}]},
  {functionalId:'STEP_WARM',stepIndex:2,programs:[{programKey:'PROGRAM_778',programName:'Other cooking mode'}]},
 ],
};

test('only authorized live variant ID can become an actionable loaded recipe',()=>{
 assert.deepEqual(loadedRecipeTarget(live(),{live:true,state:live().state}),{variant:'VARIANT_B',title:'Risotto'});
 assert.equal(loadedRecipeTarget(live(),{live:false,state:live().state}),null);
 assert.equal(loadedRecipeTarget({...live(),accessible:false},{live:true,state:live().state}),null);
 assert.equal(loadedRecipeTarget(live({variantFunctionalId:''}),{live:true,state:live({variantFunctionalId:''}).state}),null);
 assert.equal(loadedRecipeTarget(live({recipeTitle:'Risotto'}),{live:true,state:{recipeTitle:'Risotto'}}),null);
});

test('live pressure label is used only for the exact variant and active step',()=>{
 assert.equal(loadedRecipeStep(recipe,live()),1);
 const mode=liveModeForRecipeStep(recipe,live(),1,'el');
 assert.equal(mode.mode,'high_pressure');
 assert.equal(mode.label,'Μαγείρεμα σε υψηλή πίεση');
 assert.equal(mode.source,'live_device');
 assert.equal(liveModeForRecipeStep(recipe,live(),0,'el'),null);
 assert.equal(liveModeForRecipeStep({...recipe,displayVariantId:'SOME_OTHER_RECIPE'},live(),1,'el'),null);
});

test('keep warm source is localized from explicit live program, not from guessed phase',()=>{
 const current=live({stepFunctionalId:'STEP_WARM',stepIndex:2,programName:'Warm holding',phase:'keep_warm'});
 assert.equal(liveModeForRecipeStep(recipe,current,2,'de').mode,'keep_warm');
 assert.equal(liveModeForRecipeStep(recipe,current,2,'el').label,'Διατήρηση θερμοκρασίας');
 assert.equal(liveModeForRecipeStep(recipe,current,1,'el'),null);
 const withoutProgram=live({stepFunctionalId:'STEP_WARM',stepIndex:2,phase:'keep_warm',programName:''});
 assert.equal(liveModeForRecipeStep(recipe,withoutProgram,2,'el'),null);
});

test('when device step ID is present it is authoritative over a different index',()=>{
 const mismatch=live({stepFunctionalId:'SOME_OTHER_STEP',stepIndex:1});
 assert.equal(loadedRecipeStep(recipe,mismatch),-1);
 assert.equal(liveModeForRecipeStep(recipe,mismatch,1,'en'),null);
 const indexOnly=live({stepFunctionalId:'',stepIndex:2,programName:'Keep warm'});
 assert.equal(loadedRecipeStep(recipe,indexOnly),2);
 const unknown=live({stepFunctionalId:'',stepIndex:null});
 assert.equal(loadedRecipeStep(recipe,unknown),-1);
});

test('unknown provider labels and opaque program IDs remain unknown without verified live match',()=>{
 const row=stepCookingModes(recipe.steps[1],'el')[0];
 assert.equal(row.mode,null);
 assert.equal(row.label,'Άλλη λειτουργία μαγειρέματος');
 assert.equal(stepCookingModes({programKey:'PROGRAM_99'},'el')[0].mode,null);
 assert.equal(liveModeForRecipeStep(recipe,live({programName:'Other cooking mode'}),1,'de'),null);
});

test('all supported UI languages map exact high-pressure and warm-holding program names',()=>{
 const expected={
  en:['High-pressure cooking','Keep warm'],
  de:['Garen unter hohem Druck','Warmhalten'],
  el:['Μαγείρεμα σε υψηλή πίεση','Διατήρηση θερμοκρασίας'],
  fr:['Cuisson sous haute pression','Maintien au chaud'],
 };
 for(const [language,labels] of Object.entries(expected)){
  assert.equal(stepCookingModes({programName:'High pressure cooking'},language)[0].label,labels[0]);
  assert.equal(stepCookingModes({programName:'Warm holding'},language)[0].label,labels[1]);
 }
});

class FakeButton{
 constructor(){this.dataset={};this.attributes={};this.tagName='BUTTON';this.listeners={};}
 setAttribute(k,v){this.attributes[k]=v;}
 addEventListener(k,fn){this.listeners[k]=fn;}
 click(){this.listeners.click?.();}
}
class Base{
 _v81RenderInfo(){this.renderCount=(this.renderCount||0)+1;}
}
class Panel extends LoadedDeviceRecipeMixin(Base){
 constructor(){
  super();
  this.current=live();
  this.view={live:true,state:this.current.state};
  this._entryId='ENTRY_A';
  this._hass={user:{id:'USER_A'}};
  this.buttons=[];
  this.fakeCell={
   tagName:'DD',
   old:null,
   querySelector:()=>this.fakeCell.old,
   replaceChildren:button=>{this.fakeCell.old=button;this.buttons.push(button);},
  };
  this.term={textContent:'Recipe',nextElementSibling:this.fakeCell};
  this._v81InfoDialog={isConnected:true,
   querySelector:selector=>selector==='[data-v81-details]'?{
    querySelectorAll:()=>[this.term],
   }:null};
  this.shadowRoot={querySelector:()=>true,append:()=>{}};
  this.showCalls=[];
  this.closeCalls=0;
 }
 _v81View(){return this.view;}
 _entry(){return this.current;}
 _v81Text(){return 'Recipe';}
 _prefKey(){return 'user:entry';}
 _langCode(){return 'en';}
 _v81CloseInfo(){this.closeCalls++;}
 _showRecipe(row,custom){this.showCalls.push({row,custom});}
 _v284Styles(){}
}

test('device info creates accessible button and opens the existing exact-edition fullscreen path',()=>{
 const previous=globalThis.document;
 globalThis.document={createElement:()=>new FakeButton()};
 try{
  const panel=new Panel();
  panel._v81RenderInfo();
  assert.equal(panel.buttons.length,1);
  const button=panel.buttons[0];
  assert.equal(button.dataset.variant,'VARIANT_B');
  assert.equal(button.textContent,'Risotto');
  assert.match(button.attributes['aria-label'],/fullscreen/i);
  panel._v81RenderInfo();
  assert.equal(panel.buttons.length,1,'same button survives live updates');
  button.click();
  assert.equal(panel.closeCalls,1);
  assert.deepEqual(panel.showCalls[0],{
   custom:false,
   row:{title:'Risotto',displayVariantId:'VARIANT_B',searchVariantId:'VARIANT_B',variantFunctionalId:'VARIANT_B'},
  });
 }finally{globalThis.document=previous;}
});

test('disappearing variant removes the stale recipe action without guessing by title',()=>{
 const previous=globalThis.document;globalThis.document={createElement:()=>new FakeButton()};
 try{
  const panel=new Panel();panel._v81RenderInfo();
  assert.equal(panel.buttons.length,1);
  panel.view={live:true,state:{...live().state,variantFunctionalId:''}};
  panel._v81RenderInfo();
  assert.equal(panel.fakeCell.textContent,'Risotto');
  panel.buttons[0].click();
  assert.equal(panel.showCalls.length,0);
 }finally{globalThis.document=previous;}
});

test('stale recipe/other entry/user cannot open a previous device recipe',()=>{
 const previous=globalThis.document;globalThis.document={createElement:()=>new FakeButton()};
 try{
  const panel=new Panel();panel._v81RenderInfo();
  const old=panel.buttons[0];
  panel.view={live:true,state:{...live().state,variantFunctionalId:'VARIANT_C'}};
  old.click();assert.equal(panel.showCalls.length,0);
  panel.view={live:true,state:live().state};
  panel._entryId='ENTRY_B';old.click();assert.equal(panel.showCalls.length,0);
  panel._entryId='ENTRY_A';panel._hass.user.id='USER_B';old.click();assert.equal(panel.showCalls.length,0);
 }finally{globalThis.document=previous;}
});

test('runtime owns final mixin, version-busted UI and stable device-info row updates',()=>{
 const root=new URL('../custom_components/cook4me/',import.meta.url);
 const app=readFileSync(new URL('frontend/cook4me-panel-v180.js',root),'utf8');
 const panel=readFileSync(new URL('panel.py',root),'utf8');
 const legacy=readFileSync(new URL('frontend/cook4me-panel-v81.js',root),'utf8');
 const feature=readFileSync(new URL('frontend/loaded-device-recipe-v284.js',root),'utf8');
 assert.match(app,/const BasePanel=ProductScaleLayoutMixin/);
 assert.match(app,/customElements\.define\('cook4me-recipe-hub-panel-v180-runtime-v284',LoadedDeviceRecipeMixin\(customElements\.get\('cook4me-recipe-hub-panel-v180-runtime-v272'\)\)\)/);
 assert.match(app,/runtime-v284/);
 assert.match(panel,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v284"/);
 assert.match(panel,/loadedrecipe=284/);
 assert.match(legacy,/_v81SourceHtml!==html/);
 assert.match(feature,/chips\.length>1/);
 assert.match(feature,/!current\|\|current\.variant!==target\.variant/);
});
