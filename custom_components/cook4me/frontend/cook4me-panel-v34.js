import "./cook4me-panel-v33.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v33");
const TODAY_MEAL_TYPES=["breakfast","starter","salad","soup","main","side","dessert","snack"];

const TEXT={
  en:{selectAll:"Select all",deselectAll:"Deselect all",preferredIngredients:"Ingredients",preferredIngredientsHelp:"Optional. Choose ingredients from the Cook4Me catalog instead of typing recipe text. A suggestion must contain every selected ingredient.",needMealType:"Select at least one meal category.",onePerCategory:"One suggestion is shown for every selected meal category.",tapCollapse:"Tap the card again to collapse",steps:"Steps",loadingIngredientCatalog:"Loading ingredient catalog…"},
  de:{selectAll:"Alle auswählen",deselectAll:"Alle abwählen",preferredIngredients:"Zutaten",preferredIngredientsHelp:"Optional. Zutaten direkt aus dem Cook4Me-Katalog auswählen statt Rezepttext einzugeben. Eine Empfehlung muss alle gewählten Zutaten enthalten.",needMealType:"Mindestens eine Mahlzeitenkategorie auswählen.",onePerCategory:"Für jede ausgewählte Mahlzeitenkategorie wird genau eine Empfehlung angezeigt.",tapCollapse:"Karte erneut antippen zum Einklappen",steps:"Schritte",loadingIngredientCatalog:"Zutatenkatalog wird geladen…"},
  el:{selectAll:"Επιλογή όλων",deselectAll:"Αποεπιλογή όλων",preferredIngredients:"Υλικά",preferredIngredientsHelp:"Προαιρετικό. Επίλεξε υλικά απευθείας από τον κατάλογο Cook4Me αντί να γράφεις κείμενο. Η πρόταση πρέπει να περιέχει όλα τα επιλεγμένα υλικά.",needMealType:"Επίλεξε τουλάχιστον μία κατηγορία γεύματος.",onePerCategory:"Εμφανίζεται μία πρόταση για κάθε επιλεγμένη κατηγορία γεύματος.",tapCollapse:"Πάτησε ξανά την κάρτα για σύμπτυξη",steps:"Βήματα",loadingIngredientCatalog:"Φόρτωση καταλόγου υλικών…"},
};

class Cook4MeRecipeHubPanelV34 extends BasePanel{
  constructor(){
    super();
    this._inlineRecipeKey="";
    this._inlineRecipeCard=null;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _todayStorageKey(){
    const user=String(this._hass?.user?.id||"anonymous");
    const entry=String(this._entryId||"default");
    return `cook4me.today.v2.${user}.${entry}`;
  }

  _todayDefaults(){
    const base=super._todayDefaults?.()||{};
    return {...base,mealTypes:[...TODAY_MEAL_TYPES],mealCount:TODAY_MEAL_TYPES.length,query:"",ingredients:[]};
  }

  _loadTodaySettings(){
    const defaults=this._todayDefaults();
    try{
      const current=JSON.parse(localStorage.getItem(this._todayStorageKey())||"null");
      if(current&&typeof current==="object")return {...defaults,...current,mealTypes:Array.isArray(current.mealTypes)?current.mealTypes:defaults.mealTypes,ingredients:Array.isArray(current.ingredients)?current.ingredients:[]};
      const user=String(this._hass?.user?.id||"anonymous"),entry=String(this._entryId||"default");
      const legacy=JSON.parse(localStorage.getItem(`cook4me.today.v1.${user}.${entry}`)||"null");
      if(legacy&&typeof legacy==="object"){
        const mealTypes=Array.isArray(legacy.mealTypes)&&legacy.mealTypes.length?legacy.mealTypes:[...TODAY_MEAL_TYPES];
        return {...defaults,...legacy,mealTypes,mealCount:mealTypes.length,query:"",ingredients:[]};
      }
    }catch(_e){}
    return defaults;
  }

  _todayIngredientIdentity(row){
    const key=String(row?.key||row?.foodKey||"").trim();
    if(key)return `k:${key}`;
    return `n:${String(row?.name||row?.foodName||"").trim().toLocaleLowerCase()}`;
  }

  _todayIngredientRows(){return Array.isArray(this._ingredientCatalog)?this._ingredientCatalog:[];}
  _todaySelectedIngredientRows(settings){
    const selected=new Set((settings?.ingredients||[]).map(String));
    return this._todayIngredientRows().filter(row=>selected.has(this._todayIngredientIdentity(row)));
  }

  _todayIngredientsHtml(settings){
    const rows=this._todayIngredientRows();
    const selected=new Set((settings.ingredients||[]).map(String));
    if(!rows.length)return `<div class="muted">${this._escape(this._ingredientCatalogLoading?this._t("loadingIngredientCatalog"):this._t("noResults"))}</div>`;
    return `<select id="todayIngredients" multiple size="8" style="width:100%;min-height:210px">${rows.map(row=>{const id=this._todayIngredientIdentity(row);return `<option value="${this._escape(id)}" ${selected.has(id)?"selected":""}>${this._escape(row.name||row.foodName||id)}</option>`;}).join("")}</select>`;
  }

  _bulkButton(group,allSelected){return `<button type="button" class="btn secondary rx-bulk" data-today-bulk="${group}"><ha-icon icon="mdi:${allSelected?"checkbox-multiple-blank-outline":"checkbox-multiple-marked-outline"}"></ha-icon><span>${this._escape(this._t(allSelected?"deselectAll":"selectAll"))}</span></button>`;}

  async _loadIngredientCatalog(language=null,refresh=false){
    const result=await super._loadIngredientCatalog(language,refresh);
    if(this._tab==="today")this._renderTab();
    return result;
  }

  _renderToday(c){
    if(!this._todaySettings)this._todaySettings=this._loadTodaySettings();
    if(!this._todayOptions&&!this._todayOptionsLoading)queueMicrotask(()=>void this._loadTodayOptions());
    if(!this._ingredientCatalog?.length&&!this._ingredientCatalogLoading){
      const language=this._ingredientCatalogLanguage||this._capabilities?.ingredientCatalogLanguage||this._capabilities?.deviceCatalogLanguage||"de";
      queueMicrotask(()=>void this._loadIngredientCatalog(language,false));
    }
    const s=this._todaySettings;
    const date=new Intl.DateTimeFormat(this._langCode(),{dateStyle:"full"}).format(new Date());
    const selectedMeals=new Set(s.mealTypes||[]),languageRows=this._todayLanguageRows(),selectedLanguages=new Set((s.languages||[]).map(x=>String(x).toLowerCase()));
    const ingredientRows=this._todayIngredientRows(),selectedIngredients=new Set((s.ingredients||[]).map(String));
    const results=this._todayResults.length?`<section class="card" style="margin-top:14px"><div class="detail-head"><div><h2 style="margin:0">${this._escape(this._t("todayResults"))}</h2><div class="muted">${this._escape(date)} · ${this._escape(this._t("onePerCategory"))}</div></div></div></section><div id="todayGrid" class="rx-category-results">${this._todayResults.map(recipe=>{const type=String(recipe.todayMealType||"");const visual=globalThis.COOK4ME_MEAL_VISUALS?.[type];return `<section class="rx-category-result"><h3><ha-icon icon="mdi:${this._mealIcon(type)}"></ha-icon>${this._escape(this._t(type)||type)}</h3>${this._recipeCard(recipe,false)}</section>`;}).join("")}</div>`:(this._todayMeta&&!this._todayBusy?`<section class="card" style="margin-top:14px"><div class="empty">${this._escape(this._t("noTodayResults"))}</div></section>`:"");

    c.innerHTML=`<section class="card rx-today-planner">
      <div class="detail-head"><div><h2 style="margin:0">${this._escape(this._t("todayMeal"))}</h2><div class="muted">${this._escape(date)}</div></div></div>
      <div class="muted" style="margin:8px 0 14px">${this._escape(this._t("todayHelp"))}<br>${this._escape(this._t("onePerCategory"))}</div>
      <div class="formgrid">
        <div class="field"><label>${this._escape(this._t("dietFilter"))}</label><select id="todayDiet">${this._todayDietOptions(String(s.diet||"profile"))}</select></div>
        <div class="field"><label>${this._escape(this._t("nutritionTarget"))}</label><select id="todayNutritionGoal">${this._todayGoalOptions(String(s.nutritionGoal||"balanced"))}</select></div>
        <div class="field"><label>${this._escape(this._t("calorieTarget"))}</label><input id="todayCalories" type="number" min="1" step="1" value="${this._escape(s.calorieTarget??"")}" placeholder="kcal"></div>
      </div>

      <div style="margin-top:14px"><div class="rx-group-head"><label class="rx-section-label"><ha-icon icon="mdi:silverware-fork-knife"></ha-icon>${this._escape(this._t("mealTypes"))}</label>${this._bulkButton("meals",selectedMeals.size===TODAY_MEAL_TYPES.length)}</div><div class="chips rx-choice-grid rx-meal-grid" style="margin-top:6px">${this._todayMealTypeHtml(s)}</div></div>

      <div style="margin-top:14px"><div class="rx-group-head"><label class="rx-section-label"><ha-icon icon="mdi:translate"></ha-icon>${this._escape(this._t("catalogLanguages"))}</label>${this._bulkButton("languages",languageRows.length>0&&selectedLanguages.size===languageRows.length)}</div><div class="muted">${this._escape(this._t("catalogLanguagesHelp"))}</div><div class="chips rx-choice-grid rx-language-grid" style="margin-top:6px">${this._todayLanguageHtml(s)}</div></div>

      <div class="field wide" style="margin-top:14px"><div class="rx-group-head"><label class="rx-section-label"><ha-icon icon="mdi:food-apple-outline"></ha-icon>${this._escape(this._t("preferredIngredients"))}</label>${ingredientRows.length?this._bulkButton("ingredients",selectedIngredients.size===ingredientRows.length):""}</div><div class="muted" style="margin-bottom:7px">${this._escape(this._t("preferredIngredientsHelp"))}</div>${this._todayIngredientsHtml(s)}</div>

      <details class="rx-advanced"><summary><ha-icon icon="mdi:filter-variant"></ha-icon><span>${this._escape(this._t("moreFilters"))}</span></summary><div class="rx-advanced-content">
        <div class="field"><label>${this._escape(this._t("calorieTolerance"))}</label><select id="todayCalTolerance">${[10,15,25,40,50].map(n=>`<option value="${n}" ${Number(s.calorieTolerance||25)===n?"selected":""}>±${n}%</option>`).join("")}</select></div>
        <div class="field"><label>${this._escape(this._t("maxMissing"))}</label><input id="todayMaxMissing" type="number" min="0" max="20" step="1" value="${this._escape(s.maxMissing??"")}"></div>
        <div class="field"><label>${this._escape(this._t("avoidRecent"))}</label><select id="todayRecent"><option value="0" ${Number(s.avoidRecentDays||0)===0?"selected":""}>${this._escape(this._t("dontAvoid"))}</option>${[1,3,7,14,30].map(n=>`<option value="${n}" ${Number(s.avoidRecentDays||0)===n?"selected":""}>${n} ${this._escape(this._t("days"))}</option>`).join("")}</select></div>
        <label class="chip"><input id="todayPreferExpiring" type="checkbox" ${s.preferExpiring!==false?"checked":""}> ${this._escape(this._t("preferExpiring"))}</label>
        <label class="chip"><input id="todayOnlyHome" type="checkbox" ${s.onlyHome?"checked":""}> ${this._escape(this._t("onlyHome"))}</label>
      </div></details>
      <div class="toolbar" style="margin-top:14px"><button id="todaySuggest" class="btn" ${this._todayBusy?"disabled":""}><ha-icon icon="mdi:chef-hat"></ha-icon><span>${this._escape(this._todayBusy?this._t("loading"):this._t("suggestToday"))}</span></button><button id="todayReset" class="btn secondary"><ha-icon icon="mdi:backup-restore"></ha-icon><span>${this._escape(this._t("resetToday"))}</span></button></div>
    </section>${results}`;

    this._bindTodayV34(c);
    const grid=c.querySelector("#todayGrid");if(grid)this._bindCards(grid,this._todayResults,false);
    this._professionalizeSoon?.();
  }

  _collectTodayV34(c){
    const mealTypes=[...c.querySelectorAll("[data-today-meal-type]:checked")].map(x=>String(x.dataset.todayMealType||""));
    const languages=[...c.querySelectorAll("[data-today-language]:checked")].map(x=>String(x.dataset.todayLanguage||""));
    const ingredients=[...c.querySelector("#todayIngredients")?.selectedOptions||[]].map(option=>String(option.value||""));
    return {diet:String(c.querySelector("#todayDiet")?.value||"profile"),nutritionGoal:String(c.querySelector("#todayNutritionGoal")?.value||"balanced"),calorieTarget:String(c.querySelector("#todayCalories")?.value||""),calorieTolerance:Number(c.querySelector("#todayCalTolerance")?.value||25),maxMissing:String(c.querySelector("#todayMaxMissing")?.value||""),mealTypes,languages,ingredients,onlyHome:Boolean(c.querySelector("#todayOnlyHome")?.checked),preferExpiring:Boolean(c.querySelector("#todayPreferExpiring")?.checked),avoidRecentDays:Number(c.querySelector("#todayRecent")?.value||0),variety:true,mealCount:mealTypes.length,query:""};
  }

  _rememberTodayFromUi(c){this._todaySettings=this._collectTodayV34(c);this._saveTodaySettings();}

  _toggleTodayBulk(c,group){
    if(group==="ingredients"){
      const select=c.querySelector("#todayIngredients");if(!select)return;
      const options=[...select.options],all=options.length>0&&options.every(x=>x.selected);options.forEach(x=>x.selected=!all);
    }else{
      const selector=group==="meals"?"[data-today-meal-type]":"[data-today-language]";
      const rows=[...c.querySelectorAll(selector)],all=rows.length>0&&rows.every(x=>x.checked);rows.forEach(x=>{x.checked=!all;x.closest(".rx-choice-card")?.classList.toggle("selected",!all);});
    }
    this._rememberTodayFromUi(c);this._renderToday(c);
  }

  _bindTodayV34(c){
    c.querySelector("#todaySuggest")?.addEventListener("click",()=>void this._suggestTodayV34(c));
    c.querySelector("#todayReset")?.addEventListener("click",()=>{this._todaySettings=this._todayDefaults();this._todayResults=[];this._todayMeta=null;this._saveTodaySettings();this._renderToday(c);});
    c.querySelectorAll("[data-today-bulk]").forEach(button=>button.addEventListener("click",()=>this._toggleTodayBulk(c,String(button.dataset.todayBulk||""))));
    c.addEventListener("change",event=>{if(event.target.closest(".rx-today-planner"))this._rememberTodayFromUi(c);});
    this._upgradeChoiceStates?.(c);
  }

  _todayRecipeIdentity(recipe){
    if(typeof this._recipeKeyLocal==="function")return String(this._recipeKeyLocal(recipe)||"");
    for(const key of ["groupingFunctionalId","recipeFunctionalId","variantFunctionalId","displayVariantId","id"]){const value=String(recipe?.[key]||"").trim();if(value)return `${key}:${value}`;}
    return `title:${String(recipe?.title||"").trim().toLocaleLowerCase()}`;
  }

  _recipeHasTodayIngredients(recipe,rows){
    if(!rows.length)return true;
    const ingredients=(recipe?.ingredients||[]).filter(Boolean);
    return rows.every(target=>{
      const key=String(target.key||target.foodKey||"").trim();const name=String(target.name||target.foodName||"").trim().toLocaleLowerCase();
      return ingredients.some(item=>{const ik=String(item?.foodKey||item?.key||"").trim();const iname=this._ingredientName(item).trim().toLocaleLowerCase();return Boolean((key&&ik===key)||(name&&iname===name));});
    });
  }

  _todayRotationKey(){const user=String(this._hass?.user?.id||"anonymous"),entry=String(this._entryId||"default");return `cook4me.today.rotation.v2.${user}.${entry}`;}
  _pickTodayForCategory(category,pool,settings){
    if(!pool.length)return null;
    const date=new Date().toLocaleDateString("sv-SE"),fingerprint=JSON.stringify({category,diet:settings.diet,languages:[...settings.languages].sort(),ingredients:[...settings.ingredients].sort(),nutritionGoal:settings.nutritionGoal,onlyHome:settings.onlyHome,calorieTarget:settings.calorieTarget,maxMissing:settings.maxMissing});
    let state={date,fingerprint,seen:[]};try{const saved=JSON.parse(localStorage.getItem(this._todayRotationKey())||"null");if(saved?.date===date&&saved?.fingerprint===fingerprint&&Array.isArray(saved.seen))state=saved;}catch(_e){}
    let candidates=pool.filter(row=>!state.seen.includes(this._todayRecipeIdentity(row)));if(!candidates.length){state.seen=[];candidates=[...pool];}
    const chosen=candidates[0];const id=this._todayRecipeIdentity(chosen);if(id)state.seen.push(id);try{localStorage.setItem(this._todayRotationKey(),JSON.stringify(state));}catch(_e){}return chosen;
  }

  async _suggestTodayV34(c){
    const s=this._collectTodayV34(c);if(!s.mealTypes.length){this._message(this._t("needMealType"),true);return;}if(!s.languages.length){this._message(this._t("needLanguage"),true);return;}
    this._todaySettings=s;this._saveTodaySettings();this._todayBusy=true;this._todayResults=[];this._todayMeta=null;this._renderToday(c);
    const ingredientRows=this._todaySelectedIngredientRows(s),ingredientQuery=ingredientRows.slice(0,3).map(row=>String(row.name||row.foodName||"").trim()).filter(Boolean).join(" ");
    const maxLanguages=Math.max(1,Number(this._todayOptions?.maxLanguages||8)),chunks=[];for(let i=0;i<s.languages.length;i+=maxLanguages)chunks.push(s.languages.slice(i,i+maxLanguages));
    const total=s.mealTypes.length*chunks.length,job=this._processStart(this._t("today"),this._t("buildingToday"),{icon:"chef-hat",delay:80});let done=0,candidateCount=0;const chosen=[];
    try{
      for(const category of s.mealTypes){
        if(job.cancelled)break;const pool=[],seen=new Set();
        for(const languages of chunks){
          if(job.cancelled)break;
          this._processUpdate(job,`${this._t(category)} · ${languages.map(x=>x.toUpperCase()).join(", ")}`,done,total);
          const payload={entry_id:this._entryId,languages,diet:s.diet,meal_types:[category],only_home:s.onlyHome,nutrition_goal:s.nutritionGoal,meal_count:8,calorie_tolerance:s.calorieTolerance,prefer_expiring:s.preferExpiring,avoid_recent_days:s.avoidRecentDays,variety:true,query:ingredientQuery,catalog_size:50};
          if(s.calorieTarget!=="")payload.calorie_target=s.calorieTarget;if(s.maxMissing!=="")payload.max_missing=Number(s.maxMissing);
          const result=await this._api("cook4me/v18/today_suggest",payload);candidateCount+=Number(result?.candidateCount||0);
          for(const recipe of result?.items||[]){const id=this._todayRecipeIdentity(recipe);if(id&&!seen.has(id)){seen.add(id);pool.push(recipe);}}
          done++;this._processUpdate(job,`${this._t(category)} · ${done}/${total}`,done,total);
        }
        const filtered=pool.filter(recipe=>this._recipeHasTodayIngredients(recipe,ingredientRows));const picked=this._pickTodayForCategory(category,filtered,s);if(picked){picked.todayMealType=category;chosen.push(picked);}
      }
      for(const recipe of chosen)this._ensureRecipeSelections(recipe);
      if(!job.cancelled&&this._shouldTranslate()&&chosen.some(recipe=>this._translationNeeded(recipe)))await this._translateItems(chosen);
      if(!job.cancelled){this._todayResults=chosen;this._todayMeta={candidateCount,filters:s};this._message("");}
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}finally{this._todayBusy=false;this._processEnd(job);this._renderTab();}
  }

  _ensureInlineStyles(){
    if(this.shadowRoot?.getElementById("cook4meInlineV34"))return;const style=document.createElement("style");style.id="cook4meInlineV34";style.textContent=`
      .rx-group-head{display:flex;align-items:center;justify-content:space-between;gap:10px}.rx-group-head .rx-section-label{margin:0}.rx-bulk{min-height:34px!important;padding:6px 9px!important;font-size:12px!important}.rx-bulk ha-icon{--mdc-icon-size:16px}
      .rx-category-results{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:14px;margin-top:14px}.rx-category-result{min-width:0}.rx-category-result>h3{display:flex;align-items:center;gap:7px;margin:0 0 7px;padding:0 4px;font-size:14px}.rx-category-result>h3 ha-icon{--mdc-icon-size:19px;color:var(--primary-color)}
      article.recipe.rx-inline-expanded{grid-column:1/-1!important;max-width:none!important}.rx-inline-expansion{margin:12px -2px -2px;padding:14px;border-top:1px solid var(--divider-color);background:color-mix(in srgb,var(--secondary-background-color) 55%,transparent);border-radius:0 0 15px 15px;animation:rxInlineOpen .18s ease}.rx-inline-head{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px}.rx-inline-head h3{display:flex;align-items:center;gap:7px;margin:0}.rx-inline-head .muted{font-size:11px}.rx-inline-step{display:grid;grid-template-columns:34px minmax(0,1fr);gap:9px;padding:11px 0;border-bottom:1px solid color-mix(in srgb,var(--divider-color) 65%,transparent)}.rx-inline-step:last-child{border-bottom:0}.rx-inline-step-number{width:30px;height:30px;border-radius:10px;display:grid;place-items:center;background:color-mix(in srgb,var(--primary-color) 14%,var(--card-background-color));color:var(--primary-color);font-weight:850}.rx-inline-step-text{line-height:1.45}.rx-inline-step .step-ingredients{margin-top:7px}@keyframes rxInlineOpen{from{opacity:.2;transform:translateY(-4px)}to{opacity:1;transform:none}}
      @media(max-width:700px){.rx-category-results{grid-template-columns:1fr}.rx-group-head{align-items:flex-start;flex-direction:column}.rx-bulk{align-self:flex-start}}
    `;this.shadowRoot.appendChild(style);
  }

  _renderShell(){super._renderShell();this._ensureInlineStyles();}

  async _inlineDetail(recipe,custom){
    if(custom)return {...recipe};
    const selected=this._ensureRecipeSelections?.(recipe);const variant=selected?.displayVariantId||recipe.selectedDisplayVariantId||recipe.displayVariantId||recipe.searchVariantId||recipe.variantFunctionalId||recipe.recipeFunctionalId;
    let detail={...recipe};const hasSteps=Array.isArray(recipe.steps)&&recipe.steps.some(step=>this._stepText(step));
    if(variant&&!hasSteps)detail=await this._api("cook4me/v7/recipe_detail",{entry_id:this._entryId,variant_id:String(variant),language:String(recipe.selectedLanguage||recipe.sourceLanguage||this._selectedLanguage())});
    detail={...recipe,...detail,servingVariants:recipe.servingVariants,availableServings:recipe.availableServings,languageVariants:recipe.languageVariants,selectedLanguage:recipe.selectedLanguage,selectedServings:recipe.selectedServings,selectedDisplayVariantId:recipe.selectedDisplayVariantId||variant,selectedSendVariantId:recipe.selectedSendVariantId||recipe.sendVariantId,sendVariantId:recipe.selectedSendVariantId||recipe.sendVariantId,sendGroupingFunctionalId:recipe.sendGroupingFunctionalId||detail.sendGroupingFunctionalId,sendRecipeFunctionalId:recipe.sendRecipeFunctionalId||detail.sendRecipeFunctionalId,match:recipe.match,nutrition:recipe.nutrition,todayMealType:recipe.todayMealType};
    await this._translateSingle?.(detail);return detail;
  }

  _inlineStepsHtml(detail){
    const ingredients=(detail?.ingredients||[]).filter(item=>this._ingredientText(item)),steps=(detail?.steps||[]).filter(step=>this._stepText(step));
    return `<div class="rx-inline-expansion"><div class="rx-inline-head"><h3><ha-icon icon="mdi:format-list-numbered"></ha-icon>${this._escape(this._t("steps"))}</h3><span class="muted">${this._escape(this._t("tapCollapse"))}</span></div>${steps.length?steps.map((step,index)=>{const text=this._stepText(step),lower=text.toLocaleLowerCase(),hits=ingredients.filter(item=>{const name=this._ingredientName(item).trim().toLocaleLowerCase();return name.length>=3&&lower.includes(name);}).slice(0,8);return `<div class="rx-inline-step"><span class="rx-inline-step-number">${index+1}</span><div class="rx-inline-step-text">${this._escape(text)}${hits.length?`<div class="step-ingredients">${hits.map(item=>`<button type="button" class="step-ingredient" data-inline-ingredient="${this._escape(this._todayIngredientIdentity(item))}"><ha-icon icon="mdi:food-apple-outline"></ha-icon>${this._escape(this._ingredientName(item))}</button>`).join("")}</div>`:""}</div></div>`;}).join(""):`<div class="muted">—</div>`}</div>`;
  }

  _collapseInline(){if(this._inlineRecipeCard?.isConnected){this._inlineRecipeCard.querySelector(".rx-inline-expansion")?.remove();this._inlineRecipeCard.classList.remove("rx-inline-expanded");}this._inlineRecipeCard=null;this._inlineRecipeKey="";}

  async _toggleInlineRecipe(card,recipe,custom){
    const key=this._todayRecipeIdentity(recipe);if(this._inlineRecipeKey===key&&card.classList.contains("rx-inline-expanded")){this._collapseInline();return;}this._collapseInline();
    const job=this._processStart(this._t("backgroundWork"),this._t("openingRecipe"),{icon:"book-open-page-variant-outline",delay:100});try{const detail=await this._inlineDetail(recipe,custom);if(job.cancelled)return;card.insertAdjacentHTML("beforeend",this._inlineStepsHtml(detail));card.classList.add("rx-inline-expanded");this._inlineRecipeKey=key;this._inlineRecipeCard=card;const ingredients=(detail.ingredients||[]).filter(item=>this._ingredientText(item));card.querySelectorAll("[data-inline-ingredient]").forEach(button=>button.addEventListener("click",event=>{event.stopPropagation();const id=String(button.dataset.inlineIngredient||"");const item=ingredients.find(row=>this._todayIngredientIdentity(row)===id);if(item)void this._showIngredientInfo(item,detail);}));card.scrollIntoView?.({behavior:"smooth",block:"nearest"});}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}finally{this._processEnd(job);}
  }

  _bindCards(container,items,custom=false){
    super._bindCards(container,items,custom);container.querySelectorAll(".recipe").forEach((card,index)=>{const recipe=items[index];if(!recipe)return;card.addEventListener("click",event=>{if(event.target.closest("button,input,select,textarea,a,label"))return;event.preventDefault();event.stopImmediatePropagation();void this._toggleInlineRecipe(card,recipe,custom);},true);});
  }
}

customElements.define("cook4me-recipe-hub-panel-v34",Cook4MeRecipeHubPanelV34);
