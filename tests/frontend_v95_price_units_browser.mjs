import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const fixture=JSON.parse(readFileSync(root+'/docs/price-expansion-v95-preview.json','utf8'));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('about:blank');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v95-bundle.js'});
 await page.evaluate(fixture=>{
  globalThis.customElements.define('cook4me-v95-test',class extends globalThis.customElements.get('cook4me-recipe-hub-panel-v95'){connectedCallback(){} disconnectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v95-test');p._hass={language:'el'};p._uiIngredientLanguage=()=>p._hass.language;p._langCode=()=>p._hass.language;
  document.body.append(p);if(!p.shadowRoot)p.attachShadow({mode:'open'});
  window.recipe=fixture.recipe;window.state={cost:fixture.cost};
  p.shadowRoot.innerHTML=fixture.recipe.ingredients.map((_,i)=>`<small data-v79-item="${i}" style="display:block"></small>`).join('');
  p.shadowRoot.querySelectorAll('[data-v79-item]').forEach(node=>p._v79PaintItem(node,state));
 },fixture);
 const p=page.locator('cook4me-v95-test');
 assert.match(await p.locator('[data-v79-item="0"]').innerText(),/1 κ\.γ\. ≈ 2 g/);
 assert.match(await p.locator('[data-v79-item="4"]').innerText(),/2 κλωνάρια ≈ 2 g/);
 assert.match(await p.locator('[data-v79-item="5"]').innerText(),/5 φύλλα ≈ 2,5 g/);
 assert.match(await p.locator('[data-v79-item="6"]').innerText(),/100 ml ≈ 103,1 g/);
 await page.evaluate(()=>panel.shadowRoot.innerHTML=panel._v79CostHtml(recipe,state));
 await p.locator('.v79-evidence>summary').click();
 const milk='https://new.milk.org/discover-dairy/recipes/winter-comfort-butter-chicken/';
 assert.equal(await p.locator(`a[href="${milk}"]`).count(),1);
 assert.equal(await p.locator('[data-v94-quantity]').count(),7);
 for(const language of ['en','de','el']){
  const text=await page.evaluate(language=>{panel._hass.language=language;return panel._v94Amount(2,'sprig');},language);
  assert.match(text,language==='de'?/2 Zweige/:language==='el'?/2 κλωνάρια/:/2 sprigs/);
 }
 // Adding a reviewed source host must not allow lookalike or credential URLs.
 for(const sourceUrl of ['https://new.milk.org.evil.test/a','https://new.milk.org@evil.test/a']){
  const links=await page.evaluate(sourceUrl=>{
   const cost=structuredClone(state.cost);cost.ingredients[0].quantityEstimate.sourceUrl=sourceUrl;
   panel.shadowRoot.innerHTML=panel._v79CostHtml(recipe,{cost});return [...panel.shadowRoot.querySelectorAll('a')].map(a=>a.href);
  },sourceUrl);assert.ok(!links.includes(sourceUrl));
 }
 assert.deepEqual(errors,[]);console.log('v95: shipped bundle displays converted costs, localized leaf/sprig notes and safe quantity-source links');
}finally{await browser.close();}
