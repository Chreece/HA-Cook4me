import "./cook4me-panel-v97.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v97');
const TARGETS=['calorieTarget','proteinTarget','carbsTarget','fatTarget','saturatedFatTarget','sugarsTarget','fiberTarget','saltTarget','sodiumTarget'];
const present=value=>value!==''&&value!=null;

class Cook4MeRecipeHubPanelV98 extends BasePanel{
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.17.2');return result;}
 _v59CompactMatch(value){
  const out=super._v59CompactMatch(value)||{};
  // Restored cards must retain the same diet/exclusion evidence as live cards.
  for(const key of ['safe','diet','dietCheckVersion','dietRulesSignature','dietary','violations','requiresSubstitutions','eligibleWithSubstitutions','substitutions']){
   if(value?.[key]!==undefined)out[key]=structuredClone(value[key]);
  }
  return Object.keys(out).length?out:null;
 }
 _v83SyncSelection(){
  // The tiny bootstrap shell has no household profile. Keep the saved filters
  // until the actual profile loads instead of resetting a selected person.
  if(!this._entry()?.profile)return;
  return super._v83SyncSelection();
 }
 async _suggestTodayV34(c){
  const context=this._prefKey();
  try{return await super._suggestTodayV34(c);}
  finally{if(context===this._prefKey()){this._v59CancelIdlePersist();this._persistUiSnapshot();}}
 }
 disconnectedCallback(){
  // Navigation can happen before the deferred idle write. Flush the small
  // snapshot while the current user and entry still own these results.
  this._v59CancelIdlePersist();this._persistUiSnapshot();super.disconnectedCallback();
 }
 async _loadBootstrap(...args){
  await super._loadBootstrap(...args);
  const rows=this._todayResults,context=this._prefKey(),revision=this._v63PrefRevision||0;
  if(this._v98RestoredToday===context&&!args[2])return;
  this._v98RestoredToday=context;
  if(!rows?.some(row=>['vegetarian','vegan','pescatarian'].includes(this._v76Diet())&&!row.match?.dietCheckVersion))return;
  // Recover a pre-v98 browser snapshot from the saved HA plan. This never
  // generates a replacement plan or relaxes the current diet checks.
  try{
   const seed=await this._api('cook4me/v30/ui_seed'),saved=seed.perEntry?.[this._entryId];
   if(context!==this._prefKey()||revision!==(this._v63PrefRevision||0)||rows!==this._todayResults||this._todayBusy)return;
   if(!saved?.todayResults?.length||!saved.todayResults.every(row=>this._v76Allowed(row)))return;
   this._todayResults=saved.todayResults;this._todayMeta=saved.todayMeta;
   this._persistUiSnapshot();this._renderTab();
  }catch{/* Keep the previous snapshot; normal refresh can retry when online. */}
 }
 _v98FilterCount(key){
  const f=this._filters(),count=values=>new Set(values||[]).size;
  if(!this._filterActive(key))return 0;
  if(key==='ingredients')return count(f.ingredients);
  if(key==='languages')return count(f.languages);
  if(key==='meals')return count(f.mealTypes);
  if(key==='diet')return Number(!['','profile','omnivore'].includes(f.diet||''))+count((f.excludedIngredients||[]).map(row=>row.ingredientId))+count(f.excludedTerms);
  if(key==='nutrition')return TARGETS.filter(name=>present(f[name])).length+Number(Boolean(f.nutritionGoal&&f.nutritionGoal!=='balanced'));
  if(key==='home')return Number(Boolean(f.onlyHome))+Number(present(f.maxMissing))+Number(f.preferExpiring===false)+Number(f.avoidRecentDays!=null&&Number(f.avoidRecentDays)!==7);
  return 1;
 }
 _v83MergeToolbar(c){
  super._v83MergeToolbar(c);
  const bar=c.querySelector('.v93-filters'),toggle=bar?.querySelector('.v93-filter-toggle'),drawer=bar?.querySelector('.v93-filter-drawer'),active=bar?.querySelector('.v93-active-filters');
  if(!toggle||!drawer||!active)return;
  bar.classList.add('v98-filters');
  toggle.querySelector('span')?.remove();toggle.title=this._v93Text('filters');toggle.setAttribute('aria-label',toggle.title);
  for(const button of bar.querySelectorAll('[data-filter]')){
   button.querySelectorAll('.v93-filter-name,.v93-filter-value,.v98-filter-count').forEach(node=>node.remove());
   const count=this._v98FilterCount(button.dataset.filter);
   if(count>0){const badge=document.createElement('span');badge.className='v98-filter-count';badge.setAttribute('aria-hidden','true');badge.textContent=String(count);button.append(badge);}
  }
  const group=document.createElement('div');group.className='v98-filter-group';group.setAttribute('role','group');group.setAttribute('aria-label',this._v93Text('filters'));
  group.append(drawer,toggle);bar.replaceChildren(group,active);this._v98Styles();
 }
 _v98Styles(){
  if(this.shadowRoot.querySelector('#v98Styles'))return;
  const style=document.createElement('style');style.id='v98Styles';style.textContent=`
   .v98-filters{gap:10px!important}.v98-filter-group{display:flex;align-items:center;gap:5px;padding:3px;border:1px solid var(--divider-color);border-radius:15px;max-width:100%;box-sizing:border-box;min-width:0}
   .v98-filter-group>.v93-filter-drawer{flex:0 1 auto;flex-basis:auto;flex-wrap:wrap;max-width:none;min-width:0;padding:0;gap:4px}
   .v98-filter-group>.v93-filter-toggle{flex:0 0 44px!important}.v98-filters [data-filter],.v98-filters .v93-filter-toggle{position:relative;min-width:44px!important;width:44px!important;min-height:44px;flex:0 0 44px;padding:8px!important}
   .v98-filter-count{position:absolute;top:-5px;right:-5px;min-width:17px;height:17px;box-sizing:border-box;display:grid;place-items:center;padding:0 4px;border-radius:9px;background:var(--primary-color);color:var(--text-primary-color,#fff);font-size:11px;font-weight:700;line-height:17px}
   .v98-filters .v93-active-filters{gap:9px;padding:3px 3px 3px 0;align-items:center}.v98-filters .v93-active-filters:empty{display:none}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v98',Cook4MeRecipeHubPanelV98);
