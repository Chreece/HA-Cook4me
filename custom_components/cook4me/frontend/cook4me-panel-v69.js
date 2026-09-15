import "./cook4me-panel-v68.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v68");
const BUILD="2026.9.15.11";

class Cook4MeRecipeHubPanelV69 extends BasePanel{
 _v69PhotoActions(photo,actions){
  if(!photo||!actions)return;
  const media=document.createElement("div");media.className="rx-v69-media";
  photo.before(media);media.append(photo,actions);actions.classList.add("rx-v69-overlay");
 }
 _recipeCard(recipe,custom=false){
  const html=super._recipeCard(recipe,custom);if(!html)return html;
  const node=this._v67Dom(html),card=node.firstElementChild;
  const title=card.querySelector(".rx-v66-title");if(title)card.prepend(title);
  const actions=card.querySelector(".rx-v67-photo-actions"),expand=title?.querySelector('[data-v66-action="expand"]');
  if(actions&&expand)actions.appendChild(expand);
  this._v69PhotoActions(card.querySelector("[data-v66-photo]"),actions);
  return node.innerHTML;
 }
 _renderRecipeDialog(){
  super._renderRecipeDialog();const overlay=this._v63RecipeDialog;if(!overlay)return;
  this._v69PhotoActions(overlay.querySelector(".rx-v66-full-photo"),overlay.querySelector(".rx-v67-photo-actions"));
  this._ensureV69Styles();
 }
 _renderTab(){const result=super._renderTab();this.setAttribute("data-cook4me-build",BUILD);this._ensureV69Styles();return result;}
 _ensureV69Styles(){
  if(!this.shadowRoot||this.shadowRoot.getElementById("cook4meV69Styles"))return;
  const style=document.createElement("style");style.id="cook4meV69Styles";style.textContent=`
   .rx-v66-recipe>.rx-v66-title{padding:14px;align-items:center}.rx-v66-title h3{line-height:1.35}
   .rx-v69-media{position:relative;isolation:isolate;min-width:0;min-height:180px;background:var(--secondary-background-color);overflow:hidden}
   .rx-v69-media>[data-v66-photo]{position:relative;z-index:0}.rx-v69-media .media{margin:0!important;border-radius:0!important;min-height:180px}
   .rx-v69-media .media-placeholder{min-height:180px}.rx-week-day .rx-v69-media img.cover{height:200px}
   .rx-v69-media>.rx-v69-overlay{position:absolute;z-index:1;inset:auto 0 0;padding:18px 8px 8px!important;display:flex;flex-wrap:wrap;align-items:center;gap:6px;background:linear-gradient(transparent,rgba(0,0,0,.5));pointer-events:none}
   .rx-v69-overlay .rx-v66-actions{display:contents;margin:0!important}
   .rx-v69-overlay button,.rx-v69-overlay select{pointer-events:auto;opacity:.5;transition:opacity .15s ease;background:rgba(20,20,20,.94)!important;color:white!important;border:1px solid rgba(255,255,255,.45)!important;box-sizing:border-box}
   .rx-v69-overlay .rx-v66-icon{flex:0 0 36px;min-width:36px!important;width:36px;height:36px;padding:6px!important;border-radius:10px}
   .rx-v69-overlay select{flex:1 1 100px;min-width:100px;max-width:160px;height:36px;min-height:36px;padding:4px;border-radius:8px}
   .rx-v69-overlay:has(button:hover,select:hover) button,.rx-v69-overlay:has(button:hover,select:hover) select,.rx-v69-overlay:focus-within button,.rx-v69-overlay:focus-within select,.rx-v69-overlay button:active,.rx-v69-overlay select:active{opacity:1}
   .rx-v69-overlay button:disabled{opacity:.25}.rx-v69-overlay button:focus-visible,.rx-v69-overlay select:focus-visible{outline:2px solid white;outline-offset:2px}
   .rx-v66-fullscreen .rx-v69-media{border-radius:12px}.rx-v66-fullscreen .rx-v69-media .rx-v66-full-photo .media{min-height:180px!important}
   @media(prefers-reduced-motion:reduce){.rx-v69-overlay button,.rx-v69-overlay select{transition:none}}
  `;this.shadowRoot.appendChild(style);
 }
}
customElements.define("cook4me-recipe-hub-panel-v69",Cook4MeRecipeHubPanelV69);
