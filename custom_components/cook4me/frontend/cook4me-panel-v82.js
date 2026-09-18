import "./cook4me-panel-v81.js";
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v81');
const BUILD='2026.9.16.7';
const NAV=[['today','weather-sunny'],['week','calendar-week'],['official','magnify'],['book','book-open-page-variant-outline'],['mine','chef-hat'],['shopping','cart-outline'],['profile','home-heart']];
const TEXT={
 en:{book:'Cooking book',official:'Search recipe',mine:'Recipe creator',profile:'My kitchen & preferences',manual:'Manual recipe creator',ai:'AI recipe creator',saved:'Saved recipes',refresh:'Update recipe prices',refreshing:'Updating recipe prices…',noRecipes:'No recipes shown',updated:'Recipe prices updated',partialUpdate:'Refresh finished; some prices are still missing.',refreshHelp:'Prices are checked when you open a recipe. Observations are reused for 24 hours, no matches for 1 hour, and source errors for 1 minute. Update recipe prices checks the recipes currently shown immediately, even when automatic lookup is off. There is no scheduled background refresh.',category_unmapped:'No automatic price category for this ingredient. Link a scanned product or enter a purchase price.',no_observation:'No usable price found for your country and currency in the latest observations.',basis_missing:'The price and recipe use incompatible units or lack a package amount.',recipe_amount_unknown:'Recipe quantity or unit is missing.',lookup_limit:'The lookup limit was reached. Link a product or enter its price.',source_unavailable:'Price lookup could not finish. Saved prices are still used.',checked:'Last calculation',manualHelp:'Write your own recipe with catalog ingredients.',aiHelp:'Create a recipe using your available AI task.'},
 de:{book:'Kochbuch',official:'Rezept suchen',mine:'Rezeptersteller',profile:'Meine Küche & Vorlieben',manual:'Manueller Rezeptersteller',ai:'KI-Rezeptersteller',saved:'Gespeicherte Rezepte',refresh:'Rezeptpreise aktualisieren',refreshing:'Rezeptpreise werden aktualisiert…',noRecipes:'Keine Rezepte angezeigt',updated:'Rezeptpreise aktualisiert',partialUpdate:'Aktualisierung beendet; einige Preise fehlen weiterhin.',refreshHelp:'Preise werden beim Öffnen eines Rezepts geprüft. Beobachtungen gelten 24 Stunden, fehlende Treffer 1 Stunde und Quellenfehler 1 Minute. Rezeptpreise aktualisieren prüft die angezeigten Rezepte sofort, auch bei ausgeschalteter automatischer Suche. Keine geplante Hintergrundaktualisierung.',category_unmapped:'Keine automatische Preiskategorie. Ein gescanntes Produkt zuordnen oder den Kaufpreis eingeben.',no_observation:'Kein nutzbarer Preis für Land und Währung in den neuesten Beobachtungen.',basis_missing:'Preis und Rezept haben nicht umrechenbare Einheiten oder keine Packungsmenge.',recipe_amount_unknown:'Rezeptmenge oder Einheit fehlt.',lookup_limit:'Das Abfragelimit wurde erreicht. Produkt zuordnen oder Preis eingeben.',source_unavailable:'Preissuche nicht abgeschlossen. Gespeicherte Preise werden weiter verwendet.',checked:'Letzte Berechnung',manualHelp:'Eigenes Rezept mit Katalogzutaten schreiben.',aiHelp:'Mit der verfügbaren KI-Aufgabe ein Rezept erstellen.'},
 el:{book:'Βιβλίο μαγειρικής',official:'Αναζήτηση συνταγής',mine:'Δημιουργός συνταγών',profile:'Η κουζίνα μου & προτιμήσεις',manual:'Χειροκίνητη δημιουργία συνταγής',ai:'Δημιουργία συνταγής με AI',saved:'Αποθηκευμένες συνταγές',refresh:'Ενημέρωση τιμών συνταγών',refreshing:'Ενημέρωση τιμών συνταγών…',noRecipes:'Δεν εμφανίζονται συνταγές',updated:'Οι τιμές συνταγών ενημερώθηκαν',partialUpdate:'Η ενημέρωση ολοκληρώθηκε· ορισμένες τιμές εξακολουθούν να λείπουν.',refreshHelp:'Οι τιμές ελέγχονται όταν ανοίγεις συνταγή. Οι καταγραφές χρησιμοποιούνται για 24 ώρες, η έλλειψη αποτελέσματος για 1 ώρα και τα σφάλματα πηγής για 1 λεπτό. Η ενημέρωση τιμών ελέγχει αμέσως τις εμφανιζόμενες συνταγές, ακόμη και με κλειστή την αυτόματη αναζήτηση. Δεν υπάρχει προγραμματισμένη ενημέρωση στο παρασκήνιο.',category_unmapped:'Δεν υπάρχει αυτόματη κατηγορία τιμής. Σύνδεσε σαρωμένο προϊόν ή συμπλήρωσε τιμή αγοράς.',no_observation:'Δεν βρέθηκε χρήσιμη τιμή για τη χώρα και το νόμισμα στις πρόσφατες καταγραφές.',basis_missing:'Η τιμή και η συνταγή έχουν ασύμβατες μονάδες ή λείπει η ποσότητα συσκευασίας.',recipe_amount_unknown:'Λείπει ποσότητα ή μονάδα από τη συνταγή.',lookup_limit:'Συμπληρώθηκε το όριο αναζητήσεων. Σύνδεσε προϊόν ή συμπλήρωσε τιμή.',source_unavailable:'Η αναζήτηση τιμής δεν ολοκληρώθηκε. Χρησιμοποιούνται οι αποθηκευμένες τιμές.',checked:'Τελευταίος υπολογισμός',manualHelp:'Γράψε συνταγή με υλικά από τον κατάλογο.',aiHelp:'Δημιούργησε συνταγή με τη διαθέσιμη εργασία AI.'}
};
class Cook4MeRecipeHubPanelV82 extends BasePanel{
 _v82Text(key){return TEXT[this._langCode()]?.[key]||TEXT.en[key]||this._t(key);}
 _t(key){return ['official','mine','profile','book'].includes(key)?(TEXT[this._langCode()]?.[key]||TEXT.en[key]):super._t(key);}
 _v78Text(key){return key==='kitchen'?this._v82Text('profile'):super._v78Text(key);}
 _renderTabs(){
  if(this._tab==='ai'){this._tab='mine';this._v82Creators().ai=true;}
  super._renderTabs();const tabs=this.shadowRoot?.querySelector('#tabs');if(!tabs)return;
  tabs.querySelector('[data-tab=ai]')?.remove();
  for(const [key,icon] of NAV){const button=tabs.querySelector(`[data-tab=${key}]`);if(!button)continue;const label=this._t(key);button.innerHTML=`<ha-icon icon="mdi:${icon}" aria-hidden="true"></ha-icon>`;button.title=label;button.setAttribute('aria-label',label);button.setAttribute('aria-pressed',String(this._tab===key));tabs.append(button);}
  tabs.setAttribute('aria-label','Cook4Me');this._v82Styles();this._v82RefreshButton();
 }
 _modernizeTabs(){
  const tabs=this.shadowRoot?.querySelector('#tabs');if(!tabs)return;
  tabs.querySelector('[data-tab=ai]')?.remove();
  for(const [key,icon] of NAV){const button=tabs.querySelector(`[data-tab=${key}]`);if(!button)continue;const label=this._t(key);if(button.querySelector('ha-icon')?.getAttribute('icon')!==`mdi:${icon}`||button.querySelector('span'))button.innerHTML=`<ha-icon icon="mdi:${icon}" aria-hidden="true"></ha-icon>`;button.title=label;button.setAttribute('aria-label',label);button.setAttribute('aria-pressed',String(this._tab===key));tabs.append(button);}
 }
 _selectV52Tab(tab){
  if(tab==='ai'){this._v82Creators().ai=true;tab='mine';}
  if(this._v82Refresh&&this._tab!==tab){this._processEnd(this._v82Refresh.job);this._v82Refresh=null;}
  return super._selectV52Tab(tab);
 }
 _renderTab(){if(this._tab==='ai'){this._tab='mine';this._v82Creators().ai=true;}const result=super._renderTab();this.setAttribute('data-cook4me-build',BUILD);this._v82Styles();this._v82RefreshButton();return result;}
 _renderShell(){super._renderShell();this._v82Styles();this._v82RefreshButton();}
 _updateHeader(){super._updateHeader();this._v82RefreshButton();}
 _v82Creators(){
  const context=this._prefKey();
  if(this._v82CreatorState?.context!==context){this._v82CreatorState={context,manual:false,ai:false};this._manualMeta={title:'',servings:'',steps:'',notes:''};this._manualDraftIngredients=[];this._manualIngredientFilter='';this._aiSettings=null;this._v82AiRecipe=null;this._aiBusy=false;this._v82ManualSaving=false;this._v82AiRequest=null;}
  return this._v82CreatorState;
 }
 _renderMineV28(c){
  const state=this._v82Creators();super._renderMineV28(c);
  const card=c.querySelector('#manualTitle')?.closest('section.card');if(!card)return;
  const header=document.createElement('h1');header.textContent=this._v82Text('mine');c.prepend(header);
  const wrap=(key,icon,help)=>{const details=document.createElement('details');details.className='v82-creator';details.dataset.v82Creator=key;details.open=state[key];details.innerHTML=`<summary><ha-icon icon="mdi:${icon}" aria-hidden="true"></ha-icon><span>${this._escape(this._v82Text(key))}<small>${this._escape(this._v82Text(help))}</small></span><ha-icon class="v82-chevron" icon="mdi:chevron-down" aria-hidden="true"></ha-icon></summary>`;details.addEventListener('toggle',()=>{if(this._prefKey()===state.context)state[key]=details.open;});return details;};
  const manual=wrap('manual','pencil-outline','manualHelp');card.before(manual);manual.append(card);card.querySelector('h2')?.remove();
  // Amounts must survive adding/removing another ingredient and async re-renders.
  card.querySelectorAll('[data-manual-qty],[data-manual-unit]').forEach(input=>input.addEventListener('input',()=>{const qty=input.hasAttribute('data-manual-qty'),index=Number(qty?input.dataset.manualQty:input.dataset.manualUnit),item=this._manualDraftIngredients[index];if(item)item[qty?'quantity':'unit']=input.value;}));
  const save=card.querySelector('#manualSave');if(save)save.disabled=Boolean(this._v82ManualSaving);
  const ai=wrap('ai','creation','aiHelp'),body=document.createElement('div');body.dataset.v82AiBody='';ai.append(body);manual.after(ai);this._renderAIV49(body);
  const saved=c.querySelector('#mineGrid')?.closest('section.card');if(saved?.querySelector('h2'))saved.querySelector('h2').textContent=this._v82Text('saved');
  ai.addEventListener('toggle',()=>{if(ai.open&&!state.requested){state.requested=true;const context=this._prefKey();void this._requestSection('ai',{missingOnly:true}).then(()=>{if(context===this._prefKey()&&body.isConnected)this._renderAIV49(body);});}});
 }
 _renderAIV49(c){
  const refs=this._v66Refs,opened=this._opened;this._opened=this._v82AiRecipe||null;
  try{super._renderAIV49(c);}finally{this._opened=opened;this._v66Refs=new Map([...(refs||[]),...(this._v66Refs||[])]);}
  c.querySelector('.detail-head h2')?.closest('.detail-head')?.remove();
  const capture=()=>{if(c.isConnected)this._aiSettings=this._collectAiSettings(c);};
  c.querySelectorAll('input,select,textarea').forEach(input=>{input.addEventListener('input',capture);input.addEventListener('change',capture);});
 }
 async _saveManualV28(c){
  if(this._v82ManualSaving)return;
  if(!this._manualDraftIngredients.length){this._message(this._t('ingredientRequired'),true);return;}
  const steps=this._splitList(c.querySelector('#manualSteps')?.value||'');if(!steps.length){this._message(this._t('stepsRequired'),true);return;}
  const context=this._prefKey(),recipe={title:String(c.querySelector('#manualTitle')?.value||'').trim(),servings:c.querySelector('#manualServings')?.value,ingredients:structuredClone(this._manualDraftIngredients),steps,notes:c.querySelector('#manualNotes')?.value||''};
  this._v82ManualSaving=true;c.querySelector('#manualSave').disabled=true;
  try{await this._api('cook4me/recipe_save',{entry_id:this._entryId,recipe,source:'manual'});if(context!==this._prefKey())return;this._manualDraftIngredients=[];this._manualMeta={title:'',servings:'',steps:'',notes:''};await this._loadOverview(true);}
  catch(error){if(context===this._prefKey())this._message(`${this._t('error')}: ${error.message||error}`,true);}
  finally{if(context===this._prefKey()){this._v82ManualSaving=false;if(this._tab==='mine')this._renderTab();}}
 }
 async _createAiRecipe(c){
  if(this._aiBusy)return;const settings=this._collectAiSettings(c),context=this._prefKey(),request={};this._v82AiRequest=request;this._saveAiSettings(settings);this._aiBusy=true;this._renderAIV49(c);
  const process=this._processStart(this._t('aiCreateTitle'),this._t('aiRunning'));
  try{
   const payload={entry_id:this._entryId,request:settings.request,language:this._langCode(),catalog_languages:settings.languages,diet:settings.diet,meal_types:settings.mealTypes,nutrition_goal:settings.nutritionGoal,calorie_tolerance:settings.calorieTolerance,only_home:settings.onlyHome,prefer_expiring:settings.preferExpiring,avoid_recent_days:settings.avoidRecentDays,ingredients:this._todaySelectedIngredientRows?.({ingredients:settings.ingredients})||[]};
   if(settings.calorieTarget!=='')payload.calorie_target=settings.calorieTarget;if(settings.maxMissing!=='')payload.max_missing=Number(settings.maxMissing);
   const result=await this._api('cook4me/v22/ai_create',payload);if(context!==this._prefKey()||this._v82AiRequest!==request)return;
   this._v82AiRecipe=result?.recipe||null;await this._loadOverview(true,false);
   if(context===this._prefKey())this._message(this._t('aiCreated'));
  }catch(error){if(context===this._prefKey())this._message(`${this._t('error')}: ${error.message||error}`,true);}
  finally{this._processEnd(process);if(context===this._prefKey()&&this._v82AiRequest===request){this._aiBusy=false;if(this._tab==='mine')this._renderTab();}}
 }
 _v66BindRecipe(container,recipe,...args){container._v82Recipe=recipe;super._v66BindRecipe(container,recipe,...args);if(container.matches('[data-v66-ref]')){const badge=document.createElement('div');badge.className='v82-card-cost';badge.dataset.v82CardCost='';(container.querySelector('.rx-v69-media')||container.querySelector('.rx-v66-title'))?.append(badge);this._v82PaintCard(recipe);}this._v82RefreshButton();}
 _v82ShownRecipes(){
  const scope=this._v63RecipeDialog?.isConnected?this._v63RecipeDialog:this.shadowRoot?.querySelector('#content');if(!scope)return [];
  const nodes=[scope,...scope.querySelectorAll('[data-v66-ref]')];
  return [...new Set(nodes.filter(node=>node._v82Recipe&&node.getClientRects().length&&!node.closest('details:not([open])')).map(node=>node._v82Recipe))];
 }
 _v82RefreshButton(){
  if(!this.shadowRoot)return;let button=this.shadowRoot.querySelector('#v82RefreshPrices');
  if(!button){const refresh=this.shadowRoot.querySelector('#refresh');if(!refresh)return;button=document.createElement('button');button.id='v82RefreshPrices';button.type='button';button.className='btn secondary v82-price-refresh';button.innerHTML='<ha-icon icon="mdi:cash-sync" aria-hidden="true"></ha-icon>';button.onclick=()=>void this._v82RefreshPrices();refresh.after(button);}
  const count=this._v82ShownRecipes().length,busy=Boolean(this._v82Refresh&&this._v82Refresh.context===this._prefKey());
  this.shadowRoot.querySelectorAll('#v82RefreshPrices,[data-v82-refresh-prices]').forEach(el=>{el.disabled=busy||!count;const label=this._v82Text(busy?'refreshing':count?'refresh':'noRecipes');el.title=label;el.setAttribute('aria-label',label);el.setAttribute('aria-busy',String(busy));});
 }
 _renderRecipeDialog(){super._renderRecipeDialog();const overlay=this._v63RecipeDialog;if(overlay&&!overlay._v82CloseHook){overlay._v82CloseHook=true;const close=this._v63CloseRecipe;this._v63CloseRecipe=()=>{close();this._v82RefreshButton();};overlay.addEventListener('click',event=>{if(event.target===overlay)queueMicrotask(()=>this._v82RefreshButton());});overlay.addEventListener('keydown',event=>{if(event.key==='Escape')queueMicrotask(()=>this._v82RefreshButton());});}const header=this._v63RecipeDialog?.querySelector('header');if(header&&!header.querySelector('[data-v82-refresh-prices]')){const button=document.createElement('button');button.className='btn secondary v82-price-refresh';button.dataset.v82RefreshPrices='';button.innerHTML='<ha-icon icon="mdi:cash-sync" aria-hidden="true"></ha-icon>';button.onclick=()=>void this._v82RefreshPrices();header.querySelector('[data-modal-close]')?.before(button);}this._v82RefreshButton();}
 _v82PaintCard(recipe){
  const state=this._v79CostState(recipe),cost=state.cost;
  this.shadowRoot.querySelectorAll('[data-v66-ref]').forEach(card=>{if(card._v82Recipe!==recipe)return;const badge=card.querySelector('[data-v82-card-cost]');if(badge)badge.textContent=state.loading?this._v82Text('refreshing'):cost?`${cost.complete?'≈ ':this._v79Text('partial')+' · '}${this._v79Money(cost.totalsByCurrency)}`:'';});
 }
 _v79PaintRecipe(recipe,state){super._v79PaintRecipe(recipe,state);this._v82PaintCard(recipe);}
 _v79CostHtml(recipe,state){
  const html=super._v79CostHtml(recipe,state),cost=state.cost;if(!cost)return html;
  const e=v=>this._escape(String(v??''));
  const node=this._v67Dom(html);
  node.querySelectorAll('.v79-evidence>div').forEach((row,index)=>{const item=cost.ingredients?.[index];if(item&&item.coverage<1){const reason=document.createElement('small');reason.className='v82-price-reasons';reason.textContent=this._v82Text(item.priceStatus||'no_observation');row.append(reason);}});
  return node.innerHTML+`${cost.checkedAt?`<p class="muted">${e(this._v82Text('checked'))}: ${e(new Date(cost.checkedAt).toLocaleString(this._langCode()))}</p>`:''}`;
 }
 _v79RenderSettings(c){super._v79RenderSettings(c);const help=document.createElement('p');help.className='muted';help.dataset.v82PriceHelp='';help.textContent=this._v82Text('refreshHelp');c.append(help);}
 async _v79LoadCost(recipe,force=false){
  if(force)return this._v82RefreshPrices([recipe]);
  if(!recipe?.ingredients?.length)return;const state=this._v79CostState(recipe);if(state.loading||state.started&&Date.now()-(state.checkedAt||0)<60000)return;
  const context=this._prefKey(),request={};state.request=request;state.loading=true;state.started=true;state.checkedAt=Date.now();state.error='';this._v79PaintRecipe(recipe,state);
  try{const cost=await this._api('cook4me/v34/recipe_cost',{entry_id:this._entryId,recipe:this._v79Payload(recipe)});if(context!==this._prefKey()||this._v79CostState(recipe)!==state||state.request!==request)return;state.cost=cost;recipe.cost=cost;}
  catch(error){if(context===this._prefKey()&&state.request===request)state.error=String(error.message||error);}
  finally{if(state.request===request){state.loading=false;if(context===this._prefKey())this._v79PaintRecipe(recipe,state);}}
 }
 async _v82RefreshPrices(recipes=this._v82ShownRecipes()){
  if(this._v82Refresh||!recipes.length)return;
  const context=this._prefKey(),entry=this._entryId,tab=this._tab,job=this._processStart(this._v82Text('refresh'),this._v82Text('refreshing'));
  const operation={context,tab,job};this._v82Refresh=operation;this._v82RefreshButton();
  const current=()=>this._v82Refresh===operation&&context===this._prefKey()&&tab===this._tab&&!job.cancelled;
  const groups=new Map();let partial=false;
  try{
   for(const recipe of recipes){
    if(!current())return;
    if(!recipe.ingredients?.length){await this._v66LoadRecipe(recipe,!this._isOfficialRecipe(recipe),this._v66State(recipe));if(!current())return;}
    const payload=this._v79Payload(recipe),key=JSON.stringify(payload),state=this._v79CostState(recipe);state.request=operation;state.loading=true;state.error='';state.started=true;this._v79PaintRecipe(recipe,state);
    if(!groups.has(key))groups.set(key,{payload,rows:[]});groups.get(key).rows.push({recipe,state});
   }
   const batches=[...groups.values()];
   for(let start=0;start<batches.length;start+=32){
    if(!current())return;const batch=batches.slice(start,start+32);
    this._processUpdate(job,`${this._v82Text('refreshing')} ${start} / ${batches.length}`,start,batches.length);
    const result=await this._api('cook4me/v34/recipe_cost_refresh',{entry_id:entry,recipes:batch.map(row=>row.payload)});
    if(!current())return;if(result.costs?.length!==batch.length)throw new Error(this._v79Text('failed'));
    batch.forEach((group,index)=>{const cost=result.costs[index];partial||=!cost.complete||cost.priceLookupIncomplete;for(const {recipe,state} of group.rows){if(this._v79CostState(recipe)!==state||state.request!==operation)continue;state.cost=cost;recipe.cost=cost;state.loading=false;state.checkedAt=Date.now();this._v79PaintRecipe(recipe,state);}});
   }
   if(current())this._message(this._v82Text(partial?'partialUpdate':'updated'));
  }catch(error){if(current()){for(const group of groups.values())for(const {recipe,state} of group.rows){if(state.request===operation){state.error=String(error.message||error);state.loading=false;this._v79PaintRecipe(recipe,state);}}this._v59FailProcess(job,String(error.message||error));}}
  finally{for(const group of groups.values())for(const {recipe,state} of group.rows){if(state.request===operation){state.loading=false;if(context===this._prefKey())this._v79PaintRecipe(recipe,state);}}this._processEnd(job);if(this._v82Refresh===operation)this._v82Refresh=null;this._v82RefreshButton();}
 }
 _resetUserScopedUiState(){super._resetUserScopedUiState();this._v82CreatorState=null;this._v82Creators();if(this._v82Refresh)this._processEnd(this._v82Refresh.job);this._v82Refresh=null;}
 _resetEntryScopedUiState(){super._resetEntryScopedUiState();this._v82CreatorState=null;this._v82Creators();if(this._v82Refresh)this._processEnd(this._v82Refresh.job);this._v82Refresh=null;}
 disconnectedCallback(){if(this._v82Refresh)this._processEnd(this._v82Refresh.job);this._v82Refresh=null;super.disconnectedCallback();}
 _v82Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v82Styles'))return;const style=document.createElement('style');style.id='v82Styles';style.textContent=`
   #tabs{display:flex!important;flex-wrap:nowrap!important;justify-content:flex-start;gap:6px!important;overflow-x:auto;padding:4px 0!important}#tabs .tab{display:inline-flex!important;align-items:center;justify-content:center;flex:0 0 48px!important;min-width:44px!important;width:48px!important;height:48px!important;padding:10px!important;border-radius:14px!important}#tabs .tab ha-icon{display:block!important;--mdc-icon-size:24px;opacity:1!important}#tabs .tab:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}
   .v82-price-refresh{display:inline-flex!important;align-items:center;justify-content:center;min-width:44px;width:44px!important;flex:0 0 44px;padding:9px!important}.v82-price-refresh[aria-busy=true] ha-icon{animation:v81-turn 2s linear infinite}.top>.toolbar{align-items:center}.v82-creator{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:18px;margin:14px 0;overflow:hidden}.v82-creator>summary{display:flex;align-items:center;gap:14px;cursor:pointer;list-style:none;padding:20px;font-weight:650;min-height:64px}.v82-creator>summary::-webkit-details-marker{display:none}.v82-creator>summary>span{flex:1;min-width:0}.v82-creator>summary small{display:block;font-size:13px;font-weight:400;color:var(--secondary-text-color);margin-top:5px;line-height:1.5}.v82-creator[open]>summary{border-bottom:1px solid var(--divider-color)}.v82-creator[open] .v82-chevron{transform:rotate(180deg)}.v82-creator>.card,.v82-creator>[data-v82-ai-body]>.card{border:0;border-radius:0;margin:0}.v82-creator input,.v82-creator select,.v82-creator textarea{max-width:100%;box-sizing:border-box}.v82-card-cost{position:absolute;top:10px;right:10px;z-index:2;max-width:calc(100% - 20px);padding:5px 9px;border-radius:9px;background:var(--card-background-color);box-shadow:0 1px 6px #0002;font-size:12px;line-height:1.35;color:var(--primary-text-color);overflow-wrap:anywhere}.v82-card-cost:empty{display:none}.rx-v69-media:has([data-v76-diet-badge]) .v82-card-cost{top:56px}.v82-price-reasons{font-size:13px;line-height:1.5;display:block;color:var(--secondary-text-color)}
   @media(max-width:480px){#tabs{gap:3px!important}#tabs .tab{flex-basis:44px!important;width:44px!important;padding:8px!important}.v82-creator>summary{padding:16px;gap:10px}.v82-creator .draft-row{display:flex;flex-wrap:wrap}.v82-creator .draft-row>div{flex:1 1 100%}.v82-creator .draft-row input{width:calc(50% - 36px);min-width:65px}.top>.toolbar #refresh{width:auto}.top>.toolbar #entrySelect{max-width:100%}}
   @media(prefers-reduced-motion:reduce){.v82-price-refresh ha-icon{animation:none!important}}
  `;this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v82',Cook4MeRecipeHubPanelV82);
