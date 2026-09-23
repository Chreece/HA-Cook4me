import test from 'node:test';
import assert from 'node:assert/strict';
import {EDITOR_TEXT,editorNumber,editorBarcode,editorIssues,mergeBarcodeDetails,editorRequest,ProductEditorMixin} from '../custom_components/cook4me/frontend/scanner-editor-v196.js';

const ingredient={key:'food-rice',name:'Ρύζι'};
const other={key:'food-carrot',name:'Καρότο'};
const fresh=()=>({requestId:'request-1',mode:'manual',editorOpen:true,productName:'',brand:'',barcode:'',quantity:'',unit:'g',purchaseDate:'2026-09-23',bestBefore:'',openedAt:'',useWithinDays:'',storageLocationId:'',containerId:'',noExpiry:false,packageCount:1,ingredient:null,ingredientLinks:[],nutrition:{basisUnit:'',values:{}},paidAmount:'',paidCurrency:'EUR',paidShop:'',editLotId:'',expectedVersion:''});
const valid=()=>({...fresh(),quantity:500,ingredient,ingredientLinks:[ingredient]});
const frames=[];
globalThis.requestAnimationFrame=callback=>{frames.push(callback);return frames.length;};
const flush=()=>{while(frames.length)frames.shift()();};
const node=()=>({isConnected:true,disabled:false,parentElement:null,focused:0,opened:0,scrolls:0,closest:()=>null,matches:()=>true,focus(){this.focused++;},scrollIntoView(){this.scrolls++;}});
class Boundary {
 constructor(){this._v78Draft=valid();this._v78Dialog={isConnected:true,querySelector:()=>null,querySelectorAll:()=>[],classList:{toggle(){}}};this._v78Context='one';this._entryId='entry';this._tab='none';this._v78Submitted=null;this._v78Busy=false;this.calls=[];this.context='one';}
 _prefKey(){return this.context;}
 _uiIngredientLanguage(){return 'el';}
 _v78Alive(c){return !!c&&c===this._v78Dialog&&c.isConnected&&this._v78Context===this.context;}
 _v114Links(){return this._v78Draft.ingredientLinks;}
 _v78ProductExtras(){return {paid_price:{country:'DE'},extra:'preserved'};}
 _v78Fresh(){return {...fresh(),requestId:'fresh-'+Math.random()};}
 _v111CancelRead(){this._v111ReadToken={};}
 _v78StopCamera(){this.cameraStops=(this.cameraStops||0)+1;}
 _v78SetBusy(value){this._v78Busy=value;}
 _v78AcceptState(value){this.accepted=value;}
 _v78RenderCapture(){this.renders=(this.renders||0)+1;}
 _v111Paint(){}
 _api(type,data){this.calls.push([type,data]);return this.response?.(type,data)??Promise.resolve({houseIngredients:[]});}
 _v78Save(){this.delegated=true;return Promise.resolve();}
 _v78Close(force){if(!force&&this._v78Dirty){this._v78Discard=true;}else{this._v78Dialog=null;this._v78Draft=null;}}
 _v112Editor(open){this._v78Draft.editorOpen=open;}
 _r195LoadItem(){}
 _r195Action(action){this.receiptAction=action;return Promise.resolve();}
 _r195Current(){return this.receiptItem;}
 _r195Flush(){}
}
class Harness extends ProductEditorMixin(Boundary){
 _v196Decorate(){} // DOM integration is exercised separately in Chromium.
}

for(const [input,expected] of [['01234567','01234567'],[' 0123-4567 ','01234567'],['012345678901','012345678901'],['0123456789012','0123456789012'],['00123456789012','00123456789012'],['1e123456',null],['',null],['123456789',null],['123456789012345',null],['abc',null]])test(`barcode normalization ${JSON.stringify(input)}`,()=>assert.equal(editorBarcode(input),expected));
test('numeric parser keeps decimal comma and rejects blank, booleans and infinity through validation',()=>{
 assert.equal(editorNumber('1,5'),1.5);assert.ok(Number.isNaN(editorNumber('')));assert.ok(Number.isNaN(editorNumber(true)));
 for(const quantity of [0,-1,Infinity,'NaN',true,''])assert.equal(editorIssues({...valid(),quantity},[ingredient])[0].field,'quantity');
});
test('valid manual product permits optional barcode, expiry, storage, nutrients and paid price',()=>assert.deepEqual(editorIssues(valid(),[ingredient]),[]));
test('all invalid package counts are rejected',()=>{for(const packageCount of [0,-1,1.5,101,'',Infinity])assert.ok(editorIssues({...valid(),packageCount},[ingredient]).some(row=>row.field==='packageCount'));});
test('compatible ingredient assignment is required, not the barcode product name',()=>{
 assert.ok(editorIssues(valid(),[]).some(row=>row.field==='ingredient'));
 assert.ok(editorIssues(valid(),[{name:'no id'}]).some(row=>row.field==='ingredient'));
 assert.deepEqual(editorIssues(valid(),[ingredient,other]),[]);
});
test('invalid and leap dates are checked without creating a date',()=>{
 for(const purchaseDate of ['2026-02-29','2026-13-01','2026-04-31','yesterday'])assert.ok(editorIssues({...valid(),purchaseDate},[ingredient]).some(row=>row.field==='purchaseDate'));
 assert.deepEqual(editorIssues({...valid(),purchaseDate:'2024-02-29'},[ingredient]),[]);
});
test('receipt application requires purchase date but ordinary manual entry does not',()=>{
 assert.deepEqual(editorIssues({...valid(),purchaseDate:''},[ingredient]),[]);
 assert.ok(editorIssues({...valid(),purchaseDate:''},[ingredient],true).some(row=>row.field==='purchaseDate'));
});
test('no-expiry ignores obsolete expiry field',()=>assert.deepEqual(editorIssues({...valid(),noExpiry:true,bestBefore:'bad'},[ingredient]),[]));
test('optional opened days are validated',()=>{for(const useWithinDays of ['0','3651','1.5','bad'])assert.ok(editorIssues({...valid(),useWithinDays},[ingredient]).some(row=>row.field==='useWithinDays'));});
test('zero paid price is accepted; invalid prices and missing currencies are rejected',()=>{
 assert.deepEqual(editorIssues({...valid(),paidAmount:0,paidCurrency:'eur'},[ingredient]),[]);
 for(const paidAmount of [-1,'infinite'])assert.ok(editorIssues({...valid(),paidAmount},[ingredient]).some(row=>row.field==='paidAmount'));
 assert.ok(editorIssues({...valid(),paidAmount:2,paidCurrency:''},[ingredient]).some(row=>row.field==='paidCurrency'));
});
test('nutrient values need a known basis and valid non-negative numbers',()=>{
 assert.ok(editorIssues({...valid(),nutrition:{basisUnit:'',values:{protein:2}}},[ingredient]).some(row=>row.field==='nutritionBasis'));
 assert.ok(editorIssues({...valid(),nutrition:{basisUnit:'g',values:{protein:-2}}},[ingredient]).some(row=>row.field==='nutrient:protein'));
 assert.deepEqual(editorIssues({...valid(),nutrition:{basisUnit:'g',values:{protein:0}}},[ingredient]),[]);
});
test('paid-price basis on stock edits cannot be zero',()=>assert.ok(editorIssues({...valid(),editLotId:'lot1',paidAmount:2,paidBasisQuantity:0},[ingredient]).some(row=>row.field==='paidBasisQuantity')));
test('barcode result fills blanks and returns every compatible suggestion',()=>{
 const suggestions=Array.from({length:80},(_,i)=>({ingredient:{key:`id${i}`,name:`name${i}`}}));
 const d=fresh(),before=structuredClone(d);const out=mergeBarcodeDetails(d,{product:{productName:'Rice',quantity:1,unit:'kg',nutrition:{basisUnit:'g',values:{protein:7}}},suggestions});
 assert.equal(out.productName,'Rice');assert.equal(out.quantity,1);assert.equal(out.unit,'kg');assert.equal(out.suggestions.length,80);assert.equal(out.ingredient,null);assert.deepEqual(d,before);
});
test('lookup preserves remaining stock amount, lot revision, paid price, location and assignments',()=>{
 const d={...valid(),editLotId:'lot',expectedVersion:'revision',quantity:123,productName:'My rice',paidAmount:'2,49',storageLocationId:'shelf',containerId:'jar'};
 const out=mergeBarcodeDetails(d,{product:{productName:'New name',quantity:1,unit:'kg'},mapping:{ingredient:other}},[ingredient]);
 for(const field of ['editLotId','expectedVersion','quantity','unit','productName','paidAmount','storageLocationId','containerId'])assert.equal(out[field],d[field]);
 assert.deepEqual(out.ingredientLinks,[ingredient]);
});
test('lookup preserves unmatched drafts and nutrient bases',()=>{
 const d={...valid(),nutrition:{basisUnit:'ml',values:{protein:4}}};
 assert.deepEqual(mergeBarcodeDetails(d,{product:{nutrition:{basisUnit:'g',values:{protein:8}}}},[ingredient]).nutrition,d.nutrition);
 const unknown=mergeBarcodeDetails(d,{},[ingredient]);assert.equal(unknown.quantity,500);assert.deepEqual(unknown.ingredientLinks,[ingredient]);
});
test('existing nutrient values survive and same-basis missing values can be filled',()=>{
 const d={...valid(),nutrition:{basisUnit:'g',values:{protein:0}}};
 const out=mergeBarcodeDetails(d,{product:{nutrition:{basisUnit:'g',values:{protein:8,salt:.1}}}},[ingredient]);
 assert.equal(out.nutrition.values.protein,0);assert.equal(out.nutrition.values.salt,.1);
});
test('saved barcode mapping is used only without explicit selections',()=>assert.deepEqual(mergeBarcodeDetails(fresh(),{mapping:{ingredientLinks:[ingredient,other]}}).ingredientLinks,[ingredient,other]));
test('request uses existing product schema and preserves container/paid basis/aliases',()=>{
 const d={...valid(),quantity:'1,5',packageCount:2,barcode:'0123-4567',paidAmount:'2,49',paidCurrency:'eur',nutrition:{basisUnit:'g',values:{protein:'0',salt:'0,2'}},containerId:'jar'};
 const request=editorRequest(d,[ingredient,other],{paid_price:{country:'DE'},custom:'keep'},'entry','el');
 assert.equal(request.quantity,1.5);assert.equal(request.package_count,2);assert.equal(request.paid_price.amount,2.49);assert.equal(request.paid_price.currency,'EUR');assert.equal(request.paid_price.country,'DE');assert.equal(request.lot_metadata.containerId,'jar');assert.equal(request.lot_metadata.barcode,'01234567');assert.equal(request.ingredient_links.length,2);assert.equal(request.nutrition.values.salt,.2);assert.equal(request.custom,'keep');
});
test('edit request targets original lot with optimistic revision and paid basis',()=>{
 const request=editorRequest({...valid(),editLotId:'lot',expectedVersion:'v1',paidAmount:2,paidCurrency:'EUR',paidBasisQuantity:1000,paidBasisUnit:'g'},[ingredient],{},'entry','el');
 assert.equal(request.edit_lot_id,'lot');assert.equal(request.expected_version,'v1');assert.equal(request.paid_price.basisQuantity,1000);assert.equal(request.package_count,1);
});
test('blank paid amount stays absent, never becomes zero',()=>assert.equal(editorRequest(valid(),[ingredient],{paid_price:{}},'e','el').paid_price,undefined));
test('successful manual save resets to empty manual form with a new request ID',async()=>{
 const h=new Harness(),d=h._v78Draft;d.storageLocationId='old';d.containerId='jar';
 await h._v78Save();assert.equal(h.calls.length,1);assert.equal(h.calls[0][0],'cook4me/v33/product_add');
 assert.notEqual(h._v78Draft,d);assert.notEqual(h._v78Draft.requestId,d.requestId);assert.equal(h._v78Draft.mode,'manual');assert.equal(h._v78Draft.quantity,'');assert.equal(h._v78Draft.storageLocationId,'');assert.equal(h._v78Draft.containerId,'');assert.equal(h._v78Draft.ingredient,null);assert.equal(h._v78Submitted,null);assert.ok(h._v78Dialog);
});
test('successful edit does not close the dialog and clears its target',async()=>{
 const h=new Harness();h._v78Draft.editLotId='lot';h._v78Draft.expectedVersion='old';await h._v78Save();
 assert.equal(h.calls[0][1].edit_lot_id,'lot');assert.equal(h._v78Draft.editLotId,'');assert.ok(h._v78Dialog);
});
test('double-click save makes only one request',async()=>{
 const h=new Harness();let done;h.response=()=>new Promise(resolve=>done=resolve);const first=h._v78Save();await h._v78Save();assert.equal(h.calls.length,1);done({});await first;
});
test('network uncertainty retains frozen request and retry cannot duplicate the request ID',async()=>{
 const h=new Harness();h.response=()=>Promise.reject(new Error('connection lost'));await h._v78Save();const request=h._v78Submitted,id=request.request_id;
 h._v196Discard();assert.equal(h._v78Submitted,request);h._v78Close();assert.ok(h._v78Dialog);
 h.response=()=>Promise.resolve({});await h._v78Save();assert.equal(h.calls[1][1],request);assert.equal(h.calls[1][1].request_id,id);assert.equal(h._v78Submitted,null);
});
test('partial persistence warning retains retry instead of clearing the form',async()=>{
 const h=new Harness(),d=h._v78Draft;h.response=()=>Promise.resolve({warnings:['price not saved']});await h._v78Save();assert.equal(h._v78Draft,d);assert.ok(h._v78Submitted);assert.equal(h._v78Busy,false);
});
test('product validation error retains editable draft and clears submitted lock',async()=>{
 const h=new Harness(),d=h._v78Draft;h.response=()=>Promise.reject({code:'product_validation',message:'Invalid product'});await h._v78Save();assert.equal(h._v78Draft,d);assert.equal(h._v78Submitted,null);assert.equal(d.editorOpen,true);
});
test('discard of an edit only clears the draft; it never removes stock',()=>{
 const h=new Harness();h._v78Draft.editLotId='lot';h._v196Discard();assert.equal(h.calls.length,0);assert.equal(h._v78Draft.editLotId,'');assert.equal(h._v78Draft.mode,'manual');
});
test('save result from old entry cannot reset or update the current entry',async()=>{
 const h=new Harness();let done;h.response=()=>new Promise(resolve=>done=resolve);const pending=h._v78Save();h.context='two';const d=h._v78Draft=fresh();done({});await pending;assert.equal(h._v78Draft,d);assert.equal(h.accepted,undefined);
});
test('scan result view keeps inherited scanning save flow',async()=>{
 const h=new Harness();Object.assign(h._v78Draft,{mode:'barcode',editorOpen:false});await h._v78Save();assert.equal(h.delegated,true);assert.equal(h.calls.length,0);
});
test('receipt Save delegates and never resets the receipt session',async()=>{
 const h=new Harness();const s=h._r195Session={};await h._v78Save();assert.equal(h.delegated,true);assert.equal(h._r195Session,s);h._v196Reset('discarded');assert.equal(h._r195Session,s);
});
test('valid receipt Apply delegates; draft saves remain allowed when incomplete',async()=>{
 const h=new Harness();h.receiptItem={status:'pending'};await h._r195Action('apply');assert.equal(h.receiptAction,'apply');h._v78Draft=fresh();await h._r195Action('save');assert.equal(h.receiptAction,'save');
});
test('barcode lookup is explicit, supports locked edits, and never saves stock',async()=>{
 const h=new Harness();Object.assign(h._v78Draft,{barcode:'01234567',editLotId:'lot',productLocked:true,scanRecognized:true});h.response=()=>Promise.resolve({product:{productName:'Rice',found:true,quantity:1000,unit:'g'},suggestions:[]});
 await h._v196Lookup();assert.equal(h.calls.length,1);assert.equal(h.calls[0][0],'cook4me/v33/barcode_lookup');assert.equal(h.calls[0][1].barcode,'01234567');assert.equal(h._v78Draft.editLotId,'lot');assert.equal(h._v78Draft.quantity,500);assert.equal(h._v78Draft.editorOpen,true);
});
test('barcode lookup double click is serialized',async()=>{
 const h=new Harness();h._v78Draft.barcode='01234567';let done;h.response=()=>new Promise(resolve=>done=resolve);const p=h._v196Lookup();await h._v196Lookup();assert.equal(h.calls.length,1);done({});await p;
});
test('late barcode result cannot modify a replacement draft or focus it',async()=>{
 const h=new Harness();h._v78Draft.barcode='01234567';let done;h.response=()=>new Promise(resolve=>done=resolve);const p=h._v196Lookup();const replacement=h._v78Draft=fresh();done({product:{productName:'Old'}});await p;assert.equal(h._v78Draft,replacement);assert.equal(replacement.productName,'');
});
test('readonly receipt items cannot request barcode lookups',async()=>{
 const h=new Harness();h._r195Session={};h.receiptItem={status:'applied',kind:'product'};h._v78Draft.barcode='01234567';await h._v196Lookup();assert.equal(h.calls.length,0);
});
test('focus opens collapsed ancestors and focuses the requested field',()=>{
 const h=new Harness(),target=node(),details={tagName:'DETAILS',open:false,parentElement:h._v78Dialog};target.parentElement=details;h._v196Focus(target);flush();assert.equal(details.open,true);assert.equal(target.focused,1);
});
test('superseded focus callbacks cannot steal focus',()=>{
 const h=new Harness(),old=node(),current=node();h._v196Focus(old);h._v196Focus(current);flush();assert.equal(old.focused,0);assert.equal(current.focused,1);
});
test('stale focus cannot follow a changed product or closed dialog',()=>{
 const h=new Harness(),target=node();h._v196Focus(target);h._v78Draft=fresh();flush();assert.equal(target.focused,0);h._v196Focus(target);h._v78Close(true);flush();assert.equal(target.focused,0);
});
test('X focuses the required keep/discard confirmation rather than disappearing',()=>{
 const h=new Harness(),keep=node();h._v78Dialog.querySelector=s=>s==='[data-v78-keep]'?keep:null;h._v78Dirty=true;h._v78Close();flush();assert.equal(h._v78Discard,true);assert.equal(keep.focused,1);
});
test('back-to-camera cannot unlock an in-flight or uncertain save',()=>{
 const h=new Harness();h._v78Busy=true;h._v112Editor(false);assert.equal(h._v78Draft.editorOpen,true);h._v78Busy=false;h._v78Submitted={};h._v112Editor(false);assert.equal(h._v78Draft.editorOpen,true);
});
test('all editor labels are provided in Greek German and English',()=>{for(const lang of ['el','de'])assert.deepEqual(Object.keys(EDITOR_TEXT[lang]).sort(),Object.keys(EDITOR_TEXT.en).sort());});
test('unlimited manual stock keeps its established semantics without fabricated package prices',()=>{
 const d={...fresh(),unlimited:true,unit:'',paidAmount:'bad',paidCurrency:'',nutrition:{basisUnit:'bad',values:{protein:-1}}};
 assert.deepEqual(editorIssues(d,[ingredient]),[]);
 const request=editorRequest(d,[ingredient],{unlimited:true},'entry','el');
 assert.equal(request.unlimited,true);assert.equal(request.package_count,1);assert.equal(request.quantity,1);assert.equal(request.unit,'pcs');assert.equal(request.paid_price,undefined);assert.equal(request.nutrition,undefined);
});
test('unlimited stock must still have a valid ingredient and optional barcode',()=>{
 assert.ok(editorIssues({...fresh(),unlimited:true,barcode:'wrong'},[]).some(row=>row.field==='barcode'));
 assert.ok(editorIssues({...fresh(),unlimited:true},[]).some(row=>row.field==='ingredient'));
});
test('receipt actions do not validate or change draft during another pending operation',async()=>{
 const h=new Harness();h._v78Busy=true;h.receiptItem={status:'pending',kind:'product'};h._v78Draft=fresh();await h._r195Action('apply');assert.equal(h.receiptAction,undefined);assert.equal(h._v78Draft.scanPhase,undefined);
});
test('not-found barcode is not used as a fabricated product name',()=>{
 const d={...fresh(),barcode:'01234567'};
 const out=mergeBarcodeDetails(d,{barcode:d.barcode,product:{found:false,name:d.barcode}});
 assert.equal(out.productName,'');
});
test('generic product names and mapping-only names remain available',()=>{
 assert.equal(mergeBarcodeDetails(fresh(),{product:{genericName:'Rice'}}).productName,'Rice');
 assert.equal(mergeBarcodeDetails(fresh(),{mapping:{ingredientLinks:[ingredient]}}).productName,ingredient.name);
});
