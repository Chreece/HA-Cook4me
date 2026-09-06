import "./cook4me-panel-v10.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v10");

const TEXT = {
  en:{
    recommend:"For what I have in my house",profile:"House ingredients & diet",pantry:"What I have in my house",
    automaticLanguage:"Automatic (Cook4Me setup language)",ingredientCatalog:"Ingredient catalog language",ingredientSearch:"Search ingredients…",
    addHouse:"Add to house",removeHouse:"Remove",houseEmpty:"No house ingredients selected yet.",catalogLoading:"Loading ingredient catalog…",
    addMissing:"Add missing ingredients to shopping list",addOne:"Add to shopping list",atHome:"At home",staple:"Basic staple",
    shoppingAdded:"Added to Home Assistant Shopping List",shoppingNothing:"Everything is already on the Shopping List",
  },
  de:{
    recommend:"Für das, was ich zu Hause habe",profile:"Zutaten zu Hause & Ernährung",pantry:"Was ich zu Hause habe",
    automaticLanguage:"Automatisch (Cook4Me-Einrichtungssprache)",ingredientCatalog:"Sprache des Zutatenkatalogs",ingredientSearch:"Zutaten suchen…",
    addHouse:"Zu Hause hinzufügen",removeHouse:"Entfernen",houseEmpty:"Noch keine Zutaten für zu Hause ausgewählt.",catalogLoading:"Zutatenkatalog wird geladen…",
    addMissing:"Fehlende Zutaten zur Einkaufsliste",addOne:"Zur Einkaufsliste",atHome:"Zu Hause",staple:"Grundvorrat",
    shoppingAdded:"Zur Home-Assistant-Einkaufsliste hinzugefügt",shoppingNothing:"Alles steht bereits auf der Einkaufsliste",
  },
  el:{
    recommend:"Για όσα έχω στο σπίτι",profile:"Υλικά στο σπίτι & διατροφή",pantry:"Τι έχω στο σπίτι",
    automaticLanguage:"Αυτόματα (γλώσσα ρύθμισης Cook4Me)",ingredientCatalog:"Γλώσσα καταλόγου υλικών",ingredientSearch:"Αναζήτηση υλικών…",
    addHouse:"Προσθήκη στο σπίτι",removeHouse:"Αφαίρεση",houseEmpty:"Δεν έχουν επιλεγεί ακόμη υλικά που υπάρχουν στο σπίτι.",catalogLoading:"Φόρτωση καταλόγου υλικών…",
    addMissing:"Προσθήκη υλικών που λείπουν στη λίστα αγορών",addOne:"Προσθήκη στη λίστα αγορών",atHome:"Υπάρχει στο σπίτι",staple:"Βασικό υλικό",
    shoppingAdded:"Προστέθηκε στη λίστα αγορών του Home Assistant",shoppingNothing:"Όλα υπάρχουν ήδη στη λίστα αγορών",
  },
};

class Cook4MeRecipeHubPanelV11 extends BasePanel {
  constructor(){
    super();
    this._ingredientCatalog=[];
    this._ingredientCatalogLanguage="";
    this._ingredientCatalogLoading=false;
    this._houseIngredients=[];
    this._houseEntryId="";
    this._houseFilter="";
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  async _api(type,data={}){
    const mapped={
      "cook4me/v8/capabilities":"cook4me/v11/capabilities",
      "cook4me/v9/capabilities":"cook4me/v11/capabilities",
    }[type]||type;
    return super._api(mapped,data);
  }

  _selectedLanguage(){
    if(this._catalogLanguage!=="auto")return this._catalogLanguage;
    return String(this._capabilities?.deviceCatalogLanguage||"de").toLowerCase();
  }

  _localeControlsHtml(){
    let html=super._localeControlsHtml();
    const language=String(this._capabilities?.deviceCatalogLanguage||"").toLowerCase();
    if(language){
      const label=`${this._t("automaticLanguage")} · ${this._languageName(language)} (${language.toUpperCase()})`;
      html=html.replace(this._escape(super._t("automaticLanguage")),this._escape(label));
    }
    return html;
  }

  _ensureHouseState(){
    if(this._houseEntryId===this._entryId)return;
    const profile=this._entry()?.profile||{};
    const rows=Array.isArray(profile.houseIngredients)&&profile.houseIngredients.length
      ?profile.houseIngredients
      :(profile.pantry||[]).map(name=>({name:String(name)}));
    this._houseIngredients=rows.map(row=>({...(row?.key?{key:String(row.key)}:{}),name:String(row?.name||row||"").trim()})).filter(row=>row.name);
    this._houseEntryId=this._entryId||"";
    this._ingredientCatalog=[];
    this._ingredientCatalogLanguage="";
  }

  async _loadIngredientCatalog(language=null,refresh=false){
    if(!this._entryId||this._ingredientCatalogLoading)return;
    const selected=String(language||this._ingredientCatalogLanguage||this._capabilities?.ingredientCatalogLanguage||this._capabilities?.deviceCatalogLanguage||"de").toLowerCase();
    this._ingredientCatalogLoading=true;
    try{
      const result=await this._api("cook4me/v11/ingredient_catalog",{entry_id:this._entryId,language:selected,refresh:Boolean(refresh)});
      this._ingredientCatalog=Array.isArray(result?.items)?result.items:[];
      this._ingredientCatalogLanguage=String(result?.language||selected);
      if(this._tab==="profile")this._renderTab();
    }catch(e){
      this._message(`${this._t("error")}: ${e.message||e}`,true);
    }finally{this._ingredientCatalogLoading=false;}
  }

  _catalogLanguageOptions(){
    return (this._capabilities?.languages||[]).map(row=>{
      const code=String(row?.code||"").toLowerCase();
      return code?`<option value="${this._escape(code)}" ${code===this._ingredientCatalogLanguage?"selected":""}>${this._escape(this._languageName(code))} (${this._escape(code.toUpperCase())})</option>`:"";
    }).join("");
  }

  _houseKey(row){return row?.key?`k:${row.key}`:`n:${String(row?.name||"").trim().toLocaleLowerCase()}`;}

  _renderHouseChoices(c){
    const select=c.querySelector("#houseCatalog");
    if(!select)return;
    const q=String(this._houseFilter||"").trim().toLocaleLowerCase();
    const selected=new Set(this._houseIngredients.map(row=>this._houseKey(row)));
    const rows=this._ingredientCatalog.filter(row=>!selected.has(this._houseKey(row))&&(!q||String(row.name||"").toLocaleLowerCase().includes(q))).slice(0,100);
    select.innerHTML=rows.map((row,index)=>`<option value="${index}" data-key="${this._escape(row.key||"")}" data-name="${this._escape(row.name||"")}">${this._escape(row.name||"")}</option>`).join("");
    select._cook4meRows=rows;
  }

  _renderProfile(c){
    this._ensureHouseState();
    const e=this._entry()||{}; const p=e.profile||{}; const join=x=>(x||[]).join("\n"); const habits=e.habitTerms||[];
    const defaultLanguage=String(this._capabilities?.ingredientCatalogLanguage||this._capabilities?.deviceCatalogLanguage||"de").toLowerCase();
    if(!this._ingredientCatalogLanguage)this._ingredientCatalogLanguage=defaultLanguage;
    if(!this._ingredientCatalog.length&&!this._ingredientCatalogLoading)queueMicrotask(()=>void this._loadIngredientCatalog(this._ingredientCatalogLanguage));
    const house=this._houseIngredients.length
      ?`<div class="chips">${this._houseIngredients.map((row,index)=>`<span class="chip">${this._escape(row.name)} <button type="button" class="house-remove" data-index="${index}" title="${this._escape(this._t("removeHouse"))}" style="border:0;background:transparent;color:inherit;cursor:pointer">×</button></span>`).join("")}</div>`
      :`<div class="muted">${this._escape(this._t("houseEmpty"))}</div>`;
    c.innerHTML=`<section class="card"><div class="formgrid">
      <div class="field"><label>${this._t("diet")}</label><select id="diet"><option value="omnivore">${this._t("omnivore")}</option><option value="pescatarian">${this._t("pescatarian")}</option><option value="vegetarian">${this._t("vegetarian")}</option><option value="vegan">${this._t("vegan")}</option></select></div><div></div>
      <div class="field wide"><label>${this._escape(this._t("pantry"))}</label>${house}</div>
      <div class="field"><label>${this._escape(this._t("ingredientCatalog"))}</label><select id="ingredientLanguage">${this._catalogLanguageOptions()}</select></div>
      <div class="field"><label>${this._escape(this._t("ingredientSearch"))}</label><input id="houseSearch" value="${this._escape(this._houseFilter)}" placeholder="${this._escape(this._t("ingredientSearch"))}"></div>
      <div class="field wide"><select id="houseCatalog" size="8" style="min-height:180px"></select><button id="houseAdd" type="button" class="btn secondary" style="margin-top:8px">${this._escape(this._t("addHouse"))}</button>${this._ingredientCatalogLoading?`<span class="muted">${this._escape(this._t("catalogLoading"))}</span>`:""}</div>
      <div class="field"><label>${this._t("allergies")}</label><textarea id="allergies">${this._escape(join(p.allergies))}</textarea></div>
      <div class="field"><label>${this._t("avoid")}</label><textarea id="avoid">${this._escape(join(p.avoid))}</textarea></div>
      <div class="field wide"><label>${this._t("preferences")}</label><textarea id="preferences">${this._escape(join(p.preferences))}</textarea></div>
      ${habits.length?`<div class="field wide"><label>${this._t("learnedHabits")}</label><div class="chips">${habits.map(x=>`<span class="chip">♥ ${this._escape(x)}</span>`).join("")}</div></div>`:""}
      </div><button id="profileSave" class="btn">${this._t("save")}</button></section>`;
    c.querySelector("#diet").value=p.diet||"omnivore";
    this._renderHouseChoices(c);
    c.querySelector("#houseSearch")?.addEventListener("input",event=>{this._houseFilter=String(event.target.value||"");this._renderHouseChoices(c);});
    c.querySelector("#ingredientLanguage")?.addEventListener("change",event=>{this._houseFilter="";void this._loadIngredientCatalog(String(event.target.value||defaultLanguage));});
    c.querySelector("#houseAdd")?.addEventListener("click",()=>{
      const select=c.querySelector("#houseCatalog"); const rows=select?._cook4meRows||[]; const row=rows[Number(select?.value)]; if(!row)return;
      if(!this._houseIngredients.some(item=>this._houseKey(item)===this._houseKey(row)))this._houseIngredients.push({...row});
      this._renderProfile(c);
    });
    c.querySelectorAll(".house-remove").forEach(button=>button.addEventListener("click",()=>{this._houseIngredients.splice(Number(button.dataset.index),1);this._renderProfile(c);}));
    c.querySelector("#profileSave")?.addEventListener("click",()=>this._saveProfile());
  }

  async _saveProfile(){
    const c=this.shadowRoot.getElementById("content");
    const profile={
      diet:c.querySelector("#diet")?.value||"omnivore",
      houseIngredients:this._houseIngredients.map(row=>({...row})),
      pantry:this._houseIngredients.map(row=>row.name),
      allergies:this._splitList(c.querySelector("#allergies")?.value||""),
      avoid:this._splitList(c.querySelector("#avoid")?.value||""),
      preferences:this._splitList(c.querySelector("#preferences")?.value||""),
    };
    try{
      await this._api("cook4me/profile_save",{entry_id:this._entryId,profile});
      await this._loadOverview(true); this._houseEntryId=""; this._results=[]; this._recommendations=[];
      this._message(this._t("save")); this._renderTab();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  _missingIngredientObjects(recipe){
    const missing=(recipe?.match?.missingIngredients||[]).map(value=>String(value).trim()).filter(Boolean);
    const missingNames=new Set(missing.map(value=>value.toLocaleLowerCase()));
    const missingKeys=new Set((recipe?.match?.ingredientAvailability||[]).filter(row=>row?.missing&&row?.key).map(row=>String(row.key)));
    const rows=(recipe?.ingredients||[]).filter(item=>{
      if(typeof item==="string")return missingNames.has(String(item).trim().toLocaleLowerCase());
      const key=String(item?.foodKey||item?.key||""); const name=this._ingredientName(item).toLocaleLowerCase();
      return (key&&missingKeys.has(key))||missingNames.has(name);
    });
    return rows.length?rows:missing;
  }

  async _addShopping(ingredients){
    if(!ingredients?.length)return;
    try{
      const result=await this._api("cook4me/v11/shopping_add",{entry_id:this._entryId,ingredients});
      this._message(result?.count?`${this._t("shoppingAdded")}: ${result.count}`:this._t("shoppingNothing"));
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  _recipeCard(recipe,custom=false){
    let html=super._recipeCard(recipe,custom);
    const missing=this._missingIngredientObjects(recipe);
    if(missing.length){
      const button=`<button class="btn secondary" data-action="shop-missing">🛒 ${this._escape(this._t("addMissing"))} (${missing.length})</button>`;
      html=html.replace('<div class="actions">',`<div class="actions">${button}`);
    }
    return html;
  }

  _bindCards(container,items,custom=false){
    super._bindCards(container,items,custom);
    container.querySelectorAll(".recipe").forEach((card,index)=>{
      card.querySelector('[data-action="shop-missing"]')?.addEventListener("click",event=>{event.stopPropagation();void this._addShopping(this._missingIngredientObjects(items[index]));});
    });
  }

  _ingredientAvailability(recipe,item){
    const key=String(item?.foodKey||item?.key||""); const name=this._ingredientName(item).toLocaleLowerCase();
    return (recipe?.match?.ingredientAvailability||[]).find(row=>(key&&String(row?.key||"")===key)||String(row?.name||"").toLocaleLowerCase()===name)||null;
  }

  _detailHtml(recipe){
    let html=super._detailHtml(recipe); if(!html||!recipe)return html;
    const marker=`<h3>${this._t("ingredients")}</h3>`;
    const start=html.indexOf(marker); if(start<0)return html;
    const end=html.indexOf(`</div><div><h3>${this._t("steps")}</h3>`,start); if(end<0)return html;
    const ingredients=(recipe.ingredients||[]).filter(item=>this._ingredientText(item));
    const missing=this._missingIngredientObjects(recipe);
    const list=ingredients.length?`<div class="ingredient-status-list">${ingredients.map((item,index)=>{
      const availability=this._ingredientAvailability(recipe,item); const missingItem=availability?.status==="missing"||missing.some(row=>this._ingredientName(row).toLocaleLowerCase()===this._ingredientName(item).toLocaleLowerCase());
      const status=availability?.status==="at_home"?`<span class="chip ok">✓ ${this._escape(this._t("atHome"))}</span>`:availability?.status==="staple"?`<span class="chip">${this._escape(this._t("staple"))}</span>`:"";
      const button=missingItem?`<button class="btn secondary" data-action="shop-one" data-index="${index}" style="padding:6px 9px;min-height:34px">🛒 ${this._escape(this._t("addOne"))}</button>`:"";
      return `<div style="display:flex;gap:8px;align-items:center;justify-content:space-between;border-bottom:1px solid var(--divider-color);padding:8px 0"><span>${this._escape(this._ingredientText(item))}</span><span style="display:flex;gap:6px;align-items:center">${status}${button}</span></div>`;
    }).join("")}</div>${missing.length?`<button class="btn secondary" data-action="shop-all-missing" style="margin-top:10px">🛒 ${this._escape(this._t("addMissing"))} (${missing.length})</button>`:""}`:`<div class="muted">—</div>`;
    return html.slice(0,start+marker.length)+list+html.slice(end);
  }

  _bindDetail(container){
    super._bindDetail(container); const recipe=this._opened; if(!recipe)return;
    const ingredients=(recipe.ingredients||[]).filter(item=>this._ingredientText(item));
    container.querySelectorAll('#recipeDetail [data-action="shop-one"]').forEach(button=>button.addEventListener("click",()=>{const item=ingredients[Number(button.dataset.index)];if(item)void this._addShopping([item]);}));
    container.querySelector('#recipeDetail [data-action="shop-all-missing"]')?.addEventListener("click",()=>void this._addShopping(this._missingIngredientObjects(recipe)));
  }
}

customElements.define("cook4me-recipe-hub-panel-v11",Cook4MeRecipeHubPanelV11);
