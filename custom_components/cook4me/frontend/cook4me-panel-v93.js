import "./cook4me-panel-v92.js";

const BasePanel=customElements.get('cook4me-recipe-hub-panel-v92');
const MEALS=['breakfast','starter','salad','soup','main','side','dessert','snack'];
const TARGETS=['calorieTarget','proteinTarget','carbsTarget','fatTarget','saturatedFatTarget','sugarsTarget','fiberTarget','saltTarget','sodiumTarget'];
const WORDS={
 en:{filters:'Filters',active:'Active filters',cancel:'Cancel',cancelled:'Cancelled',cancelFailed:'Stopped locally; the server could not confirm cancellation.',otherMeal:'For another meal time',breakfast:'Breakfast',morningSnack:'Morning snack',lunch:'Lunch',afternoonSnack:'Afternoon snack',dinner:'Dinner',lateSnack:'Late snack'},
 de:{filters:'Filter',active:'Aktive Filter',cancel:'Abbrechen',cancelled:'Abgebrochen',cancelFailed:'Lokal gestoppt; der Server konnte den Abbruch nicht bestätigen.',otherMeal:'Für eine andere Mahlzeit',breakfast:'Frühstück',morningSnack:'Vormittagssnack',lunch:'Mittagessen',afternoonSnack:'Nachmittagssnack',dinner:'Abendessen',lateSnack:'Später Snack'},
 el:{filters:'Φίλτρα',active:'Ενεργά φίλτρα',cancel:'Ακύρωση',cancelled:'Ακυρώθηκε',cancelFailed:'Σταμάτησε τοπικά· ο διακομιστής δεν επιβεβαίωσε την ακύρωση.',otherMeal:'Για άλλη ώρα γεύματος',breakfast:'Πρωινό',morningSnack:'Δεκατιανό',lunch:'Μεσημεριανό',afternoonSnack:'Απογευματινό',dinner:'Βραδινό',lateSnack:'Νυχτερινό σνακ'},
};

class Cook4MeRecipeHubPanelV93 extends BasePanel{
 _v93Text(key){return WORDS[this._uiIngredientLanguage()]?.[key]||WORDS.en[key]||this._t(key);}
 _renderTab(){if(this._tab!=='today'){clearInterval(this._v93ClockTimer);this._v93ClockTimer=null;}const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.16.17');this._v93Styles();return result;}

 // Attach ownership before any asynchronous API layer runs. Transport hooks in
 // the existing terminal layers preserve their mapping, diet and cache logic.
 async _api(type,data={}){
  const inline=type.startsWith('cook4me/v34/')&&!type.endsWith('/recipe_cost_refresh');
  // Saves can run alongside background work and must not inherit its cancellation.
  const created=!inline&&(type==='cook4me/v33/product_add'||!this._process);
  const job=inline?null:created?this._processStart(this._t('backgroundWork'),this._loadLabel(type)||this._t('loading')):this._process;
  try{
   if(job?.cancelled)throw this._v93CancelledError();
   const result=await super._api(type,job?{...data,__cook4meJobId:job.id}:data);
   if(job?.cancelled)throw this._v93CancelledError();
   return result;
  }finally{if(created)this._processEnd(job);}
 }
 _v93CancelledError(){const error=new Error(this._v93Text('cancelled'));error.code='job_cancelled';return error;}
 async _v93SendJobRequest(payload){
  const {__cook4meJobId:jobId,...request}=payload;
  const job=this._v63Jobs?.get(jobId),connection=job?.connection||this._hass.connection;
  if(!job)return connection.sendMessagePromise(request);
  if(job.cancelled)throw this._v93CancelledError();
  const response=connection.sendMessagePromise({type:'cook4me/v36/job_run',job_id:job.id,request}).catch(error=>{
   // Short synchronous commands retain their original validated HA endpoint.
   if(error.code==='job_unsupported'&&!job.cancelled)return connection.sendMessagePromise(request);
   throw error;
  });
  let onCancel;
  const cancelled=new Promise((_,reject)=>{onCancel=()=>reject(this._v93CancelledError());job.listeners.add(onCancel);});
  try{const result=await Promise.race([response,cancelled]);if(job.cancelled)throw this._v93CancelledError();return result;}
  finally{job.listeners.delete(onCancel);}
 }
 _processStart(...args){
  const job=super._processStart(...args);job.connection=this._hass?.connection;job.listeners=new Set();
  const button=document.createElement('button');button.type='button';button.className='btn secondary v93-cancel';
  button.textContent=this._v93Text('cancel');button.setAttribute('aria-label',`${this._v93Text('cancel')}: ${job.title}`);
  button.onclick=()=>void this._v93CancelJob(job);job.card.querySelector('.rx-v59-op-head').append(button);this._v93Styles();return job;
 }
 async _v93CancelJob(job){
  if(!job||job.ended||job.cancelled)return;
  job.cancelled=true;job.failed=false;
  for(const cancel of job.listeners)cancel();
  this._processEnd(job);
  try{await job.connection.sendMessagePromise({type:'cook4me/v36/job_cancel',job_id:job.id});}
  catch{if(job.card?.isConnected){clearTimeout(job.removeTimer);job.card.querySelector('.rx-v59-op-detail').textContent=this._v93Text('cancelFailed');job.removeTimer=setTimeout(()=>job.card.remove(),6000);}}
 }
 _processUpdate(job,...args){if(!job?.cancelled)return super._processUpdate(job,...args);}
 _v59FailProcess(job,error){if(!job?.cancelled)return super._v59FailProcess(job,error);}
 _v59HandleProgress(event){const data=event?.data||event||{},job=this._v63Jobs?.get(String(data.operationId||''));if(job?.cancelled)return;return super._v59HandleProgress(event);}
 _message(message,bad=false){if(bad&&String(message).includes(this._v93Text('cancelled')))return;return super._message(message,bad);}
 _processEnd(job){
  if(!job||job.ended)return;
  job.card?.querySelector('.v93-cancel')?.remove();
  if(!job.cancelled)return super._processEnd(job);
  job.ended=true;job.failed=false;job.card?.classList.remove('bad','indeterminate');
  job.card?.querySelector('ha-icon')?.setAttribute('icon','mdi:cancel');
  if(job.card){job.card.querySelector('.rx-v59-op-detail').textContent=this._v93Text('cancelled');job.card.querySelector('.rx-v59-op-count').textContent='';job.card.querySelector('.rx-v59-op-track').hidden=true;}
  this._v63Jobs?.delete(job.id);
  if(this._process===job)this._process=[...(this._v63Jobs?.values()||[])].at(-1)||null;
  job.removeTimer=setTimeout(()=>job.card?.remove(),1800);
 }

 _filterActive(key){
  const f=this._filters(),selected=(values,all)=>Array.isArray(values)&&values.length>0&&(values.length!==all.length||all.some(value=>!values.includes(value)));
  if(key==='dietProfile')return Boolean(f.dietProfile&&f.dietProfile!=='manual');
  if(key==='diet')return !['','profile','omnivore'].includes(f.diet||'')||Boolean(f.excludedIngredients?.length||f.excludedTerms?.length);
  if(key==='meals')return selected(f.mealTypes,MEALS);
  if(key==='languages')return selected(f.languages,this._languageRows().map(row=>row.code));
  if(key==='home')return Boolean(f.onlyHome||f.maxMissing!==''&&f.maxMissing!=null||f.preferExpiring===false||(f.avoidRecentDays!=null&&Number(f.avoidRecentDays)!==7));
  if(key==='nutrition')return TARGETS.some(name=>f[name]!==''&&f[name]!=null)||Boolean(f.nutritionGoal&&f.nutritionGoal!=='balanced');
  return super._filterActive(key);
 }
 _v93FilterSummary(key){
  const f=this._filters();
  if(key==='dietProfile')return this._v83SourceLabel();
  if(key==='ingredients')return String(f.ingredients?.length||0);
  if(key==='languages')return String(f.languages?.length||0);
  if(key==='meals')return String(f.mealTypes?.length||0);
  if(key==='cost')return `${f.maxCost} ${f.currency||'EUR'}`;
  if(key==='diet')return this._t(f.diet||'omnivore');
  if(key==='nutrition')return String(TARGETS.filter(name=>f[name]!==''&&f[name]!=null).length||this._t(f.nutritionGoal||'balanced'));
  if(key==='home')return f.maxMissing!==''&&f.maxMissing!=null?`≤ ${f.maxMissing}`:'';
  return '';
 }
 _v83MergeToolbar(c){
  const toolbar=c.querySelector('#todaySuggest,#generateWeek,#searchBtn')?.closest('.toolbar'),bar=c.querySelector('.rx-shared-filters');if(!toolbar||!bar)return;
  toolbar.classList.add('v83-controls','v93-controls');toolbar.closest('section.card')?.classList.add('v83-control-card');
  let left=toolbar.querySelector('.v93-menu-controls');
  if(!left){left=document.createElement('div');left.className='v93-menu-controls';toolbar.prepend(left);}
  // Later parent layers may append controls after the first toolbar pass.
  for(const child of [...toolbar.children])if(child!==left&&child!==bar)left.append(child);
  toolbar.append(bar);bar.classList.add('v93-filters');bar.setAttribute('aria-label',this._t('sharedFilters'));
  const buttons=[...bar.querySelectorAll('[data-filter]')];bar.replaceChildren();
  const toggle=document.createElement('button');toggle.type='button';toggle.className='btn secondary v93-filter-toggle';toggle.innerHTML='<ha-icon icon="mdi:filter-variant" aria-hidden="true"></ha-icon><span></span>';toggle.querySelector('span').textContent=this._v93Text('filters');
  const drawer=document.createElement('div');drawer.className='v93-filter-drawer';drawer.id='v93FilterDrawer';drawer.hidden=!this._v93FiltersOpen;
  const active=document.createElement('div');active.className='v93-active-filters';active.setAttribute('role','group');active.setAttribute('aria-label',this._v93Text('active'));
  toggle.setAttribute('aria-controls',drawer.id);toggle.setAttribute('aria-expanded',String(!drawer.hidden));
  toggle.onclick=()=>{drawer.hidden=!drawer.hidden;this._v93FiltersOpen=!drawer.hidden;toggle.setAttribute('aria-expanded',String(!drawer.hidden));};
  drawer.onkeydown=event=>{if(event.key==='Escape'){drawer.hidden=true;this._v93FiltersOpen=false;toggle.setAttribute('aria-expanded','false');toggle.focus();event.stopPropagation();}};
  for(const button of buttons){
   const key=button.dataset.filter,isActive=this._filterActive(key);
   button.querySelectorAll('.v93-filter-value,.v93-filter-name').forEach(node=>node.remove());
   const base=button.dataset.v93Label||button.getAttribute('aria-label')||button.title;button.dataset.v93Label=base;
   const label=document.createElement('span');label.className=isActive?'v93-filter-value':'v93-filter-name';label.textContent=isActive?this._v93FilterSummary(key):base;
   if(label.textContent)button.append(label);
   const description=isActive&&label.textContent&&!base.includes(label.textContent)?`${base}: ${label.textContent}`:base;
   button.title=description;button.setAttribute('aria-label',description);button.setAttribute('aria-pressed',String(isActive));
   (isActive?active:drawer).append(button);
  }
  bar.append(toggle,active,drawer);this._v93Styles();
 }

 _renderToday(c){super._renderToday(c);this._v93UpdateTodayClock();if(!this._v93ClockTimer)this._v93ClockTimer=setInterval(()=>this._v93UpdateTodayClock(),15000);}
 disconnectedCallback(){clearInterval(this._v93ClockTimer);this._v93ClockTimer=null;super.disconnectedCallback();}
 _v93Now(){return new Date();}
 _v93Daypart(hour){return hour>=5&&hour<10?'breakfast':hour<12&&hour>=10?'morningSnack':hour>=12&&hour<15?'lunch':hour>=15&&hour<18?'afternoonSnack':hour>=18&&hour<22?'dinner':'lateSnack';}
 _v93MealRelevant(recipe,period){
  const meal=recipe?.todayMealType||recipe?.mealType;
  if(!meal)return true;
  const periods={breakfast:['breakfast'],lunch:['lunch'],dinner:['dinner'],morningSnack:['morningSnack'],afternoonSnack:['afternoonSnack'],lateSnack:['lateSnack'],snack:['morningSnack','afternoonSnack','lateSnack'],dessert:['lunch','afternoonSnack','dinner'],main:['lunch','dinner'],starter:['lunch','dinner'],salad:['lunch','dinner'],soup:['lunch','dinner'],side:['lunch','dinner']};
  return !periods[meal]||periods[meal].includes(period);
 }
 _v93UpdateTodayClock(){
  const c=this.shadowRoot?.querySelector('#content'),heading=c?.querySelector('#todaySuggest')?.closest('.toolbar')?.querySelector('h2');if(!heading)return;
  const now=this._v93Now(),locale=this._hass?.locale?.language||this._hass?.language||this._uiIngredientLanguage()||'en';
  let zone=this._hass?.config?.time_zone;try{new Intl.DateTimeFormat(locale,{timeZone:zone}).format(now);}catch{zone=undefined;}
  const parts=new Intl.DateTimeFormat('en-GB',{hour:'2-digit',hourCycle:'h23',timeZone:zone}).formatToParts(now),hour=Number(parts.find(p=>p.type==='hour').value),period=this._v93Daypart(hour);
  let date=heading.querySelector('[data-v93-date]');
  if(!date){date=document.createElement('time');date.dataset.v93Date='';heading.append(date);}
  date.textContent=new Intl.DateTimeFormat(locale,{day:'numeric',month:'long',year:'numeric',timeZone:zone}).format(now);date.dateTime=new Intl.DateTimeFormat('sv-SE',{year:'numeric',month:'2-digit',day:'2-digit',timeZone:zone}).format(now);
  let clock=heading.parentElement.querySelector('[data-v93-clock]');
  if(!clock){clock=document.createElement('span');clock.dataset.v93Clock='';clock.className='v93-clock';clock.innerHTML='<ha-icon icon="mdi:clock-outline" aria-hidden="true"></ha-icon><time></time><span></span>';heading.after(clock);}
  const time=clock.querySelector('time');time.dateTime=now.toISOString();time.textContent=new Intl.DateTimeFormat(locale,{hour:'2-digit',minute:'2-digit',timeZone:zone}).format(now);clock.querySelector('span').textContent=this._v93Text(period);clock.dataset.period=period;
  c.querySelectorAll('#todayGrid .rx-category-result').forEach((section,index)=>{
   const card=section.querySelector('[data-v66-ref]'),recipe=card?._v82Recipe||(this._todayResults||[])[index];
   const other=!this._v93MealRelevant(recipe,period);section.classList.toggle('v93-other-meal',other);
   let note=section.querySelector('[data-v93-other-meal]');
   if(other&&!note){note=document.createElement('span');note.dataset.v93OtherMeal='';note.className='v93-meal-note';section.querySelector('h3')?.append(note);}
   if(note){note.textContent=this._v93Text('otherMeal');note.hidden=!other;}
  });
 }
 _v93Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v93Styles'))return;const style=document.createElement('style');style.id='v93Styles';style.textContent=`
   .v93-controls{align-items:flex-start!important;justify-content:space-between!important}.v93-menu-controls{display:flex;align-items:center;flex-wrap:wrap;gap:12px;flex:1 1 420px;min-width:0}.v93-menu-controls h2{display:flex;align-items:baseline;flex-wrap:wrap;gap:8px;margin:0}.v93-menu-controls #searchQ{flex:1 1 180px;width:auto;min-width:100px}.v93-menu-controls>div{min-width:0}.v93-controls>.rx-shared-filters.v93-filters{display:flex!important;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:6px!important;flex:0 1 auto!important;width:auto!important;max-width:100%;margin-left:auto!important;position:relative}.v93-filters button{display:inline-flex!important;width:auto!important;flex:0 1 auto;min-height:44px;padding:8px 10px!important;gap:6px}.v93-active-filters{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:6px}.v93-active-filters:empty{display:none}.v93-filter-drawer{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:6px;flex-basis:100%;max-width:550px;padding:10px 0 0}.v93-filter-drawer[hidden]{display:none!important}.v93-filter-value{max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}.v93-filter-name{font-size:13px}.v93-clock{display:inline-flex;align-items:center;flex-wrap:wrap;gap:6px;color:var(--secondary-text-color);font-size:14px}.v93-clock ha-icon{--mdc-icon-size:20px}[data-v93-date]{font-size:14px;font-weight:400;color:var(--secondary-text-color)}.v93-other-meal [data-v66-ref]{filter:grayscale(.85);opacity:.52;transition:opacity .15s}.v93-other-meal [data-v66-ref]:hover,.v93-other-meal [data-v66-ref]:focus-within{opacity:1;filter:none}.v93-meal-note{display:block;font-size:12px;font-weight:400;color:var(--secondary-text-color);margin-top:4px}.v93-meal-note[hidden]{display:none}.rx-v59-op .v93-cancel{pointer-events:auto;min-height:36px;padding:5px 10px!important;flex:0 0 auto}.rx-v59-op-head{flex-wrap:wrap}.rx-v59-op-title{min-width:0}.rx-v59-op-track[hidden]{display:none}
   @media(max-width:700px){.v93-menu-controls{flex-basis:100%}.v93-controls>.rx-shared-filters.v93-filters{flex-basis:100%!important}.v93-filters .v93-filter-drawer{max-width:100%}.v93-menu-controls #todaySuggest{max-width:100%;white-space:normal}.v93-filter-value{max-width:100px}}
   @media(prefers-reduced-motion:reduce){.v93-other-meal [data-v66-ref]{transition:none}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v93',Cook4MeRecipeHubPanelV93);
