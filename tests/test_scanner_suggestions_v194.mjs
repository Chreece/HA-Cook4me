import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

const source = await fs.readFile(new URL('../custom_components/cook4me/frontend/scanner-suggestions-v194.js', import.meta.url), 'utf8');
const {scannerSuggestionRows, toggleScannerLink, ScannerSuggestionsMixin} = await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const identity = row => row.key || row.name || '';
const item = (key,name=key) => ({ingredient:{key,name},reason:'name_exact'});
const escape = value => String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');

// A minimal DOM double exercises production rendering and event handlers; not a browser/camera test.
class Holder {
 constructor(){this.html='';this.buttons=[];this.list={scrollTop:0};}
 set innerHTML(value){
  this.html=value;this.list={scrollTop:0};
  this.buttons=[...value.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)].map(match=>{
   const attributes=match[1];
   return {dataset:{v194Ingredient:/data-v194-ingredient="([^"]*)"/.exec(attributes)?.[1],v194Index:/data-v194-index="([^"]*)"/.exec(attributes)?.[1]},
    disabled:/\sdisabled(?:\s|$)/.test(attributes),pressed:/aria-pressed="true"/.test(attributes),text:match[2],
    focus(){this.focused=true;}};
  });
 }
 get innerHTML(){return this.html;}
 querySelector(selector){return selector==='[data-v194-list]'&&this.html.includes('data-v194-list')?this.list:null;}
 querySelectorAll(){return this.buttons;}
 contains(element){return this.buttons.includes(element);}
}
function panel(suggestions,lang='en'){
 const holder=new Holder();
 class Base {
  _v78IngredientOptions(){} _v114Picker(){} _v111Paint(){}
  _uiIngredientLanguage(){return lang;}
  _scanIngredientIdentity(row){return identity(row);}
  _escape(value){return escape(value);}
  _v114Links(){return this._v78Draft.ingredientLinks||[];}
  _v112Local(row){return row;}
  _ingredientQueryMatches(row,query){return row.name.toLocaleLowerCase().includes(query.toLocaleLowerCase());}
 }
 const host=new (ScannerSuggestionsMixin(Base))();
 host.shadowRoot={activeElement:null};host._v78Dialog={querySelector:()=>holder};
 host._v78Draft={suggestions,ingredient:null,ingredientLinks:[],query:''};
 host._v194Suggestions();return {host,holder,draft:host._v78Draft};
}

test('returns every candidate beyond both old limits',()=>assert.equal(scannerSuggestionRows(Array.from({length:75},(_,i)=>item(String(i))),identity).length,75));
test('deduplicates identities, not identical labels',()=>assert.deepEqual(scannerSuggestionRows([item('a','Rice'),item('b','Rice'),item('a','Rice')],identity).map(x=>x.ingredient.key),['a','b']));
test('ignores malformed suggestion rows',()=>assert.deepEqual(scannerSuggestionRows([null,{},item('r','Rice')],identity),[item('r','Rice')]));
test('pure toggle preserves other linked ingredients',()=>{
 const old=[{key:'a',name:'A'}];const added=toggleScannerLink(old,{key:'b',name:'B'},identity);
 assert.equal(old.length,1);assert.deepEqual(added.map(identity),['a','b']);assert.deepEqual(toggleScannerLink(added,old[0],identity).map(identity),['b']);
});
test('renders all 75 buttons in bounded scroll area',()=>{
 const {holder}=panel(Array.from({length:75},(_,i)=>item(String(i))));assert.equal(holder.buttons.length,75);
 assert.match(holder.html,/75 \/ 75/);assert.match(holder.html,/max-height:260px;overflow:auto/);
});
test('suggestions never select a product automatically',()=>{
 const {draft}=panel([item('a')]);assert.equal(draft.ingredient,null);assert.deepEqual(draft.ingredientLinks,[]);
});
test('clicking two suggestions keeps both and toggles one off',()=>{
 const {holder,draft}=panel([item('a'),item('b')]);holder.buttons[0].onclick();holder.buttons[1].onclick();
 assert.deepEqual(draft.ingredientLinks.map(identity),['a','b']);assert.equal(draft.ingredient.key,'a');
 holder.buttons[0].onclick();assert.deepEqual(draft.ingredientLinks.map(identity),['b']);assert.equal(draft.ingredient.key,'b');
 holder.buttons[1].onclick();assert.equal(draft.ingredient,null);assert.deepEqual(draft.ingredientLinks,[]);
});
test('selected rows remain visible through searches',()=>{
 const {host,holder,draft}=panel([item('a','Carrot'),item('b','Peeled carrot'),item('c','Onion')]);
 holder.buttons[0].onclick();draft.query='Onion';host._v194Suggestions();
 assert.deepEqual(holder.buttons.map(x=>x.dataset.v194Ingredient),['a','c']);assert.match(holder.html,/2 \/ 3/);
});
test('selections use the current local catalog identity',()=>{
 const {host,holder,draft}=panel([item('old','Source')]);host._v112Local=()=>({key:'current',name:'Τοπικό'});
 holder.buttons[0].onclick();assert.equal(draft.ingredient.key,'current');assert.equal(draft.ingredient.name,'Τοπικό');
});
test('busy or submitted scanner cannot change selection',()=>{
 for(const flag of ['_v78Busy','_v78Submitted']){
  const {host,holder,draft}=panel([item('a')]);host[flag]=true;host._v194Suggestions();
  assert.equal(holder.buttons[0].disabled,true);holder.buttons[0].onclick();assert.deepEqual(draft.ingredientLinks,[]);
 }
});
test('stale buttons cannot modify a new product draft',()=>{
 const {host,holder,draft}=panel([item('a')]);const button=holder.buttons[0];host._v78Draft={ingredientLinks:[]};
 button.onclick();assert.deepEqual(draft.ingredientLinks,[]);assert.deepEqual(host._v78Draft.ingredientLinks,[]);
});
test('closed or replaced dialog rejects old handlers',()=>{
 const {host,holder,draft}=panel([item('a')]);const button=holder.buttons[0];host._v78Dialog=null;button.onclick();assert.deepEqual(draft.ingredientLinks,[]);
});
test('server names and keys are HTML escaped',()=>{
 const {holder}=panel([item('bad" onclick="evil','<script>alert(1)</script>')]);
 assert.ok(!holder.html.includes('<script>'));assert.ok(!holder.html.includes('onclick="evil'));
 assert.match(holder.html,/&lt;script&gt;/);assert.match(holder.html,/&quot;/);
});
test('empty results explicitly offer full catalog search',()=>{
 const {holder}=panel([]);assert.match(holder.html,/Search the full catalog below/);assert.equal(holder.buttons.length,0);
});
test('Greek and German guidance and reasons are localized',()=>{
 for(const [lang,title,reason] of [['el','Πιθανά συμβατά υλικά','Παραλλαγή προετοιμασίας'],['de','Mögliche passende Zutaten','Zubereitungsvariante']]){
  const {holder}=panel([{...item('a'),reason:'preparation_variant'}],lang);assert.ok(holder.html.includes(title));assert.ok(holder.html.includes(reason));
 }
});
test('scroll position survives selection redraw',()=>{
 const {holder}=panel([item('a'),item('b')]);holder.list.scrollTop=85;holder.buttons[0].onclick();assert.equal(holder.list.scrollTop,85);
});
test('unchanged render keeps DOM button objects',()=>{
 const {host,holder}=panel([item('a')]);const before=holder.buttons[0];host._v194Suggestions();assert.equal(holder.buttons[0],before);
});
test('existing camera and save methods are not overridden',()=>{
 for(const method of ['_v78Camera','_v78Recognize','_v78Lookup','_v78Save','_v78StopCamera'])assert.ok(!source.includes(method+'('));
});
