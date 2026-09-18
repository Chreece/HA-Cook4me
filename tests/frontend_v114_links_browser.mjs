import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const version=process.env.COOK4ME_TEST_PANEL_VERSION||'114';
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu','--disable-software-rasterizer','--use-gl=disabled']});
try{
 const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[];
 page.on('pageerror',error=>{errors.push(error.message);console.error(error.stack);});
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><style>body{margin:0;font-family:Arial;--primary-color:#3d775d;--primary-text-color:#253b30;--primary-background-color:#f8faf8;--card-background-color:#fff;--secondary-background-color:#edf2ee;--secondary-text-color:#627468;--divider-color:#dce5df}</style><body></body>'}));
 await page.goto('http://cook4me.test/');
 await page.addScriptTag({path:fileURLToPath(new URL(`../custom_components/cook4me/frontend/cook4me-panel-v${version}-bundle.js`,import.meta.url))});
 await page.evaluate(version=>{
  const panel=document.createElement(`cook4me-recipe-hub-panel-v${version}`);window.panel=panel;window.calls=[];
  for(const method of ['_restorePreferences','_loadOverview','_loadBookState','_requestSection','_loadRecipeNutrition','_loadNutritionSettings','_loadFoodState','_loadInventoryState','_loadIngredientCatalog'])panel[method]=async()=>{};
  panel._hass={language:'en',user:{id:'scanner'},states:{},config:{country:'DE'},connection:{}};
  panel._entryId='one';panel._entries=[{entry_id:'one',title:'Kitchen Cook4Me',connected:true,state:{},recipes:[],profile:{diet:'vegetarian',houseIngredients:[],allergies:['peanuts'],avoid:[],preferences:[],householdMembers:[]}}];panel._tab='profile';
  panel._loadIngredientCatalog=async()=>{panel._ingredientCatalog=[{key:'rice',name:'Rice',searchAliases:['ρύζι']},{key:'milk',name:'Milk'}];panel._ingredientCatalog.push(...Array.from({length:400},(_,i)=>({key:'food-'+i,name:'Ingredient '+String(i).padStart(3,'0'),searchAliases:['Alias '+i,'Υλικό '+i]})));panel._ingredientCatalogLanguage='en';};
  panel._capabilities={ingredientCatalogLanguage:'en',deviceCatalogLanguage:'en'};panel._ingredientCatalog=[{key:'rice',name:'Rice',searchAliases:['ρύζι']},{key:'milk',name:'Milk'}];panel._ingredientCatalog.push(...Array.from({length:400},(_,i)=>({key:'food-'+i,name:'Ingredient '+String(i).padStart(3,'0'),searchAliases:['Alias '+i,'Υλικό '+i]})));panel._ingredientCatalogLanguage='en';panel._inventoryLoadedEntry='one';panel._nutritionSettings={};panel._foodState={history:[],summary:{}};
  window.state={storageLocations:[{id:'pantry',name:'Kitchen cupboard',kind:'pantry'},{id:'fridge',name:'Main fridge',kind:'fridge'}],houseIngredients:[],aiEntityId:'ai_task.photos',aiChoices:[{id:'ai_task.photos',name:'Photo assistant'}]};panel._v78AcceptState(structuredClone(window.state));
  panel._api=async(type,payload)=>{
   window.calls.push({type,...structuredClone(payload)});
   if(type.endsWith('/ingredient_info'))return {ingredientInfoContract:'offline-ingredient-info-v62',ingredient:{name:'Rice'},stock:null,catalogNutrition:null,nutritionReferences:[],exactNutritionLots:[],history:[],savedRecipeUsage:[],officialRecipeUsage:[]};
   if(type.endsWith('/scanner_state'))return structuredClone(window.state);
   if(type.endsWith('/barcode_lookup')){if(window.delayLookup)return new Promise(resolve=>window.releaseLookup=resolve);if(payload.barcode==='99999999')return {barcode:payload.barcode,product:{found:false},suggestions:[]};return {barcode:payload.barcode,product:{productName:'Wholegrain rice',quantity:500,unit:'g',nutrition:{basisQuantity:100,basisUnit:'g',values:{energyKcal:350,protein:8,salt:0}}},match:{ingredient:{key:'rice',name:'Rice'},score:1},suggestions:[]};}
   if(type.endsWith('/product_add')){if(window.failSave){window.failSave=false;throw new Error('Connection lost; retry');}window.state.houseIngredients=[{key:'rice',name:'Rice',quantity:500,unit:'g',lots:[{id:'lot',quantity:500,storage:'pantry',storageLocationId:'pantry'}]}];return {...structuredClone(window.state),status:'added',warnings:[]};}
   if(type.endsWith('/recognize_photo')){if(window.delayPhoto)return new Promise(resolve=>window.releasePhoto=resolve);const product=payload.mode==='date'?{bestBefore:'2027-03-10'}:payload.mode==='nutrition'?{nutrition:{basisQuantity:100,basisUnit:'g',values:{protein:0,salt:0.3}}}:{productName:'Brown rice',quantity:750,unit:'g'};return {product,match:{ingredient:{key:'rice',name:'Rice'},score:1},suggestions:[{ingredient:{key:'rice',name:'Rice'}}]};}
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

 await page.evaluate(()=>{
  window.state.houseIngredients=[{key:'rice',name:'Rice',quantity:750,unit:'g',lots:[{id:'first',quantity:500,productName:'First rice',storageLocationId:'pantry'},{id:'second',quantity:250,productName:'Second rice',storageLocationId:'fridge'}]}];
  panel._v78AcceptState(structuredClone(state));panel._renderTab();
  const original=panel._api;panel._api=async(type,payload)=>{
   if(type.endsWith('/product_price'))return {estimate:3,reference:{amount:3,currency:'EUR',basisQuantity:500,basisUnit:'g',source:'purchase',country:'DE'},settings:{currency:'EUR',country:'DE'}};
   if(type.endsWith('/product_details')){calls.push({type,...structuredClone(payload)});const row=state.houseIngredients.find(row=>row.lots.some(lot=>lot.id===payload.lot_id)),lot=row.lots.find(lot=>lot.id===payload.lot_id);return {lot,unit:row.unit,ingredient:{key:row.key,name:row.name},version:'version-'+lot.id,nutrition:lot.nutrition,paidPrice:lot.paidPrice};}
   if(type.endsWith('/product_add')){
    calls.push({type,...structuredClone(payload)});if(window.failSave){window.failSave=false;throw new Error('Connection lost; retry');}
    const row=state.houseIngredients[0];
    const make=id=>({id,ingredientLinks:payload.ingredient_links,quantity:Number(payload.quantity),...payload.lot_metadata,bestBefore:payload.best_before,nutrition:payload.nutrition,paidPrice:payload.paid_price?{...payload.paid_price,basisQuantity:payload.paid_price.basisQuantity||Number(payload.quantity),basisUnit:payload.paid_price.basisUnit||payload.unit}:null});
    if(payload.edit_lot_id)row.lots=row.lots.map(lot=>lot.id===payload.edit_lot_id?make(lot.id):lot);
    else for(let i=0;i<payload.package_count;i++)row.lots.push(make('new-'+i));
    row.quantity=row.lots.reduce((total,lot)=>total+lot.quantity,0);return {...structuredClone(state),status:'added',warnings:[]};
   }
   return original(type,payload);
  };
 });
 const groups=panel.locator('.v112-stock-group');assert.equal(await groups.count(),2);assert.equal(await groups.first().getAttribute('open'),null);
 await panel.locator('[data-v78-open=barcode]').first().click();
 const dialog=panel.locator('dialog.v78-capture'),frame=dialog.locator('[data-v111-frame]');
 await page.waitForFunction(()=>panel._v78Stream&&!panel._v80CameraPending&&panel._v78Dialog.querySelector('video').videoWidth>0);
 const restart=frame.locator('[data-v113-restart]');
 assert.equal(await restart.isVisible(),true);assert.equal(await restart.isEnabled(),true);
 await page.evaluate(()=>{window.originalStream=panel._v78Stream;window.delayLookup=true;window.detectedBarcode='12345678';});
 await frame.locator('.v111-spinner').waitFor();
 await page.evaluate(()=>{window.detectedBarcode='';window.delayLookup=false;});
 await restart.click();
 await page.evaluate(()=>releaseLookup({barcode:'12345678',product:{productName:'Stale product'},mapping:{ingredientLinks:[{key:'milk',name:'Milk'}]}}));
 await page.waitForFunction(()=>panel._v78Draft.scanPhase==='scanning'&&!panel._v78Busy);
 assert.equal(await page.evaluate(()=>panel._v78Draft.productName),'');assert.deepEqual(await page.evaluate(()=>panel._v78Draft.ingredientLinks),[]);
 await page.evaluate(()=>window.detectedBarcode='12345679');
 await page.waitForFunction(()=>panel._v78Draft.scanRecognized&&!panel._v78Busy);
 assert.equal(await restart.isVisible(),true);
 await frame.locator('[data-v112-details]').click();
 assert.equal(await frame.locator('[data-v114-link]').count(),402,'Full catalogue available for multiple assignment');
 await frame.locator('[data-v114-links]').getByLabel('Milk',{exact:true}).check();
 await frame.locator('[data-v78-search]').fill('Alias 399');
 await frame.locator('[data-v114-links]').getByLabel('Ingredient 399',{exact:true}).check();
 assert.deepEqual(await page.evaluate(()=>panel._v114Links().map(row=>row.key)),['rice','milk','food-399']);
 await frame.locator('[data-v114-links]').getByLabel('Ingredient 399',{exact:true}).uncheck();
 await frame.locator('main [data-draft=productName]').fill('My pantry product');
 await frame.locator('[data-v112-back]').click();
 assert.equal(await frame.locator('[data-v112-details] strong').innerText(),'My pantry product (Rice, Milk)');
 await frame.locator('[data-v112-count]').fill('3');await frame.locator('[data-v111-place]').selectOption('fridge');
 await frame.locator('[data-v113-expiry]').fill('2027-11-21');
 // Restart is beside Apply throughout, including recognised products and label modes.
 for(const mode of ['date','nutrition','product','barcode']){
  await frame.locator(`[data-v80-scan=${mode}]`).click();assert.equal(await restart.isVisible(),true);assert.equal(await restart.isEnabled(),true);
 }
 for(const [width,height] of [[1280,900],[390,844],[360,740]]){
  await page.setViewportSize({width,height});
  const bounds=await frame.boundingBox(),retry=await restart.boundingBox(),apply=await frame.locator('[data-v112-apply]').boundingBox();
  assert.ok(retry.x>=bounds.x&&retry.x+retry.width<=apply.x&&apply.x-retry.x-retry.width<=8);
  assert.ok(apply.x+apply.width<=bounds.x+bounds.width);
  if(process.env.COOK4ME_SCANNER_SCREENSHOT)await frame.screenshot({path:process.env.COOK4ME_SCANNER_SCREENSHOT+`-${width}.png`});
 }
 await page.evaluate(()=>window.failSave=true);
 await frame.locator('[data-v112-apply]').click();
 await page.waitForFunction(()=>panel._v78Draft.scanPhase==='error'&&!panel._v78Busy);
 assert.equal(await restart.isVisible(),true);assert.equal(await restart.isEnabled(),true);
 await restart.click();
 await page.waitForFunction(()=>!panel._v78Draft.productLocked&&panel._v78Draft.scanPhase==='scanning');
 const save=await page.evaluate(()=>calls.filter(row=>row.type.endsWith('/product_add')).at(-1));
 assert.deepEqual(await page.evaluate(()=>calls.filter(row=>row.type.endsWith('/product_add'))[0]),save,'Restart finishes the same uncertain save before advancing');
 assert.deepEqual(save.ingredient_links.map(row=>row.key),['rice','milk']);assert.equal(save.package_count,3);
 assert.equal(await page.evaluate(()=>state.houseIngredients[0].quantity),2250);
 assert.equal(await page.evaluate(()=>state.houseIngredients[0].lots.length),5);
 await page.evaluate(()=>panel._v78Close(true));
 assert.equal(await groups.count(),3,'Different product names keep separate folded groups');
 const product=groups.filter({hasText:'My pantry product (Rice, Milk)'});
 assert.equal(await product.count(),1);assert.equal(await product.getAttribute('open'),null);
 assert.match(await product.locator('summary').innerText(),/1,500 g/);
 await product.locator('summary').click();assert.equal(await product.locator('[data-v112-edit-lot]').count(),3);
 await product.locator('[data-v112-edit-lot="new-0"]').click();
 await frame.locator('[data-v114-links]').waitFor();
 assert.equal(await frame.locator('[data-v114-links]').getByLabel('Milk',{exact:true}).isChecked(),true);
 await frame.locator('[data-v114-links]').getByLabel('Rice',{exact:true}).uncheck();
 assert.equal(await page.evaluate(()=>panel._v78Draft.ingredient.key),'milk');
 await frame.locator('[data-v112-apply]').click();await page.waitForFunction(()=>!panel._v78Dialog);
 const edit=await page.evaluate(()=>calls.filter(row=>row.type.endsWith('/product_add')).at(-1));
 assert.equal(edit.edit_lot_id,'new-0');assert.deepEqual(edit.ingredient_links.map(row=>row.key),['milk']);
 // Restart after recognition discards only that unsaved review and keeps the camera.
 await panel.locator('[data-v78-open=barcode]').first().click();
 await page.evaluate(()=>window.detectedBarcode='87654321');
 await page.waitForFunction(()=>panel._v78Draft.scanRecognized&&!panel._v78Busy);
 await page.evaluate(()=>{window.detectedBarcode='';window.restartStream=panel._v78Stream;});await restart.click();
 assert.equal(await page.evaluate(()=>panel._v78Draft.productLocked),false);assert.equal(await page.evaluate(()=>panel._v78Draft.bestBefore),'');
 assert.equal(await page.evaluate(()=>panel._v78Stream===restartStream),true);
 await page.evaluate(()=>panel._v78Close(true));
 assert.deepEqual(errors,[]);
 console.log('v114 browser: always-visible Restart, pending lookup cancellation, multiple searchable catalogue links, additive package save, product-name stock grouping, persisted link editing and continuous camera passed');
}finally{await browser.close();}
