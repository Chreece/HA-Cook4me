import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const fixture=JSON.parse(readFileSync(root+'/docs/price-conversions-v94.json','utf8'));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage({viewport:{width:1000,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><body style="font:16px Arial"></body>'}));
 await page.goto('http://cook4me.test/');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v94-bundle.js'});
 await page.evaluate(fixture=>{
  globalThis.customElements.define('cook4me-v94-test',class extends globalThis.customElements.get('cook4me-recipe-hub-panel-v94'){connectedCallback(){} disconnectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v94-test');p._hass={language:'el',user:{id:'alice'},config:{country:'DE'}};p._entryId='one';p._entries=[{entry_id:'one',profile:{diet:'omnivore'}}];
  p._uiIngredientLanguage=()=>p._hass.language;p._langCode=()=>p._hass.language;p._prefKey=()=>p._entryId;p._filters=()=>({diet:'omnivore'});p._v84SchedulePricePoll=()=>{};p._v86QueuePreview=()=>{};
  document.body.append(p);if(!p.shadowRoot)p.attachShadow({mode:'open'});
  window.recipe=fixture.recipe;recipe.match={quantityAvailability:recipe.ingredients.map(item=>({key:item.foodKey||item.key,name:item.name,coverage:0,status:'missing'}))};
  window.cost=fixture.cost;window.state=p._v79CostState(recipe);state.cost=cost;
  p.shadowRoot.innerHTML=p._v66Body(recipe,false,p._v66State(recipe));p.shadowRoot.querySelectorAll('[data-v79-item]').forEach(node=>p._v79PaintItem(node,state));
 },fixture);
 const panel=page.locator('cook4me-v94-test');
 assert.equal(await panel.locator('[data-v79-item]').count(),9);
 await panel.locator('details[data-v66-section="ingredients"] > summary').click();
 assert.match(await panel.locator('[data-v79-item="1"]').innerText(),/≈.*0,86.*1 τεμ\. ≈ 400 g/s);
 assert.match(await panel.locator('[data-v79-item="4"]').innerText(),/20 g ≈ 18,75 ml/);
 assert.match(await panel.locator('[data-v79-item="5"]').innerText(),/40 g ≈ 43,48 ml/);
 assert.match(await panel.locator('[data-v79-item="7"]').innerText(),/Πρόχειρη εκτίμηση.*Αλάτι και πιπέρι.*1 g/s);
 assert.equal(await panel.locator('[data-v66-ingredient] > .chip ha-icon[icon="mdi:home-outline"]').count(),9);
 assert.match(await panel.locator('[data-v66-ingredient="1"] > .chip').getAttribute('aria-label'),/Στο ντουλάπι: 0%/);
 // Repaint must replace the old annotation, not duplicate it.
 await page.evaluate(()=>{const node=panel.shadowRoot.querySelector('[data-v79-item="1"]');panel._v79PaintItem(node,state);panel._v79PaintItem(node,state);});
 assert.equal(await panel.locator('[data-v79-item="1"] [data-v94-quantity]').count(),1);
 // Detailed source links keep the original recipe, quantity and price evidence visible.
 await page.evaluate(()=>panel.shadowRoot.innerHTML=panel._v79CostHtml(recipe,state));
 await panel.locator('.v79-evidence>summary').click();
 assert.match(await panel.locator('.v79-price-head').innerText(),/Εκτιμώμενο σύνολο/);
 assert.equal(await panel.locator('a[href="https://www.tefal.pl/przepisy/detail/index/source/PRO/id/848764/"]').count(),2);
 assert.match(await panel.locator('[data-v94-quantity]').last().innerText(),/ποσότητα αναφοράς: 1 g/);
 assert.equal(await panel.locator('a[href="https://www.fao.org/4/ap815e/ap815e.pdf"]').count(),1);
 assert.equal(await panel.locator('a[href="https://fdc.nal.usda.gov/food-details/172241/nutrients"]').count(),1);
 // Unknown amounts remain explicit, and untrusted source links cannot execute.
 await page.evaluate(()=>{
  panel._hass.language='en';const node=document.createElement('small');node.dataset.v79Item='0';panel.shadowRoot.replaceChildren(node);
  panel._v79PaintItem(node,{cost:{ingredients:[{coverage:0,costsByCurrency:{},priceStatus:'recipe_amount_unknown'}]}});
 });
 assert.match(await panel.locator('[data-v79-item]').innerText(),/Recipe quantity missing/);
 for(const sourceUrl of ['javascript:alert(1)','https://www.tefal.pl.evil.test/a','https://www.tefal.pl@evil.test/a']){
  const anchors=await page.evaluate(sourceUrl=>{
   const fake={...cost,ingredients:[{name:'Unsafe <script>',coverage:1,costsByCurrency:{EUR:1},quantityEstimate:{kind:'source_recipe_quantity',quantity:1,unit:'g',label:'<script>',sourceUrl}}],fallbackIngredientCount:0};
   panel.shadowRoot.innerHTML=panel._v79CostHtml(recipe,{cost:fake});return panel.shadowRoot.querySelectorAll('a').length;
  },sourceUrl);assert.equal(anchors,0);
 }
 assert.equal(await panel.locator('script').count(),0);
 assert.deepEqual(errors,[]);console.log('v94: real screenshot prices, quantity notes, pantry indicators, source links, repainting and missing-quantity messages passed');
}finally{await browser.close();}
