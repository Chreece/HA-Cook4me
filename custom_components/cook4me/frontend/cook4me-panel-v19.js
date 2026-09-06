import "./cook4me-panel-v18.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v18");

const TEXT = {
  en:{
    suggestedIngredients:"Suggested Cook4Me ingredients",
    searchCatalog:"Search Cook4Me ingredient catalog",
    chooseFromCatalog:"Choose from Cook4Me catalog",
    catalogPickerHelp:"Likely matches are shown first. Search the full catalog if none is correct.",
    catalogPickerLoading:"Loading Cook4Me ingredient catalog…",
    catalogPickerEmpty:"No catalog ingredients match this search.",
    catalogShowing:"catalog matches shown",
  },
  de:{
    suggestedIngredients:"Vorgeschlagene Cook4Me-Zutaten",
    searchCatalog:"Cook4Me-Zutatenkatalog durchsuchen",
    chooseFromCatalog:"Aus dem Cook4Me-Katalog auswählen",
    catalogPickerHelp:"Wahrscheinliche Treffer stehen zuerst. Falls keiner passt, den vollständigen Katalog durchsuchen.",
    catalogPickerLoading:"Cook4Me-Zutatenkatalog wird geladen…",
    catalogPickerEmpty:"Keine Katalogzutat passt zu dieser Suche.",
    catalogShowing:"Katalogtreffer angezeigt",
  },
  el:{
    suggestedIngredients:"Προτεινόμενα υλικά Cook4Me",
    searchCatalog:"Αναζήτηση στον κατάλογο υλικών Cook4Me",
    chooseFromCatalog:"Επιλογή από τον κατάλογο Cook4Me",
    catalogPickerHelp:"Οι πιθανότερες αντιστοιχίσεις εμφανίζονται πρώτες. Αν καμία δεν είναι σωστή, αναζήτησε ολόκληρο τον κατάλογο.",
    catalogPickerLoading:"Φόρτωση καταλόγου υλικών Cook4Me…",
    catalogPickerEmpty:"Δεν βρέθηκε υλικό καταλόγου για αυτή την αναζήτηση.",
    catalogShowing:"αντιστοιχίσεις καταλόγου εμφανίζονται",
  },
};

class Cook4MeRecipeHubPanelV19 extends BasePanel {
  constructor(){
    super();
    this._scanIngredientFilter="";
    this._scanSelectedIngredient="";
    this._scanCatalogLoading=false;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _scanIngredientIdentity(row){
    if(!row)return "";
    return row.key?`k:${String(row.key)}`:`n:${this._catalogVisualKey?this._catalogVisualKey(row.name):String(row.name||"").trim().toLocaleLowerCase()}`;
  }

  _scanNormalize(value){
    if(this._catalogVisualKey)return this._catalogVisualKey(value);
    return String(value||"").normalize("NFKD").replace(/\p{M}/gu,"").toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu," ").trim();
  }

  _scanSuggestions(){
    const out=[]; const seen=new Set();
    for(const item of this._scannerResult?.suggestions||[]){
      const row=item?.ingredient;
      if(!row?.name)continue;
      const id=this._scanIngredientIdentity(row); if(!id||seen.has(id))continue;
      seen.add(id);out.push({...row,_score:item.score,_reason:item.reason});
    }
    return out;
  }

  _scanCatalogRows(){
    const query=this._scanNormalize(this._scanIngredientFilter);
    const suggestions=this._scanSuggestions();
    const out=[]; const seen=new Set();
    const add=row=>{
      if(!row?.name)return;
      const id=this._scanIngredientIdentity(row);if(!id||seen.has(id))return;
      if(query&&!this._scanNormalize(row.name).includes(query))return;
      seen.add(id);out.push(row);
    };
    suggestions.forEach(add);
    for(const row of this._ingredientCatalog||[])add(row);
    return out.slice(0,120);
  }

  async _ensureScanCatalog(c){
    if(this._ingredientCatalog?.length||this._scanCatalogLoading||!this._entryId)return;
    this._scanCatalogLoading=true;
    try{
      const language=this._ingredientCatalogLanguage||this._capabilities?.ingredientCatalogLanguage||this._capabilities?.deviceCatalogLanguage||"de";
      const result=await this._api("cook4me/v11/ingredient_catalog",{entry_id:this._entryId,language:String(language),refresh:false});
      this._ingredientCatalog=Array.isArray(result?.items)?result.items:[];
      this._ingredientCatalogLanguage=String(result?.language||language).toLowerCase();
      if(typeof this._dedupeIngredientCatalog==="function")this._dedupeIngredientCatalog();
    }catch(e){
      this._scannerStatus=`${this._t("error")}: ${e.message||e}`;
    }finally{
      this._scanCatalogLoading=false;
      this._renderScannerResult(c);
    }
  }

  _scanPickerHtml(){
    const suggestions=this._scanSuggestions();
    const suggestionButtons=suggestions.length
      ?`<div style="margin:8px 0"><div class="muted" style="margin-bottom:6px">${this._escape(this._t("suggestedIngredients"))}</div><div class="chips">${suggestions.slice(0,8).map(row=>`<button type="button" class="chip" data-scan-suggestion="${this._escape(this._scanIngredientIdentity(row))}" style="cursor:pointer;border:1px solid var(--divider-color);background:var(--secondary-background-color);color:var(--primary-text-color)">${this._escape(row.name)}</button>`).join("")}</div></div>`:"";
    return `${suggestionButtons}
      <div class="muted" style="margin:6px 0">${this._escape(this._t("catalogPickerHelp"))}</div>
      <div class="field wide"><label>${this._escape(this._t("searchCatalog"))}</label><input id="scanIngredientFilter" value="${this._escape(this._scanIngredientFilter)}" autocomplete="off" placeholder="${this._escape(this._t("searchCatalog"))}"></div>
      <div class="field wide" style="margin-top:8px"><label>${this._escape(this._t("chooseFromCatalog"))}</label><select id="scanIngredientSelect" size="7" style="min-height:180px;width:100%"></select><div id="scanCatalogHint" class="muted" style="margin-top:4px"></div></div>`;
  }

  _scannerResultHtml(){
    const result=this._scannerResult;
    if(!result||result.status!=="needs_mapping")return super._scannerResultHtml();
    const product=result.product||{};
    const first=this._scanSuggestions()[0]||result.mapping?.ingredient||{};
    if(!this._scanSelectedIngredient&&first?.name)this._scanSelectedIngredient=this._scanIngredientIdentity(first);
    const quantity=product.quantity??result.mapping?.quantity??1;
    const unit=String(product.unit||result.mapping?.unit||"pcs");
    const productName=product.productName||product.name||result.mapping?.productName||this._t("unknownProduct");
    const brand=product.brand||result.mapping?.brand||"";
    return `<div class="card" style="padding:12px;margin:0">
      <h3 style="margin:0 0 4px">${this._escape(this._t("mapProduct"))}</h3>
      <div class="muted">${this._escape(this._t("mapHelp"))}</div>
      <div style="margin:10px 0"><strong>${this._escape(this._t("product"))}:</strong> ${this._escape(productName)}${brand?` · ${this._escape(brand)}`:""}<br><span class="muted">${this._escape(result.barcode||"")}${product.rawQuantity?` · ${this._escape(product.rawQuantity)}`:""}</span></div>
      ${this._scanPickerHtml()}
      <div class="formgrid" style="margin-top:10px">
        <div class="field"><label>${this._escape(this._t("packageAmount"))}</label><input id="scanPackageAmount" type="number" min="0" step="any" value="${this._escape(quantity)}"></div>
        <div class="field"><label>${this._escape(this._t("unit"))}</label><input id="scanPackageUnit" value="${this._escape(unit)}" list="cook4meStockUnits"></div>
      </div>
      <button id="scanMapAdd" type="button" class="btn" style="margin-top:8px">${this._escape(this._t("mapAndAdd"))}</button>
    </div>`;
  }

  _renderScanIngredientOptions(c){
    const select=c.querySelector("#scanIngredientSelect");if(!select)return;
    const rows=this._scanCatalogRows();
    select._cook4meRows=rows;
    select.innerHTML=rows.map((row,index)=>`<option value="${index}" ${this._scanIngredientIdentity(row)===this._scanSelectedIngredient?"selected":""}>${this._escape(row.name||"")}</option>`).join("");
    if(this._scanSelectedIngredient&&!rows.some(row=>this._scanIngredientIdentity(row)===this._scanSelectedIngredient)){
      this._scanSelectedIngredient="";
    }
    if(!this._scanSelectedIngredient&&rows.length){
      this._scanSelectedIngredient=this._scanIngredientIdentity(rows[0]);
      select.value="0";
    }
    const hint=c.querySelector("#scanCatalogHint");
    if(hint){
      hint.textContent=this._scanCatalogLoading?this._t("catalogPickerLoading"):(rows.length?`${rows.length} ${this._t("catalogShowing")}`:this._t("catalogPickerEmpty"));
    }
  }

  _selectedScanIngredient(c){
    const select=c.querySelector("#scanIngredientSelect");
    const rows=select?._cook4meRows||[];
    const row=rows[Number(select?.value)];
    return row?{...(row.key?{key:String(row.key)}:{}),name:String(row.name||"")}:null;
  }

  _bindScannerMapping(c){
    this._renderScanIngredientOptions(c);
    c.querySelector("#scanIngredientFilter")?.addEventListener("input",event=>{
      this._scanIngredientFilter=String(event.target.value||"");
      this._scanSelectedIngredient="";
      this._renderScanIngredientOptions(c);
    });
    c.querySelector("#scanIngredientSelect")?.addEventListener("change",event=>{
      const rows=event.target?._cook4meRows||[];
      const row=rows[Number(event.target.value)];
      this._scanSelectedIngredient=this._scanIngredientIdentity(row);
    });
    c.querySelectorAll("[data-scan-suggestion]").forEach(button=>button.addEventListener("click",()=>{
      this._scanSelectedIngredient=String(button.dataset.scanSuggestion||"");
      this._scanIngredientFilter="";
      const input=c.querySelector("#scanIngredientFilter");if(input)input.value="";
      this._renderScanIngredientOptions(c);
    }));
    c.querySelector("#scanMapAdd")?.addEventListener("click",async()=>{
      const result=this._scannerResult;if(!result?.barcode)return;
      const ingredient=this._selectedScanIngredient(c);
      if(!ingredient?.name){this._scannerStatus=this._t("invalidIngredient");this._renderScannerResult(c);return;}
      const quantity=String(c.querySelector("#scanPackageAmount")?.value||"").trim();
      const unit=String(c.querySelector("#scanPackageUnit")?.value||"").trim();
      if(!quantity)return;
      this._scannerBusy=true;this._scannerStatus=this._t("lookingUp");this._renderScannerResult(c);
      try{
        const mapped=await this._api("cook4me/v15/barcode_map_add",{
          entry_id:this._entryId,barcode:String(result.barcode),ingredient,
          quantity,unit,product_name:String(result.product?.productName||result.product?.name||""),brand:String(result.product?.brand||""),
        });
        this._houseIngredients=mapped?.houseIngredients||[];this._syncEntryProfile();this._renderInventoryOnly(c);
        this._scannerResult=mapped;this._scannerStatus=this._t("scannedAdded");navigator.vibrate?.(80);
        this._scanIngredientFilter="";this._scanSelectedIngredient="";
      }catch(e){this._scannerStatus=`${this._t("error")}: ${e.message||e}`;}
      finally{this._scannerBusy=false;this._renderScannerResult(c);}
      if(this._scannerOpen&&this._nativeBarcodeScannerAvailable()&&!this._nativeScannerActive){
        await this._startNativeBarcodeScanner(c);
      }
    });
  }

  async _handleBarcode(code,c){
    const previous=String(this._scannerResult?.barcode||"");
    await super._handleBarcode(code,c);
    if(this._scannerResult?.status!=="needs_mapping")return;
    if(String(this._scannerResult.barcode||"")!==previous){
      this._scanIngredientFilter="";
      const first=this._scanSuggestions()[0];
      this._scanSelectedIngredient=first?this._scanIngredientIdentity(first):"";
    }
    if(!this._ingredientCatalog?.length)void this._ensureScanCatalog(c);
    else this._renderScannerResult(c);
  }
}

customElements.define("cook4me-recipe-hub-panel-v19",Cook4MeRecipeHubPanelV19);
