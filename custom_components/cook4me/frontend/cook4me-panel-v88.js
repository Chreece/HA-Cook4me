import "./cook4me-panel-v87.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v87');
class Cook4MeRecipeHubPanelV88 extends BasePanel{
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.16.12');return result;}
 _v79Reference(ref){
  const html=super._v79Reference(ref);
  if(ref?.source!=='retail_snapshot')return html;
  let url;try{url=new URL(ref.sourceUrl);}catch{return html;}
  if(url.protocol!=='https:'||url.hostname!=='www.dallmayr-versand.de'||url.username||url.password||url.port)return html;
  const node=this._v67Dom(html),detail=node.querySelector('[data-v87-reference]');
  if(!detail)return html;
  const link=document.createElement('a');link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';link.textContent='www.dallmayr-versand.de ↗';
  detail.append(' · ',link);return node.innerHTML;
 }
}
customElements.define('cook4me-recipe-hub-panel-v88',Cook4MeRecipeHubPanelV88);
