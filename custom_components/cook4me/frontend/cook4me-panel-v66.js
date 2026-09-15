import "./cook4me-panel-v65.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v65");
const BATCH=8,BUILD="2026.9.15.8";
const COUNTRY_LANGUAGE={DE:"de",AT:"de",CH:"de",GR:"el",CY:"el",GB:"en",US:"en",AU:"en",IE:"en",CA:"en",FR:"fr",BE:"fr",ES:"es",IT:"it",PT:"pt",BR:"pt",PL:"pl",CZ:"cs",SK:"sk",HU:"hu",RO:"ro",BG:"bg",HR:"hr",SI:"sl",UA:"uk",RU:"ru",TR:"tr",JP:"ja",KR:"ko",CN:"zh",TW:"zh",AE:"ar",SA:"ar"};
const TEXT={
 en:{loadEight:"Load 8 more",expandRecipe:"Expand recipe",collapseRecipe:"Collapse recipe",recipeInfo:"Info",recipeFullscreen:"Open recipe fullscreen",recipeLanguageChoice:"Recipe language",recipeDevice:"Cook4Me device",translateRecipeUi:"Translate to UI language",startCookingView:"Cooking mode",stopCookingView:"Leave cooking mode",previousStep:"Previous step",nextStep:"Next step",instructionsUnavailable:"Instructions are not cached yet. Connect to the internet and retry.",retryInstructions:"Retry loading instructions",translationUnavailable:"Local AI could not provide a complete translation.",filteredResults:"Recipes matching your filters",unknownDiet:"Diet unknown",unknownMeal:"Meal type unknown",noMissingIngredients:"No missing ingredients",deviceSendUnavailable:"This edition cannot be sent to the selected device.",sendQueued:"Recipe queued",recipeSent:"Recipe sent"},
 el:{loadEight:"Φόρτωση άλλων 8",expandRecipe:"Ανάπτυξη συνταγής",collapseRecipe:"Σύμπτυξη συνταγής",recipeInfo:"Πληροφορίες",recipeFullscreen:"Άνοιγμα συνταγής σε πλήρη οθόνη",recipeLanguageChoice:"Γλώσσα συνταγής",recipeDevice:"Συσκευή Cook4Me",translateRecipeUi:"Μετάφραση στη γλώσσα της εφαρμογής",startCookingView:"Λειτουργία μαγειρέματος",stopCookingView:"Έξοδος από τη λειτουργία μαγειρέματος",previousStep:"Προηγούμενο βήμα",nextStep:"Επόμενο βήμα",instructionsUnavailable:"Τα βήματα δεν έχουν αποθηκευτεί ακόμη. Συνδεθείτε στο διαδίκτυο και δοκιμάστε ξανά.",retryInstructions:"Επανάληψη φόρτωσης βημάτων",translationUnavailable:"Το τοπικό AI δεν μπόρεσε να δώσει πλήρη μετάφραση.",filteredResults:"Συνταγές με τα επιλεγμένα φίλτρα",unknownDiet:"Άγνωστη διατροφή",unknownMeal:"Άγνωστος τύπος γεύματος",noMissingIngredients:"Δεν λείπουν υλικά",deviceSendUnavailable:"Αυτή η έκδοση δεν μπορεί να σταλεί στην επιλεγμένη συσκευή.",sendQueued:"Η συνταγή μπήκε στην ουρά",recipeSent:"Η συνταγή στάλθηκε"},
 de:{loadEight:"8 weitere laden",expandRecipe:"Rezept aufklappen",collapseRecipe:"Rezept zuklappen",recipeInfo:"Informationen",recipeFullscreen:"Rezept im Vollbild öffnen",recipeLanguageChoice:"Rezeptsprache",recipeDevice:"Cook4Me-Gerät",translateRecipeUi:"In die Sprache der Oberfläche übersetzen",startCookingView:"Kochmodus",stopCookingView:"Kochmodus beenden",previousStep:"Vorheriger Schritt",nextStep:"Nächster Schritt",instructionsUnavailable:"Die Anleitung ist noch nicht gespeichert. Verbinde dich mit dem Internet und versuche es erneut.",retryInstructions:"Anleitung erneut laden",translationUnavailable:"Die lokale KI konnte keine vollständige Übersetzung liefern.",filteredResults:"Rezepte mit den gewählten Filtern",unknownDiet:"Ernährungsform unbekannt",unknownMeal:"Mahlzeitentyp unbekannt",noMissingIngredients:"Keine fehlenden Zutaten",deviceSendUnavailable:"Diese Fassung kann nicht an das ausgewählte Gerät gesendet werden.",sendQueued:"Rezept vorgemerkt",recipeSent:"Rezept gesendet"},
};

class Cook4MeRecipeHubPanelV66 extends BasePanel{
 _t(key){return TEXT[this._uiIngredientLanguage()]?.[key]||TEXT.en[key]||super._t(key);}
 _recipeKey(recipe){const key=super._recipeKey(recipe);return key==="recipe"?`local:${recipe.id||recipe.title||""}`:key;}
 _v66Key(recipe,slot=""){return `${this._prefKey()}:${this._recipeKey(recipe)||recipe.title||""}:${slot}`;}
 _v66State(recipe,slot=""){
  this._v66States??=new Map();const key=this._v66Key(recipe,slot);
  if(!this._v66States.has(key))this._v66States.set(key,{expanded:false,sections:new Set(),device:this._entryId});
  return this._v66States.get(key);
 }
 _v66PageKey(section){return `${this._prefKey()}:${section}`;}
 _v66Render(section,container,render){
  this._v66Limits??=new Map();this._v66Refs=new Map();
  const key=this._v66PageKey(section),context={section,key,total:0,limit:this._v66Limits.get(key)||BATCH};
  const previous=this._v66Context;this._v66Context=context;
  try{render();}finally{this._v66Context=previous;}
  container.querySelectorAll(".rx-category-result").forEach(node=>{if(!node.querySelector("article.recipe"))node.remove();});
  const remote=section==="official"&&Number(this._searchMeta?.page?.totalElements)>this._results.length;
  container.querySelectorAll("[data-load-more]").forEach(node=>node.remove());
  if(context.total>context.limit||remote){
   const footer=document.createElement("div");footer.className="rx-v66-more";
   footer.innerHTML=`<button class="btn secondary" data-load-more type="button">${this._escape(this._t("loadEight"))}</button>`;
   const grid=container.querySelector(section==="today"?"#todayGrid":section==="week"?".rx-week-grid":section==="mine"?"#mineGrid":"#recipeGrid");
   if(grid)grid.after(footer);else container.appendChild(footer);
   footer.querySelector("button").addEventListener("click",()=>void this._v66More(context));
  }
  this._ensureV66Styles();
  const pending=[];
  if(section!=="official")for(const {recipe,slot} of this._v66Refs.values()){
   const state=this._v66State(recipe,slot?.id||"");
   if(!state.languageInitialized){state.languageInitialized=true;if(this._v66PreferredLanguage(recipe)!==recipe.language)pending.push(recipe);}
  }
  if(pending.length)void this._v66PreferLanguages(pending).then(()=>{if(key===this._v66PageKey(this._tab))this._renderTab();});
 }
 async _v66More(context){
  if(this._v66MoreBusy)return;this._v66MoreBusy=true;
  try{
   if(context.section==="official"&&context.limit>=this._results.length){
    const loaded=await this._v66SearchPage((this._searchMeta?.page?.number||0)+1,true);
    return loaded;
   }
   if(context.key!==this._v66PageKey(context.section))return;
   const rows=context.section==="today"?this._todayResults:context.section==="week"?this._weekState?.slots?.map(slot=>slot.recipe).filter(Boolean):context.section==="book"?[...(this._bookState?.favorites||[]),...(this._bookState?.recipeList||[])]:context.section==="mine"?this._entry()?.recipes:[];
   await this._v66PreferLanguages((rows||[]).slice(context.limit,context.limit+BATCH));
   if(context.key!==this._v66PageKey(context.section))return;
   this._v66Limits.set(context.key,context.limit+BATCH);this._renderTab();
  }finally{this._v66MoreBusy=false;}
 }
 _renderOfficial(c){this._v66Render("official",c,()=>{super._renderOfficial(c);c.querySelector("#recipeLanguage")?.closest(".field")?.remove();});}
 _renderToday(c){this._v66Render("today",c,()=>super._renderToday(c));}
 _renderMineV28(c){this._v66Render("mine",c,()=>super._renderMineV28(c));}
 _renderBook(c){this._v66Render("book",c,()=>super._renderBook(c));}
 _renderAIV49(c){
  this._v66Render("ai",c,()=>{
   super._renderAIV49(c);
   if(this._opened){const grid=document.createElement("div");grid.id="recipeGrid";grid.innerHTML=this._recipeCard(this._opened,!this._isOfficialRecipe(this._opened));c.appendChild(grid);this._bindCards(grid,[]);}
  });
 }
 _renderRecommend(c){this._v66Render("recommend",c,()=>super._renderRecommend(c));}
 _renderWeek(c){
  this._v66Render("week",c,()=>{super._renderWeek(c);this._bindCards(c,[],false);});
 }
 _weekDayHtml(stamp){
  const slots=(this._weekState?.slots||[]).filter(row=>row.date===stamp);
  const label=new Intl.DateTimeFormat(this._hass?.language||"en",{weekday:"long",day:"2-digit",month:"2-digit"}).format(new Date(`${stamp}T12:00:00`));
  const html=slots.map(slot=>{
   const recipe=slot.recipe||this._leftoverById(slot.leftoverId)?.recipe;if(!recipe)return "";
   this._v66Slot=slot;
   let card;try{card=this._recipeCard(recipe,!this._isOfficialRecipe(recipe));}finally{this._v66Slot=null;}
   return card?`<div class="rx-week-slot" data-slot-id="${this._escape(slot.id)}"><h4>${this._escape(this._t(slot.mealType||"dinner"))}</h4>${card}</div>`:"";
  }).join("");
  return html?`<section class="rx-week-day"><h3>${this._escape(label)}</h3>${html}</section>`:"";
 }
 async _search(query){
  this._searchQuery=String(query||"").trim();this._v61SearchRequest=(this._v61SearchRequest||0)+1;
  this._v66Limits??=new Map();this._v66Limits.set(this._v66PageKey("official"),BATCH);
  return this._v66SearchPage(0,false);
 }
 async _v66SearchPage(page,append){
  const entry=this._entryId,user=this._hass?.user?.id,request=this._v61SearchRequest,query=this._searchQuery;
  const filters=structuredClone(this._filters()),signature=JSON.stringify(filters);
  const current=()=>entry===this._entryId&&user===this._hass?.user?.id&&request===this._v61SearchRequest&&signature===JSON.stringify(this._filters());
  const job=this._processStart(this._t("official"),this._t("loading"));
  try{
   if(!filters.languages?.length)throw new Error(this._t("chooseCatalog"));
   const result=await this._api("cook4me/v31/official_search",{entry_id:entry,query,query_language:this._uiIngredientLanguage(),languages:filters.languages,shared_filters:filters,page,size:BATCH});
   if(!current()||job.cancelled)return false;
   const items=await this._v66PreferLanguages(result.items||[]);if(!current())return false;
   this._results=append?[...this._results,...items.filter(row=>!this._results.some(old=>this._recipeKey(old)===this._recipeKey(row)))]:items;
   if(append)this._v66Limits.set(this._v66PageKey("official"),(this._v66Limits.get(this._v66PageKey("official"))||BATCH)+BATCH);
   this._searchMeta=result;this._renderTab();return true;
  }catch(error){if(current())this._v59FailProcess(job,`${this._t("error")}: ${error.message||error}`);return false;}
  finally{this._processEnd(job);}
 }
 _v66PreferredLanguage(recipe){
  const languages=recipe.languageVariants?.map(row=>row.language)||recipe.availableLanguages||[recipe.language];
  return [this._uiIngredientLanguage(),COUNTRY_LANGUAGE[String(this._hass?.config?.country||"").toUpperCase()],"en",...languages].find(code=>languages.includes(code));
 }
 _v66Editions(recipe){
  return recipe.languageVariants?.length?Object.fromEntries(["languageVariants","availableLanguages","publicationCount","regionalPublications","displayFamilyId"].filter(key=>recipe[key]!==undefined).map(key=>[key,recipe[key]])):null;
 }
 _v66RestoreEditions(recipe,editions){
  if(!editions)return;Object.assign(recipe,editions);
  const variants=editions.languageVariants.find(row=>row.language===recipe.language)?.servingVariants;
  if(variants)recipe.servingVariants=variants;
 }
 async _v66PreferLanguages(rows){
  await Promise.all(rows.slice(0,BATCH).map(async recipe=>{
   const language=this._v66PreferredLanguage(recipe);if(!language||language===recipe.language)return;
   const options=recipe.languageVariants?.find(row=>row.language===language)?.servingVariants||[];
   const option=options.find(row=>row.servings===recipe.selectedServings)||options[0];if(!option)return;
   try{
    const detail=await super._api("cook4me/v31/recipe_detail",{entry_id:this._entryId,variant_id:String(option.displayVariantId),language,ui_language:this._uiIngredientLanguage()});
    const editions=this._v66Editions(recipe);Object.assign(recipe,detail);this._v66RestoreEditions(recipe,editions);this._ensureRecipeSelections(recipe);
   }catch(_e){/* Keep the accurately labelled source edition if it cannot load. */}
  }));return rows;
 }
 async _api(type,data={}){
  if(/^cook4me\/v31\/(recipe_detail|recipe_translation)$/.test(type)&&this._process?.id)data={...data,client_operation_id:this._process.id};
  if(/\/recipe_detail$/.test(type))data={...data,ui_language:this._uiIngredientLanguage(),include_instructions:data.include_instructions??true};
  const result=await super._api(type,data);
  if(/\/(today_suggest|week_generate)$/.test(type)){
   const rows=result?.items||result?.slots?.map(slot=>slot.recipe).filter(Boolean)||[];
   await this._v66PreferLanguages(rows);
  }
  if(type.endsWith("/ingredient_info"))this._v66IngredientInfo=result;
  return result;
 }
 async _showIngredientInfo(ingredient,recipe){
  await super._showIngredientInfo(ingredient,recipe);
  const info=this._v66IngredientInfo,overlay=this.shadowRoot.querySelector("[data-ingredient-dialog]");
  if(!info||!overlay)return;
  const section=overlay.querySelector("[data-use]")?.closest("section");if(!section)return;
  const rows=[...(info.savedRecipeUsage||[]).map(row=>row.recipe),...(info.officialRecipeUsage||[])].filter(Boolean);
  this._v66UsageView={section,rows:rows.filter((row,index)=>rows.findIndex(other=>this._recipeKey(other)===this._recipeKey(row))===index),limit:BATCH};
  this._v66RenderUsage();
 }
 _v66RenderUsage(){
  const view=this._v66UsageView;if(!view)return;if(view.section.getRootNode()!==this.shadowRoot){this._v66UsageView=null;return;}
  const previous=this._v66Context;this._v66Context=null;this._v66IgnoreTags=true;
  try{view.section.innerHTML=`<h3>${this._escape(this._t("usedIn"))}</h3><div class="grid">${view.rows.slice(0,view.limit).map(row=>this._recipeCard(row,!this._isOfficialRecipe(row))).join("")}</div>${view.rows.length>view.limit?`<button class="btn secondary" data-usage-more>${this._escape(this._t("loadEight"))}</button>`:""}`;}
  finally{this._v66Context=previous;this._v66IgnoreTags=false;}
  this._bindCards(view.section,[]);
  view.section.querySelector("[data-usage-more]")?.addEventListener("click",()=>{view.limit+=BATCH;this._v66RenderUsage();});
 }
 _v66PassesTag(recipe){
  if(this._v66IgnoreTags)return true;
  const tags=this._v66Tags?.get(this._v66PageKey(this._tab));if(!tags)return true;
  if(tags.signature!==JSON.stringify(this._filters())){this._v66Tags.delete(this._v66PageKey(this._tab));return true;}
  const dietary=recipe.dietary||recipe.match?.dietary||{},meals=recipe.mealTypes||[recipe.todayMealType];
  return (!tags.diet||tags.diet==="omnivore"||dietary[tags.diet]===true)&&(!tags.meal||meals.includes(tags.meal));
 }
 _recipeCard(recipe,custom=false){
  if(!this._v66PassesTag(recipe))return "";
  const context=this._v66Context;if(context&&++context.total>context.limit)return "";
  const slot=this._v66Slot,state=this._v66State(recipe,slot?.id||"");
  const ref=String(this._v66NextRef=(this._v66NextRef||0)+1);
  this._v66Refs??=new Map();this._v66Refs.set(ref,{recipe,custom,slot});
  const language=recipe.translatedTo||recipe.selectedLanguage||recipe.language||"";
  return `<article class="card recipe rx-v66-recipe" data-v66-ref="${ref}" data-recipe="${this._escape(recipe.displayVariantId||recipe.id||"")}">
   <button type="button" class="rx-v66-photo" data-v66-photo aria-label="${this._escape(this._t("recipeFullscreen"))}">${this._mediaHtml(recipe)}</button>
   <div class="rx-v66-title"><h3>${this._escape(recipe.title||recipe.canonicalName||"")} ${language?`<span>(${this._escape(this._languageName(language))})</span>`:""}</h3>${this._v66Icon("expand",state.expanded?"chevron-up":"chevron-down",state.expanded?"collapseRecipe":"expandRecipe",`aria-expanded="${state.expanded}"`)}</div>
   ${state.expanded?`<div class="rx-v66-body">${this._v66Body(recipe,custom,state,slot)}</div>`:""}
  </article>`;
 }
 _v66Icon(action,icon,label,attributes=""){
  return `<button type="button" class="btn secondary rx-v66-icon" data-v66-action="${action}" title="${this._escape(this._t(label))}" aria-label="${this._escape(this._t(label))}" ${attributes}><ha-icon icon="mdi:${icon}" aria-hidden="true"></ha-icon></button>`;
 }
 _v66Body(recipe,custom,state,slot=null){
  const escape=value=>this._escape(String(value??""));
  const disclosure=(key,label,html)=>`<details data-v66-section="${key}" ${state.sections.has(key)?"open":""}><summary>${escape(this._t(label))}</summary><div class="rx-v66-section">${html}</div></details>`;
  const dietary=recipe.dietary||recipe.match?.dietary||{};
  const diets=["vegan","vegetarian","pescatarian"].filter(key=>dietary[key]===true);
  if(!diets.length&&Object.keys(dietary).length)diets.push("omnivore");
  const meals=recipe.mealTypes||[];
  const tag=(kind,key)=>`<button type="button" class="chip" data-v66-tag="${kind}" data-value="${escape(key)}">${escape(this._t(key))}</button>`;
  const info=`<div><strong>${escape(this._t("diet"))}</strong><div class="chips">${diets.map(key=>tag("diet",key)).join("")||escape(this._t("unknownDiet"))}</div></div><div><strong>${escape(this._t("mealTypes"))}</strong><div class="chips">${meals.map(key=>tag("meal",key)).join("")||escape(this._t("unknownMeal"))}</div></div>${this._v60NutritionChips?.(recipe)||""}${recipe.notes?`<p>${escape(recipe.notes)}</p>`:""}`;
  const ingredients=(recipe.ingredients||[]).map((item,index)=>{
   const original=typeof item==="string"?item:item.originalName||item.name||item.foodName||"";
   const display=typeof item==="string"?item:item.displayName||this._v66IngredientName(item)||original;
   const coverage=this._coverage(recipe,item),percent=Number.isFinite(coverage.percent)?`${coverage.percent}%`:"—";
   const quantity=typeof item==="object"?[item.quantity,item.unit].filter(value=>value!==undefined&&value!==null&&value!=="").join(" "):"";
   return `<li><button type="button" data-v66-ingredient="${index}"><span>${escape(display)} <small>(${escape(original)})</small>${quantity?`<small class="rx-v66-quantity">${escape(quantity)}</small>`:""}</span><span class="chip" title="${escape(this._t("coverage"))}">${percent}</span></button></li>`;
  }).join("");
  const languages=recipe.languageVariants?.length?recipe.languageVariants:[{language:recipe.language||this._uiIngredientLanguage()}];
  const selected=recipe.selectedLanguage||recipe.language;
  const languageSelect=`<div class="field"><label>${escape(this._t("recipeLanguageChoice"))}</label><select data-v66-language>${languages.map(row=>`<option value="${escape(row.language)}" ${row.language===selected?"selected":""}>${escape(this._languageName(row.language))}</option>`).join("")}</select></div>`;
  const servings=this._servingOptions(recipe)||[],options=servings.length?servings:[{displayVariantId:recipe.displayVariantId||recipe.id,servings:recipe.servings||this._servings(recipe)}];
  const servingSelect=`<div class="field"><label>${escape(this._t("servings"))}</label><select data-v66-servings>${options.map(option=>`<option value="${escape(option.displayVariantId||option.sendVariantId||"")}" ${String(option.displayVariantId)===String(recipe.displayVariantId)?"selected":""}>${escape(option.label??option.servings??"—")}${option.publicationNumber?` · ${escape(this._t("publicationVersion"))} ${option.publicationNumber}`:""}</option>`).join("")}</select></div>`;
  const steps=(recipe.steps||[]).map((step,index)=>`<li class="step" data-v66-step="${index}"><span class="step-num">${escape(Number.isFinite(Number(step?.stepIndex))?Number(step.stepIndex)+1:index+1)}</span><span>${escape(this._stepText(step))}</span></li>`).join("");
  const instructionBlock=steps?`<ol class="rx-v66-steps">${steps}</ol>`:`<p class="muted">${escape(this._t("instructionsUnavailable"))}</p>${this._v66Icon("retry","refresh","retryInstructions")}`;
  const devices=this._entries||[],deviceSelect=devices.length>1?`<select data-v66-device aria-label="${escape(this._t("recipeDevice"))}">${devices.map(device=>`<option value="${escape(device.entry_id)}" ${device.entry_id===(state.device||this._entryId)?"selected":""}>${escape(device.title||device.entry_id)}</option>`).join("")}</select>`:"";
  const canSend=!custom&&!!(recipe.displayVariantId||recipe.sendVariantId)&&recipe.match?.safe!==false;
  const canTranslate=this._v66LocalAiAvailable()&&!languages.some(row=>row.language===this._uiIngredientLanguage())&&recipe.translatedTo!==this._uiIngredientLanguage();
  const actions=`<div class="rx-v66-actions">${deviceSelect}${this._v66Icon("send","send","send",`data-detail-send ${canSend?"":"disabled"}`)}${this._v66Icon("shopping","cart-plus","addMissing")}${canTranslate?this._v66Icon("translate","translate","translateRecipeUi"):""}${this._v66Icon("favorite",this._isFavorite(recipe)?"heart":"heart-outline","favorites")}${this._v66Icon("list","playlist-plus","recipeList")}${custom?this._v66Icon("delete","delete-outline","delete"):""}${this._v66Icon("cook",state.cooking?"stop-circle-outline":"chef-hat",state.cooking?"stopCookingView":"startCookingView")}</div>`;
  const cooking=state.cooking?`<div class="rx-v66-cooking-controls">${this._v66Icon("previous","skip-previous","previousStep")}${this._v66Icon("next","skip-next","nextStep")}</div>`:"";
  const schedule=slot?`<div class="rx-v66-actions">${this._v66Icon("regenerate","refresh","regenerate")}${this._v66Icon("clear-slot","calendar-remove","clear")}</div>`:"";
  return `${state.error?`<p role="alert">${escape(state.error)}</p>`:""}${disclosure("info","recipeInfo",info)}${disclosure("ingredients","ingredients",`<ul class="rx-v66-ingredients">${ingredients}</ul>`)}<div class="rx-v66-selects">${languageSelect}${servingSelect}</div>${disclosure("steps","steps",instructionBlock+cooking)}${actions}${schedule}`;
 }
 _v66IngredientName(item){
  const id=String(item.ingredientId||item.foodKey||item.key||"");
  return this._ingredientCatalog?.find(row=>(row.sourceIngredientIds||[row.ingredientId,row.key]).some(value=>String(value)===id))?.name||item.canonicalName||item.name;
 }
 _bindCards(container,_items,custom=false){
  if(!container)return;
  container.querySelectorAll("[data-v66-ref]").forEach(card=>{
   if(card._v66Bound)return;card._v66Bound=true;
   const row=this._v66Refs?.get(card.dataset.v66Ref);if(!row)return;
   this._v66BindRecipe(card,row.recipe,row.custom??custom,row.slot);
  });
 }
 _v66BindRecipe(container,recipe,custom,slot=null,fullscreen=false){
  const state=this._v66State(recipe,slot?.id||"");
  container.addEventListener("click",event=>event.stopPropagation());
  container.querySelectorAll("img.cover").forEach(img=>img.addEventListener("error",()=>img.remove()));
  container.querySelector("[data-v66-photo]")?.addEventListener("click",()=>void this._showRecipe(recipe,custom));
  container.querySelectorAll("[data-v66-section]").forEach(details=>details.addEventListener("toggle",()=>{if(details.open)state.sections.add(details.dataset.v66Section);else state.sections.delete(details.dataset.v66Section);}));
  container.querySelectorAll("[data-v66-ingredient]").forEach(button=>button.addEventListener("click",()=>void this._showIngredientInfo(recipe.ingredients[Number(button.dataset.v66Ingredient)],recipe)));
  container.querySelectorAll("[data-v66-tag]").forEach(button=>button.addEventListener("click",()=>void this._v66FilterTag(button.dataset.v66Tag,button.dataset.value)));
  container.querySelector("[data-v66-language]")?.addEventListener("change",event=>void this._selectRecipeLanguage(recipe,event.target.value,fullscreen));
  container.querySelector("[data-v66-servings]")?.addEventListener("change",event=>void this._selectServing(recipe,event.target.value,fullscreen));
  container.querySelector("[data-v66-device]")?.addEventListener("change",event=>{state.device=event.target.value;});
  container.querySelectorAll("[data-v66-action]").forEach(button=>button.addEventListener("click",async()=>{
   const action=button.dataset.v66Action;
   if(action==="expand"){
    state.expanded=!state.expanded;this._renderTab();if(state.expanded)await this._v66LoadRecipe(recipe,custom,state);return;
   }
   if(action==="retry")return this._v66LoadRecipe(recipe,custom,state,true);
   if(action==="send")return this._v66Send(recipe,state.device||this._entryId);
   if(action==="shopping"){
    const missing=this._missingIngredientObjects(recipe);if(missing?.length)return this._addShopping(missing);
    this._message(this._t("noMissingIngredients"));return;
   }
   if(action==="favorite"||action==="list")return this._toggleBook(action==="favorite"?"favorites":"recipeList",recipe);
   if(action==="delete")return this._deleteRecipe(recipe);
   if(action==="translate")return this._v66Translate(recipe,state);
   if(action==="regenerate")return this._generateWeek(slot.id);
   if(action==="clear-slot")return this._weekClear(slot.id);
   if(action==="cook"){state.cooking=!state.cooking;state.step=state.step||0;state.sections.add("steps");}
   if(action==="previous"||action==="next")state.step=Math.max(0,Math.min((recipe.steps?.length||1)-1,(state.step||0)+(action==="next"?1:-1)));
   if(fullscreen)this._renderRecipeDialog();else this._renderTab();
  }));
  this._v66Highlight(container,recipe,state);
 }
 async _v66LoadRecipe(recipe,custom,state,force=false){
  const variant=String(recipe.displayVariantId||recipe.searchVariantId||recipe.id||"");
  if(state.loading||(!force&&state.loaded===variant&&recipe.presentationLanguage===this._uiIngredientLanguage()))return;
  const entry=this._entryId,user=this._hass?.user?.id;state.loading=true;state.error="";
  const job=this._processStart(this._t("openingRecipe"),recipe.title||"");
  try{
   if(!custom&&!state.loaded)await this._v66PreferLanguages([recipe]);
   const selectedVariant=String(recipe.displayVariantId||recipe.searchVariantId||recipe.id||variant);
   const result=custom?await this._api("cook4me/v31/recipe_presentation",{entry_id:entry,recipe,language:this._uiIngredientLanguage()}):await this._api("cook4me/v31/recipe_detail",{entry_id:entry,variant_id:selectedVariant,language:recipe.selectedLanguage||recipe.language,include_instructions:true});
   if(entry!==this._entryId||user!==this._hass?.user?.id||selectedVariant!==String(recipe.displayVariantId||recipe.searchVariantId||recipe.id||""))return;
   const editions=this._v66Editions(recipe);Object.assign(recipe,result);this._v66RestoreEditions(recipe,editions);state.loaded=selectedVariant;this._ensureRecipeSelections(recipe);
  }catch(error){state.error=`${this._t("error")}: ${error.message||error}`;this._v59FailProcess(job,state.error);}
  finally{state.loading=false;this._processEnd(job);if(entry===this._entryId&&user===this._hass?.user?.id)this._renderTab();}
 }
 async _changeRecipeVariant(recipe,option,language,fromDetail){
  const editions=this._v66Editions(recipe);
  await super._changeRecipeVariant(recipe,option,language,fromDetail);this._v66RestoreEditions(recipe,editions);
  if(String(recipe.displayVariantId)===String(option.displayVariantId)){
   delete recipe.translatedTo;delete recipe.translationMethod;
   this._renderTab();
  }
 }
 async _showRecipe(recipe,custom=false){
  const translated=recipe.translatedTo?{title:recipe.title,steps:recipe.steps,translatedTo:recipe.translatedTo,translationMethod:recipe.translationMethod}:null;
  const editions=this._v66Editions(recipe);
  await super._showRecipe(recipe,custom);
  if(this._opened&&this._opened.displayVariantId===recipe.displayVariantId){this._v66RestoreEditions(this._opened,editions);this._renderRecipeDialog();}
  if(translated&&this._opened&&this._opened.displayVariantId===recipe.displayVariantId){Object.assign(this._opened,translated);this._renderRecipeDialog();}
 }
 async _v66FilterTag(kind,value){
  const filters={...this._filters(),...(kind==="diet"?{diet:value}:{mealTypes:[value]})};
  this._v63Filters=filters;this._persistPreferences({filters});
  this._v66Tags??=new Map();const key=this._v66PageKey(this._tab);this._v66Tags.set(key,{...(this._v66Tags.get(key)||{}),[kind]:value,signature:JSON.stringify(filters)});
  this._v66Limits?.set(key,BATCH);this._v63CloseRecipe?.();
  if(this._tab==="official")await this._search(this._searchQuery);else this._renderTab();
 }
 async _v66Send(recipe,target){
  const job=this._processStart(this._t("send"),recipe.title||"");
  try{
   // Resolve send identity against the chosen device, never reuse another
   // device's proof or change the displayed source edition.
   const variant=recipe.displayVariantId||recipe.searchVariantId;
   const original=variant?await this._api("cook4me/v31/recipe_detail",{entry_id:target,variant_id:String(variant),language:recipe.language,include_instructions:false}):recipe;
   if(!original.sendVariantId||original.match?.safe===false)throw new Error(this._t("deviceSendUnavailable"));
   const result=await this._api("cook4me/v22/send_multi",{entry_id:target,entry_ids:[target],recipe:original});
   if(!result?.sentCount&&!result?.queuedCount)throw new Error(result?.results?.[0]?.error||this._t("deviceSendUnavailable"));
   this._message(this._t(result.queuedCount?"sendQueued":"recipeSent"));await this._loadOverview(true);
  }catch(error){this._v59FailProcess(job,`${this._t("error")}: ${error.message||error}`);}finally{this._processEnd(job);}
 }
 async _v66Translate(recipe,state){
  if(!this._v66LocalAiAvailable()||state.translating)return;state.translating=true;
  const entry=this._entryId,user=this._hass?.user?.id,variant=recipe.displayVariantId;
  const job=this._processStart(this._t("translateRecipeUi"),recipe.title||"");
  try{
   const result=await this._api("cook4me/v31/recipe_translation",{entry_id:entry,recipe,target_language:this._uiIngredientLanguage()});
   if(entry!==this._entryId||user!==this._hass?.user?.id||variant!==recipe.displayVariantId)return;
   if(!result?.available)throw new Error(this._t("translationUnavailable"));
   Object.assign(recipe,result.recipe);state.error="";this._renderTab();
  }catch(error){this._v59FailProcess(job,`${this._t("error")}: ${error.message||error}`);}finally{state.translating=false;this._processEnd(job);}
 }
 _renderRecipeDialog(){
  const overlay=this._v63RecipeDialog,recipe=this._opened;if(!overlay||!recipe)return;
  const state=this._v66State(recipe);if(!state.fullscreenVisited){state.sections.add("steps");state.fullscreenVisited=true;}overlay.dataset.v66Fullscreen="";
  overlay.innerHTML=`<div class="rx-dialog rx-v66-fullscreen" role="dialog" aria-modal="true" aria-label="${this._escape(recipe.title||"")}"><header><h2>${this._escape(recipe.title||"")} (${this._escape(this._languageName(recipe.translatedTo||recipe.selectedLanguage||recipe.language))})</h2><button class="btn secondary" data-modal-close aria-label="${this._escape(this._t("closeDialog"))}">✕</button></header><section id="recipeDetail"><div class="rx-v66-full-photo">${this._mediaHtml(recipe)}</div><div class="rx-v66-body">${this._v66Body(recipe,!this._isOfficialRecipe(recipe),state)}</div></section></div>`;
  overlay.querySelector("[data-modal-close]").addEventListener("click",()=>this._v63CloseRecipe?.());
  this._v66BindRecipe(overlay,recipe,!this._isOfficialRecipe(recipe),null,true);this._ensureV66Styles();
 }
 _v66ActiveStep(recipe,state){
  const ids=new Set([recipe.displayVariantId,recipe.sendVariantId,recipe.selectedSendVariantId].filter(Boolean).map(String));
  const device=this._entries?.find(entry=>ids.has(String(entry.state?.variantFunctionalId||"")));
  if(device){
   const live=device.state||{},steps=recipe.steps||[];
   const id=String(live.stepFunctionalId||"");
   let index=id?steps.findIndex(step=>String(step?.functionalId||step?.stepFunctionalId||"")===id):-1;
   if(index<0&&live.stepIndex!==undefined)index=steps.findIndex((step,pos)=>Number(step?.stepIndex??pos)===Number(live.stepIndex));
   if(index>=0)return index;
  }
  return state.cooking?state.step||0:-1;
 }
 _v66Highlight(container,recipe,state){
  const current=this._v66ActiveStep(recipe,state);
  container.querySelectorAll("[data-v66-step]").forEach(node=>{
   const active=Number(node.dataset.v66Step)===current;node.classList.toggle("rx-v66-current-step",active);
   if(active)node.setAttribute("aria-current","step");else node.removeAttribute("aria-current");
  });
 }
 _v66LocalAiAvailable(){
  const caps=this._capabilities||{},ids=caps.localAiTaskEntityIds||[caps.localAiTaskEntityId].filter(Boolean);
  return ids.some(id=>{const state=this._hass?.states?.[id];return state&&!['unknown','unavailable'].includes(state.state);});
 }
 _updateHeader(){
  super._updateHeader();
  const available=this._v66LocalAiAvailable();
  if(this._v66AiWasAvailable!==available){this._v66AiWasAvailable=available;this._renderTab();}
  if(this._v63RecipeDialog&&this._opened)this._v66Highlight(this._v63RecipeDialog,this._opened,this._v66State(this._opened));
  this.shadowRoot?.querySelectorAll("[data-v66-ref]").forEach(node=>{const row=this._v66Refs?.get(node.dataset.v66Ref);if(row)this._v66Highlight(node,row.recipe,this._v66State(row.recipe,row.slot?.id||""));});
 }
 _renderTab(){this._v66AiWasAvailable=this._v66LocalAiAvailable();const result=super._renderTab();this._v66RenderUsage();this.setAttribute("data-cook4me-build",BUILD);this._ensureV66Styles();return result;}
 _ensureV66Styles(){
  if(!this.shadowRoot||this.shadowRoot.getElementById("cook4meV66Styles"))return;
  const style=document.createElement("style");style.id="cook4meV66Styles";style.textContent=`
   .rx-v66-recipe{padding:0!important;overflow:hidden;align-self:start}.rx-v66-photo{display:block;width:100%;padding:0;border:0;background:transparent;color:inherit;cursor:pointer}.rx-v66-photo .media{margin:0!important;border-radius:0!important}.rx-v66-photo .media-buttons,.rx-v66-photo .media-actions{display:none!important}.rx-v66-photo img.cover{width:100%;height:220px;object-fit:cover}.rx-v66-title{display:flex;align-items:center;gap:10px;padding:12px 14px}.rx-v66-title h3{margin:0;flex:1;min-width:0;overflow-wrap:anywhere}.rx-v66-title h3 span{font-size:.82em;font-weight:400}.rx-v66-icon{width:44px;min-width:44px!important;height:44px;padding:9px!important;flex-shrink:0}.rx-v66-icon ha-icon{--mdc-icon-size:22px;display:block}.rx-v66-body{padding:0 14px 14px}.rx-v66-body details{border-top:1px solid var(--divider-color);padding:10px 0}.rx-v66-body summary{cursor:pointer;font-weight:600;min-height:32px;display:list-item}.rx-v66-section{padding:10px 0;overflow-wrap:anywhere}.rx-v66-selects{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 0}.rx-v66-selects .field{min-width:0}.rx-v66-selects select{width:100%;min-height:44px}.rx-v66-ingredients{list-style:none;padding:0;margin:0}.rx-v66-ingredients li{padding:5px 0}.rx-v66-ingredients button{width:100%;display:flex;align-items:center;justify-content:space-between;gap:10px;text-align:left;background:transparent;border:1px solid var(--divider-color);border-radius:10px;padding:10px;color:inherit;cursor:pointer}.rx-v66-ingredients small{opacity:.7}.rx-v66-quantity{display:block;margin-top:3px}.rx-v66-actions,.rx-v66-cooking-controls{display:flex;flex-wrap:wrap;gap:7px;margin-top:12px}.rx-v66-actions select{min-width:0;max-width:100%;flex:1;min-height:44px}.rx-v66-steps{list-style:none;padding:0;margin:0}.rx-v66-steps .step{padding:12px;border-radius:10px;white-space:pre-line}.rx-v66-current-step{background:color-mix(in srgb,var(--primary-color) 20%,transparent);outline:2px solid var(--primary-color)}.rx-v66-more{display:flex;justify-content:center;margin:20px 0}.rx-week-slot:has(.rx-v66-recipe){display:block!important}.rx-week-grid{align-items:start}.rx-category-results{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:14px;align-items:start}
   [data-v66-fullscreen]{position:fixed!important;inset:0!important;padding:0!important;z-index:10040!important;background:var(--primary-background-color)!important}.rx-v66-fullscreen.rx-dialog{width:100vw!important;max-width:none!important;height:100dvh!important;max-height:100dvh!important;margin:0!important;padding:0!important;border-radius:0!important;overflow:auto!important;box-sizing:border-box}.rx-v66-fullscreen header{position:sticky;top:0;display:flex;align-items:center;justify-content:space-between;gap:12px;background:var(--card-background-color);padding:12px 20px;z-index:2}.rx-v66-fullscreen header h2{font-size:1.3rem;margin:0}.rx-v66-fullscreen #recipeDetail{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:24px;max-width:1400px;margin:auto!important;padding:20px}.rx-v66-full-photo .media{margin:0!important;border-radius:16px}.rx-v66-full-photo img{width:100%;height:auto;max-height:65dvh;object-fit:contain}.rx-v66-fullscreen .rx-v66-body{padding:0}.rx-v66-fullscreen [data-modal-close]{float:none!important;position:static!important}@media(max-width:700px){.rx-v66-fullscreen #recipeDetail{grid-template-columns:1fr;padding:12px;gap:12px}.rx-v66-full-photo img{max-height:36dvh}.rx-v66-title h3{font-size:1.08rem}.rx-v66-selects{grid-template-columns:1fr 1fr}}
  `;this.shadowRoot.appendChild(style);
 }
}

customElements.define("cook4me-recipe-hub-panel-v66",Cook4MeRecipeHubPanelV66);
