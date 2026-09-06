import "./cook4me-panel-v11.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v11");

const TEXT = {
  en:{
    shopping:"Shopping list",houseForRecipes:"What I have in my house",houseForRecipesHelp:"Select the ingredients you already have. Changes are saved immediately and used by recipe recommendations.",
    addSelectedHouse:"Add selected to house",houseUpdated:"House ingredients updated",shoppingEmpty:"Your Home Assistant Shopping List is empty.",shoppingUnavailable:"Home Assistant Shopping List is not available.",
    shoppingInput:"Add an item…",shoppingAdd:"Add item",shoppingRefresh:"Refresh",shoppingClearCompleted:"Clear completed",shoppingRemove:"Remove",shoppingActive:"to buy",shoppingCompleted:"completed",
  },
  de:{
    shopping:"Einkaufsliste",houseForRecipes:"Was ich zu Hause habe",houseForRecipesHelp:"Wähle die Zutaten aus, die du bereits zu Hause hast. Änderungen werden sofort gespeichert und für Rezeptempfehlungen verwendet.",
    addSelectedHouse:"Auswahl zu Hause hinzufügen",houseUpdated:"Zutaten zu Hause aktualisiert",shoppingEmpty:"Deine Home-Assistant-Einkaufsliste ist leer.",shoppingUnavailable:"Die Home-Assistant-Einkaufsliste ist nicht verfügbar.",
    shoppingInput:"Artikel hinzufügen…",shoppingAdd:"Hinzufügen",shoppingRefresh:"Aktualisieren",shoppingClearCompleted:"Erledigte löschen",shoppingRemove:"Entfernen",shoppingActive:"einzukaufen",shoppingCompleted:"erledigt",
  },
  el:{
    shopping:"Λίστα αγορών",houseForRecipes:"Τι έχω στο σπίτι",houseForRecipesHelp:"Επίλεξε τα υλικά που έχεις ήδη στο σπίτι. Οι αλλαγές αποθηκεύονται αμέσως και χρησιμοποιούνται στις προτάσεις συνταγών.",
    addSelectedHouse:"Προσθήκη επιλεγμένων στο σπίτι",houseUpdated:"Τα υλικά στο σπίτι ενημερώθηκαν",shoppingEmpty:"Η λίστα αγορών του Home Assistant είναι κενή.",shoppingUnavailable:"Η λίστα αγορών του Home Assistant δεν είναι διαθέσιμη.",
    shoppingInput:"Προσθήκη είδους…",shoppingAdd:"Προσθήκη",shoppingRefresh:"Ανανέωση",shoppingClearCompleted:"Διαγραφή ολοκληρωμένων",shoppingRemove:"Αφαίρεση",shoppingActive:"για αγορά",shoppingCompleted:"ολοκληρωμένα",
  },
};

class Cook4MeRecipeHubPanelV12 extends BasePanel {
  constructor(){
    super();
    this._shoppingItems=[];
    this._shoppingEntityId="";
    this._shoppingAvailable=null;
    this._shoppingLoading=false;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  async _loadCapabilities(){
    await super._loadCapabilities();
    const tab=String(this._capabilities?.preferences?.lastTab||"");
    if(tab==="shopping"&&this._tab!=="shopping"){
      this._tab="shopping";
      this._uiPreferences.lastTab="shopping";
      this._renderTabs();
      this._renderTab();
    }
  }

  _renderTabs(){
    super._renderTabs();
    const tabs=this.shadowRoot?.getElementById("tabs");
    if(!tabs||tabs.querySelector('[data-tab="shopping"]'))return;
    const button=document.createElement("button");
    button.className=`tab ${this._tab==="shopping"?"active":""}`;
    button.dataset.tab="shopping";
    button.textContent=this._t("shopping");
    button.addEventListener("click",()=>{
      this._tab="shopping";
      this._opened=null;
      this._uiPreferences.lastTab="shopping";
      this._schedulePreferenceSave();
      this._renderTabs();
      this._renderTab();
    });
    tabs.appendChild(button);
  }

  _renderTab(){
    if(this._tab==="shopping"){
      const c=this.shadowRoot?.getElementById("content");
      if(c)this._renderShopping(c);
      return;
    }
    super._renderTab();
  }

  async _loadIngredientCatalog(language=null,refresh=false){
    await super._loadIngredientCatalog(language,refresh);
    if(this._tab==="recommend")this._renderTab();
  }

  _recommendHouseRows(){
    const q=String(this._houseFilter||"").trim().toLocaleLowerCase();
    const selected=new Set(this._houseIngredients.map(row=>this._houseKey(row)));
    return this._ingredientCatalog
      .filter(row=>!selected.has(this._houseKey(row))&&(!q||String(row.name||"").toLocaleLowerCase().includes(q)))
      .slice(0,150);
  }

  _renderRecommendHouseChoices(c){
    const select=c.querySelector("#recommendHouseCatalog");
    if(!select)return;
    const rows=this._recommendHouseRows();
    select.innerHTML=rows.map((row,index)=>`<option value="${index}">${this._escape(row.name||"")}</option>`).join("");
    select._cook4meRows=rows;
  }

  _recommendHouseEditorHtml(){
    const defaultLanguage=String(this._capabilities?.ingredientCatalogLanguage||this._capabilities?.deviceCatalogLanguage||"de").toLowerCase();
    if(!this._ingredientCatalogLanguage)this._ingredientCatalogLanguage=defaultLanguage;
    const house=this._houseIngredients.length
      ?`<div class="chips" style="margin:8px 0 12px">${this._houseIngredients.map((row,index)=>`<span class="chip">${this._escape(row.name)} <button type="button" data-recommend-house-remove="${index}" title="${this._escape(this._t("removeHouse"))}" style="border:0;background:transparent;color:inherit;cursor:pointer">×</button></span>`).join("")}</div>`
      :`<div class="muted" style="margin:8px 0 12px">${this._escape(this._t("houseEmpty"))}</div>`;
    return `<div style="border-top:1px solid var(--divider-color);margin-top:14px;padding-top:14px">
      <h3 style="margin:0 0 4px">${this._escape(this._t("houseForRecipes"))}</h3>
      <div class="muted" style="margin-bottom:10px">${this._escape(this._t("houseForRecipesHelp"))}</div>
      ${house}
      <div class="toolbar" style="align-items:end">
        <div class="field" style="min-width:220px"><label>${this._escape(this._t("ingredientCatalog"))}</label><select id="recommendIngredientLanguage">${this._catalogLanguageOptions()}</select></div>
        <div class="field grow"><label>${this._escape(this._t("ingredientSearch"))}</label><input id="recommendHouseSearch" value="${this._escape(this._houseFilter)}" placeholder="${this._escape(this._t("ingredientSearch"))}"></div>
      </div>
      <div class="field" style="margin-top:8px"><select id="recommendHouseCatalog" multiple size="7" style="min-height:170px"></select></div>
      <div class="toolbar" style="margin-top:8px;align-items:center"><button id="recommendHouseAdd" type="button" class="btn secondary">${this._escape(this._t("addSelectedHouse"))}</button>${this._ingredientCatalogLoading?`<span class="muted">${this._escape(this._t("catalogLoading"))}</span>`:""}</div>
    </div>`;
  }

  async _persistRecommendHouse(){
    const profile=await this._api("cook4me/profile_save",{
      entry_id:this._entryId,
      profile:{
        houseIngredients:this._houseIngredients.map(row=>({...row})),
        pantry:this._houseIngredients.map(row=>row.name),
      },
    });
    const entry=this._entry();
    if(entry&&profile&&typeof profile==="object")entry.profile={...(entry.profile||{}),...profile};
    this._recommendations=[];
  }

  _bindRecommendHouse(c){
    this._renderRecommendHouseChoices(c);
    c.querySelector("#recommendHouseSearch")?.addEventListener("input",event=>{
      this._houseFilter=String(event.target.value||"");
      this._renderRecommendHouseChoices(c);
    });
    c.querySelector("#recommendIngredientLanguage")?.addEventListener("change",event=>{
      this._houseFilter="";
      void this._loadIngredientCatalog(String(event.target.value||""));
    });
    c.querySelector("#recommendHouseAdd")?.addEventListener("click",async()=>{
      const select=c.querySelector("#recommendHouseCatalog");
      const rows=select?._cook4meRows||[];
      const picked=[...(select?.selectedOptions||[])].map(option=>rows[Number(option.value)]).filter(Boolean);
      if(!picked.length)return;
      for(const row of picked){
        if(!this._houseIngredients.some(item=>this._houseKey(item)===this._houseKey(row)))this._houseIngredients.push({...row});
      }
      try{
        await this._persistRecommendHouse();
        this._message(this._t("houseUpdated"));
        this._renderTab();
      }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    });
    c.querySelectorAll("[data-recommend-house-remove]").forEach(button=>button.addEventListener("click",async()=>{
      this._houseIngredients.splice(Number(button.dataset.recommendHouseRemove),1);
      try{
        await this._persistRecommendHouse();
        this._message(this._t("houseUpdated"));
        this._renderTab();
      }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    }));
  }

  _renderRecommend(c){
    this._ensureHouseState();
    const defaultLanguage=String(this._capabilities?.ingredientCatalogLanguage||this._capabilities?.deviceCatalogLanguage||"de").toLowerCase();
    if(!this._ingredientCatalogLanguage)this._ingredientCatalogLanguage=defaultLanguage;
    if(!this._ingredientCatalog.length&&!this._ingredientCatalogLoading)queueMicrotask(()=>void this._loadIngredientCatalog(this._ingredientCatalogLanguage));
    super._renderRecommend(c);
    const section=c.querySelector("section.card");
    if(!section)return;
    const staleNotice=[...section.querySelectorAll(".notice")].find(node=>node.textContent?.trim()===super._t("ingredientsHelp"));
    staleNotice?.remove();
    section.insertAdjacentHTML("beforeend",this._recommendHouseEditorHtml());
    this._bindRecommendHouse(c);
  }

  async _loadShoppingList(silent=false){
    if(!this._entryId||this._shoppingLoading)return;
    this._shoppingLoading=true;
    try{
      const result=await this._api("cook4me/v12/shopping_list",{entry_id:this._entryId});
      this._shoppingAvailable=Boolean(result?.available);
      this._shoppingEntityId=String(result?.entityId||"");
      this._shoppingItems=Array.isArray(result?.items)?result.items:[];
      if(this._tab==="shopping")this._renderTab();
      if(!silent)this._message("");
    }catch(e){
      this._shoppingAvailable=false;
      if(!silent)this._message(`${this._t("error")}: ${e.message||e}`,true);
    }finally{this._shoppingLoading=false;}
  }

  async _shoppingAction(action,uid=""){
    try{
      const result=await this._api("cook4me/v12/shopping_action",{entry_id:this._entryId,action,...(uid?{uid}: {})});
      this._shoppingAvailable=Boolean(result?.available);
      this._shoppingEntityId=String(result?.entityId||"");
      this._shoppingItems=Array.isArray(result?.items)?result.items:[];
      this._renderTab();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  async _addShopping(ingredients){
    if(!ingredients?.length)return;
    try{
      const result=await this._api("cook4me/v11/shopping_add",{entry_id:this._entryId,ingredients});
      this._message(result?.count?`${this._t("shoppingAdded")}: ${result.count}`:this._t("shoppingNothing"));
      this._shoppingAvailable=null;
      if(this._tab==="shopping")await this._loadShoppingList(true);
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  _renderShopping(c){
    if(this._shoppingAvailable===null&&!this._shoppingLoading)queueMicrotask(()=>void this._loadShoppingList(true));
    if(this._shoppingLoading&&this._shoppingAvailable===null){
      c.innerHTML=`<section class="card"><div class="empty">${this._escape(this._t("loading"))}</div></section>`;
      return;
    }
    if(this._shoppingAvailable===false){
      c.innerHTML=`<section class="card"><div class="notice error">${this._escape(this._t("shoppingUnavailable"))}</div></section>`;
      return;
    }
    const active=this._shoppingItems.filter(row=>String(row.status)!=="completed").length;
    const completed=this._shoppingItems.length-active;
    const rows=this._shoppingItems.length?this._shoppingItems.map((row,index)=>{
      const done=String(row.status)==="completed";
      return `<div style="display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;padding:10px 0;border-bottom:1px solid var(--divider-color)">
        <input type="checkbox" data-shopping-toggle="${index}" ${done?"checked":""} style="width:20px;height:20px">
        <span style="${done?"text-decoration:line-through;opacity:.65":""}">${this._escape(row.summary||"")}</span>
        <button class="btn secondary" data-shopping-remove="${index}" style="padding:6px 9px;min-height:34px">${this._escape(this._t("shoppingRemove"))}</button>
      </div>`;
    }).join(""):`<div class="empty">${this._escape(this._t("shoppingEmpty"))}</div>`;
    c.innerHTML=`<section class="card">
      <div class="detail-head"><div><h2 style="margin:0">${this._escape(this._t("shopping"))}</h2><div class="muted">${active} ${this._escape(this._t("shoppingActive"))} · ${completed} ${this._escape(this._t("shoppingCompleted"))}</div></div><button id="shoppingRefresh" class="btn secondary">${this._escape(this._t("shoppingRefresh"))}</button></div>
      <div class="toolbar" style="margin:14px 0"><input id="shoppingManual" class="grow" placeholder="${this._escape(this._t("shoppingInput"))}"><button id="shoppingAddManual" class="btn">${this._escape(this._t("shoppingAdd"))}</button>${completed?`<button id="shoppingClearCompleted" class="btn secondary">${this._escape(this._t("shoppingClearCompleted"))}</button>`:""}</div>
      <div>${rows}</div>
    </section>`;
    c.querySelector("#shoppingRefresh")?.addEventListener("click",()=>void this._loadShoppingList());
    const addManual=async()=>{
      const input=c.querySelector("#shoppingManual"); const value=String(input?.value||"").trim(); if(!value)return;
      await this._addShopping([value]);
      if(input)input.value="";
    };
    c.querySelector("#shoppingAddManual")?.addEventListener("click",()=>void addManual());
    c.querySelector("#shoppingManual")?.addEventListener("keydown",event=>{if(event.key==="Enter")void addManual();});
    c.querySelector("#shoppingClearCompleted")?.addEventListener("click",()=>void this._shoppingAction("clear_completed"));
    c.querySelectorAll("[data-shopping-toggle]").forEach(input=>input.addEventListener("change",()=>{
      const row=this._shoppingItems[Number(input.dataset.shoppingToggle)]; if(row)void this._shoppingAction(input.checked?"complete":"incomplete",String(row.uid||""));
    }));
    c.querySelectorAll("[data-shopping-remove]").forEach(button=>button.addEventListener("click",()=>{
      const row=this._shoppingItems[Number(button.dataset.shoppingRemove)]; if(row)void this._shoppingAction("remove",String(row.uid||""));
    }));
  }
}

customElements.define("cook4me-recipe-hub-panel-v12",Cook4MeRecipeHubPanelV12);
