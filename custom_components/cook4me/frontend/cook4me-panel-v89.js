import "./cook4me-panel-v88.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v88');
function extraEvidenceUrl(value){
 try{const url=new URL(value);return url.protocol==='https:'&&!url.username&&!url.password&&!url.port&&['www.africshopping.com','www.clubhouseforchefs.ca','www.alnatura.de'].includes(url.hostname)?url:null;}catch{return null;}
}
function addEvidenceLink(detail,url){
 if(!detail||!url||detail.querySelector('a'))return;
 const link=document.createElement('a');link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';link.textContent=` ${url.hostname} ↗`;detail.append(link);
}
class Cook4MeRecipeHubPanelV89 extends BasePanel{
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.16.13');return result;}
 _v79Reference(ref){
  const node=this._v67Dom(super._v79Reference(ref));
  if(ref?.source==='retail_snapshot')addEvidenceLink(node.querySelector('[data-v87-reference]'),extraEvidenceUrl(ref.sourceUrl));
  return node.innerHTML;
 }
 _v79CostHtml(recipe,state){
  const node=this._v67Dom(super._v79CostHtml(recipe,state));
  node.querySelectorAll('.v79-evidence>div').forEach((element,index)=>{
   addEvidenceLink(element.querySelector('[data-v86-quantity-estimate]'),extraEvidenceUrl(state.cost?.ingredients?.[index]?.quantityEstimate?.sourceUrl));
  });
  return node.innerHTML;
 }
}
customElements.define('cook4me-recipe-hub-panel-v89',Cook4MeRecipeHubPanelV89);
