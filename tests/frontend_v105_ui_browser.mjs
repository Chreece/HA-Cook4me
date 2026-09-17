import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
const root=fileURLToPath(new URL('..',import.meta.url));
const fixture=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-c',`import importlib.util,json
s=importlib.util.spec_from_file_location('catalog','custom_components/cook4me/release_catalog.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
x=json.load(open('custom_components/cook4me/catalog/merged_catalog.v1.json'))
v=next(v for r in x['recipes'] for v in r['variants'] if v['title']=='Porridge fraises coco' and v.get('yield',{}).get('quantity')==4)
print(json.dumps({'catalogs':{lang:{'items':c.ingredient_choices(lang),'presentationVersion':63,'offline':True} for lang in ['en','de','el']},'recipes':[c.recipe_by_variant(str(v['variantId']),language='fr',configured_language='el',country='DE'),c.recipe_by_variant('314559',language='ro',configured_language='el',country='DE')]}))`],{cwd:root,maxBuffer:30_000_000}));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage({viewport:{width:1360,height:960}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><style>body{margin:0;font-family:Arial;--primary-color:#009bbb;--primary-text-color:#eee;--primary-background-color:#111;--card-background-color:#1e2223;--secondary-background-color:#222;--secondary-text-color:#aaa;--divider-color:#444}</style><body></body>'}));
 await page.goto('http://cook4me.test/');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v105-bundle.js'});
 await page.evaluate(fixture=>{
  window.fixture=fixture;window.calls=[];
  globalThis.customElements.define('cook4me-v105-test',class extends globalThis.customElements.get('cook4me-recipe-hub-panel-v105'){connectedCallback(){} disconnectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v105-test');
  for(const method of ['_restorePreferences','_loadOverview','_loadBookState','_requestSection','_loadRecipeNutrition','_loadNutritionSettings','_loadFoodState','_loadInventoryState','_loadTodayOptions'])p[method]=async()=>{};
  p._hass={language:'en',user:{id:'alice'},states:{},config:{country:'DE'},connection:{sendMessagePromise:async()=>({}),subscribeMessage:async()=>()=>{},addEventListener(){},removeEventListener(){}}};
  p._entryId='one';p._entries=['one','two'].map(id=>({entry_id:id,title:id,connected:true,state:{phase:'idle'},recipes:[],profile:{diet:'vegetarian',houseIngredients:[],allergies:[],avoid:[],preferences:[],householdMembers:[]}}));p._tab='profile';
  p._capabilities={ingredientCatalogLanguage:'en',deviceCatalogLanguage:'en'};p._ingredientCatalog=[];p._inventoryLoadedEntry='one';p._houseEntryId='one';p._nutritionSettings={};p._foodState={history:[],summary:{}};
  p._v78AcceptState({storageLocations:[{id:'pantry',name:'Pantry',kind:'pantry'}],houseIngredients:[],aiEntityId:'',aiChoices:[]});
  p._v86QueuePreview=()=>{};p._v79SchedulePrice=()=>{};
  p._api=async(type,data={})=>{
   calls.push({type,...data});
   if(type.endsWith('/ingredient_catalog')){
    if(window.failCatalog){window.failCatalog=false;throw Error('Temporarily unavailable');}
    if(window.delayCatalog)return new Promise(resolve=>window.releaseCatalog=()=>resolve(structuredClone(fixture.catalogs[data.language])));
    return structuredClone(fixture.catalogs[data.language]);
   }
   if(type.endsWith('/ingredient_info')){window.requestedIngredient=data.ingredient;return {ingredientInfoContract:'offline-ingredient-info-v62',ingredient:data.ingredient,stock:{quantity:2,unit:'pcs',lots:[{quantity:1}]}};}
   if(type.endsWith('/scanner_state'))return p._v78State;
   if(type.endsWith('/price_settings'))return {settings:{country:'DE',currency:'EUR',autoGlobalPrices:false}};
   return {};
  };
  document.body.append(p);p._renderShell();p._renderTab();
 },fixture);
 const p=page.locator('cook4me-v105-test');
 await page.waitForFunction(()=>panel._ingredientCatalog.length>3000);
 assert.equal(await page.evaluate(()=>calls.filter(r=>r.type.endsWith('/ingredient_catalog')).length),1);
 const select=p.locator('[data-v105-select]'),search=p.locator('[data-v84-search]');
 assert.equal(await select.locator('option').count(),fixture.catalogs.en.items.length+1);
 assert.equal(await p.locator('[data-v84-rows]').count(),0);
 assert.equal(await p.locator('[data-v105-info]').isDisabled(),true);
 await search.fill('basmati');assert.ok(await select.locator('option').count()>1);await select.selectOption('0');
 await p.locator('[data-v105-info]').click();await p.locator('[data-ingredient-dialog]').waitFor();
 assert.match(await page.evaluate(()=>requestedIngredient.name),/basmati/i);
 await p.locator('[data-ingredient-dialog] [data-close]').click();
 await p.locator('[data-v105-add]').click();await page.waitForFunction(()=>!!panel._v78Draft?.ingredient);
 assert.match(await page.evaluate(()=>panel._v78Draft.ingredient.name),/basmati/i);
 const unit=p.locator('[data-draft=unit]');assert.equal(await unit.evaluate(n=>n.tagName),'SELECT');
 await unit.selectOption('pcs');assert.equal(await page.evaluate(()=>panel._v78Draft.unit),'pcs');
 await page.evaluate(()=>panel._v78Close(true));
 await page.evaluate(()=>panel._renderTab());assert.equal(await select.inputValue(),'0');
 await search.fill('not-an-ingredient-123');assert.equal(await select.isDisabled(),true);assert.equal(await p.locator('[data-v105-add]').isDisabled(),true);
 await search.fill('');assert.equal(await select.locator('option').count(),fixture.catalogs.en.items.length+1);
 await select.selectOption(String(fixture.catalogs.en.items.length-1));assert.equal(await p.locator('[data-v105-info]').isEnabled(),true);
 // Catalog failure settles with a usable retry; overlapping language loads remain scoped.
 await page.evaluate(()=>{panel._ingredientCatalog=[];window.failCatalog=true;void panel._loadIngredientCatalog(null,true);});
 await page.waitForFunction(()=>!!panel._v63CatalogFailure&&!panel._ingredientCatalogLoading);
 await p.locator('[data-v84-retry]').click();await page.waitForFunction(()=>panel._ingredientCatalog.length>3000);
 await page.evaluate(()=>{window.delayCatalog=true;panel._ingredientCatalog=[];window.first=panel._loadIngredientCatalog(null,true);window.second=panel._loadIngredientCatalog();});
 assert.equal(await page.evaluate(()=>first===second),true);
 await page.evaluate(()=>{window.delayCatalog=false;panel._hass.language='el';void panel._loadIngredientCatalog();});
 await page.waitForFunction(()=>panel._ingredientCatalog[0]?.displayLanguage==='el');
 await page.evaluate(async()=>{releaseCatalog();await first;});
 assert.equal(await select.locator('option').count(),fixture.catalogs.el.items.length+1);
 await search.fill('ρύζι');assert.ok(await select.locator('option').count()>1);
 for(const width of [360,390,1360]){
  await page.setViewportSize({width,height:960});
  const position=await p.locator('.v105-catalog-controls').evaluate(node=>{
   const a=node.querySelector('input').getBoundingClientRect(),b=node.querySelector('select').getBoundingClientRect();
   return {sameRow:Math.abs(a.top-b.top)<2,right:b.left>a.right,overflow:node.scrollWidth>node.clientWidth+1};
  });assert.deepEqual(position,{sameRow:true,right:true,overflow:false});
  if(process.env.COOK4ME_SCREENSHOT_DIR)await p.locator('[data-v84-catalog]').screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+`/v105-dropdown-${width}.png`});
 }
 // Use actual French and Romanian recipe objects; presentation must not rewrite them.
 for(const [language,pinch,spoon,pieces] of [['el','πρέζα','κ.γ.','τεμ.'],['de','Prise','TL','Stück'],['en','pinch','tsp','pcs']]){
  const result=await page.evaluate(language=>{
   panel._hass.language=language;const values=[];
   for(const recipe of fixture.recipes){
    const before=JSON.stringify(recipe.ingredients),box=panel._v67Dom(panel._v66Body(recipe,false,panel._v66State(recipe)));
    values.push({quantities:[...box.querySelectorAll('.rx-v66-quantity')].map(n=>n.textContent),unchanged:before===JSON.stringify(recipe.ingredients),payload:panel._v79Payload(recipe).ingredients});
   }
   return {values,amounts:[panel._displayAmount(1,'pincée','UNIT_42'),panel._displayAmount(2,'pincée','UNIT_42'),panel._displayAmount(1,'càc','UNIT_11'),panel._displayAmount(20,'buc','UNIT_41'),panel._displayAmount(0,'g','UNIT_27')],
    stock:panel._stockText({quantity:2,unit:'pcs'}),spoon:panel._v94QuantityText({kind:'usda_portion',sourceQuantity:1,sourceUnit:'càc',quantity:2.6,unit:'g'}),
    reference:panel._v67Dom(panel._v79Reference({source:'manual',basisQuantity:2,basisUnit:'pcs',currency:'EUR',amount:1,country:'DE'})).textContent,
    unitOptions:panel._unitInput('tbsp','data-test'),speech:panel._v72Text('original')};
  },language);
  assert.equal(result.amounts[0],`1 ${pinch}`);assert.equal(result.amounts[2],`1 ${spoon}`);assert.equal(result.amounts[3],`20 ${pieces}`);
  assert.ok(result.values[0].quantities.includes(`1 ${pinch}`),JSON.stringify({language,result}));assert.ok(result.values[0].quantities.includes(`1 ${spoon}`));
  assert.ok(result.values[1].quantities.includes(`20 ${pieces}`));
  for(let i=0;i<result.values.length;i++){assert.equal(result.values[i].unchanged,true);assert.deepEqual(result.values[i].payload,fixture.recipes[i].ingredients);}
  assert.ok(result.stock.includes(`2 ${pieces}`));assert.ok(result.reference.includes(`2 ${pieces}`));assert.ok(result.spoon.includes(`1 ${spoon}`));
  assert.ok(result.speech.length>80);assert.match(result.unitOptions,/value="tbsp" selected/);
 }
 // Same quantity ID renders in the new UI language immediately; missing quantity stays missing.
 const remaining=await page.evaluate(()=>{
  panel._hass.language='el';panel._manualDraftIngredients=[{name:'Salt',quantity:1,unit:'tsp'}];
  const manual=panel._v67Dom(panel._manualIngredientsHtml()).querySelector('[data-manual-unit]');
  return {manualValue:manual.value,manualLabel:manual.selectedOptions[0].textContent,missing:panel._displayAmount(undefined,''),
   unknown:panel._displayAmount(2,'custom unit'),leaf:panel._displayAmount(2,'feuille','UNIT_24'),pod:panel._displayAmount(2,'gousse','UNIT_28',{canonicalName:'Vanilla pod'}),
   lot:panel._v67Dom(panel._lotRowHtml({quantity:2},0,'pcs')).textContent};
 });
 assert.equal(remaining.manualValue,'tsp');assert.equal(remaining.manualLabel,'κ.γ.');assert.equal(remaining.missing,'');
 assert.equal(remaining.unknown,'2 custom unit');assert.equal(remaining.leaf,'2 φύλλα');assert.equal(remaining.pod,'2 λοβοί');assert.match(remaining.lot,/τεμ\./);
 assert.deepEqual(errors,[]);console.log('v105: real multilingual recipes and full catalog; translated units, unchanged pricing payloads, canonical form values, dropdown search/details/add/retry/language race and 360/390/1360 px layouts passed');
}finally{await browser.close();}
