import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
 seasonalFilterEnabled,
 seasonalFilterLabel,
 SeasonalFilterStateMixin,
} from '../custom_components/cook4me/frontend/seasonal-filter-state-v263.js';
import {ViewFiltersMixin} from '../custom_components/cook4me/frontend/view-filters-v199.js';

test('seasonal selection counts as an active ingredients filter even with no ingredient choices',()=>{
 class Base{
  constructor(){this.filters={ingredients:[],seasonalIngredients:true};}
  _filters(){return this.filters;}
  _filterActive(){return false;}
 }
 const Panel=SeasonalFilterStateMixin(Base),panel=new Panel();
 assert.equal(panel._filterActive('ingredients'),true);
 panel.filters.seasonalIngredients=false;
 assert.equal(panel._filterActive('ingredients'),false);
});

test('seasonal labels follow interface language',()=>{
 assert.equal(seasonalFilterLabel('el-GR'),'Υλικά εποχής');
 assert.equal(seasonalFilterLabel('de-DE'),'Saisonale Zutaten');
 assert.equal(seasonalFilterLabel('fr-FR'),'Seasonal ingredients');
 assert.equal(seasonalFilterEnabled({seasonalIngredients:true}),true);
 assert.equal(seasonalFilterEnabled({seasonalIngredients:false}),false);
});

const storage=new Map();
globalThis.localStorage={
 getItem:key=>storage.get(key)||null,
 setItem:(key,value)=>storage.set(key,value),
};

const clone=structuredClone;
class Legacy{
 constructor(){
  this._entryId='entry';
  this._tab='today';
  this.sent=[];
  this._hass={
   user:{id:crypto.randomUUID()},
   connection:{sendMessagePromise:async msg=>{this.sent.push(clone(msg));return this.respond?.(msg)||{};}},
  };
 }
 _prefKey(){return this._hass.user.id+'.'+this._entryId;}
 _filters(){
  if(this._v63FilterKey!==this._prefKey()){
   this._v63FilterKey=this._prefKey();
   let saved={};try{saved=JSON.parse(localStorage.getItem(this._prefKey())||'{}')||{};}catch{}
   this._v63Filters={diet:'profile',languages:['de'],ingredients:[],...saved.filters};
   this._v63Dirty=saved.pending||null;
   if(saved.lastTab)this._tab=saved.lastTab;
  }
  return this._v63Filters;
 }
 _persistPreferences(patch){
  this._v63PrefRevision=(this._v63PrefRevision||0)+1;
  this._v63Dirty={...this._v63Dirty,...patch};
  this._cachePreferences();
  void this._flushPreferences();
 }
 _v179ClearOpenRecipe(){}
 _v63CloseRecipe(){}
 _t(key){return key;}
 _message(){}
 _renderTabs(){}
 _renderTab(){}
}
const Filters=ViewFiltersMixin(Legacy);
const idle=async()=>{for(let i=0;i<8;i++)await Promise.resolve();};

test('seasonal choice is persisted per view and survives a new browser component',async()=>{
 const first=new Filters();
 first._filters();
 first._persistPreferences({filters:{...first._filters(),seasonalIngredients:true}});
 await idle();
 assert.equal(first.sent[0].preferences.filtersByView.today.seasonalIngredients,true);

 const second=new Filters();
 second._hass.user.id=first._hass.user.id;
 assert.equal(second._filters().seasonalIngredients,true);

 second._tab='week';
 assert.notEqual(second._filters().seasonalIngredients,true);
 second._tab='today';
 assert.equal(second._filters().seasonalIngredients,true);
});

test('server restore preserves seasonal choice in its owning view',async()=>{
 const panel=new Filters();
 panel.respond=()=>({
  lastTab:'week',
  filtersByView:{
   today:{seasonalIngredients:true},
   week:{seasonalIngredients:false},
  },
 });
 await panel._restorePreferences();
 assert.equal(panel._tab,'week');
 assert.equal(panel._filters().seasonalIngredients,false);
 panel._tab='today';
 assert.equal(panel._filters().seasonalIngredients,true);
});


test('actual seasonal control writes through the normal per-view filter preference path',()=>{
 const season=readFileSync(
  new URL('../custom_components/cook4me/frontend/ingredient-season-v223.js',import.meta.url),
  'utf8',
 );
 const filters=readFileSync(
  new URL('../custom_components/cook4me/frontend/cook4me-panel-v63.js',import.meta.url),
  'utf8',
 );
 assert.match(season,/input\.dataset\.field='seasonalIngredients'/);
 assert.match(season,/_persistPreferences\(\{filters:\{\.\.\.this\._filters\(\),seasonalIngredients:input\.checked\}\}\)/);
 assert.match(filters,/next\[input\.dataset\.field\]=input\.type==="checkbox"\?input\.checked:input\.value/);
 assert.match(filters,/_persistPreferences\(\{filters:next\}\)/);
});

test('active seasonal choice is rendered outside the filter button and opens ingredients filter',()=>{
 const source=readFileSync(
  new URL('../custom_components/cook4me/frontend/seasonal-filter-state-v263.js',import.meta.url),
  'utf8',
 );
 assert.match(source,/summary\.dataset\.v263ActiveFilters=''/);
 assert.match(source,/chip\.dataset\.v263ActiveFilter='seasonalIngredients'/);
 assert.match(source,/bar\.insertAdjacentElement\('afterend',summary\)/);
 assert.match(source,/_showFilter\('ingredients'\)/);
});

test('active panel and registration use runtime v269',()=>{
 const panel=readFileSync(
  new URL('../custom_components/cook4me/frontend/cook4me-panel-v180.js',import.meta.url),
  'utf8',
 );
 const registration=readFileSync(
  new URL('../custom_components/cook4me/panel.py',import.meta.url),
  'utf8',
 );
 assert.match(panel,/seasonal-filter-state-v263\.js/);
 assert.match(panel,/SeasonalFilterStateMixin\(FullscreenStabilityMixin/);
 assert.match(panel,/data-cook4me-ui-revision','268'/);
 assert.match(panel,/runtime-v268/);
 assert.match(registration,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v272"/);
 assert.match(registration,/seasonal=263/);
});
