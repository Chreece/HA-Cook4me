import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu','--disable-software-rasterizer','--use-gl=disabled']});
try{
 const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><style>body{margin:0;font-family:Arial;--primary-color:#3d775d;--primary-text-color:#253b30;--primary-background-color:#f8faf8;--card-background-color:#fff;--secondary-background-color:#edf2ee;--secondary-text-color:#627468;--divider-color:#dce5df}</style><body></body>'}));
 await page.goto('http://cook4me.test/');
 await page.addScriptTag({path:fileURLToPath(new URL('../custom_components/cook4me/frontend/cook4me-panel-v81-bundle.js',import.meta.url))});
 await page.evaluate(()=>{
  const p=window.panel=document.createElement('cook4me-recipe-hub-panel-v81');window.calls=[];window.subscriptions=[];window.connectionEvents={};window.saved={};
  for(const method of ['_restorePreferences','_loadOverview','_loadBookState','_requestSection','_loadRecipeNutrition','_loadNutritionSettings','_loadFoodState','_loadInventoryState','_loadIngredientCatalog'])p[method]=async()=>{};
  const connection={subscribeMessage:async(callback,msg)=>{const r={callback,msg,removed:false};window.subscriptions.push(r);return()=>{r.removed=true;};},addEventListener:(type,cb)=>window.connectionEvents[type]=cb,removeEventListener:(type,cb)=>{if(window.connectionEvents[type]===cb)delete window.connectionEvents[type];}};
  p._hass={language:'en',user:{id:'alice'},states:{},config:{country:'DE'},connection};
  p._entryId='one';p._entries=['one','two'].map(id=>({entry_id:id,title:id==='one'?'Kitchen Cook4Me':'Second Cook4Me',connected:true,state:{phase:'idle'},recipes:[],profile:{diet:'vegetarian',houseIngredients:[],allergies:[],avoid:[],preferences:[],householdMembers:[]}}));p._tab='profile';
  p._ingredientCatalog=[{key:'rice',name:'Rice'}];p._ingredientCatalogLanguage='en';p._capabilities={ingredientCatalogLanguage:'en',deviceCatalogLanguage:'en'};p._inventoryLoadedEntry='one';p._nutritionSettings={};p._foodState={history:[],summary:{}};
  const state={storageLocations:[{id:'pantry',name:'Pantry',kind:'pantry'}],houseIngredients:[],aiEntityId:'',aiChoices:[]};p._v78AcceptState(state);
  p._api=async(type,payload)=>{
   window.calls.push({type,...structuredClone(payload)});
   if(type.endsWith('/scanner_state'))return state;
   if(type.endsWith('/device_settings')){
    const key=p._hass.user.id+':'+payload.entry_id;
    if(payload.settings)window.saved[key]=structuredClone(payload.settings);
    return {settings:window.saved[key]||{enabled:false,recipe:true,steps:true,state:true,connection:false,players:[],tts:'',ai:'',language:'',voice:''},choices:{players:[{id:'media_player.kitchen',name:'Kitchen speaker',announce:true}],tts:[{id:'tts.home',name:'Home voice',languages:['en','el','de'],defaultLanguage:'en',voices:{en:[{id:'warm',name:'Warm voice'}],el:[],de:[]}}],ai:[]}};
   }
   return {};
  };
  window.emit=(state,connected=true)=>{
   const sub=window.subscriptions.findLast(r=>r.msg.type.endsWith('/device_state_subscribe')&&!r.removed);
   sub.callback({entry_id:sub.msg.entry_id,accessible:true,connected,canAcceptRecipe:state.phase==='idle',loadedRecipe:null,state});
  };
  document.body.append(p);p._renderShell();p._renderTab();p._updateHeader();
 });
 const panel=page.locator('cook4me-recipe-hub-panel-v81');
 assert.equal(await panel.locator('[data-v78-open]').count(),1);
 assert.equal(await panel.locator('[data-v78-open]').innerText(),'Add product');
 await panel.locator('[data-v78-open]').click();
 assert.equal(await panel.locator('dialog.v78-capture [data-v80-scan]').count(),4);
 assert.equal(await panel.locator('dialog.v78-capture [data-draft=productName]').isVisible(),true);
 await panel.locator('[data-v78-close]').click();
 assert.equal(await panel.locator('#status .v81-cooker').getAttribute('data-phase'),'waiting','Do not animate cached state while connecting');
 await page.evaluate(()=>window.emit({phase:'warming',uiFirmware:'1.2.3',wifiFirmware:'4.5.6',remainingTime:90,recipeTitle:'Rice supper',currentInstruction:'Add 200 g rice'}));
 await panel.locator('#status .status').click();
 const info=panel.locator('[data-device-info]');await info.waitFor({state:'visible'});
 assert.equal(await info.locator('form,input,select,[data-setting]').count(),0,'Device info has no announcement controls');
 assert.ok((await info.innerText()).includes('1.2.3'));assert.ok((await info.innerText()).includes('1:30'));
 assert.equal(await page.evaluate(()=>window.calls.filter(r=>r.type.endsWith('/device_settings')).length),0,'Opening device info does not load announcement settings');
 for(const phase of ['warming','cooking','depressurization','keep_warm','ready','done','preparation','add_ingredient','paused','stopped','idle']){
  await page.evaluate(phase=>window.emit({phase,uiFirmware:'1.2.3',wifiFirmware:'4.5.6',recipeTitle:'Rice supper'}),phase);
  assert.equal(await info.locator('.v81-cooker').getAttribute('data-phase'),phase);
  assert.equal(await panel.locator('#status .v81-cooker').getAttribute('data-phase'),phase);
 }
 await page.evaluate(()=>window.emit({phase:'cooking',recipeTitle:'Rice supper',currentInstruction:'Cooking under pressure',remainingTime:540,uiFirmware:'1.2.3',wifiFirmware:'4.5.6'}));
 assert.ok(await info.locator('.v81-steam path').first().evaluate(el=>getComputedStyle(el).animationName!=='none'));
 await page.evaluate(()=>{window.oldArt=window.panel._v81HeaderArt;window.panel._entry().state={phase:'idle'};window.panel._updateHeader();});
 assert.equal(await info.locator('.v81-cooker').getAttribute('data-phase'),'cooking','Late overview cannot overwrite live telemetry');
 assert.equal(await page.evaluate(()=>window.oldArt===window.panel._v81HeaderArt),true,'Ordinary HA updates preserve animation');
 await page.emulateMedia({reducedMotion:'reduce'});
 assert.equal(await info.locator('.v81-steam path').first().evaluate(el=>getComputedStyle(el).animationName),'none');
 await page.emulateMedia({reducedMotion:'no-preference'});
 if(process.env.COOK4ME_SCREENSHOT_DIR)await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+'/v81-device-desktop.png'});
 await page.evaluate(()=>window.emit({phase:'cooking',recipeTitle:'Stale recipe'},false));
 assert.equal(await info.locator('.v81-cooker').getAttribute('data-phase'),'offline');
 assert.equal(await info.locator('.v81-steam path').first().evaluate(el=>getComputedStyle(el).animationName),'none');
 assert.ok(!(await info.innerText()).includes('Stale recipe'));
 await page.evaluate(()=>window.emit({phase:'unexpected_new_status',active:true}));
 assert.equal(await info.locator('.v81-cooker').getAttribute('data-phase'),'unknown');
 await page.evaluate(()=>window.emit({phase:'idle',updating:true}));
 assert.equal(await info.locator('.v81-cooker').getAttribute('data-phase'),'updating');
 await page.evaluate(()=>window.connectionEvents.disconnected());
 assert.equal(await info.locator('.v81-cooker').getAttribute('data-phase'),'unavailable');
 await page.evaluate(()=>window.emit({phase:'idle',uiFirmware:'1.2.3',wifiFirmware:'4.5.6'}));
 for(const [language,label] of [['en','Device information'],['de','Geräteinformationen'],['el','Πληροφορίες συσκευής']]){
  await panel.locator('[data-v81-close]').click();
  await page.evaluate(language=>{window.panel._hass.language=language;window.panel._langCode=()=>language;window.panel._updateHeader();},language);
  await page.setViewportSize({width:360,height:740});await panel.locator('#status .status').focus();await page.keyboard.press('Enter');
  assert.equal(await info.getAttribute('aria-label'),label);
  assert.ok(await info.evaluate(el=>el.scrollWidth<=el.clientWidth+1));
 }
 if(process.env.COOK4ME_SCREENSHOT_DIR)await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+'/v81-device-mobile.png'});
 await page.keyboard.press('Escape');assert.equal(await info.count(),0);
 await page.evaluate(()=>{window.panel._hass.language='en';window.panel._langCode=()=>'en';window.panel._renderTab();});
 await page.setViewportSize({width:1280,height:900});
 await panel.locator('[data-v78-pane=integration]').click();
 assert.ok((await panel.locator('[data-v78-section=integration]').innerText()).includes('Device options'));
 await panel.locator('[data-v78-device]').click();const announcements=panel.locator('[data-announcements]');await announcements.waitFor();
 assert.equal(await announcements.locator('h2').innerText(),'Announcements');assert.equal(await announcements.locator('dl,[data-device-info]').count(),0);
 await announcements.locator('[data-setting=enabled]').check();await announcements.locator('summary').click();await announcements.locator('[data-player]').check();
 await announcements.locator('[data-setting=tts]').selectOption('tts.home');await announcements.locator('[data-setting=voice]').selectOption('warm');await announcements.locator('[data-v72-save]').click();
 await page.waitForFunction(()=>window.saved['alice:one']?.voice==='warm');
 await announcements.locator('[data-v72-test]').click();await page.waitForFunction(()=>window.calls.some(r=>r.type.endsWith('/announcement_test')));
 if(process.env.COOK4ME_SCREENSHOT_DIR)await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+'/v81-announcements.png'});
 // User and device switches close private settings and discard late telemetry.
 await page.evaluate(()=>{window.oldSubscription=window.subscriptions.findLast(r=>r.msg.type.endsWith('/device_state_subscribe'));window.panel._hass.user={id:'bob'};window.panel._updateHeader();});
 assert.equal(await announcements.count(),0);assert.equal(await page.evaluate(()=>window.oldSubscription.removed),true);
 await panel.locator('[data-v78-device]').click();await announcements.waitFor();assert.equal(await announcements.locator('[data-setting=enabled]').isChecked(),false);
 await page.evaluate(()=>{window.panel._entryId='two';window.panel._updateHeader();window.oldSubscription.callback({entry_id:'one',connected:true,state:{phase:'cooking',recipeTitle:'Wrong account'}});});
 assert.equal(await announcements.count(),0);assert.ok(!(await panel.locator('#status').innerText()).includes('Wrong account'));
 await page.evaluate(()=>window.emit({phase:'ready'}));await panel.locator('#status .status').click();await info.waitFor();
 await page.evaluate(()=>{window.panel._entryId='one';window.panel._updateHeader();});assert.equal(await info.count(),0);
 // HA device page deep link opens info, never the announcement form.
 await page.evaluate(()=>{history.replaceState({},'', '/?device=two');window.panel._v72DeepLink=false;window.panel._updateHeader();});await info.waitFor();assert.equal(await info.locator('h2').innerText(),'Second Cook4Me');
 await page.evaluate(()=>window.panel.remove());assert.ok(await page.evaluate(()=>window.subscriptions.every(r=>r.removed)));assert.equal(await page.evaluate(()=>Boolean(window.connectionEvents.disconnected)),false);
 assert.deepEqual(errors,[]);console.log('v81: merged entry, live animated device info, announcements, permissions context, accessibility and mobile layouts passed');
}finally{await browser.close();}
