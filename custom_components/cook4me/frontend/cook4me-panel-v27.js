import "./cook4me-panel-v26.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v26");

const TEXT = {
  en:{
    today:"Today",todayMeal:"Today's meal",todayHelp:"Build today's suggestion from several official Cook4Me catalogs while keeping diet/allergy safety, real stock quantities, expiry priority and nutrition evidence.",
    craving:"Craving / recipe text",cravingPlaceholder:"e.g. risotto, curry…",mealTypes:"Meal type",breakfast:"Breakfast",starter:"Starter",salad:"Salad",soup:"Soup",main:"Main course",side:"Side dish",dessert:"Dessert",snack:"Snack",
    onlyHome:"Only what I have at home",catalogLanguages:"Catalog languages",catalogLanguagesHelp:"Choose one or more official source catalogs.",nutritionTarget:"Nutritional target",numberMeals:"How many meal suggestions",calorieTarget:"Calories per serving target",calorieTolerance:"Calorie tolerance",maxMissing:"Maximum known missing ingredients",maxMissingHelp:"Leave empty for no limit. “Only at home” is stricter and also rejects uncertain quantities.",
    preferExpiring:"Prefer food expiring soon",avoidRecent:"Avoid meals cooked recently",dontAvoid:"Do not avoid",days:"days",variety:"Keep multiple suggestions diverse",suggestToday:"Suggest today's meal",resetToday:"Reset",todayResults:"Today's suggestions",noTodayResults:"No recipe matched all selected filters.",todayCandidates:"candidates considered",tooManyLanguages:"Too many catalog languages selected",needLanguage:"Select at least one catalog language",perServingTarget:"target",catalog:"catalog",
  },
  de:{
    today:"Heute",todayMeal:"Heutiges Essen",todayHelp:"Erstellt den heutigen Vorschlag aus mehreren offiziellen Cook4Me-Katalogen und berücksichtigt Ernährung/Allergien, echte Vorratsmengen, Ablaufpriorität und Nährwertdaten.",
    craving:"Wunsch / Rezepttext",cravingPlaceholder:"z. B. Risotto, Curry…",mealTypes:"Mahlzeitentyp",breakfast:"Frühstück",starter:"Vorspeise",salad:"Salat",soup:"Suppe",main:"Hauptgericht",side:"Beilage",dessert:"Dessert",snack:"Snack",
    onlyHome:"Nur mit dem, was ich zu Hause habe",catalogLanguages:"Katalogsprachen",catalogLanguagesHelp:"Eine oder mehrere offizielle Quellsprachen wählen.",nutritionTarget:"Nährwertziel",numberMeals:"Anzahl Essensvorschläge",calorieTarget:"Kalorienziel pro Portion",calorieTolerance:"Kalorientoleranz",maxMissing:"Maximal bekannte fehlende Zutaten",maxMissingHelp:"Leer lassen für unbegrenzt. „Nur zu Hause“ ist strenger und schließt auch unsichere Mengen aus.",
    preferExpiring:"Bald ablaufende Lebensmittel bevorzugen",avoidRecent:"Kürzlich gekochte Gerichte vermeiden",dontAvoid:"Nicht vermeiden",days:"Tage",variety:"Mehrere Vorschläge abwechslungsreich halten",suggestToday:"Heutiges Essen vorschlagen",resetToday:"Zurücksetzen",todayResults:"Heutige Vorschläge",noTodayResults:"Kein Rezept erfüllt alle gewählten Filter.",todayCandidates:"Kandidaten geprüft",tooManyLanguages:"Zu viele Katalogsprachen ausgewählt",needLanguage:"Mindestens eine Katalogsprache auswählen",perServingTarget:"Ziel",catalog:"Katalog",
  },
  el:{
    today:"Σήμερα",todayMeal:"Σημερινό γεύμα",todayHelp:"Δημιουργεί τη σημερινή πρόταση από πολλούς επίσημους καταλόγους Cook4Me, διατηρώντας τους κανόνες διατροφής/αλλεργιών, τις πραγματικές ποσότητες, την προτεραιότητα λήξης και τα διαθέσιμα διατροφικά στοιχεία.",
    craving:"Επιθυμία / κείμενο συνταγής",cravingPlaceholder:"π.χ. ριζότο, κάρυ…",mealTypes:"Τύπος γεύματος",breakfast:"Πρωινό",starter:"Ορεκτικό",salad:"Σαλάτα",soup:"Σούπα",main:"Κυρίως",side:"Συνοδευτικό",dessert:"Επιδόρπιο",snack:"Σνακ",
    onlyHome:"Μόνο με όσα έχω στο σπίτι",catalogLanguages:"Γλώσσες καταλόγου",catalogLanguagesHelp:"Επίλεξε μία ή περισσότερες επίσημες γλώσσες πηγής.",nutritionTarget:"Διατροφικός στόχος",numberMeals:"Πόσες προτάσεις γεύματος",calorieTarget:"Στόχος θερμίδων ανά μερίδα",calorieTolerance:"Ανοχή θερμίδων",maxMissing:"Μέγιστα γνωστά υλικά που λείπουν",maxMissingHelp:"Κενό σημαίνει χωρίς όριο. Το «μόνο στο σπίτι» είναι αυστηρότερο και απορρίπτει και αβέβαιες ποσότητες.",
    preferExpiring:"Προτίμηση τροφίμων που λήγουν σύντομα",avoidRecent:"Αποφυγή πρόσφατα μαγειρεμένων γευμάτων",dontAvoid:"Χωρίς αποφυγή",days:"ημέρες",variety:"Διαφορετικές προτάσεις όταν ζητούνται πολλά γεύματα",suggestToday:"Πρότεινε σημερινό γεύμα",resetToday:"Επαναφορά",todayResults:"Σημερινές προτάσεις",noTodayResults:"Καμία συνταγή δεν ταίριαξε σε όλα τα επιλεγμένα φίλτρα.",todayCandidates:"υποψήφιες συνταγές",tooManyLanguages:"Επιλέχθηκαν πάρα πολλές γλώσσες καταλόγου",needLanguage:"Επίλεξε τουλάχιστον μία γλώσσα καταλόγου",perServingTarget:"στόχος",catalog:"κατάλογος",
  },
};

class Cook4MeRecipeHubPanelV27 extends BasePanel {
  constructor(){
    super();
    this._todayOptions=null;
    this._todayOptionsLoading=false;
    this._todayResults=[];
    this._todayMeta=null;
    this._todayBusy=false;
    this._todaySettings=null;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _todayStorageKey(){
    const user=String(this._hass?.user?.id||"anonymous");
    const entry=String(this._entryId||"default");
    return `cook4me.today.v1.${user}.${entry}`;
  }

  _todayDefaults(){
    const language=String(this._capabilities?.deviceCatalogLanguage||this._capabilities?.ingredientCatalogLanguage||"de").toLowerCase();
    return {diet:"profile",mealTypes:[],onlyHome:false,languages:[language],nutritionGoal:String(this._uiPreferences?.nutritionGoal||"balanced"),mealCount:1,calorieTarget:"",calorieTolerance:25,maxMissing:"",preferExpiring:true,avoidRecentDays:7,variety:true,query:""};
  }

  _loadTodaySettings(){
    const defaults=this._todayDefaults();
    try{
      const raw=JSON.parse(localStorage.getItem(this._todayStorageKey())||"null");
      if(!raw||typeof raw!=="object")return defaults;
      return {...defaults,...raw,mealTypes:Array.isArray(raw.mealTypes)?raw.mealTypes:[],languages:Array.isArray(raw.languages)&&raw.languages.length?raw.languages:defaults.languages};
    }catch(_e){return defaults;}
  }

  _saveTodaySettings(){
    try{localStorage.setItem(this._todayStorageKey(),JSON.stringify(this._todaySettings||this._todayDefaults()));}catch(_e){}
  }

  async _loadCapabilities(){
    await super._loadCapabilities();
    const tab=String(this._capabilities?.preferences?.lastTab||"");
    if(tab==="today"&&this._tab!=="today"){
      this._tab="today";
      this._uiPreferences={...(this._uiPreferences||{}),lastTab:"today"};
      this._renderTabs();
      this._renderTab();
    }
  }

  _renderTabs(){
    super._renderTabs();
    const tabs=this.shadowRoot?.getElementById("tabs");
    if(!tabs||tabs.querySelector('[data-tab="today"]'))return;
    const button=document.createElement("button");
    button.className=`tab ${this._tab==="today"?"active":""}`;
    button.dataset.tab="today";
    button.textContent=this._t("today");
    button.addEventListener("click",()=>{
      this._tab="today";
      this._opened=null;
      this._uiPreferences={...(this._uiPreferences||{}),lastTab:"today"};
      this._schedulePreferenceSave?.();
      this._renderTabs();
      this._renderTab();
    });
    tabs.prepend(button);
  }

  _renderTab(){
    if(this._tab==="today"){
      const c=this.shadowRoot?.getElementById("content");
      if(c)this._renderToday(c);
      return;
    }
    super._renderTab();
  }

  async _loadTodayOptions(){
    if(this._todayOptionsLoading||!this._entryId)return;
    this._todayOptionsLoading=true;
    try{this._todayOptions=await this._api("cook4me/v18/today_options",{entry_id:this._entryId});}
    catch(_e){}
    finally{this._todayOptionsLoading=false;if(this._tab==="today")this._renderTab();}
  }

  _todayLanguageRows(){
    const rows=this._todayOptions?.languages||this._capabilities?.languages||[];
    return Array.isArray(rows)?rows:[];
  }

  _todayMealTypeHtml(settings){
    const values=["breakfast","starter","salad","soup","main","side","dessert","snack"];
    const selected=new Set(settings.mealTypes||[]);
    return values.map(value=>`<label class="chip" style="cursor:pointer"><input data-today-meal-type="${value}" type="checkbox" ${selected.has(value)?"checked":""}> ${this._escape(this._t(value))}</label>`).join("");
  }

  _todayLanguageHtml(settings){
    const selected=new Set((settings.languages||[]).map(x=>String(x).toLowerCase()));
    return this._todayLanguageRows().map(row=>{const code=String(row.code||"").toLowerCase();if(!code)return"";return`<label class="chip" style="cursor:pointer"><input data-today-language="${this._escape(code)}" type="checkbox" ${selected.has(code)?"checked":""}> ${this._escape(code.toUpperCase())}${row.country?` · ${this._escape(row.country)}`:""}</label>`;}).join("");
  }

  _todayDietOptions(value){
    const rows=[["profile",`${this._t("profileDiet")} (${this._t(String(this._entry()?.profile?.diet||"omnivore"))})`],["omnivore",this._t("omnivore")],["pescatarian",this._t("pescatarian")],["vegetarian",this._t("vegetarian")],["vegan",this._t("vegan")]];
    return rows.map(([v,l])=>`<option value="${v}" ${v===value?"selected":""}>${this._escape(l)}</option>`).join("");
  }

  _todayGoalOptions(value){
    const rows=[["balanced","balanced"],["high_protein","highProtein"],["lower_calorie","lowerCalorie"],["high_fiber","highFiber"],["lower_saturated_fat","lowerSaturatedFat"]];
    return rows.map(([v,k])=>`<option value="${v}" ${v===value?"selected":""}>${this._escape(this._t(k))}</option>`).join("");
  }

  _renderToday(c){
    if(!this._todaySettings)this._todaySettings=this._loadTodaySettings();
    if(!this._todayOptions&&!this._todayOptionsLoading)queueMicrotask(()=>void this._loadTodayOptions());
    const s=this._todaySettings;
    const date=new Intl.DateTimeFormat(this._langCode(),{dateStyle:"full"}).format(new Date());
    const detail=this._detailHtml(this._opened);
    const results=this._todayResults.length?`<section class="card" style="margin-top:14px"><div class="detail-head"><div><h2 style="margin:0">${this._escape(this._t("todayResults"))}</h2><div class="muted">${this._escape(date)}${this._todayMeta?` · ${Number(this._todayMeta.candidateCount||0)} ${this._escape(this._t("todayCandidates"))}`:""}</div></div></div></section><div id="todayGrid" class="grid" style="margin-top:14px">${this._todayResults.map(recipe=>this._recipeCard(recipe,false)).join("")}</div>`:(this._todayMeta&&!this._todayBusy?`<section class="card" style="margin-top:14px"><div class="empty">${this._escape(this._t("noTodayResults"))}</div></section>`:"");
    c.innerHTML=`<section class="card">
      <div class="detail-head"><div><h2 style="margin:0">${this._escape(this._t("todayMeal"))}</h2><div class="muted">${this._escape(date)}</div></div></div>
      <div class="muted" style="margin:8px 0 14px">${this._escape(this._t("todayHelp"))}</div>
      <div class="formgrid">
        <div class="field"><label>${this._escape(this._t("dietFilter"))}</label><select id="todayDiet">${this._todayDietOptions(String(s.diet||"profile"))}</select></div>
        <div class="field"><label>${this._escape(this._t("nutritionTarget"))}</label><select id="todayNutritionGoal">${this._todayGoalOptions(String(s.nutritionGoal||"balanced"))}</select></div>
        <div class="field"><label>${this._escape(this._t("numberMeals"))}</label><select id="todayMealCount">${[1,2,3,4,5,6,7,8].map(n=>`<option value="${n}" ${Number(s.mealCount||1)===n?"selected":""}>${n}</option>`).join("")}</select></div>
        <div class="field"><label>${this._escape(this._t("calorieTarget"))}</label><input id="todayCalories" type="number" min="1" step="1" value="${this._escape(s.calorieTarget??"")}" placeholder="kcal"></div>
        <div class="field"><label>${this._escape(this._t("calorieTolerance"))}</label><select id="todayCalTolerance">${[10,15,25,40,50].map(n=>`<option value="${n}" ${Number(s.calorieTolerance||25)===n?"selected":""}>±${n}%</option>`).join("")}</select></div>
        <div class="field"><label>${this._escape(this._t("maxMissing"))}</label><input id="todayMaxMissing" type="number" min="0" max="20" step="1" value="${this._escape(s.maxMissing??"")}"><div class="muted">${this._escape(this._t("maxMissingHelp"))}</div></div>
        <div class="field wide"><label>${this._escape(this._t("craving"))}</label><input id="todayQuery" value="${this._escape(s.query||"")}" placeholder="${this._escape(this._t("cravingPlaceholder"))}"></div>
      </div>
      <div style="margin-top:12px"><label>${this._escape(this._t("mealTypes"))}</label><div class="chips" style="margin-top:6px">${this._todayMealTypeHtml(s)}</div></div>
      <div style="margin-top:12px"><label>${this._escape(this._t("catalogLanguages"))}</label><div class="muted">${this._escape(this._t("catalogLanguagesHelp"))}${this._todayOptions?.maxLanguages?` · max ${this._todayOptions.maxLanguages}`:""}</div><div class="chips" style="margin-top:6px">${this._todayLanguageHtml(s)}</div></div>
      <div class="toolbar" style="margin-top:14px;align-items:center">
        <label class="chip"><input id="todayOnlyHome" type="checkbox" ${s.onlyHome?"checked":""}> ${this._escape(this._t("onlyHome"))}</label>
        <label class="chip"><input id="todayPreferExpiring" type="checkbox" ${s.preferExpiring!==false?"checked":""}> ${this._escape(this._t("preferExpiring"))}</label>
        <label class="chip"><input id="todayVariety" type="checkbox" ${s.variety!==false?"checked":""}> ${this._escape(this._t("variety"))}</label>
      </div>
      <div class="field" style="max-width:260px;margin-top:12px"><label>${this._escape(this._t("avoidRecent"))}</label><select id="todayRecent"><option value="0" ${Number(s.avoidRecentDays||0)===0?"selected":""}>${this._escape(this._t("dontAvoid"))}</option>${[1,3,7,14,30].map(n=>`<option value="${n}" ${Number(s.avoidRecentDays||0)===n?"selected":""}>${n} ${this._escape(this._t("days"))}</option>`).join("")}</select></div>
      <div class="toolbar" style="margin-top:14px"><button id="todaySuggest" class="btn" ${this._todayBusy?"disabled":""}>${this._escape(this._todayBusy?this._t("loading"):this._t("suggestToday"))}</button><button id="todayReset" class="btn secondary">${this._escape(this._t("resetToday"))}</button></div>
    </section>${detail}${results}`;
    this._bindToday(c);
    this._bindDetail(c);
    const grid=c.querySelector("#todayGrid");if(grid)this._bindCards(grid,this._todayResults,false);
  }

  _collectToday(c){
    const languages=[...c.querySelectorAll("[data-today-language]:checked")].map(x=>String(x.dataset.todayLanguage||""));
    const mealTypes=[...c.querySelectorAll("[data-today-meal-type]:checked")].map(x=>String(x.dataset.todayMealType||""));
    return {diet:String(c.querySelector("#todayDiet")?.value||"profile"),nutritionGoal:String(c.querySelector("#todayNutritionGoal")?.value||"balanced"),mealCount:Number(c.querySelector("#todayMealCount")?.value||1),calorieTarget:String(c.querySelector("#todayCalories")?.value||""),calorieTolerance:Number(c.querySelector("#todayCalTolerance")?.value||25),maxMissing:String(c.querySelector("#todayMaxMissing")?.value||""),query:String(c.querySelector("#todayQuery")?.value||"").trim(),mealTypes,languages,onlyHome:Boolean(c.querySelector("#todayOnlyHome")?.checked),preferExpiring:Boolean(c.querySelector("#todayPreferExpiring")?.checked),variety:Boolean(c.querySelector("#todayVariety")?.checked),avoidRecentDays:Number(c.querySelector("#todayRecent")?.value||0)};
  }

  _bindToday(c){
    c.querySelector("#todaySuggest")?.addEventListener("click",()=>void this._suggestToday(c));
    c.querySelector("#todayQuery")?.addEventListener("keydown",event=>{if(event.key==="Enter")void this._suggestToday(c);});
    c.querySelector("#todayReset")?.addEventListener("click",()=>{this._todaySettings=this._todayDefaults();this._todayResults=[];this._todayMeta=null;this._saveTodaySettings();this._renderTab();});
  }

  async _suggestToday(c){
    const s=this._collectToday(c);const max=Number(this._todayOptions?.maxLanguages||8);
    if(!s.languages.length){this._message(this._t("needLanguage"),true);return;}
    if(s.languages.length>max){this._message(`${this._t("tooManyLanguages")}: ${max}`,true);return;}
    this._todaySettings=s;this._saveTodaySettings();this._opened=null;this._todayBusy=true;this._renderTab();
    try{
      const payload={entry_id:this._entryId,languages:s.languages,diet:s.diet,meal_types:s.mealTypes,only_home:s.onlyHome,nutrition_goal:s.nutritionGoal,meal_count:s.mealCount,calorie_tolerance:s.calorieTolerance,prefer_expiring:s.preferExpiring,avoid_recent_days:s.avoidRecentDays,variety:s.variety,query:s.query};
      if(s.calorieTarget!=="")payload.calorie_target=s.calorieTarget;
      if(s.maxMissing!=="")payload.max_missing=Number(s.maxMissing);
      const result=await this._api("cook4me/v18/today_suggest",payload);
      const items=Array.isArray(result?.items)?result.items:[];
      items.forEach(recipe=>this._ensureRecipeSelections(recipe));
      if(this._shouldTranslate()&&items.some(recipe=>this._translationNeeded(recipe)))await this._translateItems(items);
      this._todayResults=items;this._todayMeta=result||{};this._message("");
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    finally{this._todayBusy=false;this._renderTab();}
  }

  _recipeCard(recipe,custom=false){
    let html=super._recipeCard(recipe,custom);
    if(recipe?.todayCatalogLanguage){html=html.replace('<div class="chips">',`<div class="chips"><span class="chip">🌐 ${this._escape(String(recipe.todayCatalogLanguage).toUpperCase())}</span>`);}
    const target=Number(recipe?.match?.calorieTarget),actual=Number(recipe?.match?.caloriePerServing);
    if(Number.isFinite(target)&&Number.isFinite(actual)){html=html.replace('<div class="chips">',`<div class="chips"><span class="chip">🎯 ${this._escape(Math.round(actual))} kcal · ${this._escape(this._t("perServingTarget"))} ${this._escape(Math.round(target))}</span>`);}
    return html;
  }
}

customElements.define("cook4me-recipe-hub-panel-v27",Cook4MeRecipeHubPanelV27);
