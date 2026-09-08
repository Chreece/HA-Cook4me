import "./cook4me-panel-v43.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v43");

const TEXT={
  en:{week:"Week",weeklyPlanner:"7-day meal planner",generateWeek:"Generate week",regenerate:"Regenerate",clear:"Clear",plannerSettings:"Planner settings",mealSlots:"Meal slots",breakfast:"Breakfast",lunch:"Lunch",dinner:"Dinner",snack:"Snack",leftoversFirst:"Use leftovers first",avoidRecent:"Avoid recent meals (days)",nutritionTargets:"Daily nutrition targets",targetCalories:"Calories (kcal)",targetProtein:"Protein (g)",targetFiber:"Fibre (g)",savePlanner:"Save planner settings",reservedStock:"Reserved stock",shoppingDelta:"Plan shopping",addPlanShopping:"Add shortages to Shopping List",required:"required",available:"available",shortage:"buy",unknownStock:"stock amount/unit unknown",weeklyCost:"Weekly cost",costSettings:"Cost settings",currency:"Currency",country:"Country",globalPrices:"Use worldwide Open Prices barcode observations",saveCostSettings:"Save cost settings",costHelp:"Exact purchase/lot prices are preferred. Worldwide barcode observations are estimates and are used only when an explicit package quantity/unit exists. Different currencies are never silently converted.",leftovers:"Leftovers",consumeServing:"Eat 1 serving",nutritionDashboard:"Nutrition dashboard",todayTargets:"Today vs your targets",mealCost:"Meal cost",estimatedCost:"estimated",costCoverage:"cost coverage",exactCost:"exact purchase coverage",priceInventory:"Ingredient & lot prices",purchasePrice:"Purchase price",purchaseAmount:"Purchased amount",merchant:"Shop / location",saveLotPrice:"Save exact lot price",lookupGlobal:"Find worldwide price",ingredientReference:"Generic ingredient reference",saveReference:"Save reference",completedPurchases:"Completed Shopping List → stock",reviewPurchases:"Review completed purchases",importSelected:"Add selected to stock",needsMapping:"needs mapping",needsQuantity:"needs quantity + unit",feedback:"Your feedback",rating:"Rating",wouldCookAgain:"Would cook again",yes:"Yes",no:"No",unsure:"Not set",feedbackNotes:"Notes",saveFeedback:"Save feedback",substitutions:"Substitutions",findSubstitutes:"Find substitutes",approve:"Approve",approved:"approved",advisory:"AI advisory",substitutionHelp:"Suggestions never modify an official Cook4Me recipe automatically. Only user-approved mappings are remembered.",globalPriceFound:"Global price reference stored",noGlobalPrice:"No price observation with a proven package basis was found",plannerEmpty:"No weekly plan yet.",costUnknown:"Cost unknown",refreshCost:"Refresh cost"},
  de:{week:"Woche",weeklyPlanner:"7-Tage-Speiseplan",generateWeek:"Woche erstellen",regenerate:"Neu wählen",clear:"Entfernen",plannerSettings:"Planer-Einstellungen",mealSlots:"Mahlzeiten",breakfast:"Frühstück",lunch:"Mittagessen",dinner:"Abendessen",snack:"Snack",leftoversFirst:"Reste zuerst verwenden",avoidRecent:"Kürzlich gegessene Gerichte vermeiden (Tage)",nutritionTargets:"Tägliche Nährwertziele",targetCalories:"Kalorien (kcal)",targetProtein:"Eiweiß (g)",targetFiber:"Ballaststoffe (g)",savePlanner:"Planer speichern",reservedStock:"Reservierter Vorrat",shoppingDelta:"Einkauf für den Plan",addPlanShopping:"Fehlmengen zur Einkaufsliste",required:"benötigt",available:"vorhanden",shortage:"kaufen",unknownStock:"Vorratsmenge/-einheit unbekannt",weeklyCost:"Wochenkosten",costSettings:"Kosten-Einstellungen",currency:"Währung",country:"Land",globalPrices:"Weltweite Open-Prices-Barcodedaten verwenden",saveCostSettings:"Kosten-Einstellungen speichern",costHelp:"Exakte Kauf-/Chargenpreise haben Vorrang. Weltweite Barcode-Beobachtungen sind Schätzungen und werden nur mit expliziter Packungsmenge/-einheit verwendet. Währungen werden nie stillschweigend umgerechnet.",leftovers:"Reste",consumeServing:"1 Portion essen",nutritionDashboard:"Nährwertübersicht",todayTargets:"Heute im Vergleich zu deinen Zielen",mealCost:"Gerichtskosten",estimatedCost:"geschätzt",costCoverage:"Kostenabdeckung",exactCost:"exakte Kaufpreisabdeckung",priceInventory:"Zutaten- & Chargenpreise",purchasePrice:"Kaufpreis",purchaseAmount:"Gekaufte Menge",merchant:"Geschäft / Ort",saveLotPrice:"Exakten Chargenpreis speichern",lookupGlobal:"Weltweiten Preis suchen",ingredientReference:"Generischer Zutaten-Referenzpreis",saveReference:"Referenz speichern",completedPurchases:"Erledigte Einkaufsliste → Vorrat",reviewPurchases:"Erledigte Einkäufe prüfen",importSelected:"Auswahl zum Vorrat",needsMapping:"Zuordnung nötig",needsQuantity:"Menge + Einheit nötig",feedback:"Deine Bewertung",rating:"Bewertung",wouldCookAgain:"Wieder kochen",yes:"Ja",no:"Nein",unsure:"Nicht gesetzt",feedbackNotes:"Notizen",saveFeedback:"Bewertung speichern",substitutions:"Alternativen",findSubstitutes:"Alternativen suchen",approve:"Bestätigen",approved:"bestätigt",advisory:"KI-Vorschlag",substitutionHelp:"Vorschläge ändern ein offizielles Cook4Me-Rezept niemals automatisch. Nur bestätigte Zuordnungen werden gespeichert.",globalPriceFound:"Globale Preisreferenz gespeichert",noGlobalPrice:"Keine Preisbeobachtung mit nachgewiesener Packungsbasis gefunden",plannerEmpty:"Noch kein Wochenplan vorhanden.",costUnknown:"Kosten unbekannt",refreshCost:"Kosten aktualisieren"},
  el:{week:"Εβδομάδα",weeklyPlanner:"Πλάνο γευμάτων 7 ημερών",generateWeek:"Δημιουργία εβδομάδας",regenerate:"Νέα επιλογή",clear:"Αφαίρεση",plannerSettings:"Ρυθμίσεις πλάνου",mealSlots:"Γεύματα",breakfast:"Πρωινό",lunch:"Μεσημεριανό",dinner:"Βραδινό",snack:"Σνακ",leftoversFirst:"Πρώτα τα περισσεύματα",avoidRecent:"Αποφυγή πρόσφατων γευμάτων (ημέρες)",nutritionTargets:"Ημερήσιοι διατροφικοί στόχοι",targetCalories:"Θερμίδες (kcal)",targetProtein:"Πρωτεΐνη (g)",targetFiber:"Φυτικές ίνες (g)",savePlanner:"Αποθήκευση πλάνου",reservedStock:"Δεσμευμένο απόθεμα",shoppingDelta:"Αγορές πλάνου",addPlanShopping:"Προσθήκη ελλείψεων στη λίστα αγορών",required:"απαιτούνται",available:"διαθέσιμα",shortage:"αγορά",unknownStock:"άγνωστη ποσότητα/μονάδα αποθέματος",weeklyCost:"Κόστος εβδομάδας",costSettings:"Ρυθμίσεις κόστους",currency:"Νόμισμα",country:"Χώρα",globalPrices:"Χρήση παγκόσμιων παρατηρήσεων barcode από Open Prices",saveCostSettings:"Αποθήκευση ρυθμίσεων κόστους",costHelp:"Οι ακριβείς τιμές αγοράς/παρτίδας έχουν προτεραιότητα. Οι παγκόσμιες παρατηρήσεις barcode είναι εκτιμήσεις και χρησιμοποιούνται μόνο όταν υπάρχει ρητή ποσότητα/μονάδα συσκευασίας. Διαφορετικά νομίσματα δεν μετατρέπονται σιωπηρά.",leftovers:"Περισσεύματα",consumeServing:"Κατανάλωση 1 μερίδας",nutritionDashboard:"Διατροφική εικόνα",todayTargets:"Σήμερα σε σχέση με τους στόχους σου",mealCost:"Κόστος γεύματος",estimatedCost:"εκτίμηση",costCoverage:"κάλυψη κόστους",exactCost:"κάλυψη ακριβούς τιμής αγοράς",priceInventory:"Τιμές υλικών & παρτίδων",purchasePrice:"Τιμή αγοράς",purchaseAmount:"Αγορασμένη ποσότητα",merchant:"Κατάστημα / τοποθεσία",saveLotPrice:"Αποθήκευση ακριβούς τιμής παρτίδας",lookupGlobal:"Αναζήτηση παγκόσμιας τιμής",ingredientReference:"Γενική τιμή αναφοράς υλικού",saveReference:"Αποθήκευση αναφοράς",completedPurchases:"Ολοκληρωμένες αγορές → απόθεμα",reviewPurchases:"Έλεγχος ολοκληρωμένων αγορών",importSelected:"Προσθήκη επιλεγμένων στο απόθεμα",needsMapping:"χρειάζεται αντιστοίχιση",needsQuantity:"χρειάζεται ποσότητα + μονάδα",feedback:"Η αξιολόγησή σου",rating:"Βαθμολογία",wouldCookAgain:"Θα το ξαναέφτιαχνες",yes:"Ναι",no:"Όχι",unsure:"Δεν ορίστηκε",feedbackNotes:"Σημειώσεις",saveFeedback:"Αποθήκευση αξιολόγησης",substitutions:"Αντικαταστάσεις",findSubstitutes:"Εύρεση εναλλακτικών",approve:"Έγκριση",approved:"εγκεκριμένο",advisory:"πρόταση AI",substitutionHelp:"Οι προτάσεις δεν αλλάζουν ποτέ αυτόματα μια επίσημη συνταγή Cook4Me. Αποθηκεύονται μόνο αντικαταστάσεις που εγκρίνει ο χρήστης.",globalPriceFound:"Αποθηκεύτηκε παγκόσμια αναφορά τιμής",noGlobalPrice:"Δεν βρέθηκε παρατήρηση τιμής με αποδεδειγμένη βάση συσκευασίας",plannerEmpty:"Δεν υπάρχει ακόμη εβδομαδιαίο πλάνο.",costUnknown:"Άγνωστο κόστος",refreshCost:"Ανανέωση κόστους"},
};

class Cook4MeRecipeHubPanelV44 extends BasePanel{
  constructor(){
    super();
    this._weekState=null;
    this._weekStateEntry="";
    this._weekLoading=false;
    this._reconcilePreview=null;
    this._substitutionState=new Map();
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _loadLastSection(user){
    try{
      const value=String(localStorage.getItem(this._lastSectionKey(user))||"");
      if(value==="week")return"week";
    }catch(_e){}
    return super._loadLastSection(user);
  }
  _rememberSection(section){
    if(String(section)==="week"){
      try{localStorage.setItem(this._lastSectionKey(),"week");}catch(_e){}
      return;
    }
    super._rememberSection(section);
  }

  _renderTabs(){
    super._renderTabs();
    const tabs=this.shadowRoot?.getElementById("tabs");
    if(!tabs||tabs.querySelector('[data-tab="week"]'))return;
    const button=document.createElement("button");
    button.className=`tab ${this._tab==="week"?"active":""}`;
    button.dataset.tab="week";
    button.innerHTML=`<span aria-hidden="true">📅</span><span>${this._escape(this._t("week"))}</span>`;
    button.addEventListener("click",()=>{
      this._tab="week";this._opened=null;this._rememberSection("week");this._renderTabs();this._renderTab();
    });
    const today=tabs.querySelector('[data-tab="today"]');
    today?.after(button);
  }

  _renderTab(){
    if(this._tab==="week"){
      this._rememberSection("week");
      const c=this.shadowRoot?.getElementById("content");
      if(c)this._renderWeek(c);
      if(!this._weekLoading&&(!this._weekState||this._weekStateEntry!==String(this._entryId||"")))queueMicrotask(()=>void this._loadWeekState());
      return;
    }
    return super._renderTab();
  }

  async _loadWeekState(){
    if(this._weekLoading||!this._entryId)return;
    this._weekLoading=true;
    try{
      this._weekState=await this._api("cook4me/v20/week_state",{entry_id:this._entryId,history_days:30});
      this._weekStateEntry=String(this._entryId||"");
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    finally{this._weekLoading=false;if(this._tab==="week")this._renderTab();}
  }

  _money(values){
    if(!values||typeof values!=="object"||!Object.keys(values).length)return this._t("costUnknown");
    return Object.entries(values).map(([currency,value])=>`${Number(value).toFixed(2)} ${currency}`).join(" + ");
  }
  _percent(value){const n=Number(value);return Number.isFinite(n)?`${Math.round(n*100)}%`:"—";}
  _slotTitle(slot){return slot?.recipe?.title||this._leftoverById(slot?.leftoverId)?.title||"—";}
  _leftoverById(id){return(this._weekState?.leftovers||[]).find(row=>String(row.id)===String(id));}

  _weekDayHtml(stamp){
    const slots=(this._weekState?.slots||[]).filter(row=>row.date===stamp);
    const label=new Intl.DateTimeFormat(this._hass?.language||"en",{weekday:"long",day:"2-digit",month:"2-digit"}).format(new Date(`${stamp}T12:00:00`));
    return `<section class="card rx-week-day"><h3 style="margin-top:0">${this._escape(label)}</h3>${slots.length?slots.map(slot=>{
      const cost=slot.cost||slot.recipe?.cost||{};
      const nutrition=slot.nutrition||slot.recipe?.nutrition||{};
      const kcal=Number(nutrition?.perServing?.energyKcal??nutrition?.totals?.energyKcal);
      return `<div class="rx-week-slot" data-slot-id="${this._escape(slot.id)}">
        <div><strong>${this._escape(this._t(slot.mealType||"dinner"))}</strong><div>${this._escape(this._slotTitle(slot))}</div><div class="muted">${Number.isFinite(kcal)?`${Math.round(kcal)} kcal · `:""}${this._escape(this._money(cost.totalsByCurrency))}</div></div>
        <div class="toolbar"><button class="btn secondary" data-week-regenerate="${this._escape(slot.id)}">${this._escape(this._t("regenerate"))}</button><button class="btn secondary" data-week-clear="${this._escape(slot.id)}">${this._escape(this._t("clear"))}</button></div>
      </div>`;
    }).join(""):`<div class="muted">—</div>`}</section>`;
  }

  _reservationHtml(){
    const r=this._weekState?.reservations||{};
    const rows=r.items||[];
    if(!rows.length)return`<div class="muted">—</div>`;
    return rows.map(row=>`<div class="rx-list-row"><strong>${this._escape(row.name||row.identity)}</strong> · ${this._escape(`${row.quantity} ${row.unit}`)} ${this._escape(this._t("required"))} · ${row.available===null?this._escape(this._t("unknownStock")):`${this._escape(`${row.available} ${row.unit}`)} ${this._escape(this._t("available"))}`}${Number(row.shortage)>0?` · <strong>${this._escape(`${row.shortage} ${row.unit}`)} ${this._escape(this._t("shortage"))}</strong>`:""}</div>`).join("");
  }

  _shoppingDeltaHtml(){
    const rows=this._weekState?.shoppingDelta||[];
    if(!rows.length)return`<div class="muted">—</div>`;
    return rows.map(row=>`<div class="rx-list-row"><strong>${this._escape(row.name)}</strong> · ${this._escape(`${row.quantity} ${row.unit}`)}</div>`).join("");
  }

  _leftoversHtml(){
    const rows=this._weekState?.leftovers||[];
    if(!rows.length)return`<div class="muted">—</div>`;
    return rows.map(row=>`<div class="rx-list-row"><strong>${this._escape(row.title||"Leftovers")}</strong> · ${this._escape(row.servings)} ${this._escape(this._t("servings"))} · ${this._escape(this._money(row.costByCurrency))}<button class="btn secondary" data-leftover-consume="${this._escape(row.id)}" style="margin-left:8px">${this._escape(this._t("consumeServing"))}</button></div>`).join("");
  }

  _dashboardHtml(){
    const d=this._weekState?.nutritionDashboard||{};
    const progress=d.todayTargetProgress||{};
    const targetRows=Object.entries(progress).map(([key,row])=>`<div class="rx-target-row"><span>${this._escape(key)}</span><div class="rx-target-bar"><i style="width:${Math.min(100,Math.max(0,Number(row.fraction||0)*100))}%"></i></div><strong>${this._escape(`${row.value} / ${row.target}`)}</strong></div>`).join("");
    const recent=(d.series||[]).slice(-7).reverse().map(row=>`<tr><td>${this._escape(row.date)}</td><td>${this._escape(row.mealCount)}</td><td>${this._escape(Math.round(Number(row.nutrition?.energyKcal||0)))}</td><td>${this._escape(Number(row.nutrition?.protein||0).toFixed(1))}</td><td>${this._escape(this._money(row.costByCurrency))}</td></tr>`).join("");
    return `${targetRows?`<h4>${this._escape(this._t("todayTargets"))}</h4>${targetRows}`:""}<div style="overflow:auto"><table class="rx-week-table"><thead><tr><th>Date</th><th>Meals</th><th>kcal</th><th>Protein</th><th>${this._escape(this._t("mealCost"))}</th></tr></thead><tbody>${recent}</tbody></table></div>`;
  }

  _costInventoryHtml(){
    const inventory=this._entry()?.profile?.houseIngredients||[];
    const defaultCurrency=this._weekState?.costSettings?.currency||"";
    const defaultCountry=this._weekState?.costSettings?.country||this._weekState?.suggestedCountry||"";
    if(!inventory.length)return`<div class="muted">—</div>`;
    return inventory.map((row,rowIndex)=>{
      const lots=row.lots||[];
      const lotHtml=lots.map(lot=>`<div class="rx-price-row" data-lot-id="${this._escape(lot.id||"")}" data-barcode="${this._escape(lot.barcode||"")}">
        <div><strong>${this._escape(lot.productName||row.name)}</strong><div class="muted">${this._escape(`${lot.quantity??"?"} ${row.unit||""}`)}${lot.barcode?` · ${this._escape(lot.barcode)}`:""}</div></div>
        <input data-price type="number" min="0" step="0.01" placeholder="${this._escape(this._t("purchasePrice"))}"><input data-currency maxlength="3" value="${this._escape(defaultCurrency)}" placeholder="EUR"><input data-basis-qty type="number" min="0" step="any" value="${this._escape(lot.quantity??"")}" placeholder="${this._escape(this._t("purchaseAmount"))}"><input data-basis-unit value="${this._escape(row.unit||"")}" placeholder="g"><input data-country maxlength="2" value="${this._escape(defaultCountry)}" placeholder="DE"><input data-merchant placeholder="${this._escape(this._t("merchant"))}"><button class="btn secondary" data-save-lot>${this._escape(this._t("saveLotPrice"))}</button>${lot.barcode?`<button class="btn secondary" data-global-price>${this._escape(this._t("lookupGlobal"))}</button>`:""}
      </div>`).join("");
      return `<div class="rx-ingredient-price"><h4>${this._escape(row.name)}</h4>${lotHtml}<div class="rx-reference-row" data-ingredient-index="${rowIndex}"><span class="muted">${this._escape(this._t("ingredientReference"))}</span><input data-ref-price type="number" min="0" step="0.01" placeholder="${this._escape(this._t("purchasePrice"))}"><input data-ref-currency maxlength="3" value="${this._escape(defaultCurrency)}" placeholder="EUR"><input data-ref-qty type="number" min="0" step="any" placeholder="100"><input data-ref-unit value="${this._escape(row.unit||"")}" placeholder="g"><button class="btn secondary" data-save-reference>${this._escape(this._t("saveReference"))}</button></div></div>`;
    }).join("");
  }

  _reconcileHtml(){
    if(!this._reconcilePreview)return`<button id="reviewPurchases" class="btn secondary">${this._escape(this._t("reviewPurchases"))}</button>`;
    const rows=this._reconcilePreview.items||[];
    if(!rows.length)return`<div class="muted">—</div><button id="reviewPurchases" class="btn secondary">${this._escape(this._t("reviewPurchases"))}</button>`;
    return `<div>${rows.map((row,index)=>{
      const suggestions=row.suggestions||[];
      const mapping=row.ingredient?`<span>${this._escape(row.ingredient.name||row.name)}</span>`:suggestions.length?`<select data-reconcile-map>${suggestions.map((s,i)=>`<option value="${i}">${this._escape(s.ingredient?.name||s.name||`#${i+1}`)}</option>`).join("")}</select>`:`<span class="warn">${this._escape(row.status==="needs_mapping"?this._t("needsMapping"):this._t("needsQuantity"))}</span>`;
      return `<div class="rx-reconcile-row" data-reconcile-index="${index}"><input type="checkbox" data-reconcile-check ${row.status==="ready"||suggestions.length?"checked":""} ${row.status==="needs_quantity_and_unit"?"disabled":""}><span>${this._escape(row.summary)}</span>${mapping}<input data-rec-best-before type="date"><input data-rec-price type="number" min="0" step="0.01" placeholder="${this._escape(this._t("purchasePrice"))}"><input data-rec-currency maxlength="3" value="${this._escape(this._weekState?.costSettings?.currency||"")}" placeholder="EUR"><input data-rec-purchase-qty type="number" min="0" step="any" value="${this._escape(row.quantity??"")}"><input data-rec-purchase-unit value="${this._escape(row.unit||"")}"></div>`;
    }).join("")}</div><button id="importPurchases" class="btn">${this._escape(this._t("importSelected"))}</button>`;
  }

  _renderWeek(c){
    const s=this._weekState;
    if(!s){c.innerHTML=`<section class="card"><h2>${this._escape(this._t("weeklyPlanner"))}</h2><div class="empty">${this._escape(this._weekLoading?this._t("loading"):this._t("plannerEmpty"))}</div></section>`;return;}
    const start=new Date(`${s.weekStart}T12:00:00`);
    const days=Array.from({length:7},(_,i)=>{const d=new Date(start);d.setDate(d.getDate()+i);return d.toISOString().slice(0,10)});
    const settings=s.settings||{};const types=new Set(settings.mealTypes||[]);const targets=settings.nutritionTargets||{};const cost=s.costSettings||{};
    c.innerHTML=`<style id="cook4meWeekV44Styles">
      .rx-week-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px}.rx-week-slot{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:9px;align-items:center;padding:10px 0;border-top:1px solid var(--divider-color)}.rx-week-slot:first-of-type{border-top:0}.rx-week-table{width:100%;border-collapse:collapse}.rx-week-table th,.rx-week-table td{text-align:left;padding:7px;border-bottom:1px solid var(--divider-color);white-space:nowrap}.rx-target-row{display:grid;grid-template-columns:120px minmax(80px,1fr) auto;gap:8px;align-items:center;margin:7px 0}.rx-target-bar{height:8px;background:var(--secondary-background-color);border-radius:999px;overflow:hidden}.rx-target-bar i{display:block;height:100%;background:var(--primary-color)}.rx-price-row{display:grid;grid-template-columns:minmax(180px,1.5fr) repeat(6,minmax(80px,1fr));gap:7px;align-items:center;padding:8px 0;border-top:1px solid var(--divider-color)}.rx-reference-row,.rx-reconcile-row{display:grid;grid-template-columns:auto repeat(5,minmax(80px,1fr));gap:7px;align-items:center;padding:7px 0}.rx-ingredient-price{padding:8px 0;border-top:1px solid var(--divider-color)}@media(max-width:900px){.rx-price-row,.rx-reference-row,.rx-reconcile-row{grid-template-columns:1fr 1fr}.rx-price-row>div,.rx-reference-row>span,.rx-reconcile-row>span{grid-column:1/-1}}
    </style>
    <section class="card"><div class="toolbar" style="justify-content:space-between"><div><h2 style="margin:0">${this._escape(this._t("weeklyPlanner"))}</h2><div class="muted">${this._escape(s.weekStart)} · ${this._escape(this._t("weeklyCost"))}: ${this._escape(this._money(s.weeklyCostByCurrency))}</div></div><button id="generateWeek" class="btn">${this._escape(this._t("generateWeek"))}</button></div></section>
    <div class="two" style="margin-top:12px"><section class="card"><h3>${this._escape(this._t("plannerSettings"))}</h3><div class="toolbar">${["breakfast","lunch","dinner","snack"].map(type=>`<label><input type="checkbox" data-week-meal="${type}" ${types.has(type)?"checked":""}> ${this._escape(this._t(type))}</label>`).join("")}</div><label style="display:block;margin-top:10px"><input id="leftoversFirst" type="checkbox" ${settings.leftoversFirst?"checked":""}> ${this._escape(this._t("leftoversFirst"))}</label><div class="field"><label>${this._escape(this._t("avoidRecent"))}</label><input id="avoidRecentDays" type="number" min="0" max="90" value="${this._escape(settings.avoidRecentDays??7)}"></div><h4>${this._escape(this._t("nutritionTargets"))}</h4><div class="formgrid"><div class="field"><label>${this._escape(this._t("targetCalories"))}</label><input id="targetCalories" type="number" min="0" value="${this._escape(targets.energyKcal??"")}"></div><div class="field"><label>${this._escape(this._t("targetProtein"))}</label><input id="targetProtein" type="number" min="0" value="${this._escape(targets.protein??"")}"></div><div class="field"><label>${this._escape(this._t("targetFiber"))}</label><input id="targetFiber" type="number" min="0" value="${this._escape(targets.fiber??"")}"></div></div><button id="savePlanner" class="btn secondary">${this._escape(this._t("savePlanner"))}</button></section>
    <section class="card"><h3>${this._escape(this._t("costSettings"))}</h3><div class="muted">${this._escape(this._t("costHelp"))}</div><div class="formgrid" style="margin-top:10px"><div class="field"><label>${this._escape(this._t("currency"))}</label><input id="costCurrency" maxlength="3" value="${this._escape(cost.currency||"")}" placeholder="EUR"></div><div class="field"><label>${this._escape(this._t("country"))}</label><input id="costCountry" maxlength="2" value="${this._escape(cost.country||s.suggestedCountry||"")}" placeholder="DE"></div></div><label><input id="autoGlobalPrices" type="checkbox" ${cost.autoGlobalPrices!==false?"checked":""}> ${this._escape(this._t("globalPrices"))}</label><div><button id="saveCostSettings" class="btn secondary" style="margin-top:10px">${this._escape(this._t("saveCostSettings"))}</button></div></section></div>
    <h2>${this._escape(this._t("mealSlots"))}</h2><div class="rx-week-grid">${days.map(day=>this._weekDayHtml(day)).join("")}</div>
    <div class="two" style="margin-top:12px"><section class="card"><h3>${this._escape(this._t("reservedStock"))}</h3>${this._reservationHtml()}</section><section class="card"><h3>${this._escape(this._t("shoppingDelta"))}</h3>${this._shoppingDeltaHtml()}<button id="addPlanShopping" class="btn" style="margin-top:10px" ${!(s.shoppingDelta||[]).length?"disabled":""}>${this._escape(this._t("addPlanShopping"))}</button></section></div>
    <div class="two" style="margin-top:12px"><section class="card"><h3>${this._escape(this._t("leftovers"))}</h3>${this._leftoversHtml()}</section><section class="card"><h3>${this._escape(this._t("nutritionDashboard"))}</h3>${this._dashboardHtml()}</section></div>
    <section class="card" style="margin-top:12px"><h3>${this._escape(this._t("priceInventory"))}</h3>${this._costInventoryHtml()}</section>
    <section class="card" style="margin-top:12px"><h3>${this._escape(this._t("completedPurchases"))}</h3>${this._reconcileHtml()}</section>`;
    this._bindWeek(c);
  }

  _weekTargets(c){const values={};const kcal=Number(c.querySelector("#targetCalories")?.value);const protein=Number(c.querySelector("#targetProtein")?.value);const fiber=Number(c.querySelector("#targetFiber")?.value);if(kcal>0)values.energyKcal=kcal;if(protein>0)values.protein=protein;if(fiber>0)values.fiber=fiber;return values;}

  _bindWeek(c){
    c.querySelector("#generateWeek")?.addEventListener("click",()=>void this._generateWeek());
    c.querySelector("#savePlanner")?.addEventListener("click",async()=>{try{this._weekState=await this._api("cook4me/v20/week_settings_set",{entry_id:this._entryId,meal_types:[...c.querySelectorAll("[data-week-meal]:checked")].map(x=>x.dataset.weekMeal),leftovers_first:Boolean(c.querySelector("#leftoversFirst")?.checked),avoid_recent_days:Number(c.querySelector("#avoidRecentDays")?.value||7),nutrition_targets:this._weekTargets(c)});this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}});
    c.querySelector("#saveCostSettings")?.addEventListener("click",async()=>{try{this._weekState=await this._api("cook4me/v20/cost_settings_set",{entry_id:this._entryId,currency:String(c.querySelector("#costCurrency")?.value||"").toUpperCase(),country:String(c.querySelector("#costCountry")?.value||"").toUpperCase(),auto_global_prices:Boolean(c.querySelector("#autoGlobalPrices")?.checked)});this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}});
    c.querySelectorAll("[data-week-clear]").forEach(b=>b.addEventListener("click",()=>void this._weekClear(b.dataset.weekClear)));
    c.querySelectorAll("[data-week-regenerate]").forEach(b=>b.addEventListener("click",()=>void this._generateWeek(b.dataset.weekRegenerate)));
    c.querySelector("#addPlanShopping")?.addEventListener("click",()=>void this._addPlanShopping());
    c.querySelectorAll("[data-leftover-consume]").forEach(b=>b.addEventListener("click",()=>void this._consumeLeftover(b.dataset.leftoverConsume)));
    c.querySelectorAll("[data-save-lot]").forEach(b=>b.addEventListener("click",()=>void this._saveLotPrice(b.closest("[data-lot-id]"))));
    c.querySelectorAll("[data-global-price]").forEach(b=>b.addEventListener("click",()=>void this._globalPrice(b.closest("[data-lot-id]"))));
    c.querySelectorAll("[data-save-reference]").forEach(b=>b.addEventListener("click",()=>void this._saveIngredientReference(b.closest("[data-ingredient-index]"))));
    c.querySelector("#reviewPurchases")?.addEventListener("click",()=>void this._reviewPurchases());
    c.querySelector("#importPurchases")?.addEventListener("click",()=>void this._importPurchases(c));
  }

  async _generateWeek(replace=""){if(!this._entryId)return;try{this._message(this._t("loading"));this._weekState=await this._api("cook4me/v20/week_generate",{entry_id:this._entryId,week_start:this._weekState?.weekStart,replace_slot_id:replace||""});this._message("");this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}}
  async _weekClear(id){try{this._weekState=await this._api("cook4me/v20/week_slot_clear",{entry_id:this._entryId,slot_id:id});this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}}
  async _addPlanShopping(){try{const r=await this._api("cook4me/v20/week_add_shopping",{entry_id:this._entryId});this._message(`${r.added?.length||0} ${this._t("shoppingDelta")}`);}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}}
  async _consumeLeftover(id){try{const r=await this._api("cook4me/v20/leftover_consume",{entry_id:this._entryId,leftover_id:id,servings:1});this._weekState=r;this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}}

  async _saveLotPrice(row){if(!row)return;try{await this._api("cook4me/v20/lot_cost_set",{entry_id:this._entryId,lot_id:row.dataset.lotId,price:row.querySelector("[data-price]")?.value,currency:row.querySelector("[data-currency]")?.value,purchase_quantity:row.querySelector("[data-basis-qty]")?.value,purchase_unit:row.querySelector("[data-basis-unit]")?.value,country:row.querySelector("[data-country]")?.value,merchant:row.querySelector("[data-merchant]")?.value});this._weekState=await this._api("cook4me/v20/week_state",{entry_id:this._entryId});this._message(this._t("save"));this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}}
  async _globalPrice(row){if(!row?.dataset.barcode)return;try{const r=await this._api("cook4me/v20/global_price_lookup",{entry_id:this._entryId,barcode:row.dataset.barcode,currency:this._weekState?.costSettings?.currency||"",country:this._weekState?.costSettings?.country||""});this._message(r.storedReference?this._t("globalPriceFound"):this._t("noGlobalPrice"),!r.storedReference);this._weekState=await this._api("cook4me/v20/week_state",{entry_id:this._entryId});this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}}
  async _saveIngredientReference(row){if(!row)return;const ingredient=(this._entry()?.profile?.houseIngredients||[])[Number(row.dataset.ingredientIndex)];if(!ingredient)return;try{await this._api("cook4me/v20/price_reference_set",{entry_id:this._entryId,ingredient,price:row.querySelector("[data-ref-price]")?.value,currency:row.querySelector("[data-ref-currency]")?.value,basis_quantity:row.querySelector("[data-ref-qty]")?.value,basis_unit:row.querySelector("[data-ref-unit]")?.value,country:this._weekState?.costSettings?.country||""});this._message(this._t("save"));}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}}
  async _reviewPurchases(){try{this._reconcilePreview=await this._api("cook4me/v20/shopping_reconcile_preview",{entry_id:this._entryId});this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}}
  async _importPurchases(c){const items=[];c.querySelectorAll("[data-reconcile-index]").forEach(row=>{if(!row.querySelector("[data-reconcile-check]")?.checked)return;const raw=this._reconcilePreview?.items?.[Number(row.dataset.reconcileIndex)];if(!raw)return;let ingredient=raw.ingredient;const select=row.querySelector("[data-reconcile-map]");if(!ingredient&&select){ingredient=raw.suggestions?.[Number(select.value)]?.ingredient}if(!ingredient||!raw.quantity||!raw.unit)return;items.push({uid:raw.uid,ingredient,quantity:raw.quantity,unit:raw.unit,best_before:row.querySelector("[data-rec-best-before]")?.value||"",price:row.querySelector("[data-rec-price]")?.value||"",currency:row.querySelector("[data-rec-currency]")?.value||"",purchase_quantity:row.querySelector("[data-rec-purchase-qty]")?.value||"",purchase_unit:row.querySelector("[data-rec-purchase-unit]")?.value||""})});try{await this._api("cook4me/v20/shopping_reconcile_apply",{entry_id:this._entryId,items,remove_completed:false});await this._loadOverview(true,false);this._reconcilePreview=null;await this._loadWeekState();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}}

  async _loadRecipeNutrition(recipe,resolveMissing=true){
    const result=await super._loadRecipeNutrition(recipe,resolveMissing);
    if(recipe&&this._entryId){
      try{recipe.cost=await this._api("cook4me/v20/recipe_cost",{entry_id:this._entryId,recipe:this._nutritionRecipePayload(recipe),refresh_global:false});if(this._opened&&this._recipeKey&&this._recipeKey(this._opened)===this._recipeKey(recipe))this._opened.cost=recipe.cost;}catch(_e){}
      if(this._opened)this._renderTab();
    }
    return result;
  }

  _feedbackFor(recipe){const rows=Object.values(this._weekState?.feedback||{});const ids=[recipe?.groupingFunctionalId,recipe?.recipeFunctionalId,recipe?.variantFunctionalId,recipe?.id].filter(Boolean).map(String);return rows.find(row=>ids.some(id=>String(row.recipeKey||"").endsWith(`:${id}`)))||rows.find(row=>String(row.title||"")===String(recipe?.title||""))||null;}
  _subKey(ingredient){return String(ingredient?.foodKey||ingredient?.key||ingredient?.foodName||ingredient?.name||"").trim().toLowerCase();}

  _lifecycleDetailBlock(recipe){
    if(!recipe)return"";const cost=recipe.cost||{};const feedback=this._feedbackFor(recipe)||{};const ingredients=(recipe.ingredients||[]).filter(x=>x&&typeof x==="object");
    const costBlock=`<section class="card" data-v44-cost style="margin:12px 0"><h3 style="margin-top:0">${this._escape(this._t("mealCost"))}</h3><div class="chips"><span class="chip">${this._escape(this._money(cost.totalsByCurrency))}</span>${Number.isFinite(Number(cost.coverage))?`<span class="chip">${this._escape(this._t("costCoverage"))}: ${this._escape(this._percent(cost.coverage))}</span>`:""}${Number.isFinite(Number(cost.exactPurchaseCoverage))?`<span class="chip">${this._escape(this._t("exactCost"))}: ${this._escape(this._percent(cost.exactPurchaseCoverage))}</span>`:""}${cost.estimated?`<span class="chip">${this._escape(this._t("estimatedCost"))}</span>`:""}</div></section>`;
    const feedbackBlock=`<section class="card" data-v44-feedback style="margin:12px 0"><h3 style="margin-top:0">${this._escape(this._t("feedback"))}</h3><div class="formgrid"><div class="field"><label>${this._escape(this._t("rating"))}</label><select id="recipeRating"><option value="">—</option>${[1,2,3,4,5].map(v=>`<option value="${v}" ${Number(feedback.rating)===v?"selected":""}>${v} ★</option>`).join("")}</select></div><div class="field"><label>${this._escape(this._t("wouldCookAgain"))}</label><select id="recipeAgain"><option value="" ${feedback.wouldCookAgain==null?"selected":""}>${this._escape(this._t("unsure"))}</option><option value="yes" ${feedback.wouldCookAgain===true?"selected":""}>${this._escape(this._t("yes"))}</option><option value="no" ${feedback.wouldCookAgain===false?"selected":""}>${this._escape(this._t("no"))}</option></select></div><div class="field wide"><label>${this._escape(this._t("feedbackNotes"))}</label><input id="recipeFeedbackNotes" value="${this._escape(feedback.notes||"")}"></div></div><button id="saveRecipeFeedback" class="btn secondary">${this._escape(this._t("saveFeedback"))}</button></section>`;
    const subs=ingredients.map((ingredient,index)=>{const key=this._subKey(ingredient);const state=this._substitutionState.get(key)||{};const approved=state.approved||[];const suggestions=state.suggestions||[];return `<div class="rx-list-row"><strong>${this._escape(this._ingredientName(ingredient))}</strong><button class="btn secondary" data-sub-suggest="${index}" style="margin-left:8px">${this._escape(this._t("findSubstitutes"))}</button>${approved.map((row,i)=>`<span class="chip">✓ ${this._escape(row.ingredient?.name||"")} · ${this._escape(this._t("approved"))}</span>`).join("")}${suggestions.map((row,i)=>`<span class="chip">${this._escape(row.ingredient?.name||"")} · ${this._escape(this._t("advisory"))} <button data-sub-approve="${index}:${i}">${this._escape(this._t("approve"))}</button></span>`).join("")}</div>`}).join("");
    const substitutionBlock=ingredients.length?`<section class="card" data-v44-substitutions style="margin:12px 0"><h3 style="margin-top:0">${this._escape(this._t("substitutions"))}</h3><div class="muted">${this._escape(this._t("substitutionHelp"))}</div>${subs}</section>`:"";
    return costBlock+feedbackBlock+substitutionBlock;
  }

  _detailHtml(recipe){let html=super._detailHtml(recipe);if(!html||!recipe||html.includes("data-v44-feedback"))return html;const block=this._lifecycleDetailBlock(recipe);const marker='<div class="detail-layout"';const pos=html.indexOf(marker);return pos>=0?`${html.slice(0,pos)}${block}${html.slice(pos)}`:`${block}${html}`;}

  _bindDetail(c){
    super._bindDetail(c);const recipe=this._opened;if(!recipe)return;
    c.querySelector("#saveRecipeFeedback")?.addEventListener("click",async()=>{const rating=c.querySelector("#recipeRating")?.value;const again=c.querySelector("#recipeAgain")?.value;const payload={entry_id:this._entryId,recipe,rating:rating||undefined,notes:c.querySelector("#recipeFeedbackNotes")?.value||""};if(again)payload.would_cook_again=again==="yes";try{const saved=await this._api("cook4me/v20/feedback_set",payload);if(!this._weekState)this._weekState={feedback:{}};this._weekState.feedback=this._weekState.feedback||{};this._weekState.feedback[saved.recipeKey]=saved;this._message(this._t("save"));this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}});
    const ingredients=(recipe.ingredients||[]).filter(x=>x&&typeof x==="object");
    c.querySelectorAll("[data-sub-suggest]").forEach(button=>button.addEventListener("click",async()=>{const ingredient=ingredients[Number(button.dataset.subSuggest)];if(!ingredient)return;try{const result=await this._api("cook4me/v20/substitution_suggest",{entry_id:this._entryId,ingredient,use_ai:true});this._substitutionState.set(this._subKey(ingredient),result);this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}}));
    c.querySelectorAll("[data-sub-approve]").forEach(button=>button.addEventListener("click",async()=>{const [ingredientIndex,suggestionIndex]=String(button.dataset.subApprove).split(":").map(Number);const ingredient=ingredients[ingredientIndex];const state=this._substitutionState.get(this._subKey(ingredient))||{};const substitute=state.suggestions?.[suggestionIndex]?.ingredient;if(!ingredient||!substitute)return;try{await this._api("cook4me/v20/substitution_approve",{entry_id:this._entryId,ingredient,substitute,note:state.suggestions?.[suggestionIndex]?.note||""});const result=await this._api("cook4me/v20/substitution_suggest",{entry_id:this._entryId,ingredient,use_ai:false});this._substitutionState.set(this._subKey(ingredient),result);this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}}));
  }
}

customElements.define("cook4me-recipe-hub-panel-v44",Cook4MeRecipeHubPanelV44);
