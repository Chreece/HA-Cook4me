import "./cook4me-panel-v42.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v42");

const TEXT={
  en:{
    officialEnergy:"Energy",
    officialEnergyUnknownUnit:"SEB proves this value is per 100 g, but this payload does not expose the energy unit.",
    cachedUnresolved:"temporarily cached unresolved",
    readyToTry:"ready to try",
  },
  de:{
    officialEnergy:"Energie",
    officialEnergyUnknownUnit:"SEB bestätigt den Bezug pro 100 g, aber diese Antwort enthält keine Einheit für den Energiewert.",
    cachedUnresolved:"vorübergehend als ungelöst zwischengespeichert",
    readyToTry:"für einen neuen Versuch bereit",
  },
  el:{
    officialEnergy:"Ενέργεια",
    officialEnergyUnknownUnit:"Η SEB επιβεβαιώνει ότι η τιμή είναι ανά 100 g, αλλά αυτό το payload δεν εκθέτει τη μονάδα ενέργειας.",
    cachedUnresolved:"προσωρινά αποθηκευμένα ως μη επιλυμένα",
    readyToTry:"έτοιμα για νέα προσπάθεια",
  },
};

class Cook4MeRecipeHubPanelV43 extends BasePanel{
  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  async _maybeAutoFillNutritionCatalog(){
    const entryId=String(this._entryId||"");
    if(!entryId||this._nutritionAutoFillBusy||this._nutritionAutoFillEntry===entryId)return;
    this._nutritionAutoFillEntry=entryId;
    this._nutritionAutoFillBusy=true;
    try{
      const settings=await this._api("cook4me/v16/nutrition_settings",{entry_id:entryId});
      this._nutritionSettings={...(this._nutritionSettings||{}),...(settings||{})};
      if(Number(settings?.remaining)===0){
        this._nutritionAutoFillResult={skipped:true,reason:"catalog_complete",...settings};
        return;
      }
      const custom=Boolean(settings?.fdcApiKeyConfigured);
      const fill=await this._api("cook4me/v16/nutrition_catalog_fill",{
        entry_id:entryId,
        limit:custom?25:3,
      });
      this._nutritionAutoFillResult=fill||null;
      if(fill)this._nutritionSettings={...(this._nutritionSettings||{}),...fill};
    }catch(_e){
      this._nutritionAutoFillResult={error:true};
    }finally{
      this._nutritionAutoFillBusy=false;
    }
  }

  _officialNutritionBlock(recipe){
    const official=recipe?.officialNutrition;
    if(!official||typeof official!=="object")return"";
    const rows=super._officialNutritionRows(recipe);
    const energy=Number(official.energyPer100gValue);
    if(!rows.length&&!Number.isFinite(energy))return"";

    const chips=[];
    if(Number.isFinite(energy)){
      const shown=Number.isInteger(energy)?String(energy):String(Number(energy.toFixed(2)));
      chips.push(`<span class="chip">${this._escape(this._t("officialEnergy"))}: ${this._escape(shown)}</span>`);
    }
    for(const row of rows){
      const shown=Number.isInteger(row.value)?String(row.value):String(Number(row.value.toFixed(2)));
      chips.push(`<span class="chip">${this._escape(row.name)}: ${this._escape(shown)}${row.unit?` ${this._escape(row.unit)}`:""}</span>`);
    }

    return `<section class="card" data-cook4me-official-nutrition style="margin:12px 0">
      <h3 style="margin-top:0">${this._escape(this._t("officialNutrition"))}</h3>
      <div class="muted" style="margin-bottom:7px">${this._escape(this._t("officialPer100g"))} · ${this._escape(this._t("officialNutritionHelp"))}</div>
      <div class="chips">${chips.join("")}</div>
      ${Number.isFinite(energy)?`<div class="muted" style="margin-top:7px">${this._escape(this._t("officialEnergyUnknownUnit"))}</div>`:""}
    </section>`;
  }

  _nutritionSettingsHtml(){
    const html=super._nutritionSettingsHtml();
    const s=this._nutritionSettings||{};
    const blocked=Number(s.blockedFailures||0);
    const actionable=Number(s.actionableRemaining||0);
    const parts=[];
    if(blocked>0)parts.push(`${blocked} ${this._t("cachedUnresolved")}`);
    if(Number.isFinite(actionable)&&Number.isFinite(Number(s.remaining)))parts.push(`${actionable} ${this._t("readyToTry")}`);
    if(!parts.length)return html;
    const extra=`<div data-nutrition-resolution-status class="muted" style="margin-top:5px">${this._escape(parts.join(" · "))}</div>`;
    const pos=html.lastIndexOf("</section>");
    return pos>=0?`${html.slice(0,pos)}${extra}${html.slice(pos)}`:`${html}${extra}`;
  }

  _bindNutritionSettings(c){
    c.querySelector("#saveFdcApiKey")?.addEventListener("click",async()=>{
      const key=String(c.querySelector("#fdcApiKey")?.value||"").trim();
      if(!key)return;
      try{
        this._nutritionSettings=await this._api("cook4me/v16/nutrition_settings_set",{entry_id:this._entryId,api_key:key});
        this._nutritionAutoFillEntry="";
        await this._maybeAutoFillNutritionCatalog();
        this._renderTab();
      }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    });
    c.querySelector("#clearFdcApiKey")?.addEventListener("click",async()=>{
      try{
        this._nutritionSettings=await this._api("cook4me/v16/nutrition_settings_set",{entry_id:this._entryId,api_key:""});
        this._nutritionAutoFillEntry="";
        await this._maybeAutoFillNutritionCatalog();
        this._renderTab();
      }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    });
    c.querySelector("#buildNutritionCatalog")?.addEventListener("click",async()=>{
      const button=c.querySelector("#buildNutritionCatalog");if(button)button.disabled=true;
      try{
        const custom=Boolean(this._nutritionSettings?.fdcApiKeyConfigured);
        const result=await this._api("cook4me/v16/nutrition_catalog_fill",{entry_id:this._entryId,limit:custom?25:3});
        this._nutritionSettings={...(this._nutritionSettings||{}),...result};
        this._nutritionAutoFillResult=result;
        this._renderTab();
      }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
      finally{if(button)button.disabled=false;}
    });
  }
}

customElements.define("cook4me-recipe-hub-panel-v43",Cook4MeRecipeHubPanelV43);
