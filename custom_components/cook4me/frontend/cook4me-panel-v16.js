import "./cook4me-panel-v15.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v15");

const TEXT = {
  en:{
    stock:"House stock",stockHelp:"Select an ingredient, enter what you bought, or mark it unlimited. Adding an ingredient you already have increases its current amount.",
    amount:"Amount",unit:"Unit",unlimited:"Unlimited (∞)",addStock:"Add to house stock",updateStock:"Update",removeStock:"Remove",
    stockUnknown:"amount not set",consumeTitle:"Confirm consumed ingredients",consumeHelp:"The recipe finished successfully. Each ingredient defaults to Yes and to the amount required by the recipe. Edit anything before confirming.",
    consume:"Consumed",confirmConsumption:"Confirm deductions",nothingConsumed:"Nothing was consumed",recipeAmount:"Recipe amount",currentStock:"Current stock",
    stockUpdated:"House stock updated",consumptionUpdated:"House stock deductions confirmed",
  },
  de:{
    stock:"Vorrat zu Hause",stockHelp:"Zutat auswählen und gekaufte Menge eintragen oder als unbegrenzt markieren. Bei einer bereits vorhandenen Zutat wird die Menge addiert.",
    amount:"Menge",unit:"Einheit",unlimited:"Unbegrenzt (∞)",addStock:"Zum Vorrat hinzufügen",updateStock:"Aktualisieren",removeStock:"Entfernen",
    stockUnknown:"Menge nicht gesetzt",consumeTitle:"Verbrauchte Zutaten bestätigen",consumeHelp:"Das Rezept wurde erfolgreich beendet. Jede Zutat steht standardmäßig auf Ja und auf der im Rezept benötigten Menge. Vor dem Bestätigen kann alles geändert werden.",
    consume:"Verbraucht",confirmConsumption:"Abzüge bestätigen",nothingConsumed:"Nichts wurde verbraucht",recipeAmount:"Rezeptmenge",currentStock:"Aktueller Vorrat",
    stockUpdated:"Vorrat aktualisiert",consumptionUpdated:"Vorratsabzüge bestätigt",
  },
  el:{
    stock:"Απόθεμα στο σπίτι",stockHelp:"Επίλεξε υλικό και βάλε την ποσότητα που αγόρασες ή όρισέ το ως απεριόριστο. Αν υπάρχει ήδη, η νέα ποσότητα προστίθεται στην υπάρχουσα.",
    amount:"Ποσότητα",unit:"Μονάδα",unlimited:"Απεριόριστο (∞)",addStock:"Προσθήκη στο απόθεμα",updateStock:"Ενημέρωση",removeStock:"Αφαίρεση",
    stockUnknown:"χωρίς ποσότητα",consumeTitle:"Επιβεβαίωση κατανάλωσης υλικών",consumeHelp:"Η συνταγή ολοκληρώθηκε επιτυχώς. Κάθε υλικό είναι προεπιλεγμένο σε Ναι και στην ποσότητα που απαιτούσε η συνταγή. Μπορείς να αλλάξεις κάθε ποσότητα πριν την επιβεβαίωση.",
    consume:"Καταναλώθηκε",confirmConsumption:"Επιβεβαίωση αφαίρεσης",nothingConsumed:"Δεν καταναλώθηκε τίποτα",recipeAmount:"Ποσότητα συνταγής",currentStock:"Τρέχον απόθεμα",
    stockUpdated:"Το απόθεμα ενημερώθηκε",consumptionUpdated:"Οι αφαιρέσεις από το απόθεμα επιβεβαιώθηκαν",
  },
};

class Cook4MeRecipeHubPanelV16 extends BasePanel {
  constructor(){
    super();
    this._pendingConsumption=null;
    this._inventoryLoadedEntry="";
    this._inventoryLoading=false;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _ensureHouseState(){
    if(this._houseEntryId===this._entryId)return;
    const profile=this._entry()?.profile||{};
    const rows=Array.isArray(profile.houseIngredients)&&profile.houseIngredients.length
      ?profile.houseIngredients
      :(profile.pantry||[]).map(name=>({name:String(name)}));
    this._houseIngredients=rows.map(row=>typeof row==="object"&&row?{...row}:{name:String(row||"")}).filter(row=>String(row.name||"").trim());
    this._houseEntryId=this._entryId||"";
    this._ingredientCatalog=[];
    this._ingredientCatalogLanguage="";
    this._pendingConsumption=null;
    this._inventoryLoadedEntry="";
  }

  _stockIdentity(row){return row?.key?`k:${row.key}`:`n:${String(row?.name||"").trim().toLocaleLowerCase()}`;}

  _stockText(row){
    if(row?.unlimited)return "∞";
    if(row?.quantity===undefined||row?.quantity===null||row?.quantity==="")return this._t("stockUnknown");
    const amount=Number(row.quantity);
    const shown=Number.isFinite(amount)?(Number.isInteger(amount)?String(amount):String(Number(amount.toFixed(6)))):String(row.quantity);
    return `${shown}${row?.unit?` ${row.unit}`:""}`;
  }

  _syncEntryProfile(){
    const entry=this._entry();
    if(!entry)return;
    entry.profile={...(entry.profile||{}),houseIngredients:this._houseIngredients.map(row=>({...row})),pantry:this._houseIngredients.map(row=>row.name)};
  }

  async _loadInventoryState(){
    if(!this._entryId||this._inventoryLoading)return;
    this._inventoryLoading=true;
    try{
      const result=await this._api("cook4me/v14/inventory_state",{entry_id:this._entryId});
      this._houseIngredients=Array.isArray(result?.houseIngredients)?result.houseIngredients:[];
      this._pendingConsumption=result?.pendingConsumption||null;
      this._inventoryLoadedEntry=this._entryId;
      this._syncEntryProfile();
      if(this._tab==="profile")this._renderTab();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    finally{this._inventoryLoading=false;}
  }

  _renderHouseChoices(c){
    const select=c.querySelector("#houseCatalog");
    if(!select)return;
    const q=String(this._houseFilter||"").trim().toLocaleLowerCase();
    const rows=this._ingredientCatalog.filter(row=>!q||String(row.name||"").toLocaleLowerCase().includes(q));
    select.innerHTML=rows.map((row,index)=>`<option value="${index}">${this._escape(row.name||"")}</option>`).join("");
    select._cook4meRows=rows;
  }

  _inventoryRowsHtml(){
    if(!this._houseIngredients.length)return `<div class="muted">${this._escape(this._t("houseEmpty"))}</div>`;
    return this._houseIngredients.map((row,index)=>{
      const unlimited=Boolean(row.unlimited);
      const amount=row.quantity===undefined||row.quantity===null?"":row.quantity;
      return `<div data-stock-row="${index}" style="display:grid;grid-template-columns:minmax(180px,1fr) minmax(90px,140px) minmax(80px,130px) auto auto;gap:8px;align-items:end;padding:10px 0;border-bottom:1px solid var(--divider-color)">
        <div><strong>${this._escape(row.name||"")}</strong> <span class="muted">(${this._escape(this._stockText(row))})</span></div>
        <div class="field"><label>${this._escape(this._t("amount"))}</label><input data-stock-amount type="number" min="0" step="any" value="${this._escape(amount)}" ${unlimited?"disabled":""}></div>
        <div class="field"><label>${this._escape(this._t("unit"))}</label><input data-stock-unit value="${this._escape(row.unit||"")}" list="cook4meStockUnits"></div>
        <label style="display:flex;align-items:center;gap:6px;min-height:42px"><input data-stock-unlimited type="checkbox" ${unlimited?"checked":""}> ${this._escape(this._t("unlimited"))}</label>
        <div style="display:flex;gap:6px"><button class="btn secondary" data-stock-save>${this._escape(this._t("updateStock"))}</button><button class="btn secondary" data-stock-remove>${this._escape(this._t("removeStock"))}</button></div>
      </div>`;
    }).join("");
  }

  _renderInventoryOnly(c){
    const target=c.querySelector("#houseInventoryRows");
    if(!target)return;
    target.innerHTML=this._inventoryRowsHtml();
    this._bindInventoryRows(c);
  }

  _bindInventoryRows(c){
    c.querySelectorAll("[data-stock-row]").forEach(container=>{
      const index=Number(container.dataset.stockRow); const row=this._houseIngredients[index]; if(!row)return;
      const unlimited=container.querySelector("[data-stock-unlimited]");
      const amount=container.querySelector("[data-stock-amount]");
      unlimited?.addEventListener("change",()=>{if(amount)amount.disabled=Boolean(unlimited.checked);});
      container.querySelector("[data-stock-save]")?.addEventListener("click",async()=>{
        try{
          const result=await this._api("cook4me/v14/inventory_update",{
            entry_id:this._entryId,identity:this._stockIdentity(row),
            ...(amount?.value!==""?{quantity:amount.value}:{}),
            unit:String(container.querySelector("[data-stock-unit]")?.value||""),
            unlimited:Boolean(unlimited?.checked),
          });
          this._houseIngredients=result?.houseIngredients||[]; this._syncEntryProfile(); this._renderInventoryOnly(c); this._message(this._t("stockUpdated"));
        }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
      });
      container.querySelector("[data-stock-remove]")?.addEventListener("click",async()=>{
        try{
          const result=await this._api("cook4me/v14/inventory_remove",{entry_id:this._entryId,identity:this._stockIdentity(row)});
          this._houseIngredients=result?.houseIngredients||[]; this._syncEntryProfile(); this._renderInventoryOnly(c); this._message(this._t("stockUpdated"));
        }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
      });
    });
  }

  _pendingHtml(){
    const pending=this._pendingConsumption;
    if(!pending?.id)return "";
    const rows=(pending.ingredients||[]).map((row,index)=>{
      const unlimited=Boolean(row.stockUnlimited);
      const amount=row.quantity===undefined||row.quantity===null?"":row.quantity;
      return `<div data-consume-row="${index}" style="display:grid;grid-template-columns:auto minmax(180px,1fr) minmax(90px,140px) minmax(80px,130px);gap:8px;align-items:end;padding:9px 0;border-bottom:1px solid var(--divider-color)">
        <label style="display:flex;align-items:center;gap:6px;min-height:42px"><input data-consume-check type="checkbox" checked ${unlimited?"disabled":""}> ${this._escape(this._t("consume"))}</label>
        <div><strong>${this._escape(row.name||"")}</strong><div class="muted">${this._escape(this._t("currentStock"))}: ${this._escape(unlimited?"∞":`${row.stockQuantity??"?"}${row.stockUnit?` ${row.stockUnit}`:""}`)}</div></div>
        <div class="field"><label>${this._escape(this._t("recipeAmount"))}</label><input data-consume-amount type="number" min="0" step="any" value="${this._escape(amount)}" ${unlimited?"disabled":""}></div>
        <div class="field"><label>${this._escape(this._t("unit"))}</label><input data-consume-unit value="${this._escape(row.unit||"")}" list="cook4meStockUnits" ${unlimited?"disabled":""}></div>
      </div>`;
    }).join("");
    return `<section class="card" style="border-left:4px solid var(--primary-color)"><h2 style="margin-top:0">${this._escape(this._t("consumeTitle"))}</h2><div class="muted"><strong>${this._escape(pending.recipeTitle||"")}</strong> · ${this._escape(this._t("consumeHelp"))}</div><div style="margin-top:10px">${rows}</div><div class="toolbar" style="margin-top:12px"><button id="confirmConsumption" class="btn">${this._escape(this._t("confirmConsumption"))}</button><button id="clearConsumption" class="btn secondary">${this._escape(this._t("nothingConsumed"))}</button></div></section>`;
  }

  _bindPending(c){
    const pending=this._pendingConsumption; if(!pending?.id)return;
    c.querySelector("#confirmConsumption")?.addEventListener("click",async()=>{
      const ingredients=[];
      c.querySelectorAll("[data-consume-row]").forEach(container=>{
        const index=Number(container.dataset.consumeRow); const row=pending.ingredients[index]; if(!row)return;
        const unlimited=Boolean(row.stockUnlimited);
        ingredients.push({identity:row.identity,key:row.key,name:row.name,consume:unlimited?true:Boolean(container.querySelector("[data-consume-check]")?.checked),quantity:container.querySelector("[data-consume-amount]")?.value||null,unit:String(container.querySelector("[data-consume-unit]")?.value||"")});
      });
      try{
        const result=await this._api("cook4me/v14/consumption_confirm",{entry_id:this._entryId,pending_id:pending.id,ingredients});
        this._houseIngredients=result?.houseIngredients||result?.profile?.houseIngredients||[]; this._pendingConsumption=null; this._syncEntryProfile(); this._message(this._t("consumptionUpdated")); this._renderProfile(c);
      }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    });
    c.querySelector("#clearConsumption")?.addEventListener("click",async()=>{
      try{
        await this._api("cook4me/v14/consumption_clear",{entry_id:this._entryId,pending_id:pending.id});
        this._pendingConsumption=null; this._renderProfile(c);
      }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    });
  }

  _renderProfile(c){
    this._ensureHouseState();
    const e=this._entry()||{}; const p=e.profile||{}; const join=x=>(x||[]).join("\n"); const habits=e.habitTerms||[];
    const defaultLanguage=String(this._capabilities?.ingredientCatalogLanguage||this._capabilities?.deviceCatalogLanguage||"de").toLowerCase();
    if(!this._ingredientCatalogLanguage)this._ingredientCatalogLanguage=defaultLanguage;
    if(!this._ingredientCatalog.length&&!this._ingredientCatalogLoading)queueMicrotask(()=>void this._loadIngredientCatalog(this._ingredientCatalogLanguage));
    if(this._inventoryLoadedEntry!==this._entryId&&!this._inventoryLoading)queueMicrotask(()=>void this._loadInventoryState());
    c.innerHTML=`${this._pendingHtml()}<section class="card"><div class="formgrid">
      <div class="field"><label>${this._t("diet")}</label><select id="diet"><option value="omnivore">${this._t("omnivore")}</option><option value="pescatarian">${this._t("pescatarian")}</option><option value="vegetarian">${this._t("vegetarian")}</option><option value="vegan">${this._t("vegan")}</option></select></div><div></div>
      <div class="field wide"><details><summary style="cursor:pointer;font-weight:600">${this._escape(this._t("stock"))} (${this._houseIngredients.length})</summary><div class="muted" style="margin:8px 0">${this._escape(this._t("stockHelp"))}</div><div id="houseInventoryRows">${this._inventoryRowsHtml()}</div></details></div>
      <div class="field"><label>${this._escape(this._t("ingredientCatalog"))}</label><select id="ingredientLanguage">${this._catalogLanguageOptions()}</select></div>
      <div class="field"><label>${this._escape(this._t("ingredientSearch"))}</label><input id="houseSearch" value="${this._escape(this._houseFilter)}" placeholder="${this._escape(this._t("ingredientSearch"))}"></div>
      <div class="field wide"><select id="houseCatalog" size="8" style="min-height:180px"></select></div>
      <div class="field"><label>${this._escape(this._t("amount"))}</label><input id="stockAddAmount" type="number" min="0" step="any"></div>
      <div class="field"><label>${this._escape(this._t("unit"))}</label><input id="stockAddUnit" list="cook4meStockUnits"><datalist id="cook4meStockUnits"><option value="g"><option value="kg"><option value="ml"><option value="l"><option value="pcs"></datalist></div>
      <div class="field wide"><label style="display:flex;align-items:center;gap:8px"><input id="stockAddUnlimited" type="checkbox"> ${this._escape(this._t("unlimited"))}</label><button id="houseAdd" type="button" class="btn secondary" style="margin-top:8px">${this._escape(this._t("addStock"))}</button>${this._ingredientCatalogLoading?`<span class="muted">${this._escape(this._t("catalogLoading"))}</span>`:""}</div>
      <div class="field"><label>${this._t("allergies")}</label><textarea id="allergies">${this._escape(join(p.allergies))}</textarea></div>
      <div class="field"><label>${this._t("avoid")}</label><textarea id="avoid">${this._escape(join(p.avoid))}</textarea></div>
      <div class="field wide"><label>${this._t("preferences")}</label><textarea id="preferences">${this._escape(join(p.preferences))}</textarea></div>
      ${habits.length?`<div class="field wide"><label>${this._t("learnedHabits")}</label><div class="chips">${habits.map(x=>`<span class="chip">♥ ${this._escape(x)}</span>`).join("")}</div></div>`:""}
      </div><button id="profileSave" class="btn">${this._t("save")}</button></section>`;
    c.querySelector("#diet").value=p.diet||"omnivore";
    this._renderHouseChoices(c); this._bindInventoryRows(c); this._bindPending(c);
    c.querySelector("#houseSearch")?.addEventListener("input",event=>{this._houseFilter=String(event.target.value||"");this._renderHouseChoices(c);});
    c.querySelector("#ingredientLanguage")?.addEventListener("change",event=>{this._houseFilter="";void this._loadIngredientCatalog(String(event.target.value||defaultLanguage));});
    const unlimited=c.querySelector("#stockAddUnlimited"); const amount=c.querySelector("#stockAddAmount");
    unlimited?.addEventListener("change",()=>{if(amount)amount.disabled=Boolean(unlimited.checked);});
    c.querySelector("#houseCatalog")?.addEventListener("change",event=>{
      const rows=event.target?._cook4meRows||[]; const selected=rows[Number(event.target.value)]; if(!selected)return;
      const existing=this._houseIngredients.find(row=>this._stockIdentity(row)===this._stockIdentity(selected));
      if(existing&&c.querySelector("#stockAddUnit")&&!c.querySelector("#stockAddUnit").value)c.querySelector("#stockAddUnit").value=existing.unit||"";
    });
    c.querySelector("#houseAdd")?.addEventListener("click",async()=>{
      const select=c.querySelector("#houseCatalog"); const rows=select?._cook4meRows||[]; const row=rows[Number(select?.value)]; if(!row)return;
      const scrollTop=select.scrollTop; const selectedValue=select.value;
      try{
        const result=await this._api("cook4me/v14/inventory_add",{entry_id:this._entryId,ingredient:row,...(amount?.value!==""?{quantity:amount.value}:{}),unit:String(c.querySelector("#stockAddUnit")?.value||""),unlimited:Boolean(unlimited?.checked)});
        this._houseIngredients=result?.houseIngredients||[]; this._syncEntryProfile(); this._renderInventoryOnly(c); select.value=selectedValue; select.scrollTop=scrollTop; if(amount)amount.value=""; this._message(this._t("stockUpdated"));
      }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    });
    c.querySelector("#profileSave")?.addEventListener("click",async()=>{
      const profile={diet:c.querySelector("#diet")?.value||"omnivore",allergies:this._splitList(c.querySelector("#allergies")?.value||""),avoid:this._splitList(c.querySelector("#avoid")?.value||""),preferences:this._splitList(c.querySelector("#preferences")?.value||"")};
      try{await this._api("cook4me/profile_save",{entry_id:this._entryId,profile});const entry=this._entry();if(entry)entry.profile={...(entry.profile||{}),...profile};this._message(this._t("save"));}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    });
  }
}

customElements.define("cook4me-recipe-hub-panel-v16",Cook4MeRecipeHubPanelV16);
