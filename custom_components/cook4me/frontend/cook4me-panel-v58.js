import "./cook4me-panel-v57.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v57");
const MAX_IMAGE_CACHE=96;

class Cook4MeRecipeHubPanelV58 extends BasePanel{
  constructor(){
    super();
    this._v58ImagePool=new Map();
    this._v58ImageOrder=[];
  }

  async _api(type,data={}){
    const mapped=String(type)==="cook4me/v18/today_suggest"
      ?"cook4me/v29/today_suggest"
      :type;
    return super._api(mapped,data);
  }

  _recipeCard(recipe,custom=false){
    let html=super._recipeCard(recipe,custom);
    if(this._tab!=="today")return html;
    const language=String(recipe?.todayCatalogLanguage||"").trim().toUpperCase();
    if(!language)return html;
    const chip=`<span class="chip" data-today-catalog-chip>${this._escape(this._t("catalog"))}: ${this._escape(language)}</span>`;
    return html.replace('<div class="chips">',`<div class="chips">${chip}`);
  }

  _v58ImageKey(image){
    return String(image?.getAttribute?.("src")||image?.src||"").trim();
  }

  _v58ImageReady(image){
    if(!image)return false;
    if(image.dataset?.cook4meV58Ready==="1")return true;
    return Boolean(image.complete&&Number(image.naturalWidth||0)>0);
  }

  _v58TrackImage(image){
    if(!image||image.dataset?.cook4meV58Bound==="1")return;
    image.dataset.cook4meV58Bound="1";
    image.addEventListener("load",()=>{image.dataset.cook4meV58Ready="1";});
    if(this._v58ImageReady(image))image.dataset.cook4meV58Ready="1";
  }

  _v58TouchKey(key){
    const index=this._v58ImageOrder.indexOf(key);
    if(index>=0)this._v58ImageOrder.splice(index,1);
    this._v58ImageOrder.push(key);
    while(this._v58ImageOrder.length>MAX_IMAGE_CACHE){
      const oldest=this._v58ImageOrder.shift();
      if(oldest)this._v58ImagePool.delete(oldest);
    }
  }

  _v58StashImages(){
    const content=this.shadowRoot?.getElementById("content");
    if(!content)return;
    for(const image of [...content.querySelectorAll("img.cover,img.detail-cover")]){
      this._v58TrackImage(image);
      if(!this._v58ImageReady(image))continue;
      const key=this._v58ImageKey(image);
      if(!key)continue;
      image.remove();
      const rows=this._v58ImagePool.get(key)||[];
      if(!rows.includes(image))rows.push(image);
      this._v58ImagePool.set(key,rows.slice(-2));
      this._v58TouchKey(key);
    }
  }

  _v58CopyPresentation(from,to){
    for(const name of ["class","alt","loading","decoding","fetchpriority","style"]){
      const value=from.getAttribute?.(name);
      if(value===null||value===undefined)to.removeAttribute?.(name);
      else to.setAttribute?.(name,value);
    }
  }

  _v58RestoreImages(){
    const content=this.shadowRoot?.getElementById("content");
    if(!content)return;
    for(const image of [...content.querySelectorAll("img.cover,img.detail-cover")]){
      const key=this._v58ImageKey(image);
      const rows=key?this._v58ImagePool.get(key):null;
      const cached=rows?.shift();
      if(cached){
        this._v58CopyPresentation(image,cached);
        cached.dataset.cook4meV58Ready="1";
        this._v58TrackImage(cached);
        image.replaceWith(cached);
        if(rows.length)this._v58ImagePool.set(key,rows);
        else this._v58ImagePool.delete(key);
        this._v58TouchKey(key);
      }else{
        this._v58TrackImage(image);
      }
    }
  }

  _renderTab(){
    // Preserve already-loaded image DOM nodes before inherited renderers replace
    // the section with innerHTML. Restoring the same node keeps the decoded
    // image in memory and prevents a visible reload when navigating back.
    this._v58StashImages();
    const result=super._renderTab();
    this._v58RestoreImages();
    return result;
  }

  disconnectedCallback(){
    this._v58StashImages();
    if(super.disconnectedCallback)super.disconnectedCallback();
  }
}

customElements.define("cook4me-recipe-hub-panel-v58",Cook4MeRecipeHubPanelV58);
