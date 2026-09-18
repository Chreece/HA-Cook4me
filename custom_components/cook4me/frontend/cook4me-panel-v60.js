import "./cook4me-panel-v59.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v59");
const TEXT={
  en:{offlineCatalogHelp:"Searches the local offline Cook4Me catalog. Query language is independent of the selected source catalogs.",nutrition:"Nutrition",perServing:"per serving",recipeTotal:"recipe total",energy:"Energy",protein:"Protein",carbs:"Carbs",fat:"Fat",fiber:"Fibre",coverage:"coverage"},
  de:{offlineCatalogHelp:"Durchsucht den lokalen Offline-Cook4Me-Katalog. Die Suchsprache ist unabhängig von den ausgewählten Quellkatalogen.",nutrition:"Nährwerte",perServing:"pro Portion",recipeTotal:"Rezept gesamt",energy:"Energie",protein:"Eiweiß",carbs:"Kohlenhydrate",fat:"Fett",fiber:"Ballaststoffe",coverage:"Abdeckung"},
  el:{offlineCatalogHelp:"Αναζητά στον τοπικό offline κατάλογο Cook4Me. Η γλώσσα αναζήτησης είναι ανεξάρτητη από τους επιλεγμένους καταλόγους πηγής.",nutrition:"Διατροφικά στοιχεία",perServing:"ανά μερίδα",recipeTotal:"σύνολο συνταγής",energy:"Ενέργεια",protein:"Πρωτεΐνη",carbs:"Υδατάνθρακες",fat:"Λιπαρά",fiber:"Ίνες",coverage:"κάλυψη"},
};

class Cook4MeRecipeHubPanelV60 extends BasePanel{
  constructor(){
    super();
    this._v60OutsidePointer=(event)=>{
      const path=typeof event.composedPath==="function"?event.composedPath():[];
      this.shadowRoot?.querySelectorAll(".rx-v49-picker[open]").forEach(picker=>{if(!path.includes(picker))picker.removeAttribute("open");});
    };
    this._v60Escape=(event)=>{if(event.key==="Escape")this.shadowRoot?.querySelectorAll(".rx-v49-picker[open]").forEach(picker=>picker.removeAttribute("open"));};
    globalThis.document?.addEventListener("pointerdown",this._v60OutsidePointer,true);
    globalThis.document?.addEventListener("keydown",this._v60Escape,true);
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _ensureV60Styles(){
    if(this.shadowRoot?.getElementById("cook4meV60Styles"))return;
    const style=document.createElement("style");style.id="cook4meV60Styles";style.textContent=`
      .rx-v60-nutrition{margin:12px 0}.rx-v60-nutrition-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(115px,1fr));gap:8px;margin-top:9px}.rx-v60-nutrient{padding:9px 10px;border:1px solid var(--divider-color);border-radius:11px;background:var(--secondary-background-color)}.rx-v60-nutrient small{display:block;color:var(--secondary-text-color);margin-bottom:3px}.rx-v60-nutrient strong{font-size:15px}.rx-v60-coverage{margin-top:8px;color:var(--secondary-text-color);font-size:12px}
      @media(max-width:700px){
        #officialCatalogLanguages.rx-v49-picker>.rx-v49-picker-body{position:fixed;z-index:10080;left:max(12px,env(safe-area-inset-left));right:max(12px,env(safe-area-inset-right));top:max(68px,calc(env(safe-area-inset-top) + 54px));bottom:max(14px,env(safe-area-inset-bottom));width:auto;min-width:0;max-width:none;max-height:none;overflow:auto;overscroll-behavior:contain}
        #officialCatalogLanguages .rx-v49-checks{grid-template-columns:1fr 1fr}
      }
      @media(max-width:430px){#officialCatalogLanguages .rx-v49-checks{grid-template-columns:1fr}}
    `;this.shadowRoot?.appendChild(style);
  }

  _renderShell(){const result=super._renderShell();this._ensureV60Styles();return result;}

  _renderOfficial(c){
    super._renderOfficial(c);this._ensureV60Styles();
    const note=c?.querySelector(".rx-v49-cache-note");if(note)note.textContent=this._t("offlineCatalogHelp");
  }

  async _search(query){
    this._searchQuery=String(query||"").trim();this._opened=null;
    try{
      this._message(this._t("loading"));
      const result=await this._api("cook4me/v31/official_search",{
        entry_id:this._entryId,
        query:this._searchQuery,
        query_language:this._langCode(),
        languages:this._loadOfficialLanguages(),
        page:0,
        size:20,
      });
      const items=result?.items||[];items.forEach(recipe=>this._ensureRecipeSelections?.(recipe));
      if(this._shouldTranslate?.()&&items.some(recipe=>this._translationNeeded?.(recipe))){this._message(this._t("translating"));await this._translateItems(items);}
      this._results=items;this._searchMeta=result;this._message("");this._renderTab();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  _v59MapApi(type){
    const mapped=super._v59MapApi(type);
    return mapped==="cook4me/v30/recipe_detail"?"cook4me/v31/recipe_detail":mapped;
  }

  _v60Nutrition(recipe){
    const nutrition=recipe?.catalogNutrition||recipe?.nutrition;
    if(!nutrition||typeof nutrition!=="object"||nutrition.available===false)return null;
    const perServing=nutrition.perServing&&typeof nutrition.perServing==="object"?nutrition.perServing:null;
    const values=perServing||nutrition.values||nutrition.totals||{};
    const pick=(...keys)=>{for(const key of keys){const value=Number(values?.[key]);if(Number.isFinite(value))return value;}return null;};
    const coverage=nutrition.coverage&&typeof nutrition.coverage==="object"?Number(nutrition.coverage.coveragePercent):Number(nutrition.coverage)*100;
    return {
      nutrition,values,perServing:Boolean(perServing),coverage:Number.isFinite(coverage)?Math.max(0,Math.min(100,coverage)):null,
      energy:pick("energyKcal","calories","energy"),protein:pick("proteinG","protein"),carbs:pick("carbohydrateG","carbohydrates","carbs"),fat:pick("fatG","fat"),fiber:pick("fiberG","fiber"),
    };
  }

  _v60Metric(value,energy=false){if(!Number.isFinite(Number(value)))return"";const number=Number(value);return energy?`${Math.round(number)} kcal`:`${Number(number.toFixed(1))} g`;}

  _v60NutritionChips(recipe){
    const data=this._v60Nutrition(recipe);if(!data)return"";const chips=[];
    for(const [label,value,energy] of [[this._t("energy"),data.energy,true],[this._t("protein"),data.protein,false],[this._t("carbs"),data.carbs,false],[this._t("fat"),data.fat,false],[this._t("fiber"),data.fiber,false]])if(value!==null)chips.push(`<span class="chip" data-v60-nutrition>${this._escape(label)}: ${this._escape(this._v60Metric(value,energy))}</span>`);
    if(data.coverage!==null)chips.push(`<span class="chip rx-v59-nutrition-meta" data-v60-nutrition>${this._escape(this._t("coverage"))}: ${Math.round(data.coverage)}%</span>`);
    return chips.join("");
  }

  _recipeCard(recipe,custom=false){
    let html=super._recipeCard(recipe,custom);const chips=this._v60NutritionChips(recipe);if(!chips)return html;
    return html.replace('<div class="chips">',`<div class="chips">${chips}`);
  }

  _v60NutritionBlock(recipe){
    const data=this._v60Nutrition(recipe);if(!data)return"";const rows=[];
    for(const [label,value,energy] of [[this._t("energy"),data.energy,true],[this._t("protein"),data.protein,false],[this._t("carbs"),data.carbs,false],[this._t("fat"),data.fat,false],[this._t("fiber"),data.fiber,false]])if(value!==null)rows.push(`<div class="rx-v60-nutrient"><small>${this._escape(label)}</small><strong>${this._escape(this._v60Metric(value,energy))}</strong></div>`);
    if(!rows.length)return"";const basis=data.perServing?this._t("perServing"):this._t("recipeTotal");const coverage=data.coverage!==null?`<div class="rx-v60-coverage">${this._escape(this._t("coverage"))}: ${Math.round(data.coverage)}%</div>`:"";
    return `<section class="card rx-v60-nutrition"><h3 style="margin:0">${this._escape(this._t("nutrition"))}</h3><div class="muted">${this._escape(basis)}</div><div class="rx-v60-nutrition-grid">${rows.join("")}</div>${coverage}</section>`;
  }

  _detailHtml(recipe){
    let html=super._detailHtml(recipe);const block=this._v60NutritionBlock(recipe);if(!block||!html)return html;const marker='<div class="detail-layout"';const pos=html.indexOf(marker);return pos>=0?`${html.slice(0,pos)}${block}${html.slice(pos)}`:`${block}${html}`;
  }

  disconnectedCallback(){
    globalThis.document?.removeEventListener("pointerdown",this._v60OutsidePointer,true);globalThis.document?.removeEventListener("keydown",this._v60Escape,true);
    if(super.disconnectedCallback)super.disconnectedCallback();
  }
}

customElements.define("cook4me-recipe-hub-panel-v60",Cook4MeRecipeHubPanelV60);
