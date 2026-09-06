import "./cook4me-panel-v7.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v7");

class Cook4MeRecipeHubPanelV8 extends BasePanel {
  constructor(){
    super();
    this._preferencesLoaded=false;
    this._uiPreferences={
      catalogLanguage:"auto",
      translateResults:true,
      lastTab:"official",
      recipeLanguageSelections:{},
      recipeServingSelections:{},
    };
    this._preferenceSaveTimer=null;
  }

  async _loadCapabilities(){
    try{
      const capabilities=await this._api("cook4me/v8/capabilities",{
        ...(this._entryId?{entry_id:this._entryId}:{})
      });
      this._capabilities=capabilities||this._capabilities;
      const preferences=capabilities?.preferences;
      if(preferences&&typeof preferences==="object"){
        this._uiPreferences={...this._uiPreferences,...preferences};
        this._catalogLanguage=String(this._uiPreferences.catalogLanguage||"auto");
        this._translateEnabled=Boolean(this._uiPreferences.translateResults);
        const tab=String(this._uiPreferences.lastTab||"official");
        if(["official","recommend","mine","profile","ai"].includes(tab))this._tab=tab;
        this._preferencesLoaded=true;
        this._translationPreferenceInitialized=true;
      }
      this._renderTabs();
      this._renderTab();
    }catch(_e){
      // If multiple entries exist, the first capability request can happen
      // before overview has selected an entry. Load generic v7 capabilities and
      // retry once the entry becomes known instead of losing the saved prefs.
      try{
        const capabilities=await this._api("cook4me/v7/capabilities");
        this._capabilities=capabilities||this._capabilities;
      }catch(_ignored){}
    }
  }

  async _loadOverview(silent=false,rerender=true){
    const before=this._entryId;
    await super._loadOverview(silent,rerender);
    if(!this._preferencesLoaded||before!==this._entryId)await this._loadCapabilities();
  }

  _renderEntrySelect(){
    super._renderEntrySelect();
    const select=this.shadowRoot?.getElementById("entrySelect");
    if(select&&!select.dataset.cook4meV8Bound){
      select.dataset.cook4meV8Bound="1";
      select.addEventListener("change",()=>{
        this._preferencesLoaded=false;
        queueMicrotask(()=>void this._loadCapabilities());
      });
    }
  }

  _renderTabs(){
    super._renderTabs();
    this.shadowRoot?.querySelectorAll("[data-tab]").forEach(button=>{
      if(button.dataset.cook4meV8Bound)return;
      button.dataset.cook4meV8Bound="1";
      button.addEventListener("click",()=>{
        this._uiPreferences.lastTab=String(button.dataset.tab||"official");
        this._schedulePreferenceSave();
      });
    });
  }

  _schedulePreferenceSave(){
    if(!this._entryId)return;
    if(this._preferenceSaveTimer)clearTimeout(this._preferenceSaveTimer);
    this._preferenceSaveTimer=setTimeout(()=>{
      this._preferenceSaveTimer=null;
      void this._savePreferences();
    },250);
  }

  async _savePreferences(){
    if(!this._entryId)return;
    this._uiPreferences.catalogLanguage=this._catalogLanguage||"auto";
    this._uiPreferences.translateResults=Boolean(this._translateEnabled);
    this._uiPreferences.lastTab=this._tab||"official";
    try{
      const result=await this._api("cook4me/v8/preferences_set",{
        entry_id:this._entryId,
        preferences:this._uiPreferences,
      });
      if(result?.preferences)this._uiPreferences={...this._uiPreferences,...result.preferences};
    }catch(_e){
      // Preference persistence must never break recipe browsing.
    }
  }

  _bindLocaleControls(container){
    super._bindLocaleControls(container);
    const language=container.querySelector("#recipeLanguage");
    if(language&&!language.dataset.cook4meV8Bound){
      language.dataset.cook4meV8Bound="1";
      language.addEventListener("change",()=>{
        this._uiPreferences.catalogLanguage=String(language.value||"auto");
        this._schedulePreferenceSave();
      });
    }
    const translate=container.querySelector("#translateResults");
    if(translate&&!translate.dataset.cook4meV8Bound){
      translate.dataset.cook4meV8Bound="1";
      translate.addEventListener("change",()=>{
        this._uiPreferences.translateResults=Boolean(translate.checked);
        this._schedulePreferenceSave();
      });
    }
  }

  _recipeKey(recipe){
    const groups=Array.isArray(recipe?.groupingFunctionalIds)?recipe.groupingFunctionalIds.map(String).filter(Boolean).sort():[];
    if(groups.length)return `mg:${groups.join("|")}`;
    const grouping=String(recipe?.groupingFunctionalId||recipe?.sendGroupingFunctionalId||"").trim();
    if(grouping)return `g:${grouping}`;
    const variant=String(recipe?.displayVariantId||recipe?.searchVariantId||recipe?.variantFunctionalId||recipe?.sendVariantId||"").trim();
    return variant?`v:${variant}`:"recipe";
  }

  _languageOptions(recipe){return Array.isArray(recipe?.languageVariants)?recipe.languageVariants:[];}

  _ensureRecipeSelections(recipe){
    const languages=this._languageOptions(recipe);
    const key=this._recipeKey(recipe);
    let languageOption=null;
    if(languages.length){
      const saved=String(this._uiPreferences.recipeLanguageSelections?.[key]||"").toLowerCase();
      const current=String(recipe.selectedLanguage||recipe.sourceLanguage||recipe.language||"").toLowerCase().split(/[-_]/)[0];
      languageOption=languages.find(row=>String(row.language||"").toLowerCase()===saved)
        ||languages.find(row=>String(row.language||"").toLowerCase()===current)
        ||languages.find(row=>String(row.language||"").toLowerCase()===this._selectedLanguage())
        ||languages[0];
      recipe.selectedLanguage=String(languageOption.language||"");
      recipe.servingVariants=Array.isArray(languageOption.servingVariants)?languageOption.servingVariants:[];
      recipe.availableServings=Array.isArray(languageOption.availableServings)?languageOption.availableServings:[];
    }

    const options=Array.isArray(recipe.servingVariants)?recipe.servingVariants:[];
    if(!options.length)return null;
    const savedServing=String(this._uiPreferences.recipeServingSelections?.[key]||"");
    let selected=null;
    if(savedServing){
      selected=options.find(row=>String(row.servings??"")===savedServing)
        ||options.find(row=>String(row.displayVariantId||"")===savedServing);
    }
    if(!selected){
      selected=options.find(row=>String(row.sendVariantId||"")===String(recipe.selectedSendVariantId||recipe.sendVariantId||""));
    }
    if(!selected)selected=options.find(row=>Number(row.servings)===Number(recipe.selectedServings));
    if(!selected)selected=options[0];

    recipe.selectedServings=selected.servings;
    recipe.selectedDisplayVariantId=selected.displayVariantId||recipe.displayVariantId;
    recipe.selectedSendVariantId=selected.sendVariantId||null;
    recipe.displayVariantId=selected.displayVariantId||recipe.displayVariantId;
    recipe.sendVariantId=selected.sendVariantId||null;
    recipe.sendGroupingFunctionalId=selected.sendGroupingFunctionalId||recipe.sendGroupingFunctionalId;
    recipe.sendRecipeFunctionalId=selected.sendRecipeFunctionalId||recipe.sendRecipeFunctionalId;
    recipe.sendable=Boolean(recipe.sendVariantId);
    return selected;
  }

  _languageSelectHtml(recipe,detail=false){
    const options=this._languageOptions(recipe);
    if(options.length<=1)return"";
    const selected=String(recipe.selectedLanguage||options[0]?.language||"");
    return `<div class="field recipe-language-choice" style="min-width:${detail?"190":"150"}px"><label>${this._escape(this._t("recipeLanguage"))}</label><select data-action="recipe-language">${options.map(row=>{
      const code=String(row.language||"").toLowerCase();
      return `<option value="${this._escape(code)}" ${code===selected?"selected":""}>${this._escape(this._languageName(code))} (${this._escape(code.toUpperCase())})</option>`;
    }).join("")}</select></div>`;
  }

  _recipeCard(recipe,custom=false){
    if(!custom)this._ensureRecipeSelections(recipe);
    let html=super._recipeCard(recipe,custom);
    if(!custom){
      const selector=this._languageSelectHtml(recipe,false);
      if(selector){
        const servingMarker='<div class="field serving-choice"';
        if(html.includes(servingMarker))html=html.replace(servingMarker,`${selector}${servingMarker}`);
        else html=html.replace('<div class="actions">',`${selector}<div class="actions">`);
      }
    }
    return html;
  }

  _bindCards(container,items,custom=false){
    super._bindCards(container,items,custom);
    if(custom)return;
    container.querySelectorAll(".recipe").forEach((card,index)=>{
      const recipe=items[index];
      card.querySelector('[data-action="recipe-language"]')?.addEventListener("change",event=>{
        void this._selectRecipeLanguage(recipe,String(event.target.value||""));
      });
    });
  }

  _detailHtml(recipe){
    if(recipe)this._ensureRecipeSelections(recipe);
    let html=super._detailHtml(recipe);
    if(!html||!recipe)return html;
    const selector=this._languageSelectHtml(recipe,true);
    if(selector)html=html.replace('<div class="detail-layout"',`${selector}<div class="detail-layout"`);
    return html;
  }

  _bindDetail(container){
    super._bindDetail(container);
    container.querySelector('#recipeDetail [data-action="recipe-language"]')?.addEventListener("change",event=>{
      if(this._opened)void this._selectRecipeLanguage(this._opened,String(event.target.value||""),true);
    });
  }

  async _search(query){
    this._searchQuery=String(query||"").trim();
    this._opened=null;
    try{
      this._message(this._t("loading"));
      const result=await this._api("cook4me/v8/search",{
        entry_id:this._entryId,
        query:this._searchQuery,
        size:20,
        language:this._selectedLanguage(),
        strict_language:this._strictLanguage(),
      });
      const items=result?.items||[];
      items.forEach(recipe=>this._ensureRecipeSelections(recipe));
      if(this._shouldTranslate()&&items.some(recipe=>this._translationNeeded(recipe))){
        this._message(this._t("translating"));
        await this._translateItems(items);
      }
      this._results=items;
      this._message("");
      this._renderTab();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  async _recommend(){
    this._opened=null;
    try{
      this._message(this._t("loading"));
      const result=await this._api("cook4me/v8/recommend",{
        entry_id:this._entryId,
        limit:12,
        catalog_size:24,
        language:this._selectedLanguage(),
        strict_language:this._strictLanguage(),
      });
      const items=result?.items||[];
      items.forEach(recipe=>this._ensureRecipeSelections(recipe));
      if(this._shouldTranslate()&&items.some(recipe=>this._translationNeeded(recipe))){
        this._message(this._t("translating"));
        await this._translateItems(items);
      }
      this._recommendations=items;
      this._message("");
      this._renderTab();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  async _selectRecipeLanguage(recipe,language,fromDetail=false){
    const key=this._recipeKey(recipe);
    const languageOption=this._languageOptions(recipe).find(row=>String(row.language||"").toLowerCase()===String(language||"").toLowerCase());
    if(!languageOption)return;
    const previousServing=recipe.selectedServings;
    const servings=Array.isArray(languageOption.servingVariants)?languageOption.servingVariants:[];
    let selected=servings.find(row=>Number(row.servings)===Number(previousServing));
    if(!selected)selected=servings[0];
    if(!selected)return;

    this._uiPreferences.recipeLanguageSelections={...(this._uiPreferences.recipeLanguageSelections||{}),[key]:String(languageOption.language)};
    if(selected.servings!==undefined&&selected.servings!==null){
      this._uiPreferences.recipeServingSelections={...(this._uiPreferences.recipeServingSelections||{}),[key]:String(selected.servings)};
    }
    this._schedulePreferenceSave();

    try{
      this._message(this._t("loading"));
      const detail=await this._api("cook4me/v7/recipe_detail",{
        entry_id:this._entryId,
        variant_id:String(selected.displayVariantId),
        language:String(languageOption.language),
      });
      const preserved={
        languageVariants:recipe.languageVariants,
        availableLanguages:recipe.availableLanguages,
        match:recipe.match,
        deviceCanAccept:recipe.deviceCanAccept,
      };
      Object.assign(recipe,detail,preserved,{
        selectedLanguage:String(languageOption.language),
        servingVariants:languageOption.servingVariants,
        availableServings:languageOption.availableServings,
        selectedServings:selected.servings,
        selectedDisplayVariantId:selected.displayVariantId,
        selectedSendVariantId:selected.sendVariantId||null,
        displayVariantId:selected.displayVariantId,
        sendVariantId:selected.sendVariantId||null,
        sendGroupingFunctionalId:selected.sendGroupingFunctionalId||recipe.sendGroupingFunctionalId,
        sendRecipeFunctionalId:selected.sendRecipeFunctionalId||recipe.sendRecipeFunctionalId,
        sendable:Boolean(selected.sendVariantId),
      });
      delete recipe.translationMethod;
      delete recipe.translatedFrom;
      recipe.sourceLanguage=String(languageOption.language);
      if(this._shouldTranslate()&&this._translationNeeded(recipe))await this._translateSingle(recipe);
      if(fromDetail)this._opened=recipe;
      else if(this._opened&&this._recipeKey(this._opened)===key)this._opened={...recipe};
      this._message("");
      this._renderTab();
      if(fromDetail)this._scrollToDetail();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  async _selectServing(recipe,sendVariantId,fromDetail=false){
    const options=Array.isArray(recipe.servingVariants)?recipe.servingVariants:[];
    const option=options.find(row=>String(row.sendVariantId||row.displayVariantId||"")===String(sendVariantId||""));
    if(!option)return;
    const key=this._recipeKey(recipe);
    const savedValue=option.servings!==undefined&&option.servings!==null?String(option.servings):String(option.displayVariantId||"");
    this._uiPreferences.recipeServingSelections={...(this._uiPreferences.recipeServingSelections||{}),[key]:savedValue};
    this._schedulePreferenceSave();

    try{
      this._message(this._t("loading"));
      const detail=await this._api("cook4me/v7/recipe_detail",{
        entry_id:this._entryId,
        variant_id:String(option.displayVariantId||option.sendVariantId),
        language:String(recipe.selectedLanguage||this._selectedLanguage()),
      });
      const preserved={
        languageVariants:recipe.languageVariants,
        availableLanguages:recipe.availableLanguages,
        servingVariants:recipe.servingVariants,
        availableServings:recipe.availableServings,
        selectedLanguage:recipe.selectedLanguage,
        match:recipe.match,
        deviceCanAccept:recipe.deviceCanAccept,
      };
      Object.assign(recipe,detail,preserved,{
        selectedServings:option.servings,
        selectedDisplayVariantId:option.displayVariantId||option.sendVariantId,
        selectedSendVariantId:option.sendVariantId||null,
        displayVariantId:option.displayVariantId||option.sendVariantId,
        sendVariantId:option.sendVariantId||null,
        sendGroupingFunctionalId:option.sendGroupingFunctionalId||recipe.sendGroupingFunctionalId,
        sendRecipeFunctionalId:option.sendRecipeFunctionalId||recipe.sendRecipeFunctionalId,
        sendable:Boolean(option.sendVariantId),
      });
      delete recipe.translationMethod;
      delete recipe.translatedFrom;
      if(this._shouldTranslate()&&this._translationNeeded(recipe))await this._translateSingle(recipe);
      if(fromDetail)this._opened=recipe;
      else if(this._opened&&this._recipeKey(this._opened)===key)this._opened={...recipe};
      this._message("");
      this._renderTab();
      if(fromDetail)this._scrollToDetail();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  async _openOfficial(recipe){
    const selected=this._ensureRecipeSelections(recipe);
    const variant=selected?.displayVariantId||recipe.displayVariantId||recipe.searchVariantId;
    if(!variant){return super._openOfficial(recipe);}
    try{
      this._message(this._t("loading"));
      let detail;
      const hasSteps=Array.isArray(recipe.steps)&&recipe.steps.some(step=>this._stepText(step));
      const sameVariant=String(variant)===String(recipe.displayVariantId||recipe.searchVariantId||"");
      if(hasSteps&&sameVariant)detail={...recipe};
      else detail=await this._api("cook4me/v7/recipe_detail",{
        entry_id:this._entryId,
        variant_id:String(variant),
        language:String(recipe.selectedLanguage||this._selectedLanguage()),
      });
      detail={
        ...recipe,
        ...detail,
        languageVariants:recipe.languageVariants,
        availableLanguages:recipe.availableLanguages,
        servingVariants:recipe.servingVariants,
        availableServings:recipe.availableServings,
        selectedLanguage:recipe.selectedLanguage,
        selectedServings:selected?.servings??recipe.selectedServings,
        selectedSendVariantId:selected?.sendVariantId||recipe.sendVariantId,
        selectedDisplayVariantId:selected?.displayVariantId||variant,
        sendVariantId:selected?.sendVariantId||null,
        displayVariantId:selected?.displayVariantId||variant,
        sendGroupingFunctionalId:selected?.sendGroupingFunctionalId||recipe.sendGroupingFunctionalId,
        sendRecipeFunctionalId:selected?.sendRecipeFunctionalId||recipe.sendRecipeFunctionalId,
        sendable:Boolean(selected?.sendVariantId),
      };
      if(this._shouldTranslate()&&this._translationNeeded(detail))await this._translateSingle(detail);
      this._opened=detail;
      this._message("");
      this._renderTab();
      this._scrollToDetail();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }
}

customElements.define("cook4me-recipe-hub-panel-v8",Cook4MeRecipeHubPanelV8);
