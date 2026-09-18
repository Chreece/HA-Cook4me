import "./cook4me-panel-v66.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v66");
const BUILD="2026.9.15.9";
// Adult label reference intakes: Regulation (EU) 1169/2011, Annex XIII.
// Fibre: EFSA Journal 2010;8(3):1462. These are daily, not per-meal targets.
const NUTRIENTS=[
 ["energy",["energyKcal","calories"],"kcal",2000],
 ["protein",["proteinG","protein"],"g",50],
 ["carbs",["carbohydrateG","carbohydrates","carbs"],"g",260],
 ["fat",["fatG","fat"],"g",70],
 ["saturatedFat",["saturatedFatG","saturatedFat"],"g",20],
 ["sugars",["sugarsG","sugarG","sugars"],"g",90],
 ["fiber",["fiberG","fiber"],"g",25],
 ["salt",["saltG","salt"],"g",6],
 ["nutrientSodium",["sodiumG","sodium"],"g",2.4],
];
const TEXT={
 en:{dailyReference:"of daily reference",dailyReferenceHelp:"Adult daily reference values; fibre uses the EFSA adequate intake.",dailyReferenceUnknown:"Daily percentage unavailable without a serving basis",nutrientsUnavailable:"Nutrient values are not available yet.",nutrientCoverage:"Ingredients with nutrient data",nextSevenDays:"Today and the next 6 days",noPlannedMeal:"No meal planned",generateWeek:"Plan the next 7 days",saturatedFat:"Saturated fat",sugars:"Sugars",salt:"Salt"},
 el:{dailyReference:"της ημερήσιας τιμής αναφοράς",dailyReferenceHelp:"Ημερήσιες τιμές αναφοράς ενηλίκων· για τις ίνες χρησιμοποιείται η επαρκής πρόσληψη της EFSA.",dailyReferenceUnknown:"Δεν διατίθεται ημερήσιο ποσοστό χωρίς βάση ανά μερίδα",nutrientsUnavailable:"Δεν υπάρχουν ακόμη τιμές θρεπτικών στοιχείων.",nutrientCoverage:"Υλικά με διατροφικά δεδομένα",nextSevenDays:"Σήμερα και οι επόμενες 6 ημέρες",noPlannedMeal:"Δεν έχει προγραμματιστεί γεύμα",generateWeek:"Πρόγραμμα επόμενων 7 ημερών",saturatedFat:"Κορεσμένα λιπαρά",sugars:"Σάκχαρα",salt:"Αλάτι"},
 de:{dailyReference:"des Tagesreferenzwerts",dailyReferenceHelp:"Tagesreferenzwerte für Erwachsene; Ballaststoffe nach der angemessenen Zufuhr der EFSA.",dailyReferenceUnknown:"Tagesanteil ohne Portionsbasis nicht verfügbar",nutrientsUnavailable:"Noch keine Nährwertangaben verfügbar.",nutrientCoverage:"Zutaten mit Nährwertangaben",nextSevenDays:"Heute und die nächsten 6 Tage",noPlannedMeal:"Keine Mahlzeit geplant",generateWeek:"Nächste 7 Tage planen",saturatedFat:"Gesättigte Fettsäuren",sugars:"Zucker",salt:"Salz"},
};
const finite=value=>value!==null&&value!==undefined&&value!==""&&typeof value!=="boolean"&&Number.isFinite(Number(value))&&Number(value)>=0?Number(value):null;
const CALENDAR='<svg data-v67-week-icon viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18M7 14h2m2 0h2m2 0h2M7 18h2m2 0h2m2 0h2"/></svg>';

class Cook4MeRecipeHubPanelV67 extends BasePanel{
 _t(key){return TEXT[this._uiIngredientLanguage()]?.[key]||TEXT.en[key]||super._t(key);}
 async _v66PreferLanguages(rows){
  const key=this._prefKey(),language=this._uiIngredientLanguage();
  for(let offset=0;offset<rows.length;offset+=8){if(key!==this._prefKey()||language!==this._uiIngredientLanguage())break;await super._v66PreferLanguages(rows.slice(offset,offset+8));}
  return rows;
 }
 _v67Dom(html){const node=document.createElement("div");node.innerHTML=html;return node;}
 _recipeCard(recipe,custom=false){
  const html=super._recipeCard(recipe,custom);if(!html)return html;
  const node=this._v67Dom(html),card=node.firstElementChild;
  const row=this._v66Refs.get(card.dataset.v66Ref),state=this._v66State(recipe,row?.slot?.id||"");
  const source=state.expanded?card:this._v67Dom(this._v66Body(recipe,custom,state,row?.slot));
  const actions=document.createElement("div");actions.className="rx-v67-photo-actions";
  source.querySelectorAll(".rx-v66-actions").forEach(group=>actions.appendChild(group));
  card.querySelector("[data-v66-photo]").after(actions);
  const cook=actions.querySelector('[data-v66-action="cook"]');
  if(cook){cook.title=this._t("startCookingView");cook.setAttribute("aria-label",cook.title);cook.querySelector("ha-icon")?.setAttribute("icon","mdi:chef-hat");}
  return node.innerHTML;
 }
 _v60NutritionChips(recipe){
  const data=this._v60Nutrition(recipe),escape=value=>this._escape(String(value));
  const title=`<h4>${escape(this._t("nutrition"))}</h4>`;
  if(!data)return `<section class="rx-v67-nutrition">${title}<p class="muted">${escape(this._t("nutrientsUnavailable"))}</p></section>`;
  const rows=[];
  for(const [key,aliases,unit,reference] of NUTRIENTS){
   let value=null;for(const alias of aliases){value=finite(data.values[alias]);if(value!==null)break;}
   if(value===null)continue;
   const amount=new Intl.NumberFormat(this._hass?.language||"en",{maximumFractionDigits:unit==="kcal"?0:2}).format(value);
   const percent=data.perServing?Math.round(value/reference*100):null;
   rows.push(`<div class="rx-v67-nutrient" data-nutrient="${key}"><span>${escape(this._t(key))}</span><strong>${amount} ${unit}</strong><small ${percent!==null?`data-daily-percent="${percent}"`:""}>${percent!==null?`${percent}% ${escape(this._t("dailyReference"))}`:"—"}</small></div>`);
  }
  const estimate=data.coverage!==null&&data.coverage<100?this._t("partialNutrition"):data.nutrition.estimated?this._t("estimatedNutrition"):"";
  return `<section class="rx-v67-nutrition">${title}<p class="muted">${escape(this._t(data.perServing?"perServing":"recipeTotal"))}${estimate?` · ${escape(estimate)}`:""}</p><div class="rx-v67-nutrient-list">${rows.join("")}</div>${data.coverage!==null?`<p class="muted">${escape(this._t("nutrientCoverage"))}: ${Math.round(data.coverage)}%</p>`:""}<p class="rx-v67-reference muted">${escape(this._t(data.perServing?"dailyReferenceHelp":"dailyReferenceUnknown"))}</p></section>`;
 }
 _v66BindRecipe(container,recipe,custom,slot=null,fullscreen=false){
  const state=this._v66State(recipe,slot?.id||"");
  container.querySelector('[data-v66-action="cook"]')?.addEventListener("click",event=>{
   event.stopImmediatePropagation();void this._v67Cook(recipe,custom,state,fullscreen);
  });
  container.querySelector('[data-v66-action="shopping"]')?.addEventListener("click",async event=>{
   event.stopImmediatePropagation();
   if(!recipe.ingredients?.length)await this._v66LoadRecipe(recipe,custom,state);
   if(state.error)return;
   const missing=this._missingIngredientObjects(recipe);
   if(missing?.length)await this._addShopping(missing);else this._message(this._t("noMissingIngredients"));
  });
  super._v66BindRecipe(container,recipe,custom,slot,fullscreen);
 }
 async _v66Translate(recipe,state){
  if(!this._v66LocalAiAvailable())return;
  if(!recipe.steps?.length)await this._v66LoadRecipe(recipe,!this._isOfficialRecipe(recipe),state);
  if(state.error)return;
  return super._v66Translate(recipe,state);
 }
 async _v67Cook(recipe,custom,state,fullscreen){
  if(fullscreen){state.cooking=!state.cooking;state.sections.add("steps");this._renderRecipeDialog();return;}
  await this._showRecipe(recipe,custom);
  if(!this._opened||this._recipeKey(this._opened)!==this._recipeKey(recipe))return;
  const opened=this._v66State(this._opened);opened.cooking=true;opened.step=state.step||0;opened.device=state.device;opened.sections=new Set(["steps"]);
  this._renderRecipeDialog();
 }
 _renderRecipeDialog(){
  super._renderRecipeDialog();
  const overlay=this._v63RecipeDialog;if(!overlay||!this._opened)return;
  const state=this._v66State(this._opened);overlay.toggleAttribute("data-v67-cooking",Boolean(state.cooking));
  const photo=overlay.querySelector(".rx-v66-full-photo");
  if(photo){
   const side=document.createElement("div");side.className="rx-v67-photo-side";photo.before(side);side.appendChild(photo);
   const actions=document.createElement("div");actions.className="rx-v67-photo-actions";
   overlay.querySelectorAll(".rx-v66-actions").forEach(group=>actions.appendChild(group));side.appendChild(actions);
  }
  this._ensureV67Styles();overlay._v67Highlighted=null;this._v66Highlight(overlay,this._opened,state);
 }
 _v66Highlight(container,recipe,state){
  super._v66Highlight(container,recipe,state);
  if(container.hasAttribute("data-v67-cooking")){
   const current=container.querySelector('[aria-current="step"]');
   if(current&&container._v67Highlighted!==current.dataset.v66Step){container._v67Highlighted=current.dataset.v66Step;current.scrollIntoView?.({block:"nearest"});}
  }
 }
 _renderTabs(){
  super._renderTabs();const week=this.shadowRoot?.querySelector('[data-tab="week"]');
  if(week)week.innerHTML=`${CALENDAR}<span>${this._escape(this._t("week"))}</span>`;
  this._ensureV67Styles();
 }
 _v67Today(now=new Date()){
  const parts=new Intl.DateTimeFormat("en-CA",{timeZone:this._hass?.config?.time_zone||undefined,year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(now);
  const part=type=>parts.find(row=>row.type===type).value;
  return `${part("year")}-${part("month")}-${part("day")}`;
 }
 _v67Days(){
  const today=this._v67Today();return Array.from({length:7},(_,offset)=>{const date=new Date(`${today}T12:00:00Z`);date.setUTCDate(date.getUTCDate()+offset);return date.toISOString().slice(0,10);});
 }
 _renderWeek(c){
  const days=this._v67Days(),key=this._v66PageKey("week"),original=this._weekState;
  const projected=original?{...original,weekStart:days[0],weekEnd:days[6],slots:(original.slots||[]).filter(row=>days.includes(row.date))}:{weekStart:days[0],weekEnd:days[6],slots:[],settings:{}};
  if(original?.weekStart!==days[0])projected.weeklyCostByCurrency={};
  this._weekState=projected;this._v66Limits??=new Map();const limit=this._v66Limits.get(key);this._v66Limits.set(key,Number.MAX_SAFE_INTEGER);
  try{super._renderWeek(c);}finally{this._weekState=original;if(limit===undefined)this._v66Limits.delete(key);else this._v66Limits.set(key,limit);}
  // Replace the legacy browser-timezone/Monday calendar with seven HA-local dates.
  const grid=c.querySelector(".rx-week-grid");
  if(grid){grid.innerHTML=days.map(stamp=>this._weekDayHtml(stamp)).join("");this._bindCards(grid,[]);
   grid.querySelectorAll("[data-slot-id]").forEach(node=>{const slot=original?.slots?.find(row=>row.id===node.dataset.slotId),recipe=slot?.recipe||this._leftoverById(slot?.leftoverId)?.recipe;
    if(recipe)node.addEventListener("click",event=>{if(!event.target.closest("button,input,select,a"))void this._showRecipe(recipe,!this._isOfficialRecipe(recipe));});});}
  c.querySelector("#generateWeek")?.closest(".toolbar")?.querySelector(".muted")?.replaceChildren(document.createTextNode(`${days[0]} – ${days[6]} · ${this._t("weeklyCost")}: ${this._money(projected.weeklyCostByCurrency)}`));
  const heading=c.querySelector("h2");if(heading)heading.textContent=this._t("nextSevenDays");
  this._v67RenderedDay=days[0];this._ensureV67Styles();
  const loaded=`${this._prefKey()}:${days[0]}`;
  if(this._entryId&&!this._weekLoading&&this._v67WeekLoaded!==loaded)queueMicrotask(()=>void this._loadWeekState());
 }
 _weekDayHtml(stamp){
  const date=new Date(`${stamp}T12:00:00Z`),label=new Intl.DateTimeFormat(this._hass?.language||"en",{weekday:"long",day:"2-digit",month:"2-digit",timeZone:"UTC"}).format(date);
  const slots=(this._weekState?.slots||[]).filter(row=>row.date===stamp),cards=[];
  for(const slot of slots){const recipe=slot.recipe||this._leftoverById(slot.leftoverId)?.recipe;if(!recipe)continue;
   this._v66Slot=slot;try{const card=this._recipeCard(recipe,!this._isOfficialRecipe(recipe));if(card)cards.push(`<div class="rx-week-slot" data-slot-id="${this._escape(slot.id)}"><h4>${this._escape(this._t(slot.mealType||"dinner"))}</h4>${card}</div>`);}finally{this._v66Slot=null;}
  }
  return `<section class="rx-week-day" data-week-date="${stamp}" ${stamp===this._v67Today()?'aria-current="date"':""}><h3>${this._escape(label)}</h3>${cards.join("")||`<p class="muted rx-v67-empty-day">${this._escape(this._t("noPlannedMeal"))}</p>`}</section>`;
 }
 async _loadWeekState(){
  if(this._weekLoading||!this._entryId)return;
  const key=this._prefKey(),entry=this._entryId,day=this._v67Today();this._weekLoading=true;this._v67WeekLoaded=`${key}:${day}`;
  try{const state=await this._api("cook4me/v20/week_state",{entry_id:entry,history_days:30});if(key!==this._prefKey())return;this._weekState=state;this._weekStateEntry=entry;}
  catch(error){if(key===this._prefKey())this._message(`${this._t("error")}: ${error.message||error}`,true);}
  finally{this._weekLoading=false;if(this._tab==="week")this._renderTab();}
 }
 async _api(type,data={}){
  if(type.endsWith("/week_generate"))data={...data,week_start:this._v67Today()};
  return super._api(type,data);
 }
 _updateHeader(){super._updateHeader();if(this._tab==="week"&&this._v67RenderedDay!==this._v67Today())this._renderTab();}
 _renderTab(){const result=super._renderTab();this.setAttribute("data-cook4me-build",BUILD);this._ensureV67Styles();return result;}
 _ensureV67Styles(){
  if(!this.shadowRoot||this.shadowRoot.getElementById("cook4meV67Styles"))return;
  const style=document.createElement("style");style.id="cook4meV67Styles";style.textContent=`
   .rx-v67-photo-actions{padding:12px 14px 2px}.rx-v67-photo-actions .rx-v66-actions{margin:0 0 8px;gap:8px}.rx-v66-title{padding-top:8px}.rx-v66-body .chip,.rx-v66-recipe .chip{display:inline-flex;white-space:nowrap;line-height:1.4}.rx-v66-body .chips,.rx-v66-recipe .chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
   [data-v66-section=info]>.rx-v66-section{display:flex;flex-direction:column;gap:24px;padding:16px 0}.rx-v66-section>div>strong{display:block;margin-bottom:8px}.rx-v67-nutrition{margin:0}.rx-v67-nutrition h4{margin:0 0 8px;font-size:1rem}.rx-v67-nutrition p{margin:8px 0 12px;line-height:1.5}.rx-v67-nutrient-list{display:flex;flex-direction:column;gap:10px}.rx-v67-nutrient{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 12px;padding:12px;border:1px solid var(--divider-color);border-radius:10px;background:var(--secondary-background-color)}.rx-v67-nutrient strong{white-space:nowrap}.rx-v67-nutrient small{grid-column:1/-1;color:var(--secondary-text-color)}.rx-v67-reference{font-size:.8rem}
   .tab[data-tab=week] svg[data-v67-week-icon]{display:inline-block!important;flex:0 0 24px;width:24px!important;height:24px!important;min-width:24px;opacity:1!important;visibility:visible!important;color:currentColor;vertical-align:middle}.tab[data-tab=week]::before,.tab[data-tab=week]::after{content:none!important}
   .rx-week-grid{grid-template-columns:repeat(7,minmax(0,1fr))!important;gap:12px}.rx-week-day{min-width:0}.rx-week-day>h3{font-size:1rem;min-height:2.7em;line-height:1.4}.rx-week-day[aria-current=date]>h3{color:var(--primary-color)}.rx-week-day .rx-v66-photo img.cover{height:145px}.rx-week-day .rx-v66-title{padding:8px}.rx-week-day .rx-v66-title h3{font-size:.95rem}.rx-week-day .rx-v66-title h3 span{display:block}.rx-week-day .rx-v67-photo-actions{padding:10px 8px 0}.rx-week-day .rx-v66-icon{min-width:36px!important;width:36px;height:36px;padding:6px!important}.rx-v67-empty-day{min-height:80px;border:1px dashed var(--divider-color);border-radius:12px;padding:12px}
   .rx-v66-fullscreen.rx-dialog{display:flex!important;flex-direction:column;height:100dvh!important;overflow:hidden!important}.rx-v66-fullscreen header{flex:0 0 auto}.rx-v66-fullscreen #recipeDetail{flex:1;min-height:0;width:100%;box-sizing:border-box;overflow:hidden}.rx-v66-fullscreen .rx-v66-body{overflow:auto;min-height:0;padding:0 5px 16px}.rx-v67-photo-side{min-height:0;overflow:auto}.rx-v66-fullscreen .rx-v67-photo-actions{padding:12px 0}.rx-v66-fullscreen .rx-v66-full-photo img{max-height:48dvh}.rx-v66-fullscreen .rx-v66-full-photo .media{height:auto!important;min-height:0!important}.rx-v66-fullscreen .rx-v66-steps .step{line-height:1.6;font-size:1.05rem}
   @media(max-width:1150px){.rx-week-grid{grid-template-columns:repeat(3,minmax(0,1fr))!important}}@media(max-width:700px){.rx-week-grid{grid-template-columns:1fr!important}.rx-week-day .rx-v66-photo img.cover{height:200px}.rx-v66-fullscreen #recipeDetail{display:flex;flex-direction:column;padding:10px;gap:12px}.rx-v67-photo-side{flex:0 0 auto;max-height:38dvh}.rx-v66-fullscreen .rx-v66-full-photo img{max-height:20dvh}.rx-v66-fullscreen .rx-v66-body{flex:1}.rx-v66-fullscreen .rx-v67-photo-actions .rx-v66-icon{width:36px;min-width:36px!important;height:36px;padding:6px!important}.rx-v66-fullscreen header h2{font-size:1rem}}
  `;this.shadowRoot.appendChild(style);
 }
}
customElements.define("cook4me-recipe-hub-panel-v67",Cook4MeRecipeHubPanelV67);
