import "./cook4me-panel-v34.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v34");

class Cook4MeRecipeHubPanelV35 extends BasePanel{
  _highResCover(value){
    const url=String(value||"").trim();
    if(!url)return url;
    return url.replace("/statics/thumb/","/statics/original/");
  }

  _mediaHtml(recipe){
    if(!recipe||typeof recipe!=="object")return super._mediaHtml(recipe);
    const cover=this._highResCover(recipe.cover);
    return super._mediaHtml(cover===recipe.cover?recipe:{...recipe,cover});
  }

  _detailHtml(recipe){
    if(!recipe||typeof recipe!=="object")return super._detailHtml(recipe);
    const cover=this._highResCover(recipe.cover);
    return super._detailHtml(cover===recipe.cover?recipe:{...recipe,cover});
  }

  _ensureSplitInlineStyles(){
    if(this.shadowRoot?.getElementById("cook4meInlineV35"))return;
    const style=document.createElement("style");
    style.id="cook4meInlineV35";
    style.textContent=`
      article.recipe.rx-inline-expanded{
        grid-column:span 2!important;
        display:grid!important;
        grid-template-columns:minmax(0,1fr) minmax(0,1fr)!important;
        gap:14px!important;
        align-items:start!important;
        max-width:none!important;
      }
      article.recipe.rx-inline-expanded>.rx-inline-left{
        min-width:0;
        display:flex;
        flex-direction:column;
        gap:10px;
      }
      article.recipe.rx-inline-expanded>.rx-inline-expansion{
        grid-column:2!important;
        grid-row:1!important;
        min-width:0;
        margin:0!important;
        padding:0 0 0 14px!important;
        border-top:0!important;
        border-left:1px solid var(--divider-color)!important;
        border-radius:0!important;
        background:transparent!important;
      }
      article.recipe.rx-inline-expanded>.rx-inline-left .media,
      article.recipe.rx-inline-expanded>.rx-inline-left img.cover{
        width:100%!important;
        max-width:100%!important;
      }
      @media(max-width:650px){
        article.recipe.rx-inline-expanded{
          grid-column:1/-1!important;
          grid-template-columns:minmax(0,1fr)!important;
        }
        article.recipe.rx-inline-expanded>.rx-inline-expansion{
          grid-column:1!important;
          grid-row:2!important;
          margin-top:12px!important;
          padding:14px 0 0!important;
          border-left:0!important;
          border-top:1px solid var(--divider-color)!important;
        }
      }
    `;
    this.shadowRoot.appendChild(style);
  }

  _renderShell(){
    super._renderShell();
    this._ensureSplitInlineStyles();
  }

  _wrapInlineLeft(card){
    let left=card.querySelector(":scope > .rx-inline-left");
    if(left)return left;
    left=document.createElement("div");
    left.className="rx-inline-left";
    while(card.firstChild)left.appendChild(card.firstChild);
    card.appendChild(left);
    return left;
  }

  _collapseInline(){
    const card=this._inlineRecipeCard;
    if(card?.isConnected){
      card.querySelector(":scope > .rx-inline-expansion")?.remove();
      const left=card.querySelector(":scope > .rx-inline-left");
      if(left){
        while(left.firstChild)card.insertBefore(left.firstChild,left);
        left.remove();
      }
      card.classList.remove("rx-inline-expanded");
    }
    this._inlineRecipeCard=null;
    this._inlineRecipeKey="";
  }

  async _toggleInlineRecipe(card,recipe,custom){
    const key=this._todayRecipeIdentity(recipe);
    if(this._inlineRecipeKey===key&&card.classList.contains("rx-inline-expanded")){
      this._collapseInline();
      return;
    }
    this._collapseInline();
    const job=this._processStart(this._t("backgroundWork"),this._t("openingRecipe"),{icon:"book-open-page-variant-outline",delay:100});
    try{
      const detail=await this._inlineDetail(recipe,custom);
      if(job.cancelled)return;
      this._wrapInlineLeft(card);
      card.insertAdjacentHTML("beforeend",this._inlineStepsHtml(detail));
      card.classList.add("rx-inline-expanded");
      this._inlineRecipeKey=key;
      this._inlineRecipeCard=card;
      const ingredients=(detail.ingredients||[]).filter(item=>this._ingredientText(item));
      card.querySelectorAll("[data-inline-ingredient]").forEach(button=>button.addEventListener("click",event=>{
        event.stopPropagation();
        const id=String(button.dataset.inlineIngredient||"");
        const item=ingredients.find(row=>this._todayIngredientIdentity(row)===id);
        if(item)void this._showIngredientInfo(item,detail);
      }));
      card.scrollIntoView?.({behavior:"smooth",block:"nearest"});
    }catch(e){
      this._message(`${this._t("error")}: ${e.message||e}`,true);
    }finally{
      this._processEnd(job);
    }
  }
}

customElements.define("cook4me-recipe-hub-panel-v35",Cook4MeRecipeHubPanelV35);
