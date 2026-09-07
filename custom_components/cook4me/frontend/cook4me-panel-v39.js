import "./cook4me-panel-v38.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v38");

class Cook4MeRecipeHubPanelV39 extends BasePanel{
  _ensureV39Styles(){
    if(this.shadowRoot?.getElementById("cook4meV39Styles"))return;
    const style=document.createElement("style");
    style.id="cook4meV39Styles";
    style.textContent=`
      #refresh.rx-v38-refresh{
        position:relative!important;
        display:grid!important;
        place-items:center!important;
        width:40px!important;
        min-width:40px!important;
        max-width:40px!important;
        height:40px!important;
        min-height:40px!important;
        max-height:40px!important;
        padding:0!important;
        margin:0!important;
        overflow:hidden!important;
        line-height:0!important;
        font-size:0!important;
      }
      #refresh.rx-v38-refresh>ha-icon{
        position:static!important;
        display:block!important;
        width:22px!important;
        min-width:22px!important;
        max-width:22px!important;
        height:22px!important;
        min-height:22px!important;
        max-height:22px!important;
        margin:0!important;
        padding:0!important;
        line-height:1!important;
        --mdc-icon-size:22px!important;
      }
      #cook4meUiLanguageControl.rx-v38-globe,
      #cook4meUiLanguageControl.rx-v38-globe>.field,
      #cook4meUiLanguageControl.rx-v38-globe .rx-v38-globe-icon{
        overflow:hidden!important;
      }

      .rx-today-planner.rx-today-compact{min-width:0!important;overflow:visible!important}
      .rx-today-row{
        display:grid!important;
        grid-template-columns:repeat(auto-fit,minmax(180px,1fr))!important;
        align-items:end!important;
        gap:8px!important;
        width:100%!important;
        min-width:0!important;
        max-width:100%!important;
        overflow:visible!important;
      }
      .rx-today-row>*{box-sizing:border-box!important;min-width:0!important;max-width:100%!important}
      .rx-today-row>.field,
      .rx-today-row>.rx-today-picker,
      .rx-today-row>.rx-today-actions{
        width:100%!important;
        min-width:0!important;
        max-width:100%!important;
      }
      .rx-today-row>.field label{
        width:100%!important;
        min-width:0!important;
        max-width:100%!important;
        overflow:hidden!important;
        text-overflow:ellipsis!important;
        white-space:nowrap!important;
      }
      .rx-today-row>.field input,
      .rx-today-row>.field select{
        box-sizing:border-box!important;
        width:100%!important;
        min-width:0!important;
        max-width:100%!important;
        overflow:hidden!important;
        text-overflow:ellipsis!important;
        white-space:nowrap!important;
      }

      .rx-today-picker>summary,
      .rx-today-row>details.rx-advanced>summary{
        box-sizing:border-box!important;
        display:grid!important;
        grid-template-columns:auto minmax(0,1fr) auto!important;
        align-items:center!important;
        gap:7px!important;
        width:100%!important;
        min-width:0!important;
        max-width:100%!important;
        overflow:hidden!important;
        padding:8px 10px!important;
      }
      .rx-today-picker>summary>ha-icon,
      .rx-today-row>details.rx-advanced>summary>ha-icon{
        position:static!important;
        display:block!important;
        flex:none!important;
        width:18px!important;
        min-width:18px!important;
        max-width:18px!important;
        height:18px!important;
        min-height:18px!important;
        max-height:18px!important;
        margin:0!important;
        padding:0!important;
        --mdc-icon-size:18px!important;
      }
      .rx-today-picker>summary>span,
      .rx-today-row>details.rx-advanced>summary>span{
        display:block!important;
        min-width:0!important;
        max-width:100%!important;
        overflow:hidden!important;
        text-overflow:ellipsis!important;
        white-space:nowrap!important;
      }
      .rx-today-picker>summary>b{
        position:static!important;
        min-width:0!important;
        max-width:48px!important;
        margin:0!important;
        overflow:hidden!important;
        text-overflow:ellipsis!important;
        white-space:nowrap!important;
      }

      .rx-today-actions{
        grid-column:span 2!important;
        display:grid!important;
        grid-template-columns:minmax(0,1fr) 42px!important;
        align-items:stretch!important;
        gap:6px!important;
        width:100%!important;
        min-width:0!important;
        max-width:100%!important;
        overflow:hidden!important;
      }
      .rx-today-actions .btn{
        box-sizing:border-box!important;
        position:relative!important;
        display:flex!important;
        align-items:center!important;
        justify-content:center!important;
        gap:6px!important;
        width:100%!important;
        min-width:0!important;
        max-width:100%!important;
        height:40px!important;
        min-height:40px!important;
        max-height:40px!important;
        padding:7px 10px!important;
        margin:0!important;
        overflow:hidden!important;
        white-space:nowrap!important;
        line-height:1.2!important;
      }
      .rx-today-actions .btn>ha-icon{
        position:static!important;
        display:block!important;
        flex:0 0 19px!important;
        width:19px!important;
        min-width:19px!important;
        max-width:19px!important;
        height:19px!important;
        min-height:19px!important;
        max-height:19px!important;
        margin:0!important;
        padding:0!important;
        --mdc-icon-size:19px!important;
      }
      .rx-today-actions .btn>span{
        display:block!important;
        min-width:0!important;
        max-width:100%!important;
        overflow:hidden!important;
        text-overflow:ellipsis!important;
        white-space:nowrap!important;
      }
      .rx-today-actions .btn.secondary{
        width:42px!important;
        min-width:42px!important;
        max-width:42px!important;
        padding:0!important;
        overflow:hidden!important;
        font-size:0!important;
      }
      .rx-today-actions .btn.secondary>ha-icon{
        flex:0 0 20px!important;
        width:20px!important;
        min-width:20px!important;
        max-width:20px!important;
        height:20px!important;
        min-height:20px!important;
        max-height:20px!important;
        --mdc-icon-size:20px!important;
      }

      @media(max-width:1200px){
        .rx-today-row{grid-template-columns:repeat(auto-fit,minmax(165px,1fr))!important}
      }
      @media(max-width:720px){
        .rx-today-row{grid-template-columns:repeat(2,minmax(0,1fr))!important}
        .rx-today-actions{grid-column:1/-1!important}
      }
      @media(max-width:420px){
        .rx-today-row{grid-template-columns:1fr!important}
        .rx-today-actions{grid-column:1!important}
      }
    `;
    this.shadowRoot.appendChild(style);
  }

  _normalizeRefreshControl(){
    const refresh=this.shadowRoot?.getElementById("refresh");
    if(!refresh)return;
    const icon=this._newIcon("refresh","rx-leading-icon");
    refresh.replaceChildren(icon);
    refresh.dataset.rxIcon="refresh";
    refresh.classList.add("rx-icon-only","rx-v38-refresh");
    refresh.title=this._t("refresh");
    refresh.setAttribute("aria-label",this._t("refresh"));
  }

  _applyV38TopBar(){
    super._applyV38TopBar();
    this._ensureV39Styles();
    this._normalizeRefreshControl();
  }

  _renderToday(c){
    super._renderToday(c);
    this._ensureV39Styles();
  }

  _renderShell(){
    super._renderShell();
    this._ensureV39Styles();
    this._normalizeRefreshControl();
  }
}

customElements.define("cook4me-recipe-hub-panel-v39",Cook4MeRecipeHubPanelV39);
