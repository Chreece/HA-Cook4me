import "./cook4me-panel-v14.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v14");

const TEXT = {
  en:{
    recommendQuery:"Recipe filter",recommendQueryPlaceholder:"e.g. risotto",dietFilter:"Diet filter",profileDiet:"Profile diet",
  },
  de:{
    recommendQuery:"Rezeptfilter",recommendQueryPlaceholder:"z. B. Risotto",dietFilter:"Ernährungsfilter",profileDiet:"Profil-Ernährung",
  },
  el:{
    recommendQuery:"Φίλτρο συνταγής",recommendQueryPlaceholder:"π.χ. ριζότο",dietFilter:"Φίλτρο διατροφής",profileDiet:"Διατροφή προφίλ",
  },
};

class Cook4MeRecipeHubPanelV15 extends BasePanel {
  constructor(){
    super();
    this._recommendQuery="";
    this._recommendDiet="profile";
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _recommendDietOptions(){
    const profileDiet=String(this._entry()?.profile?.diet||"omnivore");
    const options=[
      ["profile",`${this._t("profileDiet")} (${this._t(profileDiet)})`],
      ["omnivore",this._t("omnivore")],
      ["pescatarian",this._t("pescatarian")],
      ["vegetarian",this._t("vegetarian")],
      ["vegan",this._t("vegan")],
    ];
    return options.map(([value,label])=>`<option value="${this._escape(value)}" ${value===this._recommendDiet?"selected":""}>${this._escape(label)}</option>`).join("");
  }

  _renderRecommend(c){
    const locale=this._localeControlsHtml();
    c.innerHTML=`<section class="card">
      ${locale}
      <div class="toolbar" style="align-items:end">
        <div class="field" style="min-width:220px"><label>${this._escape(this._t("dietFilter"))}</label><select id="recommendDiet">${this._recommendDietOptions()}</select></div>
        <div class="field grow"><label>${this._escape(this._t("recommendQuery"))}</label><input id="recommendQuery" value="${this._escape(this._recommendQuery)}" placeholder="${this._escape(this._t("recommendQueryPlaceholder"))}"></div>
        <button id="recommendBtn" class="btn">${this._escape(this._t("recommendBtn"))}</button>
      </div>
    </section>${this._detailHtml(this._opened)}<div id="recipeGrid" class="grid" style="margin-top:14px"></div>`;

    const section=c.querySelector("section.card");
    if(section)this._bindLocaleControls(section);
    c.querySelector("#recommendDiet")?.addEventListener("change",event=>{
      this._recommendDiet=String(event.target.value||"profile");
    });
    c.querySelector("#recommendQuery")?.addEventListener("input",event=>{
      this._recommendQuery=String(event.target.value||"");
    });
    c.querySelector("#recommendQuery")?.addEventListener("keydown",event=>{
      if(event.key==="Enter")void this._recommend();
    });
    c.querySelector("#recommendBtn")?.addEventListener("click",()=>void this._recommend());

    this._bindDetail(c);
    const grid=c.querySelector("#recipeGrid");
    if(this._recommendations.length){
      grid.innerHTML=this._recommendations.map(recipe=>this._recipeCard(recipe,false)).join("");
      this._bindCards(grid,this._recommendations,false);
    }
  }

  async _recommend(){
    this._opened=null;
    try{
      this._message(this._t("loading"));
      const result=await this._api("cook4me/v13/recommend",{
        entry_id:this._entryId,
        query:String(this._recommendQuery||"").trim(),
        diet:this._recommendDiet||"profile",
        limit:24,
        catalog_size:50,
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
}

customElements.define("cook4me-recipe-hub-panel-v15",Cook4MeRecipeHubPanelV15);
