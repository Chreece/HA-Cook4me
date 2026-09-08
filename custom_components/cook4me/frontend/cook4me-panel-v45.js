import "./cook4me-panel-v44.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v44");

const TEXT={
  en:{currency:"Currency",currencyAuto:"Auto",currencyHelp:"Display currency. Auto follows the Cook4Me UI language.",fxRates:"ECB reference rates",fxStale:"cached FX rates",fxUnavailable:"Some currencies could not be converted",costHelp:"Costs are shown in your selected currency using cached online reference rates. Exact purchase prices remain stored in their original currency for audit. No density/unit conversions are guessed."},
  de:{currency:"Währung",currencyAuto:"Auto",currencyHelp:"Anzeigewährung. Auto folgt der Cook4Me-Oberflächensprache.",fxRates:"EZB-Referenzkurse",fxStale:"zwischengespeicherte Wechselkurse",fxUnavailable:"Einige Währungen konnten nicht umgerechnet werden",costHelp:"Kosten werden mit zwischengespeicherten Online-Referenzkursen in der gewählten Währung angezeigt. Exakte Kaufpreise bleiben zur Nachvollziehbarkeit in ihrer Originalwährung gespeichert. Einheiten/Dichten werden nicht geraten."},
  el:{currency:"Νόμισμα",currencyAuto:"Αυτόματο",currencyHelp:"Νόμισμα εμφάνισης. Το Αυτόματο ακολουθεί τη γλώσσα του Cook4Me UI.",fxRates:"Ισοτιμίες αναφοράς ΕΚΤ",fxStale:"αποθηκευμένες ισοτιμίες",fxUnavailable:"Κάποια νομίσματα δεν μπόρεσαν να μετατραπούν",costHelp:"Τα κόστη εμφανίζονται στο επιλεγμένο νόμισμα με αποθηκευμένες online ισοτιμίες αναφοράς. Οι ακριβείς τιμές αγοράς διατηρούνται στο αρχικό τους νόμισμα για ιχνηλασιμότητα. Δεν γίνονται υποθέσεις για μονάδες ή πυκνότητα."},
};

const SYMBOL={EUR:"€",GBP:"£",USD:"$",JPY:"¥",CNY:"¥",KRW:"₩",PLN:"zł",CZK:"Kč",HUF:"Ft",RON:"lei",SEK:"kr",NOK:"kr",DKK:"kr",TRY:"₺",CHF:"CHF",AUD:"A$",CAD:"C$",NZD:"NZ$",AED:"د.إ"};

class Cook4MeRecipeHubPanelV45 extends BasePanel{
  constructor(){
    super();
    this._currencyState=null;
    this._currencyStateEntry="";
    this._currencyBusy=false;
  }

  _t(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||super._t(key);}

  _ensureCurrencyStyles(){
    if(this.shadowRoot?.getElementById("cook4meCurrencyV45"))return;
    const style=document.createElement("style");
    style.id="cook4meCurrencyV45";
    style.textContent=`
      #cook4meCurrencyControl{display:flex;align-items:center;height:40px;min-width:0}
      #cook4meCurrencyControl .rx-currency-field{position:relative;display:flex;align-items:center;height:40px;min-width:74px;border:1px solid var(--divider-color);border-radius:12px;background:var(--secondary-background-color);overflow:hidden}
      #cook4meCurrencyControl ha-icon{position:absolute;left:8px;--mdc-icon-size:18px;color:var(--primary-color);pointer-events:none;z-index:1}
      #cook4meCurrencyControl select{width:100%;height:40px;min-height:40px;border:0!important;background:transparent!important;padding:6px 7px 6px 29px!important;font-weight:650;cursor:pointer}
      #cook4meCurrencyControl select:focus{outline:1px solid var(--primary-color);outline-offset:-1px}

      /* v32 originally clipped rx-advanced. v36 later moves it into a popup row,
         so clipping makes More filters appear to do nothing even though <details>
         has opened. The popup parent must be allowed to paint outside itself. */
      .rx-today-row>details.rx-advanced{overflow:visible!important;position:relative!important}
      .rx-today-row>details.rx-advanced[open]{z-index:65!important}
      .rx-today-row>details.rx-advanced[open]>.rx-advanced-content{display:grid!important;visibility:visible!important;opacity:1!important;pointer-events:auto!important}
      .rx-today-row>details.rx-today-picker[open]{z-index:65!important}

      @media(max-width:520px){#cook4meCurrencyControl .rx-currency-field{min-width:66px}#cook4meCurrencyControl select{padding-right:2px!important;font-size:12px}}
    `;
    this.shadowRoot.appendChild(style);
  }

  _currencyLabel(code){const c=String(code||"").toUpperCase();return `${SYMBOL[c]?`${SYMBOL[c]} `:""}${c}`.trim();}

  _ensureCurrencyControl(){
    const root=this.shadowRoot;if(!root)return;
    this._ensureCurrencyStyles();
    const language=root.getElementById("cook4meUiLanguageControl");
    const toolbar=language?.parentElement||root.querySelector(".top>.toolbar");
    if(!toolbar)return;
    let control=root.getElementById("cook4meCurrencyControl");
    if(!control){
      control=document.createElement("div");
      control.id="cook4meCurrencyControl";
      control.innerHTML=`<div class="rx-currency-field"><ha-icon icon="mdi:currency-eur"></ha-icon><select id="cook4meCurrency"></select></div>`;
      if(language?.parentElement===toolbar)language.after(control);else toolbar.insertBefore(control,root.getElementById("refresh")||null);
      control.querySelector("select")?.addEventListener("change",event=>void this._setCurrency(String(event.target.value||"")));
    }else if(language?.parentElement===toolbar&&control.previousElementSibling!==language){
      language.after(control);
    }
    const select=control.querySelector("#cook4meCurrency");
    if(!select)return;
    const state=this._currencyState||{};
    const current=String(state.currency||this._weekState?.costSettings?.currency||"").toUpperCase();
    const defaults=String(state.defaultCurrency||current||"EUR").toUpperCase();
    const currencies=[...new Set([...(state.currencies||[]),current,defaults].map(x=>String(x||"").toUpperCase()).filter(Boolean))].sort();
    const autoLabel=`${this._t("currencyAuto")} · ${this._currencyLabel(defaults)}`;
    select.innerHTML=`<option value="__auto__" ${state.mode!=="fixed"?"selected":""}>${this._escape(autoLabel)}</option>${currencies.map(code=>`<option value="${this._escape(code)}" ${state.mode==="fixed"&&code===current?"selected":""}>${this._escape(this._currencyLabel(code))}</option>`).join("")}`;
    const rateDate=String(state.rateDate||"");
    const title=`${this._t("currencyHelp")}${rateDate?` · ${this._t("fxRates")}: ${rateDate}`:""}${state.stale?` · ${this._t("fxStale")}`:""}`;
    select.title=title;select.setAttribute("aria-label",this._t("currency"));

    const languageSelect=root.getElementById("cook4meUiLanguage");
    if(languageSelect&&!languageSelect.dataset.currencyV45Bound){
      languageSelect.dataset.currencyV45Bound="1";
      languageSelect.addEventListener("change",()=>{
        if(this._currencyState?.mode!=="fixed")setTimeout(()=>void this._setCurrency("__auto__"),0);
      });
    }
  }

  async _loadCurrencyState(force=false){
    const entry=String(this._entryId||"");
    if(!entry||this._currencyBusy||(!force&&this._currencyState&&this._currencyStateEntry===entry))return;
    this._currencyBusy=true;
    try{
      const result=await this._api("cook4me/v21/currency_state",{entry_id:entry,language:this._langCode(),refresh:false});
      if(result?.currency){
        this._currencyState=result;
        this._currencyStateEntry=entry;
        if(this._weekState?.costSettings)this._weekState.costSettings.currency=result.currency;
      }
    }catch(_e){}
    finally{this._currencyBusy=false;this._ensureCurrencyControl();if(this._tab==="week"&&this._currencyState)this._renderTab();}
  }

  async _setCurrency(value){
    if(!this._entryId)return;
    try{
      const auto=value==="__auto__";
      const result=await this._api("cook4me/v21/currency_set",{
        entry_id:this._entryId,
        language:this._langCode(),
        mode:auto?"auto":"fixed",
        currency:auto?"":String(value||"").toUpperCase(),
      });
      if(result?.currency){
        this._currencyState=result;this._currencyStateEntry=String(this._entryId||"");
        if(this._weekState?.costSettings)this._weekState.costSettings.currency=result.currency;
      }
      if(this._weekStateEntry===String(this._entryId||""))await this._loadWeekState();
      this._ensureCurrencyControl();this._renderTab();
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  _convertMoney(values){
    if(!values||typeof values!=="object")return null;
    const state=this._currencyState||{};
    const target=String(state.currency||this._weekState?.costSettings?.currency||"").toUpperCase();
    const rates=state.rates&&typeof state.rates==="object"?state.rates:{};
    if(!target)return null;
    let total=0,convertedCount=0;const unconverted={};
    for(const [rawCurrency,rawAmount] of Object.entries(values)){
      const source=String(rawCurrency||"").toUpperCase(),amount=Number(rawAmount);
      if(!source||!Number.isFinite(amount))continue;
      if(source===target){total+=amount;convertedCount++;continue;}
      const fromRate=source==="EUR"?1:Number(rates[source]);
      const toRate=target==="EUR"?1:Number(rates[target]);
      if(!Number.isFinite(fromRate)||fromRate<=0||!Number.isFinite(toRate)||toRate<=0){unconverted[source]=(unconverted[source]||0)+amount;continue;}
      total+=(amount/fromRate)*toRate;convertedCount++;
    }
    return {target,total,convertedCount,unconverted};
  }

  _money(values){
    const result=this._convertMoney(values);
    if(!result||!result.convertedCount)return super._money(values);
    const primary=`${Number(result.total).toLocaleString(this._langCode(),{minimumFractionDigits:2,maximumFractionDigits:2})} ${result.target}`;
    const rest=Object.keys(result.unconverted).length?super._money(result.unconverted):"";
    return rest?`${primary} + ${rest}`:primary;
  }

  _updateTodayBulkButton(c,group){
    const button=c.querySelector(`[data-today-bulk="${group}"]`);if(!button)return;
    let all=false;
    if(group==="ingredients"){
      const options=[...(c.querySelector("#todayIngredients")?.options||[])];
      all=options.length>0&&options.every(option=>option.selected);
    }else{
      const selector=group==="meals"?"[data-today-meal-type]":"[data-today-language]";
      const rows=[...c.querySelectorAll(selector)];
      all=rows.length>0&&rows.every(row=>row.checked);
    }
    button.innerHTML=`<ha-icon icon="mdi:${all?"checkbox-multiple-blank-outline":"checkbox-multiple-marked-outline"}"></ha-icon><span>${this._escape(this._t(all?"deselectAll":"selectAll"))}</span>`;
  }

  _toggleTodayBulk(c,group){
    /* Do not call _renderToday here. Replacing the planner DOM destroys the
       currently-open <details> popup, which made Select/Deselect all close it. */
    if(group==="ingredients"){
      const select=c.querySelector("#todayIngredients");if(!select)return;
      const options=[...select.options],all=options.length>0&&options.every(option=>option.selected);
      options.forEach(option=>{option.selected=!all;});
    }else{
      const selector=group==="meals"?"[data-today-meal-type]":"[data-today-language]";
      const rows=[...c.querySelectorAll(selector)],all=rows.length>0&&rows.every(row=>row.checked);
      rows.forEach(row=>{
        row.checked=!all;
        row.closest(".rx-choice-card")?.classList.toggle("selected",!all);
      });
    }
    this._rememberTodayFromUi(c);
    this._updateTodayPickerCounts?.(c);
    this._updateTodayBulkButton(c,group);
    this._updateTodaySummary?.(c.querySelector(".rx-today-planner"));
  }

  _renderShell(){
    super._renderShell();this._ensureCurrencyControl();queueMicrotask(()=>void this._loadCurrencyState(false));
  }

  _renderTabs(){
    super._renderTabs();this._ensureCurrencyControl();
    if(this._entryId&&this._currencyStateEntry!==String(this._entryId||""))queueMicrotask(()=>void this._loadCurrencyState(false));
  }

  _renderToday(c){
    super._renderToday(c);
    this._ensureCurrencyStyles();
  }

  _renderWeek(c){
    super._renderWeek(c);
    const input=c.querySelector("#costCurrency");
    if(input&&this._currencyState?.currency){input.value=this._currencyState.currency;input.readOnly=true;input.title=this._t("currencyHelp");}
    if(this._currencyState?.rateDate){
      const costSettings=c.querySelector("#saveCostSettings")?.closest("section.card")||c.querySelector("#saveCostSettings")?.parentElement;
      costSettings?.insertAdjacentHTML("beforeend",`<div data-fx-status class="muted" style="margin-top:7px">${this._escape(this._t("fxRates"))}: ${this._escape(this._currencyState.rateDate)}${this._currencyState.stale?` · ${this._escape(this._t("fxStale"))}`:""}</div>`);
    }
  }
}

customElements.define("cook4me-recipe-hub-panel-v45",Cook4MeRecipeHubPanelV45);
