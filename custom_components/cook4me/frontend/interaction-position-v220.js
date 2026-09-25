// Preserve the user's place across synchronous DOM replacements. Deliberate
// navigation, new forms and validation focus keep their existing behaviour.
const escape = value => CSS.escape(String(value));
function pathTo(node, root) {
 const parts=[];
 for(let current=node;current&&current!==root;current=current.parentElement){
  if(current.id){parts.unshift('#'+escape(current.id));break;}
  const attr=[...current.attributes].find(a=>a.name.startsWith('data-')&&!/state-watch|persist|signature|index|bound/.test(a.name));
  if(attr){parts.unshift(`${current.localName}[${attr.name}="${escape(attr.value)}"]`);}
  else {const siblings=[...((current.parentElement||current.parentNode)?.children||[])].filter(n=>n.localName===current.localName);parts.unshift(`${current.localName}:nth-of-type(${siblings.indexOf(current)+1})`);}
 }
 return parts.join(' > ');
}
function ancestors(panel) {
 const nodes=[];
 for(let n=panel;n;n=n.parentElement||n.getRootNode?.().host)if(!nodes.includes(n))nodes.push(n);
 const page=panel.ownerDocument?.scrollingElement;if(page&&!nodes.includes(page))nodes.push(page);
 return nodes;
}
export function capturePosition(panel, root=panel.shadowRoot) {
 if(!root)return null;
 const nodes=[...root.querySelectorAll('div,section,main,dialog,select,textarea,ul,ol'),...ancestors(panel)];
 const scroll=[];
 for(const node of new Set(nodes)){
  const external=!root.contains(node),style=getComputedStyle(node);
  if(!external&&!node.scrollTop&&!node.scrollLeft&&!/(auto|scroll)/.test(style.overflowX+style.overflowY))continue;
  scroll.push({node,path:external?null:pathTo(node,root),top:node.scrollTop,left:node.scrollLeft});
 }
 const active=panel.shadowRoot?.activeElement;
 const focus=active&&root.contains(active)?{node:active,path:pathTo(active,root),start:active.selectionStart,end:active.selectionEnd}:null;
 const details=[...root.querySelectorAll('details')].map(node=>({path:pathTo(node,root),open:node.open}));
 return {root,scroll,focus,details};
}
export function restorePosition(panel, saved, {focus=true,details=true}={}) {
 if(!saved)return;
 const root=saved.root;
 const find=item=>item.node?.isConnected?item.node:item.path?root.querySelector(item.path):null;
 if(details)for(const item of saved.details){const node=root.querySelector(item.path);if(node)node.open=item.open;}
 if(focus&&saved.focus){
  const node=find(saved.focus),active=panel.shadowRoot?.activeElement;
  // Do not steal focus from a new modal, validation target or later interaction.
  if(node&&!node.disabled&&(!active||active===saved.focus.node||active===node)){
   node.focus?.({preventScroll:true});
   if(typeof saved.focus.start==='number')try{node.setSelectionRange(saved.focus.start,saved.focus.end);}catch(_error){}
  }
 }
 for(const item of [...saved.scroll].reverse()){
  const node=find(item);if(!node)continue;
  if(Math.abs(node.scrollTop-item.top)>.5||Math.abs(node.scrollLeft-item.left)>.5)node.scrollTo({top:item.top,left:item.left,behavior:'instant'});
 }
}
export const InteractionPositionMixin=Base=>class extends Base {
 _renderShell(...args){
  const result=super._renderShell(...args),root=this.shadowRoot;
  if(root&&!root.querySelector('#v220PositionStyle')){
   const style=document.createElement('style');style.id='v220PositionStyle';
   // Browser anchoring otherwise follows a replaced/focused row after our
   // restoration, including the editor's asynchronously sized sticky footer.
   style.textContent=':host,.v78-capture,.rx-dialog,.v114-link-list,[data-v194-list]{overflow-anchor:none}';root.append(style);
  }
  if(root&&!this._v220ClickRoot){
   this._v220ClickRoot=root;
   root.addEventListener('click',event=>{
    const target=event.composedPath().find(node=>node.matches?.('summary,[data-v179-fold-button]'));
    if(!target)return;
    const saved=capturePosition(this),tab=this._tab,context=this._v179StateKey(),ticket=this._v220Interaction=(this._v220Interaction||0)+1;
    requestAnimationFrame(()=>{
     if(ticket===this._v220Interaction&&target.isConnected&&tab===this._tab&&context===this._v179StateKey())restorePosition(this,saved,{focus:false,details:false});
    });
   },true);
   for(const type of ['wheel','touchstart','pointerdown','keydown'])root.addEventListener(type,()=>{this._v220Interaction=(this._v220Interaction||0)+1;},{capture:true,passive:true});
  }
  return result;
 }
 _v220KeepPosition(render,root=this.shadowRoot,settle=false){
  if(this._v220Rendering)return render();
  const saved=capturePosition(this,root),context=this._v179StateKey?.(),tab=this._tab;
  const interaction=this._v220Interaction||0,draft=this._v78Draft,focusEpoch=this._v196FocusEpoch;
  this._v220Rendering=true;
  try{return render();}
  finally{
   this._v220Rendering=false;
   if(context===this._v179StateKey?.()&&tab===this._tab){
    restorePosition(this,saved);
    if(settle)requestAnimationFrame(()=>{
     if(context===this._v179StateKey?.()&&tab===this._tab&&draft===this._v78Draft&&interaction===(this._v220Interaction||0)&&focusEpoch===this._v196FocusEpoch&&draft?.scanPhase!=='error')restorePosition(this,saved,{focus:false,details:false});
    });
   }
  }
 }
 _renderTab(){
  if(this._v179RenderedTab&&this._v179RenderedTab!==this._tab){
   const previous=this._v220Rendering;this._v220Rendering=true;
   try{return super._renderTab();}finally{this._v220Rendering=previous;}
  }
  return this._v220KeepPosition(()=>super._renderTab());
 }
 _renderProfile(...args){return this._v220KeepPosition(()=>super._renderProfile(...args));}
 _renderWeek(...args){return this._v220KeepPosition(()=>super._renderWeek(...args));}
 _v66Render(...args){return this._v220KeepPosition(()=>super._v66Render(...args));}
 _renderInventoryOnly(...args){return this._v220KeepPosition(()=>super._renderInventoryOnly(...args));}
 _v142PaintStockSummary(...args){return this._v220KeepPosition(()=>super._v142PaintStockSummary(...args));}
 _renderRecipeDialog(...args){return this._v220KeepPosition(()=>super._renderRecipeDialog(...args));}
 _v84CatalogRows(...args){return this._v220KeepPosition(()=>super._v84CatalogRows(...args));}
 _v78IngredientOptions(...args){return this._v220KeepPosition(()=>super._v78IngredientOptions(...args));}
 _v78RenderCapture(...args){
  // A fresh draft intentionally starts a new form; an existing draft keeps its
  // open sections, nested lists and keyboard position during async updates.
  const draft=this._v78Draft,same=this._v220RenderedDraft===draft;
  this._v220RenderedDraft=draft;
  return same?this._v220KeepPosition(()=>super._v78RenderCapture(...args),this.shadowRoot,true):super._v78RenderCapture(...args);
 }
 _v179CaptureViewState(tab=this._v179RenderedTab){
  if(tab){
   this._v220Views??=new Map();
   this._v220Views.set(`${this._v179StateKey()}:${tab}`,capturePosition(this));
  }
  return super._v179CaptureViewState(tab);
 }
 _v179RestoreViewState(){
  // The old implementation only restored #content.scrollTop. HA may scroll
  // the document or an outer shadow host instead; capture those actual owners.
  const saved=this._v220Views?.get(`${this._v179StateKey()}:${this._tab}`);
  if(!saved)return super._v179RestoreViewState();
  restorePosition(this,saved,{focus:false});
  this._v179RestoreRecipe();this._v179RestoreFilter();
 }
 _v114Picker(){
  const c=this._v78Dialog,d=this._v78Draft,select=c?.querySelector('[data-v78-ingredient]');if(!select||!d)return;
  if(!d.ingredient&&d.ingredientLinks?.length)d.ingredient=this._v112Local(d.ingredientLinks[0]);
  const label=select.closest('label');label.hidden=true;select.required=false;
  let holder=c.querySelector('[data-v114-links]');
  if(!holder){holder=document.createElement('div');holder.dataset.v114Links='';label.after(holder);}
  c.querySelector('[data-v111-catalog]')?.setAttribute('hidden','');
  d.ingredientLinks=this._v114Links();
  const identity=row=>this._scanIngredientIdentity(row),picked=new Set(d.ingredientLinks.map(identity));
  const language=this._uiIngredientLanguage(),all=new Map();
  for(const row of [...(this._ingredientCatalog||[]),...d.ingredientLinks])all.set(identity(row),row);
  const candidates=this._v223SeasonRows?.([...all.values()],picked,identity)||[...all.values()];
  const rows=candidates.filter(row=>picked.has(identity(row))||!d.query||this._ingredientQueryMatches(row,d.query)).sort((a,b)=>a.name.localeCompare(b.name,language));
  if(!holder._v220List){
   holder.replaceChildren();
   const title=document.createElement('strong'),help=document.createElement('p'),list=document.createElement('div'),count=document.createElement('small');
   title.textContent=this._v114Text('links');help.textContent=this._v114Text('help');list.className='v114-link-list';
   holder.append(title,help,list,count);holder._v220List=list;holder._v220Count=count;holder._v220Rows=new Map();
  }
  const list=holder._v220List,cache=holder._v220Rows,visible=new Set(rows.map(identity)),top=list.scrollTop;
  for(const [key,node] of cache)if(!visible.has(key)){node.remove();cache.delete(key);}
  rows.forEach((row,index)=>{
   const key=identity(row);let node=cache.get(key);
   if(!node){
    node=document.createElement('label');const input=document.createElement('input'),text=document.createElement('span');input.type='checkbox';input.dataset.v220Ingredient=key;node.append(input,text);cache.set(key,node);
    input.onchange=()=>{
     if(this._v78Dialog!==c||this._v78Draft!==d||this._v78Busy||this._v78Submitted)return;
     d.ingredientLinks=this._v114Links().filter(item=>identity(item)!==key);
     if(input.checked)d.ingredientLinks.push(node._v220Ingredient);
     if(!d.ingredientLinks.some(item=>identity(item)===identity(d.ingredient||{})))d.ingredient=d.ingredientLinks[0]||null;
     d.productLocked=true;this._v78Dirty=true;this._v78IngredientOptions();
    };
   }
   node._v220Ingredient=row;const input=node.firstElementChild;input.dataset.v114Link=String(index);input.checked=picked.has(key);input.disabled=!!this._v78Busy||!!this._v78Submitted;node.lastElementChild.textContent=this._v223Name?.(row)||row.name;
   // Leave unchanged nodes attached: moving a focused checkbox can itself
   // reset focus and scroll, even when the final HTML is identical.
   if(list.children[index]!==node)list.insertBefore(node,list.children[index]||null);
  });
  list.scrollTop=top;holder._v220Count.textContent=`${rows.length} / ${all.size}`;
  if(!this.shadowRoot.querySelector('#v114Styles')){
   const style=document.createElement('style');style.id='v114Styles';style.textContent='.v114-link-list{max-height:230px;overflow:auto;border:1px solid #ffffff60;border-radius:10px;padding:8px}.v114-link-list label{display:flex;gap:10px;align-items:center;padding:8px;cursor:pointer}.v114-link-list input[type=checkbox]{flex:0 0 20px;width:20px;height:20px;min-height:20px}.v114-link-list span{overflow-wrap:anywhere}[data-v114-links]>p{font-size:.85rem}';this.shadowRoot.append(style);
  }
  this._v194Suggestions?.();
 }
};
