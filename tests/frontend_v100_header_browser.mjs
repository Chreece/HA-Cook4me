import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
const fixture=JSON.parse(readFileSync(root+'/docs/price-confidence-v99-preview.json','utf8'));
const {chromium}=createRequire(import.meta.url)('playwright');
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-gpu']});
try{
 const page=await browser.newPage({viewport:{width:390,height:1000}}),errors=[];
 page.on('pageerror',error=>{errors.push(error.message);console.error(error.stack);});
 await page.route('http://cook4me.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><body style="margin:0;font:16px Arial;--primary-color:#00a4ca;--card-background-color:#202525;--primary-background-color:#111;--primary-text-color:#eee;--text-primary-color:#fff;--secondary-text-color:#aaa;--divider-color:#3e4444;--secondary-background-color:#292e2e"></body>'}));
 await page.goto('http://cook4me.test/');
 // HA supplies this element in production. A compact SVG stand-in makes the
 // isolated layout screenshot readable without contacting the HA frontend.
 await page.evaluate(()=>customElements.define('ha-icon',class extends HTMLElement{
  static get observedAttributes(){return ['icon'];}
  connectedCallback(){this.paint();}attributeChangedCallback(){this.paint();}
  paint(){if(!this.shadowRoot)this.attachShadow({mode:'open'});const name=this.getAttribute('icon')||'';
   const symbols={'mdi:weather-sunny':'☼','mdi:calendar-week':'▣','mdi:magnify':'⌕','mdi:book-open-page-variant-outline':'▤','mdi:chef-hat':'♧','mdi:cart-outline':'🛒','mdi:home-heart':'⌂','mdi:web':'◎','mdi:refresh':'⟳','mdi:filter-variant':'☰','mdi:leaf':'♧','mdi:clock-outline':'◷'};
   this.shadowRoot.innerHTML=`<style>:host{display:inline-flex;width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px);align-items:center;justify-content:center;vertical-align:middle;flex-shrink:0}span{font:24px/1 Arial;color:inherit}</style><span aria-hidden="true">${symbols[name]||'◇'}</span>`;
  }
 }));
 await page.addScriptTag({path:root+'/custom_components/cook4me/frontend/cook4me-panel-v100-bundle.js'});
 await page.evaluate(fixture=>{
  window.fixture=fixture;window.requests=[];window.subscriptions=[];
  globalThis.customElements.define('cook4me-v100-test',class extends globalThis.customElements.get('cook4me-recipe-hub-panel-v100'){connectedCallback(){}});
  const p=window.panel=document.createElement('cook4me-v100-test');
  p._hass={language:'el',user:{id:'alice'},states:{},config:{country:'DE',time_zone:'Europe/Berlin'},connection:{
   sendMessagePromise:async message=>{const request=message.request||message;requests.push(request);if(request.type.endsWith('/currency_set'))return {currency:request.currency||'EUR',defaultCurrency:'EUR',mode:request.mode,currencies:['EUR','USD','GBP']};return {};},
   subscribeMessage:async(callback,request)=>{subscriptions.push({callback,request});return ()=>{};},addEventListener(){},removeEventListener(){}}};
  for(const method of ['_restorePreferences','_loadOverview','_requestSection','_loadRecipeNutrition','_loadIngredientCatalog','_loadTodayOptions','_loadCurrencyState','_loadBookState','_loadShoppingList','_v78Load','_v79LoadSettings','_loadNutritionOptions'])p[method]=async()=>{};
  p._v84SchedulePricePoll=()=>{};p._v86QueuePreview=()=>{};p._v66PreferLanguages=async rows=>rows;
  p._entryId='one';p._entries=[{entry_id:'one',title:'Cook4Me της κουζίνας',connected:false,state:{phase:'idle'},profile:{diet:'vegetarian',houseIngredients:[]},recipes:[]}];p._tab='today';
  p._v63FilterKey=p._prefKey();p._v63Filters={diet:'vegetarian',dietProfile:'manual',ingredients:[],languages:p._languageRows().map(row=>row.code),mealTypes:['breakfast','starter','salad','soup','main','side','dessert','snack'],onlyHome:false,preferExpiring:true,avoidRecentDays:7,maxMissing:'',nutritionGoal:'balanced',maxCost:'',excludedIngredients:[],excludedTerms:[]};
  p._currencyState={currency:'EUR',defaultCurrency:'EUR',mode:'auto',currencies:['EUR','USD','GBP']};p._currencyStateEntry='one';
  p._bookState={favorites:[],recipeList:[]};p._shoppingList=[];p._v78State={storageLocations:[],products:[]};p._v78Loaded=p._prefKey();
  p._todayResults=fixture.slice(0,2).map(row=>({...row.recipe,match:{diet:'vegetarian',dietCheckVersion:76,safe:true}}));
  p._v67WeekLoaded=`${p._prefKey()}:${p._v67Today()}`;p._v93Now=()=>new Date('2026-09-17T08:07:00Z');
  p._renderShell();document.body.append(p);p._renderEntrySelect();p._updateHeader();p._renderTab();
 },fixture);
 const p=page.locator('cook4me-v100-test');
 await page.waitForTimeout(150);
 assert.equal(await page.evaluate(()=>panel._cook4meUiGuardTripped),false,'initial header must settle without a DOM loop');
 for(const language of ['el','de','en']){
  for(const width of [320,390,768,1600]){
   await page.setViewportSize({width,height:1000});
   for(const tab of ['today','week','official','book','mine','shopping','profile']){
    await page.evaluate(({language,tab})=>{panel._hass.language=language;panel._tab=tab;panel._renderTabs();panel._renderTab();panel._updateHeader();},{language,tab});
    await page.waitForTimeout(70);
    const layout=await page.evaluate(()=>{
     const q=s=>panel.shadowRoot.querySelector(s),r=s=>{if(!q(s))throw Error('Missing '+s+' in '+panel._tab+'; '+panel.shadowRoot.querySelector('.v100-navigation')?.outerHTML);return q(s).getBoundingClientRect();},top=r('.v100-top'),nav=r('.v100-navigation'),tabs=r('#tabs'),filters=q('.v100-filter-slot'),section=q('[data-v100-section]');
     return {topHeight:top.height,topOverflow:q('.v100-top').scrollWidth>q('.v100-top').clientWidth+1,
      navOverflow:q('.v100-navigation').scrollWidth>q('.v100-navigation').clientWidth+1,
      actions:[...q('.v100-global-actions').children].filter(node=>getComputedStyle(node).display!=='none').map(node=>node.id),
      filters:!filters.hidden,filtersRight:filters.hidden||filters.getBoundingClientRect().left>=tabs.right-1,
      aligned:filters.hidden||Math.abs(filters.getBoundingClientRect().top+filters.getBoundingClientRect().height/2-(tabs.top+tabs.height/2))<2,
      sectionTop:section.getBoundingClientRect().top,navBottom:nav.bottom,sectionCount:panel.shadowRoot.querySelectorAll('[data-v100-section]').length,
      title:section.querySelector('h1,h2')?.textContent,icons:q('#v82RefreshPrices').querySelectorAll('ha-icon').length,
      statusHeight:q('.status-main').getBoundingClientRect().height,allMenus:q('#tabs').children.length};
    });
    assert.ok(layout.topHeight<=94&&!layout.topOverflow,`${language}/${width}/${tab} header: ${JSON.stringify(layout)}`);
    assert.ok(!layout.navOverflow&&layout.aligned&&layout.filtersRight,`${language}/${width}/${tab} nav: ${JSON.stringify(layout)}`);
    assert.deepEqual(layout.actions,['cook4meUiLanguageControl','cook4meCurrencyControl','v82RefreshPrices']);
    assert.equal(layout.filters,['today','week','official'].includes(tab));
    assert.equal(layout.sectionCount,1);assert.ok(layout.title);assert.ok(Math.abs(layout.sectionTop-layout.navBottom)<=1,JSON.stringify(layout));
    assert.equal(layout.icons,1);assert.ok(layout.statusHeight<65);assert.equal(layout.allMenus,7);
    assert.equal(await page.evaluate(()=>panel._cook4meUiGuardTripped),false,'navigation must leave optional decoration active');
   }
  }
 }
 // Exercise actual menu clicks, hidden filters, migration and one reload action.
 await page.setViewportSize({width:390,height:1000});
 await p.locator('[data-tab=today]').click();
 await p.locator('.v93-filter-toggle').click();assert.equal(await p.locator('.v93-filter-drawer').isVisible(),true);
 await p.locator('.v93-filter-drawer [data-filter=languages]').click();
 assert.equal(await p.locator('[data-filter-dialog=languages]').count(),1);
 await page.keyboard.press('Escape');
 await page.evaluate(()=>{panel._v93FiltersOpen=false;panel._v63FilterDialog?.remove();panel.shadowRoot.querySelector('[data-filter-dialog]')?.remove();panel._renderTab();});
 await p.locator('.v93-active-filters [data-filter=diet]').click();
 await p.locator('[data-filter-dialog=diet] [data-field=diet]').selectOption('omnivore');
 await p.locator('[data-filter-dialog=diet] [data-apply]').click();
 assert.equal(await p.locator('.v93-active-filters [data-filter=diet]').count(),0);
 await page.evaluate(()=>{window.priceClicks=0;panel._v82RefreshPrices=async()=>{window.priceClicks++;};});
 await p.locator('#v82RefreshPrices').click();assert.equal(await page.evaluate(()=>priceClicks),1);
 assert.equal(await p.locator('#v82RefreshPrices ha-icon').count(),1);
 await p.locator('#cook4meCurrency').selectOption('USD');
 await page.waitForFunction(()=>panel._currencyState.currency==='USD');
 assert.equal(await p.locator('[data-v100-currency]').innerText(),'USD');
 await p.locator('#cook4meUiLanguage').selectOption('de');
 assert.equal(await page.evaluate(()=>panel._langCode()),'de');
 assert.equal(await page.evaluate(()=>localStorage.getItem(panel._uiLanguageStorageKey())),'de');
 // Even many active options remain on the right in one scrollable row.
 await page.evaluate(()=>{Object.assign(panel._filters(),{diet:'vegetarian',ingredients:['a','b','c'],languages:['de','en'],mealTypes:['main'],onlyHome:true,calorieTarget:1500,maxCost:5});panel._renderTab();});
 assert.equal(await p.locator('.v93-active-filters [data-filter]').count(),7);
 assert.equal(await p.locator('.v100-navigation').evaluate(row=>row.scrollWidth<=row.clientWidth+1),true);
 assert.equal(await p.locator('.v100-filter-slot').evaluate(slot=>slot.scrollWidth>slot.clientWidth),true);
 await p.locator('.v93-active-filters [data-filter=cost]').click();
 assert.equal(await p.locator('[data-filter-dialog=cost]').count(),1);
 await page.keyboard.press('Escape');
 await page.evaluate(()=>{panel.shadowRoot.querySelector('[data-filter-dialog]')?.remove();});
 // Live state and info remain connected to the compact device illustration.
 await page.evaluate(()=>{const sub=subscriptions.find(row=>row.request.type==='cook4me/v32/device_state_subscribe');sub.callback({entry_id:'one',connected:true,accessible:true,state:{phase:'cooking',recipeTitle:'Vegetable stew'}});});
 assert.equal(await p.locator('#status .v81-cooker').getAttribute('data-phase'),'cooking');
 await p.locator('#status .status').click();assert.equal(await p.locator('[data-device-info]').isVisible(),true);await p.locator('[data-v81-close]').click();
 // Multiple-device controls stay on the left and cannot squeeze the header.
 await page.evaluate(()=>{panel._entries.push({...panel._entries[0],entry_id:'two',title:'Second Cook4Me with a long device name'});panel._renderEntrySelect();panel._updateHeader();});
 assert.equal(await p.locator('.v100-device #entrySelect').isVisible(),true);
 assert.equal(await p.locator('.v100-device #cook4meTargetDevicesControl').count(),1);
 assert.equal(await p.locator('.v100-global-actions #cook4meTargetDevicesControl').count(),0);
 await p.locator('#cook4meTargetDevicesControl summary').click();assert.equal(await p.locator('[data-target-entry="two"]').isVisible(),true);
 await p.locator('[data-target-entry="two"]').check();assert.equal(await p.locator('[data-target-count]').innerText(),'2');
 if(process.env.COOK4ME_SCREENSHOT_DIR){
  await page.evaluate(()=>{
   panel._entries.pop();panel._hass.language='el';panel._saveUiLanguage('auto');panel._currencyState.currency='EUR';
   Object.assign(panel._filters(),{diet:'vegetarian',ingredients:[],languages:panel._languageRows().map(row=>row.code),mealTypes:['breakfast','starter','salad','soup','main','side','dessert','snack'],onlyHome:false,calorieTarget:'',maxCost:''});
   panel._renderEntrySelect();panel._updateHeader();panel._renderTabs();panel._renderTab();
   for(let index=0;index<panel._todayResults.length;index++){const recipe=panel._todayResults[index],cost=fixture[index].cost;panel._v79CostState(recipe).cost=cost;panel._v82PaintCard(recipe);}
  });
  await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+'/v100-mobile.png'});
  await page.setViewportSize({width:1600,height:1000});await page.screenshot({path:process.env.COOK4ME_SCREENSHOT_DIR+'/v100-desktop.png'});
 }
 await page.evaluate(()=>{for(const [key,value] of Object.entries({'--primary-color':'#397b58','--card-background-color':'#fff','--primary-background-color':'#f5f7f5','--primary-text-color':'#183526','--secondary-text-color':'#596f63','--divider-color':'#d7dfd9','--secondary-background-color':'#edf2ee'}))document.body.style.setProperty(key,value);});
 await page.setViewportSize({width:390,height:1000});
 assert.equal(await p.locator('.v100-top').evaluate(top=>top.scrollWidth<=top.clientWidth+1),true);
 assert.equal(await p.locator('.v100-navigation').evaluate(nav=>nav.scrollWidth<=nav.clientWidth+1),true);
 assert.equal(await page.evaluate(()=>panel._cook4meUiGuardTripped),false);
 assert.deepEqual(errors,[]);console.log('v100: compact header and joined menu/filter/section controls pass all seven views, three languages, four widths and live device/filter/reload interactions');
}finally{await browser.close();}
