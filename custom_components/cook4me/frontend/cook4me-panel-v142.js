const V141='cook4me-recipe-hub-panel-v141';
if(!customElements.get(V141))await import('./cook4me-panel-v141.js?v=2026.9.21.6');
const BasePanel=customElements.get(V141);

const V142_TEXT={
 en:{
  packages:'Packages',stockValue:'Stock value',priced:'priced',exactPrices:'exact purchases',
  stockNutrition:'Nutrients currently in stock',nutritionCoverage:'nutrition coverage',
  expiring:'Expiring within 7 days',expiringHelp:'Physical products whose effective expiry is within the next 7 days. Expired products are shown first.',
  expiringCount:'Expiring soon',noneExpiring:'No products expire within the next 7 days.',
  expired:'Expired {days} day(s) ago',today:'Expires today',tomorrow:'Expires tomorrow',inDays:'Expires in {days} days',
  openedLimit:'opened-package limit',noLocation:'No storage place',loading:'Calculating stock totals…',summaryError:'Stock totals could not be loaded.'
 },
 de:{
  packages:'Packungen',stockValue:'Vorratswert',priced:'mit Preis',exactPrices:'exakte Käufe',
  stockNutrition:'Nährstoffe im aktuellen Vorrat',nutritionCoverage:'Nährwertabdeckung',
  expiring:'Läuft innerhalb von 7 Tagen ab',expiringHelp:'Physische Produkte, deren effektives Ablaufdatum in den nächsten 7 Tagen liegt. Abgelaufene Produkte stehen zuerst.',
  expiringCount:'Bald ablaufend',noneExpiring:'In den nächsten 7 Tagen läuft kein Produkt ab.',
  expired:'Seit {days} Tag(en) abgelaufen',today:'Läuft heute ab',tomorrow:'Läuft morgen ab',inDays:'Läuft in {days} Tagen ab',
  openedLimit:'Frist nach dem Öffnen',noLocation:'Kein Lagerort',loading:'Vorratssummen werden berechnet…',summaryError:'Vorratssummen konnten nicht geladen werden.'
 },
 el:{
  packages:'Συσκευασίες',stockValue:'Αξία αποθέματος',priced:'με τιμή',exactPrices:'ακριβείς αγορές',
  stockNutrition:'Θρεπτικά στοιχεία στο τρέχον απόθεμα',nutritionCoverage:'κάλυψη θρεπτικών',
  expiring:'Λήγουν μέσα σε 7 ημέρες',expiringHelp:'Φυσικά προϊόντα των οποίων η πραγματική ημερομηνία λήξης είναι μέσα στις επόμενες 7 ημέρες. Τα ήδη ληγμένα εμφανίζονται πρώτα.',
  expiringCount:'Λήγουν σύντομα',noneExpiring:'Κανένα προϊόν δεν λήγει μέσα στις επόμενες 7 ημέρες.',
  expired:'Έληξε πριν από {days} ημέρα/ημέρες',today:'Λήγει σήμερα',tomorrow:'Λήγει αύριο',inDays:'Λήγει σε {days} ημέρες',
  openedLimit:'όριο μετά το άνοιγμα',noLocation:'Χωρίς χώρο αποθήκευσης',loading:'Υπολογισμός συνόλων αποθέματος…',summaryError:'Δεν ήταν δυνατή η φόρτωση των συνόλων αποθέματος.'
 }
};

class Cook4MeRecipeHubPanelV142 extends BasePanel{
 _v142Text(key){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return (V142_TEXT[lang]||V142_TEXT.en)[key]||V142_TEXT.en[key]||key;
 }
 _v142StockFingerprint(){
  return JSON.stringify((this._houseIngredients||[]).map(row=>[
   this._stockIdentity?.(row)||row?.key||row?.name||'',!!row?.unlimited,row?.quantity,row?.unit,
   (row?.lots||[]).map(lot=>[lot?.id,lot?.quantity,lot?.bestBefore,lot?.effectiveBestBefore,lot?.barcode,lot?.revision])
  ]));
 }
 async _v142LoadStockSummary(force=false){
  if(!this._entryId||this._v142StockSummaryLoading)return;
  const fingerprint=this._v142StockFingerprint(),fresh=Date.now()-(this._v142StockSummaryAt||0)<60000;
  if(!force&&this._v142StockSummary&&this._v142StockSummaryFingerprint===fingerprint&&fresh)return;
  const context=this._prefKey();this._v142StockSummaryLoading=true;this._v142StockSummaryError='';this._v142PaintStockSummary();
  try{
   const result=await this._api('cook4me/v39/stock_summary',{entry_id:this._entryId});
   if(context!==this._prefKey())return;
   this._v142StockSummary=result||{};this._v142StockSummaryFingerprint=this._v142StockFingerprint();this._v142StockSummaryAt=Date.now();
  }catch(error){
   if(context===this._prefKey())this._v142StockSummaryError=String(error?.message||error||this._v142Text('summaryError'));
  }finally{
   if(context===this._prefKey()){this._v142StockSummaryLoading=false;this._v142PaintStockSummary();}
  }
 }
 _v142Money(values){
  const totals=values&&typeof values==='object'?values:{};
  if(!Object.keys(totals).length)return '—';
  try{return this._v79Money(totals);}catch(_error){}
  return Object.entries(totals).map(([currency,value])=>`${this._shownNumber(value)} ${currency}`).join(' · ');
 }
 _v142Coverage(done,total,label){
  return `${done||0} / ${total||0} ${label}`;
 }
 _v142RelativeExpiry(row){
  const days=Number(row?.daysRemaining);
  if(!Number.isFinite(days))return '';
  const replace=(key,value)=>this._v142Text(key).replace('{days}',String(value));
  if(days<0)return replace('expired',Math.abs(days));
  if(days===0)return this._v142Text('today');
  if(days===1)return this._v142Text('tomorrow');
  return replace('inDays',days);
 }
 _v142Date(value){
  const text=String(value||'');if(!text)return '';
  try{
   return new Intl.DateTimeFormat(this._langCode?.()||undefined,{year:'numeric',month:'short',day:'numeric'}).format(new Date(text+'T12:00:00'));
  }catch(_error){return text;}
 }
 _v142MountStock(c){
  const kitchen=c?.querySelector?.('[data-v78-kitchen]')||c;
  const stock=kitchen?.querySelector?.('[data-v78-section="stock"]'),launch=stock?.querySelector?.('.v78-launch');
  if(!stock||!launch)return;
  let summary=launch.querySelector('[data-v142-stock-summary]');
  if(!summary){
   summary=document.createElement('div');summary.dataset.v142StockSummary='';summary.className='v142-stock-summary';
   const actions=launch.querySelector('.v78-actions');if(actions)actions.after(summary);else launch.append(summary);
  }
  let expiry=stock.querySelector('[data-v142-expiry]');
  if(!expiry){
   expiry=document.createElement('section');expiry.className='card v142-expiry';expiry.dataset.v142Expiry='';
   const inventory=stock.querySelector('[data-v78-inventory]');if(inventory)inventory.before(expiry);else launch.after(expiry);
  }
  this._v142PaintStockSummary(kitchen);
 }
 _v142PaintStockSummary(root=this.shadowRoot){
  const summaryNode=root?.querySelector?.('[data-v142-stock-summary]'),expiryNode=root?.querySelector?.('[data-v142-expiry]');
  if(!summaryNode||!expiryNode)return;
  const e=value=>this._escape(String(value??''));
  if(this._v142StockSummaryLoading&&!this._v142StockSummary){
   summaryNode.innerHTML=`<div class="v142-loading"><span class="v142-mini-ring"></span><span>${e(this._v142Text('loading'))}</span></div>`;
   expiryNode.innerHTML=`<div class="v142-loading"><span class="v142-mini-ring"></span><span>${e(this._v142Text('loading'))}</span></div>`;return;
  }
  if(this._v142StockSummaryError&&!this._v142StockSummary){
   const message=e(this._v142StockSummaryError||this._v142Text('summaryError'));
   summaryNode.innerHTML=`<div class="muted v142-summary-error">${message}</div>`;
   expiryNode.innerHTML=`<h2><ha-icon icon="mdi:calendar-alert"></ha-icon>${e(this._v142Text('expiring'))}</h2><p class="muted">${message}</p>`;return;
  }
  const data=this._v142StockSummary||{},value=data.value||{},nutrition=data.nutrition||{},expiring=Array.isArray(data.expiring)?data.expiring:[];
  const valueText=this._v142Money(value.totalsByCurrency||{});
  const nutritionHtml=this._nutritionChips?.(nutrition.totals||{},true)||'';
  summaryNode.innerHTML=`
   <div class="v142-summary-grid">
    <div class="v142-summary-stat"><ha-icon icon="mdi:package-variant-closed"></ha-icon><span><small>${e(this._v142Text('packages'))}</small><strong>${e(data.packageCount||0)}</strong></span></div>
    <div class="v142-summary-stat"><ha-icon icon="mdi:cash-multiple"></ha-icon><span><small>${e(this._v142Text('stockValue'))}</small><strong>${e(valueText)}</strong><em>${e(this._v142Coverage(value.pricedPackages,value.packageCount,this._v142Text('priced')))} · ${e(value.exactPackages||0)} ${e(this._v142Text('exactPrices'))}</em></span></div>
    <div class="v142-summary-stat ${expiring.length?'v142-summary-warning':''}"><ha-icon icon="mdi:calendar-alert"></ha-icon><span><small>${e(this._v142Text('expiringCount'))}</small><strong>${e(expiring.length)}</strong></span></div>
   </div>
   <div class="v142-stock-nutrition"><div class="v142-stock-nutrition-head"><ha-icon icon="mdi:nutrition"></ha-icon><strong>${e(this._v142Text('stockNutrition'))}</strong><small>${e(this._v142Coverage(nutrition.coveredPackages,nutrition.packageCount,this._v142Text('nutritionCoverage')))}</small></div><div class="chips v142-stock-nutrient-chips">${nutritionHtml||'<span class="muted">—</span>'}</div></div>`;

  expiryNode.innerHTML=`<div class="v142-expiry-head"><div><h2><ha-icon icon="mdi:calendar-alert"></ha-icon>${e(this._v142Text('expiring'))}</h2><p class="muted">${e(this._v142Text('expiringHelp'))}</p></div><span class="v142-expiry-badge">${e(expiring.length)}</span></div>${expiring.length?`<div class="v142-expiry-list">${expiring.map((row,index)=>this._v142ExpiryRow(row,index)).join('')}</div>`:`<div class="v142-expiry-empty"><ha-icon icon="mdi:calendar-check-outline"></ha-icon><span>${e(this._v142Text('noneExpiring'))}</span></div>`}`;
  expiryNode.querySelectorAll('[data-v142-expiry-lot]').forEach(button=>button.onclick=()=>{const id=button.dataset.v142ExpiryLot;if(id)void this._v112EditLot(id);});
 }
 _v142ExpiryRow(row,index){
  const e=value=>this._escape(String(value??'')),name=row.productName||row.ingredientName||'',ingredient=row.ingredientName&&row.ingredientName!==name?row.ingredientName:'';
  const amount=row.quantity!==undefined&&row.quantity!==null?this._displayAmount(row.quantity,row.unit):'';
  const relative=this._v142RelativeExpiry(row),stamp=this._v142Date(row.effectiveBestBefore||row.bestBefore);
  const location=row.storageName||this._v142Text('noLocation'),opened=row.openedDrivenExpiry?this._v142Text('openedLimit'):'';
  const cls=row.pastBestBefore?'v142-expired':Number(row.daysRemaining)<=1?'v142-urgent':'';
  const tag=row.lotId?'button':'div',attr=row.lotId?`type="button" data-v142-expiry-lot="${e(row.lotId)}"`:'';
  return `<${tag} ${attr} class="v142-expiry-row ${cls}" data-v142-index="${index}"><span class="v142-expiry-icon"><ha-icon icon="mdi:${row.pastBestBefore?'alert-circle':'package-variant-closed'}"></ha-icon></span><span class="v142-expiry-product"><strong>${e(name)}</strong>${ingredient?`<small>${e(ingredient)}</small>`:''}${row.brand?`<small>${e(row.brand)}</small>`:''}</span><span class="v142-expiry-meta"><span>${e(amount)}</span><span><ha-icon icon="mdi:map-marker-outline"></ha-icon>${e(location)}</span></span><span class="v142-expiry-date"><strong>${e(stamp)}</strong><small>${e(relative)}${opened?` · ${e(opened)}`:''}</small></span>${row.lotId?'<ha-icon class="v142-edit-chevron" icon="mdi:chevron-right"></ha-icon>':''}</${tag}>`;
 }
 _renderProfile(c){
  super._renderProfile(c);this._v142Styles();this._v142MountStock(c);queueMicrotask(()=>void this._v142LoadStockSummary());
 }
 _renderTab(){
  const result=super._renderTab();this._v142Styles();this.setAttribute('data-cook4me-build','2026.9.21.7');return result;
 }
 _v142Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v142Styles'))return;
  const style=document.createElement('style');style.id='v142Styles';style.textContent=`
   .v142-stock-summary{margin-top:18px;max-width:900px}.v142-summary-grid{display:grid;grid-template-columns:minmax(120px,.7fr) minmax(220px,1.3fr) minmax(130px,.75fr);gap:9px}.v142-summary-stat{display:flex;align-items:center;gap:10px;padding:11px 13px;border:1px solid var(--divider-color);border-radius:13px;background:color-mix(in srgb,var(--card-background-color) 72%,transparent);min-width:0}.v142-summary-stat>ha-icon{color:var(--primary-color);flex:0 0 auto}.v142-summary-stat>span{display:flex;flex-direction:column;min-width:0}.v142-summary-stat small{color:var(--secondary-text-color);font-size:.75rem}.v142-summary-stat strong{font-size:1.05rem;overflow-wrap:anywhere}.v142-summary-stat em{font-style:normal;color:var(--secondary-text-color);font-size:.7rem;line-height:1.3;margin-top:2px}.v142-summary-warning>ha-icon{color:#ffb74d}.v142-stock-nutrition{margin-top:9px;padding:11px 13px;border:1px solid var(--divider-color);border-radius:13px;background:color-mix(in srgb,var(--card-background-color) 72%,transparent)}.v142-stock-nutrition-head{display:flex;align-items:center;gap:8px}.v142-stock-nutrition-head>ha-icon{color:var(--primary-color)}.v142-stock-nutrition-head small{margin-left:auto;color:var(--secondary-text-color)}.v142-stock-nutrient-chips{margin-top:8px;gap:7px}
   .v142-expiry{margin-top:18px!important}.v142-expiry-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}.v142-expiry-head h2{display:flex;align-items:center;gap:9px}.v142-expiry-head h2 ha-icon{color:#ffb74d}.v142-expiry-head p{margin:5px 0 0}.v142-expiry-badge{display:inline-flex;align-items:center;justify-content:center;min-width:34px;height:34px;padding:0 9px;border-radius:17px;background:color-mix(in srgb,#ffb74d 18%,transparent);border:1px solid color-mix(in srgb,#ffb74d 55%,transparent);font-weight:750}.v142-expiry-list{display:grid;gap:8px;margin-top:16px}.v142-expiry-row{display:grid;grid-template-columns:auto minmax(190px,1.5fr) minmax(130px,.8fr) minmax(190px,1fr) auto;align-items:center;gap:12px;width:100%;box-sizing:border-box;padding:13px 14px;border:1px solid var(--divider-color);border-radius:13px;background:var(--card-background-color);color:var(--primary-text-color);text-align:left;font:inherit}.v142-expiry-row[type=button]{cursor:pointer}.v142-expiry-row[type=button]:hover{border-color:color-mix(in srgb,var(--primary-color) 60%,var(--divider-color));background:color-mix(in srgb,var(--primary-color) 5%,var(--card-background-color))}.v142-expiry-icon{display:flex;padding:8px;border-radius:10px;background:color-mix(in srgb,#ffb74d 12%,transparent);color:#ffb74d}.v142-expiry-product,.v142-expiry-meta,.v142-expiry-date{display:flex;flex-direction:column;min-width:0;gap:3px}.v142-expiry-product strong{overflow-wrap:anywhere}.v142-expiry-product small,.v142-expiry-date small,.v142-expiry-meta{color:var(--secondary-text-color);font-size:.8rem}.v142-expiry-meta>span:last-child{display:flex;align-items:center;gap:4px}.v142-expiry-meta ha-icon{--mdc-icon-size:15px}.v142-expiry-date strong{font-size:.88rem}.v142-expired{border-color:color-mix(in srgb,#ff5252 58%,var(--divider-color));background:color-mix(in srgb,#ff5252 7%,var(--card-background-color))}.v142-expired .v142-expiry-icon,.v142-expired .v142-expiry-date strong{color:#ff6b6b}.v142-urgent:not(.v142-expired){border-color:color-mix(in srgb,#ffb74d 65%,var(--divider-color))}.v142-edit-chevron{color:var(--secondary-text-color)}.v142-expiry-empty{display:flex;align-items:center;justify-content:center;gap:10px;min-height:82px;margin-top:12px;border:1px dashed var(--divider-color);border-radius:13px;color:var(--secondary-text-color)}.v142-loading{display:flex;align-items:center;gap:9px;color:var(--secondary-text-color);padding:10px 0}.v142-mini-ring{display:inline-block;width:18px;height:18px;border:2px solid color-mix(in srgb,var(--secondary-text-color) 35%,transparent);border-top-color:var(--secondary-text-color);border-radius:50%;animation:v142spin .8s linear infinite}
   .v131-history-main>strong+.muted{margin-left:12px}
   @keyframes v142spin{to{transform:rotate(360deg)}}@media(max-width:900px){.v142-summary-grid{grid-template-columns:1fr 1fr}.v142-summary-grid>.v142-summary-stat:last-child{grid-column:1/-1}.v142-expiry-row{grid-template-columns:auto minmax(0,1fr) auto}.v142-expiry-meta,.v142-expiry-date{grid-column:2}.v142-edit-chevron{grid-column:3;grid-row:1/4}}@media(max-width:620px){.v142-summary-grid{grid-template-columns:1fr}.v142-summary-grid>.v142-summary-stat:last-child{grid-column:auto}.v142-stock-nutrition-head{align-items:flex-start;flex-wrap:wrap}.v142-stock-nutrition-head small{width:100%;margin-left:32px}.v142-expiry-head{align-items:center}.v142-expiry-row{padding:11px}.v131-history-main>strong+.muted{display:inline-block;margin-left:10px}}@media(prefers-reduced-motion:reduce){.v142-mini-ring{animation-duration:2s}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v142',Cook4MeRecipeHubPanelV142);
