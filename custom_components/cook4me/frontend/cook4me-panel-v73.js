import "./cook4me-panel-v72.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v72");
const BUILD="2026.9.15.15";

class Cook4MeRecipeHubPanelV73 extends BasePanel{
 _renderTab(){const result=super._renderTab();this._ensureV73Styles();this.setAttribute('data-cook4me-build',BUILD);return result;}
 _bindCards(container,items,custom=false){super._bindCards(container,items,custom);this._ensureV73Styles();}
 _ensureV73Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#cook4meV73Styles'))return;
  const style=document.createElement('style');style.id='cook4meV73Styles';style.textContent=`
   /* 310px = 88px title + 220px photo + two 1px borders. Legacy recipe
      padding and flex gaps must not displace the photo below this frame. */
   article.card.recipe.rx-v66-recipe{padding:0!important;gap:0!important;border-width:1px;}
   article.card.recipe.rx-v66-recipe>.rx-v66-title,
   article.card.recipe.rx-v66-recipe>.rx-v69-media{margin:0;box-sizing:border-box;}
   article.card.recipe.rx-v66-recipe>.rx-v69-media{overflow:hidden;}
   article.card.recipe.rx-v66-recipe .rx-v66-photo,
   article.card.recipe.rx-v66-recipe .rx-v66-photo>.media{padding:0!important;margin:0!important;box-sizing:border-box;aspect-ratio:auto;}
   article.card.recipe.rx-v66-recipe .rx-v69-overlay{box-sizing:border-box;max-height:100%;overflow-y:auto;pointer-events:auto;}
  `;this.shadowRoot.appendChild(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v73',Cook4MeRecipeHubPanelV73);
