import "./cook4me-panel-v80.js";

const BasePanel=customElements.get('cook4me-recipe-hub-panel-v80');
const BUILD='2026.9.16.6';
const WORDS={
 en:{add:'Add product',addHelp:'Scan a barcode, date, nutrition label or product — or enter the details manually.',options:'Device options',info:'Device information',idle:'Ready to cook',warming:'Preheating',cooking:'Cooking',depressurization:'Releasing pressure',keep_warm:'Keeping warm',ready:'Ready',done:'Finished',add_ingredient:'Add ingredients',preparation:'Preparation',stopped:'Stopped',paused:'Paused',updating:'Updating',offline:'Device offline',unknown:'State unavailable',waiting:'Connecting to device updates',unavailable:'Device updates unavailable',remaining:'Time remaining',program:'Program',recipe:'Recipe',instruction:'Current step',connection:'Connection',online:'Connected'},
 de:{add:'Produkt hinzufügen',addHelp:'Barcode, Datum, Nährwerte oder Produkt scannen — oder die Angaben manuell eingeben.',options:'Geräteoptionen',info:'Geräteinformationen',idle:'Bereit zum Kochen',warming:'Vorheizen',cooking:'Kochen',depressurization:'Druck ablassen',keep_warm:'Warmhalten',ready:'Bereit',done:'Fertig',add_ingredient:'Zutaten hinzufügen',preparation:'Vorbereitung',stopped:'Gestoppt',paused:'Pausiert',updating:'Aktualisierung',offline:'Gerät offline',unknown:'Status nicht verfügbar',waiting:'Verbindung zu Geräteaktualisierungen',unavailable:'Geräteaktualisierungen nicht verfügbar',remaining:'Verbleibende Zeit',program:'Programm',recipe:'Rezept',instruction:'Aktueller Schritt',connection:'Verbindung',online:'Verbunden'},
 el:{add:'Προσθήκη προϊόντος',addHelp:'Σαρώστε barcode, ημερομηνία, διατροφική ετικέτα ή προϊόν — ή συμπληρώστε τα στοιχεία χειροκίνητα.',options:'Επιλογές συσκευής',info:'Πληροφορίες συσκευής',idle:'Έτοιμο για μαγείρεμα',warming:'Προθέρμανση',cooking:'Μαγείρεμα',depressurization:'Εκτόνωση πίεσης',keep_warm:'Διατήρηση θερμοκρασίας',ready:'Έτοιμο',done:'Ολοκληρώθηκε',add_ingredient:'Προσθήκη υλικών',preparation:'Προετοιμασία',stopped:'Διακόπηκε',paused:'Σε παύση',updating:'Ενημέρωση',offline:'Συσκευή εκτός σύνδεσης',unknown:'Μη διαθέσιμη κατάσταση',waiting:'Σύνδεση με ενημερώσεις συσκευής',unavailable:'Μη διαθέσιμες ενημερώσεις συσκευής',remaining:'Χρόνος που απομένει',program:'Πρόγραμμα',recipe:'Συνταγή',instruction:'Τρέχον βήμα',connection:'Σύνδεση',online:'Συνδεδεμένη'}
};
const PHASES=new Set(['idle','warming','cooking','depressurization','keep_warm','ready','done','add_ingredient','preparation','stopped','paused']);

class Cook4MeRecipeHubPanelV81 extends BasePanel{
 _v81Text(key){return WORDS[this._langCode?.()]?.[key]||WORDS.en[key]||key;}
 _v78Text(key){if(key==='scan')return this._v81Text('add');if(key==='scanHelp')return this._v81Text('addHelp');return super._v78Text(key);}
 _v72Text(key){return super._v72Text(key==='settings'?'announcements':key);}
 _renderProfile(c){
  super._renderProfile(c);this._v81Styles();
  c.querySelector('.v78-heading [data-v78-open]')?.remove();
  c.querySelector('[data-v78-open=manual]')?.remove();
  const button=c.querySelector('[data-v78-device]');
  if(button){
   button.closest('.card').querySelector('h2').textContent=this._v81Text('options');
   button.textContent=this._v72Text('announcements');
   button.onclick=()=>void this._v81OpenAnnouncements();
  }
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build',BUILD);this._v81Styles();return result;}
 _updateHeader(){
  const current=this._v81Subscription,entry=this._entry();
  if(entry&&current?.context===this._prefKey()&&current.snapshot)Object.assign(entry,current.snapshot);
  super._updateHeader();this._v81Styles();
  if(this._v81InfoDialog&&this._v81InfoContext!==this._prefKey())this._v81CloseInfo();
  void this._v81Subscribe();
  const status=this.shadowRoot?.querySelector('#status .status');
  if(status){
   const e=v=>this._escape(String(v??'')),view=this._v81View(),entry=this._entry();
   status.setAttribute('aria-label',`${entry?.title||'Cook4Me'}: ${view.label}. ${this._v81Text('info')}`);status.title=this._v81Text('info');
   // Preserve the animated node across unrelated HA updates to avoid restarting it.
   const old=this._v81HeaderArt,art=old?.dataset.phase===view.phase?old:null;
   status.innerHTML=`${this._v81Cooker(view.phase)}<div class="status-main"><div class="status-title">${e(entry?.title||'Cook4Me')}</div><div class="v81-state-label">${e(view.label)}</div>${view.live&&view.state.recipeTitle?`<div class="muted">${e(view.state.recipeTitle)}</div>`:''}</div><ha-icon class="v81-info-icon" icon="mdi:information-outline"></ha-icon>`;
   if(art)status.querySelector('.v81-cooker').replaceWith(art);
   this._v81HeaderArt=status.querySelector('.v81-cooker');
  }
  this._v81RenderInfo();
 }
 _v81View(){
  const entry=this._entry(),state=entry?.state||{},record=this._v81Subscription;
  const context=record?.context===this._prefKey(),live=context?record.live===true:true;
  let phase=String(state.phase||state.status||'').toLowerCase().replaceAll(' ','_');
  phase=({'preheating':'warming','keepwarm':'keep_warm','completed':'done','depressurizing':'depressurization'})[phase]||phase;
  if(context&&!live)phase=record.failed?'unavailable':'waiting';
  else if(!entry?.connected)phase='offline';
  else if(state.updating===true)phase='updating';
  else if(!PHASES.has(phase))phase='unknown';
  const online=live&&entry?.connected&&entry?.accessible!==false;
  return {phase,label:this._v81Text(phase),state,live:online};
 }
 async _v81Subscribe(){
  const connection=this._hass?.connection,context=this._prefKey(),entryId=this._entryId;
  const old=this._v81Subscription;
  if(old?.context===context&&old.connection===connection)return;
  this._v81StopSubscription();
  if(!entryId||!connection?.subscribeMessage)return;
  const record={context,connection,live:false};this._v81Subscription=record;
  record.disconnected=()=>{if(this._v81Subscription===record){record.live=false;record.failed=true;this._updateHeader();}};
  connection.addEventListener?.('disconnected',record.disconnected);
  try{
   const unsubscribe=await connection.subscribeMessage(snapshot=>{
    if(this._v81Subscription!==record||context!==this._prefKey()||snapshot?.entry_id!==entryId)return;
    const entry=this._entries?.find(row=>row.entry_id===entryId);if(!entry)return;
    record.live=true;record.failed=false;
    record.snapshot={state:snapshot.state||{},connected:snapshot.connected===true,accessible:snapshot.accessible!==false,canAcceptRecipe:snapshot.canAcceptRecipe===true,loadedRecipe:snapshot.loadedRecipe||null};
    Object.assign(entry,record.snapshot);
    if(snapshot.accessible===false){record.live=false;record.failed=true;}
    this._updateHeader();
   },{type:'cook4me/v32/device_state_subscribe',entry_id:entryId});
   if(this._v81Subscription===record)record.unsubscribe=unsubscribe;else unsubscribe();
  }catch(_error){if(this._v81Subscription===record){record.failed=true;record.live=false;this._updateHeader();}}
 }
 _v81StopSubscription(){const old=this._v81Subscription;this._v81Subscription=null;old?.unsubscribe?.();old?.connection.removeEventListener?.('disconnected',old.disconnected);}
 // Existing header keyboard controls and HA device deep links now open information.
 _v72OpenSettings(){this._v81OpenInfo();}
 async _v81OpenAnnouncements(){this._v81CloseInfo();return super._v72OpenSettings();}
 _v72RenderSettings(){
  super._v72RenderSettings();const dialog=this._v72Dialog;if(!dialog)return;
  dialog.setAttribute('data-announcements','');dialog.querySelector('dl')?.remove();dialog.querySelector('h3')?.remove();
  dialog.querySelector('h2').textContent=this._v72Text('announcements');
  dialog.querySelector('header .muted').textContent=this._entry()?.title||'Cook4Me';
 }
 _v81OpenInfo(){
  this._v72CloseSettings();this._v81CloseInfo();this._v81Styles();
  const dialog=document.createElement('dialog');dialog.className='v81-device-info';dialog.setAttribute('data-device-info','');dialog.setAttribute('aria-label',this._v81Text('info'));
  this._v81InfoFocus=this.shadowRoot.activeElement;this._v81InfoContext=this._prefKey();this._v81InfoDialog=dialog;
  const e=v=>this._escape(String(v??''));
  dialog.innerHTML=`<header><div><p class="muted">${e(this._v81Text('info'))}</p><h2>${e(this._entry()?.title||'Cook4Me')}</h2></div><button class="btn secondary" data-v81-close aria-label="${e(this._v72Text('close'))}">✕</button></header><div class="v81-device-hero"><div data-v81-art></div><strong data-v81-phase role="status" aria-live="polite"></strong></div><dl data-v81-details></dl>`;
  this.shadowRoot.append(dialog);this._v81RenderInfo();
  dialog.querySelector('[data-v81-close]').onclick=()=>this._v81CloseInfo();
  dialog.addEventListener('cancel',event=>{event.preventDefault();this._v81CloseInfo();});
  dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)this._v81CloseInfo();});
  if(dialog.showModal)dialog.showModal();else dialog.setAttribute('open','');
  dialog.querySelector('button').focus();
 }
 _v81CloseInfo(){this._v81InfoDialog?.remove();this._v81InfoDialog=null;this._v81InfoFocus?.focus?.();this._v81InfoFocus=null;}
 _v81RenderInfo(){
  const dialog=this._v81InfoDialog;if(!dialog)return;
  const view=this._v81View(),s=view.state,e=v=>this._escape(String(v??''));
  const art=dialog.querySelector('[data-v81-art]');if(art.firstElementChild?.dataset.phase!==view.phase)art.innerHTML=this._v81Cooker(view.phase);
  const label=dialog.querySelector('[data-v81-phase]');if(label.textContent!==view.label)label.textContent=view.label;
  const rows=[[this._v81Text('connection'),view.live?this._v81Text('online'):view.label]];
  if(view.live){
   for(const [key,value] of [['recipe',s.recipeTitle],['instruction',s.currentInstruction],['program',s.programName]])if(value)rows.push([this._v81Text(key),value]);
   if(typeof s.remainingTime==='number'&&Number.isFinite(s.remainingTime)&&s.remainingTime>=0){const seconds=Math.floor(s.remainingTime);rows.push([this._v81Text('remaining'),`${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`]);}
  }
  rows.push(['UI '+this._v72Text('firmware'),s.uiFirmware||'—'],['Wi-Fi '+this._v72Text('firmware'),s.wifiFirmware||'—']);
  const html=rows.map(([key,value])=>`<dt>${e(key)}</dt><dd>${e(value)}</dd>`).join('');
  const details=dialog.querySelector('[data-v81-details]');if(details.innerHTML!==html)details.innerHTML=html;
 }
 _v81Cooker(phase){
  const safe=PHASES.has(phase)||['offline','unknown','waiting','unavailable','updating'].includes(phase)?phase:'unknown';
  return `<svg class="v81-cooker" data-phase="${safe}" viewBox="0 0 200 180" aria-hidden="true"><ellipse cx="100" cy="164" rx="68" ry="7" fill="currentColor" opacity=".07"/><g class="v81-steam" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"><path d="M78 39c-10-10 10-14 0-25"/><path d="M100 33c-10-10 10-14 0-25"/><path d="M122 39c-10-10 10-14 0-25"/></g><rect x="23" y="84" width="22" height="24" rx="8" fill="#283d38"/><rect x="155" y="84" width="22" height="24" rx="8" fill="#283d38"/><path d="M40 78h120v41c0 27-21 43-60 43s-60-16-60-43z" fill="#dce7e1" stroke="#425d52" stroke-width="3"/><path d="M47 90v28c0 22 19 35 48 37" fill="none" stroke="#f8faf9" stroke-width="6" stroke-linecap="round"/><g class="v81-lid"><path d="M36 77c0-21 25-38 64-38s64 17 64 38z" fill="#334c42"/><path d="M69 49v-8c0-8 62-8 62 0v8" fill="none" stroke="#253c33" stroke-width="10" stroke-linecap="round"/><path d="M39 77h122" stroke="#a7b8b0" stroke-width="5" stroke-linecap="round"/></g><rect class="v81-screen" x="75" y="95" width="50" height="34" rx="8" fill="#45695b"/><g class="v81-screen-bars" stroke="#d5f5df" stroke-width="3" stroke-linecap="round"><path d="M86 107h28M86 117h17"/></g><path class="v81-tick" d="m87 113 9 8 18-19" fill="none" stroke="#dcffe7" stroke-width="4" stroke-linecap="round"/><circle cx="100" cy="140" r="4" fill="#61796e"/><path d="M62 158v5m76-5v5" stroke="#334c42" stroke-width="9" stroke-linecap="round"/><circle class="v81-update" cx="100" cy="112" r="11" fill="none" stroke="#def1ff" stroke-width="3" stroke-dasharray="20 50"/></svg>`;
 }
 disconnectedCallback(){this._v81CloseInfo();this._v81StopSubscription();super.disconnectedCallback();}
 _v81Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#cook4meV81Styles'))return;
  const style=document.createElement('style');style.id='cook4meV81Styles';style.textContent=`
   #status .status{gap:16px;padding:10px 16px}#status .status-main{min-width:0;flex:1}#status .status-main>div{overflow-wrap:anywhere}.v81-state-label{font-weight:600;margin:4px 0}.v81-info-icon{opacity:.55;flex-shrink:0}
   .v81-cooker{display:block;width:100px;flex:0 0 100px;height:auto;color:#739a88}.v81-steam{opacity:0}.v81-tick,.v81-update{display:none}
   .v81-cooker[data-phase=warming] .v81-screen{fill:#c48638;animation:v81-heat 2s ease-in-out infinite}.v81-cooker[data-phase=cooking] .v81-screen{fill:#bd6d36}
   .v81-cooker:is([data-phase=warming],[data-phase=cooking],[data-phase=depressurization],[data-phase=keep_warm]) .v81-steam{opacity:1}
   .v81-steam path{animation:v81-steam 2.6s ease-in-out infinite;transform-box:fill-box;transform-origin:center}.v81-steam path:nth-child(2){animation-delay:-.9s}.v81-steam path:nth-child(3){animation-delay:-1.7s}
   .v81-cooker[data-phase=depressurization] .v81-steam path{animation-duration:1.1s;stroke-width:5}.v81-cooker[data-phase=keep_warm] .v81-steam{opacity:.45}.v81-cooker[data-phase=keep_warm] .v81-steam path{animation-duration:4s}
   .v81-cooker:is([data-phase=ready],[data-phase=done]) .v81-tick{display:block}.v81-cooker:is([data-phase=ready],[data-phase=done],[data-phase=updating]) .v81-screen-bars{display:none}
   .v81-cooker:is([data-phase=preparation],[data-phase=add_ingredient]) .v81-lid{transform:translateY(-9px) rotate(-7deg);transform-origin:40px 77px}
   .v81-cooker[data-phase=updating] .v81-update{display:block;animation:v81-turn 1.5s linear infinite;transform-origin:100px 112px}
   .v81-cooker:is([data-phase=offline],[data-phase=unknown],[data-phase=unavailable],[data-phase=waiting]){filter:grayscale(1);opacity:.55}.v81-cooker:not(:is([data-phase=warming],[data-phase=cooking],[data-phase=depressurization],[data-phase=keep_warm])) .v81-steam path{animation:none}
   .v81-device-info{box-sizing:border-box;width:min(560px,calc(100vw - 28px));max-height:90dvh;overflow:auto;padding:28px;border:1px solid var(--divider-color);border-radius:24px;background:var(--card-background-color);color:var(--primary-text-color);box-shadow:0 20px 80px #0003}.v81-device-info::backdrop{background:#14291f80;backdrop-filter:blur(4px)}.v81-device-info header{display:flex;align-items:center;justify-content:space-between;gap:16px}.v81-device-info h2{margin:4px 0;font-size:23px;overflow-wrap:anywhere}.v81-device-info header p{margin:0;font-size:13px}.v81-device-info header button{flex-shrink:0}.v81-device-hero{display:grid;justify-items:center;padding:20px 0 26px;gap:4px}.v81-device-hero .v81-cooker{width:200px}.v81-device-hero strong{font-size:20px;text-align:center}.v81-device-info dl{display:grid;grid-template-columns:minmax(90px,.8fr) minmax(0,1.4fr);gap:16px 22px;padding-top:22px;border-top:1px solid var(--divider-color);font-size:14px;line-height:1.5}.v81-device-info dt{color:var(--secondary-text-color)}.v81-device-info dd{margin:0;overflow-wrap:anywhere}
   @keyframes v81-steam{0%{transform:translateY(5px);opacity:.1}45%{opacity:.8}100%{transform:translateY(-7px);opacity:0}}@keyframes v81-heat{50%{opacity:.5}}@keyframes v81-turn{to{transform:rotate(360deg)}}
   @media(max-width:520px){#status .status{gap:10px;padding:8px}.v81-cooker{width:80px;flex-basis:80px}.v81-device-info{padding:20px}.v81-device-info dl{gap:14px}}
   @media(prefers-reduced-motion:reduce){.v81-cooker *{animation:none!important}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v81',Cook4MeRecipeHubPanelV81);
