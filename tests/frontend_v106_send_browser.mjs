import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
const root=fileURLToPath(new URL('..',import.meta.url));
const fixture=JSON.parse(execFileSync(process.env.PYTHON||'python3',['tests/build_cross_language_fixture_v106.py'],{cwd:root,maxBuffer:5_000_000}));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage(),browserErrors=[];page.on('pageerror',e=>browserErrors.push(e.message));
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><body></body>'}));
 await page.goto('http://cook4me.test/');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v106-bundle.js'});
 await page.evaluate(fixture=>{
  window.fixture=fixture;window.calls=[];window.errors=[];window.messages=[];window.finished=0;
  globalThis.customElements.define('cook4me-v106-test',class extends globalThis.customElements.get('cook4me-recipe-hub-panel-v106'){connectedCallback(){} disconnectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v106-test');
  p._entryId='one';p._hass={language:'el',user:{id:'alice'},config:{country:'DE'},states:{},connection:{sendMessagePromise:async msg=>{
   calls.push(structuredClone(msg));
   if(msg.type.endsWith('/recipe_detail'))return window.detail?await window.detail(msg):structuredClone(window.recipe);
   if(msg.type.endsWith('/send_multi'))return window.outcome||{sentCount:1,queuedCount:0,results:[{sent:true}]};
   return {};
  }}};
  p._entries=[{entry_id:'one',title:'Cook4Me',connected:true,profile:{diet:'omnivore'}},{entry_id:'two',title:'Other',connected:true,profile:{diet:'omnivore'}}];p._tab='today';
  p._v63FilterKey=p._prefKey();p._v63Filters={diet:'omnivore',languages:[],mealTypes:[],ingredients:[]};
  p._processStart=()=>1;p._processEnd=()=>{window.finished++;};p._v59FailProcess=(_job,error)=>errors.push(error);
  p._loadOverview=async()=>{};p._message=text=>messages.push(text);p._renderTab=()=>{};p._renderRecipeDialog=()=>{};
  document.body.append(p);
  window.prepare=index=>{
   window.calls=[];window.errors=[];window.messages=[];window.outcome=null;window.detail=null;
   window.recipe={...structuredClone(fixture[index]),match:{safe:true,diet:'omnivore'}};
   const body=p._v67Dom(p._v66Body(recipe,false,{sections:new Set(),device:'one'}));
   p.shadowRoot.replaceChildren(body);p._v66BindRecipe(body,recipe,false);
  };
 },fixture);
 for(let index=0;index<fixture.length;index++){
  await page.evaluate(index=>prepare(index),index);
  const original=await page.evaluate(()=>JSON.stringify(recipe));
  const before=await page.evaluate(()=>finished);
  const button=page.locator('cook4me-v106-test [data-v66-action="send"]');assert.equal(await button.isEnabled(),true);
  await button.click();await page.waitForFunction(before=>finished>before,before);
  const result=await page.evaluate(()=>({calls,errors,messages,recipe:JSON.stringify(recipe)}));
  assert.deepEqual(result.errors,[]);assert.equal(result.recipe,original);
  const sent=result.calls.find(row=>row.type.endsWith('/send_multi'));
  assert.equal(sent.recipe.sendVariantId,fixture[index].displayVariantId);
  assert.equal(sent.recipe.sendOriginalLanguage,true);
  assert.equal(sent.recipe.groupingFunctionalId,fixture[index].groupingFunctionalId);
  assert.deepEqual(sent.recipe.ingredients,fixture[index].ingredients);
  assert.deepEqual(sent.recipe.yield,fixture[index].yield);
  assert.equal(sent.recipe.sendFilters.diet,'omnivore');
  assert.ok(result.messages.at(-1).includes('φόρτωσε'));
 }
 // An existing target-language mapping remains preferred and retains normal queueing.
 const mapped=await page.evaluate(async()=>{
  prepare(0);window.detail=async()=>({...structuredClone(recipe),sendVariantId:'official-de'});
  window.outcome={sentCount:0,queuedCount:1};await panel._v66Send(recipe,'two');
  return {calls,errors,messages};
 });
 assert.deepEqual(mapped.errors,[]);const send=mapped.calls.find(r=>r.type.endsWith('/send_multi'));
 assert.equal(send.entry_id,'two');assert.equal(send.recipe.sendVariantId,'official-de');assert.equal(send.recipe.sendOriginalLanguage,undefined);
 // A cloud acknowledgement without appliance confirmation must remain an error in each UI language.
 for(const language of ['el','de','en']){
  const result=await page.evaluate(async language=>{
   prepare(0);panel._hass.language=language;window.outcome={sentCount:0,queuedCount:0,results:[{reason:'original_language_not_loaded'}]};
   await panel._v66Send(recipe,'one');return {errors,messages,expected:panel._v106Text('notLoaded'),success:panel._v106Text('loaded')};
  },language);
  assert.equal(result.errors.length,1);assert.ok(result.errors[0].includes(result.expected));assert.ok(!result.messages.includes(result.success));
 }
 const blocked=await page.evaluate(async()=>{
  prepare(0);window.detail=async()=>({...structuredClone(recipe),match:{safe:false}});await panel._v66Send(recipe,'one');
  return {calls,errors};
 });assert.equal(blocked.calls.some(r=>r.type.endsWith('/send_multi')),false);assert.equal(blocked.errors.length,1);
 const mismatched=await page.evaluate(async()=>{
  prepare(0);window.detail=async()=>({...structuredClone(recipe),displayVariantId:'another-serving'});await panel._v66Send(recipe,'one');return {calls,errors};
 });assert.equal(mismatched.calls.some(r=>r.type.endsWith('/send_multi')),false);assert.equal(mismatched.errors.length,1);
 const stale=await page.evaluate(async()=>{
  prepare(0);window.detail=async()=>{panel._v63Filters.diet='vegan';return structuredClone(recipe);};await panel._v66Send(recipe,'one');return {calls,errors};
 });assert.equal(stale.calls.some(r=>r.type.endsWith('/send_multi')),false);assert.equal(stale.errors.length,1);
 assert.deepEqual(browserErrors,[]);
 console.log('v106: Send clicks for four real foreign editions, exact IDs/servings, preferred device-language mapping, existing queue path, target/filter scoping, stale and blocked requests, and localized unconfirmed-load errors passed');
}finally{await browser.close();}
