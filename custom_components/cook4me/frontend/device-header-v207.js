// Compact presentation of the existing authorized live-device subscription.
const ICONS={idle:'mdi:check-circle-outline',ready:'mdi:check-circle-outline',done:'mdi:check-circle-outline',
 warming:'mdi:thermometer',cooking:'mdi:pot-steam',depressurization:'mdi:weather-windy',keep_warm:'mdi:thermometer',
 preparation:'mdi:hand-back-right-outline',add_ingredient:'mdi:plus-circle-outline',paused:'mdi:pause-circle-outline',
 stopped:'mdi:stop-circle-outline',updating:'mdi:update',offline:'mdi:cloud-off-outline',waiting:'mdi:sync',
 unavailable:'mdi:alert-circle-outline',unknown:'mdi:help-circle-outline'};
const clean=value=>typeof value==='string'?value.trim():'';
export function compactDeviceHeader(entry,view){
 const phase=clean(view?.phase)||'unknown';
 return {name:entry?.accessible===false?'Cook4Me':clean(entry?.state?.deviceName)||clean(entry?.title)||'Cook4Me',
  phase,label:clean(view?.label),icon:ICONS[phase]||ICONS.unknown};
}
// Keep the new text on the app theme, not inherited graphic-specific colours.
export const COMPACT_HEADER_CSS=`
 :host(.ui203) .wrap>.top.v100-top.ui207-header{min-height:0!important;padding:6px 12px!important;gap:10px!important;align-items:center!important}
 :host(.ui203) .ui207-header .v100-device{display:flex!important;align-items:center!important;flex-wrap:wrap;gap:6px 12px!important;min-width:0}
 :host(.ui203) .ui207-header #status{flex:1 1 180px;min-width:0!important}
 :host(.ui203) .ui207-header .v130-device-summary.ui207-device{display:flex!important;align-items:center!important;gap:10px!important;min-height:44px!important;min-width:0;padding:0!important;cursor:pointer}
 :host(.ui203) .ui207-device>ha-icon{flex:0 0 24px;--mdc-icon-size:24px;width:24px;height:24px;color:var(--ui203-accent,var(--primary-color))!important}
 :host(.ui203) .ui207-device[data-phase=offline]>ha-icon,:host(.ui203) .ui207-device[data-phase=waiting]>ha-icon{color:var(--ui203-muted,var(--secondary-text-color))!important}
 :host(.ui203) .ui207-device[data-phase=unavailable]>ha-icon{color:var(--error-color)!important}
 :host(.ui203) .ui207-device-copy{display:flex;align-items:baseline;flex-wrap:wrap;gap:2px 12px;min-width:0;flex:1}
 :host(.ui203) .ui207-device-name{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ui203-ink,var(--primary-text-color))!important;font-size:1rem;font-weight:650;line-height:1.4}
 :host(.ui203) .ui207-device-state{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ui203-muted,var(--secondary-text-color))!important;font-size:.85rem;line-height:1.4}
 :host(.ui203) .ui207-device:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px;border-radius:7px}
 :host(.ui203) .ui207-header #entrySelect{flex:0 1 180px;width:auto!important;max-width:180px!important}
 :host(.ui203) .ui207-header #cook4meTargetDevicesControl{flex:0 1 auto;max-width:100%}
 @media(max-width:760px){
  :host(.ui203) .wrap>.top.v100-top.ui207-header{padding:6px 10px!important;gap:8px!important}
  :host(.ui203) .ui207-device-copy{display:block}
  :host(.ui203) .ui207-device-name{font-size:.9rem}
  :host(.ui203) .ui207-device-state{font-size:.76rem}
 }
`;
export const CompactDeviceHeaderMixin=Base=>class extends Base{
 _v130DeviceHtml(entry){
  const value=compactDeviceHeader(entry,this._v81View()),e=value=>this._escape(String(value));
  const description=[value.name,value.label,this._v81Text('info')].filter(Boolean).join(' · ');
  // No photo/model markup is created, not merely hidden behind CSS.
  return `<div class="v130-device-summary ui207-device" data-phase="${e(value.phase)}" role="button" tabindex="0" aria-haspopup="dialog" aria-label="${e(description)}" title="${e(description)}"><ha-icon icon="${e(value.icon)}" aria-hidden="true"></ha-icon><div class="ui207-device-copy"><strong class="ui207-device-name">${e(value.name)}</strong><span class="ui207-device-state" role="status">${e(value.label)}</span></div></div>`;
 }
 _v207Header(){
  const root=this.shadowRoot;if(!root)return;
  root.querySelector('.top.v100-top')?.classList.add('ui207-header');
  if(!root.querySelector('#compactHeaderV207')){
   const style=document.createElement('style');style.id='compactHeaderV207';style.textContent=COMPACT_HEADER_CSS;root.append(style);
  }
  const node=root.querySelector('#status .ui207-device');if(!node||node._v207Bound)return;
  node._v207Bound=true;const context=this._prefKey(),entryId=this._entryId;
  const open=()=>{if(context===this._prefKey()&&entryId===this._entryId&&node.isConnected)this._v81OpenInfo();};
  node.onclick=open;
  node.onkeydown=event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();open();}};
 }
 _updateHeader(){
  const focused=this.shadowRoot?.activeElement?.classList.contains('ui207-device'),scope=this._prefKey();
  const result=super._updateHeader();this._v207Header();
  if(focused&&scope===this._prefKey())this.shadowRoot?.querySelector('#status .ui207-device')?.focus({preventScroll:true});
  return result;
 }
 _renderShell(){const result=super._renderShell();this._v207Header();return result;}
 _renderTab(){const result=super._renderTab();this._v207Header();return result;}
};
