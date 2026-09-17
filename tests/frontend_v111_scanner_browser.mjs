import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const version=process.env.COOK4ME_TEST_PANEL_VERSION||'111';
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
 await panel.locator('[data-v78-open=barcode]').first().click();
 const dialog=panel.locator('dialog.v78-capture'),frame=dialog.locator('[data-v111-frame]');
 await page.waitForFunction(()=>panel._v78Stream&&!panel._v80CameraPending&&panel._v78Dialog.querySelector('video').videoWidth>0);
 await page.evaluate(()=>{window.originalStream=panel._v78Stream;window.originalVideo=panel._v78Dialog.querySelector('video');});
 assert.equal(await frame.locator('[data-v80-scan]').count(),4);
 assert.equal(await dialog.locator('[data-v78-ingredient] option').count(),403,'Every catalog ingredient is available, including entries after 150');
 await dialog.locator('[data-v78-search]').fill('Υλικό 399');
 assert.equal(await dialog.locator('[data-v78-ingredient] option').count(),2,'Picker searches multilingual aliases');
 await dialog.locator('[data-v78-search]').fill('');
 await page.evaluate(()=>{delayLookup=true;detectedBarcode='12345678';});
 await frame.locator('.v111-spinner').waitFor();
 assert.equal(await page.evaluate(()=>cameraStarts),1);assert.equal(await page.evaluate(()=>cameraStops),0);
 assert.equal(await page.evaluate(()=>panel._v78Stream===originalStream),true);
 await page.evaluate(()=>{delayLookup=false;detectedBarcode='';releaseLookup({barcode:'12345678',product:{found:true,productName:'Wholegrain rice',quantity:500,unit:'g',nutrition:{basisQuantity:100,basisUnit:'g',values:{protein:8,salt:0}}},match:{ingredient:{key:'rice',name:'Rice'},score:1},suggestions:[]});});
 await page.waitForFunction(()=>panel._v78Draft.scanPhase==='recognized'&&!panel._v78Busy);
 assert.match(await frame.innerText(),/Wholegrain rice/);
 assert.equal(await frame.locator('.v111-ok').count(),1);
 assert.equal(await frame.locator('[data-v111-amount]').inputValue(),'500');
 assert.equal(await dialog.locator('[data-v78-ingredient]').inputValue(),'k:rice');
 assert.equal(await page.evaluate(()=>panel._v78Dialog.querySelector('video')===originalVideo),true,'Form redraw reuses the live video element');
 assert.equal(await page.evaluate(()=>cameraStops),0);
 assert.equal(await page.evaluate(()=>calls.filter(row=>row.type.endsWith('/product_add')).length),0,'Recognition does not silently add stock');
 // Label modes keep the last product and attach their results to it.
 await frame.locator('[data-v80-scan=date]').click();
 assert.equal(await frame.getAttribute('data-mode'),'date');
 assert.match(await frame.locator('[data-v111-target]').innerText(),/Wholegrain rice/);
 await frame.locator('[data-v78-take]').click();
 await page.waitForFunction(()=>panel._v78Draft.bestBefore==='2027-03-10'&&!panel._v78Busy);
 assert.match(await frame.innerText(),/2027-03-10/);
 await frame.locator('[data-v80-scan=nutrition]').click();await frame.locator('[data-v78-take]').click();
 await page.waitForFunction(()=>panel._v78Draft.labelNutrition&&!panel._v78Busy);
 assert.equal(await page.evaluate(()=>panel._v78Draft.nutrition.values.protein),0);
 assert.equal(await page.evaluate(()=>panel._v78Draft.productName),'Wholegrain rice');
 assert.match(await frame.locator('.v111-nutrients').innerText(),/0/);
 assert.equal(await page.evaluate(()=>cameraStops),0);
 const photos=await page.evaluate(()=>calls.filter(row=>row.type.endsWith('/recognize_photo')));
 assert.deepEqual(photos.map(row=>row.mode),['date','nutrition']);
 assert.ok(photos.every(row=>row.image.startsWith('data:image/jpeg;base64,')));
 // Quantity and location controls inside the image feed the same reviewed save.
 await frame.locator('[data-v111-amount]').fill('750');
 await frame.locator('[data-v111-place]').selectOption('pantry');
 assert.equal(await dialog.locator('main [data-draft=quantity]').inputValue(),'750');
 assert.equal(await dialog.locator('main [data-draft=storageLocationId]').inputValue(),'pantry');
 await page.evaluate(()=>failSave=true);await frame.locator('[data-v111-apply]').click();
 await page.waitForFunction(()=>panel._v78Draft.scanPhase==='error'&&!panel._v78Busy);
 assert.equal(await frame.locator('[data-v111-amount]').isDisabled(),true);
 assert.match(await frame.innerText(),/Connection lost/);
 await frame.locator('[data-v111-apply]').click();
 await page.waitForFunction(()=>panel._v78Draft.scanApplied&&!panel._v78Busy);
 const saves=await page.evaluate(()=>calls.filter(row=>row.type.endsWith('/product_add')));
 assert.equal(saves.length,2);assert.deepEqual(saves[0],saves[1]);
 assert.equal(saves[0].quantity,'750');assert.equal(saves[0].lot_metadata.productName,'Wholegrain rice');assert.equal(saves[0].best_before,'2027-03-10');assert.equal(saves[0].nutrition.values.protein,0);
 assert.equal(await page.evaluate(()=>cameraStops),0,'Camera remains on even after Apply');
 // Clicking the image resumes capture; next products never inherit old labels.
 await frame.locator('video').click({position:{x:4,y:200}});
 await page.waitForFunction(()=>panel._v78Draft.scanPhase==='scanning');
 assert.equal(await page.evaluate(()=>panel._v78Submitted),null);
 assert.equal(await page.evaluate(()=>panel._v78Draft.bestBefore),'');
 await page.evaluate(()=>detectedBarcode='99999999');await frame.locator('[data-v80-scan=barcode]').click();
 await page.waitForFunction(()=>panel._v78Draft.scanPhase==='notfound'&&!panel._v78Busy);
 assert.match(await frame.innerText(),/Product not recognized/);
 assert.equal(await frame.locator('[data-v111-apply]').count(),0);
 assert.equal(await page.evaluate(()=>panel._v78Draft.productName),'');
 assert.deepEqual(await page.evaluate(()=>panel._v78Draft.nutrition.values),{});
 assert.equal(await page.evaluate(()=>cameraStarts),1);
 // An unknown barcode can be identified by AI using the same camera.
 await page.evaluate(()=>detectedBarcode='');await frame.locator('[data-v80-scan=product]').click();
 assert.equal(await frame.getAttribute('data-mode'),'product');
 await frame.locator('[data-v78-take]').click();
 await page.waitForFunction(()=>panel._v78Draft.productName==='Brown rice'&&!panel._v78Busy);
 assert.equal(await page.evaluate(()=>panel._v78Draft.barcode),'99999999');
 assert.equal(await dialog.locator('[data-v78-ingredient]').inputValue(),'k:rice');
 assert.equal(await page.evaluate(()=>cameraStops),0);
 // Last entries can be assigned manually; overlay follows the manual picker.
 await dialog.locator('[data-v78-ingredient]').selectOption('k:food-399');
 assert.match(await frame.innerText(),/Ingredient 399/);
 await dialog.locator('[data-v78-ingredient]').selectOption('k:rice');
 // A tap cancels a pending read: its late response must not populate the draft.
 await frame.locator('[data-v80-scan=date]').click();await page.evaluate(()=>delayPhoto=true);
 await frame.locator('[data-v78-take]').click();await frame.locator('.v111-spinner').waitFor();
 await frame.locator('video').click({position:{x:4,y:200}});
 await page.evaluate(()=>{delayPhoto=false;releasePhoto({product:{bestBefore:'2099-01-01'}});});
 await page.waitForTimeout(50);assert.equal(await page.evaluate(()=>panel._v78Draft.bestBefore),'');
 assert.equal(await page.evaluate(()=>panel._v78Draft.scanPhase),'scanning');
 assert.equal(await page.evaluate(()=>cameraStops),0);
 // Manual camera stop works, and missing browser barcode detection leaves a
 // live preview with keyboard/photo fallback rather than shutting it down.
 await frame.locator('[data-v111-power]').click();assert.equal(await page.evaluate(()=>cameraStops),1);
 await page.evaluate(()=>window.BarcodeDetector=undefined);await frame.locator('[data-v80-scan=barcode]').click();
 await page.waitForFunction(()=>!!panel._v78Stream&&!panel._v80CameraPending);
 assert.equal(await frame.locator('[data-v111-code-wrap]').isVisible(),true);
 await frame.locator('[data-draft=barcode]').fill('12345678');await frame.locator('[data-v78-lookup]').click();
 await page.waitForFunction(()=>panel._v78Draft.scanRecognized&&!panel._v78Busy);
 assert.equal(await page.evaluate(()=>cameraStops),1);
 // Every mode and result fit the camera on desktop and narrow phones.
 for(const lang of ['en','de','el']){
  await page.evaluate(lang=>{panel._hass.language=lang;panel._v78RenderCapture();},lang);
  for(const [width,height] of [[1280,900],[390,844],[360,740]]){
   await page.setViewportSize({width,height});
   assert.ok(await dialog.evaluate(el=>el.scrollWidth-el.clientWidth)<=1,lang+' '+width);
   const bounds=await frame.boundingBox();
   for(const button of await frame.locator('.v111-modes button,.v111-bottom button').all())if(await button.isVisible()){
    const box=await button.boundingBox();assert.ok(box.x>=bounds.x&&box.x+box.width<=bounds.x+bounds.width+1,'All scan buttons stay inside camera');
   }
   if(process.env.COOK4ME_SCANNER_SCREENSHOT&&lang==='el')await frame.screenshot({path:process.env.COOK4ME_SCANNER_SCREENSHOT+`-${width}.png`});
  }
 }
 await page.evaluate(()=>panel._v78Close(true));assert.equal(await page.evaluate(()=>cameraStops),2);
 // A pending permission request is stopped if it completes after the dialog closes.
 await page.evaluate(()=>{window.stopped=0;Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:()=>new Promise(resolve=>window.releaseCamera=resolve)}});void panel._v78Open('barcode');});
 await page.waitForFunction(()=>!!window.releaseCamera);await page.evaluate(()=>{panel._v78Close(true);releaseCamera({getTracks:()=>[{stop:()=>stopped++}]});});
 await page.waitForFunction(()=>stopped===1);
 // Late product lookup cannot overwrite a new capture session.
 await page.evaluate(async()=>{await panel._v78Open('manual');delayLookup=true;void panel._v78Lookup('11111111');});
 await page.waitForFunction(()=>!!window.releaseLookup);
 await page.evaluate(async()=>{const release=releaseLookup;panel._v78Close(true);await panel._v78Open('manual');release({barcode:'11111111',product:{productName:'Stale'}});});
 await page.waitForTimeout(50);assert.equal(await dialog.locator('[data-draft=productName]').inputValue(),'');
 await page.evaluate(()=>panel._v78Close(true));
 assert.deepEqual(errors,[]);
 console.log('v111 browser: persistent camera/video, barcode spinner/result, mode overlays, product-linked labels, complete multilingual picker, Apply and exact save retries, next-product isolation, stale reads, permission cleanup and three-language responsive layouts passed');
}finally{await browser.close();}
