import './cook4me-panel-v114.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v114');
class Cook4MeRecipeHubPanelV115 extends BasePanel{
 _v114Picker(){
  const d=this._v78Draft;
  if(d&&!d.ingredient&&d.ingredientLinks?.length)d.ingredient=this._v112Local(d.ingredientLinks[0]);
  super._v114Picker();
 }
 _v112PaintTotal(){
  super._v112PaintTotal();
  const d=this._v78Draft,place=this._v78Dialog?.querySelector('[data-v112-details]>span:last-of-type');
  if(d&&place)place.textContent=this._v78Locations().find(row=>row.id===d.storageLocationId)?.name||this._v78Text('choosePlace');
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.17.19');return result;}
}
customElements.define('cook4me-recipe-hub-panel-v115',Cook4MeRecipeHubPanelV115);
