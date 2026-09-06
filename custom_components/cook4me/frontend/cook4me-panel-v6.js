import "./cook4me-panel-v5.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v5");

class Cook4MeRecipeHubPanelV6 extends BasePanel {
  _needsHydration(recipe){
    const title=this._clean(recipe?.title||"");
    const ids=[
      recipe?.displayVariantId,
      recipe?.searchVariantId,
      recipe?.variantFunctionalId,
      recipe?.sendVariantId,
      recipe?.recipeFunctionalId,
    ].filter(Boolean).map(String);
    if(!title)return true;
    if(ids.includes(title))return true;
    return /^\d{4,}$/.test(title);
  }

  async _hydrateRecipe(recipe){
    if(!this._needsHydration(recipe))return false;
    const variant=recipe?.displayVariantId
      ||recipe?.sendVariantId
      ||recipe?.searchVariantId
      ||recipe?.variantFunctionalId
      ||recipe?.recipeFunctionalId;
    if(!variant)return false;
    const source=String(recipe?.sourceLanguage||recipe?.deviceSourceLanguage||recipe?.language||this._selectedLanguage()).toLowerCase().split(/[-_]/)[0];
    try{
      const detail=await this._api("cook4me/v5/recipe_detail",{
        entry_id:this._entryId,
        variant_id:String(variant),
        language:source||this._selectedLanguage(),
      });
      if(!detail||typeof detail!=="object")return false;
      const send={
        sendVariantId:recipe.sendVariantId,
        sendGroupingFunctionalId:recipe.sendGroupingFunctionalId,
        sendRecipeFunctionalId:recipe.sendRecipeFunctionalId,
        sendable:recipe.sendable,
        deviceCanAccept:recipe.deviceCanAccept,
        match:recipe.match,
      };
      Object.assign(recipe,detail);
      for(const [key,value] of Object.entries(send))if(value!==undefined)recipe[key]=value;
      recipe.sourceLanguage=String(detail.language||source||"").toLowerCase().split(/[-_]/)[0];
      recipe.translationRequired=Boolean(recipe.sourceLanguage&&recipe.sourceLanguage!==this._langCode());
      delete recipe.translationMethod;
      delete recipe.translatedFrom;
      return Boolean(this._clean(recipe.title||""));
    }catch(_e){
      return false;
    }
  }

  async _hydrateItems(items){
    const pending=(items||[]).filter(recipe=>this._needsHydration(recipe));
    let changed=false;
    for(let offset=0;offset<pending.length;offset+=4){
      const batch=pending.slice(offset,offset+4);
      const results=await Promise.all(batch.map(recipe=>this._hydrateRecipe(recipe)));
      if(results.some(Boolean))changed=true;
      if(changed&&(this._tab==="official"||this._tab==="recommend"))this._renderTab();
    }
    return changed;
  }

  async _search(query){
    await super._search(query);
    const changed=await this._hydrateItems(this._results);
    if(changed&&this._shouldTranslate()&&this._results.some(recipe=>this._translationNeeded(recipe))){
      this._message(this._t("translating"));
      await this._translateItems(this._results);
      this._message("");
    }
    if(changed)this._renderTab();
  }

  async _recommend(){
    await super._recommend();
    const changed=await this._hydrateItems(this._recommendations);
    if(changed&&this._shouldTranslate()&&this._recommendations.some(recipe=>this._translationNeeded(recipe))){
      this._message(this._t("translating"));
      await this._translateItems(this._recommendations);
      this._message("");
    }
    if(changed)this._renderTab();
  }
}

customElements.define("cook4me-recipe-hub-panel-v6",Cook4MeRecipeHubPanelV6);
