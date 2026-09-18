import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage({viewport:{width:1600,height:950}}),errors=[];page.on('pageerror',e=>{errors.push(e.message);console.error(e.stack);});
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><body style="margin:20px;font:16px Arial;background:#111;color:#eee"></body>'}));
 await page.goto('http://cook4me.test/');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v93-bundle.js'});
 await page.evaluate(()=>{
  globalThis.customElements.define('cook4me-v93-test',class extends globalThis.customElements.get('cook4me-recipe-hub-panel-v93'){connectedCallback(){} disconnectedCallback(){clearInterval(this._v93ClockTimer);}});
  const p=window.panel=document.createElement('cook4me-v93-test');p._hass={language:'el',user:{id:'alice'},config:{time_zone:'Europe/Berlin',country:'DE'},connection:{sendMessagePromise:async()=>({})}};p._entryId='one';p._tab='today';
  p._uiIngredientLanguage=()=>p._hass.language;p._langCode=()=>p._hass.language;p._prefKey=()=>p._entryId;p._v84SchedulePricePoll=()=>{};p._v86QueuePreview=()=>{};p._v66PreferLanguages=async rows=>rows;
  p._v63FilterKey='one';p._v63Filters={diet:'omnivore',dietProfile:'manual',mealTypes:['breakfast','starter','salad','soup','main','side','dessert','snack'],languages:p._languageRows().map(r=>r.code),ingredients:[],onlyHome:false,preferExpiring:true,avoidRecentDays:7,maxMissing:'',nutritionGoal:'balanced',maxCost:''};
  p._entries=[{entry_id:'one',profile:{diet:'omnivore',dietProfiles:{household:{name:'Household',diet:'omnivore'},members:[{id:'anna',name:'Anna',icon:'face-woman',diet:'vegan'}]}}}];
  p._todayResults=[{id:'b',title:'Breakfast',todayMealType:'breakfast'},{id:'l',title:'Lunch',todayMealType:'lunch'},{id:'d',title:'Dinner',todayMealType:'dinner'},{id:'s',title:'Snack',todayMealType:'snack'},{id:'m',title:'Main',todayMealType:'main'}];
  p._v93Now=()=>new Date('2026-09-16T11:05:00Z');document.body.append(p);if(!p.shadowRoot)p.attachShadow({mode:'open'});
  p.shadowRoot.innerHTML='<style>:host{display:block;--primary-color:#00a4ca;--card-background-color:#202525;--primary-text-color:#eee;--secondary-text-color:#bbb;--divider-color:#444;--secondary-background-color:#303535}.toolbar{display:flex}.card{padding:16px;border:1px solid #444;border-radius:18px}.btn{border:1px solid #555;border-radius:10px;background:#272c2c;color:inherit;cursor:pointer;padding:12px}#todayGrid{display:grid;grid-template-columns:repeat(5,1fr);gap:16px}article{background:#263039;padding:16px}ha-icon{display:inline-block;width:24px;height:24px}</style><div id="content"></div>';
  p._renderToday(p.shadowRoot.querySelector('#content'));
 });
 const panel=page.locator('cook4me-v93-test');
 assert.equal(await panel.locator('.v93-active-filters [data-filter]').count(),0,'default filters do not crowd the bar');
 assert.equal(await panel.locator('.v93-filter-drawer [data-filter]').count(),8);
 assert.equal(await panel.locator('.v93-filter-drawer').isVisible(),false);
 await panel.locator('.v93-filter-toggle').click();assert.equal(await panel.locator('.v93-filter-drawer').isVisible(),true);
 await panel.locator('.v93-filter-drawer button').first().focus();await page.keyboard.press('Escape');
 assert.equal(await panel.locator('.v93-filter-drawer').isVisible(),false);
 assert.match(await panel.locator('[data-v93-date]').innerText(),/16.*Σεπτεμβρίου.*2026/);
 assert.match(await panel.locator('[data-v93-clock]').innerText(),/(13|01):05.*Μεσημεριανό/s);
 assert.equal(await panel.locator('.v93-other-meal').count(),3);
 // Actual card bindings remain enabled when a card is dimmed.
 assert.equal(await panel.locator('.v93-other-meal [data-v66-ref]').count(),3);
 assert.equal(await panel.locator('.v93-other-meal [aria-disabled=true]').count(),0);
 await page.evaluate(()=>{
  Object.assign(panel._filters(),{dietProfile:'member:anna',diet:'vegan',ingredients:['i:1','i:2','i:3'],languages:['de','en'],mealTypes:['breakfast','main']});
  panel._renderToday(panel.shadowRoot.querySelector('#content'));
 });
 assert.equal(await panel.locator('.v93-active-filters [data-filter]').count(),5);
 assert.equal(await panel.locator('.v93-active-filters [data-filter=ingredients]').innerText(),'3');
 assert.equal(await panel.locator('.v93-active-filters [data-filter=languages]').innerText(),'2');
 assert.equal(await panel.locator('.v93-active-filters [data-filter=dietProfile] ha-icon').getAttribute('icon'),'mdi:face-woman');
 assert.match(await panel.locator('.v93-active-filters [data-filter=dietProfile]').innerText(),/Anna/);
 const menu=await panel.locator('.v93-menu-controls').boundingBox(),filter=await panel.locator('.v93-filters').boundingBox();assert.ok(menu.x<filter.x,'menu controls stay on the left');
 await page.evaluate(()=>{panel._v93Now=()=>new Date('2026-09-16T17:10:00Z');panel._v93UpdateTodayClock();});
 assert.match(await panel.locator('[data-v93-clock]').innerText(),/(19|07):10.*Βραδινό/s);
 await page.evaluate(()=>{panel._hass.language='de';panel._v93UpdateTodayClock();});
 assert.match(await panel.locator('[data-v93-clock]').innerText(),/Abendessen/);
 await page.evaluate(()=>{panel._hass.language='en';panel._hass.config.time_zone='Pacific/Auckland';panel._v93Now=()=>new Date('2026-09-16T13:10:00Z');panel._v93UpdateTodayClock();});
 assert.equal(await panel.locator('[data-v93-date]').getAttribute('datetime'),'2026-09-17');
 assert.equal(await panel.locator('[data-v93-clock]').getAttribute('data-period'),'lateSnack');
 assert.deepEqual(await page.evaluate(()=>[0,5,10,12,15,18,22,23].map(hour=>panel._v93Daypart(hour))),['lateSnack','breakfast','morningSnack','lunch','afternoonSnack','dinner','lateSnack','lateSnack']);
 // Exercise the real Today request owner and API layers, including cancellation.
 await page.evaluate(()=>{
  Object.assign(panel._filters(),{dietProfile:'manual',diet:'omnivore',languages:['en'],mealTypes:['main']});
  panel._hass.language='en';window.requests=[];window.finish=null;window.before=panel._todayResults;
  panel._hass.connection.sendMessagePromise=msg=>{requests.push(msg);if(msg.type==='cook4me/v36/job_cancel')return Promise.resolve({cancelled:true});return new Promise(resolve=>finish=resolve);};
  panel._renderTab=()=>panel._renderToday(panel.shadowRoot.querySelector('#content'));
  window.todayDone=panel._suggestTodayV34(panel.shadowRoot.querySelector('#content'));
 });
 await page.waitForFunction(()=>window.finish!==null);
 assert.equal(await panel.locator('.v93-cancel').count(),1);
 await panel.locator('.v93-cancel').click();await page.evaluate(()=>todayDone);
 assert.equal(await page.evaluate(()=>panel._todayBusy),false);
 assert.equal(await page.evaluate(()=>panel._todayResults===before),true);
 assert.match(await panel.locator('.rx-v59-op-detail').last().innerText(),/Cancelled/);
 assert.equal(await panel.locator('.rx-v59-op.bad').count(),0);
 assert.equal(await panel.locator('#todaySuggest').isDisabled(),false);
 assert.equal(await page.evaluate(()=>requests[0].request.type),'cook4me/v30/today_suggest');
 assert.equal(await page.evaluate(()=>Object.hasOwn(requests[0].request,'__cook4meJobId')),false);
 assert.equal(await page.evaluate(()=>requests.filter(r=>r.type==='cook4me/v36/job_cancel').length),1);
 await page.evaluate(()=>finish({items:[{id:'late',title:'Late result'}]}));
 assert.equal(await page.evaluate(()=>panel._todayResults===before),true,'late result cannot replace current recipes');
 // Cancellation addresses its own job even while another job is current.
 await page.evaluate(()=>{window.a=panel._processStart('A');window.b=panel._processStart('B');});
 await panel.locator('.v93-cancel[aria-label="Cancel: A"]').click();
 assert.equal(await page.evaluate(()=>panel._process===b&&!b.cancelled),true);
 await page.evaluate(()=>panel._processEnd(b));
 // Cancellation reaches each terminal transport used by search, detail,
 // catalogs, manual price refresh, AI and weekly generation.
 for(const type of ['cook4me/v31/official_search','cook4me/v31/recipe_detail','cook4me/v31/ingredient_catalog','cook4me/v34/recipe_cost_refresh','cook4me/v22/ai_create','cook4me/v20/week_generate']){
  await page.evaluate(type=>{
   window.transportJob=panel._processStart('Transport');window.transportRequest=null;
   panel._hass.connection.sendMessagePromise=msg=>{if(msg.type==='cook4me/v36/job_cancel')return Promise.resolve({cancelled:true});transportRequest=msg;return new Promise(()=>{});};
   window.transportDone=panel._api(type,{entry_id:'one'}).then(()=>({resolved:true}),error=>({code:error.code}));
  },type);
  await page.waitForFunction(()=>window.transportRequest!==null);
  assert.equal(await page.evaluate(()=>transportRequest.type),'cook4me/v36/job_run',type);
  assert.equal(await page.evaluate(()=>transportRequest.job_id===transportJob.id),true,type);
  await panel.locator('.v93-cancel[aria-label="Cancel: Transport"]').click();
  assert.equal(await page.evaluate(async()=>(await transportDone).code),'job_cancelled',type);
 }
 // Real Search and Week rendering use the same left/right toolbar layout.
 for(const section of ['official','week']){
  await page.evaluate(section=>{
   panel._tab=section;panel._hass.connection.sendMessagePromise=async()=>({});panel._v67WeekLoaded=`${panel._prefKey()}:${panel._v67Today()}`;
   panel[section==='official'?'_renderOfficial':'_renderWeek'](panel.shadowRoot.querySelector('#content'));
  },section);
  assert.equal(await panel.locator('.v93-filter-toggle').count(),1,section);
  assert.equal(await panel.locator('.v93-menu-controls '+(section==='official'?'#searchBtn':'#generateWeek')).count(),1,section);
 }
 // Narrow viewports do not overflow with active filters or an open drawer.
 await page.setViewportSize({width:390,height:850});
 await page.evaluate(()=>{panel._tab='today';panel._hass.language='el';panel._hass.config.time_zone='Europe/Berlin';panel._v93Now=()=>new Date('2026-09-16T11:05:00Z');panel._renderToday(panel.shadowRoot.querySelector('#content'));});
 await panel.locator('.v93-filter-toggle').click();
 assert.equal(await page.evaluate(()=>{const bar=panel.shadowRoot.querySelector('.v93-controls');return bar.scrollWidth<=bar.clientWidth+1;}),true);
 await page.screenshot({path:'/workspace/scratch/cb8275dab6b5/v93-mobile.png'});
 await page.setViewportSize({width:1600,height:950});
 await panel.locator('.v93-filter-toggle').click();
 await page.screenshot({path:'/workspace/scratch/cb8275dab6b5/v93-desktop.png'});
 assert.deepEqual(errors,[]);console.log('v93: cancellation, late results, filters, all three toolbars, localized clock, dayparts and mobile layout passed');
}finally{await browser.close();}
