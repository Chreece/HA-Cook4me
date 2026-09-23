import test from 'node:test';
import assert from 'node:assert/strict';
import {selectedFirst} from '../custom_components/cook4me/frontend/filter-selection-v202.js';
import {isRecipeRow,recipeRows,missingDayMeals,GAP_TEXT,RecipeGapsMixin} from '../custom_components/cook4me/frontend/recipe-gaps-v202.js';
import {cameraLayout,CAMERA_TEXT,RECEIPT_ICON,ScannerCameraMixin} from '../custom_components/cook4me/frontend/scanner-camera-v202.js';
test('selected first is a stable partition and never mutates the input',()=>{const a=[{id:1},{id:2,s:true},{id:3,s:true},{id:4}];assert.deepEqual(selectedFirst(a,r=>r.s).map(r=>r.id),[2,3,1,4]);assert.deepEqual(a.map(r=>r.id),[1,2,3,4]);});
test('selection changes restore unselected original ordering',()=>{const rows=['A','B','C'];assert.deepEqual(selectedFirst(rows,r=>r==='B'),['B','A','C']);assert.deepEqual(selectedFirst(rows,r=>false),rows);});
test('empty list remains empty',()=>assert.deepEqual(selectedFirst([],()=>true),[]));
test('malformed recipe rows retain their exact list positions',()=>{const good={title:'Rice'},raw=[good,null,'bad',{}],safe=recipeRows(raw);assert.equal(safe.length,4);assert.equal(safe[0],good);assert.equal(safe[1]._v202Gap,'processing_error');assert.equal(raw[1],null);});
test('summary rows are valid even before instructions have loaded',()=>{assert.equal(isRecipeRow({title:'Rice'}),true);assert.equal(isRecipeRow({canonicalName:'Rice'}),true);assert.equal(isRecipeRow({title:{bad:1}}),false);});
test('short last result page does not invent omitted recipes',()=>assert.equal(recipeRows([{title:'One'},{title:'Two'}]).length,2));
test('daily holes come from requested missing meal types, not the global result count',()=>assert.deepEqual(missingDayMeals({emptyMealTypes:['breakfast','dinner','dinner']},[{todayMealType:'breakfast'}]),['dinner']));
test('absent daily metadata creates no phantom requests',()=>assert.deepEqual(missingDayMeals(null,[]),[]));
test('unknown non-string meal metadata is ignored',()=>assert.deepEqual(missingDayMeals({emptyMealTypes:[null,2,'main']},[]),['main']));
for(const [width,height,landscape] of [[390,844,false],[844,390,true],[1366,900,true]])test(`camera layout ${width}x${height}`,()=>{const got=cameraLayout(width,height,60,1920,1080);assert.equal(got.landscape,landscape);assert.ok(got.height<=height-60);assert.equal(got.ratio,1920/1080);});
test('intrinsic camera dimensions may rotate independently of viewport',()=>{assert.equal(cameraLayout(390,844,60,1080,1920).ratio,1080/1920);assert.equal(cameraLayout(844,390,40,1920,1080).ratio,1920/1080);});
test('early camera metadata absent still has finite dimensions',()=>{const value=cameraLayout(undefined,undefined);assert.ok(Number.isFinite(value.ratio));assert.ok(value.height>0);});
test('receipt uses a published Material Design icon name',()=>assert.equal(RECEIPT_ICON,'mdi:receipt-text-outline'));
class Base { _v111Canvas(crop){return crop;} _r195Text(k){return k;} _uiIngredientLanguage(){return 'el';} }
const Camera=ScannerCameraMixin(Base);
test('receipt captures the full source frame, never the guide box',()=>{const h=new Camera();h._v78Draft={mode:'receipt'};assert.equal(h._v111Canvas(),false);});
test('barcode and nutrient cropping stays inherited',()=>{const h=new Camera();for(const mode of ['barcode','nutrition','date','product']){h._v78Draft={mode};assert.equal(h._v111Canvas(true),true);assert.equal(h._v111Canvas(false),false);}});
test('Greek receipt instruction does not demand alignment inside a box',()=>{const h=new Camera();assert.equal(h._r195Text('frame'),CAMERA_TEXT.el.frame);assert.equal(h._r195Text('other'),'other');});
test('three supported UI languages have every gap reason',()=>{for(const lang of ['el','de'])assert.deepEqual(Object.keys(GAP_TEXT[lang]),Object.keys(GAP_TEXT.en));});
class Cards { _recipeCard(r){if(r.hidden)return '';if(r.broken)throw new TypeError('private');return 'card';} _v66PreferLanguages(r){this.loaded=r;return r;} }
class Gaps extends RecipeGapsMixin(Cards){_v202GapsStyles(){} _v202GapHtml(reason){return 'gap:'+reason;} }
test('intentional filter and pagination empty returns do not become errors',()=>{const h=new Gaps();assert.equal(h._recipeCard({title:'Rice',hidden:true}),'');});
test('one card rendering error does not swallow subsequent cards',()=>{const h=new Gaps();assert.equal(h._recipeCard({title:'Rice',broken:true}),'gap:processing_error');assert.equal(h._recipeCard({title:'Other'}),'card');});
test('unreadable cards honor the same page limit',()=>{const h=new Gaps();h._v66Context={total:0,limit:1};assert.equal(h._recipeCard(null),'gap:processing_error');assert.equal(h._recipeCard(null),'');});
test('language hydration skips malformed data but retains list positions',async()=>{const h=new Gaps();const rows=await h._v66PreferLanguages([{title:'Rice'},null]);assert.equal(h.loaded.length,1);assert.equal(rows.length,2);assert.equal(rows[1]._v202Gap,'processing_error');});
