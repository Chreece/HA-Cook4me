import "./cook4me-panel-v39.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v39");

class Cook4MeRecipeHubPanelV40 extends BasePanel{
  _normalizeTodayActionIcon(button,icon,{iconOnly=false}={}){
    if(!button)return;

    // v34 renders its own <ha-icon>, while the inherited v30/v32 global
    // button modernizer also prepends an rx-leading-icon. Normalize the DOM to
    // the modernizer's contract before that queued pass runs so every Today
    // action can physically contain only one icon.
    for(const child of [...button.children]){
      if(String(child.tagName||"").toUpperCase()==="HA-ICON")child.remove();
    }

    const node=this._newIcon(icon,"rx-leading-icon");
    button.prepend(node);
    button.dataset.rxIcon=icon;

    if(iconOnly){
      for(const child of [...button.children]){
        if(child!==node)child.remove();
      }
      for(const text of [...button.childNodes]){
        if(text.nodeType===Node.TEXT_NODE)text.textContent="";
      }
    }
  }

  _normalizeTodayActionButtons(c){
    const suggest=c?.querySelector?.("#todaySuggest");
    const reset=c?.querySelector?.("#todayReset");
    this._normalizeTodayActionIcon(suggest,"chef-hat");
    this._normalizeTodayActionIcon(reset,"backup-restore",{iconOnly:true});
  }

  _modernizeButtons(root){
    super._modernizeButtons(root);
    const content=this.shadowRoot?.getElementById("content");
    if(content)this._normalizeTodayActionButtons(content);
  }

  _renderToday(c){
    super._renderToday(c);
    this._normalizeTodayActionButtons(c);
    queueMicrotask(()=>this._normalizeTodayActionButtons(c));
  }
}

customElements.define("cook4me-recipe-hub-panel-v40",Cook4MeRecipeHubPanelV40);
