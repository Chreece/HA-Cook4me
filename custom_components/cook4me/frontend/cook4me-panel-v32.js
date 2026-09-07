import "./cook4me-panel-v31.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v31");

const COUNTRY_BY_LANGUAGE={
  ar:"AE",bg:"BG",cs:"CZ",de:"DE",en:"GB",es:"ES",fr:"FR",hr:"HR",hu:"HU",
  it:"IT",ja:"JP",ko:"KR",pl:"PL",pt:"PT",ro:"RO",ru:"RU",sk:"SK",sl:"SI",
  tr:"TR",uk:"UA",zh:"TW",el:"GR",
};

const MEAL_VISUALS={
  breakfast:{icon:"coffee-outline",tone:"amber"},
  starter:{icon:"silverware-fork-knife",tone:"violet"},
  salad:{icon:"leaf",tone:"green"},
  soup:{icon:"bowl-mix-outline",tone:"orange"},
  main:{icon:"food",tone:"red"},
  side:{icon:"food-apple-outline",tone:"lime"},
  dessert:{icon:"cupcake",tone:"pink"},
  snack:{icon:"food-variant",tone:"blue"},
};

const DIET_ICONS={profile:"account-heart-outline",omnivore:"food-drumstick-outline",pescatarian:"fish",vegetarian:"sprout",vegan:"leaf-circle-outline"};
const GOAL_ICONS={balanced:"scale-balance",high_protein:"arm-flex-outline",lower_calorie:"fire",high_fiber:"grain",lower_saturated_fat:"heart-pulse"};

const TEXT={
  en:{moreFilters:"More filters",quickPlan:"Your plan",languageSource:"Source language",activeJobs:"Background jobs",jobCancelRequested:"Cancellation requested. The current Home Assistant/server request may finish, but further client work will stop.",jobDone:"Done",jobCancelled:"Cancelled",loadingCatalog:"Loading ingredient catalog",loadingNutrition:"Calculating recipe nutrition",hydratingNutrition:"Adding nutrition to visible recipes",loadingTodayOptions:"Loading Today choices",loadingBook:"Loading recipe book",lookingUpBarcode:"Looking up scanned product",changingRecipe:"Loading the selected recipe variant",savingData:"Saving changes",buildingNutritionCatalog:"Building the nutrition catalog",shoppingUpdate:"Updating Shopping List",stockUpdate:"Updating house stock",nutritionLabelJob:"Saving package nutrition",languageAuto:"Automatic",filters:"Filters"},
  de:{moreFilters:"Weitere Filter",quickPlan:"Dein Plan",languageSource:"Quellsprache",activeJobs:"Hintergrundaufgaben",jobCancelRequested:"Abbruch angefordert. Die aktuelle Home-Assistant-/Serveranfrage kann noch fertiglaufen; weitere lokale Schritte werden gestoppt.",jobDone:"Fertig",jobCancelled:"Abgebrochen",loadingCatalog:"Zutatenkatalog wird geladen",loadingNutrition:"Rezept-Nährwerte werden berechnet",hydratingNutrition:"Nährwerte werden zu sichtbaren Rezepten ergänzt",loadingTodayOptions:"Heute-Auswahl wird geladen",loadingBook:"Rezeptbuch wird geladen",lookingUpBarcode:"Gescanntes Produkt wird gesucht",changingRecipe:"Gewählte Rezeptvariante wird geladen",savingData:"Änderungen werden gespeichert",buildingNutritionCatalog:"Nährwertkatalog wird aufgebaut",shoppingUpdate:"Einkaufsliste wird aktualisiert",stockUpdate:"Vorrat wird aktualisiert",nutritionLabelJob:"Produktnährwerte werden gespeichert",languageAuto:"Automatisch",filters:"Filter"},
  el:{moreFilters:"Περισσότερα φίλτρα",quickPlan:"Το πλάνο σου",languageSource:"Γλώσσα πηγής",activeJobs:"Εργασίες στο παρασκήνιο",jobCancelRequested:"Ζητήθηκε ακύρωση. Το τρέχον αίτημα Home Assistant/server μπορεί να ολοκληρωθεί, αλλά τα επόμενα τοπικά βήματα θα σταματήσουν.",jobDone:"Έτοιμο",jobCancelled:"Ακυρώθηκε",loadingCatalog:"Φόρτωση καταλόγου υλικών",loadingNutrition:"Υπολογισμός διατροφικών στοιχείων συνταγής",hydratingNutrition:"Προσθήκη διατροφικών στοιχείων στις ορατές συνταγές",loadingTodayOptions:"Φόρτωση επιλογών Σήμερα",loadingBook:"Φόρτωση βιβλίου συνταγών",lookingUpBarcode:"Αναζήτηση σαρωμένου προϊόντος",changingRecipe:"Φόρτωση επιλεγμένης παραλλαγής συνταγής",savingData:"Αποθήκευση αλλαγών",buildingNutritionCatalog:"Δημιουργία καταλόγου διατροφής",shoppingUpdate:"Ενημέρωση λίστας αγορών",stockUpdate:"Ενημέρωση αποθέματος",nutritionLabelJob:"Αποθήκευση διατροφικών στοιχείων προϊόντος",languageAuto:"Αυτόματο",filters:"Φίλτρα"},
};

class Cook4MeRecipeHubPanelV32 extends BasePanel{
  constructor(){
    super();
    this._rxJobs=new Map();
    this._rxJobSequence=0;
    this._rxProfessionalPending=false;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _flagFromCountry(country){
    const code=String(country||"").toUpperCase();
    if(!/^[A-Z]{2}$/.test(code))return "🌐";
    return String.fromCodePoint(...[...code].map(char=>127397+char.charCodeAt(0)));
  }
  _flagForLanguage(language,country=null){
    const code=String(language||"").toLowerCase().split(/[-_]/)[0];
    if(!code||code==="auto")return "🌐";
    return this._flagFromCountry(country||COUNTRY_BY_LANGUAGE[code]);
  }

  _mealIcon(type){return MEAL_VISUALS[String(type||"").toLowerCase()]?.icon||"silverware-fork-knife";}

  _todayMealTypeHtml(settings){
    const values=["breakfast","starter","salad","soup","main","side","dessert","snack"];
    const selected=new Set(settings.mealTypes||[]);
    return values.map(value=>{
      const visual=MEAL_VISUALS[value];
      return `<label class="rx-choice-card rx-meal-choice tone-${visual.tone} ${selected.has(value)?"selected":""}">
        <input data-today-meal-type="${value}" type="checkbox" ${selected.has(value)?"checked":""}>
        <span class="rx-choice-icon"><ha-icon icon="mdi:${visual.icon}"></ha-icon></span>
        <span class="rx-choice-copy"><strong>${this._escape(this._t(value))}</strong></span>
        <ha-icon class="rx-choice-check" icon="mdi:check-circle"></ha-icon>
      </label>`;
    }).join("");
  }

  _todayLanguageHtml(settings){
    const selected=new Set((settings.languages||[]).map(x=>String(x).toLowerCase()));
    return this._todayLanguageRows().map(row=>{
      const code=String(row.code||"").toLowerCase();
      if(!code)return"";
      const flag=this._flagForLanguage(code,row.country);
      const name=this._languageName(code);
      return `<label class="rx-choice-card rx-language-choice ${selected.has(code)?"selected":""}">
        <input data-today-language="${this._escape(code)}" type="checkbox" ${selected.has(code)?"checked":""}>
        <span class="rx-language-flag" aria-hidden="true">${flag}</span>
        <span class="rx-choice-copy"><strong>${this._escape(name)}</strong><small>${this._escape(code.toUpperCase())}${row.country?` · ${this._escape(String(row.country).toUpperCase())}`:""}</small></span>
        <ha-icon class="rx-choice-check" icon="mdi:check-circle"></ha-icon>
      </label>`;
    }).join("");
  }

  _todayDietOptions(value){
    const rows=[
      ["profile",`👤 ${this._t("profileDiet")} (${this._t(String(this._entry()?.profile?.diet||"omnivore"))})`],
      ["omnivore",`🍽️ ${this._t("omnivore")}`],["pescatarian",`🐟 ${this._t("pescatarian")}`],
      ["vegetarian",`🌱 ${this._t("vegetarian")}`],["vegan",`🌿 ${this._t("vegan")}`],
    ];
    return rows.map(([v,l])=>`<option value="${v}" ${v===value?"selected":""}>${this._escape(l)}</option>`).join("");
  }

  _todayGoalOptions(value){
    const rows=[["balanced","⚖️","balanced"],["high_protein","💪","highProtein"],["lower_calorie","🔥","lowerCalorie"],["high_fiber","🌾","highFiber"],["lower_saturated_fat","♥","lowerSaturatedFat"]];
    return rows.map(([v,icon,k])=>`<option value="${v}" ${v===value?"selected":""}>${icon} ${this._escape(this._t(k))}</option>`).join("");
  }

  _courseVisuals(recipe){
    const raw=[];
    for(const source of [recipe?.courses,recipe?.mealTypes,recipe?.meal_types]){
      if(Array.isArray(source))raw.push(...source);
    }
    const text=raw.map(value=>typeof value==="object"?`${value.key||""} ${value.name||""} ${value.label||""}`:String(value||"")).join(" | ").toLocaleLowerCase();
    if(!text)return[];
    const tests={
      breakfast:["breakfast","frühstück","fruhstuck","πρωιν"],starter:["starter","appetizer","vorspeise","ορεκ"],
      salad:["salad","salat","σαλα","σαλά"],soup:["soup","suppe","σουπ","σούπ"],
      main:["main course","main_course","hauptgericht","κυρι","κύρι"],side:["side dish","side_dish","beilage","συνοδευ"],
      dessert:["dessert","nachspeise","επιδορ","επιδόρ"],snack:["snack","σνακ"],
    };
    return Object.entries(tests).filter(([,needles])=>needles.some(n=>text.includes(n))).map(([type])=>type).slice(0,3);
  }

  _visualMetaHtml(recipe){
    const parts=[];
    const lang=String(recipe?.selectedLanguage||recipe?.sourceLanguage||recipe?.language||"").toLowerCase().split(/[-_]/)[0];
    if(lang){parts.push(`<span class="chip rx-semantic-chip rx-language-badge"><span class="rx-inline-flag">${this._flagForLanguage(lang)}</span>${this._escape(this._languageName(lang))}</span>`);}
    for(const type of this._courseVisuals(recipe)){
      parts.push(`<span class="chip rx-semantic-chip rx-meal-badge tone-${MEAL_VISUALS[type].tone}"><ha-icon icon="mdi:${this._mealIcon(type)}"></ha-icon>${this._escape(this._t(type))}</span>`);
    }
    return parts.join("");
  }

  _recipeCard(recipe,custom=false){
    let html=super._recipeCard(recipe,custom);
    const meta=this._visualMetaHtml(recipe);
    if(meta)html=html.replace('<div class="chips">',`<div class="chips">${meta}`);
    return html;
  }

  _detailHtml(recipe){
    let html=super._detailHtml(recipe);
    if(!html||!recipe)return html;
    const meta=this._visualMetaHtml(recipe);
    if(meta)html=html.replace('<div class="chips">',`<div class="chips">${meta}`);
    return html;
  }

  _nutritionChips(values,compact=false){
    if(!values||typeof values!=="object")return"";
    const rows=[
      ["energyKcal",this._t("calories"),"kcal","fire","orange"],
      ["protein",this._t("protein"),"g","arm-flex-outline","violet"],
      ["carbohydrates",this._t("carbs"),"g","grain","blue"],
      ["fat",this._t("fat"),"g","water-outline","pink"],
      ...(!compact?[
        ["fiber",this._t("fiber"),"g","sprout","green"],["sugars",this._t("sugars"),"g","cube-outline","amber"],
        ["saturatedFat",this._t("saturatedFat"),"g","heart-pulse","red"],["salt",this._t("salt"),"g","shaker-outline","slate"],
      ]:[]),
    ];
    return rows.filter(([key])=>Number.isFinite(Number(values[key]))).map(([key,label,unit,icon,tone])=>`<span class="chip rx-nutrition-chip tone-${tone}" data-nutrition-key="${key}"><ha-icon icon="mdi:${icon}"></ha-icon><span>${this._escape(label)}</span><strong>${this._escape(this._metric(values[key],key,unit))}</strong></span>`).join("");
  }

  _renderShell(){
    super._renderShell();
    this._ensureProfessionalStyles();
    this._ensureJobStack();
    this._professionalizeSoon();
  }

  _modernizeSoon(){
    super._modernizeSoon();
    this._professionalizeSoon();
  }

  _professionalizeSoon(){
    if(this._rxProfessionalPending)return;
    this._rxProfessionalPending=true;
    queueMicrotask(()=>{
      this._rxProfessionalPending=false;
      if(!this.shadowRoot)return;
      this._decorateLanguages(this.shadowRoot);
      this._decorateFields(this.shadowRoot);
      this._upgradeTodayPanel(this.shadowRoot);
      this._upgradeChoiceStates(this.shadowRoot);
      this._upgradeIngredientSheet(this.shadowRoot);
    });
  }

  _ensureProfessionalStyles(){
    if(this.shadowRoot?.getElementById("cook4meProfessionalV32"))return;
    const style=document.createElement("style");
    style.id="cook4meProfessionalV32";
    style.textContent=`
      :host{--rx-green:#31a56b;--rx-orange:#ef8d32;--rx-pink:#db668d;--rx-blue:#4c83dd;--rx-violet:#805fd3;--rx-amber:#d5a329;--rx-red:#d95a5a;--rx-slate:#718096}
      #cook4meUiLanguageControl{margin:10px 0 -2px!important;padding:8px 10px;border:1px solid color-mix(in srgb,var(--divider-color) 70%,transparent);border-radius:15px;background:color-mix(in srgb,var(--card-background-color) 88%,var(--primary-color) 3%)!important;box-shadow:0 2px 10px rgba(0,0,0,.05)}
      #cook4meUiLanguageControl .field{min-width:min(100%,290px)!important}#cook4meUiLanguageControl .muted{display:none}
      .field>label.rx-field-label{display:flex!important;align-items:center;gap:6px}.rx-field-label ha-icon{--mdc-icon-size:17px;color:var(--primary-color)}
      .rx-language-field{position:relative}.rx-language-field::after{content:attr(data-rx-flag);position:absolute;right:38px;bottom:11px;font-size:18px;pointer-events:none;filter:saturate(.95)}
      .rx-semantic-chip{display:inline-flex!important;align-items:center!important;gap:5px!important}.rx-semantic-chip ha-icon{--mdc-icon-size:15px}.rx-inline-flag{font-size:15px;line-height:1}
      .rx-meal-badge,.rx-nutrition-chip{border-color:color-mix(in srgb,var(--rx-tone,var(--primary-color)) 40%,var(--divider-color))!important;background:color-mix(in srgb,var(--rx-tone,var(--primary-color)) 10%,var(--card-background-color))!important}
      .tone-green{--rx-tone:var(--rx-green)}.tone-orange{--rx-tone:var(--rx-orange)}.tone-pink{--rx-tone:var(--rx-pink)}.tone-blue{--rx-tone:var(--rx-blue)}.tone-violet{--rx-tone:var(--rx-violet)}.tone-amber{--rx-tone:var(--rx-amber)}.tone-red{--rx-tone:var(--rx-red)}.tone-lime{--rx-tone:#78a957}.tone-slate{--rx-tone:var(--rx-slate)}
      .rx-nutrition-chip{padding:6px 9px!important}.rx-nutrition-chip ha-icon{--mdc-icon-size:16px;color:var(--rx-tone)}.rx-nutrition-chip strong{font-weight:800}

      .rx-today-planner{overflow:visible!important;background:linear-gradient(145deg,color-mix(in srgb,var(--card-background-color) 96%,#f59e0b 4%),var(--card-background-color))!important}
      .rx-today-planner>.detail-head{padding-bottom:12px;border-bottom:1px solid color-mix(in srgb,var(--divider-color) 65%,transparent)}
      .rx-today-hero-icon{width:50px;height:50px;border-radius:16px;display:grid;place-items:center;color:#fff;background:linear-gradient(135deg,#f59e0b,#ef6c36);box-shadow:0 8px 20px rgba(239,141,50,.22);flex:0 0 auto}.rx-today-hero-icon ha-icon{--mdc-icon-size:27px}
      .rx-today-head{display:flex;align-items:center;gap:12px}.rx-today-planner .formgrid{margin-top:14px}
      .rx-choice-grid{display:grid!important;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:8px!important}
      .rx-language-grid{grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
      .rx-choice-card{position:relative;display:flex!important;align-items:center;gap:9px;min-height:58px;padding:9px 11px!important;border:1px solid color-mix(in srgb,var(--divider-color) 78%,transparent)!important;border-radius:14px!important;background:color-mix(in srgb,var(--card-background-color) 94%,var(--secondary-background-color) 6%)!important;cursor:pointer;transition:transform .14s ease,border-color .14s ease,background .14s ease,box-shadow .14s ease}
      .rx-choice-card:hover{transform:translateY(-1px);border-color:color-mix(in srgb,var(--rx-tone,var(--primary-color)) 35%,var(--divider-color))!important;box-shadow:0 5px 14px rgba(0,0,0,.07)}
      .rx-choice-card.selected{border-color:color-mix(in srgb,var(--rx-tone,var(--primary-color)) 65%,var(--divider-color))!important;background:color-mix(in srgb,var(--rx-tone,var(--primary-color)) 12%,var(--card-background-color))!important;box-shadow:0 4px 14px color-mix(in srgb,var(--rx-tone,var(--primary-color)) 12%,transparent)}
      .rx-choice-card>input{position:absolute!important;opacity:0!important;pointer-events:none;width:1px!important;height:1px!important}.rx-choice-icon{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;color:var(--rx-tone,var(--primary-color));background:color-mix(in srgb,var(--rx-tone,var(--primary-color)) 12%,var(--card-background-color));flex:0 0 auto}.rx-choice-icon ha-icon{--mdc-icon-size:22px}
      .rx-choice-copy{display:flex;flex-direction:column;min-width:0;line-height:1.2}.rx-choice-copy strong{font-size:13.5px}.rx-choice-copy small{font-size:11px;color:var(--secondary-text-color);margin-top:3px}.rx-choice-check{margin-left:auto;--mdc-icon-size:18px;color:var(--rx-tone,var(--primary-color));opacity:0;transform:scale(.75);transition:.14s}.rx-choice-card.selected .rx-choice-check{opacity:1;transform:scale(1)}
      .rx-language-flag{width:38px;height:38px;border-radius:50%;display:grid;place-items:center;font-size:24px;background:var(--card-background-color);box-shadow:0 2px 8px rgba(0,0,0,.11);flex:0 0 auto}
      .rx-section-label{display:flex;align-items:center;gap:7px;font-weight:750;margin-bottom:7px}.rx-section-label ha-icon{--mdc-icon-size:18px;color:var(--primary-color)}
      .rx-primary-toggle{display:inline-flex!important;align-items:center!important;gap:7px!important;min-height:42px;padding:8px 11px!important;border-radius:12px!important;background:color-mix(in srgb,var(--success-color,#43a047) 9%,var(--card-background-color))!important;border:1px solid color-mix(in srgb,var(--success-color,#43a047) 25%,var(--divider-color))!important}
      .rx-plan-summary{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:12px 0 2px}.rx-plan-summary>.rx-plan-title{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:800;color:var(--secondary-text-color);margin-right:2px}.rx-plan-summary>.rx-plan-title ha-icon{--mdc-icon-size:16px}
      details.rx-advanced{margin-top:13px;border:1px solid color-mix(in srgb,var(--divider-color) 74%,transparent);border-radius:14px;background:color-mix(in srgb,var(--secondary-background-color) 40%,transparent);overflow:hidden}details.rx-advanced>summary{list-style:none;display:flex;align-items:center;gap:8px;padding:11px 13px;cursor:pointer;font-weight:750}details.rx-advanced>summary::-webkit-details-marker{display:none}details.rx-advanced>summary ha-icon{--mdc-icon-size:19px;color:var(--primary-color)}.rx-advanced-content{padding:0 13px 13px;display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}.rx-advanced-content .field{max-width:none!important}.rx-advanced-content label.chip{align-self:end;min-height:42px;display:flex;align-items:center;gap:6px;padding:8px 10px}

      .rx-job-stack{position:fixed;right:max(14px,env(safe-area-inset-right));bottom:max(14px,env(safe-area-inset-bottom));z-index:12000;width:min(390px,calc(100vw - 24px));display:flex;flex-direction:column;gap:9px;pointer-events:none}
      .rx-job-card{pointer-events:auto;padding:12px 13px;border-radius:17px;border:1px solid color-mix(in srgb,var(--divider-color) 75%,transparent);background:color-mix(in srgb,var(--card-background-color) 95%,var(--primary-color) 5%);box-shadow:0 14px 40px rgba(0,0,0,.2);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);animation:rxJobIn .18s ease both}.rx-job-card[hidden]{display:none}.rx-job-head{display:grid;grid-template-columns:36px minmax(0,1fr) auto;gap:9px;align-items:center}.rx-job-icon{width:36px;height:36px;border-radius:11px;display:grid;place-items:center;color:var(--primary-color);background:color-mix(in srgb,var(--primary-color) 12%,var(--card-background-color))}.rx-job-icon ha-icon{--mdc-icon-size:21px}.rx-job-title{font-weight:800;font-size:13.5px}.rx-job-detail{font-size:12px;color:var(--secondary-text-color);margin-top:2px;line-height:1.35}.rx-job-cancel{width:34px!important;min-width:34px!important;height:34px!important;min-height:34px!important;padding:0!important;border-radius:50%!important}.rx-job-progress{height:6px;margin-top:9px;border-radius:999px;overflow:hidden;background:color-mix(in srgb,var(--divider-color) 45%,transparent)}.rx-job-progress>div{height:100%;width:35%;border-radius:999px;background:linear-gradient(90deg,var(--primary-color),color-mix(in srgb,var(--primary-color) 55%,#fff 45%));animation:rxJobSweep 1.15s ease-in-out infinite alternate}.rx-job-progress.determinate>div{animation:none}.rx-job-percent{font-size:11px;font-weight:700;color:var(--secondary-text-color);margin-top:5px;text-align:right}.rx-job-card.cancelled .rx-job-icon{color:var(--warning-color,#f9a825);background:color-mix(in srgb,var(--warning-color,#f9a825) 12%,var(--card-background-color))}.rx-job-card.done .rx-job-icon{color:var(--success-color,#43a047);background:color-mix(in srgb,var(--success-color,#43a047) 12%,var(--card-background-color))}@keyframes rxJobIn{from{opacity:0;transform:translateY(8px) scale(.985)}to{opacity:1;transform:none}}@keyframes rxJobSweep{from{transform:translateX(-70%)}to{transform:translateX(245%)}}

      .rx-dialog.rx-ingredient-sheet{width:min(780px,100%)}
      @media(max-width:700px){.rx-choice-grid,.rx-language-grid{grid-template-columns:1fr 1fr}.rx-choice-card{min-height:54px}.rx-language-choice{grid-column:span 1}.rx-job-stack{left:10px;right:10px;bottom:max(10px,env(safe-area-inset-bottom));width:auto}.rx-dialog.rx-ingredient-sheet{position:absolute;left:0;right:0;bottom:0;width:100%;max-height:88vh;border-radius:24px 24px 0 0!important;margin:0}.rx-overlay:has(.rx-ingredient-sheet){align-items:flex-end!important;padding:0!important}}
      @media(max-width:450px){.rx-choice-grid,.rx-language-grid{grid-template-columns:1fr}}
      @media(prefers-reduced-motion:reduce){.rx-choice-card,.rx-choice-check,.rx-job-card{transition:none!important;animation:none!important}.rx-job-progress>div{animation:none!important;width:70%!important}}
    `;
    this.shadowRoot.appendChild(style);
  }

  _ensureJobStack(){
    if(!this.shadowRoot)return null;
    let stack=this.shadowRoot.getElementById("cook4meJobStack");
    if(stack)return stack;
    stack=document.createElement("div");
    stack.id="cook4meJobStack";
    stack.className="rx-job-stack";
    stack.setAttribute("role","status");
    stack.setAttribute("aria-live","polite");
    this.shadowRoot.appendChild(stack);
    return stack;
  }

  _processStart(title,detail="",options={}){
    const id=`job-${++this._rxJobSequence}`;
    const token={id,cancelled:false,done:false,shown:false,onCancel:typeof options?.onCancel==="function"?options.onCancel:null};
    const stack=this._ensureJobStack();
    const card=document.createElement("section");
    card.className="rx-job-card";
    card.hidden=true;
    card.dataset.jobId=id;
    card.innerHTML=`<div class="rx-job-head"><div class="rx-job-icon"><ha-icon icon="mdi:${this._escape(options?.icon||"progress-clock")}"></ha-icon></div><div><div class="rx-job-title">${this._escape(title||this._t("backgroundWork"))}</div><div class="rx-job-detail">${this._escape(detail||"")}</div></div><button type="button" class="btn secondary rx-job-cancel" title="${this._escape(this._t("cancelWork"))}" aria-label="${this._escape(this._t("cancelWork"))}"><ha-icon icon="mdi:close"></ha-icon></button></div><div class="rx-job-progress"><div></div></div><div class="rx-job-percent"></div>`;
    stack?.appendChild(card);
    token.card=card;
    token.revealTimer=setTimeout(()=>{if(!token.done&&card.isConnected){card.hidden=false;token.shown=true;}},Math.max(80,Number(options?.delay??180)));
    card.querySelector(".rx-job-cancel")?.addEventListener("click",()=>{
      if(token.done||token.cancelled)return;
      token.cancelled=true;
      card.classList.add("cancelled");
      const detailNode=card.querySelector(".rx-job-detail");
      if(detailNode)detailNode.textContent=this._t("jobCancelRequested");
      const button=card.querySelector(".rx-job-cancel");if(button)button.disabled=true;
      try{token.onCancel?.();}catch(_e){}
    });
    this._rxJobs.set(id,token);
    this._process=token;
    return token;
  }

  _processUpdate(token,detail,done=null,total=null){
    if(!token||token.done||!token.card?.isConnected)return;
    const detailNode=token.card.querySelector(".rx-job-detail");if(detailNode&&detail!==undefined)detailNode.textContent=String(detail||"");
    if(Number.isFinite(done)&&Number.isFinite(total)&&Number(total)>0){
      const pct=Math.max(0,Math.min(100,Math.round(Number(done)/Number(total)*100)));
      const progress=token.card.querySelector(".rx-job-progress");progress?.classList.add("determinate");
      const bar=progress?.querySelector("div");if(bar)bar.style.width=`${pct}%`;
      const label=token.card.querySelector(".rx-job-percent");if(label)label.textContent=`${done}/${total} · ${pct}%`;
    }
  }

  _processEnd(token){
    if(!token||token.done)return;
    token.done=true;
    clearTimeout(token.revealTimer);
    const card=token.card;
    if(card?.isConnected){
      if(!token.shown){card.remove();}
      else{
        const title=card.querySelector(".rx-job-title");
        const detail=card.querySelector(".rx-job-detail");
        const icon=card.querySelector(".rx-job-icon ha-icon");
        card.classList.add(token.cancelled?"cancelled":"done");
        if(detail)detail.textContent=token.cancelled?this._t("jobCancelled"):this._t("jobDone");
        if(icon)icon.setAttribute("icon",token.cancelled?"mdi:cancel":"mdi:check-circle-outline");
        card.querySelector(".rx-job-cancel")?.remove();
        setTimeout(()=>card.remove(),token.cancelled?900:650);
      }
    }
    this._rxJobs.delete(token.id);
    if(this._process===token)this._process=[...this._rxJobs.values()].at(-1)||null;
  }

  _hasRunningJob(){return [...this._rxJobs.values()].some(job=>!job.done);}

  _autoJobForApi(type){
    const map={
      "cook4me/v16/nutrition_catalog_fill":[this._t("nutritionSettings"),this._t("buildingNutritionCatalog"),"database-sync-outline"],
      "cook4me/v15/barcode_map_add":[this._t("scanShopping"),this._t("savingData"),"barcode-scan"],
      "cook4me/v17/nutrition_label_save":[this._t("nutritionLabel"),this._t("nutritionLabelJob"),"nutrition"],
      "cook4me/v14/inventory_add":[this._t("pantry"),this._t("stockUpdate"),"basket-plus-outline"],
      "cook4me/v14/inventory_update":[this._t("pantry"),this._t("stockUpdate"),"basket-outline"],
      "cook4me/v14/inventory_remove":[this._t("pantry"),this._t("stockUpdate"),"basket-remove-outline"],
      "cook4me/v11/shopping_add":[this._t("shopping"),this._t("shoppingUpdate"),"cart-plus"],
      "cook4me/v12/shopping_action":[this._t("shopping"),this._t("shoppingUpdate"),"cart-check"],
      "cook4me/v16/nutrition_settings_set":[this._t("nutritionSettings"),this._t("savingData"),"content-save-outline"],
      "cook4me/recipe_save":[this._t("mine"),this._t("savingData"),"content-save-outline"],
      "cook4me/profile_save":[this._t("profile"),this._t("savingData"),"content-save-outline"],
    };
    return map[String(type||"")]||null;
  }

  async _api(type,data={}){
    const auto=this._autoJobForApi(type);
    if(!auto||this._hasRunningJob())return super._api(type,data);
    const [title,detail,icon]=auto;
    const job=this._processStart(title,detail,{icon,delay:160});
    try{return await super._api(type,data);}
    finally{this._processEnd(job);}
  }

  async _hydrateVisibleNutrition(items){
    const rows=(items||[]).slice(0,12);
    if(!rows.length)return;
    const job=this._processStart(this._t("nutrition"),this._t("hydratingNutrition"),{icon:"nutrition",delay:250});
    let cursor=0,done=0;
    const worker=async()=>{
      while(cursor<rows.length&&!job.cancelled){
        const index=cursor++;
        await this._fetchNutrition(rows[index],false);
        done++;
        this._processUpdate(job,`${this._t("hydratingNutrition")}: ${this._clean(rows[index]?.title||"")}`,done,rows.length);
      }
    };
    try{
      await Promise.all(Array.from({length:Math.min(3,rows.length)},()=>worker()));
      if(!job.cancelled&&(this._tab==="official"||this._tab==="recommend"||this._tab==="today"))this._renderTab();
    }finally{this._processEnd(job);}
  }

  async _loadIngredientCatalog(language=null,refresh=false){
    if(this._ingredientCatalogLoading||!this._entryId)return super._loadIngredientCatalog(language,refresh);
    const job=this._processStart(this._t("ingredientCatalog"),this._t("loadingCatalog"),{icon:"food-apple-outline",delay:250});
    try{await super._loadIngredientCatalog(language,refresh);}finally{this._processEnd(job);}
  }

  async _loadNutritionSettings(){
    if(this._nutritionSettingsLoading||!this._entryId)return super._loadNutritionSettings();
    const job=this._processStart(this._t("nutritionSettings"),this._t("loadingNutrition"),{icon:"nutrition",delay:300});
    try{await super._loadNutritionSettings();}finally{this._processEnd(job);}
  }

  async _loadTodayOptions(){
    if(this._todayOptionsLoading||!this._entryId)return super._loadTodayOptions();
    const job=this._processStart(this._t("today"),this._t("loadingTodayOptions"),{icon:"calendar-today",delay:250});
    try{await super._loadTodayOptions();}finally{this._processEnd(job);}
  }

  async _loadBookState(silent=false){
    if(this._bookLoading||!this._entryId)return super._loadBookState(silent);
    const job=this._processStart(this._t("book"),this._t("loadingBook"),{icon:"book-heart-outline",delay:450});
    try{await super._loadBookState(silent);}finally{this._processEnd(job);}
  }

  async _ensureScanCatalog(c){
    if(this._ingredientCatalog?.length||this._scanCatalogLoading||!this._entryId)return super._ensureScanCatalog(c);
    const job=this._processStart(this._t("ingredientCatalog"),this._t("loadingCatalog"),{icon:"food-apple-outline",delay:220});
    try{await super._ensureScanCatalog(c);}finally{this._processEnd(job);}
  }

  async _handleBarcode(code,c){
    if(!code||this._scannerBusy)return super._handleBarcode(code,c);
    const job=this._processStart(this._t("scanShopping"),this._t("lookingUpBarcode"),{icon:"barcode-scan",delay:120});
    try{await super._handleBarcode(code,c);}finally{this._processEnd(job);}
  }

  async _openLocal(recipe){
    const job=this._processStart(this._t("backgroundWork"),this._t("openingRecipe"),{icon:"book-open-page-variant-outline",delay:160});
    try{await super._openLocal(recipe);}finally{this._processEnd(job);}
  }

  async _selectRecipeLanguage(recipe,language,fromDetail=false){
    const job=this._processStart(this._t("recipeLanguage"),this._t("changingRecipe"),{icon:"translate",delay:150});
    try{await super._selectRecipeLanguage(recipe,language,fromDetail);}finally{this._processEnd(job);}
  }

  async _selectServing(recipe,variant,fromDetail=false){
    const job=this._processStart(this._t("servings"),this._t("changingRecipe"),{icon:"account-group-outline",delay:150});
    try{await super._selectServing(recipe,variant,fromDetail);}finally{this._processEnd(job);}
  }

  _buttonIcon(button){
    const id=String(button.id||"");
    const map={
      todaySuggest:"chef-hat",todayReset:"backup-restore",scannerToggle:"barcode-scan",manualBarcodeBtn:"barcode-scan",
      scanMapAdd:"link-plus",saveFdcApiKey:"content-save-outline",clearFdcApiKey:"key-remove",buildNutritionCatalog:"database-sync-outline",
      houseAdd:"plus-circle-outline",manualCatalogAdd:"plus-circle-outline",profileSave:"content-save-outline",manualSave:"content-save-outline",
      aiAddQueue:"playlist-plus",aiRunQueue:"play",aiStopQueue:"stop",headerQueueCancel:"close-circle-outline",bookQueueCancel:"close-circle-outline",
      nlScan:"camera-outline",nlEnter:"pencil-outline",nlSave:"content-save-outline",
    };
    if(map[id])return map[id];
    if(button.hasAttribute("data-stock-save"))return"content-save-outline";
    if(button.hasAttribute("data-stock-remove"))return"trash-can-outline";
    if(button.hasAttribute("data-manual-remove"))return"close-circle-outline";
    return super._buttonIcon(button);
  }

  _decorateLanguages(root){
    const selectors=["#cook4meUiLanguage","#recipeLanguage","#ingredientLanguage","#manualIngredientLanguage","[data-action='recipe-language']"];
    root.querySelectorAll(selectors.join(",")).forEach(select=>{
      for(const option of select.options||[]){
        if(!option.dataset.rxBaseLabel)option.dataset.rxBaseLabel=option.textContent.trim();
        const code=String(option.value||"").toLowerCase().split(/[-_]/)[0];
        const flag=this._flagForLanguage(code);
        const base=option.dataset.rxBaseLabel.replace(/^[\u{1F1E6}-\u{1F1FF}]{2}\s*/u,"").replace(/^🌐\s*/,"");
        option.textContent=`${flag} ${base}`;
      }
      const field=select.closest(".field");
      if(field){field.classList.add("rx-language-field");field.dataset.rxFlag=this._flagForLanguage(select.value);}
      if(!select.dataset.rxFlagChange){select.dataset.rxFlagChange="1";select.addEventListener("change",()=>{const f=select.closest(".field");if(f)f.dataset.rxFlag=this._flagForLanguage(select.value);});}
    });
  }

  _decorateFields(root){
    const map={
      cook4meUiLanguage:"translate",recipeLanguage:"translate",ingredientLanguage:"translate",manualIngredientLanguage:"translate",
      todayDiet:"account-heart-outline",todayNutritionGoal:"target",todayMealCount:"silverware-fork-knife",todayCalories:"fire",
      todayCalTolerance:"plus-minus",todayMaxMissing:"cart-minus",todayQuery:"magnify",todayRecent:"history",
      searchQ:"magnify",houseSearch:"magnify",manualCatalogSearch:"magnify",fdcApiKey:"key-outline",manualTitle:"format-title",manualServings:"account-group-outline",
    };
    for(const [id,icon] of Object.entries(map)){
      const input=root.getElementById(id);if(!input)continue;
      const label=input.closest(".field")?.querySelector(":scope > label");
      if(!label||label.dataset.rxIcon)return;
      label.dataset.rxIcon=icon;label.classList.add("rx-field-label");label.prepend(this._newIcon(icon,"rx-field-label-icon"));
    }
  }

  _upgradeChoiceStates(root){
    root.querySelectorAll(".rx-choice-card>input").forEach(input=>{
      const label=input.closest(".rx-choice-card");if(!label)return;
      label.classList.toggle("selected",Boolean(input.checked));
      if(input.dataset.rxChoiceBound)return;
      input.dataset.rxChoiceBound="1";
      input.addEventListener("change",()=>{label.classList.toggle("selected",Boolean(input.checked));this._updateTodaySummary(label.closest("section.rx-today-planner"));});
    });
  }

  _upgradeTodayPanel(root){
    const diet=root.getElementById("todayDiet");if(!diet)return;
    const planner=diet.closest("section.card");if(!planner)return;
    planner.classList.add("rx-today-planner");
    const head=planner.querySelector(":scope > .detail-head");
    if(head&&!head.querySelector(".rx-today-hero-icon")){
      const left=head.firstElementChild;
      if(left){const wrap=document.createElement("div");wrap.className="rx-today-head";left.before(wrap);const icon=document.createElement("span");icon.className="rx-today-hero-icon";icon.append(this._newIcon("chef-hat"));wrap.append(icon,left);}
    }
    const mealInput=planner.querySelector("[data-today-meal-type]");
    const mealGrid=mealInput?.closest(".chips");if(mealGrid)mealGrid.classList.add("rx-choice-grid","rx-meal-grid");
    const langInput=planner.querySelector("[data-today-language]");
    const langGrid=langInput?.closest(".chips");if(langGrid)langGrid.classList.add("rx-choice-grid","rx-language-grid");
    for(const [input,icon] of [[mealInput,"silverware-fork-knife"],[langInput,"translate"]]){
      const block=input?.closest("div[style*='margin-top']");const label=block?.querySelector(":scope > label");
      if(label&&!label.dataset.rxSectionIcon){label.dataset.rxSectionIcon="1";label.classList.add("rx-section-label");label.prepend(this._newIcon(icon));}
    }
    const onlyHome=planner.querySelector("#todayOnlyHome")?.closest("label");if(onlyHome)onlyHome.classList.add("rx-primary-toggle");
    const actionBar=planner.querySelector("#todaySuggest")?.closest(".toolbar");
    if(actionBar&&!planner.querySelector("details.rx-advanced")){
      const details=document.createElement("details");details.className="rx-advanced";
      details.innerHTML=`<summary><ha-icon icon="mdi:filter-variant"></ha-icon><span>${this._escape(this._t("moreFilters"))}</span></summary><div class="rx-advanced-content"></div>`;
      actionBar.before(details);
      const body=details.querySelector(".rx-advanced-content");
      for(const id of ["todayCalTolerance","todayMaxMissing","todayRecent"]){const field=planner.querySelector(`#${id}`)?.closest(".field");if(field)body.append(field);}
      for(const id of ["todayPreferExpiring","todayVariety"]){const label=planner.querySelector(`#${id}`)?.closest("label");if(label)body.append(label);}
    }
    if(!planner.querySelector(".rx-plan-summary")){
      const summary=document.createElement("div");summary.className="rx-plan-summary";
      const action=planner.querySelector("#todaySuggest")?.closest(".toolbar");action?.before(summary);
      planner.addEventListener("change",()=>this._updateTodaySummary(planner));
      planner.addEventListener("input",()=>this._updateTodaySummary(planner));
    }
    this._updateTodaySummary(planner);
  }

  _updateTodaySummary(planner){
    if(!planner)return;
    const target=planner.querySelector(".rx-plan-summary");if(!target)return;
    const parts=[];
    const diet=planner.querySelector("#todayDiet");if(diet)parts.push(`<span class="chip"><ha-icon icon="mdi:${DIET_ICONS[diet.value]||"account-heart-outline"}"></ha-icon>${this._escape(diet.options[diet.selectedIndex]?.textContent?.replace(/^[^\p{L}\p{N}]+/u,"")||diet.value)}</span>`);
    const goal=planner.querySelector("#todayNutritionGoal");if(goal)parts.push(`<span class="chip"><ha-icon icon="mdi:${GOAL_ICONS[goal.value]||"target"}"></ha-icon>${this._escape(goal.options[goal.selectedIndex]?.textContent?.replace(/^[^\p{L}\p{N}]+/u,"")||goal.value)}</span>`);
    const meals=Number(planner.querySelector("#todayMealCount")?.value||1);parts.push(`<span class="chip"><ha-icon icon="mdi:silverware-fork-knife"></ha-icon>${meals}</span>`);
    const calories=String(planner.querySelector("#todayCalories")?.value||"").trim();if(calories)parts.push(`<span class="chip"><ha-icon icon="mdi:fire"></ha-icon>${this._escape(calories)} kcal</span>`);
    const languages=[...planner.querySelectorAll("[data-today-language]:checked")].map(x=>this._flagForLanguage(x.dataset.todayLanguage)).join("");if(languages)parts.push(`<span class="chip"><ha-icon icon="mdi:translate"></ha-icon>${languages}</span>`);
    if(planner.querySelector("#todayOnlyHome")?.checked)parts.push(`<span class="chip"><ha-icon icon="mdi:home-check-outline"></ha-icon>${this._escape(this._t("onlyHome"))}</span>`);
    target.innerHTML=`<span class="rx-plan-title"><ha-icon icon="mdi:tune-variant"></ha-icon>${this._escape(this._t("quickPlan"))}</span>${parts.join("")}`;
    target.querySelectorAll("ha-icon").forEach(icon=>icon.style.setProperty("--mdc-icon-size","15px"));
  }

  _upgradeIngredientSheet(root){
    root.querySelectorAll(".rx-overlay>.rx-dialog").forEach(dialog=>{
      const heading=dialog.querySelector("h2")?.textContent||"";
      if(heading.includes(this._t("ingredientInfo"))||dialog.querySelector("[data-shop]"))dialog.classList.add("rx-ingredient-sheet");
    });
  }
}

customElements.define("cook4me-recipe-hub-panel-v32",Cook4MeRecipeHubPanelV32);
