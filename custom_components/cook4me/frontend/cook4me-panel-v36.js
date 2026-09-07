import "./cook4me-panel-v35.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v35");
const REPLACEABLE_PHASES=new Set(["idle","stopped","preparation","add_ingredient","done"]);

class Cook4MeRecipeHubPanelV36 extends BasePanel{
  _ensureV36Styles(){
    if(this.shadowRoot?.getElementById("cook4meV36Styles"))return;
    const style=document.createElement("style");
    style.id="cook4meV36Styles";
    style.textContent=`
      .top{
        display:flex!important;
        align-items:stretch!important;
        gap:10px!important;
        flex-wrap:nowrap!important;
        overflow-x:auto!important;
        scrollbar-width:thin;
      }
      .top>#status{flex:1 1 auto;min-width:340px}
      .top>.toolbar{flex:0 0 auto;flex-wrap:nowrap!important;align-items:stretch!important}
      #cook4meUiLanguageControl{
        flex:0 0 auto!important;
        margin:0!important;
        padding:0!important;
        align-items:stretch!important;
        justify-content:flex-start!important;
      }
      #cook4meUiLanguageControl>.field{min-width:205px!important;max-width:260px!important;justify-content:center}
      #cook4meUiLanguageControl .muted{display:none!important}
      #cook4meUiLanguageControl select{min-height:42px!important}
      .tabs{
        display:flex!important;
        flex-wrap:nowrap!important;
        gap:8px!important;
        overflow-x:auto!important;
        overflow-y:hidden!important;
        scrollbar-width:thin;
        padding-bottom:2px;
      }
      .tabs>.tab{flex:0 0 auto!important;white-space:nowrap!important}

      .rx-today-planner.rx-today-compact{padding:10px!important;overflow:visible!important}
      .rx-today-row{
        display:flex;
        flex-wrap:nowrap;
        align-items:flex-end;
        gap:8px;
        width:100%;
        overflow-x:auto;
        overflow-y:visible;
        padding:1px 1px 3px;
        scrollbar-width:thin;
      }
      .rx-today-row>.field{flex:0 0 160px;min-width:150px}
      .rx-today-row>.field label{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .rx-today-row #todayCalories{width:100%;min-width:100px}
      .rx-today-picker{position:relative;flex:0 0 auto;min-width:145px}
      .rx-today-picker>summary{
        list-style:none;
        display:flex;
        align-items:center;
        gap:7px;
        min-height:42px;
        padding:9px 11px;
        border:1px solid var(--divider-color);
        border-radius:10px;
        background:var(--secondary-background-color);
        color:var(--primary-text-color);
        cursor:pointer;
        white-space:nowrap;
        user-select:none;
      }
      .rx-today-picker>summary::-webkit-details-marker{display:none}
      .rx-today-picker>summary ha-icon{--mdc-icon-size:18px;color:var(--primary-color)}
      .rx-today-picker>summary b{font-size:11px;color:var(--secondary-text-color);font-weight:700;margin-left:2px}
      .rx-today-picker[open]>summary{border-color:var(--primary-color)}
      .rx-today-picker-body{
        position:absolute;
        z-index:40;
        top:calc(100% + 7px);
        left:0;
        width:max-content;
        min-width:min(430px,82vw);
        max-width:min(620px,88vw);
        max-height:58vh;
        overflow:auto;
        padding:11px;
        border:1px solid var(--divider-color);
        border-radius:12px;
        background:var(--card-background-color);
        box-shadow:0 10px 32px rgba(0,0,0,.28);
      }
      .rx-today-picker-body>.field,
      .rx-today-picker-body>div{margin-top:0!important}
      .rx-today-picker-body #todayIngredients{min-height:220px!important;max-height:42vh}
      .rx-today-row>.rx-advanced{position:relative;flex:0 0 auto;margin:0!important}
      .rx-today-row>.rx-advanced>summary{min-height:42px;white-space:nowrap}
      .rx-today-row>.rx-advanced>.rx-advanced-content{
        position:absolute;
        z-index:40;
        top:calc(100% + 7px);
        right:0;
        min-width:min(470px,84vw);
        max-width:84vw;
        padding:11px;
        border:1px solid var(--divider-color);
        border-radius:12px;
        background:var(--card-background-color);
        box-shadow:0 10px 32px rgba(0,0,0,.28);
      }
      .rx-today-actions{flex:0 0 auto!important;flex-wrap:nowrap!important;margin:0!important;align-items:flex-end!important}
      .rx-today-actions .btn{white-space:nowrap}

      .rx-category-result.rx-category-result-expanded{grid-column:span 2!important;min-width:0}
      .rx-category-result.rx-category-result-expanded>article.recipe.rx-inline-expanded{
        grid-column:auto!important;
        width:100%!important;
      }

      #shoppingToggleAll{white-space:nowrap}

      @media(max-width:700px){
        .top{gap:8px!important}
        .top>#status{min-width:280px}
        #cook4meUiLanguageControl>.field{min-width:190px!important}
        .rx-today-row{overflow-x:auto}
        .rx-category-result.rx-category-result-expanded{grid-column:1/-1!important}
      }
    `;
    this.shadowRoot.appendChild(style);
  }

  _moveUiLanguageControl(){
    const top=this.shadowRoot?.querySelector(".top");
    const control=this.shadowRoot?.getElementById("cook4meUiLanguageControl");
    const refreshToolbar=top?.querySelector(":scope > .toolbar");
    if(!top||!control)return;
    if(control.parentElement!==top){
      if(refreshToolbar)top.insertBefore(control,refreshToolbar);
      else top.appendChild(control);
    }
  }

  _renderUiLanguageControl(){
    super._renderUiLanguageControl();
    this._moveUiLanguageControl();
  }

  _renderShell(){
    super._renderShell();
    this._ensureV36Styles();
    this._moveUiLanguageControl();
  }

  _todayTopChild(planner,node){
    let current=node;
    while(current?.parentElement&&current.parentElement!==planner)current=current.parentElement;
    return current?.parentElement===planner?current:null;
  }

  _todayPicker(block,label,icon,count=""){
    if(!block)return null;
    const details=document.createElement("details");
    details.className="rx-today-picker";
    details.innerHTML=`<summary><ha-icon icon="mdi:${this._escape(icon)}"></ha-icon><span>${this._escape(label)}</span><b data-rx-picker-count>${this._escape(count)}</b></summary><div class="rx-today-picker-body"></div>`;
    details.querySelector(".rx-today-picker-body")?.appendChild(block);
    return details;
  }

  _updateTodayPickerCounts(c){
    const planner=c.querySelector(".rx-today-planner");
    if(!planner)return;
    const set=(kind,value)=>{
      const target=planner.querySelector(`[data-rx-picker="${kind}"] [data-rx-picker-count]`);
      if(target)target.textContent=value;
    };
    const meals=[...planner.querySelectorAll("[data-today-meal-type]")];
    const languages=[...planner.querySelectorAll("[data-today-language]")];
    const ingredients=[...(planner.querySelector("#todayIngredients")?.options||[])];
    set("meals",`${meals.filter(row=>row.checked).length}/${meals.length}`);
    set("languages",`${languages.filter(row=>row.checked).length}/${languages.length}`);
    set("ingredients",String(ingredients.filter(row=>row.selected).length));
  }

  _compactTodayPlanner(c){
    const planner=c.querySelector(".rx-today-planner");
    if(!planner||planner.dataset.cook4meV36Compact)return;
    planner.dataset.cook4meV36Compact="1";
    planner.classList.add("rx-today-compact");

    const form=planner.querySelector(":scope > .formgrid");
    const mealBlock=this._todayTopChild(planner,planner.querySelector("[data-today-meal-type]"));
    const languageBlock=this._todayTopChild(planner,planner.querySelector("[data-today-language]"));
    const ingredientBlock=this._todayTopChild(planner,planner.querySelector("#todayIngredients"));
    const advanced=planner.querySelector(":scope > details.rx-advanced");
    const actions=planner.querySelector(":scope > .toolbar");

    const row=document.createElement("div");
    row.className="rx-today-row";
    if(form){
      [...form.children].forEach(child=>row.appendChild(child));
    }

    const mealPicker=this._todayPicker(mealBlock,this._t("mealTypes"),"silverware-fork-knife");
    if(mealPicker){mealPicker.dataset.rxPicker="meals";row.appendChild(mealPicker);}
    const languagePicker=this._todayPicker(languageBlock,this._t("catalogLanguages"),"translate");
    if(languagePicker){languagePicker.dataset.rxPicker="languages";row.appendChild(languagePicker);}
    const ingredientPicker=this._todayPicker(ingredientBlock,this._t("preferredIngredients"),"food-apple-outline");
    if(ingredientPicker){ingredientPicker.dataset.rxPicker="ingredients";row.appendChild(ingredientPicker);}

    if(advanced){
      advanced.classList.add("rx-today-picker");
      row.appendChild(advanced);
    }
    if(actions){
      actions.classList.add("rx-today-actions");
      actions.style.marginTop="0";
      row.appendChild(actions);
    }

    planner.replaceChildren(row);
    row.querySelectorAll("details").forEach(details=>details.addEventListener("toggle",()=>{
      if(!details.open)return;
      row.querySelectorAll("details[open]").forEach(other=>{if(other!==details)other.open=false;});
    }));
    row.addEventListener("change",()=>this._updateTodayPickerCounts(c));
    this._updateTodayPickerCounts(c);
  }

  _renderToday(c){
    super._renderToday(c);
    this._compactTodayPlanner(c);
  }

  _collapseInline(){
    this._inlineRecipeCard?.closest(".rx-category-result")?.classList.remove("rx-category-result-expanded");
    super._collapseInline();
  }

  async _toggleInlineRecipe(card,recipe,custom){
    await super._toggleInlineRecipe(card,recipe,custom);
    const wrapper=card?.closest(".rx-category-result");
    if(wrapper)wrapper.classList.toggle("rx-category-result-expanded",card.classList.contains("rx-inline-expanded"));
  }

  _replaceableLoadedRecipe(){
    const entry=this._entry();
    if(!entry?.connected||!entry?.loadedRecipe)return false;
    const phase=String(entry?.state?.phase||entry?.state?.status||"").trim().toLowerCase();
    return REPLACEABLE_PHASES.has(phase);
  }

  _bindCards(container,items,custom=false){
    super._bindCards(container,items,custom);
    container.querySelectorAll(".recipe").forEach((card,index)=>{
      const recipe=items[index];
      if(!recipe)return;

      const inheritedOpen=card.querySelector('[data-action="open"]');
      if(inheritedOpen){
        const open=inheritedOpen.cloneNode(true);
        inheritedOpen.replaceWith(open);
        open.addEventListener("click",event=>{
          event.preventDefault();
          event.stopPropagation();
          void this._toggleInlineRecipe(card,recipe,custom);
        });
      }

      const send=card.querySelector('[data-action="send"]');
      if(send&&!custom&&recipe?.sendable!==false&&recipe?.match?.safe!==false&&this._replaceableLoadedRecipe()){
        send.disabled=false;
        send.removeAttribute("title");
        send.dataset.replaceLoaded="1";
      }
    });
  }

  async _send(recipe){
    try{
      const variant=recipe?.sendVariantId||recipe?.selectedSendVariantId||recipe?.searchVariantId||recipe?.variantFunctionalId||recipe?.recipeFunctionalId;
      if(!variant)throw new Error("Missing official recipe ID");
      this._message(this._t("loading"));
      await this._api("cook4me/v12/send_recipe_replaceable",{
        entry_id:this._entryId,
        variant_id:String(variant),
      });
      this._message(`${this._t("send")}: ${this._clean(recipe?.title||variant)}`);
      await this._loadOverview(true);
    }catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true);}
  }

  _renderShopping(c){
    super._renderShopping(c);
    const items=Array.isArray(this._shoppingItems)?this._shoppingItems:[];
    if(!items.length||this._shoppingAvailable===false)return;
    const allCompleted=items.every(row=>String(row?.status)==="completed");
    const refresh=c.querySelector("#shoppingRefresh");
    const head=refresh?.parentElement;
    if(!head||c.querySelector("#shoppingToggleAll"))return;
    const button=document.createElement("button");
    button.id="shoppingToggleAll";
    button.className="btn secondary";
    button.innerHTML=`<ha-icon icon="mdi:${allCompleted?"checkbox-multiple-blank-outline":"checkbox-multiple-marked-outline"}"></ha-icon><span>${this._escape(this._t(allCompleted?"deselectAll":"selectAll"))}</span>`;
    button.addEventListener("click",()=>void this._shoppingAction(allCompleted?"incomplete_all":"complete_all"));
    head.insertBefore(button,refresh||null);
  }
}

customElements.define("cook4me-recipe-hub-panel-v36",Cook4MeRecipeHubPanelV36);
