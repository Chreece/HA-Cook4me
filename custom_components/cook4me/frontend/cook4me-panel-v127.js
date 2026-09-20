import './cook4me-panel-v126.js';
const BasePanel=customElements.get('cook4me-recipe-hub-panel-v126');
const AI_DEFAULT='__home_assistant_default__';
const WORDS={
 en:{
  defaultAi:'Default (Home Assistant)',
  defaultAiUnavailable:'Default (Home Assistant) · unavailable',
  aiAll:'Process all TTS announcements through AI',
  aiAllHint:'Translate when needed and improve spoken formatting before sending the text to the selected TTS service.'
 },
 de:{
  defaultAi:'Standard (Home Assistant)',
  defaultAiUnavailable:'Standard (Home Assistant) · nicht verfügbar',
  aiAll:'Alle TTS-Ansagen durch KI verarbeiten',
  aiAllHint:'Bei Bedarf übersetzen und die gesprochene Formulierung verbessern, bevor der Text an den ausgewählten TTS-Dienst gesendet wird.'
 },
 el:{
  defaultAi:'Προεπιλογή (Home Assistant)',
  defaultAiUnavailable:'Προεπιλογή (Home Assistant) · μη διαθέσιμη',
  aiAll:'Επεξεργασία όλων των ανακοινώσεων TTS μέσω AI',
  aiAllHint:'Μετάφραση όπου χρειάζεται και βελτίωση της μορφοποίησης για εκφώνηση πριν σταλεί το κείμενο στην επιλεγμένη υπηρεσία TTS.'
 }
};
class Cook4MeRecipeHubPanelV127 extends BasePanel{
 _v127Text(key){return (WORDS[this._langCode?.()]||WORDS.en)[key]||WORDS.en[key]||key;}
 _v127NormalizeAnnouncementDraft(){
  const draft=this._v72Draft,choices=this._v72Data?.choices||{};
  if(!draft)return;
  const selectedTts=(choices.tts||[]).find(row=>row.id===draft.tts);
  const languages=selectedTts?.languages||[];
  if(selectedTts&&!languages.includes(draft.language)){
   const preferred=languages.includes(selectedTts.defaultLanguage)?selectedTts.defaultLanguage:languages[0]||'';
   draft.language=preferred;
   draft.voice='';
  }
  if(draft.ai_all&&!draft.ai){
   if(choices.defaultAiTaskId)draft.ai=AI_DEFAULT;
   else if(choices.ai?.length)draft.ai=choices.ai[0].id;
  }
 }
 _v72RenderSettings(){
  this._v127NormalizeAnnouncementDraft();
  super._v72RenderSettings();
  const overlay=this._v72Dialog,draft=this._v72Draft,choices=this._v72Data?.choices||{};
  if(!overlay||!draft)return;
  const escape=value=>this._escape(String(value??''));
  const ai=overlay.querySelector('[data-setting="ai"]');
  if(ai){
   const rows=choices.ai||[],current=String(draft.ai||''),defaultId=String(choices.defaultAiTaskId||'');
   const defaultRow=rows.find(row=>row.id===defaultId);
   let html=`<option value="">${escape(this._v72Text('none'))}</option>`;
   if(defaultId){
    const suffix=defaultRow?.name?` · ${defaultRow.name}`:'';
    html+=`<option value="${AI_DEFAULT}" ${current===AI_DEFAULT?'selected':''}>${escape(this._v127Text('defaultAi')+suffix)}</option>`;
   }else if(current===AI_DEFAULT){
    html+=`<option value="${AI_DEFAULT}" selected disabled>${escape(this._v127Text('defaultAiUnavailable'))}</option>`;
   }
   html+=rows.map(row=>`<option value="${escape(row.id)}" ${current===row.id?'selected':''}>${escape(row.name||row.id)}</option>`).join('');
   if(current&&current!==AI_DEFAULT&&!rows.some(row=>row.id===current)){
    html+=`<option value="${escape(current)}" selected disabled>${escape(current)} (${escape(this._v72Text('unavailable'))})</option>`;
   }
   ai.innerHTML=html;
   if([...ai.options].some(option=>option.value===current))ai.value=current;
  }
  const selectedTts=(choices.tts||[]).find(row=>row.id===draft.tts);
  const language=overlay.querySelector('[data-setting="language"]');
  if(language&&selectedTts){
   const supported=new Set(selectedTts.languages||[]);
   [...language.options].forEach(option=>{if(!option.value||!supported.has(option.value))option.remove();});
   if(!supported.has(draft.language)){
    draft.language=supported.has(selectedTts.defaultLanguage)?selectedTts.defaultLanguage:(selectedTts.languages?.[0]||'');
    draft.voice='';
   }
   language.value=draft.language;
  }
  const fields=overlay.querySelector('.v72-fields');
  if(fields&&!fields.querySelector('[data-v127-ai-all]')){
   const label=document.createElement('label');
   label.className='v127-ai-all';
   label.dataset.v127AiAll='';
   label.innerHTML=`<span><input type="checkbox" data-v127-ai-all-input ${draft.ai_all?'checked':''}> <strong>${escape(this._v127Text('aiAll'))}</strong></span><small>${escape(this._v127Text('aiAllHint'))}</small>`;
   fields.append(label);
   label.querySelector('[data-v127-ai-all-input]').onchange=event=>{
    draft.ai_all=Boolean(event.target.checked);
    if(draft.ai_all&&!draft.ai){
     if(choices.defaultAiTaskId)draft.ai=AI_DEFAULT;
     else if(choices.ai?.length)draft.ai=choices.ai[0].id;
     this._v72RenderSettings();
     this._v72Dialog?.querySelector('[data-v127-ai-all-input]')?.focus();
    }
   };
  }
 }
 _renderProfile(container){
  super._renderProfile(container);
  const stock=container?.querySelector?.('#houseInventoryRows');
  if(stock?.parentElement?.tagName==='DETAILS')stock.parentElement.open=false;
 }
 _renderTab(){
  const result=super._renderTab();
  this._v127Styles();
  this.setAttribute('data-cook4me-build','2026.9.20.1');
  return result;
 }
 _v127Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v127Styles'))return;
  const style=document.createElement('style');
  style.id='v127Styles';
  style.textContent=`
   [data-device-settings] .v127-ai-all{grid-column:1/-1;display:grid;gap:6px;margin:4px 0 8px}
   [data-device-settings] .v127-ai-all>span{display:flex;align-items:center;gap:9px;color:var(--primary-text-color)}
   [data-device-settings] .v127-ai-all input{margin:0}
   [data-device-settings] .v127-ai-all small{padding-left:29px}
  `;
  this.shadowRoot.append(style);
 }
}
customElements.define('cook4me-recipe-hub-panel-v127',Cook4MeRecipeHubPanelV127);
