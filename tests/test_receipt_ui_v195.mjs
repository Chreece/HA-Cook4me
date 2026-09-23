import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const source=await fs.readFile(new URL('../custom_components/cook4me/frontend/scanner-receipts-v195.js',import.meta.url),'utf8');
const {ReceiptScannerMixin,receiptPosition,receiptTotals,removeWeeklyReceiptSections,RECEIPT_TEXT}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const clone=x=>structuredClone(x);
const raw=()=>({merchant:'Fixture Markt',purchaseDate:'2026-09-23',currency:'EUR',total:4,items:[{id:'a',productName:'Carrot',kind:'product',quantity:500,unit:'g',packageCount:2,lineTotal:3,status:'pending',ingredientLinks:[]},{id:'b',productName:'Milk',kind:'product',quantity:1,unit:'l',packageCount:1,lineTotal:1,status:'pending',ingredientLinks:[]}]});
function setup(){
 const calls=[];
 class Base{
  _v78Fresh(mode){return {mode,unit:'g',purchaseDate:'TODAY',paidCurrency:'USD',paidAmount:'',ingredientLinks:[],nutrition:{basisQuantity:100,basisUnit:'',values:{}}};}
  _v78SetBusy(value){this._v78Busy=value;}
  _v78Alive(c){return c===this._v78Dialog&&!!c;}
  _v111CancelRead(){} _v78IngredientOptions(){this.optionUpdates=(this.optionUpdates||0)+1;}
  _v78SetStatus(value){this.status=value;}
  _v114Links(){return this._v78Draft.ingredientLinks;}
  _uiIngredientLanguage(){return 'el';}
  _v78Close(){this._v78Dialog=null;}
  _v141KeepCameraWarm(){calls.push({type:'warm'});}
  async _v78Camera(){calls.push({type:'camera'});}
  async _v78Save(){calls.push({type:'ordinarySave'});}
  async _v78Recognize(image){this._v78Draft.nutrition={basisQuantity:100,basisUnit:'g',values:{protein:3}};}
  _v78AcceptState(data){this.stock=data.houseIngredients;}
 }
 const host=new (ReceiptScannerMixin(Base))();host._entryId='entry';host._v78Dialog={};host._r195Paint=()=>{};host._v78RenderCapture=()=>{};host._v111Paint=()=>{};
 host._api=async(type,msg)=>{calls.push({type,msg:clone(msg)});return {suggestions:[]};};
 host._r195SetReceipt(raw());return {host,calls};
}
test('previous/next clamp at boundaries',()=>{assert.equal(receiptPosition([1,2],0,-1),0);assert.equal(receiptPosition([1,2],1,1),1);});
test('line totals include discounts and deposits but not total/tax rows',()=>{const r=raw();r.items.push({kind:'discount',lineTotal:-.5},{kind:'deposit',lineTotal:.25},{kind:'total',lineTotal:99});r.total=3.75;assert.deepEqual(receiptTotals(r),{amount:3.75,known:true,different:false});});
test('unknown prices are not presented as complete zero totals',()=>{const r=raw();r.items[0].lineTotal=null;assert.equal(receiptTotals(r).known,false);});
test('different receipt totals are reported',()=>{const r=raw();r.total=9;assert.equal(receiptTotals(r).different,true);});
test('weekly removal is limited to four data keys',()=>{const removed=[];const pair={children:[{}],style:{}};const root={querySelectorAll(selector){if(selector==='.two')return [pair];return [{remove:()=>removed.push(selector)}];}};removeWeeklyReceiptSections(root);assert.equal(removed.length,4);assert.ok(removed.some(x=>x.includes('reservedStock')));assert.ok(removed.every(x=>!x.includes('shoppingDelta')));assert.equal(pair.style.gridTemplateColumns,'minmax(0,1fr)');});
test('receipt item load never inherits today or preferred currency',()=>{const {host}=setup();const r=raw();r.purchaseDate='';r.currency='';host._r195SetReceipt(r);assert.equal(host._v78Draft.purchaseDate,'');assert.equal(host._v78Draft.paidCurrency,'');assert.equal(host._v78Draft.ingredient,null);});
test('navigation preserves amounts, nutrition and multiple ingredient choices',()=>{const {host}=setup();Object.assign(host._v78Draft,{quantity:'750',productName:'Edited carrot',ingredientLinks:[{key:'a'},{key:'b'}],nutrition:{basisQuantity:100,basisUnit:'g',values:{protein:2}}});host._v78Dirty=true;host._r195Move(1);host._r195Move(-1);assert.equal(host._v78Draft.quantity,'750');assert.equal(host._v78Draft.productName,'Edited carrot');assert.equal(host._v78Draft.ingredientLinks.length,2);assert.equal(host._v78Draft.nutrition.values.protein,2);});
test('busy scanner cannot change item',()=>{const {host}=setup();host._v78Busy=true;host._r195Move(1);assert.equal(host._r195Session.index,0);});
test('saved applied item cannot be rewritten by stale editor',()=>{const {host}=setup();host._r195Current().status='applied';host._v78Draft.quantity=999;host._r195Flush();assert.equal(host._r195Current().quantity,500);});
test('renaming invalidates semantic suggestions',()=>{const {host}=setup();host._r195Current().ingredientName='carrot';host._r195Session.suggestions.set('a',[{}]);host._v78Draft.productName='Onion';host._r195Flush();assert.equal(host._r195Current().ingredientName,'');assert.equal(host._r195Session.suggestions.has('a'),false);});
test('late suggestion response for old product name is ignored',async()=>{const {host}=setup();let resolve;host._api=()=>new Promise(r=>resolve=r);const item=host._r195Current(),d=host._v78Draft,s=host._r195Session;const pending=host._r195Suggestions(item,d,s);d.productName='Other';host._r195Flush();const before=host.optionUpdates||0;resolve({suggestions:[{ingredient:{key:'old'}}]});await pending;assert.equal(host.optionUpdates||0,before);assert.deepEqual(d.suggestions,[]);});
test('old item suggestions cannot overwrite new item',async()=>{const {host}=setup();let resolve;host._api=()=>new Promise(r=>resolve=r);const d=host._v78Draft,s=host._r195Session;const pending=host._r195Suggestions(host._r195Current(),d,s);host._v78Draft={};resolve({suggestions:[{}]});await pending;assert.equal(host._v78Draft.suggestions,undefined);});
test('save draft sends no stock call and accepts new item IDs',async()=>{const {host,calls}=setup();host._api=async(type,msg)=>{calls.push({type,msg:clone(msg)});return {receipt:{...clone(msg.receipt),id:'saved',revision:1,items:msg.receipt.items.map((x,i)=>({...x,id:'new'+i}))}};};await host._r195Action('save');assert.equal(host._r195Session.receipt.id,'saved');assert.equal(host._v78Draft.receiptItemId,'new0');assert.ok(!calls.some(x=>x.type.includes('product_add')));assert.equal(host._r195Session.dirty,false);});
test('double-click Apply is serialized before draft write',async()=>{const {host,calls}=setup();let resolve;host._api=async(type,msg)=>{calls.push({type,msg:clone(msg)});if(msg.action==='save')await new Promise(r=>resolve=r);return {receipt:{...clone(msg.receipt||host._r195Session.receipt),id:'saved',revision:1}};};const first=host._r195Action('apply');await host._r195Action('apply');assert.equal(calls.filter(x=>x.msg?.action==='save').length,1);resolve();await first;assert.equal(calls.filter(x=>x.msg?.action==='apply').length,1);});
test('retry applying item does not resave or create a new request',async()=>{const {host,calls}=setup();Object.assign(host._r195Session.receipt,{id:'saved',revision:3});host._r195Current().status='applying';host._r195Session.dirty=false;host._api=async(type,msg)=>{calls.push({type,msg});const r=clone(host._r195Session.receipt);r.items[0].status='applied';return {receipt:r,result:{houseIngredients:[{name:'Carrot'}]}}};await host._r195Action('apply');assert.equal(calls.filter(x=>x.msg?.action==='save').length,0);assert.equal(calls.filter(x=>x.msg?.action==='apply').length,1);assert.equal(host._r195Session.index,1);assert.equal(host.stock.length,1);});
test('interrupted apply reloads durable server state without advancing',async()=>{const {host,calls}=setup();Object.assign(host._r195Session.receipt,{id:'saved',revision:3});host._r195Current().status='applying';host._r195Session.dirty=false;host._api=async(type,msg)=>{calls.push({type,msg});if(msg.action==='apply')throw Error('Lost connection');return {receipt:clone(host._r195Session.receipt)};};await host._r195Action('apply');assert.equal(host._r195Session.index,0);assert.ok(calls.some(x=>x.msg?.action==='get'));assert.match(host._r195Message,/Lost connection/);});
test('discard unsaved item is local and keeps other edits',async()=>{const {host}=setup();await host._r195Action('discard');assert.equal(host._r195Session.receipt.items[0].status,'discarded');assert.equal(host._r195Session.index,1);});
test('cancel discard whole receipt changes nothing',async()=>{const {host}=setup();globalThis.confirm=()=>false;await host._r195Action('discardAll');assert.equal(host._r195Session.receipt.items.length,2);});
test('receipt upload never auto-starts the camera',async()=>{const {host,calls}=setup();await host._r195Start(true,false);host._v141KeepCameraWarm();assert.equal(host._v78Draft.mode,'receipt');assert.ok(!calls.some(x=>['camera','warm'].includes(x.type)));});
test('normal scanner Save still delegates',async()=>{const {host,calls}=setup();host._r195Session=null;await host._v78Save();assert.ok(calls.some(x=>x.type==='ordinarySave'));});
test('date/nutrient scans preserve receipt context',async()=>{const {host}=setup();host._v78Draft.mode='nutrition';await host._v78Recognize('fixture');assert.equal(host._r195Current().nutrition.values.protein,3);assert.equal(host._v78Draft.editorOpen,true);});
test('Greek/German/English expose same complete receipt wording',()=>{for(const language of ['de','el'])assert.deepEqual(Object.keys(RECEIPT_TEXT[language]).sort(),Object.keys(RECEIPT_TEXT.en).sort());});
