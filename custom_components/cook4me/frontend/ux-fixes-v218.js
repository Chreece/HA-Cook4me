const TEXT={
 en:{
  storedAt:'Stored at',unlimited:'Unlimited stock',
  fallbackTitle:'USDA fallback review',
  fallbackHelp:'This is an optional local USDA fallback for ingredients that do not already have a usable exact/reviewed value. “Remaining” does not mean those ingredients are broken. Ambiguous results stay unknown instead of being guessed.',
  unresolved:'Needs review',retry:'Retry now',manual:'Enter nutrition manually',
  manualHelp:'Use values printed or otherwise verified per 100 g or per 100 ml. Leave unknown nutrients empty.',
  saveManual:'Save verified values',basis:'Basis',reason:'Reason',query:'USDA query',retryAfter:'Automatic retry after',
  needValue:'Enter at least one valid non-negative nutrient value.',saved:'Nutrition reference saved.',
  ambiguous:'USDA returned more than one plausible food.',no_nutrition:'The matched USDA food has no usable nutrient profile.',no_english_name:'No reliable English lookup name is available.',network:'The previous USDA request could not finish.'
 },
 de:{
  storedAt:'Gelagert in',unlimited:'Unbegrenzter Vorrat',
  fallbackTitle:'USDA-Fallback prüfen',
  fallbackHelp:'Dies ist ein optionaler lokaler USDA-Fallback für Zutaten ohne bereits nutzbaren exakten/geprüften Wert. „Verbleibend“ bedeutet nicht, dass diese Zutaten defekt sind. Mehrdeutige Ergebnisse bleiben unbekannt, statt geraten zu werden.',
  unresolved:'Zu prüfen',retry:'Jetzt erneut versuchen',manual:'Nährwerte manuell eingeben',
  manualHelp:'Nur verifizierte Werte pro 100 g oder 100 ml eingeben. Unbekannte Werte leer lassen.',
  saveManual:'Geprüfte Werte speichern',basis:'Basis',reason:'Grund',query:'USDA-Suche',retryAfter:'Automatischer neuer Versuch nach',
  needValue:'Mindestens einen gültigen, nicht negativen Nährwert eingeben.',saved:'Nährwertreferenz gespeichert.',
  ambiguous:'USDA liefert mehrere plausible Lebensmittel.',no_nutrition:'Der passende USDA-Eintrag enthält kein nutzbares Nährwertprofil.',no_english_name:'Kein zuverlässiger englischer Suchname verfügbar.',network:'Die letzte USDA-Anfrage konnte nicht abgeschlossen werden.'
 },
 el:{
  storedAt:'Αποθήκευση',unlimited:'Απεριόριστο απόθεμα',
  fallbackTitle:'Έλεγχος εφεδρικών USDA στοιχείων',
  fallbackHelp:'Αυτός είναι προαιρετικός τοπικός USDA fallback για υλικά που δεν έχουν ήδη χρήσιμη ακριβή/ελεγμένη τιμή. Το «απομένουν» δεν σημαίνει ότι αυτά τα υλικά είναι χαλασμένα. Τα αμφίβολα αποτελέσματα μένουν άγνωστα αντί να γίνεται εικασία.',
  unresolved:'Χρειάζεται έλεγχο',retry:'Νέα προσπάθεια τώρα',manual:'Χειροκίνητα διατροφικά στοιχεία',
  manualHelp:'Βάλε μόνο επιβεβαιωμένες τιμές ανά 100 g ή 100 ml. Άφησε κενά όσα δεν γνωρίζεις.',
  saveManual:'Αποθήκευση επιβεβαιωμένων τιμών',basis:'Βάση',reason:'Αιτία',query:'Αναζήτηση USDA',retryAfter:'Αυτόματη νέα προσπάθεια μετά',
  needValue:'Συμπλήρωσε τουλάχιστον μία έγκυρη μη αρνητική διατροφική τιμή.',saved:'Αποθηκεύτηκαν τα διατροφικά στοιχεία.',
  ambiguous:'Το USDA επέστρεψε περισσότερα από ένα πιθανά τρόφιμα.',no_nutrition:'Το αντίστοιχο τρόφιμο USDA δεν έχει χρήσιμο διατροφικό προφίλ.',no_english_name:'Δεν υπάρχει αξιόπιστο αγγλικό όνομα αναζήτησης.',network:'Η προηγούμενη αναζήτηση USDA δεν ολοκληρώθηκε.'
 }
};
const NUTRIENTS=[
 ['energyKcal','energy','kcal'],['protein','protein','g'],['carbohydrates','carbs','g'],
 ['fat','fat','g'],['saturatedFat','saturatedFat','g'],['fiber','fiber','g'],
 ['sugars','sugars','g'],['salt','salt','g']
];
const text=v=>String(v??'').trim();
const token=v=>text(v).replace(/^[ki]:/,'');
function rawIds(row){
 const out=new Set();
 if(!row||typeof row!=='object')return out;
 for(const key of ['key','ingredientId','foodKey','id'])if(row[key])out.add(token(row[key]));
 for(const value of row.sourceIngredientIds||[])if(value)out.add(token(value));
 return out;
}
function intersects(a,b){for(const value of a)if(b.has(value))return true;return false;}

export const UXFixesMixin=Base=>class extends Base{
 _v218Text(key){const lang=String(this._uiIngredientLanguage?.()||this._langCode?.()||'en').split(/[-_]/)[0];return (TEXT[lang]||TEXT.en)[key]||TEXT.en[key]||key;}
 _v218ExpandedIds(item){
  const ids=rawIds(item),catalog=this._ingredientCatalog||[];
  let changed=true;
  while(changed){
   changed=false;
   for(const row of catalog){
    const aliases=rawIds(row);
    if(intersects(ids,aliases))for(const value of aliases)if(!ids.has(value)){ids.add(value);changed=true;}
   }
  }
  return ids;
 }
 _v218StockMatches(item,row){
  const wanted=this._v218ExpandedIds(item),have=this._v218ExpandedIds(row);
  if(intersects(wanted,have))return true;
  for(const link of row?.ingredientLinks||[])if(intersects(wanted,this._v218ExpandedIds(link)))return true;
  for(const lot of row?.lots||[])for(const link of lot?.ingredientLinks||[])if(intersects(wanted,this._v218ExpandedIds(link)))return true;
  return false;
 }
 _v218StorageNames(item){
  const locations=new Map((this._v78Locations?.()||[]).map(row=>[String(row.id),String(row.name||'')]));
  const names=[];
  for(const row of this._houseIngredients||[]){
   if(!this._v218StockMatches(item,row))continue;
   const ids=row.unlimited?[row.storageLocationId]:(row.lots||[]).map(lot=>lot.storageLocationId);
   for(const id of ids){const name=locations.get(String(id||''));if(name&&!names.includes(name))names.push(name);}
  }
  return names;
 }
 _v218DecorateRecipeStorage(container,recipe){
  if(!container||!recipe?.ingredients?.length)return;
  container.querySelectorAll('[data-v66-ingredient]').forEach(button=>{
   const index=Number(button.dataset.v66Ingredient),item=recipe.ingredients[index];
   if(!item)return;
   const names=this._v218StorageNames(item);
   let small=button.querySelector('.v218-stored-at');
   if(!names.length){small?.remove();return;}
   if(!small){
    const holder=button.querySelector(':scope > span:first-child')||button;
    small=document.createElement('small');small.className='v218-stored-at';
    const icon=document.createElement('ha-icon');icon.setAttribute('icon','mdi:map-marker-outline');icon.setAttribute('aria-hidden','true');
    small.append(icon,document.createTextNode(''));holder.append(small);
   }
   const textNode=[...small.childNodes].find(node=>node.nodeType===Node.TEXT_NODE);
   const label=`${this._v218Text('storedAt')}: ${names.join(', ')}`;
   if(textNode)textNode.textContent=label;else small.append(document.createTextNode(label));
  });
 }
 _bindCards(container,...args){
  const result=super._bindCards(container,...args);
  for(const card of container?.querySelectorAll?.('[data-v66-ref]')||[]){
   const row=this._v66Refs?.get(card.dataset.v66Ref);
   if(row?.recipe)this._v218DecorateRecipeStorage(card,row.recipe);
  }
  return result;
 }

 _v154PlaceItems(locationId){
  const rows=[...(super._v154PlaceItems?.(locationId)||[])],wanted=String(locationId||'');
  for(const row of this._houseIngredients||[]){
   if(row?.unlimited&&String(row.storageLocationId||'')===wanted)rows.push({row,lot:null,unlimited:true});
  }
  return rows;
 }
 _v154PlaceItemsHtml(locationId){
  const e=v=>this._escape(String(v??'')),items=this._v154PlaceItems(locationId);
  if(!items.length)return `<div class="v154-place-empty muted">${e(this._v154Text('noItems'))}</div>`;
  return `<div class="v154-place-items">${items.map(({row,lot,unlimited})=>{
   const name=lot?this._v154ItemName(row,lot):String(row.productName||this._v112Local?.(row)?.name||row.name||row.foodName||'').trim();
   const details=unlimited?`∞ ${this._v218Text('unlimited')}`:[
    this._displayAmount?.(lot.quantity,row.unit)||[lot.quantity,row.unit].filter(Boolean).join(' '),
    lot.bestBefore?this._v78Text('date')+': '+lot.bestBefore:'',
    this._v154ContainerName(lot.containerId)
   ].filter(Boolean).join(' · ');
   if(unlimited)return `<div class="v154-place-item v218-unlimited-item"><ha-icon icon="mdi:infinity"></ha-icon><span><strong>${e(name)}</strong><small>${e(details)}</small></span></div>`;
   return `<button type="button" class="v154-place-item" data-v154-edit-lot="${e(lot.id)}"><ha-icon icon="mdi:package-variant-closed"></ha-icon><span><strong>${e(name)}</strong><small>${e(details)}</small></span><ha-icon icon="mdi:pencil-outline"></ha-icon></button>`;
  }).join('')}</div>`;
 }
 _v218Reason(reason){
  const value=String(reason||'');
  if(value==='ambiguous')return this._v218Text('ambiguous');
  if(value==='no_nutrition')return this._v218Text('no_nutrition');
  if(value==='no_english_name')return this._v218Text('no_english_name');
  if(value.startsWith('http_')||['URLError','TimeoutError','JSONDecodeError'].includes(value))return this._v218Text('network');
  return value||this._v218Text('unresolved');
 }
 _v218LocalUnresolvedName(row){
  const wanted=token(row?.identity),match=(this._ingredientCatalog||[]).find(item=>this._v218ExpandedIds(item).has(wanted));
  return match?.name||row?.name||row?.query||row?.identity||'';
 }
 _nutritionSettingsHtml(){
  const html=super._nutritionSettingsHtml(),rows=Array.isArray(this._nutritionSettings?.unresolvedDetails)?this._nutritionSettings.unresolvedDetails:[];
  if(!html)return html;
  const e=v=>this._escape(String(v??''));
  const review=`<details class="v218-nutrition-review" ${rows.length?'':'hidden'}><summary><strong>${e(this._v218Text('fallbackTitle'))}</strong>${rows.length?` <span class="chip">${rows.length} ${e(this._v218Text('unresolved'))}</span>`:''}</summary><p class="muted">${e(this._v218Text('fallbackHelp'))}</p><div class="v218-unresolved-list">${rows.map((row,index)=>`<details class="v218-unresolved" data-v218-index="${index}"><summary>${e(this._v218LocalUnresolvedName(row))} · ${e(this._v218Reason(row.reason))}</summary><div class="v218-unresolved-body"><div class="muted">${row.query?`${e(this._v218Text('query'))}: ${e(row.query)}<br>`:''}${row.retryAfter?`${e(this._v218Text('retryAfter'))}: ${e(row.retryAfter)}`:''}</div><div class="toolbar"><button type="button" class="btn secondary" data-v218-retry>${e(this._v218Text('retry'))}</button></div><details class="v218-manual"><summary>${e(this._v218Text('manual'))}</summary><p class="muted">${e(this._v218Text('manualHelp'))}</p><label class="field">${e(this._v218Text('basis'))}<select data-v218-basis><option value="g">100 g</option><option value="ml">100 ml</option></select></label><div class="v218-nutrient-grid">${NUTRIENTS.map(([key,label,unit])=>`<label class="field">${e(this._t(label))} (${unit})<input type="number" min="0" step="any" data-v218-nutrient="${key}"></label>`).join('')}</div><button type="button" class="btn" data-v218-manual-save>${e(this._v218Text('saveManual'))}</button><p class="muted" role="status" data-v218-status></p></details></div></details>`).join('')}</div></details>`;
  const note=`<p class="muted v218-fallback-help">${e(this._v218Text('fallbackHelp'))}</p>`;
  let output=html;
  const statusPos=output.lastIndexOf('</section>');
  return statusPos>=0?`${output.slice(0,statusPos)}${note}${review}${output.slice(statusPos)}`:`${output}${note}${review}`;
 }
 _bindNutritionSettings(c){
  super._bindNutritionSettings(c);
  const rows=Array.isArray(this._nutritionSettings?.unresolvedDetails)?this._nutritionSettings.unresolvedDetails:[];
  c?.querySelectorAll('[data-v218-index]').forEach(node=>{
   const row=rows[Number(node.dataset.v218Index)];if(!row)return;
   const status=node.querySelector('[data-v218-status]');
   node.querySelector('[data-v218-retry]')?.addEventListener('click',async event=>{
    const button=event.currentTarget;button.disabled=true;
    try{const result=await this._api('cook4me/v16/nutrition_unresolved_retry',{entry_id:this._entryId,identity:row.identity});this._nutritionSettings={...(this._nutritionSettings||{}),...result};this._renderTab();}
    catch(error){if(status)status.textContent=String(error.message||error);}
    finally{button.disabled=false;}
   });
   node.querySelector('[data-v218-manual-save]')?.addEventListener('click',async event=>{
    const button=event.currentTarget,values={};
    node.querySelectorAll('[data-v218-nutrient]').forEach(input=>{if(input.value==='')return;const value=Number(String(input.value).replace(',','.'));if(Number.isFinite(value)&&value>=0)values[input.dataset.v218Nutrient]=value;});
    if(!Object.keys(values).length){if(status)status.textContent=this._v218Text('needValue');node.querySelector('[data-v218-nutrient]')?.focus();return;}
    button.disabled=true;
    try{
     const result=await this._api('cook4me/v16/nutrition_generic_set',{entry_id:this._entryId,identity:row.identity,nutrition:{basisQuantity:100,basisUnit:node.querySelector('[data-v218-basis]')?.value||'g',values}});
     this._nutritionSettings={...(this._nutritionSettings||{}),...result};this._message(this._v218Text('saved'));this._renderTab();
    }catch(error){if(status)status.textContent=String(error.message||error);}
    finally{button.disabled=false;}
   });
  });
 }
 _v218Styles(){
  if(this.shadowRoot?.querySelector('#v218Styles'))return;
  const style=document.createElement('style');style.id='v218Styles';style.textContent=`
   .v218-stored-at{display:flex!important;align-items:center;gap:4px;margin-top:5px;color:var(--secondary-text-color);font-size:.76rem}.v218-stored-at ha-icon{--mdc-icon-size:15px}
   .v218-unlimited-item{cursor:default!important}.v218-unlimited-item>ha-icon{color:var(--primary-color)}
   .v218-fallback-help{max-width:90ch;line-height:1.5}.v218-nutrition-review{margin-top:14px;border-top:1px solid var(--divider-color);padding-top:10px}.v218-nutrition-review>summary{cursor:pointer;display:flex;align-items:center;gap:8px;flex-wrap:wrap}.v218-unresolved-list{display:grid;gap:8px;margin-top:12px}.v218-unresolved{padding:10px 12px;border:1px solid var(--divider-color);border-radius:11px}.v218-unresolved>summary{cursor:pointer;font-weight:600}.v218-unresolved-body{padding-top:10px}.v218-manual{margin-top:10px}.v218-nutrient-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:10px 0}.v218-nutrient-grid input{width:100%}
   @media(max-width:620px){.v218-nutrient-grid{grid-template-columns:1fr}}
  `;this.shadowRoot?.append(style);
 }
 _renderProfile(c){const result=super._renderProfile(c);this._v218Styles();return result;}
 _renderTab(){const result=super._renderTab();this._v218Styles();return result;}
 _renderRecipeDialog(){
  const result=super._renderRecipeDialog();
  if(this._v63RecipeDialog&&this._opened)this._v218DecorateRecipeStorage(this._v63RecipeDialog,this._opened);
  this._v218Styles();return result;
 }
};
