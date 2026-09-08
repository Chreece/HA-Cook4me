import "./cook4me-panel-v45.js";

const BasePanel=customElements.get("cook4me-recipe-hub-panel-v45");

class Cook4MeRecipeHubPanelV46 extends BasePanel{
  _bulkSelectionState(c,group){
    if(group==="ingredients"){
      const options=[...(c.querySelector("#todayIngredients")?.options||[])];
      return {count:options.length,all:options.length>0&&options.every(option=>option.selected)};
    }
    const selector=group==="meals"?"[data-today-meal-type]":"[data-today-language]";
    const rows=[...c.querySelectorAll(selector)];
    return {count:rows.length,all:rows.length>0&&rows.every(row=>row.checked)};
  }

  _refreshBulkButton(c,group){
    const button=c.querySelector(`[data-today-bulk="${group}"]`);
    if(!button)return;
    const state=this._bulkSelectionState(c,group);
    const key=state.all?"deselectAll":"selectAll";
    const icon=state.all?"checkbox-multiple-blank-outline":"checkbox-multiple-marked-outline";
    const iconNode=button.querySelector("ha-icon");
    const label=button.querySelector("span");
    if(iconNode)iconNode.setAttribute("icon",`mdi:${icon}`);
    if(label)label.textContent=this._t(key);
  }

  _toggleTodayBulk(c,group){
    if(group==="ingredients"){
      const select=c.querySelector("#todayIngredients");
      if(!select)return;
      const options=[...select.options];
      const all=options.length>0&&options.every(option=>option.selected);
      options.forEach(option=>{option.selected=!all;});
    }else{
      const selector=group==="meals"?"[data-today-meal-type]":"[data-today-language]";
      const rows=[...c.querySelectorAll(selector)];
      const all=rows.length>0&&rows.every(row=>row.checked);
      rows.forEach(row=>{
        row.checked=!all;
        row.closest(".rx-choice-card")?.classList.toggle("selected",!all);
      });
    }

    // Persist and refresh only the affected controls. Re-rendering the whole
    // Today panel here used to destroy the open <details> picker.
    this._rememberTodayFromUi(c);
    this._refreshBulkButton(c,group);
    this._updateTodayPickerCounts?.(c);
    this._updateTodaySummary?.(c.querySelector(".rx-today-planner"));
  }

  _bindExplicitDetails(details){
    if(!details||details.dataset.cook4meExplicitToggle==="1")return;
    const summary=details.querySelector(":scope > summary");
    if(!summary)return;
    details.dataset.cook4meExplicitToggle="1";
    const sync=()=>summary.setAttribute("aria-expanded",details.hasAttribute("open")?"true":"false");
    sync();
    summary.addEventListener("click",event=>{
      event.preventDefault();
      const opening=!details.hasAttribute("open");
      if(opening){
        const row=details.closest(".rx-today-row");
        row?.querySelectorAll("details[open]").forEach(other=>{
          if(other!==details){
            other.removeAttribute("open");
            other.querySelector(":scope > summary")?.setAttribute("aria-expanded","false");
          }
        });
        details.setAttribute("open","");
      }else{
        details.removeAttribute("open");
      }
      sync();
    });
  }

  _ensureTodayMenuBehavior(c){
    c.querySelectorAll("details.rx-today-picker,details.rx-advanced").forEach(details=>this._bindExplicitDetails(details));
  }

  _renderToday(c){
    super._renderToday(c);
    this._ensureTodayMenuBehavior(c);
  }
}

customElements.define("cook4me-recipe-hub-panel-v46",Cook4MeRecipeHubPanelV46);
