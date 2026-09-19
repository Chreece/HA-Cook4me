import './cook4me-panel-v123.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v123');
const V124_BULK_TEXT={
 en:{selectAll:'Select all',deselectAll:'Deselect all'},
 de:{selectAll:'Alle auswählen',deselectAll:'Alle abwählen'},
 el:{selectAll:'Επιλογή όλων',deselectAll:'Αποεπιλογή όλων'}
};

class Cook4MeRecipeHubPanelV124 extends BasePanel{
 _v124Text(key){
  const lang=String(this._hass?.language||document.documentElement.lang||'en').slice(0,2).toLowerCase();
  return V124_BULK_TEXT[lang]?.[key]||V124_BULK_TEXT.en[key]||key;
 }
 _v124SetGroup(inputs,checked){
  for(const input of inputs){
   if(input.checked===checked)continue;
   input.checked=checked;
   input.dispatchEvent(new Event('change',{bubbles:true}));
  }
 }
 _v124EnhanceFilterDialog(key){
  const overlay=this.shadowRoot?.querySelector(`[data-filter-dialog="${key}"]`);
  if(!overlay)return;
  const groups=new Map();
  overlay.querySelectorAll('input[type="checkbox"][data-list]').forEach(input=>{
   const name=input.dataset.list||'';
   if(!name)return;
   if(!groups.has(name))groups.set(name,[]);
   groups.get(name).push(input);
  });
  for(const [name,inputs] of groups){
   const labels=inputs.map(input=>input.closest('label')).filter(Boolean);
   labels.forEach(label=>label.classList.add('v124-check-item'));
   if(inputs.length<2||!labels.length)continue;
   const toolbar=document.createElement('div');
   toolbar.className='v124-check-actions';
   toolbar.dataset.v124Bulk=name;
   const select=document.createElement('button');
   select.type='button';
   select.className='btn secondary';
   select.dataset.v124SelectAll=name;
   select.textContent=this._v124Text('selectAll');
   select.onclick=()=>this._v124SetGroup(inputs,true);
   const clear=document.createElement('button');
   clear.type='button';
   clear.className='btn secondary';
   clear.dataset.v124DeselectAll=name;
   clear.textContent=this._v124Text('deselectAll');
   clear.onclick=()=>this._v124SetGroup(inputs,false);
   toolbar.append(select,clear);
   const first=labels[0],parent=first.parentElement;
   if(parent?.hasAttribute('data-ingredient-choices'))parent.before(toolbar);
   else first.before(toolbar);
  }
 }
 _showFilter(key){
  super._showFilter(key);
  this._v124EnhanceFilterDialog(key);
 }
 _renderTab(){
  const result=super._renderTab();
  this._v124Styles();
  this.setAttribute('data-cook4me-build','2026.9.19.3');
  return result;
 }
 _v124Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v124Styles'))return;
  const style=document.createElement('style');
  style.id='v124Styles';
  style.textContent=`
   [data-filter-dialog] .v124-check-item{margin:2px 0!important;gap:6px!important;min-height:28px;line-height:1.25}
   [data-filter-dialog] .v124-check-item input[type=checkbox]{margin:0;flex:0 0 auto}
   [data-filter-dialog] .v124-check-actions{display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin:3px 0 6px}
   [data-filter-dialog] .v124-check-actions .btn{min-height:32px!important;padding:4px 8px!important;font-size:12px}
   [data-filter-dialog] [data-ingredient-choices] .v124-check-item{margin:1px 0!important}
  `;
  this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v124',Cook4MeRecipeHubPanelV124);
