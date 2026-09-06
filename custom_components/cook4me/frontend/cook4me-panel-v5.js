import "./cook4me-panel-v3.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v3");

const EXTRA = {
  en: {
    recipeLanguage:"Recipe language",
    automaticLanguage:"Automatic (Home Assistant language)",
    translateToHA:"Translate results to Home Assistant language",
    aiTaskReady:"Default AI Task available",
    aiTaskMissing:"No default AI Task — original recipe text will be shown",
    translated:"AI Task translation · source",
    translating:"Translating…",
  },
  de: {
    recipeLanguage:"Rezeptsprache",
    automaticLanguage:"Automatisch (Home-Assistant-Sprache)",
    translateToHA:"Ergebnisse in die Home-Assistant-Sprache übersetzen",
    aiTaskReady:"Standard-AI-Task verfügbar",
    aiTaskMissing:"Kein Standard-AI-Task — Rezepttext bleibt im Original",
    translated:"AI-Task-Übersetzung · Quelle",
    translating:"Übersetze…",
  },
  el: {
    recipeLanguage:"Γλώσσα συνταγών",
    automaticLanguage:"Αυτόματο (γλώσσα Home Assistant)",
    translateToHA:"Μετάφραση αποτελεσμάτων στη γλώσσα του Home Assistant",
    aiTaskReady:"Υπάρχει προεπιλεγμένο AI Task",
    aiTaskMissing:"Δεν υπάρχει προεπιλεγμένο AI Task — οι συνταγές μένουν στην αρχική τους γλώσσα",
    translated:"Μετάφραση AI Task · πηγή",
    translating:"Μετάφραση…",
  },
};

class Cook4MeRecipeHubPanelV5 extends BasePanel {
  constructor(){
    super();
    this._capabilities={languages:[],defaultAiTaskAvailable:false,defaultAiTaskEntityId:null};
    this._catalogLanguage="auto";
    this._translateEnabled=false;
    this._translationPreferenceInitialized=false;
  }

  _t(key){return EXTRA[this._langCode()]?.[key]||EXTRA.en[key]||super._t(key);}

  connectedCallback(){
    super.connectedCallback();
    void this._loadCapabilities();
  }

  async _loadCapabilities(){
    try{
      const capabilities=await this._api("cook4me/v5/capabilities");
      this._capabilities=capabilities||this._capabilities;
      if(!this._translationPreferenceInitialized){
        this._translateEnabled=Boolean(this._capabilities.defaultAiTaskAvailable);
        this._translationPreferenceInitialized=true;
      }
      this._renderTab();
    }catch(_e){
      this._capabilities={languages:[],defaultAiTaskAvailable:false,defaultAiTaskEntityId:null};
      this._translateEnabled=false;
      this._translationPreferenceInitialized=true;
    }
  }

  _selectedLanguage(){return this._catalogLanguage==="auto"?this._langCode():this._catalogLanguage;}
  _strictLanguage(){return this._catalogLanguage!=="auto";}
  _canTranslate(){return Boolean(this._capabilities?.defaultAiTaskAvailable);}
  _shouldTranslate(){return this._canTranslate()&&this._translateEnabled;}

  _languageName(code){
    try{return new Intl.DisplayNames([this._langCode()],{type:"language"}).of(code)||code.toUpperCase();}
    catch(_e){return code.toUpperCase();}
  }

  _localeControlsHtml(){
    const options=(this._capabilities?.languages||[]).map(item=>{
      const code=String(item?.code||"").toLowerCase();
      if(!code)return"";
      return `<option value="${this._escape(code)}" ${this._catalogLanguage===code?"selected":""}>${this._escape(this._languageName(code))} (${this._escape(code.toUpperCase())})</option>`;
    }).join("");
    const available=this._canTranslate();
    return `<div class="toolbar locale-toolbar" style="margin-bottom:12px;align-items:end">
      <div class="field" style="min-width:250px">
        <label>${this._escape(this._t("recipeLanguage"))}</label>
        <select id="recipeLanguage"><option value="auto" ${this._catalogLanguage==="auto"?"selected":""}>${this._escape(this._t("automaticLanguage"))}</option>${options}</select>
      </div>
      <label class="chip" style="min-height:42px;display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:${available?"pointer":"default"}">
        <input id="translateResults" type="checkbox" ${this._translateEnabled&&available?"checked":""} ${available?"":"disabled"}>
        <span>${this._escape(this._t("translateToHA"))}</span>
      </label>
      <span class="muted">${this._escape(available?this._t("aiTaskReady"):this._t("aiTaskMissing"))}</span>
    </div>`;
  }

  _bindLocaleControls(container){
    container.querySelector("#recipeLanguage")?.addEventListener("change",event=>{
      this._catalogLanguage=String(event.target.value||"auto");
      this._opened=null;
      if(this._tab==="official"&&this._searchQuery)void this._search(this._searchQuery);
      else if(this._tab==="recommend"&&this._recommendations.length)void this._recommend();
      else this._renderTab();
    });
    container.querySelector("#translateResults")?.addEventListener("change",event=>{
      this._translateEnabled=Boolean(event.target.checked)&&this._canTranslate();
      this._opened=null;
      if(this._tab==="official"&&this._searchQuery)void this._search(this._searchQuery);
      else if(this._tab==="recommend"&&this._recommendations.length)void this._recommend();
      else this._renderTab();
    });
  }

  _renderOfficial(container){
    super._renderOfficial(container);
    const section=container.querySelector("section.card");
    if(section){section.insertAdjacentHTML("afterbegin",this._localeControlsHtml());this._bindLocaleControls(section);}
  }

  _renderRecommend(container){
    super._renderRecommend(container);
    const section=container.querySelector("section.card");
    if(section){section.insertAdjacentHTML("afterbegin",this._localeControlsHtml());this._bindLocaleControls(section);}
  }

  _translationNeeded(recipe){
    const source=this._recipeLanguage(recipe)||String(recipe?.sourceLanguage||"").toLowerCase().split(/[-_]/)[0];
    return Boolean(source&&source!==this._langCode());
  }

  _applyTranslation(recipe,row){
    if(!row||typeof row!=="object")return false;
    const source=recipe.translatedFrom||recipe.sourceLanguage||this._recipeLanguage(recipe)||"";
    if(row.title)recipe.title=String(row.title);
    if(Array.isArray(row.ingredients)&&row.ingredients.length)recipe.ingredients=row.ingredients.map(String);
    if(Array.isArray(row.steps)&&row.steps.length)recipe.steps=row.steps.map(String);
    if(Array.isArray(row.missing)&&recipe.match){recipe.match={...recipe.match,missingIngredients:row.missing.map(String)};}
    recipe.translatedFrom=source;
    recipe.language=this._langCode();
    recipe.translationRequired=false;
    recipe.translationMethod="ai_task";
    return true;
  }

  async _translateItems(items){
    if(!this._shouldTranslate())return;
    const pending=(items||[]).filter(recipe=>this._translationNeeded(recipe));
    if(!pending.length)return;
    for(let offset=0;offset<pending.length;offset+=8){
      const chunk=pending.slice(offset,offset+8);
      try{
        const result=await this._api("cook4me/v5/translate",{
          target_language:this._langCode(),
          recipes:chunk,
        });
        if(!result?.available){this._translateEnabled=false;return;}
        const byId=new Map((result.items||[]).map(row=>[String(row?.id),row]));
        chunk.forEach((recipe,index)=>{const row=byId.get(String(index));if(row)this._applyTranslation(recipe,row);});
      }catch(_e){
        // Translation is optional: leave the original SEB text untouched.
        return;
      }
      if(this._tab==="official"||this._tab==="recommend")this._renderTab();
    }
  }

  _recipeCard(recipe,custom=false){
    let html=super._recipeCard(recipe,custom);
    if(recipe?.translationMethod==="ai_task"&&recipe?.translatedFrom){
      const chip=`<span class="chip">🌐 ${this._escape(this._t("translated"))}: ${this._escape(String(recipe.translatedFrom).toUpperCase())}</span>`;
      html=html.replace('<div class="chips">',`<div class="chips">${chip}`);
    }
    return html;
  }

  _detailHtml(recipe){
    let html=super._detailHtml(recipe);
    if(html&&recipe?.translationMethod==="ai_task"&&recipe?.translatedFrom){
      const notice=`<div class="notice">🌐 ${this._escape(this._t("translated"))}: ${this._escape(String(recipe.translatedFrom).toUpperCase())}</div>`;
      html=html.replace('<div class="detail-head">',`${notice}<div class="detail-head">`);
    }
    return html;
  }

  async _search(query){
    this._searchQuery=String(query||"").trim();
    this._opened=null;
    try{
      this._message(this._t("loading"));
      const result=await this._api("cook4me/v5/search",{
        entry_id:this._entryId,
        query:this._searchQuery,
        size:20,
        language:this._selectedLanguage(),
        strict_language:this._strictLanguage(),
      });
      this._results=result?.items||[];
      this._message("");
      this._renderTab();
      if(this._shouldTranslate()&&this._results.some(recipe=>this._translationNeeded(recipe))){
        this._message(this._t("translating"));
        await this._translateItems(this._results);
        this._message("");
        this._renderTab();
      }
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  async _recommend(){
    this._opened=null;
    try{
      this._message(this._t("loading"));
      const result=await this._api("cook4me/v5/recommend",{
        entry_id:this._entryId,
        limit:12,
        catalog_size:24,
        language:this._selectedLanguage(),
        strict_language:this._strictLanguage(),
      });
      this._recommendations=result?.items||[];
      this._message("");
      this._renderTab();
      if(this._shouldTranslate()&&this._recommendations.some(recipe=>this._translationNeeded(recipe))){
        this._message(this._t("translating"));
        await this._translateItems(this._recommendations);
        this._message("");
        this._renderTab();
      }
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  async _openOfficial(recipe){
    const variant=recipe.displayVariantId||recipe.searchVariantId||recipe.variantFunctionalId||recipe.recipeFunctionalId;
    if(!variant){this._opened={...recipe};this._renderTab();this._scrollToDetail();return;}
    try{
      this._message(this._t("loading"));
      let detail;
      const hasSteps=Array.isArray(recipe.steps)&&recipe.steps.some(step=>this._stepText(step));
      if(hasSteps)detail={...recipe};
      else detail=await this._api("cook4me/v5/recipe_detail",{
        entry_id:this._entryId,
        variant_id:String(variant),
        language:this._selectedLanguage(),
      });
      detail={
        ...recipe,
        ...detail,
        sendVariantId:recipe.sendVariantId||detail.sendVariantId||recipe.searchVariantId,
        sendGroupingFunctionalId:recipe.sendGroupingFunctionalId||detail.sendGroupingFunctionalId,
        sendRecipeFunctionalId:recipe.sendRecipeFunctionalId||detail.sendRecipeFunctionalId,
      };
      if(this._shouldTranslate()&&this._translationNeeded(detail)){
        const result=await this._api("cook4me/v5/translate",{
          target_language:this._langCode(),
          recipes:[detail],
        });
        const row=result?.items?.[0];
        if(result?.available&&row)this._applyTranslation(detail,row);
      }
      this._opened=detail;
      this._message("");
      this._renderTab();
      this._scrollToDetail();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }
}

customElements.define("cook4me-recipe-hub-panel-v5",Cook4MeRecipeHubPanelV5);
