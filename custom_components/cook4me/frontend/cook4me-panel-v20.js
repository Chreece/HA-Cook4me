import "./cook4me-panel-v19.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v19");

const TEXT = {
  en:{bestBefore:"Best before",bestBeforeHelp:"Optional. When restocking the same ingredient, the earliest known date is kept."},
  de:{bestBefore:"Mindestens haltbar bis",bestBeforeHelp:"Optional. Beim Nachfüllen derselben Zutat bleibt das früheste bekannte Datum erhalten."},
  el:{bestBefore:"Ανάλωση κατά προτίμηση πριν από",bestBeforeHelp:"Προαιρετικό. Σε νέα προσθήκη του ίδιου υλικού διατηρείται η νωρίτερη γνωστή ημερομηνία."},
};

class Cook4MeRecipeHubPanelV20 extends BasePanel {
  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _stockText(row){
    const base=super._stockText(row);
    return row?.bestBefore?`${base} · ${this._t("bestBefore")}: ${row.bestBefore}`:base;
  }

  _inventoryRowsHtml(){
    if(!this._houseIngredients.length)return `<div class="muted">${this._escape(this._t("houseEmpty"))}</div>`;
    return this._houseIngredients.map((row,index)=>{
      const unlimited=Boolean(row.unlimited);
      const amount=row.quantity===undefined||row.quantity===null?"":row.quantity;
      return `<div data-stock-row="${index}" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:8px;align-items:end;padding:10px 0;border-bottom:1px solid var(--divider-color)">
        <div style="min-width:180px"><strong>${this._escape(row.name||"")}</strong> <span class="muted">(${this._escape(this._stockText(row))})</span></div>
        <div class="field"><label>${this._escape(this._t("amount"))}</label><input data-stock-amount type="number" min="0" step="any" value="${this._escape(amount)}" ${unlimited?"disabled":""}></div>
        <div class="field"><label>${this._escape(this._t("unit"))}</label><input data-stock-unit value="${this._escape(row.unit||"")}" list="cook4meStockUnits"></div>
        <div class="field"><label>${this._escape(this._t("bestBefore"))}</label><input data-stock-best-before type="date" value="${this._escape(row.bestBefore||"")}"></div>
        <label style="display:flex;align-items:center;gap:6px;min-height:42px"><input data-stock-unlimited type="checkbox" ${unlimited?"checked":""}> ${this._escape(this._t("unlimited"))}</label>
        <div style="display:flex;gap:6px"><button class="btn secondary" data-stock-save>${this._escape(this._t("updateStock"))}</button><button class="btn secondary" data-stock-remove>${this._escape(this._t("removeStock"))}</button></div>
      </div>`;
    }).join("");
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
            entry_id:this._entryId,
            identity:this._stockIdentity(row),
            ...(amount?.value!==""?{quantity:amount.value}:{}),
            unit:String(container.querySelector("[data-stock-unit]")?.value||""),
            unlimited:Boolean(unlimited?.checked),
            best_before:String(container.querySelector("[data-stock-best-before]")?.value||""),
          });
          this._houseIngredients=result?.houseIngredients||[];
          this._syncEntryProfile();
          this._renderInventoryOnly(c);
          this._message(this._t("stockUpdated"));
        }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
      });
      container.querySelector("[data-stock-remove]")?.addEventListener("click",async()=>{
        try{
          const result=await this._api("cook4me/v14/inventory_remove",{entry_id:this._entryId,identity:this._stockIdentity(row)});
          this._houseIngredients=result?.houseIngredients||[];
          this._syncEntryProfile();
          this._renderInventoryOnly(c);
          this._message(this._t("stockUpdated"));
        }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
      });
    });
  }

  _renderProfile(c){
    super._renderProfile(c);
    const unlimited=c.querySelector("#stockAddUnlimited");
    const unlimitedField=unlimited?.closest(".field");
    if(unlimitedField&&!c.querySelector("#stockAddBestBefore")){
      const dateField=document.createElement("div");
      dateField.className="field";
      dateField.innerHTML=`<label>${this._escape(this._t("bestBefore"))}</label><input id="stockAddBestBefore" type="date"><div class="muted">${this._escape(this._t("bestBeforeHelp"))}</div>`;
      unlimitedField.parentNode?.insertBefore(dateField,unlimitedField);
    }

    // Replace the v16 add button to remove its amount-only listener, while
    // preserving every other profile/scanner binding installed by the base UI.
    const oldButton=c.querySelector("#houseAdd");
    if(!oldButton)return;
    const button=oldButton.cloneNode(true);
    oldButton.replaceWith(button);
    const amount=c.querySelector("#stockAddAmount");
    button.addEventListener("click",async()=>{
      const select=c.querySelector("#houseCatalog");
      const rows=select?._cook4meRows||[];
      const row=rows[Number(select?.value)];
      if(!row)return;
      const scrollTop=select.scrollTop;
      const selectedValue=select.value;
      try{
        const result=await this._api("cook4me/v14/inventory_add",{
          entry_id:this._entryId,
          ingredient:row,
          ...(amount?.value!==""?{quantity:amount.value}:{}),
          unit:String(c.querySelector("#stockAddUnit")?.value||""),
          unlimited:Boolean(unlimited?.checked),
          best_before:String(c.querySelector("#stockAddBestBefore")?.value||""),
        });
        this._houseIngredients=result?.houseIngredients||[];
        this._syncEntryProfile();
        this._renderInventoryOnly(c);
        select.value=selectedValue;
        select.scrollTop=scrollTop;
        if(amount)amount.value="";
        const bestBefore=c.querySelector("#stockAddBestBefore");if(bestBefore)bestBefore.value="";
        this._message(this._t("stockUpdated"));
      }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
    });
  }

  _scannerResultHtml(){
    const html=super._scannerResultHtml();
    if(this._scannerResult?.status!=="needs_mapping")return html;
    const marker='<button id="scanMapAdd"';
    const pos=html.indexOf(marker);
    if(pos<0)return html;
    const dateField=`<div class="field" style="margin-top:10px"><label>${this._escape(this._t("bestBefore"))}</label><input id="scanBestBefore" type="date"><div class="muted">${this._escape(this._t("bestBeforeHelp"))}</div></div>`;
    return `${html.slice(0,pos)}${dateField}${html.slice(pos)}`;
  }

  _bindScannerMapping(c){
    // Let v19 bind search, suggestions and selector behavior first.
    super._bindScannerMapping(c);
    const oldButton=c.querySelector("#scanMapAdd");
    if(!oldButton)return;
    const button=oldButton.cloneNode(true);
    oldButton.replaceWith(button);
    button.addEventListener("click",async()=>{
      const result=this._scannerResult;if(!result?.barcode)return;
      const ingredient=this._selectedScanIngredient(c);
      if(!ingredient?.name){this._scannerStatus=this._t("invalidIngredient");this._renderScannerResult(c);return;}
      const quantity=String(c.querySelector("#scanPackageAmount")?.value||"").trim();
      const unit=String(c.querySelector("#scanPackageUnit")?.value||"").trim();
      const bestBefore=String(c.querySelector("#scanBestBefore")?.value||"");
      if(!quantity)return;
      this._scannerBusy=true;
      this._scannerStatus=this._t("lookingUp");
      this._renderScannerResult(c);
      try{
        const mapped=await this._api("cook4me/v15/barcode_map_add",{
          entry_id:this._entryId,
          barcode:String(result.barcode),
          ingredient,
          quantity,
          unit,
          best_before:bestBefore,
          product_name:String(result.product?.productName||result.product?.name||""),
          brand:String(result.product?.brand||""),
        });
        this._houseIngredients=mapped?.houseIngredients||[];
        this._syncEntryProfile();
        this._renderInventoryOnly(c);
        this._scannerResult=mapped;
        this._scannerStatus=this._t("scannedAdded");
        navigator.vibrate?.(80);
        this._scanIngredientFilter="";
        this._scanSelectedIngredient="";
      }catch(e){this._scannerStatus=`${this._t("error")}: ${e.message||e}`;}
      finally{this._scannerBusy=false;this._renderScannerResult(c);}
      if(this._scannerOpen&&this._nativeBarcodeScannerAvailable()&&!this._nativeScannerActive){
        await this._startNativeBarcodeScanner(c);
      }
    });
  }
}

customElements.define("cook4me-recipe-hub-panel-v20",Cook4MeRecipeHubPanelV20);
