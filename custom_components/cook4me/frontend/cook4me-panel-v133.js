const V132='cook4me-recipe-hub-panel-v132';
if(!customElements.get(V132))await import('./cook4me-panel-v132.js?v=2026.9.20.6');
const BasePanel=customElements.get(V132);
const DEVICE_ASSET_V133=new URL('./assets/device-v133.jpg?v=2026.9.20.7',import.meta.url).href;

const V133_TEXT={
 en:{noConnection:'No connection'},
 de:{noConnection:'Keine Verbindung'},
 el:{noConnection:'Χωρίς σύνδεση'}
};

class Cook4MeRecipeHubPanelV133 extends BasePanel{
 _v133Text(key){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return (V133_TEXT[lang]||V133_TEXT.en)[key]||V133_TEXT.en[key]||key;
 }
 _nutritionChips(values,compact=false){
  const html=super._nutritionChips(values,compact);
  if(!html)return html;
  const template=document.createElement('template');
  template.innerHTML=String(html);
  template.content.querySelectorAll('.v131-nutrient-gap').forEach(node=>node.remove());
  template.content.querySelectorAll('.chip').forEach(chip=>{
   const walker=document.createTreeWalker(chip,NodeFilter.SHOW_TEXT);
   let node;
   while((node=walker.nextNode())){
    const match=String(node.nodeValue||'').match(/-?\d+(?:[.,]\d+)?/);
    if(!match||match.index==null)continue;
    const index=match.index;
    const before=String(node.nodeValue||'').slice(0,index).replace(/\s+$/,'');
    const after=String(node.nodeValue||'').slice(index).replace(/^\s+/,'');
    const spacer=document.createElement('span');
    spacer.className='v133-nutrient-spacer';
    spacer.setAttribute('aria-hidden','true');
    node.nodeValue=before;
    node.parentNode?.insertBefore(spacer,node.nextSibling);
    node.parentNode?.insertBefore(document.createTextNode(after),spacer.nextSibling);
    break;
   }
  });
  return template.innerHTML;
 }
 _v132FixDeviceAsset(){
  const root=this.shadowRoot;
  const image=root?.querySelector('.v130-model-photo');
  if(!image)return;
  const model=image.closest('.v130-model');
  if(image.getAttribute('src')!==DEVICE_ASSET_V133){
   image.dataset.v133Loaded='';
   image.src=DEVICE_ASSET_V133;
  }
  const loaded=()=>{
   image.dataset.v133Loaded='true';
   model?.classList.remove('v132-model-image-error','v133-model-image-error');
  };
  const failed=()=>{
   image.dataset.v133Loaded='false';
   model?.classList.add('v133-model-image-error');
  };
  if(image.complete){
   if(image.naturalWidth>0)loaded();
   else failed();
  }else{
   image.addEventListener('load',loaded,{once:true});
   image.addEventListener('error',failed,{once:true});
  }
 }
 _v133OfflineScreen(){
  const entry=this._entry();
  if(!entry||this._v130Phase(entry)!=='offline')return;
  const root=this.shadowRoot?.getElementById('status');
  const model=root?.querySelector('.v130-model');
  const screen=root?.querySelector('.v130-live-screen');
  const strong=screen?.querySelector('.v130-screen-copy strong');
  const state=screen?.querySelector('.v130-screen-copy span');
  const symbol=screen?.querySelector('.v130-screen-symbol');
  model?.classList.add('v133-offline-screen');
  if(strong)strong.textContent=this._v130Text('offline');
  if(state)state.textContent=this._v133Text('noConnection');
  if(symbol)symbol.textContent='×';
 }
 _updateHeader(){
  super._updateHeader();
  this._v132FixDeviceAsset();
  this._v133OfflineScreen();
  this._v133Styles();
 }
 _renderShell(){
  super._renderShell();
  this._v132FixDeviceAsset();
  this._v133OfflineScreen();
  this._v133Styles();
 }
 _renderTab(){
  const result=super._renderTab();
  this._v132FixDeviceAsset();
  this._v133OfflineScreen();
  this._v133Styles();
  this.setAttribute('data-cook4me-build','2026.9.20.7');
  return result;
 }
 _v133Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v133Styles'))return;
  const style=document.createElement('style');
  style.id='v133Styles';
  style.textContent=`
   .v133-nutrient-spacer{display:inline-block;width:7px;flex:0 0 7px}
   .v130-model{
    isolation:isolate;
    background:radial-gradient(circle at 50% 49%,#d8dcdd 0%,#b8bec0 54%,#777f82 76%,transparent 83%);
   }
   .v130-model-photo{
    mix-blend-mode:multiply;
    filter:brightness(1.08) contrast(1.1);
    opacity:1!important;
   }
   .v130-model.v133-model-image-error .v130-model-photo{opacity:0!important}
   .v133-offline-screen .v130-live-screen{
    box-shadow:0 0 14px color-mix(in srgb,var(--error-color,#db4437) 28%,transparent),inset 0 0 0 1px rgba(255,255,255,.07);
   }
   .v133-offline-screen .v130-screen-symbol{color:var(--error-color,#db4437);text-shadow:0 0 10px color-mix(in srgb,var(--error-color,#db4437) 55%,transparent)}
   .v133-offline-screen .v130-screen-progress{display:none}
   .v133-offline-screen .v130-screen-copy span{color:var(--error-color,#db4437);opacity:.9}
  `;
  this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v133',Cook4MeRecipeHubPanelV133);
