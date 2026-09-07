import "./cook4me-panel-v41.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v41");

const TEXT={
  en:{
    officialNutrition:"Official SEB nutrition",
    officialPer100g:"Per 100 g",
    officialNutritionHelp:"Official per-100-g values are kept separate from meal totals. Meal totals continue to use quantity-aware scanned-product and generic ingredient data.",
  },
  de:{
    officialNutrition:"Offizielle SEB-Nährwerte",
    officialPer100g:"Pro 100 g",
    officialNutritionHelp:"Offizielle Werte pro 100 g bleiben von den Gerichtssummen getrennt. Die Gerichtssummen verwenden weiterhin mengenbezogene Daten gescannter Produkte und generischer Zutaten.",
  },
  el:{
    officialNutrition:"Επίσημα διατροφικά στοιχεία SEB",
    officialPer100g:"Ανά 100 g",
    officialNutritionHelp:"Οι επίσημες τιμές ανά 100 g παραμένουν ξεχωριστές από τα σύνολα του γεύματος. Τα σύνολα συνεχίζουν να χρησιμοποιούν δεδομένα ποσότητας από σαρωμένα προϊόντα και γενικά υλικά.",
  },
};

class Cook4MeRecipeHubPanelV42 extends BasePanel{
  constructor(){
    super();
    this._nutritionAutoFillEntry="";
    this._nutritionAutoFillBusy=false;
    this._nutritionAutoFillResult=null;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _renderTab(){
    const result=super._renderTab();
    queueMicrotask(()=>void this._maybeAutoFillNutritionCatalog());
    return result;
  }

  async _maybeAutoFillNutritionCatalog(){
    const entryId=String(this._entryId||"");
    if(!entryId||this._nutritionAutoFillBusy||this._nutritionAutoFillEntry===entryId)return;
    this._nutritionAutoFillEntry=entryId;
    this._nutritionAutoFillBusy=true;
    try{
      const settings=await this._api("cook4me/v16/nutrition_settings",{entry_id:entryId});
      const custom=Boolean(settings?.fdcApiKeyConfigured);
      const fill=await this._api("cook4me/v16/nutrition_catalog_fill",{
        entry_id:entryId,
        limit:custom?25:3,
      });
      this._nutritionAutoFillResult=fill||null;
      if(fill){
        this._nutritionSettings={
          ...(this._nutritionSettings||{}),
          ...settings,
          catalogCount:fill.catalogCount??settings?.catalogCount??this._nutritionSettings?.catalogCount,
          catalogTotal:fill.catalogTotal??this._nutritionSettings?.catalogTotal,
          remaining:fill.remaining??this._nutritionSettings?.remaining,
        };
      }
    }catch(_e){
      // Nutrition enrichment is opportunistic and must never block Recipe Hub.
      this._nutritionAutoFillResult={error:true};
    }finally{
      this._nutritionAutoFillBusy=false;
    }
  }

  _nutritionRecipePayload(recipe){
    const payload=super._nutritionRecipePayload(recipe);
    if(recipe?.officialNutrition&&typeof recipe.officialNutrition==="object"){
      payload.officialNutrition=recipe.officialNutrition;
    }
    return payload;
  }

  _officialUnitLabel(unit){
    if(!unit||typeof unit!=="object")return"";
    const friendly=String(unit.abbreviation||unit.symbol||unit.name||"").trim();
    if(friendly&&!/^UNIT_\d+$/i.test(friendly))return friendly;
    return"";
  }

  _officialNutritionRows(recipe){
    const official=recipe?.officialNutrition;
    if(!official||typeof official!=="object")return[];
    const rows=[];
    for(const row of official.hierarchicalNutrients||[]){
      const value=Number(row?.valuePer100g);
      const name=String(row?.name||row?.path?.at?.(-1)||"").trim();
      if(!Number.isFinite(value)||!name)continue;
      rows.push({name,value,unit:this._officialUnitLabel(row.unit)});
    }
    return rows;
  }

  _officialNutritionBlock(recipe){
    const rows=this._officialNutritionRows(recipe);
    if(!rows.length)return"";
    const chips=rows.map(row=>{
      const shown=Number.isInteger(row.value)?String(row.value):String(Number(row.value.toFixed(2)));
      return `<span class="chip">${this._escape(row.name)}: ${this._escape(shown)}${row.unit?` ${this._escape(row.unit)}`:""}</span>`;
    }).join("");
    return `<section class="card" data-cook4me-official-nutrition style="margin:12px 0">
      <h3 style="margin-top:0">${this._escape(this._t("officialNutrition"))}</h3>
      <div class="muted" style="margin-bottom:7px">${this._escape(this._t("officialPer100g"))} · ${this._escape(this._t("officialNutritionHelp"))}</div>
      <div class="chips">${chips}</div>
    </section>`;
  }

  _detailHtml(recipe){
    let html=super._detailHtml(recipe);
    const block=this._officialNutritionBlock(recipe);
    if(!block||html.includes("data-cook4me-official-nutrition"))return html;
    const marker='<div class="detail-layout"';
    const pos=html.indexOf(marker);
    return pos>=0?`${html.slice(0,pos)}${block}${html.slice(pos)}`:`${block}${html}`;
  }
}

customElements.define("cook4me-recipe-hub-panel-v42",Cook4MeRecipeHubPanelV42);
