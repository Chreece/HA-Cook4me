import "./cook4me-panel-v71.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v71");
const BUILD="2026.9.15.14";
const TEXT={
 en:{settings:"Device settings",announcements:"Announcements",personal:"These settings apply to your account and this Cook4Me on every platform.",enabled:"Enable announcements",recipe:"Recipe loaded on the device",steps:"Current recipe step",state:"Cooking state changes",connection:"Connection changes during cooking",players:"Media players",selectPlayers:"Select speakers",tts:"Text-to-speech entity",ai:"AI Task for translation",language:"Output language",voice:"Voice",none:"None",default:"Default",save:"Save",test:"Test announcement",close:"Close",noPlayers:"No available media players with audio playback.",noTts:"No available TTS entities.",noAi:"No available AI Task entities.",original:"Without AI, recipe titles and steps are spoken in their original language. The output language controls the TTS voice.",resume:"Speakers marked ↩ support announcements with music resuming afterwards. Other players may interrupt playback.",unavailable:"Unavailable",translating:"Translating announcement",speaking:"Speaking announcement",done:"Announcement sent",skipped:"Outdated announcement skipped",error:"Announcement failed",device:"Device",status:"State",firmware:"Firmware",noVoice:"Provider default voice"},
 el:{settings:"Ρυθμίσεις συσκευής",announcements:"Ανακοινώσεις",personal:"Οι ρυθμίσεις ισχύουν για τον λογαριασμό σας και αυτό το Cook4Me σε όλες τις πλατφόρμες.",enabled:"Ενεργοποίηση ανακοινώσεων",recipe:"Φόρτωση συνταγής στη συσκευή",steps:"Τρέχον βήμα συνταγής",state:"Αλλαγές κατάστασης μαγειρέματος",connection:"Αλλαγές σύνδεσης κατά το μαγείρεμα",players:"Συσκευές αναπαραγωγής",selectPlayers:"Επιλέξτε ηχεία",tts:"Οντότητα μετατροπής κειμένου σε ομιλία",ai:"AI Task για μετάφραση",language:"Γλώσσα εκφώνησης",voice:"Φωνή",none:"Καμία",default:"Προεπιλογή",save:"Αποθήκευση",test:"Δοκιμή ανακοίνωσης",close:"Κλείσιμο",noPlayers:"Δεν υπάρχουν διαθέσιμες συσκευές αναπαραγωγής ήχου.",noTts:"Δεν υπάρχουν διαθέσιμες οντότητες TTS.",noAi:"Δεν υπάρχουν διαθέσιμες οντότητες AI Task.",original:"Χωρίς AI, οι τίτλοι και τα βήματα εκφωνούνται στην αρχική γλώσσα. Η γλώσσα εκφώνησης καθορίζει τη φωνή TTS.",resume:"Τα ηχεία με ↩ υποστηρίζουν συνέχιση της μουσικής μετά την ανακοίνωση. Τα υπόλοιπα ενδέχεται να διακόψουν την αναπαραγωγή.",unavailable:"Μη διαθέσιμο",translating:"Μετάφραση ανακοίνωσης",speaking:"Εκφώνηση ανακοίνωσης",done:"Η ανακοίνωση στάλθηκε",skipped:"Παραλείφθηκε παλιά ανακοίνωση",error:"Η ανακοίνωση απέτυχε",device:"Συσκευή",status:"Κατάσταση",firmware:"Υλικολογισμικό",noVoice:"Προεπιλεγμένη φωνή παρόχου"},
 de:{settings:"Geräteeinstellungen",announcements:"Ansagen",personal:"Diese Einstellungen gelten für Ihr Konto und dieses Cook4Me auf allen Plattformen.",enabled:"Ansagen aktivieren",recipe:"Rezept auf dem Gerät geladen",steps:"Aktueller Rezeptschritt",state:"Änderungen des Garstatus",connection:"Verbindungsänderungen beim Kochen",players:"Mediaplayer",selectPlayers:"Lautsprecher auswählen",tts:"Text-to-Speech-Entität",ai:"AI Task für Übersetzungen",language:"Ausgabesprache",voice:"Stimme",none:"Keine",default:"Standard",save:"Speichern",test:"Ansage testen",close:"Schließen",noPlayers:"Keine verfügbaren Mediaplayer mit Audiowiedergabe.",noTts:"Keine verfügbaren TTS-Entitäten.",noAi:"Keine verfügbaren AI-Task-Entitäten.",original:"Ohne KI werden Titel und Schritte in der Originalsprache vorgelesen. Die Ausgabesprache bestimmt die TTS-Stimme.",resume:"Mit ↩ markierte Lautsprecher setzen Musik nach der Ansage fort. Andere Player können die Wiedergabe unterbrechen.",unavailable:"Nicht verfügbar",translating:"Ansage wird übersetzt",speaking:"Ansage wird gesprochen",done:"Ansage gesendet",skipped:"Veraltete Ansage übersprungen",error:"Ansage fehlgeschlagen",device:"Gerät",status:"Status",firmware:"Firmware",noVoice:"Standardstimme des Anbieters"}
};

class Cook4MeRecipeHubPanelV72 extends BasePanel{
 _v72Text(key){return TEXT[this._langCode?.()]?.[key]||TEXT.en[key]||key;}
 _updateHeader(){
  super._updateHeader();this._v72Styles();
  const status=this.shadowRoot?.querySelector('#status .status');
  if(status){
   status.tabIndex=0;status.setAttribute('role','button');status.setAttribute('aria-haspopup','dialog');status.setAttribute('aria-label',this._v72Text('settings'));status.title=this._v72Text('settings');
   status.onclick=event=>{if(!event.target.closest('button,select,a,input'))void this._v72OpenSettings();};
   status.onkeydown=event=>{if(event.target===status&&['Enter',' '].includes(event.key)){event.preventDefault();void this._v72OpenSettings();}};
  }
  const context=this._prefKey();
  if(this._v72Dialog&&this._v72Context!==context)this._v72CloseSettings();
  void this._v72Subscribe();
  // The HA device page's Visit button links directly to its settings here.
  const target=new URLSearchParams(globalThis.location?.search||'').get('device');
  if(target&&!this._v72DeepLink&&this._entries?.some(e=>e.entry_id===target)){
   this._v72DeepLink=true;this._entryId=target;this._renderEntrySelect();
   queueMicrotask(()=>{this._updateHeader();void this._v72OpenSettings();});
  }
 }
 async _v72Subscribe(){
  const connection=this._hass?.connection,context=this._prefKey();
  if(!this._entryId||!connection?.subscribeMessage)return;
  if(this._v72Subscription?.context===context&&this._v72Subscription.connection===connection)return;
  const old=this._v72Subscription;this._v72Subscription=null;old?.unsubscribe?.();
  const record={context,connection};this._v72Subscription=record;
  try{
   const unsubscribe=await connection.subscribeMessage(status=>{
    if(this._v72Subscription===record)this._v72Progress(status);
   },{type:'cook4me/v32/announcement_subscribe',entry_id:this._entryId});
   if(this._v72Subscription===record)record.unsubscribe=unsubscribe;else unsubscribe();
  }catch(_error){if(this._v72Subscription===record)this._v72Subscription=null;}
 }
 _v72Progress(status){
  const busy=['translating','speaking'].includes(status.state);
  // Use the existing bottom-right progress surface for all speech work.
  let job=this._v72AnnouncementJob;
  if(!job||job.ended){
   job=this._v72AnnouncementJob=this._processStart(this._v72Text('announcements'),this._v72Text(status.state));
  }
  this._processUpdate(job,this._v72Text(status.state));
  if(status.state==='error')this._v59FailProcess(job,`${this._v72Text('error')}: ${status.detail||''}`);
  if(!busy){this._processEnd(job);this._v72AnnouncementJob=null;}
 }
 async _v72OpenSettings(){
  this._v72CloseSettings();this._v72Context=this._prefKey();
  const context=this._v72Context,request={};this._v72Request=request;
  const job=this._processStart(this._v72Text('settings'),this._t('loading'));
  try{
   const result=await this._api('cook4me/v32/device_settings',{entry_id:this._entryId});
   if(this._v72Request!==request||context!==this._prefKey())return;
   this._v72Data=result;this._v72Draft=structuredClone(result.settings);this._v72RenderSettings();
  }catch(error){this._v59FailProcess(job,`${this._t('error')}: ${error.message||error}`);}finally{this._processEnd(job);}
 }
 _v72CloseSettings(){
  this._v72Request=null;this._v72Dialog?.remove();this._v72Dialog=null;
  this._v72Focus?.focus?.();this._v72Focus=null;
 }
 _v72RenderSettings(){
  const escape=value=>this._escape(String(value??'')),t=key=>escape(this._v72Text(key)),draft=this._v72Draft,choices=this._v72Data.choices;
  const options=(rows,value,empty)=>`<option value="">${t(empty)}</option>`+rows.map(r=>`<option value="${escape(r.id)}" ${value===r.id?'selected':''}>${escape(r.name||r.id)}</option>`).join('')+(value&&!rows.some(r=>r.id===value)?`<option value="${escape(value)}" selected disabled>${escape(value)} (${t('unavailable')})</option>`:'');
  const selectedTts=choices.tts.find(row=>row.id===draft.tts),languages=selectedTts?.languages||[];
  let languageName=code=>code;try{const names=new Intl.DisplayNames([this._langCode()],{type:'language'});languageName=code=>{try{return names.of(code.replaceAll('_','-'));}catch{return code;}};}catch{}
  if(!draft.language&&selectedTts){draft.language=languages.find(code=>code.replaceAll('_','-').split('-')[0]===this._langCode())||selectedTts.defaultLanguage||languages[0]||'';}
  const voices=selectedTts?.voices?.[draft.language]||[];
  const allPlayers=[...choices.players,...draft.players.filter(id=>!choices.players.some(p=>p.id===id)).map(id=>({id,name:`${id} (${this._v72Text('unavailable')})`,missing:true}))];
  const field=(label,html)=>`<div class="field"><label>${t(label)}</label>${html}</div>`;
  const entry=this._entry(),state=entry?.state||{};
  let overlay=this._v72Dialog;
  if(!overlay){
   overlay=document.createElement('div');overlay.className='rx-overlay';overlay.setAttribute('data-device-settings','');this._v72Dialog=overlay;this._v72Focus=this.shadowRoot.activeElement;
   this.shadowRoot.appendChild(overlay);
   overlay.addEventListener('click',event=>{if(event.target===overlay)this._v72CloseSettings();});
   overlay.addEventListener('keydown',event=>{
    if(event.key==='Escape'){event.stopPropagation();this._v72CloseSettings();}
    if(event.key==='Tab'){
     const items=[...overlay.querySelectorAll('button:not([disabled]),select:not([disabled]),input:not([disabled]),summary')].filter(el=>!el.closest('details:not([open])')||el.tagName==='SUMMARY');
     const index=items.indexOf(this.shadowRoot.activeElement);
     if(event.shiftKey&&index<=0){event.preventDefault();items.at(-1)?.focus();}else if(!event.shiftKey&&index===items.length-1){event.preventDefault();items[0]?.focus();}
    }
   });
  }
  overlay.innerHTML=`<section class="rx-dialog" role="dialog" aria-modal="true" aria-label="${t('settings')}">
   <header><div><h2>${escape(entry?.title||'Cook4Me')}</h2><div class="muted">${t('settings')}</div></div><button class="btn secondary" data-v72-close aria-label="${t('close')}">✕</button></header>
   <dl><dt>${t('status')}</dt><dd>${escape(entry?.connected?(state.phase||state.status||'online'):this._t('offline'))}</dd><dt>${t('firmware')}</dt><dd>UI ${escape(state.uiFirmware||'—')} · Wi-Fi ${escape(state.wifiFirmware||'—')}</dd></dl>
   <h3><ha-icon icon="mdi:bullhorn-outline"></ha-icon> ${t('announcements')}</h3><p class="muted">${t('personal')}</p>
   <form><div class="v72-switches">${['enabled','recipe','steps','state','connection'].map(key=>`<label><input type="checkbox" data-setting="${key}" ${draft[key]?'checked':''}>${t(key)}</label>`).join('')}</div>
   ${field('players',`<details class="v72-players"><summary>${t('selectPlayers')} (<span data-v72-count>${draft.players.length}</span>)</summary><div>${allPlayers.map(p=>`<label><input type="checkbox" data-player="${escape(p.id)}" ${draft.players.includes(p.id)?'checked':''}><span>${escape(p.name)} ${p.announce?'↩':''}<small>${escape(p.id)}</small></span></label>`).join('')||`<p>${t('noPlayers')}</p>`}</div></details>`)}
   <p class="muted">${t('resume')}</p><div class="v72-fields">
   ${field('tts',`<select data-setting="tts" aria-label="${t('tts')}">${options(choices.tts,draft.tts,'none')}</select>${!choices.tts.length?`<small>${t('noTts')}</small>`:''}`)}
   ${field('language',`<select data-setting="language" aria-label="${t('language')}">${options(languages.map(id=>({id,name:languageName(id)})),draft.language,'default')}</select>`)}
   ${voices.length||draft.voice?field('voice',`<select data-setting="voice" aria-label="${t('voice')}">${options(voices,draft.voice,'noVoice')}</select>`):''}
   ${field('ai',`<select data-setting="ai" aria-label="${t('ai')}">${options(choices.ai,draft.ai,'none')}</select>${!choices.ai.length?`<small>${t('noAi')}</small>`:''}`)}
   </div><p class="muted">${t('original')}</p><footer><button type="button" class="btn secondary" data-v72-test>${t('test')}</button><button type="submit" class="btn" data-v72-save>${t('save')}</button></footer></form></section>`;
  overlay.querySelector('[data-v72-close]').onclick=()=>this._v72CloseSettings();
  overlay.querySelectorAll('[data-setting]').forEach(el=>el.addEventListener('change',()=>{
   draft[el.dataset.setting]=el.type==='checkbox'?el.checked:el.value;
   if(el.dataset.setting==='tts'){draft.language='';draft.voice='';this._v72RenderSettings();overlay.querySelector('[data-setting=tts]')?.focus();}
   if(el.dataset.setting==='language'){draft.voice='';this._v72RenderSettings();overlay.querySelector('[data-setting=language]')?.focus();}
  }));
  overlay.querySelectorAll('[data-player]').forEach(el=>el.addEventListener('change',()=>{
   draft.players=[...overlay.querySelectorAll('[data-player]')].filter(p=>p.checked).map(p=>p.dataset.player);overlay.querySelector('[data-v72-count]').textContent=String(draft.players.length);
  }));
  overlay.querySelector('form').onsubmit=event=>{event.preventDefault();void this._v72SaveSettings(false);};
  overlay.querySelector('[data-v72-test]').onclick=()=>void this._v72SaveSettings(true);
  overlay.querySelector('[data-v72-close]').focus();
 }
 async _v72SaveSettings(test){
  if(this._v72Saving)return;this._v72Saving=true;
  const context=this._prefKey(),overlay=this._v72Dialog,settings=structuredClone(this._v72Draft),entry=this._entryId;
  overlay?.querySelectorAll('button').forEach(b=>b.disabled=true);
  const job=this._processStart(this._v72Text(test?'test':'settings'),this._t('loading'));
  try{
   const result=await this._api('cook4me/v32/device_settings',{entry_id:entry,settings});
   if(context!==this._prefKey()||overlay!==this._v72Dialog)return;
   this._v72Data=result;
   if(test){this._v72AnnouncementJob=job;await this._api('cook4me/v32/announcement_test',{entry_id:entry});}
  }catch(error){this._v59FailProcess(job,`${this._t('error')}: ${error.message||error}`);}finally{
   this._v72Saving=false;overlay?.querySelectorAll('button').forEach(b=>b.disabled=false);this._processEnd(job);
   if(this._v72AnnouncementJob===job)this._v72AnnouncementJob=null;
  }
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build',BUILD);this._v72Styles();return result;}
 disconnectedCallback(){
  this._v72CloseSettings();const subscription=this._v72Subscription;this._v72Subscription=null;subscription?.unsubscribe?.();super.disconnectedCallback();
 }
 _v72Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#cook4meV72Styles'))return;
  const style=document.createElement('style');style.id='cook4meV72Styles';style.textContent=`
   #status .status[role=button]{cursor:pointer;border-radius:14px}#status .status[role=button]:focus-visible{outline:2px solid var(--primary-color)}
   .rx-v63-progress{z-index:12050}
   [data-device-settings]{z-index:12000!important}[data-device-settings] .rx-dialog{box-sizing:border-box;width:min(680px,calc(100vw - 24px));max-height:92dvh;overflow:auto;padding:24px}
   [data-device-settings] header{display:flex;justify-content:space-between;align-items:center;gap:16px}[data-device-settings] h2{margin:0}[data-device-settings] h3{margin:24px 0 12px}
   [data-device-settings] p{line-height:1.5;margin:12px 0}[data-device-settings] dl{display:grid;grid-template-columns:auto 1fr;gap:12px;margin:24px 0}[data-device-settings] dd{margin:0}
   [data-device-settings] .field{margin:14px 0;min-width:0}[data-device-settings] select{width:100%;box-sizing:border-box;min-height:44px}
   [data-device-settings] .v72-switches>label,[data-device-settings] .v72-players label{display:flex;gap:12px;align-items:center;min-height:44px}
   [data-device-settings] input[type=checkbox]{flex:0 0 20px;width:20px;height:20px;accent-color:var(--primary-color)}
   [data-device-settings] .v72-fields{display:grid;grid-template-columns:1fr 1fr;gap:0 18px}[data-device-settings] .v72-players{border:1px solid var(--divider-color);border-radius:12px;padding:12px}
   [data-device-settings] .v72-players>div{max-height:230px;overflow:auto}[data-device-settings] small{display:block;overflow-wrap:anywhere;opacity:.7}[data-device-settings] summary{cursor:pointer;min-height:28px}
   [data-device-settings] footer{display:flex;justify-content:flex-end;gap:12px;margin-top:20px;flex-wrap:wrap}
   @media(max-width:520px){[data-device-settings] .v72-fields{grid-template-columns:1fr}[data-device-settings] .rx-dialog{padding:16px}}
  `;this.shadowRoot.appendChild(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v72',Cook4MeRecipeHubPanelV72);
