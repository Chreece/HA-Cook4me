import './cook4me-panel-v82.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v82');
const TARGETS=[['calorieTarget','energy','kcal'],['proteinTarget','protein','g'],['carbsTarget','carbs','g'],['fatTarget','fat','g'],['saturatedFatTarget','saturatedFat','g'],['sugarsTarget','sugars','g'],['fiberTarget','fiber','g'],['saltTarget','salt','g'],['sodiumTarget','nutrientSodium','g']];
const ICONS=['account','account-outline','face-man','face-woman','face-man-outline','face-woman-outline','human-child','baby-face-outline','chef-hat','flower','star','heart'];
const FIELDS=['diet','nutritionGoal','excludedIngredients','excludedTerms',...TARGETS.map(r=>r[0])];
const TEXT={
 en:{household:'Whole household',manual:'Manual',source:'Diet profile',profiles:'Household diet preferences',member:'Household member',name:'Name',icon:'Icon',add:'Add member',remove:'Remove member',excluded:'Excluded ingredients',excludedHelp:'Choose ingredients to exclude for allergies or any other reason.',choose:'Choose an ingredient',addIngredient:'Exclude ingredient',legacy:'Previous exclusion',targets:'Nutrient targets per serving',targetHelp:'Leave a target empty to ignore it. Recipes with known values are ranked closer to these targets.',save:'Save diet profiles',saved:'Diet profiles saved',generalHelp:'Used when Whole household is selected. Each person can have separate preferences.',memberHelp:'Starts with the household preferences. You can change this person’s settings independently.',loading:'Loading the full ingredient catalog…',retry:'Retry catalog',removeExcluded:'Remove exclusion',changed:'Preferences changed. Refresh these recipes to check the current exclusions.',deleted:'This member was removed. The current filters are now Manual.',other:'Other preferences',iconAccount:'Person',iconFace:'Face',iconChild:'Child',iconBaby:'Baby',iconChef:'Chef',iconFlower:'Flower',iconStar:'Star',iconHeart:'Heart'},
 de:{household:'Ganzer Haushalt',manual:'Manuell',source:'Ernährungsprofil',profiles:'Ernährungsprofile im Haushalt',member:'Haushaltsmitglied',name:'Name',icon:'Symbol',add:'Mitglied hinzufügen',remove:'Mitglied entfernen',excluded:'Ausgeschlossene Zutaten',excludedHelp:'Zutaten wegen Allergien oder aus anderen Gründen ausschließen.',choose:'Zutat auswählen',addIngredient:'Zutat ausschließen',legacy:'Bisheriger Ausschluss',targets:'Nährwertziele pro Portion',targetHelp:'Leere Ziele werden ignoriert. Rezepte mit bekannten Werten werden nach Nähe zu diesen Zielen sortiert.',save:'Ernährungsprofile speichern',saved:'Ernährungsprofile gespeichert',generalHelp:'Wird für Ganzer Haushalt verwendet. Jede Person kann eigene Vorlieben haben.',memberHelp:'Beginnt mit den Haushaltsvorlieben. Die Einstellungen dieser Person lassen sich unabhängig ändern.',loading:'Vollständiger Zutatenkatalog wird geladen…',retry:'Katalog erneut laden',removeExcluded:'Ausschluss entfernen',changed:'Vorlieben geändert. Rezepte aktualisieren, um die aktuellen Ausschlüsse zu prüfen.',deleted:'Mitglied entfernt. Die aktuellen Filter sind jetzt Manuell.',other:'Weitere Vorlieben',iconAccount:'Person',iconFace:'Gesicht',iconChild:'Kind',iconBaby:'Baby',iconChef:'Koch',iconFlower:'Blume',iconStar:'Stern',iconHeart:'Herz'},
 el:{household:'Όλο το νοικοκυριό',manual:'Χειροκίνητα',source:'Διατροφικό προφίλ',profiles:'Διατροφικές προτιμήσεις νοικοκυριού',member:'Μέλος νοικοκυριού',name:'Όνομα',icon:'Εικονίδιο',add:'Προσθήκη μέλους',remove:'Αφαίρεση μέλους',excluded:'Αποκλεισμένα υλικά',excludedHelp:'Επίλεξε υλικά για αποκλεισμό λόγω αλλεργίας ή για οποιονδήποτε άλλο λόγο.',choose:'Επιλογή υλικού',addIngredient:'Αποκλεισμός υλικού',legacy:'Προηγούμενος αποκλεισμός',targets:'Στόχοι θρεπτικών ανά μερίδα',targetHelp:'Άφησε κενούς τους στόχους που δεν χρειάζεσαι. Οι συνταγές με γνωστές τιμές κατατάσσονται με βάση την εγγύτητα στους στόχους.',save:'Αποθήκευση διατροφικών προφίλ',saved:'Τα διατροφικά προφίλ αποθηκεύτηκαν',generalHelp:'Χρησιμοποιείται όταν επιλέγεις Όλο το νοικοκυριό. Κάθε άτομο μπορεί να έχει ξεχωριστές προτιμήσεις.',memberHelp:'Ξεκινά με τις προτιμήσεις του νοικοκυριού. Οι ρυθμίσεις του ατόμου μπορούν να αλλάξουν ανεξάρτητα.',loading:'Φόρτωση πλήρους καταλόγου υλικών…',retry:'Επανάληψη φόρτωσης',removeExcluded:'Αφαίρεση αποκλεισμού',changed:'Οι προτιμήσεις άλλαξαν. Ανανέωσε τις συνταγές για έλεγχο των τωρινών αποκλεισμών.',deleted:'Το μέλος αφαιρέθηκε. Τα τωρινά φίλτρα είναι πλέον Χειροκίνητα.',other:'Άλλες προτιμήσεις',iconAccount:'Άτομο',iconFace:'Πρόσωπο',iconChild:'Παιδί',iconBaby:'Μωρό',iconChef:'Μάγειρας',iconFlower:'Λουλούδι',iconStar:'Αστέρι',iconHeart:'Καρδιά'}
};
const clone=v=>structuredClone(v);
const fold=v=>String(v||'').normalize('NFD').replace(/\p{M}/gu,'').toLowerCase();
class Cook4MeRecipeHubPanelV83 extends BasePanel{
 _v83Text(key){return TEXT[this._uiIngredientLanguage()]?.[key]||TEXT.en[key]||this._t(key);}
 _v83Diet(row={}){return {diet:row.diet||'omnivore',nutritionGoal:row.nutritionGoal||'balanced',excludedIngredients:clone(row.excludedIngredients||[]),excludedTerms:clone(row.excludedTerms||[]),...Object.fromEntries(TARGETS.map(([key])=>[key,row[key]??'']))};}
 _v83Profiles(){
  const profile=this._entry()?.profile||{};if(profile.dietProfiles)return clone(profile.dietProfiles);
  const household=this._v83Diet({diet:profile.diet,excludedTerms:[...new Set([...(profile.allergies||[]),...(profile.avoid||[])])]});
  return {household,members:(profile.householdMembers||[]).map((name,index)=>({...clone(household),id:`legacy-${index}`,name,icon:'account'}))};
 }
 _v83Selected(source){const profiles=this._v83Profiles();return source==='household'?profiles.household:profiles.members.find(r=>source===`member:${r.id}`);}
 _filters(){
  const f=super._filters();
  if(!f.dietProfile){const base=this._v83Profiles().household;const inherit=(!f.diet||f.diet==='profile')&&!TARGETS.some(([key])=>f[key]!==''&&f[key]!=null)&&(!f.nutritionGoal||f.nutritionGoal==='balanced');Object.assign(f,inherit?this._v83Diet(base):{excludedIngredients:clone(base.excludedIngredients||[]),excludedTerms:clone(base.excludedTerms||[])});if(!f.diet||f.diet==='profile')f.diet=base.diet;f.dietProfile=inherit?'household':'manual';}
  return f;
 }
 _v83SyncSelection(){
  const f=this._filters();if(f.dietProfile==='manual')return;
  const row=this._v83Selected(f.dietProfile);
  if(row)Object.assign(f,this._v83Diet(row));else{f.dietProfile='manual';this._persistPreferences({filters:f});}
 }
 _v83SourceLabel(){const f=this._filters();return f.dietProfile==='manual'?this._v83Text('manual'):f.dietProfile==='household'?this._v83Text('household'):this._v83Selected(f.dietProfile)?.name||this._v83Text('manual');}
 _persistPreferences(patch){
  if(patch.filters&&this._v83FilterBefore&&this.shadowRoot?.querySelector('[data-filter-dialog]')){
   const compare=value=>{const normalized=clone(value);for(const key of [...TARGETS.map(r=>r[0]),'maxCost','maxMissing','avoidRecentDays','calorieTolerance'])normalized[key]=normalized[key]===''||normalized[key]==null?null:Number(normalized[key]);for(const key of ['languages','mealTypes','ingredients','excludedTerms'])if(Array.isArray(normalized[key]))normalized[key]=[...normalized[key]].sort();return JSON.stringify(normalized);};
   if(compare(patch.filters)!==compare(this._v83FilterBefore))patch.filters.dietProfile='manual';
   this._v83FilterBefore=null;
  }
  if(patch.filters)this._v83FilterBefore=null;
  return super._persistPreferences(patch);
 }
 _filterActive(key){const f=this._filters();if(key==='nutrition')return TARGETS.some(([name])=>f[name]!==''&&f[name]!=null)||f.nutritionGoal!=='balanced';if(key==='diet'&&((f.excludedIngredients||[]).length||(f.excludedTerms||[]).length))return true;return super._filterActive(key);}
 _mountFilters(c){
  super._mountFilters(c);const bar=c.querySelector('.rx-shared-filters');if(!bar)return;
  const source=document.createElement('button');source.type='button';source.className='btn secondary';source.dataset.filter='dietProfile';source.setAttribute('aria-label',`${this._v83Text('source')}: ${this._v83SourceLabel()}`);source.title=source.getAttribute('aria-label');source.setAttribute('aria-pressed',String(this._filters().dietProfile!=='manual'));
  const selected=this._v83Selected(this._filters().dietProfile),icon=this._filters().dietProfile==='manual'?'tune-variant':selected?.icon||'home-account';source.innerHTML=`<ha-icon icon="mdi:${ICONS.includes(icon)?icon:icon==='home-account'?icon:'tune-variant'}" aria-hidden="true"></ha-icon>`;source.onclick=()=>this._showFilter('dietProfile');bar.prepend(source);
  this._v83MergeToolbar(c);this._v83Styles();
 }
 _v83MergeToolbar(c){
  const bar=c.querySelector('.rx-shared-filters');const toolbar=c.querySelector('#todaySuggest,#generateWeek,#searchBtn')?.closest('.toolbar');if(!bar||!toolbar)return;
  toolbar.classList.add('v83-controls');toolbar.closest('section.card')?.classList.add('v83-control-card');toolbar.prepend(bar);
 }
 _renderToday(c){super._renderToday(c);this._v83MergeToolbar(c);}
 _renderWeek(c){super._renderWeek(c);this._v83MergeToolbar(c);}
 _renderOfficial(c){super._renderOfficial(c);this._v83MergeToolbar(c);}
 _v83TargetHtml(row){const e=v=>this._escape(String(v??''));return `<div class="v83-targets">${TARGETS.map(([key,label,unit])=>`<label class="field">${e(this._t(label))} (${unit})<input type="number" min="0" step="any" max="${key==='calorieTarget'?10000:key==='carbsTarget'?2000:['saltTarget','sodiumTarget'].includes(key)?100:1000}" data-v83-field="${key}" data-field="${key}" value="${e(row[key])}"></label>`).join('')}</div>`;}
 _showFilter(key){
  this._v83FilterBefore=null;
  if(key==='dietProfile')return this._v83ShowSource();
  this._v83FilterBefore=clone(this._filters());super._showFilter(key);const dialog=this.shadowRoot.querySelector(`[data-filter-dialog="${key}"] .rx-dialog`);if(!dialog)return;
  if(key==='nutrition'){
   dialog.querySelectorAll('[data-field="calorieTarget"],[data-field="proteinTarget"],[data-field="fiberTarget"]').forEach(input=>input.closest('.field')?.remove());
   const targets=document.createElement('div');targets.innerHTML=this._v83TargetHtml(this._filters());dialog.querySelector('footer').before(targets);
  }
  if(key==='diet'){
   dialog.querySelector('[data-field=diet] option[value=profile]')?.remove();
   const draft=clone(this._filters()),section=document.createElement('section');section.className='v83-exclusions';dialog.querySelector('footer').before(section);this._v83ExclusionPicker(section,draft,()=>{});
   dialog.querySelector('[data-apply]').addEventListener('click',()=>{this._filters().excludedIngredients=draft.excludedIngredients;this._filters().excludedTerms=draft.excludedTerms;},true);
  }
 }
 _v83ShowSource(){
  this._v63CloseFilter?.();const e=v=>this._escape(String(v??'')),f=this._filters(),p=this._v83Profiles();const overlay=document.createElement('div');overlay.className='rx-overlay';overlay.dataset.filterDialog='dietProfile';
  overlay.innerHTML=`<div class="rx-dialog" role="dialog" aria-modal="true" aria-label="${e(this._v83Text('source'))}"><div class="detail-head"><h2>${e(this._v83Text('source'))}</h2><button class="btn secondary" data-close aria-label="${e(this._t('closeDialog'))}">✕</button></div><label class="field">${e(this._v83Text('source'))}<select data-v83-source><option value="manual">${e(this._v83Text('manual'))}</option><option value="household">${e(this._v83Text('household'))}</option>${p.members.map(row=>`<option value="member:${e(row.id)}">${e(row.name)}</option>`).join('')}</select></label><footer><button class="btn" data-apply>${e(this._t('apply'))}</button></footer></div>`;
  const restore=this.shadowRoot.activeElement,close=()=>{overlay.remove();document.removeEventListener('keydown',keydown);this._v63CloseFilter=null;restore?.focus();},keydown=event=>{if(event.key==='Escape')close();else this._trapFocus(event,overlay);};this._v63CloseFilter=close;document.addEventListener('keydown',keydown);
  overlay.querySelector('select').value=f.dietProfile;overlay.querySelector('[data-close]').onclick=close;overlay.onclick=event=>{if(event.target===overlay)close();};
  overlay.querySelector('[data-apply]').onclick=()=>{const source=overlay.querySelector('select').value,next={...f,dietProfile:source},selected=this._v83Selected(source);if(selected)Object.assign(next,this._v83Diet(selected));this._v63Filters=next;this._persistPreferences({filters:next});this._v83InvalidateResults();close();this._renderTab();};
  this.shadowRoot.append(overlay);overlay.querySelector('select').focus();
 }
 _v83InvalidateResults(){this._v61SearchRequest=(this._v61SearchRequest||0)+1;this._v64TodayRequest=null;this._todayBusy=false;this._v66Tags?.clear();this._v63CloseRecipe?.();}
 async _v66FilterTag(kind,value){if((kind==='diet'&&this._filters().diet!==value)||(kind!=='diet'&&JSON.stringify(this._filters().mealTypes)!==JSON.stringify([value])))this._filters().dietProfile='manual';return super._v66FilterTag(kind,value);}
 _v83DraftState(){
  const context=this._prefKey();if(this._v83Draft?.context!==context){this._v83Saving=false;this._v83Draft={context,value:this._v83Profiles(),preferences:(this._entry()?.profile?.preferences||[]).join('\n'),dirty:false,open:new Set(),pickers:new Set()};}
  if(!this._v83Draft.dirty){this._v83Draft.value=this._v83Profiles();this._v83Draft.preferences=(this._entry()?.profile?.preferences||[]).join('\n');}
  return this._v83Draft;
 }
 _renderProfile(c){
  const state=this._v83DraftState();super._renderProfile(c);const food=c.querySelector('[data-v78-section="food"]');if(!food)return;this._v83RenderProfiles(food,state);this._v83Styles();
 }
 _v83RenderProfiles(c,state){
  const e=v=>this._escape(String(v??'')),t=k=>e(this._v83Text(k)),rows=[{...state.value.household,id:'household'},...state.value.members];
  const content=row=>`<div class="v83-profile-body">${row.id==='household'?`<p class="muted">${t('generalHelp')}</p>`:`<div class="v83-member-name"><label class="field">${t('name')}<input required maxlength="80" data-v83-field="name" value="${e(row.name)}"></label><label class="field">${t('icon')}<select data-v83-field="icon">${ICONS.map(icon=>`<option value="${icon}" ${icon===(row.icon||'account')?'selected':''}>${e(this._v83IconName(icon))}</option>`).join('')}</select></label><button type="button" class="btn secondary" data-v83-remove>${t('remove')}</button></div>`}<label class="field">${e(this._t('diet'))}<select data-v83-field="diet">${this._todayDietOptions(row.diet).replace(/<option value="profile"[^>]*>.*?<\/option>/,'')}</select></label><details class="v83-target-section" ${state.open.has(row.id+':targets')?'open':''}><summary>${t('targets')}</summary><p class="muted">${t('targetHelp')}</p><label class="field">${e(this._t('nutritionTarget'))}<select data-v83-field="nutritionGoal">${this._todayGoalOptions(row.nutritionGoal||'balanced')}</select></label>${this._v83TargetHtml(row)}</details><section data-v83-exclusions></section></div>`;
  c.innerHTML=`<h2>${t('profiles')}</h2><form data-v83-profiles>${rows.map(row=>row.id==='household'?`<section class="card v83-diet-card" data-v83-profile="household"><h3><ha-icon icon="mdi:home-account"></ha-icon>${t('household')}</h3>${content(row)}</section>`:`<details class="card v83-diet-card" data-v83-profile="${e(row.id)}" ${state.open.has(row.id)?'open':''}><summary><ha-icon icon="mdi:${ICONS.includes(row.icon)?row.icon:'account'}"></ha-icon><span data-v83-member-title>${e(row.name||this._v83Text('member'))}</span></summary>${content(row)}</details>`).join('')}<div class="v83-profile-actions"><button type="button" class="btn secondary" data-v83-add ${state.value.members.length>=20?'disabled':''}><ha-icon icon="mdi:account-plus"></ha-icon>${t('add')}</button></div><label class="field">${t('other')}<textarea id="preferences">${e(state.preferences)}</textarea></label><button class="btn" type="submit" data-v83-save ${this._v83Saving?'disabled':''}>${t('save')}</button><p role="status" data-v83-status></p></form>`;
  const dirty=()=>state.dirty=true;
  c.querySelectorAll('[data-v83-profile]').forEach(card=>{
   const id=card.dataset.v83Profile,row=id==='household'?state.value.household:state.value.members.find(r=>r.id===id);
   if(card.tagName==='DETAILS')card.addEventListener('toggle',()=>card.open?state.open.add(id):state.open.delete(id));
   card.querySelector('.v83-target-section').addEventListener('toggle',event=>event.target.open?state.open.add(id+':targets'):state.open.delete(id+':targets'));
   card.querySelectorAll('[data-v83-field]').forEach(input=>{const update=()=>{row[input.dataset.v83Field]=input.value;dirty();if(input.dataset.v83Field==='name')card.querySelector('[data-v83-member-title]').textContent=input.value||this._v83Text('member');if(input.dataset.v83Field==='icon')card.querySelector('summary>ha-icon')?.setAttribute('icon','mdi:'+input.value);};input.oninput=update;input.onchange=update;});
   card.querySelector('[data-v83-remove]')?.addEventListener('click',()=>{state.value.members=state.value.members.filter(r=>r.id!==id);state.open.delete(id);dirty();this._v83RenderProfiles(c,state);});
   this._v83ExclusionPicker(card.querySelector('[data-v83-exclusions]'),row,dirty,state.pickers,id);
  });
  c.querySelector('#preferences').oninput=event=>{state.preferences=event.target.value;dirty();};
  c.querySelector('[data-v83-add]').onclick=()=>{const id=globalThis.crypto?.randomUUID?.()||`member-${Date.now()}-${Math.random().toString(36).slice(2)}`;state.value.members.push({...clone(state.value.household),id,name:'',icon:'account'});state.open.add(id);dirty();this._v83RenderProfiles(c,state);c.querySelector(`[data-v83-profile="${id}"] [data-v83-field="name"]`).focus();};
  c.querySelector('form').onsubmit=event=>{event.preventDefault();void this._v83SaveProfiles(c,state);};
 }
 _v83IconName(icon){const key=icon.startsWith('face-')?'iconFace':icon.startsWith('account')?'iconAccount':{'human-child':'iconChild','baby-face-outline':'iconBaby','chef-hat':'iconChef',flower:'iconFlower',star:'iconStar',heart:'iconHeart'}[icon];return this._v83Text(key)+(icon.endsWith('outline')?' ◯':icon==='face-woman'?' ♀':icon==='face-man'?' ♂':'');}
 _v83ExclusionPicker(c,row,onchange,openSet=new Set(),key='filter'){
  row.excludedIngredients??=[];row.excludedTerms??=[];const e=v=>this._escape(String(v??'')),t=k=>e(this._v83Text(k));
  c.innerHTML=`<h4>${t('excluded')}</h4><p class="muted">${t('excludedHelp')}</p><div class="v83-excluded-chips"></div><details class="v83-ingredient-picker" ${openSet.has(key)?'open':''}><summary>${t('choose')}</summary><div class="v83-picker-body"><label class="field">${e(this._t('ingredientSearch'))}<input type="search" data-v83-ingredient-search></label><label class="field">${t('choose')}<select data-v83-ingredient></select></label><button type="button" class="btn secondary" data-v83-exclude>${t('addIngredient')}</button><span class="muted" data-v83-catalog-status></span></div></details>`;
  const chips=()=>{const holder=c.querySelector('.v83-excluded-chips');holder.replaceChildren();for(const [kind,values] of [['excludedIngredients',row.excludedIngredients],['excludedTerms',row.excludedTerms]])values.forEach((value,index)=>{const chip=document.createElement('span');chip.className='v83-excluded-chip';const text=document.createElement('span');text.textContent=kind==='excludedTerms'?String(value):this._v83IngredientLabel(value);const button=document.createElement('button');button.type='button';button.className='btn secondary';button.textContent='×';button.setAttribute('aria-label',`${this._v83Text('removeExcluded')}: ${text.textContent}`);button.onclick=()=>{values.splice(index,1);onchange();chips();fill();};chip.append(text,button);holder.append(chip);});};
  const fill=()=>{const select=c.querySelector('[data-v83-ingredient]'),query=fold(c.querySelector('[data-v83-ingredient-search]').value),selected=new Set(row.excludedIngredients.map(r=>String(r.ingredientId)));const choices=(this._ingredientCatalog||[]).filter(r=>!selected.has(String(r.ingredientId||r.key||r.id))&&fold(r.name+' '+(r.canonicalName||'')).includes(query));select.innerHTML=`<option value="">${t('choose')}</option>`+choices.map((r,index)=>`<option value="${index}">${e(r.name)}</option>`).join('');select._v83Rows=choices;c.querySelector('[data-v83-catalog-status]').textContent=this._ingredientCatalogLoading?this._v83Text('loading'):`${choices.length}`;c.querySelector('[data-v83-exclude]').disabled=!choices.length;};
  const details=c.querySelector('details');details.addEventListener('toggle',()=>{if(details.open){openSet.add(key);fill();if(!this._ingredientCatalog?.length&&!this._ingredientCatalogLoading){void this._loadIngredientCatalog().then(()=>{if(c.isConnected)fill();});}}else openSet.delete(key);});
  c.querySelector('[data-v83-ingredient-search]').oninput=fill;
  c.querySelector('[data-v83-exclude]').onclick=()=>{const select=c.querySelector('[data-v83-ingredient]'),item=select.value!==''?select._v83Rows?.[Number(select.value)]:null;if(!item)return;const identity=String(item.ingredientId||item.key||item.id);row.excludedIngredients.push({ingredientId:identity,name:item.name,canonicalName:item.canonicalName||item.name,sourceIngredientIds:clone(item.sourceIngredientIds||[identity])});onchange();chips();fill();};
  chips();if(details.open)fill();
 }
 _v83IngredientLabel(item){return this._ingredientCatalog?.find(row=>String(row.ingredientId||row.key||row.id)===String(item.ingredientId)||row.sourceIngredientIds?.includes(item.ingredientId))?.name||item.name;}
 async _v83SaveProfiles(c,state){
  if(this._v83Saving)return;const form=c.querySelector('form');if(!form.reportValidity())return;
  this._v83Saving=true;const context=this._prefKey(),payload=clone(state.value),preferences=this._splitList(state.preferences),revision=JSON.stringify(payload)+state.preferences;
  c.querySelector('[data-v83-save]').disabled=true;
  try{const result=await this._api('cook4me/v35/diet_profiles',{entry_id:this._entryId,profiles:payload,preferences});if(context!==this._prefKey())return;const entry=this._entry();if(entry)entry.profile={...entry.profile,...Object.fromEntries(['dietProfiles','householdMembers','diet','allergies','avoid','excludedIngredients','preferences'].filter(key=>key in (result.profile||{})).map(key=>[key,result.profile[key]]))};if(revision===JSON.stringify(state.value)+state.preferences){state.dirty=false;state.value=this._v83Profiles();}this._v83SyncSelection();super._persistPreferences({filters:this._filters()});this._v83InvalidateResults();c.querySelector('[data-v83-status]').textContent=this._v83Text('saved');}
  catch(error){if(context===this._prefKey())c.querySelector('[data-v83-status]').textContent=String(error.message||error);}
  finally{if(context===this._prefKey()){this._v83Saving=false;c.querySelector('[data-v83-save]').disabled=false;}}
 }
 _v83RulesSignature(){const f=this._filters(),ids=[...new Set((f.excludedIngredients||[]).flatMap(r=>[r.ingredientId,...(r.sourceIngredientIds||[])]))].sort(),terms=[...new Set([...(f.excludedTerms||[]),...(f.excludedIngredients||[]).map(r=>r.canonicalName||r.name)].map(v=>String(v).trim().toLowerCase()).filter(Boolean))].sort();return JSON.stringify([this._v76Diet(),ids,terms]);}
 _v76Allowed(recipe){if(!super._v76Allowed(recipe))return false;const f=this._filters();return !((f.excludedIngredients||[]).length||(f.excludedTerms||[]).length)||(recipe.match?.dietRulesSignature===this._v83RulesSignature()&&(recipe.match.safe||recipe.match.eligibleWithSubstitutions));}
 _v77CanSend(recipe,target){return this._v76Allowed(recipe)&&super._v77CanSend(recipe,target);}
 async _api(type,data={}){
  const checked=/\/(recipe_detail|recipe_presentation|today_suggest|official_search|week_generate)$/.test(type),context=this._prefKey(),signature=JSON.stringify(this._filters());
  if(/\/(recipe_detail|recipe_presentation)$/.test(type))data={...data,shared_filters:clone(this._filters())};
  if(type.endsWith('/send_multi')&&data.recipe){const filters=clone(this._filters());if(data.entry_id!==this._entryId)filters.dietProfile='manual';data={...data,recipe:{...data.recipe,sendFilters:filters}};}
  const result=await super._api(type,data);if(checked&&(context!==this._prefKey()||signature!==JSON.stringify(this._filters())))throw new Error(this._v83Text('changed'));return result;
 }
 _renderTab(){this._v83SyncSelection();const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.16.8');this._v83Styles();const c=this.shadowRoot?.querySelector('#content'),f=this._filters();if(c&&['today','week','official'].includes(this._tab)&&((f.excludedIngredients||[]).length||(f.excludedTerms||[]).length)&&!c.querySelector('[data-v66-ref]')){const note=c.querySelector('[data-v76-refresh]')||document.createElement('p');note.className='muted';note.dataset.v83Refresh='';note.textContent=this._v83Text('changed');if(!note.isConnected)c.append(note);}return result;}
 _resetV51EntryState(...args){this._v83Draft=null;this._v83Saving=false;this._v83FilterBefore=null;return super._resetV51EntryState(...args);}
 _v83Styles(){
  if(this.shadowRoot?.querySelector('#v83Styles'))return;const style=document.createElement('style');style.id='v83Styles';style.textContent=`
  .v83-controls{display:flex!important;align-items:center;flex-wrap:wrap;gap:12px!important}.v83-controls>.rx-shared-filters{display:grid!important;grid-template-columns:repeat(8,minmax(0,1fr));flex:0 0 380px;width:380px;max-width:100%;margin:0!important;gap:4px}.v83-controls>h2{margin:0;flex:1;min-width:80px}.v83-controls>#searchQ{flex:1 1 220px;min-width:140px;width:auto}.v83-control-card{padding:14px!important}.v83-controls .rx-shared-filters button{min-height:44px}.v83-controls>.rx-shared-filters+div{flex:1;min-width:150px}
  .v83-diet-card{margin:12px 0;padding:16px}.v83-diet-card>summary,.v83-diet-card>h3{display:flex;align-items:center;gap:10px;font-size:18px;font-weight:650;margin:0;cursor:pointer}.v83-diet-card>summary::after{content:'⌄';margin-left:auto}.v83-diet-card[open]>summary::after{transform:rotate(180deg)}.v83-profile-body{padding-top:14px}.v83-profile-body>.field{max-width:420px}.v83-target-section{margin:18px 0}.v83-target-section>summary,.v83-ingredient-picker>summary{cursor:pointer;min-height:44px;display:flex;align-items:center;font-weight:600}.v83-targets{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.v83-targets .field{margin:0}.v83-member-name{display:flex;align-items:end;gap:12px;flex-wrap:wrap;margin-bottom:16px}.v83-member-name>.field{flex:1;min-width:140px}.v83-excluded-chips{display:flex;flex-wrap:wrap;gap:8px}.v83-excluded-chip{display:inline-flex;align-items:center;gap:6px;padding-left:12px;border-radius:24px;background:var(--secondary-background-color);max-width:100%;overflow-wrap:anywhere}.v83-excluded-chip button{min-width:40px;padding:4px!important;border:0!important;background:none!important}.v83-picker-body{display:flex;align-items:end;flex-wrap:wrap;gap:10px}.v83-picker-body>.field{flex:1;min-width:160px}.v83-picker-body select{max-width:100%;width:100%;text-overflow:ellipsis}.v83-profile-actions{margin:16px 0}[data-v83-profiles] input,[data-v83-profiles] select,[data-v83-profiles] textarea{width:100%;box-sizing:border-box;min-width:0}.v83-exclusions{margin:18px 0}.v83-diet-card .field{display:flex;flex-direction:column;gap:6px}.v83-diet-card h4{margin-bottom:8px}.v83-diet-card small{display:block}
  @media(max-width:680px){.v83-controls>.rx-shared-filters{flex-basis:100%;width:100%;gap:3px}.v83-controls .rx-shared-filters button{min-height:40px;border-radius:10px;padding:4px!important}.v83-controls .rx-shared-filters ha-icon{--mdc-icon-size:20px}.v83-controls>#searchQ{flex-basis:calc(100% - 100px);min-width:0}.v83-control-card{padding:10px!important}.v83-targets{grid-template-columns:repeat(2,minmax(0,1fr))}.v83-diet-card{padding:12px}.v83-picker-body>.field{min-width:100%;flex-basis:100%}.v83-member-name{align-items:stretch}.v83-member-name>.field{min-width:100%}}
  `;this.shadowRoot?.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v83',Cook4MeRecipeHubPanelV83);
