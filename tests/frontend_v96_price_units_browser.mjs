import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const fixture=JSON.parse(readFileSync(root+'/docs/price-expansion-v96-preview.json','utf8'));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('about:blank');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v96-bundle.js'});
 await page.evaluate(fixture=>{
  globalThis.customElements.define('cook4me-v96-test',class extends globalThis.customElements.get('cook4me-recipe-hub-panel-v96'){connectedCallback(){} disconnectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v96-test');p._hass={language:'el'};p._uiIngredientLanguage=()=>p._hass.language;p._langCode=()=>p._hass.language;
  document.body.append(p);if(!p.shadowRoot)p.attachShadow({mode:'open'});
  window.recipe=fixture.recipe;window.state={cost:fixture.cost};
  p.shadowRoot.innerHTML=fixture.recipe.ingredients.map((_,i)=>`<small data-v79-item="${i}" style="display:block"></small>`).join('');
  p.shadowRoot.querySelectorAll('[data-v79-item]').forEach(node=>p._v79PaintItem(node,state));
 },fixture);
 const p=page.locator('cook4me-v96-test');
 assert.match(await p.locator('[data-v79-item="0"]').innerText(),/1 κ\.γ\. ≈ 0,6 g/);
 assert.match(await p.locator('[data-v79-item="1"]').innerText(),/1 κ\.σ\. ≈ 3,1 g/);
 assert.match(await p.locator('[data-v79-item="2"]').innerText(),/1 κ\.γ\. ≈ 2,2 g/);
 assert.match(await p.locator('[data-v79-item="3"]').innerText(),/18 g ≈ 15 ml/);
 await page.evaluate(()=>panel.shadowRoot.innerHTML=panel._v79CostHtml(recipe,state));
 await p.locator('.v79-evidence>summary').click();
 for(const href of ['https://asia4friends.de/fischsauce-38n-thanh-ha-500ml',
                    'https://asia4friends.de/gruene-linsen-trs-500g',
                    'https://fdc.nal.usda.gov/food-details/174531/nutrients']){
  assert.equal(await p.locator(`a[href="${href}"]`).count(),1);
 }
 assert.equal(await p.locator('[data-v94-quantity]').count(),4);
 for(const language of ['en','de','el']){
  const value=await page.evaluate(language=>{panel._hass.language=language;return panel._v94Amount(2,'sprig');},language);
  assert.match(value,language==='de'?/2 Zweige/:language==='el'?/2 κλωνάρια/:/2 sprigs/);
 }
 for(const sourceUrl of ['https://asia4friends.de.evil.test/a','https://asia4friends.de@evil.test/a','http://asia4friends.de/a']){
  const links=await page.evaluate(sourceUrl=>{
   const cost=structuredClone(state.cost);cost.ingredients[3].references[0].sourceUrl=sourceUrl;
   panel.shadowRoot.innerHTML=panel._v79CostHtml(recipe,{cost});return [...panel.shadowRoot.querySelectorAll('a')].map(a=>a.href);
  },sourceUrl);assert.ok(!links.includes(sourceUrl));
 }
 assert.deepEqual(errors,[]);console.log('v96: shipped bundle displays converted costs, translated units and validated retail/quantity source links');
}finally{await browser.close();}
