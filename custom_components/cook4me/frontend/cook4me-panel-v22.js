import "./cook4me-panel-v21.js";

const BasePanel = customElements.get("cook4me-recipe-hub-panel-v21");

const TEXT = {
  en:{
    batches:"Stock batches",batch:"Batch",addBatch:"Add batch",removeBatch:"Remove batch",
    nextBestBefore:"Next best before",batchHelp:"Amounts keep their own best-before dates. Recipe consumption uses the earliest-expiring batch first, then automatically advances to the next date.",
    totalStock:"Total stock",undated:"No best-before date",
  },
  de:{
    batches:"Vorratschargen",batch:"Charge",addBatch:"Charge hinzufügen",removeBatch:"Charge entfernen",
    nextBestBefore:"Nächstes MHD",batchHelp:"Jede Menge behält ihr eigenes MHD. Beim Rezeptverbrauch wird zuerst die Charge mit dem frühesten MHD abgezogen; danach wird automatisch das nächste Datum aktiv.",
    totalStock:"Gesamtvorrat",undated:"Kein MHD",
  },
  el:{
    batches:"Παρτίδες αποθέματος",batch:"Παρτίδα",addBatch:"Προσθήκη παρτίδας",removeBatch:"Αφαίρεση παρτίδας",
    nextBestBefore:"Επόμενη ανάλωση κατά προτίμηση",batchHelp:"Κάθε ποσότητα κρατά τη δική της ημερομηνία. Η κατανάλωση συνταγής αφαιρεί πρώτα την παρτίδα που λήγει νωρίτερα και μετά περνά αυτόματα στην επόμενη ημερομηνία.",
    totalStock:"Συνολικό απόθεμα",undated:"Χωρίς ημερομηνία",
  },
};

class Cook4MeRecipeHubPanelV22 extends BasePanel {
  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _shownNumber(value){
    const number=Number(value);
    if(!Number.isFinite(number))return String(value??"");
    return Number.isInteger(number)?String(number):String(Number(number.toFixed(9)));
  }

  _rowLots(row){
    if(Array.isArray(row?.lots)&&row.lots.length)return row.lots.map(lot=>({...lot}));
    if(row?.quantity!==undefined&&row?.quantity!==null&&row?.quantity!==""){
      return [{quantity:row.quantity,...(row.bestBefore?{bestBefore:row.bestBefore}:{})}];
    }
    return [];
  }

  _stockText(row){
    if(row?.unlimited){
      return row?.bestBefore?`∞ · ${this._t("nextBestBefore")}: ${row.bestBefore}`:"∞";
    }
    const amount=row?.quantity===undefined||row?.quantity===null?this._t("stockUnknown"):this._shownNumber(row.quantity);
    const total=`${amount}${row?.unit?` ${row.unit}`:""}`;
    return row?.bestBefore?`${total} · ${this._t("nextBestBefore")}: ${row.bestBefore}`:total;
  }

  _lotRowHtml(lot,index,unit){
    const amount=lot?.quantity===undefined||lot?.quantity===null?"":lot.quantity;
    return `<div data-stock-lot="${index}" style="display:grid;grid-template-columns:minmax(110px,1fr) minmax(150px,1fr) auto;gap:8px;align-items:end;padding:7px 0">
      <div class="field"><label>${this._escape(this._t("amount"))}${unit?` (${this._escape(unit)})`:""}</label><input data-stock-lot-amount type="number" min="0" step="any" value="${this._escape(amount)}"></div>
      <div class="field"><label>${this._escape(this._t("bestBefore"))}</label><input data-stock-lot-date type="date" value="${this._escape(lot?.bestBefore||"")}"></div>
      <button type="button" class="btn secondary" data-stock-lot-remove style="min-height:42px">${this._escape(this._t("removeBatch"))}</button>
    </div>`;
  }

  _inventoryRowsHtml(){
    if(!this._houseIngredients.length)return `<div class="muted">${this._escape(this._t("houseEmpty"))}</div>`;
    return this._houseIngredients.map((row,index)=>{
      const unlimited=Boolean(row.unlimited);
      const lots=this._rowLots(row);
      const lotsHtml=lots.map((lot,lotIndex)=>this._lotRowHtml(lot,lotIndex,row.unit||"")).join("");
      return `<div data-stock-row="${index}" style="padding:12px 0;border-bottom:1px solid var(--divider-color)">
        <div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start;flex-wrap:wrap">
          <div><strong>${this._escape(row.name||"")}</strong><div class="muted">${this._escape(this._t("totalStock"))}: ${this._escape(this._stockText(row))}</div></div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:end">
            <div class="field" style="min-width:100px"><label>${this._escape(this._t("unit"))}</label><input data-stock-unit value="${this._escape(row.unit||"")}" list="cook4meStockUnits"></div>
            ${unlimited?`<div class="field" style="min-width:160px"><label>${this._escape(this._t("bestBefore"))}</label><input data-stock-unlimited-date type="date" value="${this._escape(row.bestBefore||"")}"></div>`:""}
            <label style="display:flex;align-items:center;gap:6px;min-height:42px"><input data-stock-unlimited type="checkbox" ${unlimited?"checked":""}> ${this._escape(this._t("unlimited"))}</label>
          </div>
        </div>
        <div data-stock-lots-wrap style="margin-top:10px;${unlimited?"display:none":""}">
          <div><strong>${this._escape(this._t("batches"))}</strong></div>
          <div class="muted" style="margin:3px 0 6px">${this._escape(this._t("batchHelp"))}</div>
          <div data-stock-lots>${lotsHtml}</div>
          <button type="button" class="btn secondary" data-stock-lot-add style="margin-top:6px">+ ${this._escape(this._t("addBatch"))}</button>
        </div>
        <div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap"><button class="btn secondary" data-stock-save>${this._escape(this._t("updateStock"))}</button><button class="btn secondary" data-stock-remove>${this._escape(this._t("removeStock"))}</button></div>
      </div>`;
    }).join("");
  }

  _appendLotRow(container,row){
    const holder=container.querySelector("[data-stock-lots]");
    if(!holder)return;
    const index=holder.querySelectorAll("[data-stock-lot]").length;
    holder.insertAdjacentHTML("beforeend",this._lotRowHtml({},index,row?.unit||""));
    this._bindLotRemoveButtons(container);
  }

  _bindLotRemoveButtons(container){
    container.querySelectorAll("[data-stock-lot-remove]").forEach(button=>{
      if(button.dataset.cook4meBound)return;
      button.dataset.cook4meBound="1";
      button.addEventListener("click",()=>button.closest("[data-stock-lot]")?.remove());
    });
  }

  _collectLots(container,row,newUnit){
    const sourceUnit=String(row?.unit||newUnit||"");
    const lots=[];
    container.querySelectorAll("[data-stock-lot]").forEach(lotEl=>{
      const raw=String(lotEl.querySelector("[data-stock-lot-amount]")?.value||"").trim();
      if(!raw)return;
      const amount=Number(raw.replace(",","."));
      if(!Number.isFinite(amount)||amount<=0)return;
      const bestBefore=String(lotEl.querySelector("[data-stock-lot-date]")?.value||"");
      lots.push({quantity:raw,unit:sourceUnit,...(bestBefore?{bestBefore}: {})});
    });
    return lots;
  }

  _bindInventoryRows(c){
    c.querySelectorAll("[data-stock-row]").forEach(container=>{
      const index=Number(container.dataset.stockRow);
      const row=this._houseIngredients[index];
      if(!row)return;
      const unlimited=container.querySelector("[data-stock-unlimited]");
      const lotsWrap=container.querySelector("[data-stock-lots-wrap]");
      unlimited?.addEventListener("change",()=>{
        if(lotsWrap)lotsWrap.style.display=unlimited.checked?"none":"";
      });
      this._bindLotRemoveButtons(container);
      container.querySelector("[data-stock-lot-add]")?.addEventListener("click",()=>this._appendLotRow(container,row));

      container.querySelector("[data-stock-save]")?.addEventListener("click",async()=>{
        try{
          const unit=String(container.querySelector("[data-stock-unit]")?.value||"");
          const isUnlimited=Boolean(unlimited?.checked);
          if(!isUnlimited){
            const lots=this._collectLots(container,row,unit);
            if(!lots.length){
              const result=await this._api("cook4me/v14/inventory_remove",{entry_id:this._entryId,identity:this._stockIdentity(row)});
              this._houseIngredients=result?.houseIngredients||[];
              this._syncEntryProfile();
              this._renderInventoryOnly(c);
              this._message(this._t("stockUpdated"));
              return;
            }
            const result=await this._api("cook4me/v14/inventory_update",{
              entry_id:this._entryId,
              identity:this._stockIdentity(row),
              unit,
              unlimited:false,
              lots,
            });
            this._houseIngredients=result?.houseIngredients||[];
          }else{
            const result=await this._api("cook4me/v14/inventory_update",{
              entry_id:this._entryId,
              identity:this._stockIdentity(row),
              unit,
              unlimited:true,
              best_before:String(container.querySelector("[data-stock-unlimited-date]")?.value||row.bestBefore||""),
            });
            this._houseIngredients=result?.houseIngredients||[];
          }
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
}

customElements.define("cook4me-recipe-hub-panel-v22",Cook4MeRecipeHubPanelV22);
