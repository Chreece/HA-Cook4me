import "./cook4me-panel-v40.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v40");
const VALID_SECTIONS=new Set(["today","official","recommend","book","mine","profile","shopping","ai"]);
const LAST_SECTION_PREFIX="cook4me.ui.lastSection.v1.";

class Cook4MeRecipeHubPanelV41 extends BasePanel{
  constructor(){
    super();
    this._restoredSectionUser="";
    this._outsidePointerHandler=event=>this._dismissOpenMenusFromPointer(event);
  }

  get hass(){return super.hass;}
  set hass(value){
    const user=String(value?.user?.id||"anonymous");
    if(user!==this._restoredSectionUser){
      this._restoredSectionUser=user;
      const saved=this._loadLastSection(user);
      if(saved)this._tab=saved;
    }
    super.hass=value;
  }

  connectedCallback(){
    super.connectedCallback();
    document.addEventListener("pointerdown",this._outsidePointerHandler,true);
  }

  disconnectedCallback(){
    document.removeEventListener("pointerdown",this._outsidePointerHandler,true);
    if(super.disconnectedCallback)super.disconnectedCallback();
  }

  _lastSectionKey(user=this._restoredSectionUser||String(this._hass?.user?.id||"anonymous")){
    return `${LAST_SECTION_PREFIX}${user}`;
  }

  _loadLastSection(user){
    try{
      const value=String(localStorage.getItem(this._lastSectionKey(user))||"");
      return VALID_SECTIONS.has(value)?value:"";
    }catch(_e){return"";}
  }

  _rememberSection(section){
    const value=String(section||"");
    if(!VALID_SECTIONS.has(value))return;
    try{localStorage.setItem(this._lastSectionKey(),value);}catch(_e){}
  }

  _renderTabs(){
    super._renderTabs();
    const tabs=this.shadowRoot?.getElementById("tabs");
    if(!tabs||tabs.dataset.cook4meRememberSection==="1")return;
    tabs.dataset.cook4meRememberSection="1";
    tabs.addEventListener("click",event=>{
      const target=event.target instanceof Element?event.target.closest("[data-tab]"):null;
      if(target&&tabs.contains(target))this._rememberSection(target.dataset.tab);
    },true);
  }

  _renderTab(){
    this._rememberSection(this._tab);
    return super._renderTab();
  }

  _dismissOpenMenusFromPointer(event){
    const root=this.shadowRoot;
    if(!root)return;
    const path=typeof event?.composedPath==="function"?event.composedPath():[];
    const selector="details.rx-today-picker[open],details.rx-advanced[open],details[data-menu][open],details[data-selector][open]";
    root.querySelectorAll(selector).forEach(menu=>{
      if(!path.includes(menu))menu.removeAttribute("open");
    });
  }
}

customElements.define("cook4me-recipe-hub-panel-v41",Cook4MeRecipeHubPanelV41);
