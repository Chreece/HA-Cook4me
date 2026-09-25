// Package-level opening controls. Printed dates remain available for editing.
export const OPENING_FIELDS=['applyOpeningExpiry','openingRuleId','openingConditionsConfirmed'];
const TEXT={
 en:{title:'After opening',days:'Use within days after opening (package label)',catalog:'Catalog guidance',manual:'Enter the package instructions manually',apply:'Apply the opening deadline as the expiry date',opened:'Package opened',date:'Opened on',printed:'Printed expiry date',expiry:'Expiry date',confirm:'I follow these storage instructions',fridge:'Keep refrigerated at or below',fridgeRange:'Keep refrigerated at',unknown:'No matching opening window in the catalog. Enter the days stated on the package.',loading:'Checking catalog opening guidance…',failed:'Catalog guidance could not be loaded. You can enter the package instructions manually.',label:'The package instructions take priority.',choose:'Choose guidance',select:'Select the package actually used.',range:'days'},
 de:{title:'Nach dem Öffnen',days:'Nach dem Öffnen innerhalb von Tagen verbrauchen (Packungsangabe)',catalog:'Kataloghinweis',manual:'Packungsangabe manuell eingeben',apply:'Öffnungsfrist als Ablaufdatum anwenden',opened:'Packung geöffnet',date:'Geöffnet am',printed:'Aufgedrucktes Ablaufdatum',expiry:'Ablaufdatum',confirm:'Ich halte diese Lagerhinweise ein',fridge:'Gekühlt lagern bei höchstens',fridgeRange:'Gekühlt lagern bei',unknown:'Keine passende Öffnungsfrist im Katalog. Die Tage von der Packung eingeben.',loading:'Öffnungshinweise im Katalog werden geprüft…',failed:'Kataloghinweise konnten nicht geladen werden. Die Packungsangabe kann manuell eingegeben werden.',label:'Die Packungsangabe hat Vorrang.',choose:'Hinweis auswählen',select:'Die tatsächlich verwendete Packung auswählen.',range:'Tage'},
 el:{title:'Μετά το άνοιγμα',days:'Κατανάλωση εντός ημερών μετά το άνοιγμα (ετικέτα)',catalog:'Οδηγία καταλόγου',manual:'Χειροκίνητη εισαγωγή της οδηγίας συσκευασίας',apply:'Εφαρμογή της προθεσμίας ανοίγματος ως ημερομηνίας λήξης',opened:'Η συσκευασία ανοίχτηκε',date:'Ημερομηνία ανοίγματος',printed:'Αναγραφόμενη ημερομηνία λήξης',expiry:'Ημερομηνία λήξης',confirm:'Τηρώ αυτές τις οδηγίες συντήρησης',fridge:'Διατήρηση στο ψυγείο έως',fridgeRange:'Διατήρηση στο ψυγείο στους',unknown:'Δεν υπάρχει αντίστοιχη προθεσμία στον κατάλογο. Συμπλήρωσε τις ημέρες που αναγράφονται στη συσκευασία.',loading:'Έλεγχος οδηγιών ανοίγματος στον κατάλογο…',failed:'Οι οδηγίες καταλόγου δεν φορτώθηκαν. Μπορείς να συμπληρώσεις την οδηγία της συσκευασίας χειροκίνητα.',label:'Προτεραιότητα έχουν οι οδηγίες της συσκευασίας.',choose:'Επιλογή οδηγίας',select:'Επίλεξε τη συσκευασία που χρησιμοποιήθηκε.',range:'ημέρες'}
};
const CONDITIONS={
 stored_upright:['Store upright','Stehend aufbewahren','Διατήρηση σε όρθια θέση'],
 airtight_container:['In an airtight container','In einem luftdichten Behälter','Σε αεροστεγές δοχείο'],
 closed_container:['In a closed container','In einem geschlossenen Behälter','Σε κλειστό δοχείο'],
 covered_with_fresh_water:['Covered with fresh water','Mit frischem Wasser bedeckt','Καλυμμένο με φρέσκο νερό'],
 covered_with_oil:['Covered with oil','Mit Öl bedeckt','Καλυμμένο με λάδι'],
 opening_not_touched_or_drunk_from:['Do not touch the opening or drink from it','Öffnung nicht berühren oder daraus trinken','Χωρίς άγγιγμα του ανοίγματος ή κατανάλωση απευθείας από αυτό'],
 package_reclosed_promptly:['Close the package promptly','Packung umgehend wieder verschließen','Άμεσο κλείσιμο της συσκευασίας'],
 pasteurized_or_uht:['Pasteurized or UHT product','Pasteurisiertes oder ultrahocherhitztes Produkt','Παστεριωμένο προϊόν ή προϊόν UHT'],
 plain_natural_tofu:['Plain natural tofu','Naturtofu','Σκέτο φυσικό τόφου'],
 transferred_to_container:['Transfer to a container','In einen Behälter umfüllen','Μεταφορά σε δοχείο'],
 transferred_to_nonmetal_container:['Transfer to a non-metal container','In einen nichtmetallischen Behälter umfüllen','Μεταφορά σε μη μεταλλικό δοχείο'],
 water_changed_daily:['Change the water daily','Wasser täglich wechseln','Καθημερινή αλλαγή νερού'],
 transferred_to_clean_container:['Transfer to a clean container','In einen sauberen Behälter umfüllen','Μεταφορά σε καθαρό δοχείο'],
 vacuum_packed_feta:['Feta from a vacuum pack','Feta aus Vakuumverpackung','Φέτα από συσκευασία κενού αέρος'],
 feta_in_original_brine:['Keep feta in its original brine','Feta in der ursprünglichen Salzlake aufbewahren','Διατήρηση της φέτας στην αρχική άλμη']
};
export const validOpeningDays=value=>Number.isInteger(Number(value))&&Number(value)>0&&Number(value)<=3650;
export function packageExpiry(lot){
 const printed=lot.noExpiry?'':String(lot.bestBefore||'');
 if(lot.applyOpeningExpiry===false||!lot.openedAt||!validOpeningDays(lot.useWithinDays))return printed;
 const day=new Date(`${lot.openedAt}T00:00:00Z`);if(!Number.isFinite(+day))return printed;
 day.setUTCDate(day.getUTCDate()+Number(lot.useWithinDays));
 const opened=day.toISOString().slice(0,10);return printed&&printed<opened?printed:opened;
}
export const PackageOpeningMixin=Base=>class extends Base{
 _v222Lang(){return String(this._uiIngredientLanguage?.()||this._langCode?.()||'en').split(/[-_]/)[0];}
 _v222Text(key){return (TEXT[this._v222Lang()]||TEXT.en)[key]||TEXT.en[key];}
 _v222Conditions(rule){
  const index={en:0,de:1,el:2}[this._v222Lang()]||0,hasMinimum=Number.isFinite(rule.minTemperatureC);
  const temperature=hasMinimum?`${rule.minTemperatureC}–${rule.maxTemperatureC}`:rule.maxTemperatureC;
  return [`${this._v222Text(hasMinimum?'fridgeRange':'fridge')} ${temperature} °C`,...(rule.conditions||[]).map(key=>CONDITIONS[key]?.[index]||key)].join(' · ');
 }
 _v222RuleLabel(rule){return `${rule.daysMin===rule.daysMax?rule.daysMax:`${rule.daysMin}–${rule.daysMax}`} ${this._v222Text('range')}${rule.brand?` · ${rule.brand}`:''}`;}
 _v222Key(ingredient,lot){return JSON.stringify([this._prefKey(),ingredient?.key||ingredient?.ingredientId||ingredient?.id||'',lot.brand||'',lot.barcode||'']);}
 _v222Rules(ingredient,lot,refresh){
  if(!(ingredient?.key||ingredient?.ingredientId||ingredient?.id))return {rules:[]};
  const key=this._v222Key(ingredient,lot);this._v222Cache??=new Map();let cached=this._v222Cache.get(key);
  if(!cached){
   cached={rules:[],loading:true,callbacks:new Set()};this._v222Cache.set(key,cached);
   if(this._v222Cache.size>150)this._v222Cache.delete(this._v222Cache.keys().next().value);
   void this._api('cook4me/v33/opening_guidance',{entry_id:this._entryId,ingredient,lot_metadata:{brand:lot.brand||'',barcode:lot.barcode||''}}).then(result=>{cached.rules=result.rules||[];},()=>{cached.failed=true;}).finally(()=>{cached.loading=false;for(const fn of cached.callbacks)fn();cached.callbacks.clear();});
  }
  if(cached.loading&&refresh)cached.callbacks.add(refresh);
  return cached;
 }
 _v78Fresh(...args){return {...super._v78Fresh(...args),applyOpeningExpiry:false,openingRuleId:'',openingConditionsConfirmed:false};}
 _v196Decorate(){const result=super._v196Decorate();this._v222Editor();return result;}
 _v78IngredientOptions(...args){const result=super._v78IngredientOptions(...args);this._v222Editor();return result;}
 _v222Editor(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  const days=c.querySelector('main [data-draft="useWithinDays"]'),date=c.querySelector('main [data-draft="openedAt"]');if(!days||!date)return;
  const section=days.closest('details');if(!section)return;section.hidden=!!d.unlimited&&!d.editLotId;
  section.querySelector('summary').textContent=this._v222Text('title');
  for(const [input,key] of [[days,'days'],[date,'date'],[c.querySelector('main [data-draft="bestBefore"]'),'printed']]){
   const text=input?.closest('label')?.firstChild;if(text?.nodeType===3)text.textContent=this._v222Text(key);
  }
  const ingredient=this._v196Links?.()[0]||d.ingredient;
  const key=this._v222Key(ingredient,d);
  if(d._v222Identity&&d._v222Identity!==key&&d.openingRuleId){d.openingRuleId='';d.openingConditionsConfirmed=false;d.useWithinDays='';days.value='';}
  d._v222Identity=key;
  const guidance=this._v222Rules(ingredient,d,()=>{if(c===this._v78Dialog&&d===this._v78Draft)this._v222Keep(()=>this._v222Editor());});
  let holder=section.querySelector('[data-v222-editor]');
  if(!holder){holder=document.createElement('div');holder.dataset.v222Editor='';holder.className='v222-opening';section.append(holder);holder.after(date.closest('label'));}
  const rule=guidance.rules.find(row=>row.id===d.openingRuleId),e=value=>this._escape(String(value??''));
  const signature=JSON.stringify([key,guidance.loading,guidance.failed,guidance.rules,d.openingRuleId,d.openingConditionsConfirmed,validOpeningDays(d.useWithinDays)]);
  if(holder._signature!==signature){
   holder._signature=signature;
   holder.innerHTML=`<label class="field">${e(this._v222Text('catalog'))}<select data-v222-rule><option value="">${e(this._v222Text('manual'))}</option>${guidance.rules.map(r=>`<option value="${e(r.id)}" ${r.id===d.openingRuleId?'selected':''}>${e(this._v222RuleLabel(r))}</option>`).join('')}</select></label>${rule?`<label class="v222-check"><input type="checkbox" data-v222-conditions ${d.openingConditionsConfirmed?'checked':''}><span>${e(this._v222Text('confirm'))}: ${e(this._v222Conditions(rule))}</span></label>`:''}<small class="muted">${e(this._v222Text(guidance.loading?'loading':guidance.failed?'failed':guidance.rules.length?'label':'unknown'))}</small><label class="v222-check" data-v222-known><input type="checkbox" data-v222-apply><span>${e(this._v222Text('apply'))}</span></label><label class="v222-check" data-v222-known><input type="checkbox" data-v222-opened><span>${e(this._v222Text('opened'))}</span></label><small data-v222-expiry role="status"></small>`;
   holder.querySelector('[data-v222-rule]').onchange=event=>{d.openingRuleId=event.target.value;d.openingConditionsConfirmed=false;const chosen=guidance.rules.find(r=>r.id===d.openingRuleId);d.useWithinDays=chosen?.daysMax||'';days.value=d.useWithinDays;this._v78Dirty=true;this._v222Editor();};
   holder.querySelector('[data-v222-conditions]')?.addEventListener('change',event=>{d.openingConditionsConfirmed=event.target.checked;this._v78Dirty=true;this._v222Editor();});
   holder.querySelector('[data-v222-apply]').onchange=event=>{d.applyOpeningExpiry=event.target.checked;this._v78Dirty=true;this._v222Editor();};
   holder.querySelector('[data-v222-opened]').onchange=event=>{d.openedAt=event.target.checked?(d.openedAt||this._todayIso()):'';date.value=d.openedAt;this._v78Dirty=true;this._v222Editor();};
  }
  const known=validOpeningDays(d.useWithinDays),busy=!!this._v78Busy||!!this._v78Submitted;
  for(const node of holder.querySelectorAll('[data-v222-known]'))node.hidden=!known;
  for(const node of holder.querySelectorAll('input,select'))node.disabled=busy;
  for(const name of ['apply','opened'])holder.querySelector(`[data-v222-${name}]`).disabled=busy||!known||!!(d.openingRuleId&&!d.openingConditionsConfirmed);
  holder.querySelector('[data-v222-apply]').checked=d.applyOpeningExpiry===true;
  holder.querySelector('[data-v222-opened]').checked=!!d.openedAt;
  days.disabled=busy||!!d.openingRuleId;
  date.closest('label').hidden=!d.openedAt;
  const expiry=packageExpiry(d);holder.querySelector('[data-v222-expiry]').textContent=expiry?`${this._v222Text('expiry')}: ${expiry}`:'';
  if(!c._v222Bound){c._v222Bound=true;c.addEventListener('input',event=>{if(['useWithinDays','openedAt','bestBefore','brand','barcode'].includes(event.target.dataset?.draft))this._v222Editor();});c.addEventListener('change',()=>this._v222Editor());c.addEventListener('click',event=>{if(event.target.closest?.('[data-v194-index],[data-v114-link]'))queueMicrotask(()=>this._v222Editor());});}
  this._v222Styles();
 }
 _v222Keep(fn){return this._v220KeepPosition?this._v220KeepPosition(fn,this.shadowRoot,true):fn();}
 _bindPending(c){const result=super._bindPending(c);this._v222Review(c);return result;}
 _v222Review(c){
  const pending=this._pendingConsumption;if(!pending?.id)return;
  this._v222Styles();
  for(const container of c.querySelectorAll('[data-consume-row]')){
   let holder=container.querySelector('[data-v222-packages]');if(!holder){holder=document.createElement('div');holder.dataset.v222Packages='';holder.className='v222-opening';holder.style.gridColumn='1 / -1';container.append(holder);}
   const refresh=()=>this._v222Keep(()=>{
    if(!holder.isConnected||this._pendingConsumption?.id!==pending.id)return;
    const identity=container.querySelector('[data-v131-stock]')?.value,selected=container.querySelector('[data-v131-lot]')?.value;
    const stock=this._v131StockRow(identity),lots=(stock?.lots||[]).filter(lot=>!selected||lot.id===selected);
    holder._states??=new Map();holder.replaceChildren();
    for(const lot of lots){
     const guidance=validOpeningDays(lot.useWithinDays)?{rules:[]}:this._v222Rules(stock,lot,refresh);
     if(!validOpeningDays(lot.useWithinDays)&&!guidance.rules.length)continue;
     let state=holder._states.get(lot.id);if(!state){state={lotId:lot.id,opened:!!lot.openedAt,initialOpened:!!lot.openedAt,initialApply:lot.applyOpeningExpiry!==false,applyOpeningExpiry:lot.applyOpeningExpiry!==false,ruleId:'',confirmed:false};holder._states.set(lot.id,state);}
     const row=document.createElement('div');row.className='v222-opening';row.dataset.v222Package=lot.id;row._state=state;
     const e=value=>this._escape(String(value??'')),rule=guidance.rules.find(r=>r.id===state.ruleId);
     row.innerHTML=`<strong>${e(lot.productName||stock.name)} · ${e(lot.quantity)} ${e(stock.unit)}</strong>${guidance.rules.length?`<label>${e(this._v222Text('catalog'))}<select data-rule><option value="">${e(this._v222Text('choose'))}</option>${guidance.rules.map(r=>`<option value="${e(r.id)}" ${r.id===state.ruleId?'selected':''}>${e(this._v222RuleLabel(r))}</option>`).join('')}</select></label>`:`<small>${e(lot.useWithinDays)} ${e(this._v222Text('range'))}</small>`}${rule?`<label class="v222-check"><input type="checkbox" data-conditions ${state.confirmed?'checked':''}><span>${e(this._v222Text('confirm'))}: ${e(this._v222Conditions(rule))}</span></label>`:''}<label class="v222-check"><input type="checkbox" data-opened ${state.opened?'checked':''}><span>${e(this._v222Text('opened'))}${lot.openedAt?` · ${e(lot.openedAt)}`:''}</span></label><label class="v222-check"><input type="checkbox" data-apply ${state.applyOpeningExpiry?'checked':''}><span>${e(this._v222Text('apply'))}</span></label><small data-expiry></small>`;
     holder.append(row);
     const paint=()=>{const usable=validOpeningDays(lot.useWithinDays)||!!(rule&&state.confirmed),consume=container.querySelector('[data-consume-check]')?.checked;row.querySelector('[data-opened]').disabled=!consume||!usable||!!lot.openedAt;row.querySelector('[data-apply]').disabled=!consume||!usable;row.querySelector('[data-expiry]').textContent=state.opened?`${this._v222Text('expiry')}: ${packageExpiry({...lot,openedAt:lot.openedAt||this._todayIso(),useWithinDays:lot.useWithinDays||rule?.daysMax,applyOpeningExpiry:state.applyOpeningExpiry})}`:'';};
     row.querySelector('[data-rule]')?.addEventListener('change',event=>{state.ruleId=event.target.value;state.confirmed=false;state.opened=!!lot.openedAt;refresh();});
     row.querySelector('[data-conditions]')?.addEventListener('change',event=>{state.confirmed=event.target.checked;if(!state.confirmed)state.opened=!!lot.openedAt;row.querySelector('[data-opened]').checked=state.opened;paint();});
     row.querySelector('[data-opened]').onchange=event=>{state.opened=event.target.checked;paint();};row.querySelector('[data-apply]').onchange=event=>{state.applyOpeningExpiry=event.target.checked;paint();};paint();
    }
   });
   refresh();
   for(const selector of ['[data-v131-stock]','[data-v131-lot]','[data-consume-check]'])container.querySelector(selector)?.addEventListener('change',refresh);
  }
 }
 async _api(type,data){
  if(type==='cook4me/v33/product_add'&&data?.lot_metadata&&this._v78Draft){const d=this._v78Draft,enriched={...data,lot_metadata:{...Object.fromEntries(OPENING_FIELDS.map(key=>[key,d[key]])),...data.lot_metadata}};if(this._v78Submitted===data)this._v78Submitted=enriched;data=enriched;}
  if(type==='cook4me/v14/consumption_confirm'){
   const editor=this.shadowRoot?.querySelector('#v131ConsumptionEditor');
   if(editor&&String(data.pending_id)===String(this._pendingConsumption?.id))data={...data,ingredients:data.ingredients.map((item,index)=>({...item,packageOpenings:item.consume?[...editor.querySelectorAll(`[data-consume-row="${index}"] [data-v222-package]`)].filter(node=>node._state?.opened&&(!node._state.initialOpened||node._state.applyOpeningExpiry!==node._state.initialApply)).map(node=>{const s=node._state;return {lotId:s.lotId,applyOpeningExpiry:s.applyOpeningExpiry,...(s.ruleId?{ruleId:s.ruleId,confirmed:s.confirmed}:{})};}):[]}))};
  }
  const result=await super._api(type,data);
  if(type==='cook4me/v33/product_details'&&result?.lot)return {...result,lot:{...result.lot,applyOpeningExpiry:result.lot.applyOpeningExpiry!==false}};
  return result;
 }
 _inventoryRowsHtml(){return this._v222ExpiryLabels(super._inventoryRowsHtml());}
 _v154PlaceItemsHtml(...args){return this._v222ExpiryLabels(super._v154PlaceItemsHtml(...args));}
 _v222ExpiryLabels(html){if(!html||!globalThis.document)return html;
  const box=document.createElement('div');box.innerHTML=html;
  const lots=new Map((this._houseIngredients||[]).flatMap(row=>(row.lots||[]).map(lot=>[lot.id,lot])));
  for(const button of box.querySelectorAll('[data-v112-edit-lot],[data-v154-edit-lot]')){const lot=lots.get(button.dataset.v112EditLot||button.dataset.v154EditLot);if(!lot?.openedAt)continue;const expiry=packageExpiry(lot);if(!expiry)continue;const small=button.querySelector('small');if(lot.bestBefore&&small?.textContent.includes(lot.bestBefore))small.textContent=small.textContent.replace(lot.bestBefore,expiry);else{const line=document.createElement('small');line.textContent=`${this._v222Text('expiry')}: ${expiry}`;button.querySelector('span')?.append(line);}}
  return box.innerHTML;
 }
 _v222Styles(){if(!this.shadowRoot||this.shadowRoot.querySelector('#v222Styles'))return;const style=document.createElement('style');style.id='v222Styles';style.textContent='.v222-opening{display:grid;gap:10px;padding:10px 0;min-width:0}.v222-opening label{white-space:normal}.v222-check{display:flex!important;flex-direction:row!important;align-items:flex-start!important;gap:9px}.v222-check input{width:20px!important;min-height:20px!important;flex:0 0 20px}.v222-opening [hidden]{display:none!important}.v222-opening select{max-width:100%;width:100%;white-space:normal}.v222-opening small{overflow-wrap:anywhere}';this.shadowRoot.append(style);}
};
