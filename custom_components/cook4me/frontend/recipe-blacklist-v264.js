const TEXT={
 en:{
  blacklist:'Blacklist recipe',
  blacklisted:'Recipe blacklisted',
  blacklistTitle:'Recipe blacklist',
  blacklistHelp:'Blacklisted recipes are hidden everywhere and are excluded from future suggestions, searches and weekly plans.',
  empty:'No blacklisted recipes.',
  undo:'Undo',
  restored:'Recipe removed from blacklist'
 },
 de:{
  blacklist:'Rezept sperren',
  blacklisted:'Rezept gesperrt',
  blacklistTitle:'Rezept-Sperrliste',
  blacklistHelp:'Gesperrte Rezepte werden überall ausgeblendet und aus zukünftigen Vorschlägen, Suchen und Wochenplänen ausgeschlossen.',
  empty:'Keine gesperrten Rezepte.',
  undo:'Rückgängig',
  restored:'Rezept von der Sperrliste entfernt'
 },
 el:{
  blacklist:'Αποκλεισμός συνταγής',
  blacklisted:'Η συνταγή αποκλείστηκε',
  blacklistTitle:'Μαύρη λίστα συνταγών',
  blacklistHelp:'Οι αποκλεισμένες συνταγές κρύβονται παντού και δεν συμμετέχουν πλέον σε προτάσεις, αναζητήσεις ή εβδομαδιαία πλάνα.',
  empty:'Δεν υπάρχουν αποκλεισμένες συνταγές.',
  undo:'Αναίρεση',
  restored:'Η συνταγή αφαιρέθηκε από τη μαύρη λίστα'
 }
};

const textValue=value=>String(value??'').trim();

export function recipeBlacklistIdentities(recipe={}){
 const identities=[];
 for(const key of [
  'displayFamilyId','groupingFunctionalId','groupingId','recipeFunctionalId',
  'variantFunctionalId','functionalId','id'
 ]){
  const value=textValue(recipe?.[key]);
  const identity=value?`${key}:${value}`:'';
  if(identity&&!identities.includes(identity))identities.push(identity);
 }
 if(!identities.length){
  const title=textValue(recipe?.title||recipe?.canonicalName)
   .normalize('NFD').replace(/\p{M}/gu,'').toLocaleLowerCase()
   .replace(/[^\p{L}\p{N}]+/gu,' ').trim();
  if(title)identities.push(`title:${title}`);
 }
 return identities;
}

export function recipeIsBlacklisted(recipe,rows=[]){
 const wanted=new Set(recipeBlacklistIdentities(recipe));
 if(!wanted.size)return false;
 return (Array.isArray(rows)?rows:[]).some(row=>{
  if(!row||typeof row!=='object')return false;
  const blocked=new Set([
   textValue(row.identity),
   ...(Array.isArray(row.identities)?row.identities.map(textValue):[])
  ].filter(Boolean));
  return [...wanted].some(identity=>blocked.has(identity));
 });
}

export const RecipeBlacklistMixin=Base=>class extends Base{
 _v264Text(key){
  const code=String(this._uiIngredientLanguage?.()||this._langCode?.()||'en')
   .toLowerCase().replace('_','-').split('-',1)[0];
  return (TEXT[code]||TEXT.en)[key]||TEXT.en[key]||key;
 }
 _v264Rows(){
  const rows=this._entry?.()?.profile?.recipeBlacklist;
  return Array.isArray(rows)?rows:[];
 }
 _v264IsBlacklisted(recipe){
  return recipeIsBlacklisted(recipe,this._v264Rows());
 }
 _v264CompactRecipe(recipe={}){
  const keys=[
   'displayFamilyId','groupingFunctionalId','groupingId','recipeFunctionalId',
   'variantFunctionalId','functionalId','id','title','canonicalName','source',
   'selectedLanguage','language','sourceLanguage'
  ];
  return Object.fromEntries(keys.filter(key=>recipe?.[key]!==undefined).map(key=>[key,recipe[key]]));
 }
 _v264AdoptProfile(result){
  const entry=this._entry?.();
  if(entry&&result?.profile&&typeof result.profile==='object'){
   entry.profile={...(entry.profile||{}),...result.profile};
  }
 }
 _v264AfterChange(message){
  this._v83InvalidateResults?.();
  this._v63CloseRecipe?.();
  this._v179ClearOpenRecipe?.();
  this._message?.(message);
  this._renderTab?.();
 }
 async _v264Blacklist(recipe){
  const identity=recipeBlacklistIdentities(recipe)[0];
  if(!identity||this._v264BlacklistBusy?.has(identity))return;
  this._v264BlacklistBusy??=new Set();this._v264BlacklistBusy.add(identity);
  try{
   const result=await this._api('cook4me/recipe_blacklist_add',{
    entry_id:this._entryId,
    recipe:this._v264CompactRecipe(recipe),
   });
   this._v264AdoptProfile(result);
   this._v264AfterChange(this._v264Text('blacklisted'));
  }catch(error){
   this._message?.(`${this._t?.('error')||'Error'}: ${error?.message||error}`);
  }finally{
   this._v264BlacklistBusy.delete(identity);
  }
 }
 async _v264Undo(identity){
  identity=textValue(identity);
  if(!identity||this._v264UndoBusy?.has(identity))return;
  this._v264UndoBusy??=new Set();this._v264UndoBusy.add(identity);
  try{
   const result=await this._api('cook4me/recipe_blacklist_remove',{
    entry_id:this._entryId,
    identity,
   });
   this._v264AdoptProfile(result);
   this._message?.(this._v264Text('restored'));
   this._renderTab?.();
  }catch(error){
   this._message?.(`${this._t?.('error')||'Error'}: ${error?.message||error}`);
  }finally{
   this._v264UndoBusy.delete(identity);
  }
 }
 _v264BlacklistButton(recipe){
  const button=document.createElement('button');
  button.type='button';
  button.className='btn secondary rx-v66-icon v264-blacklist-button';
  button.dataset.v264Blacklist='';
  button.title=this._v264Text('blacklist');
  button.setAttribute('aria-label',button.title);
  const icon=document.createElement('ha-icon');
  icon.setAttribute('icon','mdi:block-helper');
  icon.setAttribute('aria-hidden','true');
  button.append(icon);
  return button;
 }
 _recipeCard(recipe,custom=false){
  if(this._v264IsBlacklisted(recipe))return '';
  const html=super._recipeCard(recipe,custom);if(!html)return html;
  const node=this._v67Dom?.(html)||(()=>{const wrapper=document.createElement('div');wrapper.innerHTML=html;return wrapper;})();
  const card=node.firstElementChild,title=card?.querySelector?.('.rx-v66-title');
  if(title&&!title.querySelector('[data-v264-blacklist]')){
   const button=this._v264BlacklistButton(recipe);
   const expand=title.querySelector('[data-v66-action="expand"]');
   title.insertBefore(button,expand||null);
  }
  return node.innerHTML;
 }
 _v66BindRecipe(container,recipe,...args){
  const result=super._v66BindRecipe(container,recipe,...args);
  container?.querySelectorAll?.('[data-v264-blacklist]').forEach(button=>{
   if(button._v264Bound)return;button._v264Bound=true;
   button.addEventListener('click',event=>{
    event.preventDefault();event.stopPropagation();void this._v264Blacklist(recipe);
   });
  });
  return result;
 }
 _renderRecipeDialog(){
  if(this._opened&&this._v264IsBlacklisted(this._opened)){
   this._v63CloseRecipe?.();return;
  }
  const result=super._renderRecipeDialog();
  const overlay=this._v63RecipeDialog,recipe=this._opened;
  const header=overlay?.querySelector?.('.rx-v66-fullscreen header');
  if(header&&recipe&&!header.querySelector('[data-v264-blacklist]')){
   const button=this._v264BlacklistButton(recipe);
   const close=header.querySelector('[data-modal-close]');
   header.insertBefore(button,close||null);
   button.addEventListener('click',event=>{
    event.preventDefault();event.stopPropagation();void this._v264Blacklist(recipe);
   });
  }
  return result;
 }
 _v264RenderBlacklistSection(container){
  const form=container?.querySelector?.('[data-v83-profiles]');if(!form)return;
  form.querySelector('[data-v264-blacklist-section]')?.remove();
  const section=document.createElement('section');
  section.className='card v264-blacklist-card';
  section.dataset.v264BlacklistSection='';
  const heading=document.createElement('h3');
  const icon=document.createElement('ha-icon');icon.setAttribute('icon','mdi:block-helper');
  const title=document.createElement('span');title.textContent=this._v264Text('blacklistTitle');
  heading.append(icon,title);
  const help=document.createElement('p');help.className='muted';help.textContent=this._v264Text('blacklistHelp');
  section.append(heading,help);
  const rows=this._v264Rows();
  if(!rows.length){
   const empty=document.createElement('p');empty.className='muted';empty.textContent=this._v264Text('empty');section.append(empty);
  }else{
   const list=document.createElement('div');list.className='v264-blacklist-list';
   for(const row of rows){
    if(!row||typeof row!=='object')continue;
    const item=document.createElement('div');item.className='v264-blacklist-row';
    const copy=document.createElement('div');copy.className='v264-blacklist-copy';
    const name=document.createElement('strong');name.textContent=textValue(row.title)||textValue(row.identity);
    copy.append(name);
    const meta=[row.language,row.source].map(textValue).filter(Boolean);
    if(meta.length){
     const small=document.createElement('small');small.className='muted';small.textContent=meta.join(' · ');copy.append(small);
    }
    const undo=document.createElement('button');undo.type='button';undo.className='btn secondary';undo.dataset.v264Undo=textValue(row.identity);
    const undoIcon=document.createElement('ha-icon');undoIcon.setAttribute('icon','mdi:undo');
    const undoText=document.createElement('span');undoText.textContent=this._v264Text('undo');
    undo.append(undoIcon,undoText);
    undo.addEventListener('click',()=>void this._v264Undo(row.identity));
    item.append(copy,undo);list.append(item);
   }
   section.append(list);
  }
  const preferences=form.querySelector('#preferences')?.closest?.('.field');
  const save=form.querySelector('[data-v83-save]');
  (preferences||save)?.before(section);
  if(!preferences&&!save)form.append(section);
  this._v264Styles();
 }
 _v83RenderProfiles(container,state){
  const result=super._v83RenderProfiles(container,state);
  this._v264RenderBlacklistSection(container);
  return result;
 }
 _renderTab(){
  const result=super._renderTab();
  this._v264Styles();
  return result;
 }
 _v264Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v264BlacklistStyles'))return;
  const style=document.createElement('style');style.id='v264BlacklistStyles';style.textContent=`
   .v264-blacklist-button{color:var(--error-color,var(--primary-text-color))}
   .v264-blacklist-card{margin:16px 0;padding:16px}
   .v264-blacklist-card>h3{display:flex;align-items:center;gap:10px;margin:0 0 8px}
   .v264-blacklist-list{display:flex;flex-direction:column;gap:8px;margin-top:12px}
   .v264-blacklist-row{display:flex;align-items:center;gap:12px;padding:10px 0;border-top:1px solid var(--divider-color)}
   .v264-blacklist-copy{display:flex;flex-direction:column;gap:3px;min-width:0;flex:1}
   .v264-blacklist-copy strong,.v264-blacklist-copy small{overflow-wrap:anywhere}
   .v264-blacklist-row>.btn{display:inline-flex;align-items:center;gap:6px;flex:0 0 auto}
   @media(max-width:560px){.v264-blacklist-row{align-items:stretch;flex-direction:column}.v264-blacklist-row>.btn{align-self:flex-start}}
  `;this.shadowRoot.append(style);
 }
};
