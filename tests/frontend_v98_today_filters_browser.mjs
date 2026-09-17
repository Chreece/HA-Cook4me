import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
let directory,fixturePath=process.env.COOK4ME_TODAY_FIXTURE;
if(!fixturePath){
 directory=mkdtempSync(join(tmpdir(),'cook4me-v98-'));fixturePath=join(directory,'today.json');
 const result=spawnSync('python',['-B','-m','unittest','discover','-s','tests','-p','test_today_state_v98.py'],{cwd:root,encoding:'utf8',timeout:240000,env:{...process.env,COOK4ME_TODAY_FIXTURE:fixturePath}});
 assert.equal(result.status,0,result.stdout+result.stderr);
}
const fixture=JSON.parse(readFileSync(fixturePath,'utf8'));
if(directory)rmSync(directory,{recursive:true});
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];
 page.on('pageerror',error=>{errors.push(error.message);console.error(error.stack);});
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><body style="margin:0;font:16px Arial;--primary-color:#397b58;--card-background-color:#fff;--primary-background-color:#f5f7f5;--primary-text-color:#183526;--secondary-text-color:#596f63;--divider-color:#d7dfd9;--secondary-background-color:#edf2ee"></body>'}));
 await page.goto('http://cook4me.test/');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v98-bundle.js'});
 await page.evaluate(fixture=>{
  window.fixture=fixture;window.requests=[];window.planIndex=0;
  globalThis.customElements.define('cook4me-v98-test',class extends globalThis.customElements.get('cook4me-recipe-hub-panel-v98'){connectedCallback(){}});
  window.makePanel=(user='alice',entry='one',restore=false)=>{
   const p=document.createElement('cook4me-v98-test');
   p._hass={language:'el',user:{id:user},states:{},config:{country:'DE',time_zone:'Europe/Berlin'},connection:{
    sendMessagePromise:async envelope=>{
     const request=envelope.request||envelope;requests.push(structuredClone(request));
     if(request.type.endsWith('/today_suggest')){
      if(window.delayToday)return new Promise(resolve=>window.finishToday=resolve);
      return structuredClone(fixture.plans[planIndex++%fixture.plans.length]);
     }
     if(request.type.endsWith('/ui_seed'))return {perEntry:{one:{todayResults:fixture.saved.items,todayMeta:fixture.saved}}};
     if(request.type.endsWith('/bootstrap'))return {entries:p._entries};
     return {};
    },subscribeMessage:async()=>()=>{},addEventListener(){},removeEventListener(){}}};
   for(const method of ['_restorePreferences','_loadOverview','_requestSection','_loadRecipeNutrition','_loadIngredientCatalog','_loadTodayOptions'])p[method]=async()=>{};
   p._v84SchedulePricePoll=()=>{};p._v86QueuePreview=()=>{};p._v66PreferLanguages=async rows=>rows;
   p._entryId=entry;p._entries=[{entry_id:entry,title:'Kitchen Cook4Me',connected:true,state:{phase:'idle'},profile:{diet:'vegetarian',houseIngredients:[]}}];p._tab='today';
   p._v54CacheUser=user;
   if(restore)p._hydrateUiSnapshot(user);
   else{
    p._v63FilterKey=p._prefKey();p._v63Filters={...fixture.filters,ingredients:[],onlyHome:false,avoidRecentDays:7,maxMissing:'',nutritionGoal:'balanced',maxCost:'',excludedIngredients:[],excludedTerms:[]};
    p._cachePreferences();
   }
   p._renderShell();document.body.append(p);p._renderTab();return p;
  };
  window.panel=makePanel();
 },fixture);
 const panel=page.locator('cook4me-v98-test');
 await panel.locator('#todaySuggest').click();
 await page.waitForFunction(()=>window.planIndex===1&&!panel._todayBusy);
 const count=fixture.plans[0].items.length;
 assert.equal(await panel.locator('#todayGrid [data-v66-ref]').count(),count);
 assert.equal(await panel.locator('.v93-active-filters [data-filter]').count(),1);
 assert.equal(await panel.locator('[data-filter=diet]').innerText(),'1');
 assert.equal(await panel.locator('.v93-filter-toggle').innerText(),'');
 assert.equal(await panel.locator('.v93-filter-drawer').isVisible(),false);
 await panel.locator('.v93-filter-toggle').click();
 assert.equal(await panel.locator('.v93-filter-drawer [data-filter]').count(),7);
 const positions=await panel.locator('.v93-filters').evaluate(bar=>{
  const rect=selector=>bar.querySelector(selector).getBoundingClientRect();
  return {drawerRight:rect('.v93-filter-drawer').right,toggleLeft:rect('.v93-filter-toggle').left,groupRight:rect('.v98-filter-group').right,activeLeft:rect('.v93-active-filters').left};
 });
 assert.ok(positions.drawerRight<=positions.toggleLeft&&positions.groupRight<=positions.activeLeft,'defaults expand to the left of Filter, active controls stay to its right');
 // Applying real filter dialogs moves a button between the two groups.
 await panel.locator('[data-filter=diet]').click();
 await panel.locator('[data-filter-dialog=diet] [data-field=diet]').selectOption('omnivore');
 await panel.locator('[data-filter-dialog=diet] [data-apply]').click();
 assert.equal(await panel.locator('.v93-active-filters [data-filter]').count(),0);
 assert.equal(await panel.locator('.v93-filter-drawer [data-filter=diet]').isVisible(),true);
 await panel.locator('[data-filter=diet]').click();
 await panel.locator('[data-filter-dialog=diet] [data-field=diet]').selectOption('vegetarian');
 await panel.locator('[data-filter-dialog=diet] [data-apply]').click();
 assert.equal(await panel.locator('.v93-active-filters [data-filter=diet]').innerText(),'1');
 // Fast navigation must flush pending state. Recreate the element as HA does.
 const identities=await page.evaluate(()=>panel._todayResults.map(row=>row.displayFamilyId));
 await page.evaluate(()=>{panel._v59CancelIdlePersist();panel._scheduleSnapshotPersist();panel.remove();window.panel=makePanel('alice','one',true);});
 assert.deepEqual(await page.evaluate(()=>panel._todayResults.map(row=>row.displayFamilyId)),identities);
 assert.equal(await panel.locator('#todayGrid [data-v66-ref]').count(),count,'diet checks survive browser persistence');
 assert.equal(await page.evaluate(()=>requests.filter(r=>r.type.endsWith('/today_suggest')).length),1,'returning does not generate another plan');
 // Exclusion signatures and substitution evidence also survive both compactions.
 const evidence=await page.evaluate(()=>{
  const match={score:1,diet:'vegetarian',dietCheckVersion:76,dietRulesSignature:panel._v83RulesSignature(),safe:false,eligibleWithSubstitutions:true,requiresSubstitutions:true,substitutions:[{ingredientIndex:0,original:'Stock',replacement:{key:'stock',name:'Vegetable stock'}}]};
  const compact=panel._v59CompactMatch(panel._v59CompactMatch(match));return {match,compact,allowed:panel._v76Allowed({match:compact})};
 });
 assert.deepEqual(evidence.compact,evidence.match);assert.equal(evidence.allowed,true);
 // An old browser snapshot can recover its checked saved plan without regeneration.
 await page.evaluate(async()=>{
  panel._todayResults=panel._todayResults.map(row=>({...row,match:{score:1}}));panel._v53BootstrapDone=true;
  await panel._loadBootstrap();
 });
 assert.equal(await panel.locator('#todayGrid [data-v66-ref]').count(),fixture.saved.items.length);
 assert.equal(await page.evaluate(()=>requests.filter(r=>r.type.endsWith('/today_suggest')).length),1);
 // Positive counts describe selected options, including an explicitly set zero limit.
 await page.evaluate(()=>{Object.assign(panel._filters(),{ingredients:['i:1','i:2','i:3'],languages:['de','en'],mealTypes:['main','soup'],maxMissing:0,calorieTarget:0,maxCost:0});panel._renderTab();});
 for(const [key,badge] of [['ingredients','3'],['languages','2'],['meals','2'],['home','1'],['nutrition','1'],['cost','1']]){
  assert.equal(await panel.locator(`.v93-active-filters [data-filter=${key}]`).innerText(),badge);
 }
 assert.equal(await panel.locator('.v93-active-filters [data-filter]').evaluateAll(nodes=>nodes.every(node=>/^[1-9]\d*$/.test(node.textContent)&&node.title&&node.getAttribute('aria-label'))),true);
 await panel.locator('.v93-filter-toggle').click();
 await panel.locator('.v93-filter-drawer button').first().focus();await page.keyboard.press('Escape');
 assert.equal(await panel.locator('.v93-filter-drawer').isVisible(),false);
 for(const section of ['official','week','today']){
  await page.evaluate(section=>{panel._tab=section;panel._v67WeekLoaded=`${panel._prefKey()}:${panel._v67Today()}`;panel._renderTab();},section);
  assert.equal(await panel.locator('.v98-filter-group').count(),1,section);
  assert.equal(await panel.locator('.v93-menu-controls '+({official:'#searchBtn',week:'#generateWeek',today:'#todaySuggest'}[section])).count(),1);
 }
 for(const language of ['en','de','el']){
  for(const width of [360,390,1600]){
   await page.setViewportSize({width,height:900});
   await page.evaluate(language=>{panel._hass.language=language;panel._v93FiltersOpen=true;panel._renderTab();},language);
   assert.equal(await panel.locator('.v93-controls').evaluate(bar=>bar.scrollWidth<=bar.clientWidth+1),true,`${language} ${width}`);
  }
 }
 if(process.env.COOK4ME_SCREENSHOT_DIR){
  await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+'/v98-desktop.png'});
  await page.setViewportSize({width:390,height:900});await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+'/v98-mobile.png'});
 }
 // A cancelled refresh keeps the saved results, even if its response arrives late.
 await page.evaluate(()=>{window.before=panel._todayResults;window.delayToday=true;window.finishToday=null;});
 await panel.locator('#todaySuggest').click();await page.waitForFunction(()=>window.finishToday!==null);
 await panel.locator('.v93-cancel').click();await page.waitForFunction(()=>!panel._todayBusy);
 await page.evaluate(()=>finishToday({items:[]}));
 assert.equal(await page.evaluate(()=>panel._todayResults===before),true);
 // The browser snapshot is scoped to its owner and device.
 await page.evaluate(()=>{panel.remove();window.panel=makePanel('bob','two',true);});
 assert.equal(await panel.locator('#todayGrid [data-v66-ref]').count(),0);
 assert.deepEqual(errors,[]);
 console.log('v98: real Today results survive navigation; icon counts, left expansion, filter migration, stale-cache recovery, cancellation and mobile layouts passed');
}finally{await browser.close();}
