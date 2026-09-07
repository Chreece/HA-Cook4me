import "./cook4me-panel-v32.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v32");

/**
 * v33 hotfix: keep the professional UI, but remove the broad subtree
 * MutationObserver introduced by v30.  v32's professional decorators mutate
 * option/text/summary DOM themselves, so observing every childList mutation can
 * create a self-sustaining decorate -> mutation -> decorate loop and pin the HA
 * frontend main thread as soon as the Recipe Hub is opened.
 *
 * All meaningful Recipe Hub renders already call _modernizeSoon() explicitly
 * through _renderShell/_renderTabs/_renderTab/_updateHeader, so the observer is
 * unnecessary.  We also make the two remaining text/summary decorators strictly
 * idempotent as a second guard against accidental render storms.
 */
class Cook4MeRecipeHubPanelV33 extends BasePanel{
  constructor(){
    super();
    this._rxProfessionalFrame=0;
  }

  _installModernObserver(){
    // Deliberately disable the v30 subtree observer.  Dynamic render entry
    // points already schedule modernisation, while job cards style themselves.
    this._modernObserver?.disconnect();
    this._modernObserver=null;
  }

  disconnectedCallback(){
    if(this._rxProfessionalFrame){
      cancelAnimationFrame(this._rxProfessionalFrame);
      this._rxProfessionalFrame=0;
    }
    super.disconnectedCallback?.();
  }

  _professionalizeSoon(){
    if(this._rxProfessionalPending||this._rxProfessionalFrame)return;
    this._rxProfessionalPending=true;
    this._rxProfessionalFrame=requestAnimationFrame(()=>{
      this._rxProfessionalFrame=0;
      this._rxProfessionalPending=false;
      if(!this.shadowRoot||!this.isConnected)return;
      this._decorateLanguages(this.shadowRoot);
      this._decorateFields(this.shadowRoot);
      this._upgradeTodayPanel(this.shadowRoot);
      this._upgradeChoiceStates(this.shadowRoot);
      this._upgradeIngredientSheet(this.shadowRoot);
    });
  }

  _decorateLanguages(root){
    const selectors=["#cook4meUiLanguage","#recipeLanguage","#ingredientLanguage","#manualIngredientLanguage","[data-action='recipe-language']"];
    root.querySelectorAll(selectors.join(",")).forEach(select=>{
      for(const option of select.options||[]){
        if(!option.dataset.rxBaseLabel)option.dataset.rxBaseLabel=option.textContent.trim();
        const code=String(option.value||"").toLowerCase().split(/[-_]/)[0];
        const flag=this._flagForLanguage(code);
        const base=option.dataset.rxBaseLabel
          .replace(/^[\u{1F1E6}-\u{1F1FF}]{2}\s*/u,"")
          .replace(/^🌐\s*/,"");
        const next=`${flag} ${base}`;
        if(option.textContent!==next)option.textContent=next;
      }
      const field=select.closest(".field");
      const flag=this._flagForLanguage(select.value);
      if(field){
        field.classList.add("rx-language-field");
        if(field.dataset.rxFlag!==flag)field.dataset.rxFlag=flag;
      }
      if(!select.dataset.rxFlagChange){
        select.dataset.rxFlagChange="1";
        select.addEventListener("change",()=>{
          const current=select.closest(".field");
          const nextFlag=this._flagForLanguage(select.value);
          if(current&&current.dataset.rxFlag!==nextFlag)current.dataset.rxFlag=nextFlag;
        });
      }
    });
  }

  _updateTodaySummary(planner){
    if(!planner)return;
    const target=planner.querySelector(".rx-plan-summary");
    if(!target)return;
    const parts=[];
    const diet=planner.querySelector("#todayDiet");
    if(diet)parts.push(`<span class="chip"><ha-icon icon="mdi:${DIET_ICONS_V33[diet.value]||"account-heart-outline"}"></ha-icon>${this._escape(diet.options[diet.selectedIndex]?.textContent?.replace(/^[^\p{L}\p{N}]+/u,"")||diet.value)}</span>`);
    const goal=planner.querySelector("#todayNutritionGoal");
    if(goal)parts.push(`<span class="chip"><ha-icon icon="mdi:${GOAL_ICONS_V33[goal.value]||"target"}"></ha-icon>${this._escape(goal.options[goal.selectedIndex]?.textContent?.replace(/^[^\p{L}\p{N}]+/u,"")||goal.value)}</span>`);
    const meals=Number(planner.querySelector("#todayMealCount")?.value||1);
    parts.push(`<span class="chip"><ha-icon icon="mdi:silverware-fork-knife"></ha-icon>${meals}</span>`);
    const calories=String(planner.querySelector("#todayCalories")?.value||"").trim();
    if(calories)parts.push(`<span class="chip"><ha-icon icon="mdi:fire"></ha-icon>${this._escape(calories)} kcal</span>`);
    const languages=[...planner.querySelectorAll("[data-today-language]:checked")].map(x=>this._flagForLanguage(x.dataset.todayLanguage)).join("");
    if(languages)parts.push(`<span class="chip"><ha-icon icon="mdi:translate"></ha-icon>${languages}</span>`);
    if(planner.querySelector("#todayOnlyHome")?.checked)parts.push(`<span class="chip"><ha-icon icon="mdi:home-check-outline"></ha-icon>${this._escape(this._t("onlyHome"))}</span>`);
    const next=`<span class="rx-plan-title"><ha-icon icon="mdi:tune-variant"></ha-icon>${this._escape(this._t("quickPlan"))}</span>${parts.join("")}`;
    if(target.innerHTML!==next){
      target.innerHTML=next;
      target.querySelectorAll("ha-icon").forEach(icon=>icon.style.setProperty("--mdc-icon-size","15px"));
    }
  }
}

const DIET_ICONS_V33={profile:"account-heart-outline",omnivore:"food-drumstick-outline",pescatarian:"fish",vegetarian:"sprout",vegan:"leaf-circle-outline"};
const GOAL_ICONS_V33={balanced:"scale-balance",high_protein:"arm-flex-outline",lower_calorie:"fire",high_fiber:"grain",lower_saturated_fat:"heart-pulse"};

customElements.define("cook4me-recipe-hub-panel-v33",Cook4MeRecipeHubPanelV33);
