const V136='cook4me-recipe-hub-panel-v136';
if(!customElements.get(V136))await import('./cook4me-panel-v136.js?v=2026.9.21.1');
const BasePanel=customElements.get(V136);

class Cook4MeRecipeHubPanelV137 extends BasePanel{
 _v136FoldWeekSections(_container){
  /* v136 folded the recipe's own disclosure sections. The requested folding
     is for the large Week summary panels instead, so keep recipe state intact. */
 }
 _v137FoldWeekPanels(container){
  if(!container)return;
  const wanted=new Map([
   [this._t('leftovers'),'leftovers'],
   [this._t('nutritionDashboard'),'nutrition'],
   [this._t('priceInventory'),'prices'],
  ]);

  for(const section of [...container.querySelectorAll('section.card')]){
   if(section.closest('details[data-v137-week-panel]'))continue;
   const heading=section.querySelector(':scope>h3');
   if(!heading)continue;
   const key=wanted.get(String(heading.textContent||'').trim());
   if(!key)continue;

   const details=document.createElement('details');
   details.className='card rx-v137-week-panel';
   details.dataset.v137WeekPanel=key;

   const summary=document.createElement('summary');
   summary.innerHTML=`<span>${this._escape(heading.textContent||'')}</span><ha-icon icon="mdi:chevron-down" aria-hidden="true"></ha-icon>`;
   details.append(summary);

   const body=document.createElement('div');
   body.className='rx-v137-week-panel-body';
   for(const node of [...section.childNodes]){
    if(node===heading)continue;
    body.append(node);
   }
   details.append(body);
   section.replaceWith(details);
  }
 }

 _renderWeek(container){
  const result=super._renderWeek(container);
  this._v137FoldWeekPanels(container);
  this._v137Styles();
  return result;
 }

 _updateHeader(){
  super._updateHeader();
  this._v137Styles();
 }
 _renderShell(){
  super._renderShell();
  this._v137Styles();
 }
 _renderTab(){
  const result=super._renderTab();
  this._v137Styles();
  if(this._tab==='week')this._v137FoldWeekPanels(this.shadowRoot?.getElementById('content'));
  this.setAttribute('data-cook4me-build','2026.9.21.2');
  return result;
 }

 _v137Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v137Styles'))return;
  const style=document.createElement('style');
  style.id='v137Styles';
  style.textContent=`
   /* Keep the clean v133 photo but physically crop the baked gray background
      away around the appliance silhouette. This avoids both the v134 artifacts
      and the v135/v136 rectangular photo tile. */
   .v130-model{
    isolation:auto!important;
    background:transparent!important;
    overflow:visible!important;
   }
   .v130-model-photo{
    clip-path:polygon(
     44% 9%,56% 9%,66% 12%,73% 17%,78% 24%,80% 28%,
     87% 31%,91% 38%,90% 42%,85% 46%,83% 56%,81% 69%,
     79% 80%,74% 87%,67% 92%,59% 95%,41% 95%,33% 92%,
     26% 87%,21% 80%,19% 69%,17% 56%,15% 46%,10% 42%,
     9% 38%,13% 31%,20% 28%,22% 24%,27% 17%,34% 12%
    )!important;
    mix-blend-mode:multiply!important;
    filter:brightness(1.1) contrast(1.1)!important;
    background:transparent!important;
   }

   .rx-v137-week-panel{
    margin-top:12px!important;
    padding:0!important;
    overflow:hidden;
   }
   .rx-v137-week-panel>summary{
    list-style:none;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    min-height:68px;
    padding:18px 20px;
    cursor:pointer;
    font-weight:750;
    font-size:1.05rem;
    user-select:none;
   }
   .rx-v137-week-panel>summary::-webkit-details-marker{display:none}
   .rx-v137-week-panel>summary ha-icon{
    --mdc-icon-size:22px;
    flex:0 0 auto;
    transition:transform .18s ease;
   }
   .rx-v137-week-panel[open]>summary ha-icon{transform:rotate(180deg)}
   .rx-v137-week-panel-body{
    padding:0 20px 20px;
    border-top:1px solid var(--divider-color);
   }
   .rx-v137-week-panel:not([open])>.rx-v137-week-panel-body{display:none}

   @media(max-width:700px){
    .rx-v137-week-panel>summary{padding:15px 14px;min-height:58px}
    .rx-v137-week-panel-body{padding:0 14px 14px}
   }
  `;
  this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v137',Cook4MeRecipeHubPanelV137);
