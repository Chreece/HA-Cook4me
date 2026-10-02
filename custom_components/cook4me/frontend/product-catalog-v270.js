import {IngredientNameIndex,ingredientNameScore,nameSearchTokens,normalizeNameSearch} from './ingredient-name-search-v270.js';

const PAGE_SIZE=60;
const TEXT={
 en:{previous:'Previous ingredients',next:'Next ingredients',searching:'Searching ingredients…',preparing:'Preparing ingredient search…',empty:'No matching ingredients.',retained:'Already linked — outside this search',retry:'Retry catalog loading'},
 de:{previous:'Vorherige Zutaten',next:'Weitere Zutaten',searching:'Zutaten werden gesucht…',preparing:'Zutatensuche wird vorbereitet…',empty:'Keine passenden Zutaten.',retained:'Bereits verknüpft — außerhalb dieser Suche',retry:'Katalog erneut laden'},
 el:{previous:'Προηγούμενα υλικά',next:'Επόμενα υλικά',searching:'Αναζήτηση υλικών…',preparing:'Προετοιμασία αναζήτησης υλικών…',empty:'Δεν βρέθηκαν αντίστοιχα υλικά.',retained:'Ήδη συνδεδεμένο — εκτός αυτής της αναζήτησης',retry:'Νέα φόρτωση καταλόγου'}
};
const setText=(node,text)=>{if(node&&node.textContent!==text)node.textContent=text;};
export const ProductCatalogMixin=Base=>class extends Base{
 _v270Text(key){const code=String(this._uiIngredientLanguage?.()||'en').split(/[-_]/)[0];return (TEXT[code]||TEXT.en)[key];}
 _ingredientQueryMatches(row,query){return ingredientNameScore(row,query)>0;}
 _v270Index(){
  const catalog=this._ingredientCatalog||[],language=this._uiIngredientLanguage(),context=this._prefKey();
  let state=this._v270CatalogIndex;
  if(!state||state.catalog!==catalog||state.length!==catalog.length||state.language!==language||state.context!==context||state.market!==this._v140MarketNames){
   if(state)clearTimeout(state.timer);
   state={catalog,length:catalog.length,language,context,market:this._v140MarketNames,index:new IngredientNameIndex(catalog,language,row=>this._scanIngredientIdentity(row)),position:0};
   this._v270CatalogIndex=state;
  }
  this._v270Prime(state);return state;
 }
 _v270Prime(state){
  if(state.timer||state.position>=state.index.rows.length)return;
  // Normalize the full catalog in small tasks, never in a keystroke handler.
  // A frozen/closed form must not leave a background loop attached to a draft.
  const step=()=>{
   state.timer=null;
   if(this._v270CatalogIndex!==state||!this._v78Dialog)return;
   const start=performance.now();let n=0;
   while(state.position<state.index.rows.length&&n++<128){
    nameSearchTokens(state.index.rows[state.position++]);
    if(performance.now()-start>=5)break;
   }
   if(state.position<state.index.rows.length)state.timer=setTimeout(step,0);
   else if(this._v78Dialog)this._v114Picker();
  };
  state.timer=setTimeout(step,0);
 }
 _v270Meta(d){
  this._v270Drafts??=new WeakMap();let meta=this._v270Drafts.get(d);
  if(!meta){meta={manualQuery:!!String(d.query||'').trim(),lastName:''};this._v270Drafts.set(d,meta);}
  return meta;
 }
 _v270CancelQuery(){clearTimeout(this._v270QueryTimer);this._v270QueryTimer=null;this._v270QueryDraft=null;}
 _v270QueueQuery(delay=100){
  this._v270CancelQuery();const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  const holder=c.querySelector('[data-v114-links]');
  for(const input of holder?.querySelectorAll('[data-v114-link]')||[])input.disabled=true;
  setText(holder?.querySelector('[data-v270-count]'),this._v270Text('searching'));
  this._v270QueryDraft=d;
  this._v270QueryTimer=setTimeout(()=>{
   this._v270QueryTimer=null;
   if(c===this._v78Dialog&&d===this._v78Draft)this._v78IngredientOptions();
  },delay);
 }
 _v270BindSearch(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  const name=c.querySelector('main [data-draft="productName"]'),search=c.querySelector('[data-v78-search]');
  if(!name||!search||name._v270Draft===d)return;
  name._v270Draft=d;const meta=this._v270Meta(d);
  name.addEventListener('blur',event=>{
   if(c!==this._v78Dialog||d!==this._v78Draft||this._v78Busy||this._v78Submitted)return;
   const value=name.value.trim();
   if(!value||value===meta.lastName)return;meta.lastName=value;
   if(meta.manualQuery||this._v114Links().length||(d.suggestions||[]).some(item=>item?.ingredient?.name))return;
   // Search only: a match is never permission to assign an ingredient/stock.
   d.query=value;search.value=value;meta.selectOnFocus=event.relatedTarget===search;this._v270QueueQuery(0);
  });
  search.addEventListener('focus',()=>{if(meta.selectOnFocus){meta.selectOnFocus=false;search.select();}});
  search.oninput=()=>{
   if(d!==this._v78Draft||this._v78Submitted)return;
   meta.manualQuery=true;d.query=search.value;this._v270QueueQuery();
  };
  search.addEventListener('keydown',event=>{
   if(event.key==='Enter'){event.preventDefault();this._v270CancelQuery();this._v78IngredientOptions();}
  });
 }
 _v78IngredientOptions(){
  const c=this._v78Dialog,d=this._v78Draft;if(!c||!d)return;
  // The legacy path built another hidden 3,249-option select, rebuilt the
  // checkbox list, and triggered all scanner decorators for every keypress.
  this._v114Picker();this._v194Suggestions?.();
  const links=this._v114Links(),business=JSON.stringify(links.map(row=>this._scanIngredientIdentity(row)));
  if(d._v270BusinessLinks!==business){
   d._v270BusinessLinks=business;this._v79SchedulePrice?.();this._v222Editor?.();
  }
 }
 _v114Picker(){
  const c=this._v78Dialog,d=this._v78Draft,select=c?.querySelector('[data-v78-ingredient]');if(!select||!d)return;
  if(this._v270QueryDraft&&this._v270QueryDraft!==d)this._v270CancelQuery();
  const legacyLabel=select.closest('label');legacyLabel.hidden=true;select.required=false;
  c.querySelector('[data-v111-catalog]')?.setAttribute('hidden','');
  if(!d.editorOpen&&d.mode!=='manual')return;
  const links=this._v114Links();
  if(!d.ingredient&&links.length)d.ingredient=links[0];
  d.ingredientLinks=links;
  const identity=row=>this._scanIngredientIdentity(row),picked=new Set(links.map(identity));
  const selectedKey=d.ingredient?identity(d.ingredient):'';
  if(select._v270Selected!==selectedKey){
   select.replaceChildren(new Option(this._v78Text('choose'),''));
   if(d.ingredient)select.append(new Option(d.ingredient.name,selectedKey,true,true));
   select._rows=links;select.value=selectedKey;select._v270Selected=selectedKey;
  }
  let holder=c.querySelector('[data-v114-links]');
  if(!holder){holder=document.createElement('div');holder.dataset.v114Links='';legacyLabel.after(holder);}
  // This menu assigns food already being added. Recipe season preferences must
  // neither hide ingredients here nor add a season control to the form.
  holder.querySelector('[data-v223-season]')?.remove();
  let state=holder._v270State;
  if(!state||state.draft!==d){
   const title=document.createElement('strong'),help=document.createElement('p'),list=document.createElement('div'),nav=document.createElement('div');
   list.className='v114-link-list';nav.className='v270-catalog-pages';
   const previous=document.createElement('button'),next=document.createElement('button'),count=document.createElement('small'),retry=document.createElement('button');
   for(const button of [previous,next,retry]){button.type='button';button.className='btn secondary';}
   previous.textContent='‹';next.textContent='›';previous.dataset.v270Previous='';next.dataset.v270Next='';count.dataset.v270Count='';count.setAttribute('role','status');retry.dataset.v270Retry='';
   nav.append(previous,count,next,retry);holder.replaceChildren(title,help,list,nav);
   const meta=this._v270Meta(d),samePage=meta.pageQuery===normalizeNameSearch(d.query)&&meta.pageIndex===this._v270CatalogIndex;
   state={draft:d,page:samePage?meta.page:0,query:samePage?meta.pageQuery:null,indexed:samePage?meta.pageIndex:null,nodes:new Map(),title,help,list,previous,next,count,retry};holder._v270State=state;
   previous.onclick=()=>{if(state.page>0){state.page--;state.signature=null;list.scrollTop=0;this._v114Picker();}};
   next.onclick=()=>{state.page++;state.signature=null;list.scrollTop=0;this._v114Picker();};
   retry.onclick=()=>void this._loadIngredientCatalog(null,true);
  }
  if(this._v270QueryTimer)return;
  const indexed=this._v270Index(),query=normalizeNameSearch(d.query),ready=indexed.position>=indexed.index.rows.length;
  if(state.query!==query||state.indexed!==indexed){state.page=0;state.query=query;}
  const failed=!this._ingredientCatalogLoading&&this._v63CatalogFailure===`${this._entryId}:${this._uiIngredientLanguage()}`;
  const busy=!!this._v78Busy||!!this._v78Submitted,signature=JSON.stringify([query,[...picked],busy,state.page,ready,!!this._ingredientCatalogLoading,failed]);
  if(state.indexed===indexed&&state.signature===signature)return;
  state.indexed=indexed;state.signature=signature;
  const rows=query&&!ready?[]:indexed.index.search(query);
  state.page=Math.max(0,Math.min(state.page,Math.ceil(rows.length/PAGE_SIZE)-1));
  Object.assign(this._v270Meta(d),{page:state.page,pageQuery:query,pageIndex:indexed});
  const offset=state.page*PAGE_SIZE,visible=rows.slice(offset,offset+PAGE_SIZE),visibleIds=new Set(visible.map(identity));
  // Selected identities remain removable, even outside the current search/page.
  const retained=links.filter(row=>!visibleIds.has(identity(row))),shown=[...retained,...visible];
  const retainedIds=new Set(retained.map(identity)),wanted=new Set(shown.map(identity));
  for(const [key,node] of state.nodes)if(!wanted.has(key)){node.remove();state.nodes.delete(key);}
  for(const [i,row] of shown.entries()){
   const key=identity(row);let node=state.nodes.get(key);
   if(!node){
    node=document.createElement('label');const input=document.createElement('input'),label=document.createElement('span');
    input.type='checkbox';input.dataset.v220Ingredient=key;node.append(input,label);state.nodes.set(key,node);
    input.onchange=()=>{
     if(c!==this._v78Dialog||d!==this._v78Draft||this._v78Busy||this._v78Submitted||this._v270QueryTimer)return;
     d.ingredientLinks=this._v114Links().filter(item=>identity(item)!==key);
     if(input.checked)d.ingredientLinks.push(node._v220Ingredient);
     if(!d.ingredientLinks.some(item=>identity(item)===identity(d.ingredient||{})))d.ingredient=d.ingredientLinks[0]||null;
     d.productLocked=true;this._v78Dirty=true;this._v78IngredientOptions();this._v111Paint?.();
    };
   }
   node._v220Ingredient=row;const input=node.firstElementChild;input.dataset.v114Link=String(i);input.checked=picked.has(key);input.disabled=busy||!!(query&&!ready);
   const label=this._v223Name?.(row)||row.name;
   setText(node.lastElementChild,label+(retainedIds.has(key)?` — ${this._v270Text('retained')}`:''));
   if(state.list.children[i]!==node)state.list.insertBefore(node,state.list.children[i]||null);
  }
  setText(state.title,this._v114Text('links'));setText(state.help,this._v114Text('help'));
  state.previous.hidden=state.next.hidden=rows.length<=PAGE_SIZE;
  state.previous.disabled=busy||state.page===0;state.next.disabled=busy||offset+PAGE_SIZE>=rows.length;
  state.previous.setAttribute('aria-label',this._v270Text('previous'));state.next.setAttribute('aria-label',this._v270Text('next'));
  state.retry.hidden=!failed;state.retry.disabled=busy;setText(state.retry,this._v270Text('retry'));
  setText(state.count,this._ingredientCatalogLoading?this._t('catalogLoading'):query&&!ready?this._v270Text('preparing'):rows.length?`${offset+1}–${Math.min(offset+PAGE_SIZE,rows.length)} / ${rows.length} · ${indexed.index.rows.length}`:this._v270Text('empty'));
  if(!this.shadowRoot.querySelector('#v270CatalogStyles')){
   const style=document.createElement('style');style.id='v270CatalogStyles';style.textContent=`
    .v114-link-list{max-height:260px;overflow:auto;overflow-anchor:none;border:1px solid var(--divider-color);border-radius:10px;padding:8px}
    .v114-link-list label{display:flex;gap:10px;align-items:center;padding:8px;cursor:pointer;min-height:44px;box-sizing:border-box}
    .v114-link-list input[type=checkbox]{flex:0 0 20px;width:20px;height:20px;min-height:20px}
    .v114-link-list span{overflow-wrap:anywhere}[data-v114-links]>p{font-size:.85rem}
    .v270-catalog-pages{display:flex;align-items:center;gap:10px;margin-top:6px}.v270-catalog-pages small{flex:1}
    .v270-catalog-pages button{min-width:44px;min-height:44px}
   `;this.shadowRoot.append(style);
  }
 }
 _v78RenderCapture(){const result=super._v78RenderCapture();this._v270BindSearch();return result;}
 _v78Close(...args){
  const c=this._v78Dialog,result=super._v78Close(...args);
  if(c&&!this._v78Dialog){this._v270CancelQuery();if(this._v270CatalogIndex){clearTimeout(this._v270CatalogIndex.timer);this._v270CatalogIndex.timer=null;}}
  return result;
 }
 _renderTab(){const result=super._renderTab();this.setAttribute('data-cook4me-ui-revision','270');return result;}
};
