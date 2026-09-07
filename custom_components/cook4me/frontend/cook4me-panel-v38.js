import "./cook4me-panel-v36.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v36");

class Cook4MeRecipeHubPanelV38 extends BasePanel{
  async _api(type,data={}){
    const mapped=type==="cook4me/v18/today_suggest"?"cook4me/v19/today_suggest":type;
    return super._api(mapped,data);
  }

  _ensureV38Styles(){
    if(this.shadowRoot?.getElementById("cook4meV38Styles"))return;
    const style=document.createElement("style");
    style.id="cook4meV38Styles";
    style.textContent=`
      .top.rx-v38-top{
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
      .top.rx-v38-top>#status.card{
        min-width:0!important;
        padding:0!important;
        border:0!important;
        border-radius:0!important;
        background:transparent!important;
      }
      .top.rx-v38-top>#status .status{gap:11px!important}
      .top.rx-v38-top>#status .pot{font-size:27px!important}
      .top.rx-v38-top>#status .status-title{font-size:19px!important}
      .top.rx-v38-top>.toolbar{
        display:flex!important;
        align-items:center!important;
        gap:6px!important;
        flex-wrap:nowrap!important;
        min-width:0!important;
      }
      .top.rx-v38-top #entrySelect{
        width:auto!important;
        max-width:180px!important;
        min-width:110px!important;
        min-height:40px!important;
        height:40px!important;
        padding:7px 30px 7px 9px!important;
      }
      #cook4meUiLanguageControl.rx-v38-globe{
        display:block!important;
        width:40px!important;
        min-width:40px!important;
        height:40px!important;
        margin:0!important;
        padding:0!important;
        border:0!important;
        border-radius:12px!important;
        background:transparent!important;
        overflow:visible!important;
      }
      #cook4meUiLanguageControl.rx-v38-globe>.field{
        position:relative!important;
        display:grid!important;
        place-items:center!important;
        width:40px!important;
        min-width:40px!important;
        height:40px!important;
        min-height:40px!important;
        margin:0!important;
        padding:0!important;
        border:1px solid var(--divider-color)!important;
        border-radius:12px!important;
        background:var(--secondary-background-color)!important;
        overflow:hidden!important;
      }
      #cook4meUiLanguageControl.rx-v38-globe label,
      #cook4meUiLanguageControl.rx-v38-globe .muted{display:none!important}
      #cook4meUiLanguageControl.rx-v38-globe .rx-v38-globe-icon{
        --mdc-icon-size:21px;
        color:var(--primary-color);
        pointer-events:none;
      }
      #cook4meUiLanguageControl.rx-v38-globe select{
        position:absolute!important;
        inset:0!important;
        width:40px!important;
        min-width:40px!important;
        height:40px!important;
        min-height:40px!important;
        margin:0!important;
        padding:0!important;
        opacity:0!important;
        cursor:pointer!important;
      }
      #refresh.rx-v38-refresh{
        display:grid!important;
        place-items:center!important;
        width:40px!important;
        min-width:40px!important;
        height:40px!important;
        min-height:40px!important;
        padding:0!important;
        border-radius:12px!important;
      }
      #refresh.rx-v38-refresh ha-icon{--mdc-icon-size:21px}

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
        display:block!important;
        margin:0 0 4px!important;
        font-size:11px!important;
        line-height:1.15!important;
        white-space:nowrap!important;
        overflow:hidden!important;
        text-overflow:ellipsis!important;
      }
      .rx-today-row>.field input,
      .rx-today-row>.field select,
      .rx-today-picker>summary,
      .rx-today-row>details.rx-advanced>summary{
        width:100%!important;
        min-width:0!important;
        min-height:40px!important;
        height:40px!important;
      }
      .rx-today-picker>summary span,
      .rx-today-row>details.rx-advanced>summary span{
        min-width:0!important;
        overflow:hidden!important;
        text-overflow:ellipsis!important;
        white-space:nowrap!important;
      }
      .rx-today-picker-body,
      .rx-today-row>details.rx-advanced>.rx-advanced-content{
        max-width:min(440px,calc(100vw - 24px))!important;
      }
      .rx-today-actions{
        display:grid!important;
        grid-template-columns:minmax(0,1fr) 42px!important;
        gap:6px!important;
        margin:0!important;
      }
      .rx-today-actions .btn{min-width:0!important;height:40px!important;min-height:40px!important}
      .rx-today-actions .btn.secondary{width:42px!important;padding:0!important;font-size:0!important}
      .rx-today-actions .btn.secondary ha-icon{--mdc-icon-size:20px;font-size:initial}
      .rx-today-planner .rx-plan-summary{display:none!important}

      @media(max-width:680px){
        .top.rx-v38-top{padding:8px 9px!important}
        .top.rx-v38-top>#status .status-title{font-size:17px!important}
        .top.rx-v38-top>#status .muted{font-size:11px!important}
        .top.rx-v38-top #entrySelect{max-width:110px!important;min-width:86px!important}
        .rx-today-row{grid-template-columns:repeat(2,minmax(0,1fr))!important}
        .rx-today-picker-body,
        .rx-today-row>details.rx-advanced>.rx-advanced-content{
          position:static!important;
          width:100%!important;
          max-width:100%!important;
          margin-top:6px!important;
        }
      }
      @media(max-width:390px){.rx-today-row{grid-template-columns:1fr!important}}
    `;
    this.shadowRoot.appendChild(style);
  }

  _applyV38TopBar(){
    const top=this.shadowRoot?.querySelector(".top");
    const refresh=this.shadowRoot?.getElementById("refresh");
    const toolbar=refresh?.closest(".toolbar");
    if(!top||!toolbar)return;
    top.classList.add("rx-v38-top");

    const control=this.shadowRoot?.getElementById("cook4meUiLanguageControl");
    if(control){
      control.classList.add("rx-v38-globe");
      const field=control.querySelector(".field");
      const select=control.querySelector("#cook4meUiLanguage");
      if(field&&select&&!field.querySelector(".rx-v38-globe-icon")){
        const icon=document.createElement("ha-icon");
        icon.className="rx-v38-globe-icon";
        icon.setAttribute("icon","mdi:web");
        field.insertBefore(icon,select);
      }
      select?.setAttribute("aria-label",this._t("interfaceLanguage"));
      select?.setAttribute("title",this._t("interfaceLanguage"));
      if(control.parentElement!==toolbar)toolbar.insertBefore(control,refresh);
    }
    refresh.classList.add("rx-v38-refresh");
    refresh.title=this._t("refresh");
    refresh.setAttribute("aria-label",this._t("refresh"));
    if(!refresh.querySelector("ha-icon")){
      const icon=document.createElement("ha-icon");
      icon.setAttribute("icon","mdi:refresh");
      refresh.replaceChildren(icon);
    }
  }

  _renderTabs(){
    super._renderTabs();
    this._ensureV38Styles();
    this._applyV38TopBar();
  }

  _renderShell(){
    super._renderShell();
    this._ensureV38Styles();
    this._applyV38TopBar();
  }

  _renderToday(c){
    super._renderToday(c);
    const cleanup=()=>{
      const planner=this.shadowRoot?.querySelector(".rx-today-planner");
      planner?.querySelector(".rx-plan-summary")?.remove();
    };
    cleanup();
    queueMicrotask(cleanup);
  }
}

customElements.define("cook4me-recipe-hub-panel-v38",Cook4MeRecipeHubPanelV38);
