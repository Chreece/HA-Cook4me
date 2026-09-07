import "./cook4me-panel-v29.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v29");

const TAB_ICONS={
  today:"calendar-today-outline",
  official:"pot-steam-outline",
  recommend:"home-heart",
  book:"book-heart-outline",
  mine:"notebook-edit-outline",
  profile:"basket-outline",
  shopping:"cart-outline",
  ai:"creation-outline",
};

const ACTION_ICONS={
  open:"book-open-page-variant-outline",
  send:"pot-steam-outline",
  delete:"trash-can-outline",
  favorite:"heart-outline",
  "recipe-list":"format-list-bulleted-square",
  "shop-missing":"cart-plus",
  "shop-one":"cart-plus",
  "shop-all-missing":"cart-plus",
};

class Cook4MeRecipeHubPanelV30 extends BasePanel{
  constructor(){
    super();
    this._modernObserver=null;
    this._modernizePending=false;
  }

  connectedCallback(){
    super.connectedCallback();
    this._installModernObserver();
    this._modernizeSoon();
  }

  disconnectedCallback(){
    this._modernObserver?.disconnect();
    this._modernObserver=null;
    if(super.disconnectedCallback)super.disconnectedCallback();
  }

  _renderShell(){
    super._renderShell();
    this._ensureModernStyles();
    this._installModernObserver();
    this._modernizeSoon();
  }

  _renderTabs(){
    super._renderTabs();
    this._modernizeTabs();
  }

  _renderTab(){
    super._renderTab();
    this._modernizeSoon();
  }

  _updateHeader(){
    super._updateHeader();
    this._modernizeSoon();
  }

  _ensureModernStyles(){
    if(this.shadowRoot?.getElementById("cook4meModernV30"))return;
    const style=document.createElement("style");
    style.id="cook4meModernV30";
    style.textContent=`
      :host{
        --rx-radius-xl:22px;
        --rx-radius-lg:17px;
        --rx-radius-md:13px;
        --rx-shadow-sm:0 2px 10px rgba(0,0,0,.07);
        --rx-shadow-md:0 10px 30px rgba(0,0,0,.11);
        --rx-shadow-lg:0 24px 70px rgba(0,0,0,.22);
        --rx-surface:color-mix(in srgb,var(--card-background-color) 94%,var(--primary-color) 6%);
        --rx-surface-soft:color-mix(in srgb,var(--card-background-color) 88%,var(--secondary-background-color) 12%);
      }
      *{scrollbar-color:color-mix(in srgb,var(--primary-color) 38%,transparent) transparent}
      .wrap{max-width:1780px!important;padding:clamp(10px,2vw,22px)!important}
      .card{
        border-radius:var(--rx-radius-xl)!important;
        border:1px solid color-mix(in srgb,var(--divider-color) 72%,transparent)!important;
        background:linear-gradient(145deg,var(--card-background-color),var(--rx-surface))!important;
        box-shadow:var(--rx-shadow-sm);
      }
      .top{gap:12px!important;align-items:stretch!important}
      #status.rx-status{
        position:relative;overflow:hidden;isolation:isolate;
        background:
          radial-gradient(circle at 8% 0%,color-mix(in srgb,var(--primary-color) 18%,transparent),transparent 42%),
          linear-gradient(145deg,var(--card-background-color),var(--rx-surface))!important;
      }
      #status.rx-status::after{
        content:"";position:absolute;right:-45px;top:-70px;width:180px;height:180px;border-radius:50%;z-index:-1;
        background:color-mix(in srgb,var(--primary-color) 8%,transparent);filter:blur(2px)
      }
      #status .pot{
        width:48px;height:48px;border-radius:15px;display:grid;place-items:center;font-size:0!important;
        color:var(--primary-color);background:color-mix(in srgb,var(--primary-color) 12%,var(--card-background-color));
        border:1px solid color-mix(in srgb,var(--primary-color) 25%,transparent);box-shadow:inset 0 1px 0 rgba(255,255,255,.16)
      }
      #status .pot ha-icon{--mdc-icon-size:28px}
      #status .status-title{font-size:clamp(19px,2vw,23px)!important;letter-spacing:-.02em}
      #status .status-main>div:nth-child(2)>span{display:inline-flex;padding:3px 8px;border-radius:999px;font-size:12px;font-weight:700;background:var(--secondary-background-color)}
      .queue-banner{border-radius:15px!important;box-shadow:inset 0 1px 0 rgba(255,255,255,.08)}

      .tabs{
        position:sticky!important;top:0;z-index:50;
        display:flex!important;flex-wrap:nowrap!important;gap:7px!important;overflow-x:auto;scrollbar-width:none;
        margin:14px 0!important;padding:8px!important;border-radius:18px;
        border:1px solid color-mix(in srgb,var(--divider-color) 72%,transparent);
        background:color-mix(in srgb,var(--primary-background-color) 82%,transparent)!important;
        backdrop-filter:blur(18px) saturate(1.25);-webkit-backdrop-filter:blur(18px) saturate(1.25);
        box-shadow:0 7px 24px rgba(0,0,0,.08)
      }
      .tabs::-webkit-scrollbar{display:none}
      .tab{
        flex:0 0 auto!important;display:inline-flex!important;align-items:center!important;gap:8px!important;
        min-height:44px;border-radius:13px!important;padding:9px 13px!important;font-weight:650!important;
        border:1px solid transparent!important;background:transparent!important;box-shadow:none!important;
        transition:background .18s ease,color .18s ease,transform .18s ease,box-shadow .18s ease!important
      }
      .tab ha-icon{--mdc-icon-size:20px}
      .tab:hover{transform:translateY(-1px);background:color-mix(in srgb,var(--rx,var(--primary-color)) 10%,transparent)!important;box-shadow:none!important}
      .tab.active{
        color:#fff!important;background:var(--rx,var(--primary-color))!important;
        box-shadow:0 6px 16px color-mix(in srgb,var(--rx,var(--primary-color)) 28%,transparent)!important
      }

      button.btn,.btn{
        display:inline-flex!important;align-items:center!important;justify-content:center!important;gap:8px!important;
        border-radius:12px!important;font-weight:650;letter-spacing:.005em;
        border:1px solid color-mix(in srgb,var(--primary-color) 26%,transparent)!important;
        box-shadow:0 3px 10px color-mix(in srgb,var(--primary-color) 13%,transparent);
        transition:transform .15s ease,box-shadow .15s ease,filter .15s ease,background .15s ease!important
      }
      button.btn:hover:not(:disabled),.btn:hover:not(:disabled){transform:translateY(-1px);box-shadow:0 7px 17px color-mix(in srgb,var(--primary-color) 18%,transparent);filter:saturate(1.04)}
      button.btn:active:not(:disabled),.btn:active:not(:disabled){transform:translateY(0) scale(.985)}
      .btn.secondary{
        background:color-mix(in srgb,var(--card-background-color) 82%,var(--secondary-background-color) 18%)!important;
        color:var(--primary-text-color)!important;border-color:color-mix(in srgb,var(--divider-color) 78%,transparent)!important;box-shadow:none
      }
      .btn.danger{box-shadow:0 3px 10px color-mix(in srgb,var(--error-color,#db4437) 18%,transparent)}
      .btn:focus-visible,.tab:focus-visible,.ingredient-pill:focus-visible,.step-ingredient:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{
        outline:3px solid color-mix(in srgb,var(--primary-color) 33%,transparent)!important;outline-offset:2px!important
      }
      .rx-leading-icon{--mdc-icon-size:18px;flex:0 0 auto}
      .rx-icon-only{width:40px!important;min-width:40px!important;min-height:40px!important;height:40px!important;padding:0!important;border-radius:50%!important;flex:0 0 40px!important}
      .rx-icon-only .rx-leading-icon{--mdc-icon-size:20px}

      input,select,textarea{
        border-radius:12px!important;border:1px solid color-mix(in srgb,var(--divider-color) 82%,transparent)!important;
        background:color-mix(in srgb,var(--card-background-color) 92%,var(--secondary-background-color) 8%)!important;
        transition:border-color .15s ease,box-shadow .15s ease,background .15s ease!important
      }
      input:hover,select:hover,textarea:hover{border-color:color-mix(in srgb,var(--primary-color) 35%,var(--divider-color))!important}
      input:focus,select:focus,textarea:focus{border-color:var(--primary-color)!important;box-shadow:0 0 0 3px color-mix(in srgb,var(--primary-color) 12%,transparent)!important}
      .field label{font-weight:650!important;font-size:12.5px!important;letter-spacing:.01em}
      input[type="checkbox"]{accent-color:var(--primary-color)}

      .recipe{
        position:relative;border-radius:22px!important;overflow:hidden;padding:16px!important;
        box-shadow:var(--rx-shadow-sm)!important;transform:translateZ(0);
        transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease!important
      }
      .recipe:hover{transform:translateY(-3px)!important;box-shadow:var(--rx-shadow-md)!important}
      .recipe>.media{margin:-16px -16px 2px!important;width:calc(100% + 32px)!important;border-radius:21px 21px 14px 14px!important}
      .recipe>.media::after{content:"";position:absolute;inset:auto 0 0;height:42%;pointer-events:none;background:linear-gradient(transparent,rgba(0,0,0,.17))}
      .recipe h3{font-size:18px!important;line-height:1.25;letter-spacing:-.015em;margin-top:2px!important}
      .recipe .actions{gap:7px!important;padding-top:3px;border-top:1px solid color-mix(in srgb,var(--divider-color) 64%,transparent);margin-top:5px!important;padding-top:11px}
      .recipe .actions>.btn{flex:1 1 112px}
      .rx-card-overlay-actions{position:absolute;top:10px;right:10px;z-index:4;display:flex;gap:7px}
      .rx-card-overlay-actions .btn{
        color:var(--primary-text-color)!important;background:color-mix(in srgb,var(--card-background-color) 82%,transparent)!important;
        border-color:color-mix(in srgb,var(--divider-color) 48%,transparent)!important;box-shadow:0 4px 14px rgba(0,0,0,.17)!important;
        backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)
      }
      .rx-card-overlay-actions .btn:hover{background:var(--card-background-color)!important}
      .chip{border:1px solid color-mix(in srgb,var(--divider-color) 58%,transparent);font-weight:600;line-height:1.15}

      .ingredient-mini{gap:6px!important}
      .ingredient-pill,.step-ingredient{
        display:inline-flex!important;align-items:center!important;gap:6px!important;font-weight:600!important;
        transition:transform .14s ease,box-shadow .14s ease,border-color .14s ease!important
      }
      .ingredient-pill:hover,.step-ingredient:hover{transform:translateY(-1px);box-shadow:0 4px 10px rgba(0,0,0,.09)}
      .ingredient-pill ha-icon,.step-ingredient ha-icon{--mdc-icon-size:15px}
      .ingredient-status-list>div{border:1px solid transparent!important;transition:transform .14s ease,border-color .14s ease,background .14s ease}
      .ingredient-status-list>div:hover{transform:translateX(2px);border-color:color-mix(in srgb,var(--primary-color) 25%,transparent)!important}

      .detail{border-color:color-mix(in srgb,var(--primary-color) 40%,var(--divider-color))!important;box-shadow:var(--rx-shadow-md)!important}
      .detail-head{align-items:center!important}
      .detail h2{font-size:clamp(22px,3vw,30px)!important;letter-spacing:-.025em}
      .step{
        grid-template-columns:36px minmax(0,1fr)!important;gap:10px!important;margin:8px 0!important;padding:13px!important;
        border:1px solid color-mix(in srgb,var(--divider-color) 65%,transparent)!important;border-radius:15px!important;
        background:color-mix(in srgb,var(--card-background-color) 91%,var(--secondary-background-color) 9%)!important
      }
      .step:first-child{border-top:1px solid color-mix(in srgb,var(--divider-color) 65%,transparent)!important}
      .step-num{width:30px;height:30px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:color-mix(in srgb,var(--primary-color) 12%,transparent);color:var(--primary-color)!important;font-weight:800}

      .rx-heading{display:flex!important;align-items:center!important;gap:9px!important}
      .rx-heading-icon{--mdc-icon-size:22px;color:var(--primary-color);flex:0 0 auto}
      h2.rx-heading .rx-heading-icon{width:36px;height:36px;padding:7px;border-radius:11px;background:color-mix(in srgb,var(--primary-color) 10%,transparent)}

      .notice{border:1px solid color-mix(in srgb,var(--primary-color) 17%,var(--divider-color))!important;border-left:4px solid var(--primary-color)!important;border-radius:12px!important}
      .notice.error{border-left-color:var(--error-color,#db4437)!important}
      .empty{border:1px dashed color-mix(in srgb,var(--divider-color) 78%,transparent);border-radius:15px;background:color-mix(in srgb,var(--secondary-background-color) 35%,transparent)}

      .rx-overlay{backdrop-filter:blur(7px);-webkit-backdrop-filter:blur(7px);animation:rxFade .15s ease both}
      .rx-dialog{border-radius:24px!important;box-shadow:var(--rx-shadow-lg)!important;animation:rxPop .18s cubic-bezier(.2,.8,.2,1) both}
      .rx-progress{height:9px!important;background:color-mix(in srgb,var(--secondary-background-color) 76%,var(--divider-color) 24%)!important}
      .rx-progress>div{border-radius:999px;background:linear-gradient(90deg,var(--primary-color),color-mix(in srgb,var(--primary-color) 55%,#fff 45%))!important}
      @keyframes rxFade{from{opacity:0}to{opacity:1}}
      @keyframes rxPop{from{opacity:0;transform:translateY(8px) scale(.985)}to{opacity:1;transform:none}}

      .book-heading{gap:10px!important}.book-heading .count{font-weight:700;padding:4px 8px!important}
      .queue-banner{background:linear-gradient(135deg,color-mix(in srgb,var(--warning-color,#f9a825) 12%,var(--card-background-color)),var(--card-background-color))!important}
      .draft-row,.rx-list-row{border-radius:12px}.rx-list-row{padding:10px!important}

      @media(max-width:700px){
        .tabs{margin:10px -2px!important;border-radius:15px;padding:6px!important}
        .tab{min-height:42px;padding:8px 11px!important}.tab span:last-child{font-size:13px}
        .recipe>.media{margin:-16px -16px 2px!important;width:calc(100% + 32px)!important}
        .recipe .actions>.btn{width:auto!important;flex:1 1 120px!important}
        .rx-card-overlay-actions .btn{width:40px!important}
        .detail{padding:14px!important}.detail-head{align-items:flex-start!important}
      }
      @media(prefers-reduced-motion:reduce){
        *,*::before,*::after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}
      }
    `;
    this.shadowRoot.appendChild(style);
  }

  _installModernObserver(){
    if(this._modernObserver||!this.shadowRoot)return;
    this._modernObserver=new MutationObserver(()=>this._modernizeSoon());
    this._modernObserver.observe(this.shadowRoot,{childList:true,subtree:true});
  }

  _modernizeSoon(){
    if(this._modernizePending)return;
    this._modernizePending=true;
    queueMicrotask(()=>{
      this._modernizePending=false;
      if(!this.shadowRoot)return;
      this._modernizeTabs();
      this._modernizeStatus();
      this._modernizeButtons(this.shadowRoot);
      this._modernizeCards(this.shadowRoot);
      this._modernizeIngredients(this.shadowRoot);
      this._modernizeHeadings(this.shadowRoot);
    });
  }

  _newIcon(icon,extraClass=""){
    const node=document.createElement("ha-icon");
    node.setAttribute("icon",`mdi:${icon}`);
    node.setAttribute("aria-hidden","true");
    node.className=extraClass;
    return node;
  }

  _stripLegacyGlyphs(button){
    for(const node of [...button.childNodes]){
      if(node.nodeType!==Node.TEXT_NODE)continue;
      node.textContent=String(node.textContent||"")
        .replace(/[★☆📚📤🛒⏳📷🥕✨🔄▶️▶⏹️⏹❌✕×]+/gu,"")
        .replace(/^\s+/,"");
    }
  }

  _setButtonIcon(button,icon,{iconOnly=false}={}){
    if(!button||!icon)return;
    if(button.dataset.rxIcon!==icon){
      button.querySelector(":scope > ha-icon.rx-leading-icon")?.remove();
      this._stripLegacyGlyphs(button);
      const node=this._newIcon(icon,"rx-leading-icon");
      button.prepend(node);
      button.dataset.rxIcon=icon;
    }
    if(iconOnly){
      button.classList.add("rx-icon-only");
      const label=button.getAttribute("title")||button.getAttribute("aria-label")||button.textContent.trim();
      if(label)button.setAttribute("aria-label",label);
      for(const node of [...button.childNodes]){
        if(node.nodeType===Node.TEXT_NODE)node.textContent="";
      }
    }
  }

  _modernizeTabs(){
    const tabs=this.shadowRoot?.getElementById("tabs");
    if(!tabs)return;
    tabs.querySelectorAll("[data-tab]").forEach(button=>{
      const tab=String(button.dataset.tab||"");
      const icon=TAB_ICONS[tab]||"circle-small";
      if(button.dataset.rxTabIcon===icon)return;
      const label=button.textContent.trim()||this._t(tab);
      button.textContent="";
      button.append(this._newIcon(icon,"rx-tab-icon"));
      const span=document.createElement("span");span.textContent=label;button.append(span);
      button.dataset.rxTabIcon=icon;
      button.setAttribute("title",label);
    });
  }

  _buttonIcon(button){
    const action=String(button.dataset?.action||"");
    if(action){
      if(action==="favorite")return button.textContent.includes("★")?"heart":"heart-outline";
      return ACTION_ICONS[action]||null;
    }
    if(button.hasAttribute("data-detail-favorite"))return this._isFavorite?.(this._opened)?"heart":"heart-outline";
    if(button.hasAttribute("data-detail-list"))return"format-list-bulleted-square";
    if(button.hasAttribute("data-detail-send"))return"pot-steam-outline";
    const id=String(button.id||"").toLowerCase();
    const classes=button.classList;
    if(classes.contains("house-remove"))return"close";
    if(id==="refresh"||id.includes("refresh"))return"refresh";
    if(id.includes("search"))return"magnify";
    if(id.includes("suggest")||id.includes("recommend"))return"silverware-fork-knife";
    if(id.includes("scan")&&id.includes("expiry"))return"calendar-search";
    if(id.includes("scan"))return"barcode-scan";
    if(id.includes("camera"))return"camera-outline";
    if(id.includes("shopping")&&id.includes("add"))return"cart-plus";
    if(id.includes("shopping"))return"cart-outline";
    if(id.includes("favorite"))return"heart-outline";
    if(id.includes("save"))return"content-save-outline";
    if(id.includes("update"))return"content-save-edit-outline";
    if(id.includes("add"))return"plus";
    if(id.includes("remove")||id.includes("delete"))return"trash-can-outline";
    if(id.includes("clear"))return"broom";
    if(id.includes("cancel")||id.includes("close")||id.includes("stop"))return"close-circle-outline";
    if(id.includes("generate"))return"creation-outline";
    if(id.includes("run")||id.includes("start"))return"play-circle-outline";
    if(id.includes("reset"))return"restore";
    if(id.includes("open"))return"open-in-new";
    if(id.includes("queue"))return"clock-outline";
    return null;
  }

  _modernizeButtons(root){
    root.querySelectorAll("button").forEach(button=>{
      if(button.classList.contains("tab"))return;
      const icon=this._buttonIcon(button);
      if(!icon)return;
      const action=String(button.dataset?.action||"");
      const cardIconOnly=Boolean(button.closest("article.recipe")&&(action==="favorite"||action==="recipe-list"));
      this._setButtonIcon(button,icon,{iconOnly:cardIconOnly});
    });
  }

  _modernizeCards(root){
    root.querySelectorAll("article.recipe").forEach(card=>{
      if(card.dataset.rxCardModern==="1")return;
      card.dataset.rxCardModern="1";
      const media=card.querySelector(":scope > .media");
      const fav=card.querySelector('.actions [data-action="favorite"]');
      const list=card.querySelector('.actions [data-action="recipe-list"]');
      if(media&&(fav||list)){
        const rail=document.createElement("div");rail.className="rx-card-overlay-actions";
        if(fav)rail.appendChild(fav);
        if(list)rail.appendChild(list);
        media.appendChild(rail);
      }
    });
  }

  _modernizeIngredients(root){
    root.querySelectorAll(".ingredient-pill").forEach(button=>{
      if(button.dataset.rxIngredientIcon)return;
      let icon="food-apple-outline";
      if(button.classList.contains("c100"))icon="check-circle-outline";
      else if(button.classList.contains("cpartial"))icon="circle-slice-4";
      else if(button.classList.contains("czero"))icon="cart-outline";
      else if(button.classList.contains("cstaple"))icon="infinity";
      button.prepend(this._newIcon(icon,"rx-leading-icon"));
      button.dataset.rxIngredientIcon=icon;
    });
    root.querySelectorAll(".step-ingredient").forEach(button=>{
      if(button.dataset.rxIngredientIcon)return;
      this._stripLegacyGlyphs(button);
      button.prepend(this._newIcon("food-variant","rx-leading-icon"));
      button.dataset.rxIngredientIcon="food-variant";
    });
  }

  _headingIconFor(text){
    const value=String(text||"").trim().toLocaleLowerCase();
    const pairs=[
      ["todayMeal","calendar-today-outline"],["todayResults","silverware-fork-knife"],
      ["favorites","heart-outline"],["recipeList","format-list-bulleted-square"],["book","book-heart-outline"],
      ["myRecipeBuilder","notebook-edit-outline"],["aiQueue","creation-outline"],
      ["household","account-group-outline"],["mealHistory","chart-line"],["nutrition","nutrition"],
      ["shopping","cart-outline"],["ingredientInfo","food-apple-outline"],
    ];
    for(const [key,icon] of pairs){
      const label=String(this._t(key)||"").trim().toLocaleLowerCase();
      if(label&&(value===label||value.startsWith(label)))return icon;
    }
    return null;
  }

  _modernizeHeadings(root){
    root.querySelectorAll("h2,h3").forEach(heading=>{
      if(heading.dataset.rxHeading==="1")return;
      const icon=this._headingIconFor(heading.textContent);
      if(!icon)return;
      heading.prepend(this._newIcon(icon,"rx-heading-icon"));
      heading.classList.add("rx-heading");
      heading.dataset.rxHeading="1";
    });
  }

  _modernizeStatus(){
    const status=this.shadowRoot?.getElementById("status");
    if(!status)return;
    status.classList.add("rx-status");
    const pot=status.querySelector(".pot");
    if(pot&&pot.dataset.rxPot!=="1"){
      pot.textContent="";
      pot.append(this._newIcon("pot-steam-outline"));
      pot.dataset.rxPot="1";
    }
    const queue=status.querySelector(".queue-banner strong");
    if(queue&&queue.dataset.rxQueueIcon!=="1"){
      queue.textContent=queue.textContent.replace(/^\s*⏳\s*/u,"");
      queue.prepend(this._newIcon("clock-alert-outline","rx-leading-icon"));
      queue.classList.add("rx-heading");
      queue.dataset.rxQueueIcon="1";
    }
  }
}

customElements.define("cook4me-recipe-hub-panel-v30",Cook4MeRecipeHubPanelV30);
