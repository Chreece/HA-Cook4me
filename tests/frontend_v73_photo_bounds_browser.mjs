// Real browser geometry: the DOM-only tests cannot detect CSS cascade clipping.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const {chromium}=createRequire(import.meta.url)('playwright');
const version=process.env.COOK4ME_TEST_PANEL_VERSION||'73';
const browser=await chromium.launch({headless:true,executablePath:process.env.COOK4ME_CHROMIUM_EXECUTABLE||undefined,
 args:['--no-sandbox','--disable-gpu','--disable-software-rasterizer','--use-gl=disabled']});
try{
 const page=await browser.newPage();
 await page.route('http://cook4me.test/**',route=>route.fulfill({contentType:'text/html',body:`<!doctype html><html><head><style>
  body{margin:0;background:#111;--primary-text-color:#ddd;--primary-background-color:#111;--card-background-color:#1b2426;--secondary-background-color:#222;--secondary-text-color:#aaa;--divider-color:#444;--primary-color:#009fc0;font-family:Arial}
 </style></head><body></body></html>`}));
 await page.goto('http://cook4me.test/');
 await page.addScriptTag({path:fileURLToPath(new URL(`../custom_components/cook4me/frontend/cook4me-panel-v${version}-bundle.js`,import.meta.url))});
 await page.evaluate(version=>{
  const panel=document.createElement(`cook4me-recipe-hub-panel-v${version}`);document.body.append(panel);window.panel=panel;
  panel._api=async()=>({});panel._restorePreferences=async()=>{};panel._loadOverview=async()=>{};panel._loadBookState=async()=>{};panel._requestSection=async()=>{};panel._loadRecipeNutrition=async()=>{};
  panel._hass={language:'el',user:{id:'layout'},states:{},config:{country:'DE'},connection:{}};
  panel._entryId='one';panel._entries=['one','two'].map(entry_id=>({entry_id,title:'Cook4Me',connected:true,canAcceptRecipe:true,state:{},recipes:[],profile:{houseIngredients:[]}}));
  panel._capabilities={localAiTaskAvailable:true,localAiTaskEntityId:'ai_task.local',deviceCatalogLanguage:'de'};
  panel._filters=()=>({languages:['de','fr'],diet:'vegetarian',mealTypes:[],ingredients:[],nutritionGoal:'balanced'});
  panel._renderShell();
  // Registered HA icons have a real 22px box in production. Emulate the icon
  // only; every card, action, style and responsive grid comes from the bundle.
  const icons=document.createElement('style');icons.textContent='ha-icon{display:inline-block;width:22px;height:22px}ha-icon::after{content:"◆"}';panel.shadowRoot.append(icons);
  const cover='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450"><rect width="800" height="450" fill="#dea958"/><circle cx="400" cy="225" r="180" fill="#fff2d0"/><circle cx="400" cy="225" r="135" fill="#809447"/><path d="M0 430H800" stroke="#da4444" stroke-width="40"/></svg>');
  const recipe=(i)=>({id:`r${i}`,source:'release_offline',title:i%2?'Μπρουσκέτα φασολιών και κρέμας κατσίκι':'Βρώμη με φρούτα και σιρόπι σφενδάμου',language:'de',displayVariantId:`${i}-de-4`,searchVariantId:`${i}-de-4`,sendVariantId:`${i}-de-4`,cover:i===6?'':cover,servings:4,ingredients:[],steps:[{instruction:'Stir for 2 minutes'}],dietary:{vegetarian:true},mealTypes:['main'],match:{...(Number(version)>=76?{diet:'vegetarian',dietCheckVersion:76}:{}),safe:true}});
  window.recipes=Array.from({length:7},(_,i)=>recipe(i));
  if(Number(version)>=76)window.recipes[0].match={diet:'vegetarian',dietCheckVersion:76,safe:false,eligibleWithSubstitutions:true,requiresSubstitutions:true,
   substitutions:[{ingredientIndex:0,original:'Πάπια',replacement:{key:'tofu',name:'Firm tofu'}},{ingredientIndex:1,original:'Γαρίδες',replacement:{key:'mushrooms',name:'Mushrooms'}}]};
  window.render=(kind,expanded=false)=>{
   const content=panel.shadowRoot.querySelector('#content');
   let html='';
   for(const [i,r] of window.recipes.entries()){
    const slot=kind==='week'?{id:`s${i}`,date:'2026-09-15',recipe:r,mealType:'breakfast'}:null;
    panel._v66Slot=slot;panel._v66State(r,slot?.id||'').expanded=expanded;
    const card=panel._recipeCard(r,false);panel._v66Slot=null;
    html+=kind==='week'?`<section class="rx-week-day"><div class="rx-week-slot" data-slot-id="s${i}"><h4>Πρωινό</h4>${card}</div></section>`:card;
   }
   content.innerHTML=`<div class="${kind==='week'?'rx-week-grid':'grid'}">${html}</div>`;
   // Deliberately put the old stylesheet last: the fix must withstand lazy
   // style insertion and not rely on which async render completes first.
   const legacy=panel.shadowRoot.querySelector('#cook4meModernV30');if(legacy)panel.shadowRoot.append(legacy);
   panel._bindCards(content,window.recipes,false);
  };
 },version);
 const cases=[];
 for(const [width,kind,expanded] of [[1800,'week',false],[1160,'week',false],[900,'grid',false],[390,'grid',false],[390,'week',false],[900,'grid',true]]){
  await page.setViewportSize({width,height:900});await page.evaluate(({kind,expanded})=>window.render(kind,expanded),{kind,expanded});
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  const rows=await page.evaluate(()=>[...window.panel.shadowRoot.querySelectorAll('#content article.recipe')].map(card=>{
   const box=el=>{const r=el.getBoundingClientRect();return {top:r.top,bottom:r.bottom,left:r.left,right:r.right,height:r.height,width:r.width};};
   const media=card.querySelector('.rx-v69-media'),overlay=card.querySelector('.rx-v69-overlay'),style=getComputedStyle(card);
   return {card:box(card),media:box(media),overlay:box(overlay),title:box(card.querySelector('.rx-v66-title')),padding:style.padding,gap:style.gap,
    controls:[...overlay.querySelectorAll('button,select')].map(box),body:card.querySelector('.rx-v66-body')?box(card.querySelector('.rx-v66-body')):null};
  }));
  assert.equal(rows.length,7,'All seven test cards must be rendered');
  for(const [i,row] of rows.entries()){
   const context=`${width}px ${kind} ${expanded?'expanded':'collapsed'} card ${i}`;
   assert.ok(row.media.bottom<=row.card.bottom-1+.5,`${context}: photo bottom ${row.media.bottom} exceeds card ${row.card.bottom}`);
   assert.ok(Math.abs(row.media.height-220)<.5,`${context}: full photo area retained`);
   assert.ok(Math.abs(row.card.height-(expanded?600:310))<.5,`${context}: uniform dimensions`);
   assert.equal(row.padding,'0px',`${context}: old padding removed`);assert.equal(row.gap,'0px',`${context}: old gap removed`);
   assert.ok(Math.abs(row.title.bottom-row.media.top)<.5,`${context}: no displaced photo`);
   for(const control of row.controls){
    assert.ok(control.bottom<=row.media.bottom+.5,`${context}: button clipped at photo bottom`);
    assert.ok(control.top>=row.media.top-.5,`${context}: button clipped at photo top`);
    assert.ok(control.left>=row.media.left-.5&&control.right<=row.media.right+.5,`${context}: button clipped horizontally`);
   }
   if(row.body)assert.ok(row.body.bottom<=row.card.bottom+.5,`${context}: details retained inside expanded card`);
  }
  cases.push({width,kind,expanded,cards:rows.length});
 }
 if(process.env.COOK4ME_LAYOUT_SCREENSHOT){
  await page.setViewportSize({width:900,height:800});await page.evaluate(()=>window.render('grid'));
  await page.locator('cook4me-recipe-hub-panel-v'+version).locator('#content').screenshot({path:process.env.COOK4ME_LAYOUT_SCREENSHOT});
 }
 console.log(JSON.stringify({version,cases}));console.log('Browser photo and button bounds passed across desktop, narrow weekly, mobile and expanded cards');
}finally{await browser.close();}
