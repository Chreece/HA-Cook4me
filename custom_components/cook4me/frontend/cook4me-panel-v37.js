import "./cook4me-panel-v36.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v36");

class Cook4MeRecipeHubPanelV37 extends BasePanel{
  async _api(type,data={}){
    const mapped=type==="cook4me/v18/today_suggest"?"cook4me/v19/today_suggest":type;
    return super._api(mapped,data);
  }

  _ensureV37Styles(){
    if(this.shadowRoot?.getElementById("cook4meV37Styles"))return;
    const style=document.createElement("style");
    style.id="cook4meV37Styles";
    style.textContent=`
      .top.rx-unified-top{
        display:grid!important;
        grid-template-columns:minmax(0,1fr) auto!important;
        align-items:center!important;
        gap:8px!important;
        width:100%!important;
        padding:10px 12px!important;
        border:1px solid var(--divider-color)!important;
        border-radius:18px!important;
        background:var(--card-background-color)!important;
        overflow:visible!important;
      }
      .top.rx-unified-top>#status.card{
        min-width:0!important;
        padding:0!important;
        border:0!important;
        border-radius:0!important;
        background:transparent!important;
      }
      .top.rx-unified-top>#status .status{gap:11px!important}
      .top.rx-unified-top>#status .pot{font-size:27px!important}
      .top.rx-unified-top>#status .status-title{font-size:19px!important}
      .top.rx-unified-top>.toolbar{
        display:flex!important;
        flex:0 0 auto!important;
        align-items:center!important;
        gap:6px!important;
        flex-wrap:nowrap!important;
        min-width:0!important;
      }
      .top.rx-unified-top #entrySelect{
        width:auto!important;
        max-width:180px!important;
        min-width:110px!important;
        min-height:40px!important;
        padding:7px 30px 7px 9px!important;
      }
      #cook4meUiLanguageControl{
        display:block!important;
        flex:0 0 40px!important;
        width:40px!important;
        height:40px!important;
        min-width:40px!important;
        margin:0!important;
        padding:0!important;
        border:0!important;
        border-radius:12px!important;
        background:transparent!important;
      }
      .rx-icon-select{
        position:relative;
        display:grid;
        place-items:center;
        width:40px;
        height:40px;
        border:1px solid var(--divider-color);
        border-radius:12px;
        background:var(--secondary-background-color);
        color:var(--primary-text-color);
        cursor:pointer;
        overflow:hidden;
      }
      .rx-icon-select:hover,.rx-icon-button:hover{border-color:var(--primary-color)!important}
      .rx-icon-select ha-icon{--mdc-icon-size:21px;color:var(--primary-color)}
      .rx-icon-select select{
        position:absolute!important;
        inset:0!important;
        width:100%!important;
        height:100%!important;
        min-width:0!important;
        min-height:0!important;
        padding:0!important;
        margin:0!important;
        opacity:0!important;
        cursor:pointer!important;
      }
      .rx-icon-button{
        display:grid!important;
        place-items:center!important;
        flex:0 0 40px!important;
        width:40px!important;
        min-width:40px!important;
        height:40px!important;
        min-height:40px!important;
        padding:0!important;
        border-radius:12px!important;
      }
      .rx-icon-button ha-icon{--mdc-icon-size:21px}

      .rx-today-planner.rx-today-compact{
        width:100%!important;
        min-width:0!important;
        padding:10px!important;
        overflow:visible!important;
      }
      .rx-today-row{
        display:grid!important;
        grid-template-columns:repeat(auto-fit,minmax(145px,1fr))!important;
        align-items:end!important;
        gap:8px!important;
        width:100%!important;
        min-width:0!important;
        padding:0!important;
        overflow:visible!important;
      }
      .rx-today-row>.field,
      .rx-today-row>.rx-today-picker,
      .rx-today-row>.rx-today-actions{
        width:100%!important;
        min-width:0!important;
        max-width:none!important;
        flex:none!important;
      }
      .rx-today-row>.field label{
        display:block;
        margin:0 0 4px!important;
        font-size:11px!important;
        line-height:1.15!important;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
      }
      .rx-today-row>.field input,
      .rx-today-row>.field select{
        width:100%!important;
        min-width:0!important;
        min-height:40px!important;
        height:40px!important;
        padding:7px 9px!important;
      }
      .rx-today-picker{
        position:relative!important;
        min-width:0!important;
      }
      .rx-today-picker>summary,
      .rx-today-row>details.rx-advanced>summary{
        width:100%!important;
        min-width:0!important;
        min-height:40px!important;
        height:40px!important;
        padding:7px 9px!important;
        border-radius:10px!important;
        white-space:nowrap!important;
        overflow:hidden!important;
      }
      .rx-today-picker>summary span,
      .rx-today-row>details.rx-advanced>summary span{
        overflow:hidden;
        text-overflow:ellipsis;
        white-space:nowrap;
      }
      .rx-today-picker>summary b{margin-left:auto!important;flex:0 0 auto}
      .rx-today-picker-body,
      .rx-today-row>details.rx-advanced>.rx-advanced-content{
        box-sizing:border-box!important;
        min-width:0!important;
        max-width:calc(100vw - 24px)!important;
        margin:0!important;
        border:1px solid var(--divider-color)!important;
        border-radius:13px!important;
        background:var(--card-background-color)!important;
        box-shadow:0 14px 40px rgba(0,0,0,.30)!important;
        overflow:auto!important;
      }
      .rx-today-picker-body #todayIngredients{
        width:100%!important;
        min-width:0!important;
        min-height:210px!important;
        max-height:42vh!important;
      }
      .rx-today-actions{
        display:grid!important;
        grid-template-columns:minmax(0,1fr) auto!important;
        align-items:end!important;
        gap:6px!important;
        margin:0!important;
      }
      .rx-today-actions .btn{
        min-width:0!important;
        min-height:40px!important;
        height:40px!important;
        padding:7px 10px!important;
        white-space:nowrap!important;
        overflow:hidden!important;
        text-overflow:ellipsis!important;
      }
      .rx-today-actions .btn.secondary{width:42px!important;padding:0!important;font-size:0!important}
      .rx-today-actions .btn.secondary ha-icon{--mdc-icon-size:20px;font-size:initial}
      .rx-today-planner .rx-plan-summary{display:none!important}

      @media(max-width:900px){
        .rx-today-row{grid-template-columns:repeat(4,minmax(0,1fr))!important}
      }
      @media(max-width:680px){
        .top.rx-unified-top{padding:8px 9px!important}
        .top.rx-unified-top>#status .status-title{font-size:17px!important}
        .top.rx-unified-top>#status .muted{font-size:11px!important}
        .top.rx-unified-top #entrySelect{max-width:120px!important;min-width:90px!important}
        .rx-today-row{grid-template-columns:repeat(2,minmax(0,1fr))!important}
      }
      @media(max-width:390px){
        .rx-today-row{grid-template-columns:1fr!important}
      }
    `;
    this.shadowRoot.appendChild(style);
  }

  _compactTopBar(){
    const top=this.shadowRoot?.querySelector(".top");
    if(!top)return;
    top.classList.add("rx-unified-top");
    const toolbar=top.querySelector(":scope > .toolbar");
    const control=this.shadowRoot?.getElementById("cook4meUiLanguageControl");
    const select=control?.querySelector("#cook4meUiLanguage");
    const refresh=this.shadowRoot?.getElementById("refresh");

    if(control&&select&&!control.dataset.v37Compact){
      control.dataset.v37Compact="1";
      const trigger=document.createElement("label");
      trigger.className="rx-icon-select";
      trigger.title=this._t("interfaceLanguage");
      trigger.setAttribute("aria-label",this._t("interfaceLanguage"));
      const icon=document.createElement("ha-icon");
      icon.setAttribute("icon","mdi:web");
      select.setAttribute("aria-label",this._t("interfaceLanguage"));
      select.title=this._t("interfaceLanguage");
      trigger.append(icon,select);
      control.replaceChildren(trigger);
    }
    if(toolbar&&control&&control.parentElement!==toolbar){
      toolbar.insertBefore(control,refresh||toolbar.firstChild);
    }
    if(refresh){
      refresh.classList.add("rx-icon-button");
      refresh.title=this._t("refresh");
      refresh.setAttribute("aria-label",this._t("refresh"));
      if(!refresh.querySelector("ha-icon")){
        const icon=document.createElement("ha-icon");
        icon.setAttribute("icon","mdi:refresh");
        refresh.replaceChildren(icon);
      }
    }
  }

  _renderUiLanguageControl(){
    super._renderUiLanguageControl();
    this._ensureV37Styles();
    this._compactTopBar();
  }

  _renderShell(){
    super._renderShell();
    this._ensureV37Styles();
    this._compactTopBar();
  }

  _positionTodayPopup(details){
    const body=details?.querySelector(":scope > .rx-today-picker-body")||details?.querySelector(":scope > .rx-advanced-content");
    if(!body)return;
    if(!details.open){
      for(const key of ["position","left","top","right","bottom","width","maxHeight","zIndex"])body.style.removeProperty(key);
      return;
    }
    requestAnimationFrame(()=>{
      if(!details.open)return;
      const rect=details.getBoundingClientRect();
      const viewportWidth=Math.max(280,window.innerWidth||document.documentElement.clientWidth||1024);
      const viewportHeight=Math.max(360,window.innerHeight||document.documentElement.clientHeight||768);
      const width=Math.min(520,viewportWidth-24);
      const left=Math.max(12,Math.min(rect.left,viewportWidth-width-12));
      const below=viewportHeight-rect.bottom-12;
      const above=rect.top-12;
      const maxHeight=Math.max(180,Math.min(460,Math.max(below,above)-8));
      let top=rect.bottom+6;
      if(below<220&&above>below)top=Math.max(12,rect.top-maxHeight-6);
      body.style.position="fixed";
      body.style.left=`${left}px`;
      body.style.top=`${top}px`;
      body.style.width=`${width}px`;
      body.style.maxHeight=`${maxHeight}px`;
      body.style.zIndex="13000";
    });
  }

  _compactTodayPlanner(c){
    const planner=c.querySelector(".rx-today-planner");
    if(!planner||planner.dataset.cook4meV37Compact)return;
    planner.dataset.cook4meV37Compact="1";
    planner.classList.add("rx-today-compact");

    const form=planner.querySelector(":scope > .formgrid");
    const mealBlock=this._todayTopChild(planner,planner.querySelector("[data-today-meal-type]"));
    const languageBlock=this._todayTopChild(planner,planner.querySelector("[data-today-language]"));
    const ingredientBlock=this._todayTopChild(planner,planner.querySelector("#todayIngredients"));
    const advanced=planner.querySelector(":scope > details.rx-advanced");
    const actions=planner.querySelector(":scope > .toolbar");

    const row=document.createElement("div");
    row.className="rx-today-row";
    if(form)[...form.children].forEach(child=>row.appendChild(child));

    const mealPicker=this._todayPicker(mealBlock,this._t("mealTypes"),"silverware-fork-knife");
    if(mealPicker){mealPicker.dataset.rxPicker="meals";row.appendChild(mealPicker);}
    const languagePicker=this._todayPicker(languageBlock,this._t("catalogLanguages"),"translate");
    if(languagePicker){languagePicker.dataset.rxPicker="languages";row.appendChild(languagePicker);}
    const ingredientPicker=this._todayPicker(ingredientBlock,this._t("preferredIngredients"),"food-apple-outline");
    if(ingredientPicker){ingredientPicker.dataset.rxPicker="ingredients";row.appendChild(ingredientPicker);}

    if(advanced){advanced.classList.add("rx-today-picker");row.appendChild(advanced);}
    if(actions){
      actions.classList.add("rx-today-actions");
      actions.style.marginTop="0";
      const reset=actions.querySelector("#todayReset");
      if(reset){
        reset.title=this._t("resetToday");
        reset.setAttribute("aria-label",this._t("resetToday"));
        const icon=reset.querySelector("ha-icon");
        if(icon)reset.replaceChildren(icon);
      }
      row.appendChild(actions);
    }

    planner.replaceChildren(row);
    row.querySelectorAll("details").forEach(details=>details.addEventListener("toggle",()=>{
      if(details.open)row.querySelectorAll("details[open]").forEach(other=>{if(other!==details)other.open=false;});
      this._positionTodayPopup(details);
    }));
    row.addEventListener("change",()=>this._updateTodayPickerCounts(c));
    this._updateTodayPickerCounts(c);
  }

  _professionalizeSoon(){
    super._professionalizeSoon();
    queueMicrotask(()=>{
      const planner=this.shadowRoot?.querySelector(".rx-today-planner");
      planner?.querySelector(".rx-plan-summary")?.remove();
    });
  }
}

customElements.define("cook4me-recipe-hub-panel-v37",Cook4MeRecipeHubPanelV37);
