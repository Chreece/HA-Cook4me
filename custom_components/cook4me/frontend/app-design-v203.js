import {APP_THEME} from './app-theme-v203.js';

// Presentation only. Existing route owners, eligibility and handlers are retained.
export const DESIGN_TEXT={
 en:{navToday:'Today',navWeek:'Week',navOfficial:'Discover',navBook:'Recipe book',navMine:'My recipes',navShopping:'Shopping',navProfile:'My kitchen',more:'More',actions:'Recipe actions',meals:'meals',missing:'unavailable',today:'Today',nav:'Cook4Me views',todayHint:'Your meals, ingredients and next steps for today.',weekHint:'Your week, organised by day. Each meal stays with its date.',officialHint:'Find something good to cook. Your filters stay saved for this view.',bookHint:'Your favourite recipes and the dishes you want to cook next.',mineHint:'The recipes you have made your own.',shoppingHint:'Everything you need, in one organised shopping list.',profileHint:'Keep your food, storage and preferences together.',aiHint:'Create a recipe, then review the ingredients and cooking steps.'},
 de:{navToday:'Heute',navWeek:'Woche',navOfficial:'Entdecken',navBook:'Rezeptbuch',navMine:'Meine Rezepte',navShopping:'Einkaufen',navProfile:'Meine Küche',more:'Mehr',actions:'Rezeptaktionen',meals:'Mahlzeiten',missing:'nicht verfügbar',today:'Heute',nav:'Cook4Me-Ansichten',todayHint:'Deine Mahlzeiten, Zutaten und nächsten Schritte für heute.',weekHint:'Deine Woche, nach Tagen geordnet. Jede Mahlzeit gehört zu ihrem Datum.',officialHint:'Finde etwas Gutes zum Kochen. Die Filter bleiben für diese Ansicht gespeichert.',bookHint:'Deine Lieblingsrezepte und die Gerichte, die du als Nächstes kochen möchtest.',mineHint:'Die Rezepte, die du selbst gestaltet hast.',shoppingHint:'Alles, was du brauchst, auf einer übersichtlichen Einkaufsliste.',profileHint:'Lebensmittel, Lagerorte und Vorlieben an einem Ort.',aiHint:'Erstelle ein Rezept und prüfe Zutaten und Kochschritte.'},
 el:{navToday:'Σήμερα',navWeek:'Εβδομάδα',navOfficial:'Αναζήτηση',navBook:'Συνταγές',navMine:'Οι συνταγές μου',navShopping:'Αγορές',navProfile:'Η κουζίνα μου',more:'Περισσότερα',actions:'Ενέργειες συνταγής',meals:'γεύματα',missing:'μη διαθέσιμα',today:'Σήμερα',nav:'Προβολές Cook4Me',todayHint:'Τα γεύματα, τα υλικά και τα επόμενα βήματα για σήμερα.',weekHint:'Η εβδομάδα σου, οργανωμένη ανά ημέρα. Κάθε γεύμα στη δική του ημερομηνία.',officialHint:'Βρες τι θα μαγειρέψεις. Τα φίλτρα αποθηκεύονται ξεχωριστά για αυτή την προβολή.',bookHint:'Οι αγαπημένες σου συνταγές και όσα θέλεις να μαγειρέψεις στη συνέχεια.',mineHint:'Οι συνταγές που έφτιαξες στα μέτρα σου.',shoppingHint:'Όσα χρειάζεσαι, σε μία οργανωμένη λίστα αγορών.',profileHint:'Τρόφιμα, χώροι αποθήκευσης και προτιμήσεις σε ένα μέρος.',aiHint:'Δημιούργησε συνταγή και έλεγξε τα υλικά και τα βήματα μαγειρέματος.'}
};
const NAV=[['today','weather-sunny'],['week','calendar-week'],['official','magnify'],['book','book-open-page-variant-outline'],['mine','chef-hat'],['shopping','cart-outline'],['profile','home-heart']];
const PRIMARY=new Set(['send','favorite']);
const setText=(node,value)=>{if(node&&node.textContent!==value)node.textContent=value;};
const setAttribute=(node,key,value)=>{if(node&&node.getAttribute(key)!==value)node.setAttribute(key,value);};
export function designText(language,key){return (DESIGN_TEXT[String(language||'en').split(/[-_]/)[0]]||DESIGN_TEXT.en)[key]||DESIGN_TEXT.en[key]||'';}

export function restyleRecipe(card,labels,{expanded=false}={}){
 if(!card||card.hasAttribute('data-v202-recipe-gap')||card.classList.contains('ui203-recipe'))return card;
 card.classList.add('ui203-recipe');
 const heading=card.querySelector('.rx-v66-title'),title=heading?.querySelector('h3');
 if(title){
  const body=document.createElement('div');body.className='ui203-recipe-heading';title.before(body);body.append(title);
  const language=title.querySelector('span');
  if(language){language.classList.add('ui203-recipe-language');language.textContent=language.textContent.trim().replace(/^\((.*)\)$/,'$1');body.append(language);}
 }
 const actions=card.querySelector('.rx-v67-photo-actions');
 if(actions){
  card.querySelector(':scope > .rx-v69-media')?.after(actions);
  buildActionDock(actions,labels,expanded);
 }
 return card;
}

export function buildActionDock(dock,labels,expanded=false){
 if(!dock||dock.dataset.ui203Dock)return;
 dock.dataset.ui203Dock='';dock.classList.remove('rx-v69-overlay');dock.classList.add('ui203-action-dock');
 const controls=[...dock.querySelectorAll('button,select')];
 // Select elements and all secondary controls stay the original nodes. Do not
 // clone them: some consumers bind listeners before the fullscreen is decorated.
 const secondary=controls.filter(node=>node.tagName==='SELECT'||!PRIMARY.has(node.dataset.v66Action));
 const primary=controls.filter(node=>node.tagName==='BUTTON'&&PRIMARY.has(node.dataset.v66Action));
 for(const control of primary)dock.append(control);
 let more=null;
 if(secondary.length){
  more=document.createElement('details');more.className='ui203-more';more.dataset.ui203Actions='';
  const summary=document.createElement('summary');summary.setAttribute('aria-label',labels.actions);
  const dots=document.createElement('span');dots.textContent='•••';dots.setAttribute('aria-hidden','true');
  const text=document.createElement('span');text.textContent=labels.more;summary.append(dots,text);
  const grid=document.createElement('div');grid.className='ui203-more-grid';grid.dataset.ui203Secondary='';
  for(const control of secondary){
   if(control.tagName==='BUTTON'&&!control.querySelector('.ui203-action-label')){
    const label=control.getAttribute('aria-label')||control.title;
    if(label){const span=document.createElement('span');span.className='ui203-action-label';span.textContent=label;control.append(span);}
   }
   grid.append(control);
  }
  more.append(summary,grid);more.open=!!expanded;dock.append(more);
 }
 for(const group of dock.querySelectorAll('.rx-v66-actions'))if(!group.children.length)group.remove();
}

export function decorateDay(day,labels){
 if(!day)return;
 const heading=day.querySelector(':scope > h3');if(!heading)return;
 let meta=day.querySelector(':scope > .ui203-day-meta');
 if(!meta){meta=document.createElement('div');meta.className='ui203-day-meta';heading.after(meta);}
 const meals=day.querySelectorAll('.rx-week-slot article.recipe:not([data-v202-recipe-gap])').length;
 const missing=day.querySelectorAll('[data-v202-recipe-gap]').length;
 const today=day.getAttribute('aria-current')==='date';
 const signature=JSON.stringify([meals,missing,today,labels]);
 if(meta.dataset.signature===signature)return;
 meta.dataset.signature=signature;meta.replaceChildren();
 const badge=(label,className='')=>{const span=document.createElement('span');span.className=className;span.textContent=label;meta.append(span);};
 if(today)badge(labels.today,'ui203-today');
 badge(`${meals} ${labels.meals}`);if(missing)badge(`${missing} ${labels.missing}`);
}

// Keep the existing form controls and their listeners while grouping the diet
// profiles like the other kitchen sections. Member edits rerender this form.
export function groupDietPreferences(container,state){
 const form=container?.querySelector('[data-v83-profiles]'),heading=container?.querySelector(':scope > h2');
 if(!form||!heading)return;
 state.sectionOpen??=new Map();
 const section=document.createElement('section');section.className='card ui233-diet-section';
 heading.before(section);section.append(heading,form);
 const household=form.querySelector('[data-v83-profile="household"]'),title=household?.querySelector(':scope > h3');
 if(household&&title){
  const fold=document.createElement('details'),summary=document.createElement('summary');
  fold.className=household.className;fold.dataset.v83Profile='household';
  fold.open=state.sectionOpen.get('household')??true;
  summary.append(...title.childNodes);title.remove();fold.append(summary,...household.childNodes);household.replaceWith(fold);
  fold.addEventListener('toggle',()=>state.sectionOpen.set('household',fold.open));
 }
 const input=form.querySelector('#preferences'),label=input?.closest('label');
 if(label){
  const fold=document.createElement('details'),summary=document.createElement('summary');
  fold.className='card v83-diet-card ui233-other-preferences';
  fold.open=state.sectionOpen.get('other')??false;
  summary.textContent=[...label.childNodes].filter(node=>node!==input).map(node=>node.textContent).join('').trim();
  input.setAttribute('aria-label',summary.textContent);
  const body=document.createElement('div');body.className='v83-profile-body';
  label.before(fold);body.append(input);label.remove();fold.append(summary,body);
  fold.addEventListener('toggle',()=>state.sectionOpen.set('other',fold.open));
 }
}

export const AppDesignMixin=Base=>class extends Base{
 _ui203Text(key){return designText(this._uiIngredientLanguage?.()||this._langCode?.()||'en',key);}
 _ui203Labels(){return Object.fromEntries(['more','actions','meals','missing','today'].map(key=>[key,this._ui203Text(key)]));}
 _ui203Install(){
  const root=this.shadowRoot;if(!root)return;
  this.classList.add('ui203');
  if(!root.querySelector('#ui203Theme')){const style=document.createElement('style');style.id='ui203Theme';style.textContent=APP_THEME;root.append(style);}
  if(this._ui203Root===root&&this._ui203Events)return;
  this._ui203Events?.abort();this._ui203Root=root;this._ui203Events=new AbortController();
  const options={capture:true,signal:this._ui203Events.signal};
  // Native disclosure instead of a hover-only menu: works with keyboard/touch.
  root.addEventListener('click',event=>{
   const path=event.composedPath();
   for(const more of root.querySelectorAll('details[data-ui203-actions][open]'))if(!path.includes(more))more.open=false;
  },options);
  document.addEventListener('keydown',event=>{
   if(event.key!=='Escape'||!event.composedPath().includes(this))return;
   const more=root.activeElement?.closest?.('details[data-ui203-actions][open]');
   if(more){event.preventDefault();event.stopImmediatePropagation();more.open=false;more.querySelector('summary')?.focus({preventScroll:true});}
  },options);
 }
 _ui203Navigation(){
  const tabs=this.shadowRoot?.querySelector('#tabs');if(!tabs)return;
  setAttribute(tabs,'aria-label',this._ui203Text('nav'));
  tabs.querySelector('[data-tab=ai]')?.remove(); // Matches the established shell.
  for(const [index,[key,icon]] of NAV.entries()){
   const button=tabs.querySelector(`[data-tab="${key}"]`);if(!button)continue;
   let glyph=button.querySelector('ha-icon,svg');
   if(!glyph){glyph=document.createElement('ha-icon');glyph.setAttribute('icon',`mdi:${icon}`);glyph.setAttribute('aria-hidden','true');button.prepend(glyph);}
   let label=button.querySelector('.ui203-nav-label');
   if(!label){
    // Older renderers include their own hidden text span. Reuse it if possible.
    label=[...button.children].find(node=>node.tagName==='SPAN')||document.createElement('span');
    label.classList.add('ui203-nav-label');if(label.parentElement!==button)button.append(label);
   }
   const text=this._t(key);setText(label,this._ui203Text('nav'+key[0].toUpperCase()+key.slice(1))||text);setAttribute(button,'title',text);setAttribute(button,'aria-label',text);setAttribute(button,'aria-pressed',String(this._tab===key));
   if(tabs.children[index]!==button)tabs.insertBefore(button,tabs.children[index]||null);
  }
 }
 // The old modernizer removes all text on every observed mutation. Owning this
 // hook avoids a remove/re-add observer loop while preserving order and labels.
 _modernizeTabs(){this._ui203Navigation();}
 _ui203Page(){
  this._ui203Install();this._ui203Navigation();
  const section=this.shadowRoot?.querySelector('#content > [data-v100-section]');
  if(section){
   if(this._tab==='shopping'){
    const heading=this.shadowRoot.querySelector('#shoppingRefresh')?.closest('.detail-head');
    if(heading&&!section.contains(heading)){section.querySelector(':scope > h2')?.remove();section.prepend(heading);}
   }
   const value=this._ui203Text(`${this._tab}Hint`);let subtitle=section.querySelector(':scope > .ui203-view-subtitle');
   if(value&&!subtitle){subtitle=document.createElement('p');subtitle.className='ui203-view-subtitle';section.append(subtitle);}
   if(subtitle)setText(subtitle,value);
  }
  for(const day of this.shadowRoot?.querySelectorAll('.rx-week-day[data-week-date]')||[])decorateDay(day,this._ui203Labels());
 }
 _recipeCard(recipe,custom=false){
  this._ui203Install();const html=super._recipeCard(recipe,custom);if(!html)return html;
  const holder=document.createElement('div');holder.innerHTML=html;
  const card=holder.querySelector('article.rx-v66-recipe');
  if(card){const row=this._v66Refs?.get(card.dataset.v66Ref);const state=row?this._v66State(row.recipe,row.slot?.id||''):null;restyleRecipe(card,this._ui203Labels(),{expanded:state?.ui203More===true});}
  return holder.innerHTML;
 }
 _ui203BindActions(container){
  const context=this._prefKey?.();
  for(const more of container?.querySelectorAll('details[data-ui203-actions]')||[]){
   if(more._ui203Bound)continue;more._ui203Bound=true;
   const card=more.closest('[data-v66-ref]');const row=card?this._v66Refs?.get(card.dataset.v66Ref):null;
   const state=row?this._v66State(row.recipe,row.slot?.id||''):null;
   more.addEventListener('toggle',()=>{if(state&&context===this._prefKey?.())state.ui203More=more.open;});
   // prevent a parent slot's click-to-open shortcut; the real button listeners
   // remain bound and run normally within the disclosure.
   more.addEventListener('click',event=>event.stopPropagation());
  }
 }
 _bindCards(container,...args){const result=super._bindCards(container,...args);this._ui203Install();this._ui203BindActions(container);return result;}
 _v71FitTitle(title){
  if(title?.closest('article.ui203-recipe')){for(const name of ['font-size','height','max-height','line-height'])title.style.removeProperty(name);return;}
  return super._v71FitTitle?.(title);
 }
 _v119FitInput(input,minChars){
  if(input?.matches('main [data-draft=quantity],[data-v112-count-edit]')){
   input.style.setProperty('width','100%','important');input.style.setProperty('max-width','100%','important');
   input.closest('label')?.classList.add('ui203-number-field');return;
  }
  return super._v119FitInput(input,minChars);
 }
 _buttonIcon(button){if(button?.closest('.ui203-more-grid')||button?.hasAttribute('data-ui203-control'))return null;return super._buttonIcon(button);}
 _renderRecipeDialog(){
  const result=super._renderRecipeDialog();this._ui203Install();
  const overlay=this._v63RecipeDialog,side=overlay?.querySelector('.rx-v67-photo-side'),actions=side?.querySelector('.rx-v67-photo-actions');
  if(actions){side.append(actions);buildActionDock(actions,this._ui203Labels());this._ui203BindActions(overlay);}
  return result;
 }
 _ui203Form(){
  this._ui203Install();const c=this._v78Dialog,d=this._v78Draft;
  if(!c||!d){this._ui203FooterObserver?.disconnect();this._ui203FooterObserver=null;this._ui203Footer=null;return;}
  c.classList.toggle('ui203-form',!!d.editorOpen);
  const footer=c.querySelector('[data-v196-actions]');
  if(footer!==this._ui203Footer){
   this._ui203FooterObserver?.disconnect();this._ui203FooterObserver=null;this._ui203Footer=footer;
   if(footer&&typeof ResizeObserver==='function'){
    this._ui203FooterObserver=new ResizeObserver(()=>{
     if(this._v78Dialog!==c||!footer.isConnected)return;
     const value=Math.ceil(footer.getBoundingClientRect().height)+'px';
     if(c.style.getPropertyValue('--ui203-footer-height')!==value)c.style.setProperty('--ui203-footer-height',value);
    });this._ui203FooterObserver.observe(footer);
   }
  }
 }
 _renderShell(){const result=super._renderShell();this._ui203Page();return result;}
 _renderTabs(){const result=super._renderTabs();this._ui203Navigation();return result;}
 _v100Layout(){const result=super._v100Layout();this._ui203Page();return result;}
 _v100Header(){const result=super._v100Header();this._ui203Install();return result;}
 _renderTab(){const result=super._renderTab();this._ui203Page();return result;}
 _v83RenderProfiles(container,state){const result=super._v83RenderProfiles(container,state);groupDietPreferences(container,state);return result;}
 _showFilter(key){const result=super._showFilter(key);this._ui203Install();return result;}
 _v78RenderCapture(){const result=super._v78RenderCapture();this._ui203Form();return result;}
 _v111Paint(){const result=super._v111Paint();this._ui203Form();return result;}
 _v78Close(...args){const result=super._v78Close(...args);if(!this._v78Dialog)this._ui203Form();return result;}
 _resetUserScopedUiState(){this._ui203Cleanup();return super._resetUserScopedUiState();}
 _resetEntryScopedUiState(){this._ui203Cleanup();return super._resetEntryScopedUiState();}
 _ui203Cleanup(){this._ui203Events?.abort();this._ui203Events=null;this._ui203FooterObserver?.disconnect();this._ui203FooterObserver=null;this._ui203Footer=null;}
 disconnectedCallback(){this._ui203Cleanup();super.disconnectedCallback();}
};
