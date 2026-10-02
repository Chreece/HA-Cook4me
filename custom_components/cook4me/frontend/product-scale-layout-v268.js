// Product-capture layout refinement: keep container tare controls with weighing.
export const ProductScaleLayoutMixin=Base=>class extends Base{
 _v154DecorateProductContainer(...args){
  const result=super._v154DecorateProductContainer(...args);
  const dialog=this._v78Dialog;
  const block=dialog?.querySelector?.('[data-v154-container-field]');
  const quantityField=dialog?.querySelector?.('main [data-draft="quantity"]')?.closest?.('.field, label');
  if(block&&quantityField){
   // Move the existing controls instead of cloning them so the v154 listeners,
   // selected container and deduct-tare state remain exactly the same.
   if(quantityField.nextElementSibling!==block)quantityField.insertAdjacentElement('afterend',block);
   block.classList.add('v268-scale-container');
  }
  this._v268ScaleLayoutStyles();
  return result;
 }
 _v268ScaleLayoutStyles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v268ProductScaleLayoutStyles'))return;
  const style=document.createElement('style');
  style.id='v268ProductScaleLayoutStyles';
  style.textContent=`
   .v112-editor [data-v154-container-field].v268-scale-container{
    grid-column:1 / -1;
    width:100%;
    box-sizing:border-box;
    margin:2px 0 8px!important;
    padding:10px 0 0;
    border-top:1px solid var(--divider-color);
   }
   .v112-editor [data-v154-container-field].v268-scale-container .field{
    margin:0;
   }
  `;
  this.shadowRoot.append(style);
 }
};
