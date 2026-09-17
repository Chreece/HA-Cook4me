import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const fixture=JSON.parse(readFileSync(root+'/docs/price-expansion-v103-preview.json','utf8'));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('about:blank');await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v103-bundle.js'});
 await page.evaluate(fixture=>{
  globalThis.customElements.define('cook4me-v103-test',class extends globalThis.customElements.get('cook4me-recipe-hub-panel-v103'){connectedCallback(){} disconnectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v103-test');p._hass={language:'el'};p._uiIngredientLanguage=()=>p._hass.language;p._langCode=()=>p._hass.language;
  document.body.append(p);if(!p.shadowRoot)p.attachShadow({mode:'open'});
  window.recipe=fixture.recipe;window.state={cost:fixture.cost};
 },fixture);
 const p=page.locator('cook4me-v103-test');
 for(const language of ['en','de','el']){
  await page.evaluate(language=>{panel._hass.language=language;panel.shadowRoot.innerHTML=panel._v79CostHtml(recipe,state);},language);
  await p.locator('.v79-evidence>summary').click();
  for(const row of fixture.cost.ingredients){
   for(const ref of row.references){
    const links=await p.locator('a').evaluateAll(nodes=>nodes.map(a=>a.href));
    assert.ok(links.includes(ref.sourceUrl),ref.sourceUrl);
   }
  }
  const evidenceLinks=await p.locator('a').evaluateAll(nodes=>nodes.map(a=>a.href));
  for(const id of ['172442','173647'])assert.ok(evidenceLinks.some(url=>url.includes(id)),id);
  assert.match(await p.evaluate(node=>node.shadowRoot.textContent),/5[,.]48/);
  assert.equal(await page.evaluate(()=>state.cost.priceConfidence),'reference');
 }
 for(const host of ['asianbrand.de']){
  for(const sourceUrl of [`https://${host}.evil.test/a`,`https://${host}@evil.test/a`,`http://${host}/a`,`https://${host}:444/a`]){
   const links=await page.evaluate(sourceUrl=>{
    const cost=structuredClone(state.cost);cost.ingredients[0].references[0].sourceUrl=sourceUrl;
    panel.shadowRoot.innerHTML=panel._v79CostHtml(recipe,{cost});return [...panel.shadowRoot.querySelectorAll('a')].map(a=>a.href);
   },sourceUrl);assert.ok(!links.includes(sourceUrl));
  }
 }
 assert.deepEqual(errors,[]);console.log('v103: actual offline costs and two package references and USDA spoon/water estimates render in English, German and Greek; reviewed source links validate correctly');
}finally{await browser.close();}
