import './cook4me-panel-v116.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v116');
const WORDS={
 en:{
  tab:'Smart scale',title:'Smart scale',help:'Use a Home Assistant weight sensor for recipes, scanned products, stock, portions and leftovers.',
  sensor:'Weight sensor',status:'Scale status',tare:'Tare scale',clear:'Clear tare',
  containers:'Containers',containersHelp:'Save the empty weight of bowls, jars or other containers once. When you use one, Cook4me subtracts that saved tare from the live scale weight automatically.',
  noContainers:'No saved containers yet.',active:'Active',use:'Use',edit:'Edit',delete:'Delete',
  addContainer:'Add container',editContainer:'Edit container',containerName:'Container name',emptyWeight:'Empty container weight',readScale:'Read current scale weight',
  save:'Save container',cancel:'Cancel editing',nameRequired:'Enter a container name.',weightRequired:'Enter the empty container weight or place the empty container on the scale and press “Read current scale weight”.',
  saved:'Container saved.',deleted:'Container deleted.',using:'Container tare applied.'
 },
 de:{
  tab:'Smart-Waage',title:'Smart-Waage',help:'Home-Assistant-Gewichtssensor für Rezepte, gescannte Produkte, Vorrat, Portionen und Reste.',
  sensor:'Gewichtssensor',status:'Waagenstatus',tare:'Waage tarieren',clear:'Tara löschen',
  containers:'Behälter',containersHelp:'Speichere das Leergewicht von Schüsseln, Gläsern oder anderen Behältern einmal. Bei „Verwenden“ zieht Cook4me diese Tara automatisch vom Live-Gewicht ab.',
  noContainers:'Noch keine Behälter gespeichert.',active:'Aktiv',use:'Verwenden',edit:'Bearbeiten',delete:'Löschen',
  addContainer:'Behälter hinzufügen',editContainer:'Behälter bearbeiten',containerName:'Behältername',emptyWeight:'Leergewicht des Behälters',readScale:'Aktuelles Waagengewicht übernehmen',
  save:'Behälter speichern',cancel:'Bearbeitung abbrechen',nameRequired:'Gib einen Behälternamen ein.',weightRequired:'Gib das Leergewicht ein oder stelle den leeren Behälter auf die Waage und wähle „Aktuelles Waagengewicht übernehmen“.',
  saved:'Behälter gespeichert.',deleted:'Behälter gelöscht.',using:'Behälter-Tara angewendet.'
 },
 el:{
  tab:'Έξυπνη ζυγαριά',title:'Έξυπνη ζυγαριά',help:'Χρησιμοποίησε αισθητήρα βάρους του Home Assistant για συνταγές, σαρωμένα προϊόντα, απόθεμα, μερίδες και περισσεύματα.',
  sensor:'Αισθητήρας βάρους',status:'Κατάσταση ζυγαριάς',tare:'Απόβαρο ζυγαριάς',clear:'Καθαρισμός απόβαρου',
  containers:'Δοχεία',containersHelp:'Αποθήκευσε μία φορά το βάρος του άδειου μπολ, βάζου ή άλλου δοχείου. Όταν πατήσεις «Χρήση», το Cook4me αφαιρεί αυτόματα το αποθηκευμένο απόβαρο από το ζωντανό βάρος.',
  noContainers:'Δεν υπάρχουν ακόμη αποθηκευμένα δοχεία.',active:'Ενεργό',use:'Χρήση',edit:'Επεξεργασία',delete:'Διαγραφή',
  addContainer:'Προσθήκη δοχείου',editContainer:'Επεξεργασία δοχείου',containerName:'Όνομα δοχείου',emptyWeight:'Βάρος άδειου δοχείου',readScale:'Χρήση τωρινού βάρους ζυγαριάς',
  save:'Αποθήκευση δοχείου',cancel:'Ακύρωση επεξεργασίας',nameRequired:'Δώσε όνομα στο δοχείο.',weightRequired:'Δώσε το βάρος του άδειου δοχείου ή βάλε το άδειο δοχείο στη ζυγαριά και πάτησε «Χρήση τωρινού βάρους ζυγαριάς».',
  saved:'Το δοχείο αποθηκεύτηκε.',deleted:'Το δοχείο διαγράφηκε.',using:'Εφαρμόστηκε το απόβαρο του δοχείου.'
 }
};
class Cook4MeRecipeHubPanelV117 extends BasePanel{
 constructor(){super();this._v117EditingContainerId='';this._v117ActiveContainerId='';}
 _v117Text(key){return (WORDS[this._uiIngredientLanguage?.()||this._langCode?.()]||WORDS.en)[key]||key;}
 _v117EnsureScalePane(content){
  if(!content)return null;
  if(content.matches?.('[data-v78-section="scale"]'))return content;
  const layout=content.querySelector?.('[data-v78-kitchen]');if(!layout)return null;
  let section=layout.querySelector('[data-v78-section="scale"]');
  if(!section){
   section=document.createElement('div');section.dataset.v78Section='scale';
   const integration=layout.querySelector('[data-v78-section="integration"]');
   if(integration)integration.before(section);else layout.append(section);
  }
  const nav=layout.querySelector('.v78-nav');
  let button=nav?.querySelector('[data-v78-pane="scale"]');
  if(nav&&!button){
   button=document.createElement('button');button.type='button';button.dataset.v78Pane='scale';button.textContent=this._v117Text('tab');
   const places=nav.querySelector('[data-v78-pane="places"]');if(places)places.after(button);else nav.append(button);
   button.onclick=()=>{
    this._v78Pane='scale';
    layout.querySelectorAll('[data-v78-section]').forEach(node=>node.hidden=node.dataset.v78Section!=='scale');
    layout.querySelectorAll('[data-v78-pane]').forEach(node=>node.setAttribute('aria-pressed',String(node.dataset.v78Pane==='scale')));
    this._v116Card(section);
    void this._v116Load(null,true);
   };
  }
  const active=this._v78Pane==='scale';
  section.hidden=!active;
  if(button)button.setAttribute('aria-pressed',String(active));
  return section;
 }
 _renderProfile(content){super._renderProfile(content);const section=this._v117EnsureScalePane(content);if(section&&this._v78Pane==='scale')this._v116Card(section);}
 async _v116Load(recipe=null,force=false){
  if(!this._entryId)return;
  const key=recipe?String(recipe.groupingFunctionalId||recipe.recipeFunctionalId||recipe.variantFunctionalId||recipe.id||recipe.title||''):'';
  if(!force&&this._v116Scale&&this._v116ScaleEntry===this._entryId&&this._v116RecipeKey===key)return;
  try{
   this._v116Scale=await this._api('cook4me/v37/scale_state',{entry_id:this._entryId,...(recipe?{recipe}:{})});
   this._v116ScaleEntry=this._entryId;this._v116RecipeKey=key;
   if(recipe)this._v116Session=this._v116Scale?.session||null;
   const content=this.shadowRoot?.getElementById('content');
   if(content&&this._tab==='profile'){
    const section=this._v117EnsureScalePane(content);if(section)this._v116Card(section);
   }
   const dialog=this._v63RecipeDialog,select=dialog?.querySelector?.('#v116RecipeContainer');
   if(select)select.innerHTML=this._v116Containers();
   this._v116SessionText(dialog||content);this._v116Live();
  }catch(_error){}
 }
 async _v116Tare(){
  this._v117ActiveContainerId='';this._v116SoftwareTare=0;
  await super._v116Tare();
  const content=this.shadowRoot?.getElementById('content'),section=this._v117EnsureScalePane(content);
  if(section&&this._v78Pane==='scale')this._v116Card(section);
 }
 _v117ContainersHtml(){
  const rows=this._v116Scale?.containers||[];
  if(!rows.length)return `<p class="muted v117-empty">${this._escape(this._v117Text('noContainers'))}</p>`;
  return `<div class="v117-containers">${rows.map(row=>`<div class="v117-container" data-v117-container="${this._escape(row.id)}"><div class="v117-container-main"><strong>${this._escape(row.name)}</strong><span>${this._v116Num(row.tareGrams,3)} g</span>${row.id===this._v117ActiveContainerId?`<span class="chip">${this._escape(this._v117Text('active'))}</span>`:''}</div><div class="v117-container-actions"><button type="button" class="btn secondary" data-use>⚖ ${this._escape(this._v117Text('use'))}</button><button type="button" class="btn secondary" data-edit>${this._escape(this._v117Text('edit'))}</button><button type="button" class="btn secondary" data-delete>${this._escape(this._v117Text('delete'))}</button></div></div>`).join('')}</div>`;
 }
 _v117EditorHtml(){
  const row=(this._v116Scale?.containers||[]).find(item=>String(item.id)===String(this._v117EditingContainerId));
  const edit=!!row;
  return `<section class="v117-container-editor"><h3>${this._escape(this._v117Text(edit?'editContainer':'addContainer'))}</h3><div class="v78-fields"><label class="field">${this._escape(this._v117Text('containerName'))}<input id="v117ContainerName" maxlength="120" value="${this._escape(row?.name||'')}"></label><label class="field">${this._escape(this._v117Text('emptyWeight'))} (g)<input id="v117ContainerWeight" type="number" min="0" step="0.1" inputmode="decimal" value="${row?this._v116Num(row.tareGrams,3):''}"></label></div><div class="v78-actions"><button type="button" class="btn secondary" id="v117ReadWeight">⚖ ${this._escape(this._v117Text('readScale'))}</button><button type="button" class="btn" id="v117SaveContainer">${this._escape(this._v117Text('save'))}</button>${edit?`<button type="button" class="btn secondary" id="v117CancelContainer">${this._escape(this._v117Text('cancel'))}</button>`:''}</div><p class="muted" id="v117ContainerStatus" role="status"></p></section>`;
 }
 _v116Card(content){
  const section=this._v117EnsureScalePane(content)||content;if(!section)return;
  let card=section.querySelector('#v116Scale');
  if(!card){card=document.createElement('section');card.id='v116Scale';card.className='card v116-scale-card v117-scale-card';section.append(card);}
  const leftovers=(this._v116Scale?.leftovers||[]).map(row=>`<div data-v116-leftover="${this._escape(row.id)}" class="v116-leftover"><strong>${this._escape(row.title||this._v116Text('leftovers'))}</strong> · ${this._v116Num(row.servings,2)} ${this._escape(this._t('servings'))}${Number.isFinite(Number(row.weightGrams))?` · ${this._v116Num(row.weightGrams)} g`:''}<div class="toolbar"><button class="btn secondary" data-v116-left-weigh>⚖ ${this._escape(this._v116Text('weighLeft'))}</button>${Number.isFinite(Number(row.weightGrams))?`<button class="btn secondary" data-v116-left-eat>⚖ ${this._escape(this._v116Text('eatLeft'))}</button>`:''}</div></div>`).join('');
  card.innerHTML=`<h2>⚖ ${this._escape(this._v117Text('title'))}</h2><p class="muted">${this._escape(this._v117Text('help'))}</p><div class="v117-scale-main"><label class="field">${this._escape(this._v117Text('sensor'))}<select id="v116Entity">${this._v116Options()}</select></label><div class="v117-status"><small>${this._escape(this._v117Text('status'))}</small><strong data-v116-live>${this._escape(this._v116Text('off'))}</strong><div class="muted" data-v116-meta></div></div></div><div class="v78-actions v117-tare-actions"><button class="btn secondary" id="v116Tare">⚖ ${this._escape(this._v117Text('tare'))}</button><button class="btn secondary" id="v116Clear">${this._escape(this._v117Text('clear'))}</button></div><section class="v117-container-section"><h3>${this._escape(this._v117Text('containers'))}</h3><p class="muted">${this._escape(this._v117Text('containersHelp'))}</p>${this._v117ContainersHtml()}${this._v117EditorHtml()}</section>${leftovers}`;
  card.querySelector('#v116Entity')?.addEventListener('change',async event=>{try{this._v116Scale=await this._api('cook4me/v37/scale_select',{entry_id:this._entryId,entity_id:event.target.value});this._v116ScaleEntry=this._entryId;this._v116SoftwareTare=0;this._v117ActiveContainerId='';this._v116Card(section);}catch(error){this._message(String(error.message||error),true);}});
  card.querySelector('#v116Tare')?.addEventListener('click',()=>void this._v116Tare());
  card.querySelector('#v116Clear')?.addEventListener('click',()=>{this._v116SoftwareTare=0;this._v117ActiveContainerId='';this._v116Card(section);this._v116Live();});
  card.querySelectorAll('[data-v117-container]').forEach(node=>{
   const id=node.dataset.v117Container,row=(this._v116Scale?.containers||[]).find(item=>String(item.id)===String(id));if(!row)return;
   node.querySelector('[data-use]').onclick=()=>{this._v116SoftwareTare=Number(row.tareGrams||0);this._v117ActiveContainerId=id;this._v116Card(section);this._v116Live();this._message(this._v117Text('using'));};
   node.querySelector('[data-edit]').onclick=()=>{this._v117EditingContainerId=id;this._v116Card(section);card.querySelector('#v117ContainerName')?.focus();};
   node.querySelector('[data-delete]').onclick=async()=>{try{this._v116Scale=await this._api('cook4me/v37/container_delete',{entry_id:this._entryId,container_id:id});if(this._v117ActiveContainerId===id){this._v117ActiveContainerId='';this._v116SoftwareTare=0;}if(this._v117EditingContainerId===id)this._v117EditingContainerId='';this._v116Card(section);this._message(this._v117Text('deleted'));}catch(error){this._message(String(error.message||error),true);}};
  });
  const name=card.querySelector('#v117ContainerName'),weight=card.querySelector('#v117ContainerWeight'),status=card.querySelector('#v117ContainerStatus');
  card.querySelector('#v117ReadWeight').onclick=()=>{const reading=this._v116Reading();if(!reading){status.textContent=this._v116Text('off');return;}if(this._v116Stable()===false){status.textContent=this._v116Text('waitStable');return;}weight.value=this._v116Num(reading.gross,3);status.textContent=`${this._v116Num(reading.gross,3)} g`;};
  card.querySelector('#v117SaveContainer').onclick=async()=>{
   const label=String(name.value||'').trim(),grams=Number(String(weight.value||'').replace(',','.'));
   if(!label){status.textContent=this._v117Text('nameRequired');name.focus();return;}
   if(!Number.isFinite(grams)||grams<0){status.textContent=this._v117Text('weightRequired');weight.focus();return;}
   try{
    const editing=this._v117EditingContainerId;
    const result=await this._api('cook4me/v37/container_save',{entry_id:this._entryId,name:label,tare_grams:grams,...(editing?{container_id:editing}:{})});
    this._v116Scale=result;
    if(editing&&this._v117ActiveContainerId===editing)this._v116SoftwareTare=Number(result.container?.tareGrams||0);
    this._v117EditingContainerId='';
    this._v116Card(section);this._v116Live();this._message(this._v117Text('saved'));
   }catch(error){status.textContent=String(error.message||error);}
  };
  card.querySelector('#v117CancelContainer')?.addEventListener('click',()=>{this._v117EditingContainerId='';this._v116Card(section);});
  card.querySelectorAll('[data-v116-leftover]').forEach(row=>{const id=row.dataset.v116Leftover;row.querySelector('[data-v116-left-weigh]')?.addEventListener('click',()=>void this._v116Leftover(id,false,section));row.querySelector('[data-v116-left-eat]')?.addEventListener('click',()=>void this._v116Leftover(id,true,section));});
  this._v116Live();this._v117Styles();
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-build','2026.9.18.3');return result;}
 _v117Styles(){
  if(this.shadowRoot?.querySelector('#v117Styles'))return;const style=document.createElement('style');style.id='v117Styles';style.textContent=`
   .v117-scale-card{margin-top:18px!important}.v117-scale-main{display:grid;grid-template-columns:minmax(260px,1fr) minmax(240px,1fr);gap:16px;align-items:end}.v117-status{display:flex;flex-direction:column;gap:4px;padding:10px 0}.v117-status small{color:var(--secondary-text-color)}
   .v117-tare-actions{margin:14px 0 4px}.v117-container-section{margin-top:24px;padding-top:20px;border-top:1px solid var(--divider-color)}.v117-container-section>h3,.v117-container-editor>h3{margin:0 0 8px}.v117-containers{display:grid;gap:10px;margin:16px 0}.v117-container{display:flex;align-items:center;gap:12px;padding:14px;border:1px solid var(--divider-color);border-radius:12px}.v117-container-main{display:flex;align-items:center;gap:10px;flex:1;min-width:0;flex-wrap:wrap}.v117-container-main strong{overflow-wrap:anywhere}.v117-container-main>span:not(.chip){color:var(--secondary-text-color)}.v117-container-actions{display:flex;gap:8px;flex-wrap:wrap}.v117-container-editor{margin-top:18px;padding:18px;border:1px solid var(--divider-color);border-radius:14px;background:var(--secondary-background-color)}.v117-container-editor .v78-actions{margin-top:14px}.v117-empty{margin:16px 0}
   @media(max-width:700px){.v117-scale-main{grid-template-columns:1fr}.v117-container{align-items:flex-start;flex-direction:column}.v117-container-actions{width:100%}.v117-container-actions .btn{flex:1}.v117-container-editor .v78-fields{grid-template-columns:1fr}}
  `;this.shadowRoot?.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v117',Cook4MeRecipeHubPanelV117);
