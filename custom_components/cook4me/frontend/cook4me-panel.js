const LANG = {
  en: {
    official:"Official recipes", recommend:"For my fridge", mine:"My recipes", profile:"Pantry & diet", ai:"AI recipe",
    search:"Search", searchPlaceholder:"Search SEB/Cook4Me recipes…", loading:"Loading…", send:"Send to Cook4Me",
    loaded:"A recipe/session is already loaded. Exit it on the Cook4Me before sending another recipe.", disconnected:"Cook4Me is offline.",
    ingredients:"Ingredients", missing:"Missing", coverage:"Pantry match", steps:"Steps", save:"Save", delete:"Delete", create:"Create recipe",
    title:"Title", servings:"Servings", pantry:"What I have", diet:"Diet", allergies:"Allergies", avoid:"Avoid/dislike", preferences:"Preferences",
    omnivore:"Omnivore", pescatarian:"Pescatarian", vegetarian:"Vegetarian", vegan:"Vegan", recommendBtn:"Find recipes I can make", safe:"Fits profile", blocked:"Excluded by profile",
    aiPrompt:"What should the AI make?", aiGenerate:"Generate with HA AI", aiAgent:"AI / Conversation agent", noAgent:"Configure an AI conversation agent in Home Assistant to generate recipes.",
    customNoSend:"Manual and AI recipes are cook-along recipes in Home Assistant. The proven Wi-Fi Cook4Me route only accepts official SEB recipe IDs.",
    current:"Current Cook4Me", connected:"Connected", offline:"Offline", free:"Ready for a recipe", busy:"Recipe loaded", refresh:"Refresh",
    ingredientsHelp:"One ingredient per line (or comma-separated).", listHelp:"One item per line or comma-separated.", manualIngredients:"Ingredients (one per line)", manualSteps:"Steps (one per line)", notes:"Notes",
    generateSaved:"AI recipe generated and saved to My recipes.", error:"Error", noResults:"No recipes found.", source:"Source", cookAlong:"Cook along", habitMatch:"Matches habits", learnedHabits:"Learned ranking hints from recipe sends",
  },
  de: {
    official:"Offizielle Rezepte", recommend:"Für meinen Kühlschrank", mine:"Meine Rezepte", profile:"Vorrat & Ernährung", ai:"KI-Rezept",
    search:"Suchen", searchPlaceholder:"SEB/Cook4Me-Rezepte suchen…", loading:"Lädt…", send:"An Cook4Me senden",
    loaded:"Auf dem Cook4Me ist bereits ein Rezept/eine Sitzung geladen. Beende es zuerst am Gerät.", disconnected:"Cook4Me ist offline.",
    ingredients:"Zutaten", missing:"Fehlt", coverage:"Vorrat passt", steps:"Schritte", save:"Speichern", delete:"Löschen", create:"Rezept erstellen",
    title:"Titel", servings:"Portionen", pantry:"Was ich da habe", diet:"Ernährung", allergies:"Allergien", avoid:"Meiden / mag ich nicht", preferences:"Vorlieben",
    omnivore:"Alles", pescatarian:"Pescetarisch", vegetarian:"Vegetarisch", vegan:"Vegan", recommendBtn:"Passende Rezepte finden", safe:"Passt zum Profil", blocked:"Vom Profil ausgeschlossen",
    aiPrompt:"Was soll die KI kochen?", aiGenerate:"Mit HA-KI generieren", aiAgent:"KI-/Conversation-Agent", noAgent:"Richte einen KI-Conversation-Agent in Home Assistant ein, um Rezepte zu generieren.",
    customNoSend:"Manuelle und KI-Rezepte sind Cook-along-Rezepte in Home Assistant. Der nachgewiesene Wi-Fi-Weg akzeptiert nur offizielle SEB-Rezept-IDs.",
    current:"Aktueller Cook4Me", connected:"Verbunden", offline:"Offline", free:"Bereit für ein Rezept", busy:"Rezept geladen", refresh:"Aktualisieren",
    ingredientsHelp:"Eine Zutat pro Zeile (oder mit Komma trennen).", listHelp:"Ein Eintrag pro Zeile oder kommagetrennt.", manualIngredients:"Zutaten (eine pro Zeile)", manualSteps:"Schritte (einer pro Zeile)", notes:"Notizen",
    generateSaved:"KI-Rezept erzeugt und unter Meine Rezepte gespeichert.", error:"Fehler", noResults:"Keine Rezepte gefunden.", source:"Quelle", cookAlong:"Mitkochen", habitMatch:"Passt zu Gewohnheiten", learnedHabits:"Gelernte Ranking-Hinweise aus gesendeten Rezepten",
  },
  el: {
    official:"Επίσημες συνταγές", recommend:"Για ό,τι έχω στο ψυγείο", mine:"Οι συνταγές μου", profile:"Υλικά & διατροφή", ai:"Συνταγή με AI",
    search:"Αναζήτηση", searchPlaceholder:"Αναζήτηση συνταγών SEB/Cook4Me…", loading:"Φόρτωση…", send:"Αποστολή στο Cook4Me",
    loaded:"Υπάρχει ήδη φορτωμένη συνταγή/συνεδρία στο Cook4Me. Βγες πρώτα από αυτή στη συσκευή.", disconnected:"Το Cook4Me είναι offline.",
    ingredients:"Υλικά", missing:"Λείπουν", coverage:"Κάλυψη ντουλαπιού", steps:"Βήματα", save:"Αποθήκευση", delete:"Διαγραφή", create:"Δημιουργία συνταγής",
    title:"Τίτλος", servings:"Μερίδες", pantry:"Τι έχω", diet:"Διατροφή", allergies:"Αλλεργίες", avoid:"Αποφυγή / δεν μου αρέσει", preferences:"Προτιμήσεις",
    omnivore:"Παμφάγος", pescatarian:"Ψαροφαγική", vegetarian:"Χορτοφαγική", vegan:"Vegan", recommendBtn:"Βρες τι μπορώ να φτιάξω", safe:"Ταιριάζει στο προφίλ", blocked:"Αποκλείεται από το προφίλ",
    aiPrompt:"Τι να φτιάξει το AI;", aiGenerate:"Δημιουργία με HA AI", aiAgent:"AI / Conversation agent", noAgent:"Ρύθμισε έναν AI conversation agent στο Home Assistant για δημιουργία συνταγών.",
    customNoSend:"Οι χειροκίνητες/AI συνταγές λειτουργούν ως cook-along στο Home Assistant. Το αποδεδειγμένο Wi-Fi route του Cook4Me δέχεται μόνο επίσημα SEB recipe IDs.",
    current:"Τρέχον Cook4Me", connected:"Συνδεδεμένο", offline:"Offline", free:"Έτοιμο για συνταγή", busy:"Έχει φορτωμένη συνταγή", refresh:"Ανανέωση",
    ingredientsHelp:"Ένα υλικό ανά γραμμή (ή χωρισμένα με κόμμα).", listHelp:"Μία τιμή ανά γραμμή ή με κόμμα.", manualIngredients:"Υλικά (ένα ανά γραμμή)", manualSteps:"Βήματα (ένα ανά γραμμή)", notes:"Σημειώσεις",
    generateSaved:"Η AI συνταγή δημιουργήθηκε και αποθηκεύτηκε στις συνταγές μου.", error:"Σφάλμα", noResults:"Δεν βρέθηκαν συνταγές.", source:"Πηγή", cookAlong:"Μαγείρεμα μαζί", habitMatch:"Ταιριάζει στις συνήθειες", learnedHabits:"Μαθημένες προτιμήσεις κατάταξης από συνταγές που στάλθηκαν",
  },
};

class Cook4MeRecipeHubPanel extends HTMLElement {
  constructor(){
    super();
    this.attachShadow({mode:"open"});
    this._hass=null; this._entries=[]; this._entryId=null; this._tab="official"; this._busy=false; this._results=[]; this._recommendations=[]; this._opened=null;
    this._lastOverviewRefresh=0; this._overviewLoading=false; this._agents=[]; this._agentsLoaded=false; this._agentsLoading=false;
  }
  set hass(value){
    this._hass=value;
    if(!this.shadowRoot.innerHTML) this._renderShell(); else this._updateHeader();
    const now=Date.now();
    if(this.isConnected&&this._entryId&&now-this._lastOverviewRefresh>5000&&!this._overviewLoading){
      this._lastOverviewRefresh=now;
      void this._loadOverview(true,false);
    }
  }
  get hass(){ return this._hass; }
  set panel(value){ this._panel=value; }
  connectedCallback(){ if(this._hass){ this._renderShell(); this._loadOverview(); } }
  _language(){ const code=String(this._hass?.language||"en").toLowerCase().split(/[-_]/)[0]; return LANG[code]||LANG.en; }
  _t(k){ return this._language()[k]||k; }
  _escape(value){ return String(value??"").replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c])); }
  async _api(type,data={}){ if(!this._hass) throw new Error("Home Assistant unavailable"); return this._hass.connection.sendMessagePromise({type,...data}); }
  _entry(){ return this._entries.find(e=>e.entry_id===this._entryId)||this._entries[0]||null; }
  _splitList(text){ return [...new Set(String(text||"").replace(/,/g,"\n").split(/\r?\n/).map(x=>x.trim()).filter(Boolean))]; }
  _renderShell(){
    if(!this.shadowRoot) return;
    this.shadowRoot.innerHTML=`<style>
      :host{display:block;color:var(--primary-text-color);background:var(--primary-background-color);min-height:100%;font-family:var(--paper-font-body1_-_font-family,Roboto,sans-serif)}
      *{box-sizing:border-box}.wrap{max-width:1400px;margin:0 auto;padding:18px}.top{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:start}
      .card{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:16px;padding:16px}.status{display:flex;gap:14px;align-items:center;min-width:0}
      .pot{font-size:30px}.status-main{min-width:0}.status-title{font-size:21px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.muted{color:var(--secondary-text-color);font-size:13px}.ok{color:var(--success-color,#43a047)}.warn{color:var(--warning-color,#f9a825)}.bad{color:var(--error-color,#db4437)}
      button,select,input,textarea{font:inherit}.btn{border:0;border-radius:10px;padding:10px 14px;min-height:42px;background:var(--primary-color);color:var(--text-primary-color,#fff);cursor:pointer}.btn.secondary{background:var(--secondary-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color)}.btn.danger{background:var(--error-color,#db4437)}.btn:disabled{opacity:.45;cursor:not-allowed}
      .tabs{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}.tab{background:transparent;color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:999px;padding:9px 14px;cursor:pointer}.tab.active{background:var(--primary-color);color:var(--text-primary-color,#fff);border-color:var(--primary-color)}
      .toolbar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}.field{display:flex;flex-direction:column;gap:6px;min-width:0}.field label{font-size:13px;color:var(--secondary-text-color)}input,select,textarea{background:var(--card-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:10px;padding:10px;min-height:42px}textarea{min-height:110px;resize:vertical}.grow{flex:1 1 260px}
      .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:14px}.recipe{display:flex;flex-direction:column;gap:10px;min-width:0}.cover{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:12px;background:var(--secondary-background-color)}.recipe h3{margin:0;font-size:18px}.chips{display:flex;flex-wrap:wrap;gap:6px}.chip{font-size:12px;padding:4px 8px;border-radius:999px;background:var(--secondary-background-color)}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:auto}.ingredients{font-size:13px;line-height:1.45}.missing{color:var(--warning-color,#f9a825)}
      .two{display:grid;grid-template-columns:1fr 1fr;gap:14px}.formgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.wide{grid-column:1/-1}.notice{padding:11px 13px;border-left:4px solid var(--primary-color);background:var(--secondary-background-color);border-radius:8px;margin-bottom:12px}.error{border-left-color:var(--error-color,#db4437)}
      .detail{margin-top:14px}.step{padding:10px 0;border-top:1px solid var(--divider-color)}.step:first-child{border-top:0}.empty{padding:28px;text-align:center;color:var(--secondary-text-color)}
      @media(max-width:700px){.wrap{padding:10px}.top,.two,.formgrid{grid-template-columns:1fr}.wide{grid-column:auto}.toolbar .btn{width:100%}.grid{grid-template-columns:1fr}}
    </style><div class="wrap">
      <div class="top"><div id="status" class="card"></div><div class="toolbar"><select id="entrySelect" aria-label="Cook4Me"></select><button id="refresh" class="btn secondary">${this._escape(this._t("refresh"))}</button></div></div>
      <div class="tabs" id="tabs"></div><div id="message"></div><main id="content"></main>
    </div>`;
    this.shadowRoot.getElementById("refresh").addEventListener("click",()=>this._loadOverview(true));
    this.shadowRoot.getElementById("entrySelect").addEventListener("change",e=>{this._entryId=e.target.value; this._results=[]; this._recommendations=[]; this._opened=null; this._renderTabs(); this._renderTab(); this._updateHeader();});
    this._renderTabs(); this._renderTab();
  }
  _renderTabs(){ const el=this.shadowRoot?.getElementById("tabs"); if(!el)return; const tabs=[["official","official"],["recommend","recommend"],["mine","mine"],["profile","profile"],["ai","ai"]]; el.innerHTML=tabs.map(([id,k])=>`<button class="tab ${this._tab===id?"active":""}" data-tab="${id}">${this._escape(this._t(k))}</button>`).join(""); el.querySelectorAll("[data-tab]").forEach(b=>b.addEventListener("click",()=>{this._tab=b.dataset.tab;this._opened=null;this._renderTabs();this._renderTab();})); }
  _message(text,err=false){ const el=this.shadowRoot?.getElementById("message"); if(el) el.innerHTML=text?`<div class="notice ${err?"error":""}">${this._escape(text)}</div>`:""; }
  async _loadOverview(silent=false,rerender=true){
    if(this._overviewLoading)return;
    this._overviewLoading=true;
    try{
      if(!silent)this._setBusy(true);
      const res=await this._api("cook4me/overview");
      this._entries=res?.entries||[];
      if(!this._entryId||!this._entries.some(e=>e.entry_id===this._entryId))this._entryId=this._entries[0]?.entry_id||null;
      this._lastOverviewRefresh=Date.now();
      this._renderEntrySelect(); this._updateHeader();
      if(rerender)this._renderTab();
      if(!silent)this._message("");
    }catch(e){if(!silent)this._message(`${this._t("error")}: ${e.message||e}`,true)}
    finally{this._overviewLoading=false;if(!silent)this._setBusy(false);}
  }
  _renderEntrySelect(){ const el=this.shadowRoot?.getElementById("entrySelect"); if(!el)return; el.innerHTML=this._entries.map(e=>`<option value="${this._escape(e.entry_id)}" ${e.entry_id===this._entryId?"selected":""}>${this._escape(e.title||"Cook4Me")}</option>`).join(""); el.style.display=this._entries.length>1?"block":"none"; }
  _updateHeader(){ const el=this.shadowRoot?.getElementById("status"); if(!el)return; const e=this._entry(); if(!e){el.innerHTML=`<div class="empty">Cook4Me integration not loaded.</div>`;return;} const s=e.state||{}; const recipe=s.recipeTitle||e.loadedRecipe?.title; const state=s.phase||s.status||"idle"; el.innerHTML=`<div class="status"><div class="pot">🍲</div><div class="status-main"><div class="status-title">${this._escape(e.title||this._t("current"))}</div><div><span class="${e.connected?"ok":"bad"}">${this._escape(e.connected?this._t("connected"):this._t("offline"))}</span> · <span class="${e.canAcceptRecipe?"ok":"warn"}">${this._escape(e.canAcceptRecipe?this._t("free"):this._t("busy"))}</span></div><div class="muted">${this._escape(recipe?`${state} · ${recipe}`:state)}${s.currentInstruction?` · ${this._escape(s.currentInstruction)}`:""}</div></div></div>`; }
  _setBusy(v){ this._busy=v; }
  _renderTab(){ const c=this.shadowRoot?.getElementById("content"); if(!c)return; if(this._tab==="official")this._renderOfficial(c); else if(this._tab==="recommend")this._renderRecommend(c); else if(this._tab==="mine")this._renderMine(c); else if(this._tab==="profile")this._renderProfile(c); else this._renderAI(c); }
  _recipeCard(r,custom=false){ const m=r.match||{}; const coverage=Number.isFinite(Number(m.pantryCoverage))?Math.round(Number(m.pantryCoverage)*100):null; const ingredients=(r.ingredients||[]).slice(0,6).map(x=>typeof x==="string"?x:(x.applicationDescription||x.name||x.foodName)).filter(Boolean); const canSend=!custom&&r.sendable!==false&&this._entry()?.canAcceptRecipe&&m.safe!==false; const reason=m.safe===false?this._t("blocked"):(!this._entry()?.connected?this._t("disconnected"):(this._entry()?.loadedRecipe?this._t("loaded"):"")); const source=custom?(r.source||"manual"):"SEB"; return `<article class="card recipe" data-recipe="${this._escape(r.id||r.searchVariantId||r.variantFunctionalId||"")}">${r.cover?`<img class="cover" src="${this._escape(r.cover)}" alt="">`:""}<h3>${this._escape(r.title||r.searchVariantId||"Recipe")}</h3><div class="chips"><span class="chip">${this._escape(source)}</span>${m.dietary?.pescatarian&&!m.dietary?.vegetarian?`<span class="chip">🐟 ${this._t("pescatarian")}</span>`:""}${m.dietary?.vegetarian?`<span class="chip">🌱 ${this._t("vegetarian")}</span>`:""}${m.dietary?.vegan?`<span class="chip">🌿 ${this._t("vegan")}</span>`:""}${coverage!==null?`<span class="chip">${this._t("coverage")}: ${coverage}%</span>`:""}${m.habitHits?.length?`<span class="chip">♥ ${this._t("habitMatch")}</span>`:""}${m.safe===false?`<span class="chip bad">${this._t("blocked")}</span>`:""}</div>${ingredients.length?`<div class="ingredients"><strong>${this._t("ingredients")}:</strong> ${ingredients.map(x=>this._escape(x)).join(", ")}</div>`:""}${m.missingIngredients?.length?`<div class="ingredients missing"><strong>${this._t("missing")}:</strong> ${m.missingIngredients.slice(0,5).map(x=>this._escape(x)).join(", ")}</div>`:""}<div class="actions"><button class="btn secondary" data-action="open">${this._t(custom?"cookAlong":"steps")}</button>${custom?`<button class="btn danger" data-action="delete">${this._t("delete")}</button>`:`<button class="btn" data-action="send" ${canSend?"":`disabled title="${this._escape(reason)}"`}>${this._t("send")}</button>`}</div></article>`; }
  _bindCards(container,items,custom=false){ container.querySelectorAll(".recipe").forEach((card,i)=>{ const r=items[i]; card.querySelector('[data-action="open"]')?.addEventListener("click",()=>custom?this._openLocal(r):this._openOfficial(r)); card.querySelector('[data-action="send"]')?.addEventListener("click",()=>this._send(r)); card.querySelector('[data-action="delete"]')?.addEventListener("click",()=>this._deleteRecipe(r)); }); }
  _openLocal(r){this._opened=r;this._renderTab();}
  async _openOfficial(r){
    const variant=r.searchVariantId||r.variantFunctionalId||r.recipeFunctionalId;
    if(!variant){this._opened=r;this._renderTab();return;}
    if(Array.isArray(r.steps)&&r.steps.length){this._opened=r;this._renderTab();return;}
    try{this._message(this._t("loading"));const detail=await this._api("cook4me/recipe_detail",{entry_id:this._entryId,variant_id:String(variant)});this._opened=detail;this._message("");this._renderTab();}
    catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}
  }
  _detailHtml(r){ if(!r)return""; const ingredients=r.ingredients||[]; const steps=r.steps||[]; return `<section class="card detail"><h2>${this._escape(r.title||"Recipe")}</h2>${r.source&&r.source!=="sebplatform_mobile_recipe"?`<div class="notice">${this._escape(this._t("customNoSend"))}</div>`:""}<h3>${this._t("ingredients")}</h3><ul>${ingredients.map(x=>`<li>${this._escape(typeof x==="string"?x:[x.quantity,x.unit,x.name||x.applicationDescription].filter(v=>v!==undefined&&v!==null&&v!=="").join(" "))}</li>`).join("")}</ul><h3>${this._t("steps")}</h3>${steps.map((s,i)=>`<div class="step"><strong>${i+1}.</strong> ${this._escape(typeof s==="string"?s:(s.instruction||s.text||""))}</div>`).join("")}${r.notes?`<p>${this._escape(r.notes)}</p>`:""}</section>`; }
  _renderOfficial(c){ c.innerHTML=`<section class="card"><div class="toolbar"><input id="searchQ" class="grow" placeholder="${this._escape(this._t("searchPlaceholder"))}"><button id="searchBtn" class="btn">${this._t("search")}</button></div></section><div id="recipeGrid" class="grid" style="margin-top:14px"></div>${this._detailHtml(this._opened)}`; c.querySelector("#searchBtn").addEventListener("click",()=>this._search(c.querySelector("#searchQ").value)); c.querySelector("#searchQ").addEventListener("keydown",e=>{if(e.key==="Enter")this._search(e.target.value)}); const g=c.querySelector("#recipeGrid"); if(this._results.length){g.innerHTML=this._results.map(r=>this._recipeCard(r,false)).join("");this._bindCards(g,this._results,false);} }
  async _search(q){ try{this._message(this._t("loading"));const res=await this._api("cook4me/search",{entry_id:this._entryId,query:q||"",size:20});this._results=res.items||[];this._message("");this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)} }
  _renderRecommend(c){ c.innerHTML=`<section class="card"><div class="notice">${this._escape(this._t("ingredientsHelp"))}</div><button id="recommendBtn" class="btn">${this._t("recommendBtn")}</button></section><div id="recipeGrid" class="grid" style="margin-top:14px"></div>${this._detailHtml(this._opened)}`; c.querySelector("#recommendBtn").addEventListener("click",()=>this._recommend()); const g=c.querySelector("#recipeGrid"); if(this._recommendations.length){g.innerHTML=this._recommendations.map(r=>this._recipeCard(r,false)).join("");this._bindCards(g,this._recommendations,false);} }
  async _recommend(){try{this._message(this._t("loading"));const res=await this._api("cook4me/recommend",{entry_id:this._entryId,limit:12,catalog_size:18});this._recommendations=res.items||[];this._message("");this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}}
  async _send(r){ try{const variant=r.searchVariantId||r.variantFunctionalId||r.recipeFunctionalId;if(!variant)throw new Error("Missing official recipe ID");this._message(this._t("loading"));await this._api("cook4me/send_recipe",{entry_id:this._entryId,variant_id:String(variant)});this._message(`${this._t("send")}: ${r.title||variant}`);await this._loadOverview(true);}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)} }
  _renderMine(c){ const items=this._entry()?.recipes||[]; c.innerHTML=`<div class="two"><section class="card"><h2>${this._t("create")}</h2><div class="formgrid"><div class="field wide"><label>${this._t("title")}</label><input id="manualTitle"></div><div class="field"><label>${this._t("servings")}</label><input id="manualServings" type="number" min="1" step="1"></div><div class="field wide"><label>${this._t("manualIngredients")}</label><textarea id="manualIngredients"></textarea></div><div class="field wide"><label>${this._t("manualSteps")}</label><textarea id="manualSteps"></textarea></div><div class="field wide"><label>${this._t("notes")}</label><textarea id="manualNotes"></textarea></div></div><button id="manualSave" class="btn">${this._t("save")}</button></section><section><div id="mineGrid" class="grid"></div></section></div>${this._detailHtml(this._opened)}`; c.querySelector("#manualSave").addEventListener("click",()=>this._saveManual()); const g=c.querySelector("#mineGrid"); if(items.length){g.innerHTML=items.map(r=>this._recipeCard(r,true)).join("");this._bindCards(g,items,true);}else g.innerHTML=`<div class="empty">${this._t("noResults")}</div>`; }
  async _saveManual(){ const c=this.shadowRoot.getElementById("content"); const recipe={title:c.querySelector("#manualTitle").value,servings:c.querySelector("#manualServings").value,ingredients:this._splitList(c.querySelector("#manualIngredients").value),steps:this._splitList(c.querySelector("#manualSteps").value),notes:c.querySelector("#manualNotes").value}; try{await this._api("cook4me/recipe_save",{entry_id:this._entryId,recipe,source:"manual"});await this._loadOverview(true);this._tab="mine";this._renderTabs();this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)} }
  async _deleteRecipe(r){try{await this._api("cook4me/recipe_delete",{entry_id:this._entryId,recipe_id:r.id});this._opened=null;await this._loadOverview(true);}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)}}
  _renderProfile(c){ const e=this._entry()||{}; const p=e.profile||{}; const join=x=>(x||[]).join("\n"); const habits=e.habitTerms||[]; c.innerHTML=`<section class="card"><div class="formgrid"><div class="field"><label>${this._t("diet")}</label><select id="diet"><option value="omnivore">${this._t("omnivore")}</option><option value="pescatarian">${this._t("pescatarian")}</option><option value="vegetarian">${this._t("vegetarian")}</option><option value="vegan">${this._t("vegan")}</option></select></div><div></div><div class="field wide"><label>${this._t("pantry")}</label><textarea id="pantry">${this._escape(join(p.pantry))}</textarea><span class="muted">${this._t("ingredientsHelp")}</span></div><div class="field"><label>${this._t("allergies")}</label><textarea id="allergies">${this._escape(join(p.allergies))}</textarea></div><div class="field"><label>${this._t("avoid")}</label><textarea id="avoid">${this._escape(join(p.avoid))}</textarea></div><div class="field wide"><label>${this._t("preferences")}</label><textarea id="preferences">${this._escape(join(p.preferences))}</textarea></div>${habits.length?`<div class="field wide"><label>${this._t("learnedHabits")}</label><div class="chips">${habits.map(x=>`<span class="chip">♥ ${this._escape(x)}</span>`).join("")}</div></div>`:""}</div><button id="profileSave" class="btn">${this._t("save")}</button></section>`; c.querySelector("#diet").value=p.diet||"omnivore"; c.querySelector("#profileSave").addEventListener("click",()=>this._saveProfile()); }
  async _saveProfile(){ const c=this.shadowRoot.getElementById("content"); const profile={diet:c.querySelector("#diet").value,pantry:this._splitList(c.querySelector("#pantry").value),allergies:this._splitList(c.querySelector("#allergies").value),avoid:this._splitList(c.querySelector("#avoid").value),preferences:this._splitList(c.querySelector("#preferences").value)}; try{await this._api("cook4me/profile_save",{entry_id:this._entryId,profile});await this._loadOverview(true);this._message(this._t("save"));}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)} }
  _renderAI(c){
    if(!this._agentsLoaded&&!this._agentsLoading)void this._loadAgents();
    const agents=this._agents||[];
    const body=this._agentsLoading&&!this._agentsLoaded
      ? `<div class="empty">${this._t("loading")}</div>`
      : agents.length
        ? `<div class="field"><label>${this._t("aiAgent")}</label><select id="aiAgent">${agents.map(a=>`<option value="${this._escape(a.id)}">${this._escape(a.name||a.id)}</option>`).join("")}</select></div><div class="field" style="margin-top:12px"><label>${this._t("aiPrompt")}</label><textarea id="aiPrompt" placeholder="e.g. quick mushroom risotto, high protein, 4 portions"></textarea></div><button id="aiGenerate" class="btn" style="margin-top:12px">${this._t("aiGenerate")}</button>`
        : `<div class="empty">${this._t("noAgent")}</div>`;
    c.innerHTML=`<section class="card"><div class="notice">${this._escape(this._t("customNoSend"))}</div>${body}</section>${this._detailHtml(this._opened)}`;
    c.querySelector("#aiGenerate")?.addEventListener("click",()=>this._generateAI());
  }
  async _loadAgents(){
    if(this._agentsLoading)return; this._agentsLoading=true;
    try{const res=await this._api("conversation/agent/list",{language:this._hass?.language||"en"});this._agents=res?.agents||[];this._agentsLoaded=true;}
    catch(_e){this._agents=[];this._agentsLoaded=true;}
    finally{this._agentsLoading=false;if(this._tab==="ai")this._renderTab();}
  }
  _extractAIJson(text){ let s=String(text||"").trim(); const fence=s.match(/```(?:json)?\s*([\s\S]*?)```/i); if(fence)s=fence[1].trim(); const start=s.indexOf("{"); const end=s.lastIndexOf("}"); if(start>=0&&end>start)s=s.slice(start,end+1); return JSON.parse(s); }
  async _generateAI(){ const c=this.shadowRoot.getElementById("content"); const agent=c.querySelector("#aiAgent")?.value; const request=c.querySelector("#aiPrompt")?.value?.trim(); if(!agent||!request)return; const p=this._entry()?.profile||{}; const prompt=`Create one Cook4Me-friendly recipe. User request: ${request}\nDiet: ${p.diet||"omnivore"}\nAllergies: ${(p.allergies||[]).join(", ")||"none"}\nAvoid: ${(p.avoid||[]).join(", ")||"none"}\nAvailable pantry/fridge ingredients: ${(p.pantry||[]).join(", ")||"not specified"}.\nReturn ONLY valid JSON with this schema: {"title":"...","servings":4,"ingredients":[{"name":"...","quantity":1,"unit":"..."}],"steps":[{"instruction":"..."}],"notes":"","tags":["..."]}. Never include an allergen or avoided ingredient. Do not claim the recipe can be uploaded to the appliance.`; try{this._message(this._t("loading"));const resp=await this._api("conversation/process",{text:prompt,language:this._hass.language||"en",agent_id:agent});const speech=resp?.response?.speech?.plain?.speech||resp?.response?.speech?.ssml?.speech||resp?.speech?.plain?.speech||"";const recipe=this._extractAIJson(speech);const saved=await this._api("cook4me/recipe_save",{entry_id:this._entryId,recipe,source:"ai"});this._opened=saved;await this._loadOverview(true);this._opened=saved;this._message(this._t("generateSaved"));this._renderTab();}catch(e){this._message(`${this._t("error")}: ${e.message||e}`,true)} }
}

customElements.define("cook4me-recipe-hub-panel",Cook4MeRecipeHubPanel);
