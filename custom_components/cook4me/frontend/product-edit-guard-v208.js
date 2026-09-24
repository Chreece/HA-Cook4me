// Guard asynchronous package opening above the retained compiled frontend.
export const ProductEditGuardMixin=Base=>class extends Base{
 async _v112EditLot(lotId){
  // Never replace an open or uncertain product transaction. A second click
  // while details are loading supersedes the first, not the other way around.
  if(this._v78Dialog)return;
  const context=this._prefKey(),tab=this._tab,request={};this._v112EditRequest=request;
  const current=()=>this._v112EditRequest===request&&context===this._prefKey()&&tab===this._tab&&this.isConnected!==false;
  let openedDialog=null;
  try{
   const product=await this._api('cook4me/v33/product_details',{entry_id:this._entryId,lot_id:lotId,language:this._uiIngredientLanguage()});
   if(!current()||this._v78Dialog)return;
   const opening=this._v78Open('manual'),dialog=this._v78Dialog,d=this._v78Draft;openedDialog=dialog;
   await opening;
   if(!current()||!d||d!==this._v78Draft||dialog!==this._v78Dialog||this._v78Dirty||this._v78Busy||this._v78Submitted)return;
   const lot=product.lot,paid=product.paidPrice;
   Object.assign(d,{...lot,quantity:lot.quantity,unit:product.unit,ingredient:product.ingredient,editLotId:lot.id,expectedVersion:product.version,productLocked:true,scanRecognized:true,scanPhase:'recognized',editorOpen:true,
    nutrition:product.nutrition?structuredClone(product.nutrition):{basisUnit:'',values:{}},labelNutrition:true,paidAmount:paid?.amount??'',paidCurrency:paid?.currency||d.paidCurrency,paidShop:paid?.location||'',paidBasisQuantity:paid?.basisQuantity??lot.quantity,paidBasisUnit:paid?.basisUnit||product.unit});
   this._v78Dirty=false;this._v78RenderCapture();this._v196Focus('main [data-draft="productName"]');
  }catch(error){if(current()&&(!this._v78Dialog||this._v78Dialog===openedDialog))this._message(String(error.message||error),true);}
  finally{if(this._v112EditRequest===request)this._v112EditRequest=null;}
 }
};
