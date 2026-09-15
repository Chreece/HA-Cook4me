import "./cook4me-panel-v61.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v61");
const BUILD="2026.9.15.4";

class Cook4MeRecipeHubPanelV62 extends BasePanel{
  _t(key){
    const text={en:{referenceTypes:"Other ingredient types — reference values",referenceHelp:"This ingredient has no reviewed nutrient profile. These values belong to the specific types below and are not used as this ingredient’s nutrients."},de:{referenceTypes:"Andere Zutatenarten – Referenzwerte",referenceHelp:"Für diese Zutat liegt kein geprüftes Nährwertprofil vor. Diese Werte gelten für die unten genannten Arten und werden dieser Zutat nicht zugeordnet."},el:{referenceTypes:"Άλλα είδη υλικού — τιμές αναφοράς",referenceHelp:"Αυτό το υλικό δεν έχει ελεγμένο διατροφικό προφίλ. Οι τιμές αφορούν τα συγκεκριμένα είδη παρακάτω και δεν αποδίδονται σε αυτό το υλικό."}};
    return text[this._uiIngredientLanguage()]?.[key]||text.en[key]||super._t(key);
  }
  _uiIngredientLanguage(){return String(this._hass?.language||this._langCode()||"en").toLowerCase().replaceAll("_","-").split("-")[0];}
  _recipeKey(recipe){return recipe?.displayFamilyId||super._recipeKey(recipe);}
  _todayRecipeIdentity(recipe){return recipe?.displayFamilyId||super._todayRecipeIdentity(recipe);}

  async _api(type,data={}){
    if(/^cook4me\/v\d+\/recipe_detail$/.test(type))type="cook4me/v31/recipe_detail";
    if(/^cook4me\/v\d+\/ingredient_catalog$/.test(type))type="cook4me/v31/ingredient_catalog";
    if(type==="cook4me/v31/ingredient_catalog"||type==="cook4me/v31/ingredient_info"){
      if(!this._hass)throw new Error("Home Assistant unavailable");
      return this._hass.connection.sendMessagePromise({...data,type});
    }
    return super._api(type,data);
  }

  _discardOldCatalog(){
    const language=this._uiIngredientLanguage();
    if((this._ingredientCatalog||[]).some(row=>row.presentationVersion!==62||row.displayLanguage!==language))this._ingredientCatalog=[];
    this._ingredientCatalogLanguage=language;
  }
  _applyEntrySnapshot(entry){super._applyEntrySnapshot(entry);this._discardOldCatalog();}
  _applyServerSeed(result){const value=super._applyServerSeed(result);this._discardOldCatalog();return value;}
  _resourceHasData(resource){return resource==="catalog"?Boolean(this._ingredientCatalog?.length&&this._ingredientCatalog.every(row=>row.presentationVersion===62&&row.displayLanguage===this._uiIngredientLanguage())):super._resourceHasData(resource);}
  _catalogLanguageOptions(){const language=this._uiIngredientLanguage();return `<option value="${this._escape(language)}" selected>${this._escape(this._languageName(language))}</option>`;}

  _renderHouseChoices(container){
    const query=this._houseFilter,catalog=this._ingredientCatalog;
    const fold=value=>String(value||"").normalize("NFD").replace(/\p{M}/gu,"").toLowerCase();
    this._ingredientCatalog=(catalog||[]).filter(row=>fold(`${row.name} ${row.canonicalName||""}`).includes(fold(query)));
    this._houseFilter="";
    try{return super._renderHouseChoices(container);}finally{this._ingredientCatalog=catalog;this._houseFilter=query;}
  }

  async _loadIngredientCatalog(_language=null,refresh=false){
    if(!this._entryId||this._ingredientCatalogLoading)return;
    const entry=this._entryId,language=this._uiIngredientLanguage();
    const requestKey=`${entry}:${language}`;
    if(!refresh&&this._v62CatalogFailureKey===requestKey)return;
    this._ingredientCatalogLoading=true;
    try{
      const result=await this._api("cook4me/v31/ingredient_catalog",{entry_id:entry,language,refresh:Boolean(refresh)});
      if(entry!==this._entryId||language!==this._uiIngredientLanguage())return;
      if(result.presentationVersion!==62)throw new Error("Cook4Me catalog update is not active; restart Home Assistant and reload this page.");
      this._ingredientCatalog=(result.items||[]).sort((a,b)=>String(a.name).localeCompare(String(b.name),language));
      this._ingredientCatalogLanguage=language;
      this._v62CatalogFailureKey=null;
    }catch(error){this._v62CatalogFailureKey=requestKey;this._message(`${this._t("error")}: ${error.message||error}`,true);}
    finally{this._ingredientCatalogLoading=false;}
    if(entry===this._entryId)this._renderTab();
  }

  _renderTab(){
    this._discardOldCatalog();
    const result=super._renderTab();
    this.setAttribute("data-cook4me-build",BUILD);
    for(const id of ["ingredientLanguage","manualIngredientLanguage","recommendIngredientLanguage"]){
      const select=this.shadowRoot?.getElementById(id);
      select?.closest(".field")?.remove();
    }
    return result;
  }

  async _showIngredientInfo(ingredient,recipe){
    let source=ingredient;
    if(!source||typeof source!=="object"){
      const displayed=recipe?.ingredients,originals=recipe?._nutritionIngredients;
      const index=Array.isArray(displayed)?displayed.indexOf(ingredient):-1;
      source=index>=0&&index===displayed.lastIndexOf(ingredient)&&Array.isArray(originals)&&originals.length===displayed.length&&originals[index]&&typeof originals[index]==="object"?originals[index]:{name:String(ingredient||"")};
    }
    const entry=this._entryId;
    const operation=this._processStart(this._t("ingredientInfo"),this._t("loadingIngredient"));
    let info;
    try{
      info=await this._api("cook4me/v31/ingredient_info",{entry_id:entry,ingredient:source,language:this._uiIngredientLanguage(),include_official_usage:true});
      if(info?.ingredientInfoContract!=="offline-ingredient-info-v62")throw new Error("Cook4Me ingredient update is not active; restart Home Assistant and reload this page.");
    }catch(error){this._message(`${this._t("error")}: ${error.message||error}`,true);return;}
    finally{this._processEnd(operation);}
    if(entry!==this._entryId)return;
    this._v62CloseIngredient?.();
    const overlay=document.createElement("div");overlay.className="rx-overlay";overlay.setAttribute("data-ingredient-dialog",BUILD);
    const stock=info.stock||{},quantity=stock.unlimited?"∞":stock.quantity!==undefined?`${this._shownNumber(stock.quantity)} ${stock.unit||""}`:"—";
    const history=(info.history||[]).slice(0,8).map(row=>`<div class="rx-list-row"><strong>${this._escape(row.title||"")}</strong><div class="muted">${this._escape(String(row.timestamp||"").slice(0,16).replace("T"," "))}</div></div>`).join("");
    const lots=(stock.lots||[]).map(row=>`<div class="rx-list-row">${this._escape(`${this._shownNumber(row.quantity)} ${stock.unit||""}`)}${row.productName?` · ${this._escape(row.productName)}`:""}${row.bestBefore?` · ${this._escape(this._t("bestBefore"))}: ${this._escape(row.bestBefore)}`:""}</div>`).join("");
    const uses=[...(info.savedRecipeUsage||[]).map(row=>({...row,kind:"saved"})),...(info.officialRecipeUsage||[]).map(recipe=>({title:recipe.title,recipe,kind:"official"}))];
    overlay.innerHTML=`<div class="rx-dialog" role="dialog" aria-modal="true" aria-label="${this._escape(this._t("ingredientInfo"))}">
      <div class="detail-head"><h2>🥕 ${this._escape(info.ingredient?.name||this._ingredientName(source))}</h2><button class="btn secondary" data-close aria-label="${this._escape(this._t("closeDialog"))}">✕</button></div>
      <div class="chips"><span class="chip">📦 ${this._escape(this._t("stockCoverage"))}: ${this._escape(quantity)}</span></div>
      <div class="toolbar" style="margin:12px 0"><button class="btn" data-shop>🛒 ${this._escape(this._t("addOne"))}</button></div>
      <section data-nutrition><h3>${this._escape(this._t("nutrition"))}</h3>${this._ingredientNutritionHtml(info)}</section>
      <section><h3>${this._escape(this._t("history"))}</h3>${history||"—"}</section>
      <section><h3>${this._escape(this._t("stockCoverage"))}</h3>${lots||"—"}</section>
      <section><h3>${this._escape(this._t("usedIn"))}</h3>${uses.length?uses.slice(0,16).map((row,index)=>`<button class="btn secondary" data-use="${index}" style="margin:3px">${this._escape(row.title||row.recipe?.title||"")}</button>`).join(""):"—"}</section>
    </div>`;
    const close=()=>{document.removeEventListener("keydown",escape);overlay.remove();this._v62CloseIngredient=null;};
    this._v62CloseIngredient=close;
    const escape=event=>{if(event.key==="Escape")close();};
    document.addEventListener("keydown",escape);
    overlay.querySelector("[data-close]").addEventListener("click",close);
    overlay.addEventListener("click",event=>{if(event.target===overlay)close();});
    overlay.querySelector("[data-shop]").addEventListener("click",()=>void this._addShopping([source]));
    overlay.querySelectorAll("[data-use]").forEach(button=>button.addEventListener("click",()=>{const row=uses[Number(button.dataset.use)];close();if(row?.recipe)row.kind==="official"?void this._openOfficial(row.recipe):this._openLocal(row.recipe);}));
    this.shadowRoot.appendChild(overlay);overlay.querySelector("[data-close]").focus();
  }

  _ingredientNutritionHtml(info){
    const main=super._ingredientNutritionHtml(info);
    if(info.catalogNutrition||!(info.nutritionReferences||[]).length)return main;
    const references=info.nutritionReferences.filter(row=>row.referenceOnly).map(row=>`<div data-reference-only style="margin:12px 0"><h4>${this._escape(row.name)}</h4>${super._ingredientNutritionHtml({genericNutrition:{nutrition:row.nutrition}})}</div>`).join("");
    return `${main}<h4>${this._escape(this._t("referenceTypes"))}</h4><p class="muted">${this._escape(this._t("referenceHelp"))}</p>${references}`;
  }
  disconnectedCallback(){this._v62CloseIngredient?.();super.disconnectedCallback();}
}

customElements.define("cook4me-recipe-hub-panel-v62",Cook4MeRecipeHubPanelV62);
