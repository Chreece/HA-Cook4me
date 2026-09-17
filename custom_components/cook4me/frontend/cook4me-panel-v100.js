import "./cook4me-panel-v99.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v99');
const FILTER_TABS=new Set(['today','week','official']);
const NAV=[['today','weather-sunny'],['week','calendar-week'],['official','magnify'],['book','book-open-page-variant-outline'],['mine','chef-hat'],['shopping','cart-outline'],['profile','home-heart']];

class Cook4MeRecipeHubPanelV100 extends BasePanel{
 _renderShell(){super._renderShell();this._v100Header();this._v100Layout();}
 _updateHeader(){super._updateHeader();this._v100Header();}
 _renderEntrySelect(){super._renderEntrySelect();this._v100Header();}
 _ensureCurrencyControl(){super._ensureCurrencyControl();this._v100Header();}
 _renderTabs(){super._renderTabs();this._v100Layout();}
 _modernizeTabs(){
  const tabs=this.shadowRoot?.querySelector('#tabs');if(!tabs)return;
  tabs.querySelector('[data-tab=ai]')?.remove();
  for(const [index,[key,icon]] of NAV.entries()){
   const button=tabs.querySelector(`[data-tab="${key}"]`);if(!button)continue;
   if(button.childNodes.length!==1||button.firstElementChild?.getAttribute('icon')!==`mdi:${icon}`){const node=document.createElement('ha-icon');node.setAttribute('icon',`mdi:${icon}`);node.setAttribute('aria-hidden','true');button.replaceChildren(node);}
   const label=this._t(key);button.title=label;button.setAttribute('aria-label',label);button.setAttribute('aria-pressed',String(this._tab===key));
   // Decoration is observed too. Moving already-ordered buttons causes a
   // self-sustaining mutation loop and eventually trips the UI guard.
   if(tabs.children[index]!==button)tabs.insertBefore(button,tabs.children[index]||null);
  }
 }
 _renderTab(){const result=super._renderTab();this._v100Header();this._v100Layout();this.setAttribute('data-cook4me-build','2026.9.17.4');return result;}
 _renderToday(c){super._renderToday(c);this._v100Layout();}
 _renderWeek(c){super._renderWeek(c);this._v100Layout();}
 _renderOfficial(c){super._renderOfficial(c);this._v100Layout();}
 _renderBook(c){super._renderBook(c);this._v100Layout();}
 _renderMineV28(c){super._renderMineV28(c);this._v100Layout();}
 _renderShopping(c){super._renderShopping(c);this._v100Layout();}
 _renderProfile(c){super._renderProfile(c);this._v100Layout();}
 _buttonIcon(button){return button.id==='v82RefreshPrices'||button.hasAttribute('data-v82-refresh-prices')?null:super._buttonIcon(button);}
 _v82RefreshButton(){
  super._v82RefreshButton();
  for(const button of this.shadowRoot?.querySelectorAll('#v82RefreshPrices,[data-v82-refresh-prices]')||[]){
   if(button.childNodes.length!==1||button.firstElementChild?.getAttribute('icon')!=='mdi:refresh'){
    const icon=document.createElement('ha-icon');icon.setAttribute('icon','mdi:refresh');icon.setAttribute('aria-hidden','true');button.replaceChildren(icon);
   }
  }
 }
 _v100Header(){
  const root=this.shadowRoot,top=root?.querySelector('.top'),status=root?.querySelector('#status'),actions=root?.querySelector('#refresh')?.closest('.toolbar');
  if(!top||!status||!actions)return;this._v100Styles();top.classList.add('v100-top');actions.classList.add('v100-global-actions');
  let device=top.querySelector('.v100-device');
  if(!device){device=document.createElement('div');device.className='v100-device';top.prepend(device);}
  if(status.parentElement!==device)device.prepend(status);
  // Device selection and send targets stay with the device, including when
  // an HA update rebuilds their controls. Only global display controls go right.
  for(const id of ['entrySelect','cook4meTargetDevicesControl']){
   const control=root.getElementById(id);if(control&&control.parentElement!==device)device.append(control);
  }
  const refresh=root.getElementById('refresh');refresh.hidden=true;refresh.tabIndex=-1;
  const state=status.querySelector('.status-main');if(state)for(const line of state.children)line.title=line.textContent;
  // Keep native currency options descriptive, but show a short code when closed.
  const field=root.querySelector('#cook4meCurrencyControl .rx-currency-field');
  if(field){
   let label=field.querySelector('[data-v100-currency]');if(!label){label=document.createElement('span');label.dataset.v100Currency='';label.setAttribute('aria-hidden','true');field.append(label);}
   const value=String(this._currencyState?.currency||this._weekState?.costSettings?.currency||this._currencyState?.defaultCurrency||'EUR');
   if(label.textContent!==value)label.textContent=value;
  }
 }
 _v100Layout(){
  const root=this.shadowRoot,tabs=root?.querySelector('#tabs'),c=root?.querySelector('#content');if(!tabs||!c)return;this._v100Styles();
  let row=root.querySelector('.v100-navigation');
  if(!row){row=document.createElement('div');row.className='v100-navigation';tabs.before(row);row.append(tabs);}
  for(const id of ['message','cook4meLoadStatus']){const notice=root.getElementById(id);if(notice&&(row.compareDocumentPosition(notice)&Node.DOCUMENT_POSITION_FOLLOWING))row.before(notice);}
  let filters=row.querySelector('.v100-filter-slot');
  if(!filters){filters=document.createElement('div');filters.className='v100-filter-slot';row.append(filters);}
  const bar=c.querySelector('.rx-shared-filters');
  if(FILTER_TABS.has(this._tab)){
   if(bar){filters.replaceChildren(bar);filters.dataset.v100Tab=this._tab;}
   else if(filters.dataset.v100Tab!==this._tab)filters.replaceChildren();
  }else filters.replaceChildren();
  filters.hidden=!filters.children.length;
  const button=c.querySelector('#todaySuggest,#generateWeek,#searchBtn');
  let section=button?.closest('section.card')||c.querySelector('[data-v100-section]');
  if(!section){
   // Other menus get the same heading area without moving their recipe lists
   // or changing the existing view-specific controls and event handlers.
   section=document.createElement('section');section.className='card';
   const heading=c.querySelector(':scope>h1,.v78-heading')||null;
   if(heading)section.append(heading);else{const title=document.createElement('h2');title.textContent=this._t(this._tab);section.append(title);}
   c.prepend(section);
  }
  section.dataset.v100Section=this._tab;
  if(!section.querySelector('h1,h2')){const title=document.createElement('h2');title.textContent=this._t(this._tab);(section.querySelector('.v93-menu-controls')||section).prepend(title);}
  c.classList.add('v100-content');row.dataset.v100Tab=this._tab;
  if(this._v100VisibleTab!==this._tab){
   this._v100VisibleTab=this._tab;
   const selected=tabs.querySelector(`[data-tab="${this._tab}"]`);
   if(selected){const left=selected.offsetLeft-tabs.offsetLeft;if(left<tabs.scrollLeft)tabs.scrollLeft=left;else if(left+selected.offsetWidth>tabs.scrollLeft+tabs.clientWidth)tabs.scrollLeft=left+selected.offsetWidth-tabs.clientWidth;}
  }
 }
 _v100Styles(){
  if(this.shadowRoot?.querySelector('#v100Styles'))return;
  const style=document.createElement('style');style.id='v100Styles';style.textContent=`
   .wrap>.top.v100-top{display:grid!important;grid-template-columns:minmax(0,1fr) auto!important;align-items:center!important;gap:12px!important;padding:10px 12px!important;min-height:76px;box-sizing:border-box;box-shadow:none}
   .v100-top .v100-device{min-width:0;display:grid;grid-template-columns:minmax(0,1fr);align-items:center;gap:6px}
   .v100-top #status.card{padding:0!important;margin:0!important;min-width:0;border:0!important;border-radius:0!important;box-shadow:none!important;background:transparent!important;overflow:visible}
   .v100-top #status::after{display:none!important}.v100-top #status .status{padding:0!important;gap:10px!important;min-height:52px}
   .v100-top #status .v81-cooker{width:64px;flex:0 0 64px;height:58px}.v100-top #status .status-main{flex:1 1 0;min-width:0;overflow:hidden}
   .v100-top #status .status-main>div{white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis;overflow-wrap:normal!important;word-break:normal!important;line-height:1.45}
   .v100-top #status .status-title{font-size:16px!important}.v100-top #status .v81-state-label{font-size:12px;margin:2px 0!important;font-weight:500}.v100-top #status .status-main>.muted{font-size:12px}.v100-top #status .v81-info-icon{display:none}
   .v100-top>.toolbar.v100-global-actions{display:flex!important;flex-wrap:nowrap!important;align-items:center!important;gap:6px!important;min-width:0;margin:0!important;padding:0!important}
   .v100-top #refresh{display:none!important}.v100-top #entrySelect{width:100%!important;max-width:320px!important;min-width:0!important;height:36px!important;min-height:36px!important;font-size:12px;padding:4px 24px 4px 8px!important}
   .v100-top #cook4meTargetDevicesControl{width:auto;max-width:100%;margin:0}.v100-top #cook4meTargetDevicesControl summary{min-width:0;min-height:36px;padding:4px 8px;font-size:12px}.v100-top #cook4meTargetDevicesControl .rx-v49-picker-body{left:0;right:auto;width:min(360px,calc(100vw - 40px))}
   .v100-top #cook4meUiLanguageControl,.v100-top #cook4meUiLanguageControl.rx-v38-globe>.field,.v100-top #cook4meUiLanguageControl.rx-v38-globe select{width:44px!important;min-width:44px!important;height:44px!important;min-height:44px!important}
   .v100-top #cook4meUiLanguageControl .rx-language-field::after{display:none!important}
   .v100-top #cook4meCurrencyControl{height:44px;flex:0 0 64px;width:64px}.v100-top #cook4meCurrencyControl .rx-currency-field{width:64px;min-width:64px;height:44px;justify-content:center}
   .v100-top #cook4meCurrencyControl select{position:absolute;inset:0;z-index:2;opacity:0;cursor:pointer;padding:0!important;height:44px;min-height:44px;width:100%}
   .v100-top #cook4meCurrencyControl ha-icon{display:none}.v100-top [data-v100-currency]{font-size:13px;font-weight:700;color:var(--primary-color);pointer-events:none}
   .v100-top #cook4meCurrencyControl .rx-currency-field:focus-within,.v100-top #cook4meUiLanguageControl:focus-within{outline:2px solid var(--primary-color);outline-offset:2px}
   .v100-top #v82RefreshPrices{width:44px!important;height:44px!important;min-height:44px;padding:8px!important;flex:0 0 44px}.v100-top #v82RefreshPrices ha-icon{--mdc-icon-size:23px;margin:0}
   .v100-navigation{display:flex;align-items:center;gap:12px;min-width:0;margin:12px 0 0;padding:6px 12px;background:var(--card-background-color);border:1px solid var(--divider-color);border-bottom:0;border-radius:18px 18px 0 0}
   .v100-navigation #tabs{display:flex!important;flex:1 1 auto;min-width:44px;max-width:100%;gap:5px!important;flex-wrap:nowrap!important;overflow-x:auto!important;overscroll-behavior-x:contain;scrollbar-width:none;margin:0!important;padding:5px 1px!important;border:0!important;border-radius:0!important;background:transparent!important;box-shadow:none!important}
   .v100-navigation #tabs::-webkit-scrollbar,.v100-filter-slot::-webkit-scrollbar{display:none}.v100-navigation #tabs .tab{flex:0 0 44px!important;min-width:44px!important;width:44px!important;height:44px!important;padding:8px!important;border-radius:12px!important}
   .v100-navigation #tabs{mask-image:linear-gradient(to right,#000 calc(100% - 12px),transparent);scroll-snap-type:x proximity}.v100-navigation #tabs .tab{scroll-snap-align:start}
   .v100-filter-slot{flex:0 1 auto;min-width:56px;max-width:55%;overflow-x:auto;overscroll-behavior-x:contain;scrollbar-width:none;padding:6px 2px}.v100-filter-slot[hidden]{display:none!important}
   .v100-filter-slot .rx-shared-filters.v93-filters{display:flex!important;align-items:center;flex-wrap:nowrap!important;gap:8px!important;width:max-content!important;max-width:none!important;margin:0!important;padding:0!important}
   .v100-filter-slot .v98-filter-group{flex:0 0 auto;flex-wrap:nowrap;max-width:none}.v100-filter-slot .v93-active-filters{flex:0 0 auto;flex-wrap:nowrap;max-width:none}.v100-filter-slot .v98-filter-group>.v93-filter-drawer{flex:0 0 auto;flex-wrap:nowrap;max-width:none}.v100-filter-slot [data-filter]{flex-shrink:0!important}
   .v100-filter-slot .v98-filter-group:has(>.v93-filter-drawer[hidden]){padding:0;border:0}
   #content.v100-content>[data-v100-section]{margin:0 0 14px!important;padding:12px 14px 14px!important;border:1px solid var(--divider-color)!important;border-top:0!important;border-radius:0 0 18px 18px!important;background:var(--card-background-color)!important;box-shadow:none!important;min-width:0}
   #content.v100-content>[data-v100-section] .v93-controls{padding:0!important;gap:0!important;display:block!important}.v100-content>[data-v100-section] .v93-menu-controls{display:flex;align-items:center;gap:10px;flex-wrap:wrap;width:100%;min-width:0}
   .v100-content>[data-v100-section] h1,.v100-content>[data-v100-section] h2{font-size:21px!important;line-height:1.35;margin:0!important;min-width:0;overflow-wrap:normal}
   .v100-content>[data-v100-section] .v78-heading{margin:0;padding:0}.v100-content>[data-v100-section] .v78-eyebrow{display:none}.v100-content>[data-v100-section] .v93-menu-controls #searchQ{min-width:0;flex:1 1 190px;max-width:100%}.v100-content>[data-v100-section] .toolbar .btn{width:auto;flex:0 0 auto}
   .v100-content>[data-v100-section] [data-v93-date],.v100-content>[data-v100-section] .v93-clock{font-size:12px}.v100-content>[data-v100-section] .v93-clock{gap:4px}
   @media(max-width:600px){
    .wrap>.top.v100-top{gap:8px!important;padding:8px 10px!important;min-height:72px}.v100-top #status .status{gap:6px!important}.v100-top #status .v81-cooker{width:48px;flex-basis:48px;height:48px}.v100-top #status .status-title{font-size:13px!important}.v100-top #status .v81-state-label{font-size:11px}.v100-top #status .status-main>.muted{display:none}
    .v100-navigation{gap:7px;padding:4px 8px;margin-top:10px}.v100-navigation #tabs{gap:4px!important}.v100-filter-slot{max-width:48%}#content.v100-content>[data-v100-section]{padding:10px 12px 12px!important}.v100-content>[data-v100-section] h1,.v100-content>[data-v100-section] h2{font-size:19px!important}
    .v100-content>[data-v100-section] .v93-menu-controls{gap:8px}.v100-content>[data-v100-section] .v93-menu-controls h2{flex:1 1 100%;gap:6px}.v100-content>[data-v100-section] .v93-menu-controls #todaySuggest{width:100%;justify-content:center;min-height:44px}.v100-content>[data-v100-section] .v93-menu-controls #searchQ{flex-basis:calc(100% - 116px)}
   }
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v100',Cook4MeRecipeHubPanelV100);
