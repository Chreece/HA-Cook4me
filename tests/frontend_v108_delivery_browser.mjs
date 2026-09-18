import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage({viewport:{width:390,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><style>body{margin:0;font-family:Arial;--primary-color:#009bbb;--primary-text-color:#eee;--primary-background-color:#111;--card-background-color:#1e2223;--secondary-background-color:#222;--secondary-text-color:#aaa;--divider-color:#444}</style><body></body>'}));
 await page.goto('http://cook4me.test/');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v108-bundle.js'});
 await page.evaluate(()=>{
  globalThis.customElements.define('cook4me-v108-test',class extends globalThis.customElements.get('cook4me-recipe-hub-panel-v108'){connectedCallback(){} disconnectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v108-test');window.calls=[];
  p._hass={language:'el',user:{id:'alice'},states:{},config:{country:'DE'},connection:{sendMessagePromise:async msg=>{
   const request=msg.request||msg;calls.push(structuredClone(request));
   if(request.type.endsWith('/recipe_detail'))return structuredClone(recipe);
   if(request.type.endsWith('/send_multi'))return await new Promise(resolve=>window.finishSend=resolve);
   return {};
  }}};
  p._entryId='one';p._entries=[{entry_id:'one',title:'Cook4Me',connected:true,profile:{diet:'vegetarian'}}];p._tab='book';
  p._v63FilterKey=p._prefKey();p._v63Filters={diet:'vegetarian',languages:[],ingredients:[],mealTypes:[]};
  p._loadOverview=async()=>{};p._renderTab=()=>{};p._renderRecipeDialog=()=>{};document.body.append(p);
  window.prepare=(language,variant)=>{
   for(const token of p._v63Jobs?.values()||[]){clearTimeout(token.removeTimer);token.card?.remove();}p._v63Jobs?.clear();p._process=null;p.shadowRoot.querySelectorAll('.rx-v59-op').forEach(n=>n.remove());
   p._hass.language=language;window.calls=[];window.finishSend=null;
   window.recipe={title:'An official recipe',language:'sl',displayVariantId:variant,searchVariantId:variant,recipeFunctionalId:variant,groupingFunctionalId:'source-group',ingredients:[{name:'Rice'}],steps:[],match:{safe:false}};
   window.sending=p._v66Send(recipe,'one');
  };
 });
 const p=page.locator('cook4me-v108-test');
 for(const language of ['el','de','en']){
  await page.evaluate(language=>prepare(language,'any-official-id-'+language),language);await page.waitForFunction(()=>!!window.finishSend);
  const job=p.locator('.rx-v59-op').last();assert.equal(await job.locator('.v93-cancel').count(),1);
  assert.ok((await job.innerText()).includes('90'));
  await page.evaluate(async()=>{finishSend({sentCount:0,queuedCount:0,acceptedCount:1,results:[{accepted:true,sent:false,queued:false,reason:'device_confirmation_unavailable'}]});await sending;});
  assert.equal(await job.evaluate(n=>n.classList.contains('bad')||n.classList.contains('indeterminate')),false);
  assert.equal(await job.locator('ha-icon').first().getAttribute('icon'),'mdi:clock-outline');
  assert.equal(await job.locator('.v93-cancel').count(),0);
  assert.equal(await page.evaluate(()=>panel._v63Jobs.size),0);assert.equal(await page.evaluate(()=>panel._process),null);
  assert.equal(await job.locator('.rx-v59-op-detail').innerText(),await page.evaluate(()=>panel._v108Text('unconfirmed')));
  assert.equal(await page.evaluate(()=>calls.filter(r=>r.type.endsWith('/send_multi')).length),1);
  for(const width of [390,1360]){
   await page.setViewportSize({width,height:900});assert.equal(await job.evaluate(n=>n.scrollWidth<=n.clientWidth+1),true);
   if(language==='el'&&process.env.COOK4ME_SCREENSHOT_DIR)await job.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+`/v108-unconfirmed-${width}.png`});
  }
 }
 // Actual confirmation remains success, and actual cloud rejection remains red.
 await page.evaluate(()=>prepare('en','another-id'));await page.waitForFunction(()=>!!window.finishSend);
 await page.evaluate(async()=>{finishSend({sentCount:1,queuedCount:0});await sending;});
 assert.equal(await p.locator('.rx-v59-op').last().locator('ha-icon').first().getAttribute('icon'),'mdi:check-circle-outline');
 await page.evaluate(()=>prepare('en','third-id'));await page.waitForFunction(()=>!!window.finishSend);
 await page.evaluate(async()=>{finishSend({sentCount:0,queuedCount:0,results:[{reason:'original_language_send_failed',error:'Cloud rejected'}]});await sending;});
 assert.equal(await p.locator('.rx-v59-op').last().evaluate(n=>n.classList.contains('bad')),true);
 // Cancelling the wait stays cancellable and does not send a second recipe.
 await page.evaluate(()=>prepare('el','cancel-id'));await page.waitForFunction(()=>!!window.finishSend);
 await p.locator('.rx-v59-op .v93-cancel').click();await page.evaluate(()=>sending);
 assert.equal(await page.evaluate(()=>calls.filter(r=>r.type.endsWith('/send_multi')).length),1);
 assert.equal(await page.evaluate(()=>calls.some(r=>r.type.endsWith('/job_cancel'))),true);
 assert.deepEqual(errors,[]);
 console.log('v108: generic recipe identities, 90-second waiting text, amber unconfirmed outcome, no duplicate send or lingering cancel/job, actual success/failure, cancellation, and el/de/en mobile/desktop layout passed');
}finally{await browser.close();}
