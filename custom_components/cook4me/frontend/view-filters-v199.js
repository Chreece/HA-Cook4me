// Per-view filters use the existing user/entry preference store and validators.
export const FILTER_VIEWS=['today','week','official','book','mine','profile','shopping','ai'];
const object=value=>!!value&&typeof value==='object'&&!Array.isArray(value);
const copy=value=>structuredClone(value);
const viewKey=value=>FILTER_VIEWS.includes(value)?value:'today';
export function viewFilterMap(value){
 return Object.fromEntries(FILTER_VIEWS.filter(view=>object(value?.[view])).map(view=>[view,copy(value[view])]));
}
export function mergePreferencePatches(older,newer){
 const result={...(older||{}),...(newer||{})};
 if(older?.filtersByView||newer?.filtersByView)result.filtersByView={...viewFilterMap(older?.filtersByView),...viewFilterMap(newer?.filtersByView)};
 return result;
}
export const ViewFiltersMixin=Base=>class extends Base{
 _filters(){
  const scope=this._prefKey();
  if(this._v199FilterScope!==scope){
   // Retain the old shared selection as a one-time seed, not a live shared object.
   const legacy=copy(super._filters());
   let cached={};try{cached=JSON.parse(localStorage.getItem(scope)||'{}')||{};}catch{}
   const saved=viewFilterMap(cached.filtersByView);
   this._v199HadViewFilters=Object.keys(saved).length>0;
   this._v199Filters=Object.fromEntries(FILTER_VIEWS.map(view=>[view,copy(saved[view]||legacy)]));
   this._v199FilterScope=scope;this._v199ActiveView=null;
  }
  const view=viewKey(this._tab==='recommend'?'today':this._tab);
  if(this._v199ActiveView&&object(this._v63Filters))this._v199Filters[this._v199ActiveView]=this._v63Filters;
  this._v199ActiveView=view;this._v63Filters=this._v199Filters[view];
  // Preserve inherited household/member diet and nutrient-target handling.
  return super._filters();
 }
 _cachePreferences(){
  const filters=this._filters();
  try{localStorage.setItem(this._prefKey(),JSON.stringify({lastTab:this._tab,filters,filtersByView:this._v199Filters,pending:this._v199PreferenceRequest?.key===this._prefKey()?mergePreferencePatches(this._v199PreferenceRequest.patch,this._v63Dirty):this._v63Dirty}));}catch{}
 }
 _persistPreferences(patch){
  this._filters();
  if(object(patch?.filters)){
   const view=this._v199ActiveView;this._v199HadViewFilters=true;
   this._v63Filters=patch.filters;this._v199Filters[view]=patch.filters;
   // Reuse this reference until the inherited diet-profile normalization runs.
   patch={...patch,filtersByView:{...viewFilterMap(this._v63Dirty?.filtersByView),[view]:patch.filters}};
   this._v179ClearOpenRecipe?.(view);this._v63CloseRecipe?.();
  }
  return super._persistPreferences(patch);
 }
 _v199PendingPreferences(){
  const request=this._v199PreferenceRequest;
  return mergePreferencePatches(request?.key===this._prefKey()?request.patch:null,this._v63Dirty);
 }
 async _restorePreferences(){
  if(!this._entryId||!this._hass?.user?.id)return;
  this._filters();const key=this._prefKey(),connection=this._hass.connection;
  if(this._v63PrefsLoaded===key||(this._v63PrefsLoading?.key===key&&this._v63PrefsLoading.connection===connection))return;
  const request={key,connection};this._v63PrefsLoading=request;
  const revision=this._v63PrefRevision||0;
  // A visibility/reconnect read can return before OR after the write it raced.
  // Retain the local patch even if its acknowledgement arrives before this read.
  const pendingAtStart=this._v199PendingPreferences();
  try{
   const saved=await connection.sendMessagePromise({type:'cook4me/v31/ui_preferences',entry_id:this._entryId});
   if(key!==this._prefKey()||connection!==this._hass?.connection||this._v63PrefsLoading!==request)return;
   this._v63PrefsLoaded=key;
   if(revision===(this._v63PrefRevision||0)){
    const remote=viewFilterMap(saved?.filtersByView),pending=mergePreferencePatches(pendingAtStart,this._v199PendingPreferences());
    if(Object.keys(remote).length)this._v199Filters={...this._v199Filters,...remote};
    else if(!this._v199HadViewFilters&&object(saved?.filters)){
     this._v199Filters=Object.fromEntries(FILTER_VIEWS.map(view=>[view,{...copy(this._v199Filters[view]),...copy(saved.filters)}]));
    }
    Object.assign(this._v199Filters,viewFilterMap(pending?.filtersByView));
    if(object(pending?.filters)&&!pending?.filtersByView)this._v199Filters[viewKey(pending.lastTab||this._tab)]=copy(pending.filters);
    const tab=pending?.lastTab||saved?.lastTab;if(FILTER_VIEWS.includes(tab))this._tab=tab;
    this._v199HadViewFilters=true;this._v199ActiveView=null;this._filters();this._cachePreferences();this._renderTabs();this._renderTab();
   }
   if(this._v63Dirty)void this._flushPreferences();
  }catch{if(key===this._prefKey()&&connection===this._hass?.connection&&this._v63PrefsLoading===request)this._v63PrefsLoaded=key;}
  finally{if(this._v63PrefsLoading===request)this._v63PrefsLoading=null;}
 }
 async _flushPreferences(){
  const key=this._prefKey(),connection=this._hass?.connection;
  if(!this._v63Dirty||!connection||this._v199PreferenceRequest?.key===key)return;
  const patch=copy(this._v63Dirty),request={key,connection,patch};
  this._v199PreferenceRequest=request;this._v63Dirty=null;this._v63Saving=true;
  // Cache the in-flight patch too: a reload must not lose an offline edit.
  try{localStorage.setItem(key,JSON.stringify({lastTab:this._tab,filters:this._filters(),filtersByView:this._v199Filters,pending:patch}));}catch{}
  let failed=false;
  try{await connection.sendMessagePromise({type:'cook4me/v31/ui_preferences',entry_id:this._entryId,preferences:patch});}
  catch{
   failed=true;
   if(key===this._prefKey()){
    this._v63Dirty=mergePreferencePatches(patch,this._v63Dirty);
    this._message(this._t('preferencesPending'),true);
   }
  }finally{
   if(this._v199PreferenceRequest===request){this._v199PreferenceRequest=null;this._v63Saving=false;}
   if(key===this._prefKey())this._cachePreferences();
  }
  // A failed current-context write waits for reconnect; never spin on failure.
  if(this._v63Dirty&&(!failed||key!==this._prefKey()))void this._flushPreferences();
 }
 _loadOfficialLanguages(){return this._filters().languages||super._loadOfficialLanguages();}
};
