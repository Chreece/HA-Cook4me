import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage({viewport:{width:1100,height:850}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><body style="font:16px Arial"></body>'}));
 await page.goto('http://cook4me.test/');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v88-bundle.js'});
 await page.evaluate(()=>{
  globalThis.customElements.define('cook4me-v88-test',class extends customElements.get('cook4me-recipe-hub-panel-v88'){connectedCallback(){} disconnectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v88-test');
  p._hass={language:'en',user:{id:'alice'},config:{country:'DE'}};p._entryId='one';
  p._uiIngredientLanguage=()=> 'en';p._langCode=()=> 'en';p._prefKey=()=>p._entryId;p._v84SchedulePricePoll=()=>{};
  p._v79Payload=r=>({variantFunctionalId:r.variantFunctionalId||r.id});p._v79PaintRecipe=(recipe,state)=>p._v82PaintCard(recipe);
  window.calls=[];window.active=0;window.maximum=0;window.releases=[];
  p._api=async(type,data)=>{if(!type.endsWith('/recipe_cost'))return {};calls.push({type,...data});active++;maximum=Math.max(maximum,active);await new Promise(resolve=>releases.push(resolve));active--;return {offlinePreview:true,ingredients:[{name:'Onion',coverage:1,costsByCurrency:{EUR:.22}}],totalsByCurrency:{EUR:.22},complete:true};};
  document.body.append(p);if(!p.shadowRoot)p.attachShadow({mode:'open'});p.shadowRoot.innerHTML='<div id="content"></div>';
  for(let i=0;i<5;i++){const recipe={id:String(i),variantFunctionalId:String(i)},card=document.createElement('article');card.dataset.v66Ref=String(i);card._v82Recipe=recipe;card.innerHTML='<span data-v82-card-cost></span>';p.shadowRoot.querySelector('#content').append(card);p._v86QueuePreview(recipe,card);}
 });
 await page.waitForFunction(()=>window.calls.length===3);
 assert.equal(await page.evaluate(()=>maximum),3,'card previews have bounded concurrency');
 assert.equal(await page.evaluate(()=>calls.every(call=>call.offline_only===true)),true);
 await page.evaluate(()=>{releases.splice(0).forEach(resolve=>resolve());});
 await page.waitForFunction(()=>calls.length===5);
 await page.evaluate(()=>{releases.splice(0).forEach(resolve=>resolve());});
 await page.waitForFunction(()=>window.panel._v86Running===0);
 assert.match(await page.locator('cook4me-v88-test [data-v82-card-cost]').first().innerText(),/0\.22/);
 assert.match(await page.locator('cook4me-v88-test [data-v82-card-cost]').first().innerText(),/1\/1 ingredients priced/);
 await page.evaluate(()=>{
  const card=panel.shadowRoot.querySelector('[data-v66-ref]'),recipe=card._v82Recipe;
  panel._v79CostState(recipe).cost={complete:false,estimated:true,totalsByCurrency:{EUR:2.12},ingredients:[{name:'Milk',coverage:1},{name:'Salt <unsafe>',coverage:0,priceStatus:'recipe_amount_unknown'}]};
  panel._v82PaintCard(recipe);
 });
 assert.match(await page.locator('cook4me-v88-test [data-v82-card-cost]').first().innerText(),/Subtotal.*2.12.*1\/2 ingredients priced/);
 assert.match(await page.locator('cook4me-v88-test [data-v82-card-cost]').first().getAttribute('title'),/Salt <unsafe>.*quantity missing/);
 assert.equal(await page.locator('cook4me-v88-test unsafe').count(),0);
 // An old account/entry's response cannot repaint the new account's cards.
 await page.evaluate(()=>{
  const p=panel,recipe={id:'late'},card=document.createElement('article');card.dataset.v66Ref='late';card._v82Recipe=recipe;card.innerHTML='<span data-v82-card-cost></span>';p.shadowRoot.append(card);window.lateRecipe=recipe;p._v86QueuePreview(recipe,card);p._entryId='two';releases.splice(0).forEach(resolve=>resolve());
 });
 await page.waitForFunction(()=>panel._v86Running===0);
 assert.equal(await page.evaluate(()=>panel._v79CostState(lateRecipe).cost),null);
 await page.evaluate(()=>{
  const state={cost:{complete:false,estimated:true,targetCountry:'DE',totalsByCurrency:{EUR:.22},perServingByCurrency:{EUR:.11},ingredients:[
   {name:'Onion',coverage:1,costsByCurrency:{EUR:.22},quantityEstimate:{sourceQuantity:1,sourceUnit:'piece',quantity:110,unit:'g',label:'USDA medium onion',sourceUrl:'https://fdc.nal.usda.gov/food-details/170000/nutrients'}},
   {name:'Salt <unsafe>',coverage:0,costsByCurrency:{},priceStatus:'recipe_amount_unknown'}]}};
  panel.shadowRoot.innerHTML=panel._v79CostHtml({},state);
 });
 const panel=page.locator('cook4me-v88-test');
 assert.match(await panel.locator('[data-v86-missing]').innerText(),/Salt <unsafe>.*quantity missing/);
 await panel.locator('.v79-evidence>summary').click();
 assert.match(await panel.locator('[data-v86-quantity-estimate]').innerText(),/Estimated quantity: 1 piece ≈ 110 g/);
 assert.equal(await panel.locator('unsafe').count(),0);
 assert.match(await panel.locator('[data-v86-quantity-estimate] a').getAttribute('href'),/^https:\/\/fdc\.nal\.usda\.gov/);
 assert.match(await page.evaluate(()=>panel._v79Reference({source:'retail_snapshot',productName:'dmBio sugar',location:'dm Germany',date:'2026-09-16',amount:2.45,currency:'EUR',basisQuantity:500,basisUnit:'g',sourceUrl:'https://www.dm.de/p/d/1454994/dmbio-vollrohrzucker'})),/data-v87-reference.*dmBio sugar/);
 for(const url of ['javascript:alert(1)','https://www.dm.de.evil.test/x','https://www.dm.de@evil.test/x','https://www.dallmayr-versand.de.evil.test/x','https://www.dallmayr-versand.de@evil.test/x']){
  const html=await page.evaluate(url=>panel._v79Reference({source:'utility_snapshot',productName:'Water <unsafe>',note:'Local tariff <unsafe>',sourceUrl:url}),url);
  assert.equal(html.includes('<a '),false);assert.equal(html.includes('<unsafe>'),false);
 }
 const regional=await page.evaluate(()=>panel._v79Reference({source:'utility_snapshot',productName:'Berlin water',note:'Regional benchmark; excludes fixed charges',sourceUrl:'https://www.bwb.de/de/gebuehren.php'}));
 assert.match(regional,/Regional benchmark/);assert.match(regional,/href="https:\/\/www.bwb.de/);
 const onion=await page.evaluate(()=>panel._v79Reference({source:'retail_snapshot',productName:'Spring onion',note:'130 g bunch; Munich-only delivery',sourceUrl:'https://www.dallmayr-versand.de/p/lauchzwiebel-2669BD/'}));
 assert.match(onion,/130 g bunch/);assert.match(onion,/href="https:\/\/www.dallmayr-versand.de\/p\/lauchzwiebel/);
 assert.deepEqual(errors,[]);console.log('v88 browser: offline previews, concurrency, entry isolation, quantity sources and missing-cost explanation passed');
}finally{await browser.close();}
