import "./cook4me-panel-v30.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v30");

const TAB_ICONS_V31={
  today:"calendar-today",
  official:"pot-steam-outline",
  recommend:"home-heart",
  book:"book-heart-outline",
  mine:"notebook-edit-outline",
  profile:"basket-outline",
  shopping:"cart-outline",
  ai:"creation",
};

class Cook4MeRecipeHubPanelV31 extends BasePanel{
  _modernizeTabs(){
    const tabs=this.shadowRoot?.getElementById("tabs");
    if(!tabs)return;
    tabs.querySelectorAll("[data-tab]").forEach(button=>{
      const tab=String(button.dataset.tab||"");
      const icon=TAB_ICONS_V31[tab]||"circle-small";
      const current=button.querySelector(":scope > ha-icon.rx-tab-icon")?.getAttribute("icon");
      if(button.dataset.rxTabIcon===icon&&current===`mdi:${icon}`)return;
      const label=button.querySelector(":scope > span:last-child")?.textContent?.trim()
        ||button.textContent.trim()
        ||this._t(tab);
      button.textContent="";
      button.append(this._newIcon(icon,"rx-tab-icon"));
      const span=document.createElement("span");span.textContent=label;button.append(span);
      button.dataset.rxTabIcon=icon;
      button.setAttribute("title",label);
    });
  }

  _buttonIcon(button){
    const action=String(button.dataset?.action||"");
    if(action==="favorite"){
      const title=String(button.getAttribute("title")||"");
      return title===String(this._t("removeFavorite"))?"heart":"heart-outline";
    }
    if(action==="recipe-list"){
      const title=String(button.getAttribute("title")||"");
      return title===String(this._t("removeRecipeList"))?"playlist-check":"playlist-plus";
    }
    if(action==="open")return"book-open-page-variant";
    if(button.hasAttribute("data-detail-favorite"))return this._isFavorite?.(this._opened)?"heart":"heart-outline";
    if(button.hasAttribute("data-detail-list"))return this._isListed?.(this._opened)?"playlist-check":"playlist-plus";
    return super._buttonIcon(button);
  }
}

customElements.define("cook4me-recipe-hub-panel-v31",Cook4MeRecipeHubPanelV31);
