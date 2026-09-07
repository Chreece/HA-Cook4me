import "./cook4me-panel-v20.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v20");

const TEXT = {
  en:{interfaceLanguage:"Interface language",automaticUiLanguage:"Automatic (Home Assistant)",uiLanguageHelp:"Changes only the Cook4Me interface language."},
  de:{interfaceLanguage:"Oberflächensprache",automaticUiLanguage:"Automatisch (Home Assistant)",uiLanguageHelp:"Ändert nur die Sprache der Cook4Me-Oberfläche."},
  el:{interfaceLanguage:"Γλώσσα περιβάλλοντος",automaticUiLanguage:"Αυτόματα (Home Assistant)",uiLanguageHelp:"Αλλάζει μόνο τη γλώσσα του περιβάλλοντος Cook4Me."},
};

const UI_LANGUAGES = new Set(["auto","en","de","el"]);

class Cook4MeRecipeHubPanelV21 extends BasePanel {
  constructor(){
    super();
    this._uiLanguage="auto";
    this._uiLanguageStorageKeyLoaded="";
  }

  _haLangCode(){
    return String(this._hass?.language||"en").toLowerCase().split(/[-_]/)[0]||"en";
  }

  _uiLanguageStorageKey(){
    const user=String(this._hass?.user?.id||this._hass?.user?.name||"default");
    return `cook4me.recipeHub.uiLanguage.${user}`;
  }

  _ensureUiLanguage(){
    const key=this._uiLanguageStorageKey();
    if(this._uiLanguageStorageKeyLoaded===key)return;
    let selected="auto";
    try{selected=String(globalThis.localStorage?.getItem(key)||"auto").toLowerCase();}catch(_e){}
    this._uiLanguage=UI_LANGUAGES.has(selected)?selected:"auto";
    this._uiLanguageStorageKeyLoaded=key;
  }

  _langCode(){
    this._ensureUiLanguage();
    if(this._uiLanguage!=="auto")return this._uiLanguage;
    const ha=this._haLangCode();
    return ["en","de","el"].includes(ha)?ha:"en";
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _saveUiLanguage(value){
    this._uiLanguage=UI_LANGUAGES.has(value)?value:"auto";
    try{globalThis.localStorage?.setItem(this._uiLanguageStorageKey(),this._uiLanguage);}catch(_e){}
  }

  _uiLanguageOptions(){
    const selected=this._uiLanguage;
    const options=[
      ["auto",this._t("automaticUiLanguage")],
      ["en",this._languageName("en")],
      ["de",this._languageName("de")],
      ["el",this._languageName("el")],
    ];
    return options.map(([value,label])=>`<option value="${this._escape(value)}" ${selected===value?"selected":""}>${this._escape(label)}</option>`).join("");
  }

  _renderUiLanguageControl(){
    this._ensureUiLanguage();
    const tabs=this.shadowRoot?.getElementById("tabs");
    if(!tabs?.parentNode)return;
    this.shadowRoot?.getElementById("cook4meUiLanguageControl")?.remove();
    const wrapper=document.createElement("div");
    wrapper.id="cook4meUiLanguageControl";
    wrapper.className="toolbar";
    wrapper.style.cssText="justify-content:flex-end;align-items:end;margin:12px 0 -6px";
    wrapper.innerHTML=`<div class="field" style="min-width:230px;max-width:340px"><label>${this._escape(this._t("interfaceLanguage"))}</label><select id="cook4meUiLanguage">${this._uiLanguageOptions()}</select><div class="muted">${this._escape(this._t("uiLanguageHelp"))}</div></div>`;
    tabs.parentNode.insertBefore(wrapper,tabs);
    wrapper.querySelector("#cook4meUiLanguage")?.addEventListener("change",event=>{
      this._saveUiLanguage(String(event.target.value||"auto").toLowerCase());
      this._updateHeader?.();
      this._renderTabs();
      this._renderTab();
    });
  }

  _renderTabs(){
    super._renderTabs();
    this._renderUiLanguageControl();
  }

  // The interface language is deliberately independent from recipe translation.
  // "Translate to Home Assistant language" must continue targeting HA's language.
  _translationNeeded(recipe){
    const source=this._recipeLanguage(recipe)||String(recipe?.sourceLanguage||"").toLowerCase().split(/[-_]/)[0];
    return Boolean(source&&source!==this._haLangCode());
  }

  _applyTranslation(recipe,row){
    const applied=super._applyTranslation(recipe,row);
    if(applied)recipe.language=this._haLangCode();
    return applied;
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
          target_language:this._haLangCode(),
          recipes:chunk,
        });
        if(!result?.available){this._translateEnabled=false;return;}
        const byId=new Map((result.items||[]).map(row=>[String(row?.id),row]));
        chunk.forEach((recipe,index)=>{
          const row=byId.get(String(index));
          if(row)this._applyTranslation(recipe,row);
        });
      }catch(_e){return;}
    }
  }

  async _translateSingle(recipe){
    if(!this._shouldTranslate()||!this._translationNeeded(recipe))return recipe;
    try{
      const result=await this._api("cook4me/v7/translate",{
        entry_id:this._entryId,
        target_language:this._haLangCode(),
        recipes:[recipe],
      });
      const row=result?.items?.find(item=>String(item?.id)==="0");
      if(result?.available&&row)this._applyTranslation(recipe,row);
    }catch(_e){}
    return recipe;
  }
}

customElements.define("cook4me-recipe-hub-panel-v21",Cook4MeRecipeHubPanelV21);
