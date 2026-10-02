import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {stockSearchText,stockMatches,stockNameCompare,KitchenStockScanMixin} from '../custom_components/cook4me/frontend/kitchen-stock-scan-v271.js';

test('home-stock search ignores case/accents, supports Greek final sigma and all query words',()=>{
 assert.equal(stockMatches('Kokosmilch (Γάλα καρύδας)','ΓΑΛΑ καρυδασ'),true);
 assert.equal(stockMatches('Crème (κρέμα)','creme'),true);
 assert.equal(stockMatches('Weiße Bohnen','weisse'),true);
 assert.equal(stockMatches('Tomaten Stücke (Ντομάτα κονσέρβας)','tom stuc'),true);
 assert.equal(stockMatches('Kokosmilch (Γάλα καρύδας)','Kidney'),false);
 assert.equal(stockSearchText('  ΆΛΑΣ  '),'αλασ');
});

test('alphabetical sorting is locale-aware, case-insensitive and numeric',()=>{
 assert.deepEqual(['Tomaten','Kokosmilch','Chili','Kidneybohnen'].sort(stockNameCompare('el')),['Chili','Kidneybohnen','Kokosmilch','Tomaten']);
 assert.deepEqual(['Ζάχαρη','Καρύδα','Αλάτι'].sort(stockNameCompare('el')),['Αλάτι','Ζάχαρη','Καρύδα']);
 assert.deepEqual(['Zucker','Äpfel','Apfel 10','Apfel 2'].sort(stockNameCompare('de')),['Äpfel','Apfel 2','Apfel 10','Zucker']);
 assert.doesNotThrow(()=>stockNameCompare('invalid locale')('a','b'));
});

class Base{
 _v78SetBusy(value){this._v78Busy=value;}
 _v111NewDraft(mode){return this._v78Draft={mode};}
 _v78Save(){this.saveDraft=this._v196SavingDraft;}
 _v196Reset(message){this.resetMessage=message;}
 _prefKey(){return this.context||'a';}
}
const Panel=KitchenStockScanMixin(Base);

test('only product scan reads set the return mode, not manual/auxiliary/receipt/edit',()=>{
 const p=new Panel();
 for(const d of [{mode:'manual',scanPhase:'looking'}, {mode:'barcode',scanPhase:'looking',editorOpen:true}, {mode:'product',scanPhase:'reading',editLotId:'lot'}, {mode:'date',scanPhase:'reading'}]){
  p._v78Draft=d;p._v78SetBusy(true);assert.ok(!p._v271ReturnMode());
 }
 for(const mode of ['barcode','product']){
  p._v78Draft={mode,scanPhase:mode==='barcode'?'looking':'reading'};
  p._v78SetBusy(true);assert.equal(p._v271ReturnMode(),mode);
  p._v78SetBusy(false);p._v78Save();assert.equal(p.saveDraft,p._v78Draft);
  p._v111NewDraft('nutrition');assert.equal(p._v271ReturnMode(),mode);
  p._v196Reset('discarded');assert.equal(p.resetMessage,'discarded');
  p._v111NewDraft('barcode');assert.ok(!p._v271ReturnMode());
 }
 p._r195Session={};p._v78Draft={mode:'product',scanPhase:'reading'};p._v78SetBusy(true);assert.equal(p._v271ReturnMode(),null);
});

test('home-stock query cannot leak across household/user contexts',()=>{
 const p=new Panel();p._v271StockState().query='rice';assert.equal(p._v271StockState().query,'rice');
 p.context='b';assert.equal(p._v271StockState().query,'');
});

test('active runtime includes stock/search/scan continuation with cache busting',()=>{
 const root=new URL('../custom_components/cook4me/',import.meta.url);
 const panel=readFileSync(new URL('frontend/cook4me-panel-v180.js',root),'utf8');
 const registration=readFileSync(new URL('panel.py',root),'utf8');
 assert.match(panel,/KitchenStockScanMixin\(ProductCatalogMixin\(MobileProductMixin/);
 assert.match(registration,/_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v272"/);
 assert.match(registration,/stockscan=271/);
});
