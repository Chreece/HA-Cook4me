// Weekly stage counters are work evidence, not a prediction of the entire plan.
export const WEEK_PROGRESS_TEXT = {
 en:{title:'Generating weekly menu',queued:'Waiting for the previous weekly change',elapsed:'Elapsed',stage:'Stage',estimate:'This stage: approximately',unknown:'Remaining time is not known yet',quiet:'No new completed work reported for',results:'Preparing the result'},
 de:{title:'Wochenplan wird erstellt',queued:'Warten auf die vorherige Wochenplanänderung',elapsed:'Verstrichen',stage:'Schritt',estimate:'Dieser Schritt: ungefähr',unknown:'Restzeit ist noch nicht bekannt',quiet:'Kein neuer Arbeitsfortschritt gemeldet seit',results:'Ergebnis wird vorbereitet'},
 el:{title:'Δημιουργία εβδομαδιαίου μενού',queued:'Αναμονή για την προηγούμενη αλλαγή πλάνου',elapsed:'Χρόνος που πέρασε',stage:'Στάδιο',estimate:'Για αυτό το στάδιο: περίπου',unknown:'Ο χρόνος που απομένει δεν είναι ακόμη γνωστός',quiet:'Δεν αναφέρθηκε νέα ολοκληρωμένη εργασία για',results:'Προετοιμασία αποτελέσματος'}
};
const number=value=>(typeof value==='number'||typeof value==='string'&&value.trim()!=='')&&Number.isFinite(Number(value))?Number(value):null;
export function progressClock(milliseconds){
 const seconds=Math.max(0,Math.floor(milliseconds/1000));
 return `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;
}
export function recordWeeklyProgress(previous,data,now){
 const state=previous||{started:now,phase:'starting',total:null,completed:null,advanced:now,samples:[]};
 const phase=data.done?'results':data.kind==='week_generate_queued'?'queued':String(data.phase||state.phase);
 let total=number(data.total),completed=number(data.completed);
 if(data.done||!total||total<0||completed===null||completed<0){total=null;completed=null;}
 const changed=phase!==state.phase||total!==state.total||completed!==null&&state.completed!==null&&completed<state.completed;
 const advanced=changed||completed!==null&&(state.completed===null||completed>state.completed);
 const samples=changed?[]:state.samples.slice();
 if(completed!==null&&(advanced||!samples.length))samples.push({at:now,completed});
 return {...state,phase,total,completed,updated:now,advanced:advanced?now:state.advanced,samples:samples.slice(-10)};
}
export function weeklyStageEstimate(state,now){
 if(!state||state.completed===null||state.total===null||state.completed<=0||state.completed>=state.total||now-state.advanced>=15000)return null;
 const end=state.samples.at(-1);
 const start=state.samples.find(sample=>sample.completed<end.completed&&end.at-sample.at>=1000);
 if(!start)return null;
 const rate=(end.completed-start.completed)/(end.at-start.at);
 return rate>0?(state.total-state.completed)/rate:null;
}
export const WeeklyProgressMixin=Base=>class extends Base{
 _v200Text(key){const lang=String(this._uiIngredientLanguage?.()||this._langCode?.()||'en').split(/[-_]/)[0];return (WEEK_PROGRESS_TEXT[lang]||WEEK_PROGRESS_TEXT.en)[key];}
 _v200Now(){return this._v143Now();}
 _v200Track(token,data={}){
  if(!token||token.ended||token.failed||token.cancelled)return;
  if(!token._v200Weekly){
   token._v200Scope=this._prefKey();
   token._v200Weekly={started:this._v200Now(),phase:'starting',total:null,completed:null,advanced:this._v200Now(),samples:[]};
  }
  if(token._v200Scope!==this._prefKey())return;
  token._v200Weekly=recordWeeklyProgress(token._v200Weekly,data,this._v200Now());
  token.title=this._v200Text('title');
  this._v200Jobs??=new Set();this._v200Jobs.add(token);
  if(!this._v200Timer)this._v200Timer=setInterval(()=>this._v200Tick(),1000);
  this._v200Paint(token);
 }
 _v200Tick(){
  for(const token of this._v200Jobs||[]){
   if(token.ended||token.failed||token.cancelled||!token.card?.isConnected||token._v200Scope!==this._prefKey())this._v200Jobs.delete(token);
   else this._v200Paint(token);
  }
  if(!this._v200Jobs?.size){clearInterval(this._v200Timer);this._v200Timer=null;}
 }
 _v200Paint(token){
  const state=token?._v200Weekly;
  if(!state||!token.card||token.ended||token.failed||token.cancelled)return;
  const now=this._v200Now(),eta=weeklyStageEstimate(state,now),quiet=Math.max(0,now-state.advanced);
  const node=this._v143EnsureEtaNode(token);if(node){
   node.hidden=false;
   node.querySelector('span').textContent=[`${this._v200Text('elapsed')}: ${progressClock(now-state.started)}`,
    quiet>=15000?`${this._v200Text('quiet')} ${progressClock(quiet)}`:eta===null?this._v200Text('unknown'):`${this._v200Text('estimate')} ${progressClock(eta)}`].join(' · ');
  }
  const title=token.card.querySelector('.rx-v59-op-title');if(title)title.textContent=this._v200Text('title');
  const detail=token.card.querySelector('.rx-v59-op-detail');
  if(detail)detail.textContent=state.phase==='queued'?this._v200Text('queued'):state.phase==='results'?this._v200Text('results'):this._v59PhaseLabel(state.phase);
  const count=token.card.querySelector('.rx-v59-op-count'),bar=token.card.querySelector('.rx-v59-op-bar');
  const measured=state.total!==null&&state.completed!==null;
  token.card.classList.toggle('indeterminate',!measured);
  if(count)count.textContent=measured?`${this._v200Text('stage')}: ${Math.floor(state.completed)} / ${state.total} · ${Math.min(100,Math.floor(state.completed/state.total*100))}%`:'';
  if(bar){bar.style.width=measured?`${Math.min(100,state.completed/state.total*100)}%`:'28%';bar.style.transform='';}
 }
 async _v93SendJobRequest(payload){
  if(payload.type==='cook4me/v20/week_generate'){
   const token=this._v63Jobs?.get(payload.__cook4meJobId);this._v200Track(token);
  }
  return super._v93SendJobRequest(payload);
 }
 _v59HandleProgress(event){
  const data=event?.data||event||{};
  const token=this._v63Jobs?.get(String(data.operationId||''));
  if(token&&(token._v200Weekly||String(data.kind||'').startsWith('week_generate')))this._v200Track(token,data);
  const value=super._v59HandleProgress(event);
  if(token?._v200Weekly)this._v200Paint(token);
  return value;
 }
 _v143PaintEta(token,...args){if(token?._v200Weekly)return this._v200Paint(token);return super._v143PaintEta(token,...args);}
 _v143RecordDuration(token){if(!token?._v200Weekly)return super._v143RecordDuration(token);}
 _processEnd(token){this._v200Jobs?.delete(token);this._v200Tick();return super._processEnd(token);}
 _v59FailProcess(token,...args){this._v200Jobs?.delete(token);this._v200Tick();return super._v59FailProcess(token,...args);}
 disconnectedCallback(){clearInterval(this._v200Timer);this._v200Timer=null;this._v200Jobs?.clear();super.disconnectedCallback();}
};
