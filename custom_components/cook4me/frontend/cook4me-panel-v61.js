import "./cook4me-panel-v60.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v60");
const TEXT={
  en:{chooseCatalog:"Select at least one catalog language.",closeCatalog:"Done",partialNutrition:"Partial estimate",estimatedNutrition:"Estimated",offlineCatalogHelp:"Search the local Cook4Me catalog by dish or ingredients. Source catalog languages are independent of your query language."},
  de:{chooseCatalog:"Wähle mindestens eine Katalogsprache aus.",closeCatalog:"Fertig",partialNutrition:"Teilweise Schätzung",estimatedNutrition:"Geschätzt",offlineCatalogHelp:"Durchsuche den lokalen Cook4Me-Katalog nach Gerichten oder Zutaten. Die Quellkatalogsprachen sind unabhängig von deiner Suchsprache."},
  el:{chooseCatalog:"Επίλεξε τουλάχιστον μία γλώσσα καταλόγου.",closeCatalog:"Τέλος",partialNutrition:"Μερική εκτίμηση",estimatedNutrition:"Εκτίμηση",offlineCatalogHelp:"Αναζήτησε πιάτα ή υλικά στον τοπικό κατάλογο Cook4Me. Οι γλώσσες των καταλόγων είναι ανεξάρτητες από τη γλώσσα αναζήτησης."},
};
const SOURCE_LANGUAGES="ar bg cs de en es fr hr hu it ja ko pl pt ro ru sk sl tr uk zh".split(" ");
const code=value=>String(value||"").toLowerCase().replaceAll("_","-").split("-")[0];
const number=value=>value!==null&&value!==undefined&&value!==""&&typeof value!=="boolean"&&Number.isFinite(Number(value))?Number(value):null;

class Cook4MeRecipeHubPanelV61 extends BasePanel{
  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  connectedCallback(){
    if(super.connectedCallback)super.connectedCallback();
    // The inherited disconnect hook removes these. Restore them on reattachment.
    document.addEventListener("pointerdown",this._v60OutsidePointer,true);
    document.addEventListener("keydown",this._v60Escape,true);
  }

  _languageRows(){
    const catalog=this._searchMeta?.releaseCatalog?.catalogLanguages;
    if(Array.isArray(catalog)&&catalog.length)return catalog.map(value=>({code:code(value)}));
    const available=super._languageRows();
    return available.length?available:SOURCE_LANGUAGES.map(code=>({code}));
  }

  _loadOfficialLanguages(){
    const key=this._userKey("officialCatalogLanguages");
    const valid=[...new Set(this._languageRows().map(row=>code(row.code)))];
    if(this._v61LanguageKey!==key){
      this._v61LanguageKey=key;
      try{this._v61SavedLanguages=JSON.parse(localStorage.getItem(key)||"null");}catch(_e){this._v61SavedLanguages=null;}
    }
    const saved=this._v61SavedLanguages;
    if(!valid.length)return [];
    if(Array.isArray(saved)){
      const selected=[...new Set(saved.map(code).filter(value=>valid.includes(value)))];
      // Empty is an explicit deselection; stale unsupported languages are not.
      if(selected.length||!saved.length)return this._officialLanguages=selected;
    }
    return this._officialLanguages=valid;
  }

  _saveOfficialLanguages(values){
    this._v61LanguageKey=this._userKey("officialCatalogLanguages");
    this._v61SavedLanguages=[...new Set(values.map(code).filter(Boolean))];
    this._officialLanguages=this._v61SavedLanguages;
    try{localStorage.setItem(this._v61LanguageKey,JSON.stringify(this._officialLanguages));}catch(_e){}
  }

  _officialLanguagesHtml(){
    return `${super._officialLanguagesHtml()}<button type="button" class="btn secondary rx-v61-picker-close" data-close-catalog>${this._escape(this._t("closeCatalog"))}</button>`;
  }

  _bindOfficialLanguages(container){
    super._bindOfficialLanguages(container);
    const picker=container.querySelector("#officialCatalogLanguages");
    picker?.querySelector("[data-close-catalog]")?.addEventListener("click",()=>{
      picker.removeAttribute("open");picker.querySelector("summary")?.focus();
    });
    picker?.querySelectorAll("[data-official-language]").forEach(input=>input.addEventListener("change",()=>{
      const rows=[...picker.querySelectorAll("[data-official-language]")];
      const button=picker.querySelector("[data-official-languages-bulk]");
      if(button)button.textContent=this._t(rows.every(row=>row.checked)?"deselectAll":"selectAll");
    }));
  }

  _ensureV60Styles(){
    super._ensureV60Styles();
    if(this.shadowRoot?.getElementById("cook4meV61Styles"))return;
    const style=document.createElement("style");style.id="cook4meV61Styles";
    style.textContent=`
      .rx-v61-picker-close{position:sticky;bottom:0;display:block;margin:12px 0 0 auto;min-height:44px}
      @media(max-width:700px){
        #officialCatalogLanguages{display:block;flex:1 1 auto;max-width:100%}
        #officialCatalogLanguages>summary{white-space:normal}
        #officialCatalogLanguages .rx-v49-picker-body{box-sizing:border-box}
      }
    `;this.shadowRoot?.appendChild(style);
  }

  async _api(type,data={}){
    const mapped=this._v59MapApi(type);
    // These reads use immutable local data and must not wait behind AI/cloud work.
    if(mapped==="cook4me/v31/official_search"||(mapped==="cook4me/v31/recipe_detail"&&!data.refresh)){
      if(!this._hass)throw new Error("Home Assistant unavailable");
      return this._hass.connection.sendMessagePromise({...data,type:mapped});
    }
    return super._api(type,data);
  }

  async _search(query){
    const request=(this._v61SearchRequest||0)+1;this._v61SearchRequest=request;
    const entry=this._entryId;
    this._searchQuery=String(query||"").trim();this._opened=null;
    const languages=this._loadOfficialLanguages();
    if(this._languageRows().length&&!languages.length){this._results=[];this._searchMeta=null;this._renderTab();this._message(this._t("chooseCatalog"),true);return;}
    try{
      this._message(this._t("loading"));
      const result=await this._api("cook4me/v31/official_search",{
        entry_id:entry,query:this._searchQuery,query_language:this._hass?.language||this._langCode(),languages,page:0,size:20,
      });
      if(request!==this._v61SearchRequest||entry!==this._entryId)return;
      const items=result?.items||[];items.forEach(recipe=>this._ensureRecipeSelections?.(recipe));
      this._results=items;this._searchMeta=result;this._message("");this._renderTab();
      if(this._shouldTranslate?.()&&items.some(recipe=>this._translationNeeded?.(recipe))){
        // Show usable offline results now; optional translation can finish later.
        void this._translateItems(items).then(()=>{
          if(request===this._v61SearchRequest&&entry===this._entryId&&this._results===items&&this._tab==="official")this._renderTab();
        }).catch(()=>{});
      }
    }catch(error){if(request===this._v61SearchRequest&&entry===this._entryId)this._message(`${this._t("error")}: ${error.message||error}`,true);}
  }

  _v60Nutrition(recipe){
    for(const nutrition of [recipe?.catalogNutrition,recipe?.nutrition]){
      if(!nutrition||typeof nutrition!=="object"||nutrition.available===false)continue;
      const candidates=[nutrition.perServing,nutrition.values,nutrition.totals];
      const values=candidates.find(row=>row&&typeof row==="object"&&Object.values(row).some(value=>number(value)!==null));
      if(!values)continue;
      const pick=(...keys)=>{for(const key of keys){const value=number(values[key]);if(value!==null)return value;}return null;};
      const rawCoverage=typeof nutrition.coverage==="object"?number(nutrition.coverage?.coveragePercent):number(nutrition.coverage);
      const coverage=rawCoverage===null?null:Math.max(0,Math.min(100,typeof nutrition.coverage==="object"?rawCoverage:rawCoverage*100));
      return {nutrition,values,perServing:values===nutrition.perServing,coverage,
        energy:pick("energyKcal","calories"),protein:pick("proteinG","protein"),carbs:pick("carbohydrateG","carbohydrates","carbs"),fat:pick("fatG","fat"),fiber:pick("fiberG","fiber"),
      };
    }
    return null;
  }

  _v60NutritionChips(recipe){
    const data=this._v60Nutrition(recipe);if(!data)return "";
    const basis=this._t(data.perServing?"perServing":"recipeTotal");
    const estimate=data.coverage!==null&&data.coverage<100?this._t("partialNutrition"):data.nutrition.estimated?this._t("estimatedNutrition"):"";
    return `${super._v60NutritionChips(recipe)}<span class="chip rx-v59-nutrition-meta" data-v60-nutrition>${this._escape([basis,estimate].filter(Boolean).join(" · "))}</span>`;
  }

  _recipeCard(recipe,custom=false){
    // Older panel layers also add nutrition chips. Render one consistent set.
    const html=super._recipeCard({...recipe,nutrition:null,catalogNutrition:null},custom);
    return html.replace('<div class="chips">',`<div class="chips">${this._v60NutritionChips(recipe)}`);
  }

  _v60NutritionBlock(recipe){
    const data=this._v60Nutrition(recipe);
    const html=super._v60NutritionBlock(recipe);
    if(!html||!data)return html;
    const estimate=data.coverage!==null&&data.coverage<100?this._t("partialNutrition"):data.nutrition.estimated?this._t("estimatedNutrition"):"";
    return estimate?html.replace('<div class="muted">',`<div class="muted">${this._escape(estimate)} · `):html;
  }

  disconnectedCallback(){this._v61SearchRequest=(this._v61SearchRequest||0)+1;super.disconnectedCallback();}
}

customElements.define("cook4me-recipe-hub-panel-v61",Cook4MeRecipeHubPanelV61);
