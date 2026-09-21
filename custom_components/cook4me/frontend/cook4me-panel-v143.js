const V142='cook4me-recipe-hub-panel-v142';
if(!customElements.get(V142))await import('./cook4me-panel-v142.js?v=2026.9.21.7');
const BasePanel=customElements.get(V142);

const V143_TEXT={
 en:{
  paidExact:'Paid price · exact package',barcodeObservation:'Same-barcode price observation',previousPurchase:'Estimate from a previous purchase',
  categoryEstimate:'Category estimate',ingredientEstimate:'Ingredient estimate',manualReference:'Manual price reference',
  publicObservation:'Public price observation',offlineSnapshot:'Bundled price snapshot',retailSnapshot:'Retail price snapshot',
  sourceProvider:'Source',observedToday:'observed today',observedYesterday:'observed yesterday',observedDays:'observed {days} days ago',
  updatedToday:'updated today',updatedYesterday:'updated yesterday',updatedDays:'updated {days} days ago',
  estimatedPrices:'estimated prices',eta:'Estimated remaining',estimatingEta:'Estimating remaining time…',
  lessThan5s:'less than 5 s'
 },
 de:{
  paidExact:'Bezahlter Preis · exakte Packung',barcodeObservation:'Preisbeobachtung mit gleichem Barcode',previousPurchase:'Schätzung aus einem früheren Kauf',
  categoryEstimate:'Kategorie-Schätzung',ingredientEstimate:'Zutaten-Schätzung',manualReference:'Manuelle Preisreferenz',
  publicObservation:'Öffentliche Preisbeobachtung',offlineSnapshot:'Mitgelieferter Preis-Snapshot',retailSnapshot:'Einzelhandels-Preis-Snapshot',
  sourceProvider:'Quelle',observedToday:'heute beobachtet',observedYesterday:'gestern beobachtet',observedDays:'vor {days} Tagen beobachtet',
  updatedToday:'heute aktualisiert',updatedYesterday:'gestern aktualisiert',updatedDays:'vor {days} Tagen aktualisiert',
  estimatedPrices:'geschätzte Preise',eta:'Geschätzte Restzeit',estimatingEta:'Restzeit wird geschätzt…',
  lessThan5s:'unter 5 s'
 },
 el:{
  paidExact:'Τιμή αγοράς · ακριβής συσκευασία',barcodeObservation:'Παρατήρηση τιμής με ίδιο barcode',previousPurchase:'Εκτίμηση από προηγούμενη αγορά',
  categoryEstimate:'Εκτίμηση κατηγορίας',ingredientEstimate:'Εκτίμηση υλικού',manualReference:'Χειροκίνητη αναφορά τιμής',
  publicObservation:'Δημόσια παρατήρηση τιμής',offlineSnapshot:'Ενσωματωμένο στιγμιότυπο τιμών',retailSnapshot:'Στιγμιότυπο τιμών λιανικής',
  sourceProvider:'Πηγή',observedToday:'παρατήρηση σήμερα',observedYesterday:'παρατήρηση χθες',observedDays:'παρατήρηση πριν από {days} ημέρες',
  updatedToday:'ενημερώθηκε σήμερα',updatedYesterday:'ενημερώθηκε χθες',updatedDays:'ενημερώθηκε πριν από {days} ημέρες',
  estimatedPrices:'εκτιμώμενες τιμές',eta:'Εκτιμώμενος χρόνος που απομένει',estimatingEta:'Υπολογισμός υπολειπόμενου χρόνου…',
  lessThan5s:'λιγότερο από 5 δ'
 }
};

class Cook4MeRecipeHubPanelV143 extends BasePanel{
 _v143Text(key){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return (V143_TEXT[lang]||V143_TEXT.en)[key]||V143_TEXT.en[key]||key;
 }

 // ---------- Price provenance ----------
 _v143PriceSourceInfo(reference,matchKind=''){
  const ref=reference||{},source=String(ref.source||''),confidence=String(ref.confidence||''),identity=String(ref.identity||'');
  if(source==='purchase'||confidence==='exact_purchase')return {key:'paidExact',icon:'receipt-text-check-outline',tone:'exact'};
  if(source==='purchase_reference')return {key:'previousPurchase',icon:'history',tone:'estimate'};
  if(source==='manual'||confidence==='user_entered'&&!source.startsWith('open_prices'))return {key:'manualReference',icon:'pencil-outline',tone:'manual'};
  const barcode=matchKind==='barcode'||identity.startsWith('barcode:')||Boolean(ref.barcode)&&source!=='open_prices_category';
  if(barcode)return {key:'barcodeObservation',icon:'barcode-scan',tone:'barcode'};
  if(source==='open_prices_category'||source==='retail_snapshot'||source==='utility_snapshot')return {key:'categoryEstimate',icon:'shape-outline',tone:'estimate'};
  if(source.startsWith('open_prices')||confidence==='external_observation')return {key:'ingredientEstimate',icon:'chart-line',tone:'estimate'};
  return {key:'ingredientEstimate',icon:'chart-line',tone:'estimate'};
 }
 _v143Provider(reference){
  const source=String(reference?.source||'');
  if(source==='retail_snapshot')return this._v143Text('retailSnapshot');
  if(source==='utility_snapshot')return this._v143Text('offlineSnapshot');
  if(source.startsWith('open_prices'))return 'Open Prices';
  if(source==='purchase'||source==='purchase_reference')return this._v143Text(source==='purchase'?'paidExact':'previousPurchase');
  if(source==='manual')return this._v143Text('manualReference');
  return source||this._v143Text('publicObservation');
 }
 _v143DateAge(reference){
  const raw=String(reference?.date||reference?.updatedAt||'').trim();if(!raw)return '';
  const observed=Boolean(reference?.date),stamp=new Date(/^\d{4}-\d{2}-\d{2}$/.test(raw)?raw+'T12:00:00':raw);
  if(!Number.isFinite(stamp.getTime()))return raw;
  const now=new Date(),days=Math.max(0,Math.floor((now.getTime()-stamp.getTime())/86400000));
  const key=observed?(days===0?'observedToday':days===1?'observedYesterday':'observedDays'):(days===0?'updatedToday':days===1?'updatedYesterday':'updatedDays');
  return this._v143Text(key).replace('{days}',String(days));
 }
 _v143PriceMeta(reference){
  const ref=reference||{},items=[];
  if(ref.location)items.push(String(ref.location));
  const age=this._v143DateAge(ref);if(age)items.push(age);
  if(ref.country)items.push(String(ref.country).toUpperCase());
  if(ref.productName)items.push(String(ref.productName));
  return items;
 }
 _v143CompactPriceSource(reference,matchKind=''){
  if(!reference)return '';
  const info=this._v143PriceSourceInfo(reference,matchKind),meta=this._v143PriceMeta(reference);
  return [this._v143Text(info.key),...meta.slice(0,2)].filter(Boolean).join(' · ');
 }
 _v79Reference(reference,matchKind=''){
  if(!reference)return '';
  const e=value=>this._escape(String(value??'')),info=this._v143PriceSourceInfo(reference,matchKind),meta=this._v143PriceMeta(reference),provider=this._v143Provider(reference);
  const basis=reference.currency&&reference.amount!==undefined&&reference.basisQuantity!==undefined
   ?`${this._v79Money({[reference.currency]:reference.amount})} / ${this._displayAmount(reference.basisQuantity,reference.basisUnit)}`:'';
  const link=reference.observationId&&/^\d+$/.test(String(reference.observationId))
   ?`<a href="https://prices.openfoodfacts.org/prices/${e(reference.observationId)}" target="_blank" rel="noopener noreferrer">${e(provider)}</a>`
   :e(provider);
  return `<small class="v79-source v143-price-source"><span class="v143-price-kind v143-price-${e(info.tone)}"><ha-icon icon="mdi:${e(info.icon)}" aria-hidden="true"></ha-icon><strong>${e(this._v143Text(info.key))}</strong></span>${meta.length?`<span class="v143-price-meta">${meta.map(item=>`<span>${e(item)}</span>`).join('')}</span>`:''}${basis?`<span class="v143-price-basis">${e(this._v79Text('basis'))}: ${e(basis)}</span>`:''}<span class="v143-price-provider">${e(this._v143Text('sourceProvider'))}: ${link}</span></small>`;
 }
 _v79PaintProduct(){
  const d=this._v78Draft,node=this._v78Dialog?.querySelector('[data-v79-estimate]');if(!d||!node)return;
  const t=k=>this._escape(this._v79Text(k)),r=d.priceResult,ref=r?.reference;
  if(d.priceLoading){node.innerHTML=`<p>${t('looking')}</p>`;return;}
  if(d.priceError){node.innerHTML=`<p>${this._escape(d.priceError)}</p><button type="button" class="btn secondary" data-v79-reprice>${t('retry')}</button>`;node.querySelector('[data-v79-reprice]').onclick=()=>{d.priceKey='';void this._v79PriceProduct();};return;}
  if(!r){node.innerHTML=`<p class="muted">${t('assign')}</p>`;return;}
  node.innerHTML=ref?`<div class="v79-price-value"><span>${t(r.matchKind==='ingredient'?'ingredientEstimate':'estimate')}</span><strong>${r.estimate!==null&&r.estimate!==undefined?this._escape(this._v79Money({[ref.currency]:r.estimate})):'—'}</strong></div>${this._v79Reference(ref,r.matchKind)}${r.status==='basis_missing'?`<p class="muted">${t('basis_missing')}</p>`:''}`:`<p class="muted">${t(['choose_country','automatic_disabled','source_unavailable'].includes(r.status)?r.status:'none')}</p><button type="button" class="btn secondary" data-v79-reprice>${t('retry')}</button>`;
  node.querySelector('[data-v79-reprice]')?.addEventListener('click',()=>{d.priceKey='';void this._v79PriceProduct();});
 }
 _v112PaintPrice(){
  const d=this._v78Draft,node=this._v78Dialog?.querySelector('[data-v112-price-summary]');if(!node||!d)return;
  const r=d.priceResult,ref=r?.reference;
  if(d.paidAmount!==''){
   const shop=d.paidShop?` · ${d.paidShop}`:'';
   node.textContent=`${this._v79Text('paid')}: ${this._v79Money({[d.paidCurrency]:Number(d.paidAmount)})} · ${this._v143Text('paidExact')}${shop}`;
  }else if(d.priceLoading)node.textContent=this._v79Text('looking');
  else if(r?.estimate!=null&&ref)node.textContent=`${this._v79Text('estimate')}: ${this._v79Money({[ref.currency]:r.estimate})} · ${this._v143CompactPriceSource(ref,r.matchKind)}`;
  else node.textContent=this._v79Text('none');
 }
 _v79PaintItem(node,state){
  const row=state.cost?.ingredients?.[Number(node.dataset.v79Item)];
  if(!row){node.textContent='';return;}
  const ref=(row.references||[])[0],source=ref?this._v143CompactPriceSource(ref):'';
  node.textContent=`${this._v79Money(row.costsByCurrency)}${row.coverage<1?' · '+this._v79Text(row.priced?'partialItem':'missing'):''}${source?' · '+source:''}`;
 }
 _v142PaintStockSummary(root=this.shadowRoot){
  super._v142PaintStockSummary(root);
  const data=this._v142StockSummary||{},value=data.value||{},node=root?.querySelector?.('[data-v142-stock-summary] .v142-summary-stat:nth-child(2) em');
  if(node&&value.packageCount!==undefined){
   node.textContent=`${this._v142Coverage(value.pricedPackages,value.packageCount,this._v142Text('priced'))} · ${value.exactPackages||0} ${this._v142Text('exactPrices')} · ${value.estimatedPackages||0} ${this._v143Text('estimatedPrices')}`;
  }
 }

 // ---------- Bottom-right job ETA ----------
 _v143Now(){return globalThis.performance?.now?.()??Date.now();}
 _v143EtaStorageKey(){return `cook4me.jobEta.v1.${String(this._hass?.user?.id||'anonymous')}`;}
 _v143LoadEtaHistory(){
  if(this._v143EtaHistory)return this._v143EtaHistory;
  try{const raw=JSON.parse(globalThis.localStorage?.getItem(this._v143EtaStorageKey())||'{}');this._v143EtaHistory=raw&&typeof raw==='object'?raw:{};}catch(_error){this._v143EtaHistory={};}
  return this._v143EtaHistory;
 }
 _v143SaveEtaHistory(){
  try{globalThis.localStorage?.setItem(this._v143EtaStorageKey(),JSON.stringify(this._v143EtaHistory||{}));}catch(_error){}
 }
 _v143JobKey(token){
  const kind=String(token?._v143Kind||'').trim().toLowerCase(),title=String(token?.title||'work').trim().toLowerCase().replace(/\s+/g,' ').slice(0,80);
  return (kind?`kind:${kind}`:`title:${title}`);
 }
 _v143HistoricalDuration(token){
  const row=this._v143LoadEtaHistory()[this._v143JobKey(token)],value=Number(row?.avgMs);
  return Number.isFinite(value)&&value>0?value:null;
 }
 _v143RecordDuration(token){
  if(!token||token._v143HistorySaved||token.cancelled||token.failed)return;
  token._v143HistorySaved=true;const started=Number(token._v143StartedAt),duration=this._v143Now()-started;
  if(!Number.isFinite(duration)||duration<250||duration>6*60*60*1000)return;
  const history=this._v143LoadEtaHistory(),key=this._v143JobKey(token),old=history[key]||{},count=Math.min(20,Math.max(0,Number(old.count)||0)+1);
  const previous=Number(old.avgMs),weight=Math.min(5,Math.max(1,Number(old.count)||1)),avg=Number.isFinite(previous)&&previous>0?(previous*weight+duration)/(weight+1):duration;
  history[key]={avgMs:Math.round(avg),count,updatedAt:Date.now()};
  const entries=Object.entries(history).sort((a,b)=>Number(b[1]?.updatedAt||0)-Number(a[1]?.updatedAt||0)).slice(0,80);
  this._v143EtaHistory=Object.fromEntries(entries);this._v143SaveEtaHistory();
 }
 _v143EnsureEtaNode(token){
  if(!token?.card)return null;let node=token.card.querySelector('[data-v143-eta]');
  if(!node){node=document.createElement('div');node.className='v143-eta';node.dataset.v143Eta='';node.innerHTML='<ha-icon icon="mdi:timer-sand" aria-hidden="true"></ha-icon><span></span>';const detail=token.card.querySelector('.rx-v59-op-detail');detail?.after(node);}
  return node;
 }
 _v143FormatEta(ms){
  const seconds=Math.max(0,Math.ceil(Number(ms)/1000));if(!Number.isFinite(seconds))return '';
  if(seconds<5)return this._v143Text('lessThan5s');
  if(seconds<60)return `~${Math.max(5,Math.round(seconds/5)*5)} s`;
  if(seconds<3600){const minutes=Math.floor(seconds/60),rest=Math.round((seconds%60)/10)*10;return rest>=10?`~${minutes} min ${rest} s`:`~${minutes} min`;}
  const hours=Math.floor(seconds/3600),minutes=Math.round((seconds%3600)/300)*5;return minutes>=5?`~${hours} h ${minutes} min`:`~${hours} h`;
 }
 _v143EstimateEta(token,done=null,total=null){
  if(!token||token.failed||token.cancelled||token.ended)return null;
  const now=this._v143Now(),started=Number(token._v143StartedAt)||now,elapsed=Math.max(0,now-started),d=Number(done),t=Number(total);
  if(Number.isFinite(d)&&Number.isFinite(t)&&t>0&&d>=0&&d<t){
   token._v143EtaSamples??=[];
   const last=token._v143EtaSamples.at(-1);
   if(!last||last.done!==d){token._v143EtaSamples.push({done:d,total:t,at:now});if(token._v143EtaSamples.length>10)token._v143EtaSamples.shift();}
   const base=token._v143EtaSamples.find(sample=>sample.done<d&&now-sample.at>=250);
   if(base){const rate=(d-base.done)/((now-base.at)/1000);if(Number.isFinite(rate)&&rate>0){const raw=(t-d)/rate*1000;token._v143EtaMs=token._v143EtaMs?token._v143EtaMs*.55+raw*.45:raw;return Math.max(0,token._v143EtaMs);}}
   const historical=this._v143HistoricalDuration(token);if(historical)return Math.max(0,historical*(1-d/t));
  }
  const historical=this._v143HistoricalDuration(token);if(historical)return Math.max(0,historical-elapsed);
  return null;
 }
 _v143PaintEta(token,done=null,total=null){
  const node=this._v143EnsureEtaNode(token);if(!node)return;
  if(token.failed||token.cancelled||token.ended){node.hidden=true;return;}
  const eta=this._v143EstimateEta(token,done,total);node.hidden=false;
  node.querySelector('span').textContent=eta===null?this._v143Text('estimatingEta'):`${this._v143Text('eta')}: ${this._v143FormatEta(eta)}`;
 }
 _processStart(...args){
  const token=super._processStart(...args);if(!token)return token;
  token._v143StartedAt=this._v143Now();token._v143EtaSamples=[];token._v143EtaMs=null;token._v143HistorySaved=false;this._v143PaintEta(token);this._v143Styles();return token;
 }
 _processUpdate(token,detail,done=null,total=null){
  const result=super._processUpdate(token,detail,done,total);this._v143PaintEta(token,done,total);return result;
 }
 _v59HandleProgress(event){
  const data=event?.data&&typeof event.data==='object'?event.data:event||{},token=this._v63Jobs?.get(String(data.operationId||''))||((this._process&&String(this._process.id)===String(data.operationId||''))?this._process:null);
  if(token&&data.kind)token._v143Kind=String(data.kind);
  return super._v59HandleProgress(event);
 }
 _v59FailProcess(token,message){
  token?.card?.querySelector('[data-v143-eta]')?.setAttribute('hidden','');return super._v59FailProcess(token,message);
 }
 _processEnd(token){
  if(token&&!token.ended&&!token.failed&&!token.cancelled)this._v143RecordDuration(token);
  token?.card?.querySelector('[data-v143-eta]')?.setAttribute('hidden','');
  return super._processEnd(token);
 }

 _renderTab(){const result=super._renderTab();this._v143Styles();this.setAttribute('data-cook4me-build','2026.9.21.8');return result;}
 _v143Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v143Styles'))return;
  const style=document.createElement('style');style.id='v143Styles';style.textContent=`
   .v143-price-source{display:flex!important;flex-direction:column;gap:5px;margin:9px 0!important}.v143-price-kind{display:inline-flex;align-items:center;gap:6px;width:max-content;max-width:100%;padding:4px 8px;border-radius:999px;border:1px solid var(--divider-color);color:var(--primary-text-color)}.v143-price-kind ha-icon{--mdc-icon-size:16px}.v143-price-exact{border-color:color-mix(in srgb,#43a047 55%,var(--divider-color));background:color-mix(in srgb,#43a047 10%,transparent)}.v143-price-barcode{border-color:color-mix(in srgb,var(--primary-color) 58%,var(--divider-color));background:color-mix(in srgb,var(--primary-color) 9%,transparent)}.v143-price-estimate{border-color:color-mix(in srgb,#ffb74d 55%,var(--divider-color));background:color-mix(in srgb,#ffb74d 9%,transparent)}.v143-price-manual{border-color:color-mix(in srgb,#9575cd 55%,var(--divider-color));background:color-mix(in srgb,#9575cd 9%,transparent)}.v143-price-meta{display:flex;gap:5px 9px;flex-wrap:wrap}.v143-price-meta>span{display:inline-flex}.v143-price-basis,.v143-price-provider{display:block}.v143-price-provider a{color:var(--primary-color)}
   .v143-eta{display:flex;align-items:center;gap:6px;margin-top:6px;color:var(--secondary-text-color);font-size:12px;line-height:1.3}.v143-eta ha-icon{--mdc-icon-size:16px;flex:0 0 auto}.v143-eta[hidden]{display:none!important}.rx-v59-op:has(.v143-eta:not([hidden])) .rx-v59-op-track{margin-top:7px}
   @media(max-width:520px){.v143-price-kind{width:auto}.v143-price-meta{flex-direction:column;gap:2px}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v143',Cook4MeRecipeHubPanelV143);
