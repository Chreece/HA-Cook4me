// Move existing controls, not copies: native state and all change handlers survive.
export function selectedFirst(rows, selected) {
 return [...rows.filter(selected), ...rows.filter(row=>!selected(row))];
}
export function installSelectedFirst(overlay, activeElement=()=>null) {
 if(!overlay||overlay._v202SelectedFirst)return;
 overlay._v202SelectedFirst=true;
 const groups=new Map();
 for(const input of overlay.querySelectorAll('input[type="checkbox"][data-list]')) {
  const row=input.closest('label');if(!row)continue;
  const parent=row.parentElement,key=input.dataset.list;
  let group=[...groups.values()].find(g=>g.parent===parent&&g.key===key);
  if(!group){group={parent,key,rows:[],anchor:document.createComment('selected filter items')};groups.set(group,group);parent.insertBefore(group.anchor,row);}
  group.rows.push({row,input});
 }
 const reorder=()=>{
  const active=activeElement();
  for(const {parent,anchor,rows} of groups.values()) {
   let previous=anchor;
   for(const item of selectedFirst(rows,item=>item.input.checked)) {
    if(previous.nextSibling!==item.row)parent.insertBefore(item.row,previous.nextSibling);
    previous=item.row;
   }
  }
  // Reordering a focused checkbox can blur it in some browsers.
  if(active?.isConnected&&overlay.contains(active)&&activeElement()!==active)active.focus?.({preventScroll:true});
 };
 reorder();
 overlay.addEventListener('change',event=>{
  if(event.target.matches?.('input[data-list]'))reorder();
 });
 // Search keeps its existing alias-aware matching. Selected rows remain at the
 // top even when their names do not match the search term, so they can be cleared.
 const showSelected=()=>{
  for(const group of groups.values())for(const {row,input} of group.rows)if(input.checked){row.style.display='';row.hidden=false;}
 };
 overlay.addEventListener('input',event=>{if(event.target.matches?.('[data-ingredient-search]')){showSelected();reorder();}});
 overlay.addEventListener('change',event=>{if(event.target.matches?.('input[data-list]')){
  const search=overlay.querySelector('[data-ingredient-search]');
  if(search?.value)search.dispatchEvent(new Event('input',{bubbles:true}));
 }});
}
export const SelectedFilterMixin=Base=>class extends Base {
 _showFilter(key){
  const result=super._showFilter(key);
  const overlay=[...this.shadowRoot?.querySelectorAll('[data-filter-dialog]')||[]].find(node=>node.dataset.filterDialog===key);
  installSelectedFirst(overlay,()=>this.shadowRoot?.activeElement);
  return result;
 }
};
