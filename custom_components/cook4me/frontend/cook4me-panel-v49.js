import "./cook4me-panel-v48.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v48");
const AI_MEAL_TYPES=["breakfast","starter","salad","soup","main","side","dessert","snack"];

const TEXT={
  en:{
    officialCatalogs:"Catalog languages",officialCatalogsHelp:"Search all selected official Cook4Me source catalogs. Online catalog data is cached and is not rechecked more than once per day.",
    targetDevices:"Target devices",targetDevicesHelp:"The primary Cook4Me above supplies profile/catalog context. Official recipe delivery is serialized to the selected target devices.",selectedDevices:"devices",selectAll:"Select all",deselectAll:"Deselect all",
    aiCreateTitle:"Create AI recipe",aiCreateHelp:"Create one recipe directly from the same preferences used by Today's suggestions. There is no separate AI batch queue; all Cook4Me work shares one serialized request lane.",
    aiRequest:"Recipe request",aiRequestPlaceholder:"Optional, e.g. creamy mushroom risotto",createAi:"Create recipe",aiWaiting:"Waiting for earlier Cook4Me work to finish…",aiRunning:"Generating AI recipe…",aiCreated:"AI recipe created",serializedWork:"Requests are serialized",preferredIngredients:"Preferred ingredients",mealTypes:"Meal types",catalogLanguages:"Catalog languages",onlyHome:"Only what I have at home",preferExpiring:"Prefer food expiring soon",avoidRecent:"Avoid meals cooked recently",maxMissing:"Maximum known missing ingredients",calorieTolerance:"Calorie tolerance",nutritionTarget:"Nutrition target",calorieTarget:"Calories per serving target",dietFilter:"Diet filter",profileDiet:"Profile diet",days:"days",dontAvoid:"Do not avoid",loadingCatalogs:"Loading catalog languages…",
    sendTargetsDone:"Cook4Me targets processed",onlineCacheHelp:"Online content is kept until an upstream change is detected. Revalidation is never performed less than 24 hours after the previous check.",
  },
  de:{
    officialCatalogs:"Katalogsprachen",officialCatalogsHelp:"Durchsucht alle ausgewählten offiziellen Cook4Me-Quellkataloge. Online-Katalogdaten werden zwischengespeichert und höchstens einmal pro Tag erneut geprüft.",
    targetDevices:"Zielgeräte",targetDevicesHelp:"Das primäre Cook4Me oben liefert Profil-/Katalogkontext. Offizielle Rezepte werden nacheinander an die ausgewählten Zielgeräte gesendet.",selectedDevices:"Geräte",selectAll:"Alle auswählen",deselectAll:"Alle abwählen",
    aiCreateTitle:"KI-Rezept erstellen",aiCreateHelp:"Erstellt direkt ein Rezept mit denselben Optionen wie die heutigen Vorschläge. Es gibt keine separate KI-Stapelwarteschlange; alle Cook4Me-Vorgänge teilen sich eine serielle Arbeitswarteschlange.",
    aiRequest:"Rezeptwunsch",aiRequestPlaceholder:"Optional, z. B. cremiges Pilzrisotto",createAi:"Rezept erstellen",aiWaiting:"Warte auf vorherige Cook4Me-Arbeit…",aiRunning:"KI-Rezept wird erstellt…",aiCreated:"KI-Rezept erstellt",serializedWork:"Anfragen werden seriell ausgeführt",preferredIngredients:"Bevorzugte Zutaten",mealTypes:"Mahlzeitentypen",catalogLanguages:"Katalogsprachen",onlyHome:"Nur mit dem, was ich zu Hause habe",preferExpiring:"Bald ablaufende Lebensmittel bevorzugen",avoidRecent:"Kürzlich gekochte Gerichte vermeiden",maxMissing:"Maximal bekannte fehlende Zutaten",calorieTolerance:"Kalorientoleranz",nutritionTarget:"Nährwertziel",calorieTarget:"Kalorienziel pro Portion",dietFilter:"Ernährungsfilter",profileDiet:"Profil-Ernährung",days:"Tage",dontAvoid:"Nicht vermeiden",loadingCatalogs:"Katalogsprachen werden geladen…",
    sendTargetsDone:"Cook4Me-Zielgeräte verarbeitet",onlineCacheHelp:"Online-Inhalte bleiben gespeichert, bis eine Änderung an der Quelle erkannt wird. Eine erneute Prüfung erfolgt nie früher als 24 Stunden nach der vorherigen Prüfung.",
  },
  el:{
    officialCatalogs:"Γλώσσες καταλόγου",officialCatalogsHelp:"Αναζητά σε όλους τους επιλεγμένους επίσημους καταλόγους Cook4Me. Τα online δεδομένα αποθηκεύονται και δεν ελέγχονται ξανά συχνότερα από μία φορά την ημέρα.",
    targetDevices:"Συσκευές στόχου",targetDevicesHelp:"Το κύριο Cook4Me παραπάνω παρέχει το προφίλ/πλαίσιο καταλόγου. Οι επίσημες συνταγές στέλνονται σειριακά στις επιλεγμένες συσκευές.",selectedDevices:"συσκευές",selectAll:"Επιλογή όλων",deselectAll:"Αποεπιλογή όλων",
    aiCreateTitle:"Δημιουργία συνταγής AI",aiCreateHelp:"Δημιουργεί απευθείας μία συνταγή με τις ίδιες επιλογές των σημερινών προτάσεων. Δεν υπάρχει ξεχωριστή ουρά AI· όλες οι εργασίες Cook4Me χρησιμοποιούν μία σειριακή ουρά.",
    aiRequest:"Αίτημα συνταγής",aiRequestPlaceholder:"Προαιρετικό, π.χ. κρεμώδες ριζότο μανιταριών",createAi:"Δημιουργία συνταγής",aiWaiting:"Αναμονή να ολοκληρωθεί προηγούμενη εργασία Cook4Me…",aiRunning:"Δημιουργία συνταγής AI…",aiCreated:"Η συνταγή AI δημιουργήθηκε",serializedWork:"Τα αιτήματα εκτελούνται σειριακά",preferredIngredients:"Προτιμώμενα υλικά",mealTypes:"Τύποι γεύματος",catalogLanguages:"Γλώσσες καταλόγου",onlyHome:"Μόνο με όσα έχω στο σπίτι",preferExpiring:"Προτίμηση τροφίμων που λήγουν σύντομα",avoidRecent:"Αποφυγή πρόσφατα μαγειρεμένων γευμάτων",maxMissing:"Μέγιστα γνωστά υλικά που λείπουν",calorieTolerance:"Ανοχή θερμίδων",nutritionTarget:"Διατροφικός στόχος",calorieTarget:"Στόχος θερμίδων ανά μερίδα",dietFilter:"Φίλτρο διατροφής",profileDiet:"Διατροφή προφίλ",days:"ημέρες",dontAvoid:"Χωρίς αποφυγή",loadingCatalogs:"Φόρτωση γλωσσών καταλόγου…",
    sendTargetsDone:"Ολοκληρώθηκε η επεξεργασία συσκευών Cook4Me",onlineCacheHelp:"Το online περιεχόμενο διατηρείται μέχρι να εντοπιστεί αλλαγή στην πηγή. Νέος έλεγχος δεν γίνεται ποτέ πριν περάσουν 24 ώρες από τον προηγούμενο.",
  },
};

class Cook4MeRecipeHubPanelV49 extends BasePanel{
  constructor(){
    super();
    this._cook4meApiTail=Promise.resolve();
    this._cook4meApiInflight=new Map();
    this._officialLanguages=null;
    this._aiSettings=null;
    this._aiBusy=false;
    this._targetDevicesBound=false;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _ensureV49Styles(){
    if(this.shadowRoot?.getElementById("cook4meV49Styles"))return;
    const style=document.createElement("style");style.id="cook4meV49Styles";style.textContent=`
      .rx-v49-picker{position:relative;display:inline-block}.rx-v49-picker>summary{list-style:none;display:flex;align-items:center;gap:7px;min-height:42px;padding:9px 11px;border:1px solid var(--divider-color);border-radius:11px;background:var(--secondary-background-color);cursor:pointer;white-space:nowrap}.rx-v49-picker>summary::-webkit-details-marker{display:none}.rx-v49-picker[open]>summary{border-color:var(--primary-color)}
      .rx-v49-picker-body{position:absolute;z-index:80;top:calc(100% + 7px);right:0;min-width:min(390px,88vw);max-width:min(540px,92vw);max-height:58vh;overflow:auto;padding:11px;border:1px solid var(--divider-color);border-radius:13px;background:var(--card-background-color);box-shadow:0 12px 34px rgba(0,0,0,.28)}
      .rx-v49-checks{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:7px}.rx-v49-check{display:flex;align-items:center;gap:7px;padding:8px;border:1px solid var(--divider-color);border-radius:10px;cursor:pointer}.rx-v49-check input{min-height:auto}
      .rx-v49-ai-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.rx-v49-ai-grid .wide{grid-column:1/-1}.rx-v49-ai-multi{border:1px solid var(--divider-color);border-radius:13px;padding:10px}.rx-v49-ai-multi>strong{display:block;margin-bottom:8px}.rx-v49-ai-checks{display:flex;gap:7px;flex-wrap:wrap}.rx-v49-ai-checks label{display:flex;align-items:center;gap:5px;padding:6px 8px;border:1px solid var(--divider-color);border-radius:999px;cursor:pointer}.rx-v49-ai-checks input{min-height:auto}
      #aiIngredients{width:100%;min-height:180px}.rx-v49-cache-note{margin-top:8px}.rx-v49-device-control{flex:0 0 auto;align-self:stretch;display:flex;align-items:center}.rx-v49-device-control .rx-v49-picker>summary{height:42px}
      @media(max-width:850px){.rx-v49-ai-grid{grid-template-columns:1fr 1fr}}@media(max-width:560px){.rx-v49-ai-grid{grid-template-columns:1fr}.rx-v49-ai-grid .wide{grid-column:auto}}
    `;this.shadowRoot.appendChild(style);
  }

  async _api(type,data={}){
    const mapped={
      "cook4me/v15/barcode_scan":"cook4me/v23/barcode_scan",
      "cook4me/v15/barcode_map_add":"cook4me/v23/barcode_map_add",
      "cook4me/v20/global_price_lookup":"cook4me/v23/global_price_lookup",
      "cook4me/v20/recipe_cost":"cook4me/v23/recipe_cost",
    }[type]||type;
    if(!this._cook4meApiTail)this._cook4meApiTail=Promise.resolve();
    if(!this._cook4meApiInflight)this._cook4meApiInflight=new Map();
    let key="";try{key=`${mapped}:${JSON.stringify(data||{})}`;}catch(_e){key=`${mapped}:${Date.now()}`;}
    if(this._cook4meApiInflight.has(key))return this._cook4meApiInflight.get(key);
    const execute=()=>super._api(mapped,data);
    const task=this._cook4meApiTail.then(execute,execute);
    this._cook4meApiTail=task.catch(()=>undefined);
    this._cook4meApiInflight.set(key,task);
    try{return await task;}finally{if(this._cook4meApiInflight.get(key)===task)this._cook4meApiInflight.delete(key);}
  }

  _userKey(suffix){return `cook4me.${suffix}.v1.${String(this._hass?.user?.id||"anonymous")}.${String(this._entryId||"default")}`;}

  _languageRows(){
    const rows=this._todayOptions?.languages||this._capabilities?.languages||[];
    return Array.isArray(rows)?rows.filter(row=>String(row?.code||"").trim()):[];
  }

  _loadOfficialLanguages(){
    if(Array.isArray(this._officialLanguages)&&this._officialLanguages.length)return this._officialLanguages;
    let saved=[];try{saved=JSON.parse(localStorage.getItem(this._userKey("officialCatalogLanguages"))||"[]");}catch(_e){}
    const valid=new Set(this._languageRows().map(row=>String(row.code).toLowerCase()));
    const selected=(Array.isArray(saved)?saved:[]).map(x=>String(x).toLowerCase()).filter(code=>valid.has(code));
    const fallback=String(this._selectedLanguage?.()||this._capabilities?.deviceCatalogLanguage||"de").toLowerCase();
    this._officialLanguages=selected.length?selected:[fallback];
    return this._officialLanguages;
  }

  _saveOfficialLanguages(values){
    const unique=[...new Set((values||[]).map(x=>String(x).toLowerCase()).filter(Boolean))];
    this._officialLanguages=unique.length?unique:[String(this._selectedLanguage?.()||"de")];
    try{localStorage.setItem(this._userKey("officialCatalogLanguages"),JSON.stringify(this._officialLanguages));}catch(_e){}
  }

  _officialLanguagesHtml(){
    const rows=this._languageRows(),selected=new Set(this._loadOfficialLanguages());
    if(!rows.length)return `<div class="muted">${this._escape(this._t("loadingCatalogs"))}</div>`;
    const all=rows.every(row=>selected.has(String(row.code).toLowerCase()));
    return `<div class="toolbar" style="justify-content:space-between;margin-bottom:8px"><span class="muted">${this._escape(this._t("officialCatalogsHelp"))}</span><button type="button" class="btn secondary" data-official-languages-bulk>${this._escape(this._t(all?"deselectAll":"selectAll"))}</button></div><div class="rx-v49-checks">${rows.map(row=>{const code=String(row.code).toLowerCase();return `<label class="rx-v49-check"><input type="checkbox" data-official-language="${this._escape(code)}" ${selected.has(code)?"checked":""}><span>${this._flagForLanguage?.(code,row.country)||"🌐"} ${this._escape(this._languageName?.(code)||code.toUpperCase())}</span></label>`;}).join("")}</div>`;
  }

  _bindOfficialLanguages(c){
    const picker=c.querySelector("#officialCatalogLanguages");if(!picker)return;
    const persist=()=>{
      const values=[...picker.querySelectorAll("[data-official-language]:checked")].map(row=>String(row.dataset.officialLanguage||""));
      this._saveOfficialLanguages(values);
      const count=picker.querySelector("[data-official-language-count]");if(count)count.textContent=String(this._officialLanguages.length);
    };
    picker.querySelectorAll("[data-official-language]").forEach(row=>row.addEventListener("change",persist));
    picker.querySelector("[data-official-languages-bulk]")?.addEventListener("click",event=>{
      event.preventDefault();event.stopPropagation();
      const rows=[...picker.querySelectorAll("[data-official-language]")];const all=rows.length&&rows.every(row=>row.checked);rows.forEach(row=>{row.checked=!all;});persist();
      const button=picker.querySelector("[data-official-languages-bulk]");if(button)button.textContent=this._t(!all?"deselectAll":"selectAll");
      picker.setAttribute("open","");
    });
  }

  _renderOfficial(c){
    super._renderOfficial(c);
    const card=c.querySelector("section.card"),toolbar=card?.querySelector(".toolbar");if(!card||!toolbar)return;
    const selected=this._loadOfficialLanguages();
    const details=document.createElement("details");details.id="officialCatalogLanguages";details.className="rx-v49-picker";
    details.innerHTML=`<summary><ha-icon icon="mdi:translate"></ha-icon><span>${this._escape(this._t("officialCatalogs"))}</span><b data-official-language-count>${selected.length}</b></summary><div class="rx-v49-picker-body">${this._officialLanguagesHtml()}</div>`;
    const button=toolbar.querySelector("#searchBtn");toolbar.insertBefore(details,button||null);this._bindOfficialLanguages(c);
    card.insertAdjacentHTML("beforeend",`<div class="muted rx-v49-cache-note">${this._escape(this._t("onlineCacheHelp"))}</div>`);
  }

  async _search(query){
    this._searchQuery=String(query||"").trim();this._opened=null;
    try{
      this._message(this._t("loading"));
      const result=await this._api("cook4me/v22/official_search",{
        entry_id:this._entryId,query:this._searchQuery,size:20,languages:this._loadOfficialLanguages(),strict_language:true,
      });
      const items=result?.items||[];items.forEach(recipe=>this._ensureRecipeSelections?.(recipe));
      if(this._shouldTranslate?.()&&items.some(recipe=>this._translationNeeded?.(recipe))){this._message(this._t("translating"));await this._translateItems(items);}
      this._results=items;this._message("");this._renderTab();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  _targetsStorageKey(){return `cook4me.targetDevices.v1.${String(this._hass?.user?.id||"anonymous")}`;}
  _targetEntryIds(){
    const valid=new Set((this._entries||[]).map(row=>String(row.entry_id)));
    let saved=[];try{saved=JSON.parse(localStorage.getItem(this._targetsStorageKey())||"[]");}catch(_e){}
    let values=(Array.isArray(saved)?saved:[]).map(String).filter(id=>valid.has(id));
    if(!values.length&&this._entryId)values=[String(this._entryId)];
    return [...new Set(values)];
  }
  _saveTargetEntryIds(values){
    const valid=new Set((this._entries||[]).map(row=>String(row.entry_id)));
    let next=[...new Set((values||[]).map(String).filter(id=>valid.has(id)))];
    if(!next.length&&this._entryId)next=[String(this._entryId)];
    try{localStorage.setItem(this._targetsStorageKey(),JSON.stringify(next));}catch(_e){}
    return next;
  }

  _ensureTargetDeviceControl(){
    const root=this.shadowRoot;if(!root)return;this._ensureV49Styles();
    const top=root.querySelector(".top"),language=root.getElementById("cook4meCurrencyControl")||root.getElementById("cook4meUiLanguageControl");
    let wrap=root.getElementById("cook4meTargetDevicesControl");
    if((this._entries||[]).length<=1){wrap?.remove();return;}
    if(!wrap){wrap=document.createElement("div");wrap.id="cook4meTargetDevicesControl";wrap.className="rx-v49-device-control";if(language?.parentElement)language.after(wrap);else top?.appendChild(wrap);}
    const selected=new Set(this._targetEntryIds()),all=(this._entries||[]).every(row=>selected.has(String(row.entry_id)));
    wrap.innerHTML=`<details class="rx-v49-picker"><summary><ha-icon icon="mdi:pot-mix-outline"></ha-icon><span>${this._escape(this._t("targetDevices"))}</span><b data-target-count>${selected.size}</b></summary><div class="rx-v49-picker-body"><div class="muted" style="margin-bottom:8px">${this._escape(this._t("targetDevicesHelp"))}</div><button type="button" class="btn secondary" data-target-bulk style="margin-bottom:8px">${this._escape(this._t(all?"deselectAll":"selectAll"))}</button><div class="rx-v49-checks">${(this._entries||[]).map(row=>{const id=String(row.entry_id);return `<label class="rx-v49-check"><input type="checkbox" data-target-entry="${this._escape(id)}" ${selected.has(id)?"checked":""}><span>${this._escape(row.title||"Cook4Me")}</span></label>`;}).join("")}</div></div></details>`;
    const details=wrap.querySelector("details");const persist=()=>{const values=[...wrap.querySelectorAll("[data-target-entry]:checked")].map(row=>row.dataset.targetEntry);const next=this._saveTargetEntryIds(values);const count=wrap.querySelector("[data-target-count]");if(count)count.textContent=String(next.length);};
    wrap.querySelectorAll("[data-target-entry]").forEach(row=>row.addEventListener("change",persist));
    wrap.querySelector("[data-target-bulk]")?.addEventListener("click",event=>{event.preventDefault();event.stopPropagation();const rows=[...wrap.querySelectorAll("[data-target-entry]")];const areAll=rows.every(row=>row.checked);rows.forEach(row=>{row.checked=!areAll;});persist();details?.setAttribute("open","");});
  }

  _renderShell(){super._renderShell();this._ensureV49Styles();this._ensureTargetDeviceControl();}
  _renderEntrySelect(){super._renderEntrySelect();this._ensureTargetDeviceControl();}
  _updateHeader(){super._updateHeader();this._ensureTargetDeviceControl();}

  _aiStorageKey(){return this._userKey("aiCreate");}
  _aiDefaults(){
    const today=this._todayDefaults?.()||{};
    return {request:"",diet:today.diet||"profile",nutritionGoal:today.nutritionGoal||"balanced",calorieTarget:today.calorieTarget??"",calorieTolerance:today.calorieTolerance||25,maxMissing:today.maxMissing??"",mealTypes:Array.isArray(today.mealTypes)?today.mealTypes:[...AI_MEAL_TYPES],languages:Array.isArray(today.languages)&&today.languages.length?today.languages:[String(this._selectedLanguage?.()||"de")],ingredients:Array.isArray(today.ingredients)?today.ingredients:[],onlyHome:Boolean(today.onlyHome),preferExpiring:today.preferExpiring!==false,avoidRecentDays:Number(today.avoidRecentDays??7)};
  }
  _loadAiSettings(){if(this._aiSettings)return this._aiSettings;const defaults=this._aiDefaults();try{const saved=JSON.parse(localStorage.getItem(this._aiStorageKey())||"null");this._aiSettings=saved&&typeof saved==="object"?{...defaults,...saved}:defaults;}catch(_e){this._aiSettings=defaults;}return this._aiSettings;}
  _saveAiSettings(settings){this._aiSettings=settings;try{localStorage.setItem(this._aiStorageKey(),JSON.stringify(settings));}catch(_e){}}

  _aiLanguageHtml(settings){const selected=new Set((settings.languages||[]).map(x=>String(x).toLowerCase()));const rows=this._languageRows();return rows.length?rows.map(row=>{const code=String(row.code).toLowerCase();return `<label><input type="checkbox" data-ai-language="${this._escape(code)}" ${selected.has(code)?"checked":""}>${this._flagForLanguage?.(code,row.country)||"🌐"} ${this._escape(this._languageName?.(code)||code.toUpperCase())}</label>`;}).join(""):`<span class="muted">${this._escape(this._t("loadingCatalogs"))}</span>`;}
  _aiMealHtml(settings){const selected=new Set(settings.mealTypes||[]);return AI_MEAL_TYPES.map(type=>`<label><input type="checkbox" data-ai-meal-type="${type}" ${selected.has(type)?"checked":""}>${this._escape(this._t(type))}</label>`).join("");}
  _aiIngredientHtml(settings){const rows=this._todayIngredientRows?.()||this._ingredientCatalog||[],selected=new Set((settings.ingredients||[]).map(String));return `<select id="aiIngredients" multiple size="8">${rows.map(row=>{const id=this._todayIngredientIdentity?.(row)||`k:${row.key||""}`;return `<option value="${this._escape(id)}" ${selected.has(id)?"selected":""}>${this._escape(row.name||row.foodName||id)}</option>`;}).join("")}</select>`;}

  _renderAIV49(c){
    const s=this._loadAiSettings();if(!this._todayOptions&&!this._todayOptionsLoading)queueMicrotask(()=>void this._loadTodayOptions());if(!(this._ingredientCatalog||[]).length&&!this._ingredientCatalogLoading)queueMicrotask(()=>void this._loadIngredientCatalog(this._capabilities?.ingredientCatalogLanguage||this._selectedLanguage?.()||"de",false));
    const available=Boolean(this._capabilities?.defaultAiTaskAvailable);
    c.innerHTML=`<section class="card"><div class="detail-head"><div><h2>${this._escape(this._t("aiCreateTitle"))}</h2><div class="muted">${this._escape(this._t("aiCreateHelp"))}</div></div><span class="chip">${this._escape(this._t("serializedWork"))}</span></div>${available?"":`<div class="notice error">${this._escape(this._t("aiNoTask"))}</div>`}<div class="rx-v49-ai-grid" style="margin-top:12px">
      <div class="field wide"><label>${this._escape(this._t("aiRequest"))}</label><textarea id="aiRequest" placeholder="${this._escape(this._t("aiRequestPlaceholder"))}">${this._escape(s.request||"")}</textarea></div>
      <div class="field"><label>${this._escape(this._t("dietFilter"))}</label><select id="aiDiet">${this._todayDietOptions(String(s.diet||"profile"))}</select></div>
      <div class="field"><label>${this._escape(this._t("nutritionTarget"))}</label><select id="aiNutritionGoal">${this._todayGoalOptions(String(s.nutritionGoal||"balanced"))}</select></div>
      <div class="field"><label>${this._escape(this._t("calorieTarget"))}</label><input id="aiCalories" type="number" min="1" step="1" value="${this._escape(s.calorieTarget??"")}" placeholder="kcal"></div>
      <div class="rx-v49-ai-multi wide"><strong>${this._escape(this._t("mealTypes"))}</strong><div class="rx-v49-ai-checks">${this._aiMealHtml(s)}</div></div>
      <div class="rx-v49-ai-multi wide"><strong>${this._escape(this._t("catalogLanguages"))}</strong><div class="rx-v49-ai-checks">${this._aiLanguageHtml(s)}</div></div>
      <div class="field wide"><label>${this._escape(this._t("preferredIngredients"))}</label>${this._aiIngredientHtml(s)}</div>
      <div class="field"><label>${this._escape(this._t("calorieTolerance"))}</label><select id="aiCalTolerance">${[10,15,25,40,50].map(n=>`<option value="${n}" ${Number(s.calorieTolerance||25)===n?"selected":""}>±${n}%</option>`).join("")}</select></div>
      <div class="field"><label>${this._escape(this._t("maxMissing"))}</label><input id="aiMaxMissing" type="number" min="0" max="20" step="1" value="${this._escape(s.maxMissing??"")}"></div>
      <div class="field"><label>${this._escape(this._t("avoidRecent"))}</label><select id="aiRecent"><option value="0" ${Number(s.avoidRecentDays||0)===0?"selected":""}>${this._escape(this._t("dontAvoid"))}</option>${[1,3,7,14,30].map(n=>`<option value="${n}" ${Number(s.avoidRecentDays||0)===n?"selected":""}>${n} ${this._escape(this._t("days"))}</option>`).join("")}</select></div>
      <label class="chip"><input id="aiPreferExpiring" type="checkbox" ${s.preferExpiring!==false?"checked":""}> ${this._escape(this._t("preferExpiring"))}</label>
      <label class="chip"><input id="aiOnlyHome" type="checkbox" ${s.onlyHome?"checked":""}> ${this._escape(this._t("onlyHome"))}</label>
      </div><div class="toolbar" style="margin-top:13px"><button id="aiCreate" class="btn" ${!available||this._aiBusy?"disabled":""}><ha-icon icon="mdi:creation"></ha-icon><span>${this._escape(this._aiBusy?this._t("aiRunning"):this._t("createAi"))}</span></button></div><div class="muted rx-v49-cache-note">${this._escape(this._t("onlineCacheHelp"))}</div></section>${this._detailHtml(this._opened)}`;
    this._bindDetail(c);c.querySelector("#aiCreate")?.addEventListener("click",()=>void this._createAiRecipe(c));
  }

  _collectAiSettings(c){
    const ingredients=[...(c.querySelector("#aiIngredients")?.selectedOptions||[])].map(option=>String(option.value||""));
    return {request:String(c.querySelector("#aiRequest")?.value||""),diet:String(c.querySelector("#aiDiet")?.value||"profile"),nutritionGoal:String(c.querySelector("#aiNutritionGoal")?.value||"balanced"),calorieTarget:String(c.querySelector("#aiCalories")?.value||""),calorieTolerance:Number(c.querySelector("#aiCalTolerance")?.value||25),maxMissing:String(c.querySelector("#aiMaxMissing")?.value||""),mealTypes:[...c.querySelectorAll("[data-ai-meal-type]:checked")].map(row=>String(row.dataset.aiMealType||"")),languages:[...c.querySelectorAll("[data-ai-language]:checked")].map(row=>String(row.dataset.aiLanguage||"")),ingredients,onlyHome:Boolean(c.querySelector("#aiOnlyHome")?.checked),preferExpiring:Boolean(c.querySelector("#aiPreferExpiring")?.checked),avoidRecentDays:Number(c.querySelector("#aiRecent")?.value||0)};
  }

  async _createAiRecipe(c){
    if(this._aiBusy)return;const settings=this._collectAiSettings(c);this._saveAiSettings(settings);this._aiBusy=true;this._renderAIV49(c);const process=this._processStart(this._t("aiCreateTitle"),this._t("aiWaiting"));
    try{
      const selectedIngredients=this._todaySelectedIngredientRows?.({ingredients:settings.ingredients})||[];
      this._processUpdate(process,this._t("aiRunning"));
      const payload={entry_id:this._entryId,request:settings.request,language:this._langCode(),catalog_languages:settings.languages,diet:settings.diet,meal_types:settings.mealTypes,nutrition_goal:settings.nutritionGoal,calorie_tolerance:settings.calorieTolerance,only_home:settings.onlyHome,prefer_expiring:settings.preferExpiring,avoid_recent_days:settings.avoidRecentDays,ingredients:selectedIngredients};
      if(settings.calorieTarget!=="")payload.calorie_target=settings.calorieTarget;if(settings.maxMissing!=="")payload.max_missing=Number(settings.maxMissing);
      const result=await this._api("cook4me/v22/ai_create",payload);this._opened=result?.recipe||null;await this._loadOverview(true,false);this._message(this._opened?`${this._t("aiCreated")}: ${this._clean(this._opened.title||"")}`:this._t("aiCreated"));
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}finally{this._aiBusy=false;this._processEnd(process);this._renderTab();}
  }

  _renderTab(){if(this._tab==="ai"){const c=this.shadowRoot?.getElementById("content");if(c)this._renderAIV49(c);return;}return super._renderTab();}

  async _send(recipe){
    const targets=this._targetEntryIds();const process=this._processStart(this._t("backgroundWork"),this._t("sendingRecipe"));
    try{
      const result=await this._api("cook4me/v22/send_multi",{entry_id:this._entryId,entry_ids:targets,recipe});
      const detail=`${result?.sentCount||0} sent · ${result?.queuedCount||0} queued · ${result?.targetCount||0} ${this._t("selectedDevices")}`;this._message(`${this._t("sendTargetsDone")}: ${detail}`);await this._loadOverview(true);
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}finally{this._processEnd(process);}
  }

  _bindCards(container,items,custom=false){
    super._bindCards(container,items,custom);if(custom)return;
    container.querySelectorAll(".recipe").forEach((card,index)=>{const recipe=items[index];const official=Boolean(recipe?.sendVariantId||recipe?.variantFunctionalId||recipe?.recipeFunctionalId||recipe?.sendGroupingFunctionalId);const send=card.querySelector('[data-action="send"]');if(send&&official&&recipe?.match?.safe!==false){send.disabled=false;send.removeAttribute("title");}});
  }

  _bindDetail(container){
    super._bindDetail(container);const recipe=this._opened;if(!recipe)return;const official=Boolean(recipe?.sendVariantId||recipe?.variantFunctionalId||recipe?.recipeFunctionalId||recipe?.sendGroupingFunctionalId);const send=container.querySelector("[data-detail-send]");if(send&&official&&recipe?.match?.safe!==false){send.disabled=false;send.removeAttribute("title");}
  }
}

customElements.define("cook4me-recipe-hub-panel-v49",Cook4MeRecipeHubPanelV49);
