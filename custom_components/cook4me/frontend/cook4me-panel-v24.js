import "./cook4me-panel-v23.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v23");

const TEXT = {
  en:{
    quantityCoverage:"Stock quantity coverage",quantityShortage:"Short",quantityUnknown:"Amount uncertain",enoughStock:"Enough stock by quantity",
    nutritionGoal:"Nutrition goal",balanced:"Balanced",highProtein:"High protein",lowerCalorie:"Lower calories",highFiber:"High fibre",lowerSaturatedFat:"Lower saturated fat",nutritionGoalHint:"Nutrition is a ranking hint only; diet/allergy safety and stock remain authoritative.",
    household:"Household & meal portions",householdMembers:"Household members",householdHelp:"One name per line. After cooking you can assign servings so confirmed meal nutrition is recorded per person.",saveHousehold:"Save household",
    mealHistory:"Meal nutrition history",today:"Today",week:"7 days",month:"30 days",meals:"meals",noMealHistory:"No confirmed meals recorded yet.",unassigned:"Unassigned",
    storage:"Storage",fridge:"Fridge",freezer:"Freezer",pantryStorage:"Pantry",otherStorage:"Other",purchaseDate:"Purchase date",openedAt:"Opened",useWithinDays:"Use within days after opening",openedToday:"Opened today",
    provenance:"Provenance",scanExpiry:"Scan date",scanExpiryHelp:"Take a photo of the printed date. On-device text recognition is used when the browser supports it; otherwise enter the date manually.",dateScanUnavailable:"This browser does not expose on-device text recognition. Enter the date manually.",dateNotFound:"No unambiguous date was found in the photo.",
    latestPurchase:"Latest scanned batch",saveBatchDetails:"Save batch details",mealAllocation:"Who ate this meal?",servingShare:"Servings eaten",mealRecorded:"Meal nutrition recorded",
  },
  de:{
    quantityCoverage:"Mengen-Abdeckung",quantityShortage:"Fehlt",quantityUnknown:"Menge unsicher",enoughStock:"Mengenmäßig ausreichend",
    nutritionGoal:"Nährwertziel",balanced:"Ausgewogen",highProtein:"Proteinreich",lowerCalorie:"Kalorienärmer",highFiber:"Ballaststoffreich",lowerSaturatedFat:"Weniger gesättigte Fettsäuren",nutritionGoalHint:"Nährwerte sind nur ein Ranking-Hinweis; Ernährung/Allergien und Vorrat bleiben maßgeblich.",
    household:"Haushalt & Essensportionen",householdMembers:"Haushaltsmitglieder",householdHelp:"Ein Name pro Zeile. Nach dem Kochen können Portionen Personen zugeordnet werden, damit die bestätigten Nährwerte pro Person gespeichert werden.",saveHousehold:"Haushalt speichern",
    mealHistory:"Nährwertverlauf",today:"Heute",week:"7 Tage",month:"30 Tage",meals:"Mahlzeiten",noMealHistory:"Noch keine bestätigten Mahlzeiten gespeichert.",unassigned:"Nicht zugeordnet",
    storage:"Lagerort",fridge:"Kühlschrank",freezer:"Gefrierschrank",pantryStorage:"Vorratsschrank",otherStorage:"Sonstiges",purchaseDate:"Kaufdatum",openedAt:"Geöffnet",useWithinDays:"Nach Öffnung innerhalb von Tagen",openedToday:"Heute geöffnet",
    provenance:"Herkunft",scanExpiry:"Datum scannen",scanExpiryHelp:"Fotografiere das aufgedruckte Datum. Wenn der Browser lokale Texterkennung unterstützt, wird es direkt erkannt; sonst Datum manuell eingeben.",dateScanUnavailable:"Dieser Browser stellt keine lokale Texterkennung bereit. Datum bitte manuell eingeben.",dateNotFound:"Im Foto wurde kein eindeutiges Datum gefunden.",
    latestPurchase:"Neueste gescannte Charge",saveBatchDetails:"Chargendetails speichern",mealAllocation:"Wer hat davon gegessen?",servingShare:"Gegessene Portionen",mealRecorded:"Mahlzeiten-Nährwerte gespeichert",
  },
  el:{
    quantityCoverage:"Κάλυψη ποσότητας αποθέματος",quantityShortage:"Λείπει",quantityUnknown:"Αβέβαιη ποσότητα",enoughStock:"Επαρκές απόθεμα ως προς την ποσότητα",
    nutritionGoal:"Στόχος διατροφής",balanced:"Ισορροπημένο",highProtein:"Υψηλή πρωτεΐνη",lowerCalorie:"Λιγότερες θερμίδες",highFiber:"Περισσότερες φυτικές ίνες",lowerSaturatedFat:"Λιγότερα κορεσμένα λιπαρά",nutritionGoalHint:"Η διατροφή είναι μόνο κριτήριο κατάταξης· οι αλλεργίες/διατροφή και το πραγματικό απόθεμα παραμένουν καθοριστικά.",
    household:"Νοικοκυριό & μερίδες γεύματος",householdMembers:"Μέλη νοικοκυριού",householdHelp:"Ένα όνομα ανά γραμμή. Μετά το μαγείρεμα μπορείς να αντιστοιχίσεις μερίδες ώστε τα επιβεβαιωμένα διατροφικά στοιχεία να καταγράφονται ανά άτομο.",saveHousehold:"Αποθήκευση νοικοκυριού",
    mealHistory:"Ιστορικό διατροφής γευμάτων",today:"Σήμερα",week:"7 ημέρες",month:"30 ημέρες",meals:"γεύματα",noMealHistory:"Δεν έχουν καταγραφεί ακόμη επιβεβαιωμένα γεύματα.",unassigned:"Χωρίς αντιστοίχιση",
    storage:"Αποθήκευση",fridge:"Ψυγείο",freezer:"Κατάψυξη",pantryStorage:"Ντουλάπι",otherStorage:"Άλλο",purchaseDate:"Ημερομηνία αγοράς",openedAt:"Ανοίχτηκε",useWithinDays:"Χρήση εντός ημερών μετά το άνοιγμα",openedToday:"Ανοίχτηκε σήμερα",
    provenance:"Προέλευση",scanExpiry:"Σάρωση ημερομηνίας",scanExpiryHelp:"Φωτογράφισε την τυπωμένη ημερομηνία. Χρησιμοποιείται τοπική αναγνώριση κειμένου όταν υποστηρίζεται από τον browser, διαφορετικά γράψε την ημερομηνία χειροκίνητα.",dateScanUnavailable:"Ο browser δεν διαθέτει τοπική αναγνώριση κειμένου. Γράψε την ημερομηνία χειροκίνητα.",dateNotFound:"Δεν βρέθηκε σαφής ημερομηνία στη φωτογραφία.",
    latestPurchase:"Νεότερη σαρωμένη παρτίδα",saveBatchDetails:"Αποθήκευση στοιχείων παρτίδας",mealAllocation:"Ποιος έφαγε αυτό το γεύμα;",servingShare:"Μερίδες που καταναλώθηκαν",mealRecorded:"Καταγράφηκαν τα διατροφικά στοιχεία του γεύματος",
  },
};

class Cook4MeRecipeHubPanelV24 extends BasePanel {
  constructor(){
    super();
    this._nutritionGoal="balanced";
    this._foodState=null;
    this._foodStateLoading=false;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  async _loadCapabilities(){
    await super._loadCapabilities();
    this._nutritionGoal=String(this._uiPreferences?.nutritionGoal||this._nutritionGoal||"balanced");
  }

  _nutritionGoalOptions(){
    const rows=[
      ["balanced","balanced"],["high_protein","highProtein"],["lower_calorie","lowerCalorie"],["high_fiber","highFiber"],["lower_saturated_fat","lowerSaturatedFat"]
    ];
    return rows.map(([value,label])=>`<option value="${value}" ${value===this._nutritionGoal?"selected":""}>${this._escape(this._t(label))}</option>`).join("");
  }

  _renderRecommend(c){
    super._renderRecommend(c);
    const button=c.querySelector("#recommendBtn");
    if(!button||c.querySelector("#nutritionGoal"))return;
    const field=document.createElement("div");
    field.className="field";
    field.style.minWidth="210px";
    field.innerHTML=`<label>${this._escape(this._t("nutritionGoal"))}</label><select id="nutritionGoal">${this._nutritionGoalOptions()}</select><div class="muted">${this._escape(this._t("nutritionGoalHint"))}</div>`;
    button.parentNode?.insertBefore(field,button);
    field.querySelector("#nutritionGoal")?.addEventListener("change",event=>{
      this._nutritionGoal=String(event.target.value||"balanced");
      this._uiPreferences={...(this._uiPreferences||{}),nutritionGoal:this._nutritionGoal};
      this._schedulePreferenceSave?.();
    });
  }

  async _recommend(){
    this._opened=null;
    try{
      this._message(this._t("loading"));
      const result=await this._api("cook4me/v17/recommend",{
        entry_id:this._entryId,
        query:String(this._recommendQuery||"").trim(),
        diet:this._recommendDiet||"profile",
        nutrition_goal:this._nutritionGoal||"balanced",
        limit:24,
        catalog_size:50,
        language:this._selectedLanguage(),
        strict_language:this._strictLanguage(),
      });
      const items=result?.items||[];
      items.forEach(recipe=>this._ensureRecipeSelections(recipe));
      if(this._shouldTranslate()&&items.some(recipe=>this._translationNeeded(recipe))){
        this._message(this._t("translating"));
        await this._translateItems(items);
      }
      this._recommendations=items;
      this._message("");
      this._renderTab();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  _missingIngredientObjects(recipe){
    const shortages=recipe?.match?.quantityShortages;
    if(Array.isArray(shortages)&&shortages.length){
      return shortages.map(row=>({
        ...(row?.key?{key:row.key}:{}),
        name:String(row?.name||""),
        quantity:row?.missingQuantity,
        unit:String(row?.missingUnit||""),
        shortageOnly:true,
      })).filter(row=>row.name&&Number(row.quantity)>0);
    }
    return super._missingIngredientObjects(recipe);
  }

  _feasibilityChips(recipe){
    const match=recipe?.match||{};
    if(!Number.isFinite(Number(match.quantityCoverage)))return"";
    const coverage=Math.round(Number(match.quantityCoverage)*100);
    const shortage=(match.quantityShortages||[]).reduce((out,row)=>{
      const q=Number(row?.missingQuantity);if(!Number.isFinite(q)||q<=0)return out;
      out.push(`${row.name}: ${this._shownNumber(q)}${row.missingUnit?` ${row.missingUnit}`:""}`);return out;
    },[]);
    const unknown=(match.quantityUnknown||[]).length;
    return `<span class="chip">📦 ${this._escape(this._t("quantityCoverage"))}: ${coverage}%</span>${shortage.length?`<span class="chip warn">${this._escape(this._t("quantityShortage"))}: ${this._escape(shortage.slice(0,3).join(", "))}</span>`:""}${unknown?`<span class="chip warn">${this._escape(this._t("quantityUnknown"))}: ${unknown}</span>`:""}`;
  }

  _recipeCard(recipe,custom=false){
    let html=super._recipeCard(recipe,custom);
    const chips=this._feasibilityChips(recipe);
    if(chips)html=html.replace('<div class="chips">',`<div class="chips">${chips}`);
    const bonus=Number(recipe?.match?.nutritionGoalBonus||0);
    if(bonus>0)html=html.replace('<div class="chips">',`<div class="chips"><span class="chip">🎯 ${this._escape(this._t("nutritionGoal"))}: +${this._escape(bonus)}</span>`);
    return html;
  }

  _detailHtml(recipe){
    let html=super._detailHtml(recipe);
    if(!html||!recipe)return html;
    const match=recipe.match||{};
    if(!Number.isFinite(Number(match.quantityCoverage)))return html;
    const rows=(match.quantityAvailability||[]).filter(row=>row?.status!=="staple").map(row=>{
      const required=Number.isFinite(Number(row.requiredQuantity))?`${this._shownNumber(row.requiredQuantity)}${row.requiredUnit?` ${row.requiredUnit}`:""}`:"?";
      let state="?";
      if(row.status==="enough")state=`✓ ${this._t("enoughStock")}`;
      else if(row.status==="shortage")state=`${this._t("quantityShortage")}: ${this._shownNumber(row.missingQuantity)}${row.missingUnit?` ${row.missingUnit}`:""}`;
      else state=this._t("quantityUnknown");
      return `<div style="display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px solid var(--divider-color)"><span>${this._escape(row.name||"")} · ${this._escape(required)}</span><span class="${row.status==="shortage"?"warn":"muted"}">${this._escape(state)}</span></div>`;
    }).join("");
    const block=`<section class="card" style="margin:12px 0"><h3 style="margin-top:0">${this._escape(this._t("quantityCoverage"))}: ${Math.round(Number(match.quantityCoverage)*100)}%</h3>${rows}</section>`;
    const marker='<div class="detail-layout"';const pos=html.indexOf(marker);
    return pos>=0?`${html.slice(0,pos)}${block}${html.slice(pos)}`:`${block}${html}`;
  }

  _storageOptions(selected=""){
    const rows=[["","—"],["fridge","fridge"],["freezer","freezer"],["pantry","pantryStorage"],["other","otherStorage"]];
    return rows.map(([value,label])=>`<option value="${value}" ${value===selected?"selected":""}>${this._escape(label==="—"?label:this._t(label))}</option>`).join("");
  }

  _lotRowHtml(lot,index,unit){
    const amount=lot?.quantity===undefined||lot?.quantity===null?"":lot.quantity;
    const provenance=[lot?.productName,lot?.brand,lot?.barcode?`EAN ${lot.barcode}`:"",lot?.source].filter(Boolean).join(" · ");
    return `<div data-stock-lot="${index}" style="padding:9px 0;border-bottom:1px dashed var(--divider-color)">
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:8px;align-items:end">
        <div class="field"><label>${this._escape(this._t("amount"))}${unit?` (${this._escape(unit)})`:""}</label><input data-stock-lot-amount type="number" min="0" step="any" value="${this._escape(amount)}"></div>
        <div class="field"><label>${this._escape(this._t("bestBefore"))}</label><div style="display:flex;gap:5px"><input data-stock-lot-date type="date" value="${this._escape(lot?.bestBefore||"")}" style="min-width:0;flex:1"><button type="button" class="btn secondary" data-stock-lot-scan-date title="${this._escape(this._t("scanExpiryHelp"))}">📷</button></div></div>
        <div class="field"><label>${this._escape(this._t("storage"))}</label><select data-stock-lot-storage>${this._storageOptions(String(lot?.storage||""))}</select></div>
        <div class="field"><label>${this._escape(this._t("purchaseDate"))}</label><input data-stock-lot-purchase type="date" value="${this._escape(lot?.purchaseDate||"")}"></div>
        <div class="field"><label>${this._escape(this._t("openedAt"))}</label><div style="display:flex;gap:5px"><input data-stock-lot-opened type="date" value="${this._escape(lot?.openedAt||"")}" style="min-width:0;flex:1"><button type="button" class="btn secondary" data-stock-lot-open-today>${this._escape(this._t("openedToday"))}</button></div></div>
        <div class="field"><label>${this._escape(this._t("useWithinDays"))}</label><input data-stock-lot-use-days type="number" min="1" max="3650" step="1" value="${this._escape(lot?.useWithinDays||"")}"></div>
        <button type="button" class="btn secondary" data-stock-lot-remove style="min-height:42px">${this._escape(this._t("removeBatch"))}</button>
      </div>
      ${provenance?`<div class="muted" style="margin-top:5px"><strong>${this._escape(this._t("provenance"))}:</strong> ${this._escape(provenance)}</div>`:""}
      ${lot?.effectiveBestBefore&&lot.effectiveBestBefore!==lot.bestBefore?`<div class="muted">${this._escape(this._t("nextBestBefore"))}: ${this._escape(lot.effectiveBestBefore)}</div>`:""}
    </div>`;
  }

  _collectLots(container,row,newUnit){
    const sourceUnit=String(row?.unit||newUnit||"");
    const originals=this._rowLots(row);
    const lots=[];
    container.querySelectorAll("[data-stock-lot]").forEach((lotEl,index)=>{
      const raw=String(lotEl.querySelector("[data-stock-lot-amount]")?.value||"").trim();
      if(!raw)return;
      const amount=Number(raw.replace(",","."));if(!Number.isFinite(amount)||amount<=0)return;
      const original=originals[index]||{};
      const bestBefore=String(lotEl.querySelector("[data-stock-lot-date]")?.value||"");
      const purchaseDate=String(lotEl.querySelector("[data-stock-lot-purchase]")?.value||"");
      const openedAt=String(lotEl.querySelector("[data-stock-lot-opened]")?.value||"");
      const useWithinDays=String(lotEl.querySelector("[data-stock-lot-use-days]")?.value||"");
      const storage=String(lotEl.querySelector("[data-stock-lot-storage]")?.value||"");
      const lot={quantity:raw,unit:sourceUnit,
        ...(original.id?{id:original.id}:{}),...(original.addedAt?{addedAt:original.addedAt}:{}),
        ...(bestBefore?{bestBefore}:{}),...(purchaseDate?{purchaseDate}:{}),...(openedAt?{openedAt}:{}),...(useWithinDays?{useWithinDays}:{}),...(storage?{storage}:{}),
      };
      for(const key of ["barcode","productName","brand","source","nutritionSource"]){if(original[key])lot[key]=original[key];}
      lots.push(lot);
    });
    return lots;
  }

  _bindInventoryRows(c){
    super._bindInventoryRows(c);
    c.querySelectorAll("[data-stock-lot-open-today]").forEach(button=>button.addEventListener("click",()=>{
      const input=button.closest("[data-stock-lot]")?.querySelector("[data-stock-lot-opened]");if(input)input.value=new Date().toISOString().slice(0,10);
    }));
    c.querySelectorAll("[data-stock-lot-scan-date]").forEach(button=>button.addEventListener("click",()=>{
      const input=button.closest("[data-stock-lot]")?.querySelector("[data-stock-lot-date]");if(input)void this._scanDateIntoInput(input);
    }));
  }

  _extractDateCandidate(text){
    const value=String(text||"");
    const candidates=[];
    let match;
    const iso=/(20\d{2})[.\/-](0?[1-9]|1[0-2])[.\/-](0?[1-9]|[12]\d|3[01])/g;
    while((match=iso.exec(value)))candidates.push([Number(match[1]),Number(match[2]),Number(match[3])]);
    const european=/(0?[1-9]|[12]\d|3[01])[.\/-](0?[1-9]|1[0-2])[.\/-](20\d{2}|\d{2})/g;
    while((match=european.exec(value))){let year=Number(match[3]);if(year<100)year+=2000;candidates.push([year,Number(match[2]),Number(match[1])]);}
    for(const [year,month,day] of candidates){const d=new Date(Date.UTC(year,month-1,day));if(d.getUTCFullYear()===year&&d.getUTCMonth()===month-1&&d.getUTCDate()===day)return `${year}-${String(month).padStart(2,"0")}-${String(day).padStart(2,"0")}`;}
    return"";
  }

  async _scanDateIntoInput(target){
    if(typeof globalThis.TextDetector!=="function"){this._message(this._t("dateScanUnavailable"),true);return;}
    const picker=document.createElement("input");picker.type="file";picker.accept="image/*";picker.capture="environment";picker.style.display="none";this.shadowRoot.appendChild(picker);
    picker.addEventListener("change",async()=>{
      try{
        const file=picker.files?.[0];if(!file)return;
        const image=await createImageBitmap(file);const detector=new TextDetector();const rows=await detector.detect(image);image.close?.();
        const text=(rows||[]).map(row=>row.rawValue||"").join(" ");const stamp=this._extractDateCandidate(text);
        if(stamp){target.value=stamp;this._message("");}else this._message(this._t("dateNotFound"),true);
      }catch(_e){this._message(this._t("dateNotFound"),true);}finally{picker.remove();}
    },{once:true});picker.click();
  }

  _todayIso(){return new Date().toISOString().slice(0,10);}

  _injectManualLotMetadata(c){
    const best=c.querySelector("#stockAddBestBefore");if(!best||c.querySelector("#stockAddStorage"))return;
    const parent=best.closest(".field")?.parentNode;if(!parent)return;
    const block=document.createElement("div");block.className="field wide";
    block.innerHTML=`<div class="formgrid">
      <div class="field"><label>${this._escape(this._t("storage"))}</label><select id="stockAddStorage">${this._storageOptions("")}</select></div>
      <div class="field"><label>${this._escape(this._t("purchaseDate"))}</label><input id="stockAddPurchaseDate" type="date" value="${this._todayIso()}"></div>
      <div class="field"><label>${this._escape(this._t("openedAt"))}</label><input id="stockAddOpenedAt" type="date"></div>
      <div class="field"><label>${this._escape(this._t("useWithinDays"))}</label><input id="stockAddUseWithinDays" type="number" min="1" max="3650"></div>
      <button type="button" class="btn secondary" id="stockScanBestBefore">📷 ${this._escape(this._t("scanExpiry"))}</button>
    </div>`;
    parent.insertBefore(block,best.closest(".field")?.nextSibling||null);
    block.querySelector("#stockScanBestBefore")?.addEventListener("click",()=>void this._scanDateIntoInput(best));

    const oldButton=c.querySelector("#houseAdd");if(!oldButton)return;const button=oldButton.cloneNode(true);oldButton.replaceWith(button);
    button.addEventListener("click",async()=>{
      const select=c.querySelector("#houseCatalog");const rows=select?._cook4meRows||[];const row=rows[Number(select?.value)];if(!row)return;
      const amount=c.querySelector("#stockAddAmount");const unlimited=c.querySelector("#stockAddUnlimited");const scrollTop=select.scrollTop;const selectedValue=select.value;
      try{
        const result=await this._api("cook4me/v14/inventory_add",{
          entry_id:this._entryId,ingredient:row,...(amount?.value!==""?{quantity:amount.value}:{}),unit:String(c.querySelector("#stockAddUnit")?.value||""),unlimited:Boolean(unlimited?.checked),best_before:String(best.value||""),
          lot_metadata:{source:"manual",storage:String(c.querySelector("#stockAddStorage")?.value||""),purchaseDate:String(c.querySelector("#stockAddPurchaseDate")?.value||""),openedAt:String(c.querySelector("#stockAddOpenedAt")?.value||""),useWithinDays:String(c.querySelector("#stockAddUseWithinDays")?.value||"")}
        });
        this._houseIngredients=result?.houseIngredients||[];this._syncEntryProfile();this._renderInventoryOnly(c);select.value=selectedValue;select.scrollTop=scrollTop;if(amount)amount.value="";best.value="";this._message(this._t("stockUpdated"));
      }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    });
  }

  _latestScannedLot(){
    const barcode=String(this._scannerResult?.barcode||"");if(!barcode)return null;
    let best=null;
    for(const row of this._houseIngredients||[]){for(let i=0;i<(row.lots||[]).length;i++){const lot=row.lots[i];if(String(lot?.barcode||"")!==barcode)continue;if(!best||String(lot.addedAt||"")>String(best.lot.addedAt||""))best={row,lot,index:i};}}
    return best;
  }

  _scannerResultHtml(){
    let html=super._scannerResultHtml();
    if(this._scannerResult?.status==="needs_mapping"){
      const marker='<button id="scanMapAdd"';const pos=html.indexOf(marker);
      if(pos>=0){const meta=`<div class="formgrid" style="margin:10px 0"><div class="field"><label>${this._escape(this._t("storage"))}</label><select id="scanStorage">${this._storageOptions("")}</select></div><div class="field"><label>${this._escape(this._t("purchaseDate"))}</label><input id="scanPurchaseDate" type="date" value="${this._todayIso()}"></div><div class="field"><label>${this._escape(this._t("openedAt"))}</label><input id="scanOpenedAt" type="date"></div><div class="field"><label>${this._escape(this._t("useWithinDays"))}</label><input id="scanUseWithinDays" type="number" min="1" max="3650"></div><button id="scanExpiryCamera" type="button" class="btn secondary">📷 ${this._escape(this._t("scanExpiry"))}</button></div>`;html=`${html.slice(0,pos)}${meta}${html.slice(pos)}`;}
    }else if(this._scannerResult?.status==="added"&&this._latestScannedLot()){
      const latest=this._latestScannedLot();html+=`<div class="card" style="margin-top:8px"><strong>${this._escape(this._t("latestPurchase"))}: ${this._escape(latest.row.name||"")}</strong><div class="formgrid" style="margin-top:8px"><div class="field"><label>${this._escape(this._t("bestBefore"))}</label><input id="latestScanDate" type="date" value="${this._escape(latest.lot.bestBefore||"")}"></div><div class="field"><label>${this._escape(this._t("storage"))}</label><select id="latestScanStorage">${this._storageOptions(String(latest.lot.storage||""))}</select></div><div class="field"><label>${this._escape(this._t("openedAt"))}</label><input id="latestScanOpened" type="date" value="${this._escape(latest.lot.openedAt||"")}"></div><div class="field"><label>${this._escape(this._t("useWithinDays"))}</label><input id="latestScanUseDays" type="number" min="1" max="3650" value="${this._escape(latest.lot.useWithinDays||"")}"></div></div><div class="toolbar" style="margin-top:8px"><button id="latestScanExpiryCamera" class="btn secondary">📷 ${this._escape(this._t("scanExpiry"))}</button><button id="latestScanSave" class="btn secondary">${this._escape(this._t("saveBatchDetails"))}</button></div></div>`;
    }
    return html;
  }

  _bindScannerMapping(c){
    super._bindScannerMapping(c);
    c.querySelector("#scanExpiryCamera")?.addEventListener("click",()=>{const input=c.querySelector("#scanBestBefore");if(input)void this._scanDateIntoInput(input);});
    c.querySelector("#latestScanExpiryCamera")?.addEventListener("click",()=>{const input=c.querySelector("#latestScanDate");if(input)void this._scanDateIntoInput(input);});
    c.querySelector("#latestScanSave")?.addEventListener("click",async()=>{
      const latest=this._latestScannedLot();if(!latest)return;const lots=this._rowLots(latest.row);const lot={...lots[latest.index],bestBefore:String(c.querySelector("#latestScanDate")?.value||""),storage:String(c.querySelector("#latestScanStorage")?.value||""),openedAt:String(c.querySelector("#latestScanOpened")?.value||""),useWithinDays:String(c.querySelector("#latestScanUseDays")?.value||"")};lots[latest.index]=lot;
      try{const result=await this._api("cook4me/v14/inventory_update",{entry_id:this._entryId,identity:this._stockIdentity(latest.row),unit:String(latest.row.unit||""),unlimited:false,lots});this._houseIngredients=result?.houseIngredients||[];this._syncEntryProfile();this._renderInventoryOnly(c);this._renderScannerResult(c);}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    });

    if(this._scannerResult?.status!=="needs_mapping")return;
    const oldButton=c.querySelector("#scanMapAdd");if(!oldButton)return;const button=oldButton.cloneNode(true);oldButton.replaceWith(button);
    button.addEventListener("click",async()=>{
      const result=this._scannerResult;if(!result?.barcode)return;const ingredient=this._selectedScanIngredient(c);if(!ingredient?.name){this._scannerStatus=this._t("invalidIngredient");this._renderScannerResult(c);return;}
      const quantity=String(c.querySelector("#scanPackageAmount")?.value||"").trim();const unit=String(c.querySelector("#scanPackageUnit")?.value||"").trim();const bestBefore=String(c.querySelector("#scanBestBefore")?.value||"");if(!quantity)return;
      this._scannerBusy=true;this._scannerStatus=this._t("lookingUp");this._renderScannerResult(c);
      try{
        const mapped=await this._api("cook4me/v15/barcode_map_add",{entry_id:this._entryId,barcode:String(result.barcode),ingredient,quantity,unit,best_before:bestBefore,product_name:String(result.product?.productName||result.product?.name||""),brand:String(result.product?.brand||""),lot_metadata:{storage:String(c.querySelector("#scanStorage")?.value||""),purchaseDate:String(c.querySelector("#scanPurchaseDate")?.value||""),openedAt:String(c.querySelector("#scanOpenedAt")?.value||""),useWithinDays:String(c.querySelector("#scanUseWithinDays")?.value||"")}});
        this._houseIngredients=mapped?.houseIngredients||[];this._syncEntryProfile();this._renderInventoryOnly(c);this._scannerResult=mapped;this._scannerStatus=this._t("scannedAdded");navigator.vibrate?.(80);this._scanIngredientFilter="";this._scanSelectedIngredient="";
      }catch(e){this._scannerStatus=`${this._t("error")}: ${e.message||e}`;}finally{this._scannerBusy=false;this._renderScannerResult(c);}if(this._scannerOpen&&this._nativeBarcodeScannerAvailable()&&!this._nativeScannerActive)await this._startNativeBarcodeScanner(c);
    });
  }

  _allocationHtml(pending){
    const members=this._entry()?.profile?.householdMembers||[];if(!members.length)return"";
    return `<div class="card" style="margin-top:12px;padding:10px"><strong>${this._escape(this._t("mealAllocation"))}</strong><div class="formgrid" style="margin-top:8px">${members.map(name=>`<div class="field"><label>${this._escape(name)} · ${this._escape(this._t("servingShare"))}</label><input data-meal-member="${this._escape(name)}" type="number" min="0" step="0.25" value=""></div>`).join("")}</div><div class="muted">${this._escape(this._t("unassigned"))}: ${this._escape(pending?.servings??"—")}</div></div>`;
  }

  _pendingHtml(){
    let html=super._pendingHtml();const pending=this._pendingConsumption;if(!html||!pending?.id)return html;
    const marker='<div class="toolbar" style="margin-top:12px">';const pos=html.indexOf(marker);return pos>=0?`${html.slice(0,pos)}${this._allocationHtml(pending)}${html.slice(pos)}`:html;
  }

  _bindPending(c){
    const pending=this._pendingConsumption;if(!pending?.id)return;
    c.querySelector("#confirmConsumption")?.addEventListener("click",async()=>{
      const ingredients=[];c.querySelectorAll("[data-consume-row]").forEach(container=>{const index=Number(container.dataset.consumeRow);const row=pending.ingredients[index];if(!row)return;const unlimited=Boolean(row.stockUnlimited);ingredients.push({identity:row.identity,key:row.key,name:row.name,consume:unlimited?true:Boolean(container.querySelector("[data-consume-check]")?.checked),quantity:container.querySelector("[data-consume-amount]")?.value||null,unit:String(container.querySelector("[data-consume-unit]")?.value||"")});});
      const allocations=[];c.querySelectorAll("[data-meal-member]").forEach(input=>{const servings=Number(input.value);if(Number.isFinite(servings)&&servings>0)allocations.push({name:String(input.dataset.mealMember||""),servings});});
      try{const result=await this._api("cook4me/v14/consumption_confirm",{entry_id:this._entryId,pending_id:pending.id,ingredients,allocations});this._houseIngredients=result?.houseIngredients||result?.profile?.houseIngredients||[];this._pendingConsumption=null;this._syncEntryProfile();this._foodState=null;this._message(result?.mealHistoryRecord?this._t("mealRecorded"):this._t("consumptionUpdated"));this._renderProfile(c);}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    });
    c.querySelector("#clearConsumption")?.addEventListener("click",async()=>{try{await this._api("cook4me/v14/consumption_clear",{entry_id:this._entryId,pending_id:pending.id});this._pendingConsumption=null;this._renderProfile(c);}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}});
  }

  async _loadFoodState(){
    if(this._foodStateLoading||!this._entryId)return;this._foodStateLoading=true;
    try{this._foodState=await this._api("cook4me/v17/food_state",{entry_id:this._entryId,history_limit:12});}catch(_e){}finally{this._foodStateLoading=false;if(this._tab==="profile")this._renderTab();}
  }

  _historySummaryHtml(){
    const state=this._foodState;if(!state)return"";const blocks=[["today","today"],["week","week"],["month","month"]].map(([key,label])=>{const row=state.summary?.[key]||{};return `<div class="card" style="padding:10px"><strong>${this._escape(this._t(label))}</strong><div class="muted">${Number(row.mealCount||0)} ${this._escape(this._t("meals"))}</div><div class="chips" style="margin-top:5px">${this._nutritionChips(row.totals||{},true)}</div></div>`;}).join("");
    const recent=(state.history||[]).slice(0,6);return `<section class="card" style="margin-top:14px"><h2 style="margin-top:0">${this._escape(this._t("mealHistory"))}</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px">${blocks}</div>${recent.length?`<div style="margin-top:10px">${recent.map(row=>`<div style="padding:6px 0;border-bottom:1px solid var(--divider-color)"><strong>${this._escape(row.title||"")}</strong> · ${this._escape(String(row.timestamp||"").slice(0,16).replace("T"," "))}<div class="chips">${this._nutritionChips(row.nutrition?.totals||{},true)}</div></div>`).join("")}</div>`:`<div class="muted" style="margin-top:8px">${this._escape(this._t("noMealHistory"))}</div>`}</section>`;
  }

  _householdHtml(){
    const members=this._entry()?.profile?.householdMembers||[];return `<section class="card" style="margin-top:14px"><h2 style="margin-top:0">${this._escape(this._t("household"))}</h2><div class="field"><label>${this._escape(this._t("householdMembers"))}</label><textarea id="householdMembers">${this._escape(members.join("\n"))}</textarea><div class="muted">${this._escape(this._t("householdHelp"))}</div></div><button id="saveHousehold" class="btn secondary" style="margin-top:8px">${this._escape(this._t("saveHousehold"))}</button></section>`;
  }

  _renderProfile(c){
    super._renderProfile(c);this._injectManualLotMetadata(c);if(!this._foodState&&!this._foodStateLoading)queueMicrotask(()=>void this._loadFoodState());c.insertAdjacentHTML("beforeend",this._householdHtml()+this._historySummaryHtml());
    c.querySelector("#saveHousehold")?.addEventListener("click",async()=>{const members=[...new Set(String(c.querySelector("#householdMembers")?.value||"").split(/\r?\n|,/).map(x=>x.trim()).filter(Boolean))];try{const profile=await this._api("cook4me/profile_save",{entry_id:this._entryId,profile:{householdMembers:members}});const entry=this._entry();if(entry)entry.profile={...(entry.profile||{}),...profile};this._foodState=null;this._message(this._t("saveHousehold"));this._renderProfile(c);}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}});
  }
}

customElements.define("cook4me-recipe-hub-panel-v24",Cook4MeRecipeHubPanelV24);
