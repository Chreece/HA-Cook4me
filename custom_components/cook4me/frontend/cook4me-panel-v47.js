import "./cook4me-panel-v46.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v46");

const GUARD_WINDOW_MS=1000;
const MAX_DOM_PASSES=80;
const MAX_RENDER_PASSES=60;

class Cook4MeRecipeHubPanelV47 extends BasePanel{
  constructor(){
    super();
    this._cook4meGuardWindowStart=0;
    this._cook4meGuardDomPasses=0;
    this._cook4meGuardRenderPasses=0;
    this._cook4meUiGuardTripped=false;
    this._cook4meUiGuardReason="";
  }

  _guardNow(){
    const value=globalThis.performance?.now?.();
    return Number.isFinite(Number(value))?Number(value):Date.now();
  }

  _guardPulse(kind){
    if(this._cook4meUiGuardTripped)return false;
    const now=this._guardNow();
    if(!this._cook4meGuardWindowStart||now-this._cook4meGuardWindowStart>GUARD_WINDOW_MS){
      this._cook4meGuardWindowStart=now;
      this._cook4meGuardDomPasses=0;
      this._cook4meGuardRenderPasses=0;
    }
    if(kind==="dom"){
      this._cook4meGuardDomPasses++;
      if(this._cook4meGuardDomPasses>MAX_DOM_PASSES){
        this._tripUiGuard("dom-mutation-loop");
        return false;
      }
    }else{
      this._cook4meGuardRenderPasses++;
      if(this._cook4meGuardRenderPasses>MAX_RENDER_PASSES){
        this._tripUiGuard("render-loop");
        return false;
      }
    }
    return true;
  }

  _tripUiGuard(reason){
    if(this._cook4meUiGuardTripped)return;
    this._cook4meUiGuardTripped=true;
    this._cook4meUiGuardReason=String(reason||"ui-loop");
    this._modernObserver?.disconnect?.();
    this._modernObserver=null;
    this.dataset.cook4meUiGuard="tripped";
    this.dataset.cook4meUiGuardReason=this._cook4meUiGuardReason;
    console.error(`[Cook4Me] UI loop protection stopped ${this._cook4meUiGuardReason}`);
    const message=this.shadowRoot?.getElementById("message");
    if(message&&!message.querySelector("[data-cook4me-loop-guard]")){
      const notice=document.createElement("div");
      notice.className="notice error";
      notice.dataset.cook4meLoopGuard="1";
      notice.textContent="Cook4Me stopped an abnormal UI render loop. Reload this panel; Home Assistant remains responsive.";
      message.replaceChildren(notice);
    }
  }

  _installModernObserver(){
    if(this._cook4meUiGuardTripped)return;
    return super._installModernObserver();
  }

  _modernizeSoon(){
    if(!this._guardPulse("dom"))return;
    return super._modernizeSoon();
  }

  _renderShell(){
    if(!this._guardPulse("render"))return;
    return super._renderShell();
  }

  _renderTabs(){
    if(!this._guardPulse("render"))return;
    return super._renderTabs();
  }

  _renderTab(){
    if(!this._guardPulse("render"))return;
    return super._renderTab();
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
        // Critical: assigning textContent always replaces the text node and
        // produces a childList mutation, even when the visible text is equal.
        // The global MutationObserver then schedules this decorator again.
        // Only write when the text actually changed so the pass converges.
        if(option.textContent!==next)option.textContent=next;
      }
      const field=select.closest(".field");
      if(field){
        field.classList.add("rx-language-field");
        const nextFlag=this._flagForLanguage(select.value);
        if(field.dataset.rxFlag!==nextFlag)field.dataset.rxFlag=nextFlag;
      }
      if(!select.dataset.rxFlagChange){
        select.dataset.rxFlagChange="1";
        select.addEventListener("change",()=>{
          const fieldNode=select.closest(".field");
          if(!fieldNode)return;
          const nextFlag=this._flagForLanguage(select.value);
          if(fieldNode.dataset.rxFlag!==nextFlag)fieldNode.dataset.rxFlag=nextFlag;
        });
      }
    });
  }
}

customElements.define("cook4me-recipe-hub-panel-v47",Cook4MeRecipeHubPanelV47);
