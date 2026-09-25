import assert from 'node:assert/strict';
import test from 'node:test';
import {ingredientNameParts,IngredientNamesMixin} from '../custom_components/cook4me/frontend/ingredient-names-v221.js';
import {UXFixesMixin} from '../custom_components/cook4me/frontend/ux-fixes-v218.js';

function panel(){
 const Panel=IngredientNamesMixin(UXFixesMixin(class {})),p=new Panel();
 p.ui='el';p.market='de';p.context='entry-a';
 p._prefKey=()=>p.context;p._uiIngredientLanguage=()=>p.ui;p._v140SupermarketLanguage=()=>p.market;
 p._ingredientCatalogLanguage='el';
 p._ingredientCatalog=[{key:'rice',ingredientId:'catalog-rice',sourceIngredientIds:['fr-rice'],name:'Ρύζι'},
  {key:'flour',sourceIngredientIds:['fr-flour'],name:'Αλεύρι'}];
 p._v140MarketNames=new Map([['rice','Reis'],['flour','Mehl']]);p._v140MarketCatalogKey='entry-a:de';
 return p;
}

test('UI, supermarket and recipe names use one ordered, deduplicated suffix',()=>{
 assert.equal(ingredientNameParts('Ρύζι','Reis','Riz').label,'Ρύζι (Reis, Riz)');
 assert.equal(ingredientNameParts('Reis','Reis','Riz').label,'Reis (Riz)');
 assert.equal(ingredientNameParts('Ρύζι','Reis','REIS').label,'Ρύζι (Reis)');
 assert.equal(ingredientNameParts(' Rice ','rice','RICE').label,'Rice');
 assert.equal(ingredientNameParts('Ρύζι','Ρύζι'.normalize('NFD'),'').label,'Ρύζι');
 assert.equal(ingredientNameParts('','','Custom ingredient').label,'Custom ingredient');
});

test('reviewed source identities find both catalogs without mutating recipe data',()=>{
 const p=panel(),source={ingredientId:'fr-rice',name:'Riz',displayName:'Rice',displayLanguage:'en',quantity:200,unit:'g'};
 const before=structuredClone(source);
 assert.equal(p._v221IngredientNames(source).label,'Ρύζι (Reis, Riz)');
 assert.equal(p._v221IngredientNames({identity:'i:fr-rice',name:'Riz'}).label,'Ρύζι (Reis, Riz)');
 assert.deepEqual(source,before);
 assert.equal(p._v221IngredientNames({key:'unknown',name:'Rice flour'}).label,'Rice flour');
});

test('locale and household changes cannot use stale catalog names',()=>{
 const p=panel(),source={key:'rice',name:'Riz',displayName:'Rice',displayLanguage:'en'};
 p.market='fr';assert.equal(p._v221IngredientNames(source).label,'Ρύζι (Riz)');
 p.market='de';p.context='entry-b';assert.equal(p._v221IngredientNames(source).label,'Ρύζι (Riz)');
 p.ui='en';assert.equal(p._v221IngredientNames(source).label,'Rice (Riz)');
 p._ingredientCatalogLanguage='en';p._ingredientCatalog=[{key:'rice',name:'Rice'}];
 p._v140MarketCatalogKey='entry-b:de';assert.equal(p._v221IngredientNames(source).label,'Rice (Reis, Riz)');
});

test('matching presentation and info labels work while UI catalog is unavailable',()=>{
 const p=panel();p._ingredientCatalog=[];
 assert.equal(p._v221IngredientNames({key:'rice',name:'Riz',displayName:'Ρύζι',displayLanguage:'el'}).label,'Ρύζι (Reis, Riz)');
 assert.equal(p._v221IngredientNames({key:'rice',name:'Riz'},null,{language:'el',name:'Ρύζι'}).label,'Ρύζι (Reis, Riz)');
 assert.equal(p._v221IngredientNames({key:'rice',name:'Riz'},null,{language:'en',name:'Rice'}).label,'Riz (Reis)');
});

test('the info endpoint can supply an exact identity for a text-only ingredient',()=>{
 const p=panel();
 const info={language:'el',name:'Ρύζι',ingredient:{key:'rice',name:'Ρύζι'}};
 assert.equal(p._v221IngredientNames('Riz',null,info).label,'Ρύζι (Reis, Riz)');
 // A matching-language recipe translation retains preparation qualifiers.
 assert.equal(p._v221IngredientNames({key:'rice',name:'Riz rincé',displayName:'Ρύζι, ξεπλυμένο',displayLanguage:'el'}).label,
  'Ρύζι, ξεπλυμένο (Reis, Riz rincé)');
});

test('translated string rows reuse identity only with an unambiguous aligned source',()=>{
 const p=panel(),recipe={ingredients:['Ρύζι'],_nutritionIngredients:[{ingredientId:'fr-rice',name:'Riz'}]};
 assert.equal(p._v221IngredientNames(recipe.ingredients[0],recipe).label,'Ρύζι (Reis, Riz)');
 assert.equal(p._v221IngredientNames('Custom ingredient',{ingredients:['Custom ingredient'],_nutritionIngredients:[]}).label,'Custom ingredient');
 assert.equal(p._v221IngredientNames('Rice',{ingredients:['Rice','Rice'],_nutritionIngredients:[{key:'rice'},{key:'flour'}]}).label,'Rice');
});

test('a failed catalog read does not trigger a render/load microtask loop',async()=>{
 let reads=0;
 const P=IngredientNamesMixin(class {
  _v66BindRecipe(){}
  async _loadIngredientCatalog(){reads++;}
 });
 const p=new P();p._prefKey=()=> 'entry';p._uiIngredientLanguage=()=> 'el';
 p._v221DecorateIngredients=()=>{};p._v221RefreshNames=()=>{};
 const container={querySelector:()=>({})};
 p._v66BindRecipe(container,{});p._v66BindRecipe(container,{});
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(reads,1);
});
