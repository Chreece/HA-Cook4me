import './cook4me-panel-v112.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v112');
const RESTART={en:'Restart barcode scan',de:'Barcode-Scan neu starten',el:'Επανεκκίνηση σάρωσης barcode'};
class Cook4MeRecipeHubPanelV113 extends BasePanel{
 _v113CanRestart(){
  const d=this._v78Draft;
  // A failed recognition can be discarded. An uncertain save must keep its receipt.
  return !!d&&d.mode==='barcode'&&['notfound','error'].includes(d.scanPhase)&&!this._v78Busy&&!this._v78Submitted&&!d.editLotId&&!d.scanRecognized&&!d.productName&&!d.ingredient;
 }
 async _v113Restart(){
  if(!this._v113CanRestart())return;
  this._v112SkipBarcode='';this._v112LastSaved='';
  this._v111NewDraft('barcode');
  await this._v80Scan('barcode');
 }
 _v111Paint(){
  super._v111Paint();
  const c=this._v78Dialog,d=this._v78Draft,frame=c?.querySelector('[data-v111-frame]');if(!frame||!d)return;
  this._v113Styles();
  const apply=frame.querySelector('[data-v112-apply]');
  if(apply){
   let restart=frame.querySelector('[data-v113-restart]');
   if(!restart){
    apply.insertAdjacentHTML('beforebegin',this._v111Icon('data-v113-restart','restart',RESTART[this._uiIngredientLanguage()]||RESTART.en));
    restart=frame.querySelector('[data-v113-restart]');restart.onclick=()=>void this._v113Restart();
   }
   restart.hidden=!this._v113CanRestart();
  }
  const result=frame.querySelector('[data-v111-result]'),amount=result?.querySelector('.v111-amount');
  if(!amount||!d.scanRecognized)return;
  // Replace the old read-only date fact with a single editable field below amounts.
  const oldDate=result.querySelector('.v111-facts')?.firstElementChild;
  if(d.bestBefore&&oldDate?.tagName==='DIV'&&!oldDate.className&&!oldDate.hasAttribute('data-v112-price-summary'))oldDate.remove();
  const label=document.createElement('label');label.className='v113-expiry';
  label.textContent=this._v78Text('date');
  const input=document.createElement('input');input.type='date';input.dataset.v113Expiry='';input.value=d.bestBefore||'';input.disabled=!!this._v78Submitted;
  input.addEventListener('input',()=>{
   if(d!==this._v78Draft||this._v78Submitted)return;
   d.bestBefore=input.value;this._v78Dirty=true;
   const editor=c.querySelector('main [data-draft=bestBefore]');if(editor)editor.value=input.value;
  });
  label.append(input);amount.after(label);
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.17.17');return result;}
 _v113Styles(){
  if(this.shadowRoot.querySelector('#v113Styles'))return;
  const style=document.createElement('style');style.id='v113Styles';style.textContent=`
   .v111-bottom [data-v113-restart]{margin-left:auto!important}
   .v111-bottom [data-v113-restart]:not([hidden])+[data-v112-apply]{margin-left:0!important}
   .v113-expiry{display:flex;flex-direction:column;flex-shrink:0;gap:4px;font-size:.82rem}
   .v113-expiry input{box-sizing:border-box;width:100%;min-width:0;min-height:42px;color-scheme:dark}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v113',Cook4MeRecipeHubPanelV113);
