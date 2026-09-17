import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const fixture=JSON.parse(readFileSync(root+'/docs/price-expansion-v97-preview.json','utf8'));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('about:blank');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v97-bundle.js'});
 await page.evaluate(fixture=>{
  globalThis.customElements.define('cook4me-v97-test',class extends globalThis.customElements.get('cook4me-recipe-hub-panel-v97'){connectedCallback(){} disconnectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v97-test');p._hass={language:'el'};p._uiIngredientLanguage=()=>p._hass.language;p._langCode=()=>p._hass.language;
  document.body.append(p);if(!p.shadowRoot)p.attachShadow({mode:'open'});
  window.recipe=fixture.recipe;window.state={cost:fixture.cost};
  p.shadowRoot.innerHTML=fixture.recipe.ingredients.map((_,i)=>`<small data-v79-item="${i}" style="display:block"></small>`).join('');
  p.shadowRoot.querySelectorAll('[data-v79-item]').forEach(node=>p._v79PaintItem(node,state));
 },fixture);
 const p=page.locator('cook4me-v97-test');
 assert.match(await p.locator('[data-v79-item="0"]').innerText(),/2 φύλλα ≈ 2 τεμ\./);
 assert.match(await p.locator('[data-v79-item="1"]').innerText(),/1 κ\.σ\. ≈ 16 g/);
 assert.match(await p.locator('[data-v79-item="2"]').innerText(),/1 κ\.σ\. ≈ 8,6 g/);
 assert.match(await p.locator('[data-v79-item="3"]').innerText(),/13,8 g ≈ 15 ml/);
 assert.match(await p.locator('[data-v79-item="4"]').innerText(),/386 g/);
 await page.evaluate(()=>panel.shadowRoot.innerHTML=panel._v79CostHtml(recipe,state));
 await p.locator('.v79-evidence>summary').click();
 for(const href of ['https://www.piccantino.de/dr-oetker/blattgelatine-12er',
                    'https://www.greenist.de/frischesortiment-bio-steckrueben-1-kg.html',
                    'https://asia4friends.de/japanischer-sake-junmai-kizakura-180ml',
                    'https://fdc.nal.usda.gov/food-details/172238/nutrients',
                    'https://fdc.nal.usda.gov/food-details/171009/nutrients']){
  assert.equal(await p.locator(`a[href="${href}"]`).count(),1);
 }
 assert.equal(await p.locator('[data-v94-quantity]').count(),6);
 for(const [language,sheets,pods] of [['en',['sheet','sheets'],['pod','pods']],
                                    ['de',['Blatt','Blätter'],['Schote','Schoten']],
                                    ['el',['φύλλο','φύλλα'],['λοβός','λοβοί']]]){
  for(const [unit,words] of [['sheet',sheets],['pod',pods]]){
   for(const count of [1,2]){
    const value=await page.evaluate(({language,unit,count})=>{panel._hass.language=language;return panel._v94Amount(count,unit);},{language,unit,count});
    assert.equal(value,`${count} ${words[count-1]}`);
   }
  }
 }
 for(const host of ['www.piccantino.de','www.greenist.de']){
  for(const sourceUrl of [`https://${host}.evil.test/a`,`https://${host}@evil.test/a`,`http://${host}/a`]){
   const links=await page.evaluate(sourceUrl=>{
    const cost=structuredClone(state.cost);cost.ingredients[0].references[0].sourceUrl=sourceUrl;
    panel.shadowRoot.innerHTML=panel._v79CostHtml(recipe,{cost});return [...panel.shadowRoot.querySelectorAll('a')].map(a=>a.href);
   },sourceUrl);assert.ok(!links.includes(sourceUrl));
  }
 }
 assert.deepEqual(errors,[]);console.log('v97: shipped bundle displays sheet counts, sourced portions, translated units and validated evidence links');
}finally{await browser.close();}
