import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const version=process.env.COOK4ME_TEST_PANEL_VERSION||'115';
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
 const restart=frame.locator('[data-v113-restart]'),observations=[];
 // Mock the provider below the real response adapter, so remembered links are exercised.
 await page.evaluate(()=>{
  const original=panel._api;
  let owner=Object.getPrototypeOf(panel);
  while(owner&&!Object.hasOwn(owner,'_api'))owner=Object.getPrototypeOf(owner);
  let provider=Object.getPrototypeOf(owner);
  while(provider&&!Object.hasOwn(provider,'_api'))provider=Object.getPrototypeOf(provider);
  provider._api=async(type,payload)=>payload.barcode==='87654321'&&type.endsWith('/barcode_lookup')?{product:{found:false},mapping:{productName:'Saved product',quantity:500,unit:'g',ingredient:null,ingredientLinks:[{key:'milk',name:'Milk'}]},suggestions:[]}:original(type,payload);
  delete panel._api;
 });
 await page.evaluate(()=>panel._v78Lookup('12345678'));
 await frame.locator('[data-v111-place]').selectOption('fridge');
 observations.push({case:'Storage summary follows the inline selection',pass:await frame.locator('[data-v112-details]>span').last().innerText()==='Main fridge'});
 await restart.click();
 await page.evaluate(()=>panel._v78Lookup('87654321'));
 observations.push({case:'Surviving saved links restore a usable primary ingredient',pass:await page.evaluate(()=>panel._v78Draft.ingredient?.key==='milk')});
 await restart.click();
 await frame.locator('[data-v111-power]').click();
 await page.evaluate(()=>{navigator.mediaDevices.getUserMedia=()=>new Promise((resolve,reject)=>window.rejectCamera=reject);void panel._v78Camera();});
 await page.waitForFunction(()=>panel._v80CameraPending&&window.rejectCamera);
 await restart.click();
 await page.evaluate(()=>rejectCamera(new Error('Permission denied')));
 await page.waitForFunction(()=>!panel._v80CameraPending);
 observations.push({case:'Camera errors after Restart belong to the current draft',pass:await page.evaluate(()=>panel._v78Draft.scanPhase==='error'&&panel._v78Draft.scanNote.includes('Permission denied'))});
 await page.evaluate(()=>panel._v78Close(true));
 assert.deepEqual(errors,[]);assert.deepEqual(observations.filter(row=>!row.pass),[]);
 console.log('v115 browser: immediate storage summary, surviving catalogue mappings, camera permission failure after Restart passed');
}finally{await browser.close();}
