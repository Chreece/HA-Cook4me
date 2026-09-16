import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const version=process.env.COOK4ME_TEST_PANEL_VERSION||'80';
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu','--disable-software-rasterizer','--use-gl=disabled']});
try{
 const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><style>body{margin:0;font-family:Arial;--primary-color:#3d775d;--primary-text-color:#253b30;--primary-background-color:#f8faf8;--card-background-color:#fff;--secondary-background-color:#edf2ee;--secondary-text-color:#627468;--divider-color:#dce5df}</style><body></body>'}));
 await page.goto('http://cook4me.test/');
 await page.addScriptTag({path:fileURLToPath(new URL(`../custom_components/cook4me/frontend/cook4me-panel-v${version}-bundle.js`,import.meta.url))});
 await page.evaluate(version=>{
  const panel=document.createElement(`cook4me-recipe-hub-panel-v${version}`);window.panel=panel;window.calls=[];
  for(const method of ['_restorePreferences','_loadOverview','_loadBookState','_requestSection','_loadRecipeNutrition','_loadNutritionSettings','_loadFoodState','_loadInventoryState','_loadIngredientCatalog'])panel[method]=async()=>{};
  panel._hass={language:'en',user:{id:'scanner'},states:{},config:{country:'DE'},connection:{}};
  panel._entryId='one';panel._entries=[{entry_id:'one',title:'Kitchen Cook4Me',connected:true,state:{},recipes:[],profile:{diet:'vegetarian',houseIngredients:[],allergies:['peanuts'],avoid:[],preferences:[],householdMembers:[]}}];panel._tab='profile';
  panel._loadIngredientCatalog=async()=>{panel._ingredientCatalog=[{key:'rice',name:'Rice',searchAliases:['ρύζι']},{key:'milk',name:'Milk'}];panel._ingredientCatalogLanguage='en';};
  panel._capabilities={ingredientCatalogLanguage:'en',deviceCatalogLanguage:'en'};panel._ingredientCatalog=[{key:'rice',name:'Rice',searchAliases:['ρύζι']},{key:'milk',name:'Milk'}];panel._ingredientCatalogLanguage='en';panel._inventoryLoadedEntry='one';panel._nutritionSettings={};panel._foodState={history:[],summary:{}};
  window.state={storageLocations:[{id:'pantry',name:'Kitchen cupboard',kind:'pantry'},{id:'fridge',name:'Main fridge',kind:'fridge'}],houseIngredients:[],aiEntityId:'ai_task.photos',aiChoices:[{id:'ai_task.photos',name:'Photo assistant'}]};panel._v78AcceptState(structuredClone(window.state));
  panel._api=async(type,payload)=>{
   window.calls.push({type,...structuredClone(payload)});
   if(type.endsWith('/ingredient_info'))return {ingredientInfoContract:'offline-ingredient-info-v62',ingredient:{name:'Rice'},stock:null,catalogNutrition:null,nutritionReferences:[],exactNutritionLots:[],history:[],savedRecipeUsage:[],officialRecipeUsage:[]};
   if(type.endsWith('/scanner_state'))return structuredClone(window.state);
   if(type.endsWith('/barcode_lookup')){if(window.delayLookup)return new Promise(resolve=>window.releaseLookup=resolve);return {barcode:payload.barcode,product:{productName:'Wholegrain rice',quantity:500,unit:'g',nutrition:{basisQuantity:100,basisUnit:'g',values:{energyKcal:350,protein:8,salt:0}}},mapping:{ingredient:{key:'rice',name:'Rice'}},suggestions:[]};}
   if(type.endsWith('/product_add')){if(window.failSave){window.failSave=false;throw new Error('Connection lost; retry');}window.state.houseIngredients=[{key:'rice',name:'Rice',quantity:500,unit:'g',lots:[{id:'lot',quantity:500,storage:'pantry',storageLocationId:'pantry'}]}];return {...structuredClone(window.state),status:'added',warnings:[]};}
   if(type.endsWith('/recognize_photo')){const product=payload.mode==='date'?{bestBefore:'2027-03-10'}:payload.mode==='nutrition'?{nutrition:{basisQuantity:100,basisUnit:'g',values:{protein:0,salt:0.3}}}:{productName:'Brown rice',quantity:750,unit:'g'};return {product,suggestions:[{ingredient:{key:'rice',name:'Rice'}}]};}
   if(type.endsWith('/storage_location')){if(payload.action==='delete')window.state.storageLocations=window.state.storageLocations.filter(r=>r.id!==payload.identity);else if(payload.identity)Object.assign(window.state.storageLocations.find(r=>r.id===payload.identity),{name:payload.name,kind:payload.kind});else window.state.storageLocations.push({id:'new-place',name:payload.name,kind:payload.kind});return structuredClone(window.state);}
   return {};
  };
  document.body.append(panel);panel._renderShell();panel._renderTab();
 },version);
 const panel=page.locator(`cook4me-recipe-hub-panel-v${version}`);
 assert.equal(await panel.locator('.v78-advanced').count(),0,'Advanced ingredient entry is removed');
 await page.evaluate(()=>{
  window.cameraStarts=0;window.cameraStops=0;
  Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>{
   window.cameraStarts++;const canvas=document.createElement('canvas');canvas.width=640;canvas.height=480;canvas.getContext('2d').fillRect(0,0,640,480);
   const stream=canvas.captureStream(10);for(const track of stream.getTracks()){const stop=track.stop.bind(track);track.stop=()=>{window.cameraStops++;stop();};}return stream;
  }}});
  window.BarcodeDetector=class{async detect(){return window.detectedBarcode?[{rawValue:window.detectedBarcode}]:[];}};
 });
 assert.equal(await panel.locator('[data-v78-section=stock]').isVisible(),true);
 await panel.locator('[data-v78-pane=food]').click();await panel.locator('#preferences').fill('Quick dinners');
 await page.evaluate(()=>window.panel._renderTab());assert.equal(await panel.locator('#preferences').inputValue(),'Quick dinners');
 await panel.locator('[data-v78-pane=places]').click();await panel.locator('[name=name]').fill('Garage freezer');await panel.locator('[name=kind]').selectOption('freezer');await panel.locator('.v78-place-form button[type=submit]').click();await panel.locator('[data-place=new-place]').waitFor();
 await panel.locator('[data-place=new-place] [data-edit]').click();await panel.locator('[name=name]').fill('Utility freezer');await panel.locator('.v78-place-form button[type=submit]').click();await page.waitForFunction(()=>window.state.storageLocations.some(r=>r.name==='Utility freezer'));
 await panel.locator('[data-place=new-place] [data-delete]').click();await panel.locator('[data-place=new-place]').waitFor({state:'detached'});
 await panel.locator('[data-v78-pane=stock]').click();await panel.locator('[data-v78-open=barcode]').first().click();
 const dialog=panel.locator('dialog.v78-capture');await dialog.waitFor({state:'visible'});
 assert.equal(await dialog.locator('.v78-modes').count(),0,'No separate scanning modes');
 assert.equal(await dialog.locator('[data-v80-scan]').count(),4);
 assert.equal(await dialog.locator('video').count(),1);
 assert.equal(await dialog.locator('[data-v78-form]').count(),1);
 const camera=async()=>{await dialog.locator('[data-v78-camera]').click();await page.waitForFunction(()=>Boolean(window.panel._v78Stream)&&!window.panel._v80CameraPending&&window.panel._v78Dialog.querySelector('video').videoWidth>0);};
 for(const [width,height] of [[1280,900],[390,844],[360,740]]){
  await page.setViewportSize({width,height});const rect=await dialog.boundingBox();assert.deepEqual(rect,{x:0,y:0,width,height});
  const overflow=await dialog.evaluate(el=>({scroll:el.scrollWidth,client:el.clientWidth}));assert.ok(overflow.scroll<=overflow.client+1,`No horizontal overflow at ${width}px`);
 }
 await page.setViewportSize({width:1280,height:900});
 await dialog.locator('[data-draft=barcode]').fill('12345678');await dialog.locator('[data-v78-lookup]').click();await page.waitForFunction(()=>window.panel._v78Draft.productName==='Wholegrain rice');
 assert.equal((await page.evaluate(()=>window.calls.filter(r=>r.type.endsWith('/product_add')))).length,0,'Barcode lookup only fills a draft');
 assert.equal(await dialog.locator('[data-v78-ingredient]').inputValue(),'k:rice');
 await dialog.locator('[data-draft=storageLocationId]').selectOption('pantry');
 await camera();await dialog.locator('[data-v80-scan=date]').click();
 await page.waitForFunction(()=>window.panel._v78Draft.bestBefore==='2027-03-10'&&!window.panel._v78Busy);
 assert.equal(await dialog.locator('[data-draft=bestBefore]').inputValue(),'2027-03-10');assert.equal(await dialog.locator('[data-draft=productName]').inputValue(),'Wholegrain rice');
 await camera();await dialog.locator('[data-v80-scan=nutrition]').click();
 await page.waitForFunction(()=>window.panel._v78Draft.nutrition.values.protein===0&&!window.panel._v78Busy);
 const photos=await page.evaluate(()=>window.calls.filter(r=>r.type.endsWith('/recognize_photo')));
 assert.deepEqual(photos.map(r=>r.mode),['date','nutrition']);assert.ok(photos.every(r=>r.image.startsWith('data:image/jpeg;base64,')));
 assert.equal(await dialog.locator('[data-draft=bestBefore]').inputValue(),'2027-03-10');
 assert.equal(await dialog.locator('[data-nutrient=protein]').inputValue(),'0');assert.equal(await dialog.locator('[data-nutrient=fat]').inputValue(),'');
 await page.evaluate(()=>window.failSave=true);await dialog.locator('[data-v78-save]').click();await page.waitForFunction(()=>window.panel._v78Status.includes('Connection lost'));
 assert.equal(await dialog.locator('[data-draft=quantity]').isDisabled(),true,'Unknown outcome preserves the exact retry payload');
 await dialog.locator('[data-v78-save]').click();await dialog.locator('.v78-success').waitFor();
 const saves=await page.evaluate(()=>window.calls.filter(r=>r.type.endsWith('/product_add')));assert.equal(saves.length,2);assert.deepEqual(saves[0],saves[1]);assert.equal(saves[0].lot_metadata.storageLocationId,'pantry');assert.equal(saves[0].best_before,'2027-03-10');assert.equal(saves[0].nutrition.values.protein,0);assert.ok(!('fat' in saves[0].nutrition.values));
 await dialog.locator('[data-v78-next]').click();await dialog.locator('[data-draft=productName]').fill('Rice from market');await dialog.locator('[data-draft=quantity]').fill('250');await dialog.locator('[data-v78-ingredient]').selectOption('k:rice');await dialog.locator('[data-draft=storageLocationId]').selectOption('fridge');
 await dialog.locator('[data-v78-close]').click();assert.equal(await dialog.locator('.v78-discard').isVisible(),true);await dialog.locator('[data-v78-keep]').click();assert.equal(await dialog.locator('[data-draft=productName]').inputValue(),'Rice from market');
 await dialog.locator('[data-v78-save]').click();await dialog.locator('.v78-success').waitFor();await dialog.locator('[data-v78-close]').first().click();
 // Pending camera permission must not leak a stream after closing.
 // Product AI is triggered directly by its button using the same camera.
 await panel.locator('[data-v78-open=barcode]').first().click();
 await dialog.locator('[data-v80-scan=product]').click();
 await page.waitForFunction(()=>!window.panel._v80CameraPending&&window.panel._v78Dialog.querySelector('video').videoWidth>0);
 await dialog.locator('[data-v80-scan=product]').click();
 await page.waitForFunction(()=>window.panel._v78Draft.productName==='Brown rice'&&!window.panel._v78Busy);
 await dialog.locator('[data-draft=bestBefore]').fill('2028-01-02');
 await camera();await dialog.locator('[data-v80-scan=nutrition]').click();
 await page.waitForFunction(()=>window.panel._v78Draft.nutrition.values.protein===0&&!window.panel._v78Busy);
 await page.evaluate(()=>window.detectedBarcode='12345678');
 await dialog.locator('[data-v80-scan=barcode]').click();
 await page.waitForFunction(()=>window.panel._v78Draft.productName==='Wholegrain rice'&&!window.panel._v78Busy);
 assert.equal(await dialog.locator('[data-draft=bestBefore]').inputValue(),'2028-01-02');
 assert.equal(await dialog.locator('[data-nutrient=protein]').inputValue(),'0','Barcode does not replace the scanned label with generic nutrition');
 await page.evaluate(()=>{window.detectedBarcode='';window.panel._v78Close(true);});
 await panel.locator('[data-v78-open=barcode]').first().click();
 await page.evaluate(()=>{window.stopped=0;Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:()=>new Promise(resolve=>window.releaseCamera=resolve)}});});
 await dialog.locator('[data-v78-camera]').click();await dialog.locator('[data-v78-close]').click();await page.evaluate(()=>window.releaseCamera({getTracks:()=>[{stop:()=>window.stopped++}]}));await page.waitForFunction(()=>window.stopped===1);
 // Late recognized products cannot overwrite another capture or device.
 await panel.locator('[data-v78-open=barcode]').first().click();await page.evaluate(()=>window.delayLookup=true);await dialog.locator('[data-draft=barcode]').fill('99999999');await dialog.locator('[data-v78-lookup]').click();
 await page.evaluate(()=>{window.panel._v78Close(true);void window.panel._v78Open('manual');window.releaseLookup({barcode:'99999999',product:{productName:'Stale'}});});
 assert.equal(await dialog.locator('[data-draft=productName]').inputValue(),'');
 await page.evaluate(()=>window.panel._v78Close(true));
 // Store linked IDs survive stock-row edits and row removals.
 const lots=await page.evaluate(()=>{const p=window.panel,row={unit:'g',lots:[{id:'old',quantity:5,storageLocationId:'fridge'},{id:'keep',quantity:8,storageLocationId:'pantry'}]};const c=document.createElement('div');c.innerHTML=p._lotRowHtml(row.lots[1],1,'g');return p._collectLots(c,row,'g');});assert.equal(lots[0].id,'keep');assert.equal(lots[0].storageLocationId,'pantry');
 // Click a real ingredient button in the rendered recipe card.
 await page.evaluate(()=>{
  const p=window.panel,recipe={id:'test-rice',title:'Rice supper',servings:2,language:'en',ingredients:[{key:'rice',name:'Rice',quantity:200,unit:'g'}],steps:[],match:{safe:true}};
  const node=document.createElement('div');node.id='v80-recipe';p.shadowRoot.append(node);const state=p._v66State(recipe);state.expanded=true;node.innerHTML=p._v66Body(recipe,true,state);p._v66BindRecipe(node,recipe,true);
 });
 await panel.locator('#v80-recipe [data-v66-section=ingredients]>summary').click();
 await panel.locator('#v80-recipe [data-v66-ingredient]').first().click();
 await panel.locator('[data-ingredient-dialog]').waitFor({state:'visible'});
 assert.match(await panel.locator('[data-ingredient-dialog]').innerText(),/Rice/);
 await panel.locator('[data-ingredient-dialog] [data-close]').click();
 await page.evaluate(()=>window.panel.shadowRoot.querySelector('#v80-recipe').remove());
 // Screenshots and layout checks for all supported UI languages.

 if(process.env.COOK4ME_SCANNER_SCREENSHOT){await page.setViewportSize({width:1280,height:900});await panel.locator('#content').screenshot({path:process.env.COOK4ME_SCANNER_SCREENSHOT+'-kitchen.png'});}
 for(const lang of ['en','de','el']){await page.evaluate(lang=>{window.panel._hass.language=lang;window.panel._renderTab();void window.panel._v78Open('manual');},lang);await page.setViewportSize({width:390,height:844});const overflow=await dialog.evaluate(el=>el.scrollWidth-el.clientWidth);assert.ok(overflow<=1,`${lang} mobile scanner fits`);await page.evaluate(()=>window.panel._v78Close(true));}
 if(process.env.COOK4ME_SCANNER_SCREENSHOT){await page.evaluate(()=>{window.panel._hass.language='en';void window.panel._v78Open('barcode');});await dialog.screenshot({path:process.env.COOK4ME_SCANNER_SCREENSHOT+'-mobile.png'});await page.setViewportSize({width:1280,height:900});await dialog.screenshot({path:process.env.COOK4ME_SCANNER_SCREENSHOT+'-desktop.png'});}
 assert.deepEqual(errors,[]);console.log('v80 browser: desktop/mobile/fullscreen, profile drafts, storage CRUD, review-only barcode, date/nutrition drafts, manual save, exact retries, camera cleanup, stale results and stock location edits passed');
}finally{await browser.close();}
