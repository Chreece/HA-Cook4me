import "./cook4me-panel-v6.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v6");

class Cook4MeRecipeHubPanelV7 extends BasePanel {
  constructor(){
    super();
    this._capabilities={languages:[],defaultAiTaskAvailable:false,defaultAiTaskEntityId:null,persistentCache:true};
  }

  async _loadCapabilities(){
    try{
      const capabilities=await this._api("cook4me/v7/capabilities");
      this._capabilities=capabilities||this._capabilities;
      if(!this._translationPreferenceInitialized){
        this._translateEnabled=Boolean(this._capabilities.defaultAiTaskAvailable);
        this._translationPreferenceInitialized=true;
      }
      this._renderTab();
    }catch(_e){
      this._capabilities={languages:[],defaultAiTaskAvailable:false,defaultAiTaskEntityId:null,persistentCache:true};
      this._translateEnabled=false;
      this._translationPreferenceInitialized=true;
    }
  }

  _servingOptions(recipe){return Array.isArray(recipe?.servingVariants)?recipe.servingVariants:[];}

  _ensureServingSelection(recipe){
    const options=this._servingOptions(recipe);
    if(!options.length)return null;
    let selected=options.find(option=>String(option.sendVariantId||"")===String(recipe.selectedSendVariantId||recipe.sendVariantId||""));
    if(!selected)selected=options.find(option=>Number(option.servings)===Number(recipe.selectedServings));
    if(!selected)selected=options[0];
    recipe.selectedSendVariantId=selected.sendVariantId;
    recipe.selectedDisplayVariantId=selected.displayVariantId||selected.sendVariantId;
    recipe.selectedServings=selected.servings;
    recipe.sendVariantId=selected.sendVariantId||recipe.sendVariantId;
    recipe.displayVariantId=selected.displayVariantId||recipe.displayVariantId;
    return selected;
  }

  _servingSelectHtml(recipe,detail=false){
    const options=this._servingOptions(recipe);
    if(options.length<=1)return"";
    const selected=this._ensureServingSelection(recipe);
    const select=options.map(option=>{
      const value=String(option.sendVariantId||"");
      const label=option.label??option.servings??"—";
      return `<option value="${this._escape(value)}" ${String(selected?.sendVariantId||"")===value?"selected":""}>${this._escape(label)}</option>`;
    }).join("");
    return `<div class="field serving-choice" style="min-width:${detail?"180":"140"}px"><label>${this._escape(this._t("servings"))}</label><select data-action="servings">${select}</select></div>`;
  }

  _recipeCard(recipe,custom=false){
    this._ensureServingSelection(recipe);
    let html=super._recipeCard(recipe,custom);
    if(!custom){
      const selector=this._servingSelectHtml(recipe,false);
      if(selector)html=html.replace('<div class="actions">',`${selector}<div class="actions">`);
    }
    return html;
  }

  _bindCards(container,items,custom=false){
    super._bindCards(container,items,custom);
    if(custom)return;
    container.querySelectorAll(".recipe").forEach((card,index)=>{
      const recipe=items[index];
      card.querySelector('[data-action="servings"]')?.addEventListener("change",event=>{
        void this._selectServing(recipe,String(event.target.value||""));
      });
    });
  }

  _detailHtml(recipe){
    let html=super._detailHtml(recipe);
    if(!html||!recipe)return html;
    const selector=this._servingSelectHtml(recipe,true);
    if(selector)html=html.replace('<div class="detail-layout">',`${selector}<div class="detail-layout" style="margin-top:12px">`);
    return html;
  }

  _bindDetail(container){
    super._bindDetail(container);
    container.querySelector('#recipeDetail [data-action="servings"]')?.addEventListener("change",event=>{
      if(this._opened)void this._selectServing(this._opened,String(event.target.value||""),true);
    });
  }

  async _translateItems(items){
    if(!this._shouldTranslate())return;
    const pending=(items||[]).filter(recipe=>this._translationNeeded(recipe));
    if(!pending.length)return;
    for(let offset=0;offset<pending.length;offset+=20){
      const chunk=pending.slice(offset,offset+20);
      try{
        const result=await this._api("cook4me/v7/translate",{
          entry_id:this._entryId,
          target_language:this._langCode(),
          recipes:chunk,
        });
        if(!result?.available){this._translateEnabled=false;return;}
        const byId=new Map((result.items||[]).map(row=>[String(row?.id),row]));
        chunk.forEach((recipe,index)=>{
          const row=byId.get(String(index));
          if(row)this._applyTranslation(recipe,row);
        });
      }catch(_e){
        // Optional translation failure leaves the fully hydrated source recipe.
        return;
      }
    }
  }

  async _translateSingle(recipe){
    if(!this._shouldTranslate()||!this._translationNeeded(recipe))return recipe;
    try{
      const result=await this._api("cook4me/v7/translate",{
        entry_id:this._entryId,
        target_language:this._langCode(),
        recipes:[recipe],
      });
      const row=result?.items?.find(item=>String(item?.id)==="0");
      if(result?.available&&row)this._applyTranslation(recipe,row);
    }catch(_e){}
    return recipe;
  }

  async _search(query){
    this._searchQuery=String(query||"").trim();
    this._opened=null;
    try{
      this._message(this._t("loading"));
      const result=await this._api("cook4me/v7/search",{
        entry_id:this._entryId,
        query:this._searchQuery,
        size:20,
        language:this._selectedLanguage(),
        strict_language:this._strictLanguage(),
      });
      const items=result?.items||[];
      items.forEach(recipe=>this._ensureServingSelection(recipe));
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
      const result=await this._api("cook4me/v7/recommend",{
        entry_id:this._entryId,
        limit:12,
        catalog_size:24,
        language:this._selectedLanguage(),
        strict_language:this._strictLanguage(),
      });
      const items=result?.items||[];
      items.forEach(recipe=>this._ensureServingSelection(recipe));
      if(this._shouldTranslate()&&items.some(recipe=>this._translationNeeded(recipe))){
        this._message(this._t("translating"));
        await this._translateItems(items);
      }
      this._recommendations=items;
      this._message("");
      this._renderTab();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  async _openOfficial(recipe){
    const selected=this._ensureServingSelection(recipe);
    const variant=selected?.displayVariantId
      ||recipe.selectedDisplayVariantId
      ||recipe.displayVariantId
      ||recipe.searchVariantId
      ||recipe.variantFunctionalId
      ||recipe.recipeFunctionalId;
    if(!variant){
      const detail={...recipe};
      await this._translateSingle(detail);
      this._opened=detail;
      this._renderTab();this._scrollToDetail();return;
    }
    try{
      this._message(this._t("loading"));
      let detail;
      const hasSteps=Array.isArray(recipe.steps)&&recipe.steps.some(step=>this._stepText(step));
      const sameVariant=String(variant)===String(recipe.displayVariantId||recipe.searchVariantId||"");
      if(hasSteps&&sameVariant)detail={...recipe};
      else detail=await this._api("cook4me/v7/recipe_detail",{
        entry_id:this._entryId,
        variant_id:String(variant),
        language:this._selectedLanguage(),
      });
      detail={
        ...recipe,
        ...detail,
        servingVariants:recipe.servingVariants,
        availableServings:recipe.availableServings,
        selectedServings:selected?.servings??recipe.selectedServings,
        selectedSendVariantId:selected?.sendVariantId||recipe.selectedSendVariantId||recipe.sendVariantId,
        selectedDisplayVariantId:selected?.displayVariantId||recipe.selectedDisplayVariantId||variant,
        sendVariantId:selected?.sendVariantId||recipe.sendVariantId,
        displayVariantId:selected?.displayVariantId||variant,
        sendGroupingFunctionalId:recipe.sendGroupingFunctionalId||detail.sendGroupingFunctionalId,
        sendRecipeFunctionalId:recipe.sendRecipeFunctionalId||detail.sendRecipeFunctionalId,
      };
      await this._translateSingle(detail);
      this._opened=detail;
      this._message("");
      this._renderTab();
      this._scrollToDetail();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  async _selectServing(recipe,sendVariantId,fromDetail=false){
    const option=this._servingOptions(recipe).find(row=>String(row.sendVariantId||"")===String(sendVariantId||""));
    if(!option)return;
    const displayVariant=option.displayVariantId||option.sendVariantId;
    try{
      this._message(this._t("loading"));
      let detail=await this._api("cook4me/v7/recipe_detail",{
        entry_id:this._entryId,
        variant_id:String(displayVariant),
        language:this._selectedLanguage(),
      });
      const preserved={
        servingVariants:recipe.servingVariants,
        availableServings:recipe.availableServings,
        sendGroupingFunctionalId:recipe.sendGroupingFunctionalId,
        sendRecipeFunctionalId:recipe.sendRecipeFunctionalId,
        deviceCanAccept:recipe.deviceCanAccept,
      };
      Object.assign(recipe,detail,preserved,{
        selectedServings:option.servings,
        selectedSendVariantId:option.sendVariantId,
        selectedDisplayVariantId:displayVariant,
        sendVariantId:option.sendVariantId,
        displayVariantId:displayVariant,
      });
      await this._translateSingle(recipe);
      if(fromDetail){
        this._opened=recipe;
      }else if(this._opened){
        const openedGroup=String(this._opened.groupingFunctionalId||this._opened.sendGroupingFunctionalId||"");
        const recipeGroup=String(recipe.groupingFunctionalId||recipe.sendGroupingFunctionalId||"");
        if(openedGroup&&openedGroup===recipeGroup)this._opened={...recipe};
      }
      this._message("");
      this._renderTab();
      if(fromDetail)this._scrollToDetail();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  async _send(recipe){
    try{
      const selected=this._ensureServingSelection(recipe);
      const variant=selected?.sendVariantId
        ||recipe.selectedSendVariantId
        ||recipe.sendVariantId
        ||recipe.searchVariantId
        ||recipe.variantFunctionalId
        ||recipe.recipeFunctionalId;
      if(!variant)throw new Error("Missing official recipe ID");
      this._message(this._t("loading"));
      await this._api("cook4me/send_recipe",{entry_id:this._entryId,variant_id:String(variant)});
      this._message(`${this._t("send")}: ${this._clean(recipe.title||variant)}`);
      await this._loadOverview(true);
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }
}

customElements.define("cook4me-recipe-hub-panel-v7",Cook4MeRecipeHubPanelV7);
