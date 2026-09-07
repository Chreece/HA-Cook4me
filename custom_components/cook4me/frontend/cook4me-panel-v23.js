import "./cook4me-panel-v22.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v22");

const TEXT = {
  en:{
    nutrition:"Nutrition",wholeMeal:"Whole meal",perServingNutrition:"Per serving",calories:"Calories",protein:"Protein",carbs:"Carbs",fat:"Fat",fiber:"Fibre",sugars:"Sugars",saturatedFat:"Saturated fat",salt:"Salt",
    nutritionCoverage:"Nutrition coverage",nutritionEstimate:"Estimate",nutritionExact:"Uses scanned product nutrition",nutritionLoading:"Calculating nutrition…",nutritionUnavailable:"Not enough nutrition data to calculate this meal yet.",
    nutritionSettings:"Nutrition catalog",fdcApiKey:"USDA FoodData Central API key",fdcHelp:"Optional. Without your own key Cook4Me uses USDA DEMO_KEY with low rate limits. A personal key lets the generic nutrition catalog build much faster.",
    saveApiKey:"Save API key",clearApiKey:"Clear API key",apiKeyConfigured:"Personal USDA API key configured",demoKeyMode:"Using USDA DEMO_KEY",buildCatalog:"Build next nutrition catalog batch",catalogMapped:"generic ingredients mapped",catalogRemaining:"remaining",scannedNutrition:"Nutrition captured from scanned product",
  },
  de:{
    nutrition:"Nährwerte",wholeMeal:"Gesamtes Gericht",perServingNutrition:"Pro Portion",calories:"Kalorien",protein:"Eiweiß",carbs:"Kohlenhydrate",fat:"Fett",fiber:"Ballaststoffe",sugars:"Zucker",saturatedFat:"Gesättigte Fettsäuren",salt:"Salz",
    nutritionCoverage:"Nährwert-Abdeckung",nutritionEstimate:"Schätzung",nutritionExact:"Verwendet Nährwerte gescannter Produkte",nutritionLoading:"Nährwerte werden berechnet…",nutritionUnavailable:"Noch nicht genug Nährwertdaten für dieses Gericht.",
    nutritionSettings:"Nährwertkatalog",fdcApiKey:"USDA FoodData Central API-Schlüssel",fdcHelp:"Optional. Ohne eigenen Schlüssel nutzt Cook4Me den USDA-DEMO_KEY mit niedrigen Limits. Mit einem persönlichen Schlüssel kann der generische Nährwertkatalog deutlich schneller aufgebaut werden.",
    saveApiKey:"API-Schlüssel speichern",clearApiKey:"API-Schlüssel löschen",apiKeyConfigured:"Persönlicher USDA-API-Schlüssel eingerichtet",demoKeyMode:"USDA DEMO_KEY wird verwendet",buildCatalog:"Nächsten Nährwert-Katalogblock aufbauen",catalogMapped:"generische Zutaten zugeordnet",catalogRemaining:"verbleibend",scannedNutrition:"Nährwerte vom gescannten Produkt übernommen",
  },
  el:{
    nutrition:"Διατροφικά στοιχεία",wholeMeal:"Ολόκληρο γεύμα",perServingNutrition:"Ανά μερίδα",calories:"Θερμίδες",protein:"Πρωτεΐνη",carbs:"Υδατάνθρακες",fat:"Λιπαρά",fiber:"Φυτικές ίνες",sugars:"Σάκχαρα",saturatedFat:"Κορεσμένα λιπαρά",salt:"Αλάτι",
    nutritionCoverage:"Κάλυψη διατροφικών στοιχείων",nutritionEstimate:"Εκτίμηση",nutritionExact:"Χρησιμοποιεί στοιχεία από σαρωμένα προϊόντα",nutritionLoading:"Υπολογισμός διατροφικών στοιχείων…",nutritionUnavailable:"Δεν υπάρχουν ακόμη αρκετά διατροφικά δεδομένα για αυτό το γεύμα.",
    nutritionSettings:"Κατάλογος διατροφικών στοιχείων",fdcApiKey:"Κλειδί API USDA FoodData Central",fdcHelp:"Προαιρετικό. Χωρίς προσωπικό κλειδί το Cook4Me χρησιμοποιεί το USDA DEMO_KEY με χαμηλά όρια. Με προσωπικό κλειδί ο γενικός κατάλογος διατροφής δημιουργείται πολύ γρηγορότερα.",
    saveApiKey:"Αποθήκευση κλειδιού API",clearApiKey:"Διαγραφή κλειδιού API",apiKeyConfigured:"Έχει ρυθμιστεί προσωπικό κλειδί USDA API",demoKeyMode:"Χρήση USDA DEMO_KEY",buildCatalog:"Δημιουργία επόμενης παρτίδας καταλόγου",catalogMapped:"γενικά υλικά αντιστοιχισμένα",catalogRemaining:"απομένουν",scannedNutrition:"Τα διατροφικά στοιχεία λήφθηκαν από το σαρωμένο προϊόν",
  },
};

class Cook4MeRecipeHubPanelV23 extends BasePanel {
  constructor(){
    super();
    this._nutritionSettings=null;
    this._nutritionSettingsLoading=false;
    this._nutritionBusy=new Set();
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _nutritionRecipePayload(recipe){
    return {
      title:recipe?.title||"",
      servings:recipe?.servings,
      groupSize:recipe?.groupSize,
      yield:recipe?.yield,
      ingredients:Array.isArray(recipe?._nutritionIngredients)?recipe._nutritionIngredients:(recipe?.ingredients||[]),
    };
  }

  _applyTranslation(recipe,row){
    if(!Array.isArray(recipe?._nutritionIngredients)&&Array.isArray(recipe?.ingredients)&&recipe.ingredients.some(item=>item&&typeof item==="object")){
      recipe._nutritionIngredients=recipe.ingredients.map(item=>item&&typeof item==="object"?{...item}:item);
    }
    return super._applyTranslation(recipe,row);
  }

  _metric(value,key,unit="g"){
    const number=Number(value);
    if(!Number.isFinite(number))return"";
    const shown=key==="energyKcal"?Math.round(number):Number(number.toFixed(1));
    return `${shown}${unit?` ${unit}`:""}`;
  }

  _nutritionChips(values,compact=false){
    if(!values||typeof values!=="object")return"";
    const rows=[
      ["energyKcal",this._t("calories"),"kcal"],
      ["protein",this._t("protein"),"g"],
      ["carbohydrates",this._t("carbs"),"g"],
      ["fat",this._t("fat"),"g"],
      ...(!compact?[["fiber",this._t("fiber"),"g"],["sugars",this._t("sugars"),"g"],["saturatedFat",this._t("saturatedFat"),"g"],["salt",this._t("salt"),"g"]]:[]),
    ];
    return rows.filter(([key])=>Number.isFinite(Number(values[key]))).map(([key,label,unit])=>`<span class="chip">${this._escape(label)}: ${this._escape(this._metric(values[key],key,unit))}</span>`).join("");
  }

  _nutritionBlock(nutrition){
    if(!nutrition||!nutrition.totals||!Object.keys(nutrition.totals).length)return `<section class="card" style="margin:12px 0"><h3 style="margin-top:0">${this._escape(this._t("nutrition"))}</h3><div class="muted">${this._escape(this._t("nutritionUnavailable"))}</div></section>`;
    const coverage=Math.round(Number(nutrition.coverage||0)*100);
    const exact=(nutrition.sourceKinds||[]).includes("exact_product");
    return `<section class="card" style="margin:12px 0">
      <h3 style="margin-top:0">${this._escape(this._t("nutrition"))}</h3>
      <div class="muted" style="margin-bottom:7px">${this._escape(this._t("nutritionCoverage"))}: ${coverage}%${nutrition.estimated?` · ${this._escape(this._t("nutritionEstimate"))}`:""}${exact?` · ${this._escape(this._t("nutritionExact"))}`:""}</div>
      <div><strong>${this._escape(this._t("wholeMeal"))}</strong><div class="chips" style="margin-top:6px">${this._nutritionChips(nutrition.totals,false)}</div></div>
      ${nutrition.perServing&&Object.keys(nutrition.perServing).length?`<div style="margin-top:10px"><strong>${this._escape(this._t("perServingNutrition"))}${nutrition.servings?` (${this._escape(nutrition.servings)})`:""}</strong><div class="chips" style="margin-top:6px">${this._nutritionChips(nutrition.perServing,false)}</div></div>`:""}
    </section>`;
  }

  async _fetchNutrition(recipe,resolveMissing){
    if(!this._entryId||!recipe)return null;
    const key=this._recipeKey?this._recipeKey(recipe):String(recipe?.title||"recipe");
    if(this._nutritionBusy.has(key))return null;
    this._nutritionBusy.add(key);
    try{
      const result=await this._api("cook4me/v16/nutrition_recipe",{
        entry_id:this._entryId,
        recipe:this._nutritionRecipePayload(recipe),
        resolve_missing:Boolean(resolveMissing),
        max_resolve:8,
      });
      if(result?.nutrition)recipe.nutrition=result.nutrition;
      if(result){
        this._nutritionSettings={...(this._nutritionSettings||{}),catalogCount:result.catalogCount??this._nutritionSettings?.catalogCount,fdcApiKeyConfigured:Boolean(result.fdcApiKeyConfigured),fdcMode:result.fdcMode||this._nutritionSettings?.fdcMode};
      }
      return result;
    }catch(_e){return null;}
    finally{this._nutritionBusy.delete(key);}
  }

  async _loadRecipeNutrition(recipe,resolveMissing=true){
    const key=this._recipeKey?this._recipeKey(recipe):String(recipe?.title||"recipe");
    this._nutritionBusy.add(`ui:${key}`);
    this._renderTab();
    await this._fetchNutrition(recipe,resolveMissing);
    this._nutritionBusy.delete(`ui:${key}`);
    if(this._opened&&recipe!==this._opened&&this._recipeKey&&this._recipeKey(this._opened)===key)this._opened.nutrition=recipe.nutrition;
    this._renderTab();
  }

  async _hydrateVisibleNutrition(items){
    const rows=(items||[]).slice(0,12);
    if(!rows.length)return;
    await Promise.allSettled(rows.map(recipe=>this._fetchNutrition(recipe,false)));
    if(this._tab==="official"||this._tab==="recommend")this._renderTab();
  }

  async _search(query){
    await super._search(query);
    void this._hydrateVisibleNutrition(this._results||[]);
  }

  async _recommend(){
    await super._recommend();
    void this._hydrateVisibleNutrition(this._recommendations||[]);
  }

  async _openOfficial(recipe){
    await super._openOfficial(recipe);
    if(this._opened)await this._loadRecipeNutrition(this._opened,true);
  }

  async _openLocal(recipe){
    await super._openLocal(recipe);
    if(this._opened)await this._loadRecipeNutrition(this._opened,true);
  }

  _recipeCard(recipe,custom=false){
    let html=super._recipeCard(recipe,custom);
    const nutrition=recipe?.nutrition;
    if(nutrition?.totals&&Object.keys(nutrition.totals).length){
      const chips=this._nutritionChips(nutrition.perServing&&Object.keys(nutrition.perServing).length?nutrition.perServing:nutrition.totals,true);
      if(chips)html=html.replace('<div class="chips">',`<div class="chips">${chips}`);
    }
    return html;
  }

  _detailHtml(recipe){
    let html=super._detailHtml(recipe);
    if(!html||!recipe)return html;
    const key=this._recipeKey?this._recipeKey(recipe):String(recipe?.title||"recipe");
    const loading=this._nutritionBusy.has(`ui:${key}`);
    const block=loading?`<section class="card" style="margin:12px 0"><h3 style="margin-top:0">${this._escape(this._t("nutrition"))}</h3><div class="muted">${this._escape(this._t("nutritionLoading"))}</div></section>`:this._nutritionBlock(recipe.nutrition);
    const marker='<div class="detail-layout"';
    const pos=html.indexOf(marker);
    return pos>=0?`${html.slice(0,pos)}${block}${html.slice(pos)}`:`${block}${html}`;
  }

  _scannerResultHtml(){
    const html=super._scannerResultHtml();
    const nutrition=this._scannerResult?.product?.nutrition||this._scannerResult?.mapping?.nutrition;
    if(!nutrition?.values)return html;
    const block=`<div class="card" style="padding:10px;margin:8px 0"><strong>${this._escape(this._t("scannedNutrition"))}</strong><div class="chips" style="margin-top:6px">${this._nutritionChips(nutrition.values,false)}</div></div>`;
    return `${block}${html}`;
  }

  async _loadNutritionSettings(){
    if(this._nutritionSettingsLoading||!this._entryId)return;
    this._nutritionSettingsLoading=true;
    try{this._nutritionSettings=await this._api("cook4me/v16/nutrition_settings",{entry_id:this._entryId});}
    catch(_e){}
    finally{this._nutritionSettingsLoading=false;if(this._tab==="profile")this._renderTab();}
  }

  _nutritionSettingsHtml(){
    const s=this._nutritionSettings||{};
    const status=s.fdcApiKeyConfigured?this._t("apiKeyConfigured"):this._t("demoKeyMode");
    const count=Number(s.catalogCount||0);
    const total=Number(s.catalogTotal||0);
    return `<section class="card" style="margin-top:14px">
      <h2 style="margin-top:0">${this._escape(this._t("nutritionSettings"))}</h2>
      <div class="muted" style="margin-bottom:10px">${this._escape(this._t("fdcHelp"))}</div>
      <div class="formgrid">
        <div class="field wide"><label>${this._escape(this._t("fdcApiKey"))}</label><input id="fdcApiKey" type="password" autocomplete="off" placeholder="${this._escape(status)}"></div>
        <div class="field wide"><div class="toolbar"><button id="saveFdcApiKey" type="button" class="btn secondary">${this._escape(this._t("saveApiKey"))}</button>${s.fdcApiKeyConfigured?`<button id="clearFdcApiKey" type="button" class="btn secondary">${this._escape(this._t("clearApiKey"))}</button>`:""}<button id="buildNutritionCatalog" type="button" class="btn secondary">${this._escape(this._t("buildCatalog"))}</button></div></div>
      </div>
      <div id="nutritionCatalogStatus" class="muted" style="margin-top:8px">${this._escape(status)} · ${count} ${this._escape(this._t("catalogMapped"))}${total?` / ${total}`:""}${Number.isFinite(Number(s.remaining))?` · ${s.remaining} ${this._escape(this._t("catalogRemaining"))}`:""}</div>
    </section>`;
  }

  _bindNutritionSettings(c){
    c.querySelector("#saveFdcApiKey")?.addEventListener("click",async()=>{
      const key=String(c.querySelector("#fdcApiKey")?.value||"").trim();
      if(!key)return;
      try{this._nutritionSettings=await this._api("cook4me/v16/nutrition_settings_set",{entry_id:this._entryId,api_key:key});this._renderProfile(c);}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    });
    c.querySelector("#clearFdcApiKey")?.addEventListener("click",async()=>{
      try{this._nutritionSettings=await this._api("cook4me/v16/nutrition_settings_set",{entry_id:this._entryId,api_key:""});this._renderProfile(c);}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    });
    c.querySelector("#buildNutritionCatalog")?.addEventListener("click",async()=>{
      const button=c.querySelector("#buildNutritionCatalog");if(button)button.disabled=true;
      try{
        const result=await this._api("cook4me/v16/nutrition_catalog_fill",{entry_id:this._entryId,limit:12});
        this._nutritionSettings={...(this._nutritionSettings||{}),...result};
        const status=c.querySelector("#nutritionCatalogStatus");
        if(status)status.textContent=`${result.catalogCount||0} ${this._t("catalogMapped")} / ${result.catalogTotal||0} · ${result.remaining||0} ${this._t("catalogRemaining")}`;
      }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
      finally{if(button)button.disabled=false;}
    });
  }

  _renderProfile(c){
    super._renderProfile(c);
    if(!this._nutritionSettings&&!this._nutritionSettingsLoading)queueMicrotask(()=>void this._loadNutritionSettings());
    c.insertAdjacentHTML("beforeend",this._nutritionSettingsHtml());
    this._bindNutritionSettings(c);
  }
}

customElements.define("cook4me-recipe-hub-panel-v23",Cook4MeRecipeHubPanelV23);
