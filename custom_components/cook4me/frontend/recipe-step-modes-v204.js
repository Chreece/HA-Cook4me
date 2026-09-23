// Display recipe program evidence, never infer a mode from instruction prose.
export const MODE_TEXT={
 en:{label:'Cooking mode',help:'Mode specified by this recipe step, not the device’s live status.',unknown:'Cooking mode not specified',source:'Source program',pressure:'Pressure cooking',high_pressure:'High-pressure cooking',low_pressure:'Low-pressure cooking',browning:'Browning',steam:'Steaming',simmering:'Simmering',gentle:'Gentle cooking',reheat:'Reheating',keep_warm:'Keep warm',slow:'Slow cooking',quick:'Quick cooking',preheat:'Preheating',preparation:'Preparation',serving:'Serving'},
 de:{label:'Garmodus',help:'Modus dieses Rezeptschritts, nicht der aktuelle Gerätestatus.',unknown:'Garmodus nicht angegeben',source:'Originalprogramm',pressure:'Druckgaren',high_pressure:'Garen unter hohem Druck',low_pressure:'Garen unter niedrigem Druck',browning:'Anbraten',steam:'Dampfgaren',simmering:'Köcheln',gentle:'Schonendes Garen',reheat:'Aufwärmen',keep_warm:'Warmhalten',slow:'Langsames Garen',quick:'Schnellgaren',preheat:'Vorheizen',preparation:'Vorbereitung',serving:'Servieren'},
 el:{label:'Λειτουργία μαγειρέματος',help:'Λειτουργία που ορίζει αυτό το βήμα της συνταγής, όχι η τρέχουσα κατάσταση της συσκευής.',unknown:'Δεν ορίζεται λειτουργία μαγειρέματος',source:'Αρχικό πρόγραμμα',pressure:'Μαγείρεμα υπό πίεση',high_pressure:'Μαγείρεμα σε υψηλή πίεση',low_pressure:'Μαγείρεμα σε χαμηλή πίεση',browning:'Ρόδισμα / σοτάρισμα',steam:'Μαγείρεμα στον ατμό',simmering:'Σιγανό βράσιμο',gentle:'Ήπιο μαγείρεμα',reheat:'Αναθέρμανση',keep_warm:'Διατήρηση θερμοκρασίας',slow:'Αργό μαγείρεμα',quick:'Γρήγορο μαγείρεμα',preheat:'Προθέρμανση',preparation:'Προετοιμασία',serving:'Σερβίρισμα'},
 fr:{label:'Mode de cuisson',help:'Mode indiqué pour cette étape de la recette, pas l’état actuel de l’appareil.',unknown:'Mode de cuisson non précisé',source:'Programme original',pressure:'Cuisson sous pression',high_pressure:'Cuisson sous haute pression',low_pressure:'Cuisson sous basse pression',browning:'Dorer',steam:'Cuisson vapeur',simmering:'Mijoter',gentle:'Cuisson douce',reheat:'Réchauffer',keep_warm:'Maintien au chaud',slow:'Cuisson lente',quick:'Cuisson rapide',preheat:'Préchauffage',preparation:'Préparation',serving:'Service'}
};
const object=value=>!!value&&typeof value==='object'&&!Array.isArray(value);
const text=value=>typeof value==='string'?value.trim():'';
const normalize=value=>text(value).normalize('NFKD').replace(/\p{M}/gu,'').toLowerCase().replace(/ς/g,'σ').replace(/[_-]+/g,' ').replace(/\s+/g,' ').trim();
const aliases=new Map();
for(const mode of ['pressure','high_pressure','low_pressure','browning','steam','simmering','gentle','reheat','keep_warm','slow','quick','preheat']){
 for(const words of Object.values(MODE_TEXT))aliases.set(normalize(words[mode]),mode);
}
for(const [mode,names] of Object.entries({
 pressure:['pressure cook','garen unter druck','cottura a pressione','cocción a presión'],
 high_pressure:['high pressure','haute pression','cuisson sous pression haute'],
 low_pressure:['low pressure','basse pression','cuisson sous pression basse'],
 browning:['brown','sauté','sauteing','sautéing','rissoler','σοτάρισμα','ρόδισμα'],
 steam:['steam','steam cooking','vapeur'],
 simmering:['simmer','simmern','mijotage'],gentle:['gentle cooking','sanftes garen'],
 reheat:['reheat','réchauffage','réchauffement','reheating'],
 keep_warm:['keeping warm','warm halten','maintenir au chaud'],
 preheat:['preheat'],slow:['slow cook']
}))for(const name of names)aliases.set(normalize(name),mode);

function strings(language){return MODE_TEXT[String(language||'en').toLowerCase().split(/[-_]/)[0]]||MODE_TEXT.en;}
function validProgram(row){
 if(!object(row))return false;
 const group=object(row.applianceGroup)?text(row.applianceGroup.key):text(row.applianceGroup);
 return (!group||group==='APPLIANCE_GROUP_15')&&!!(text(row.programName)||text(row.programKey));
}
export function stepCookingModes(step,language='en'){
 const labels=strings(language),row=object(step)?step:{};
 // New normalized sequences are authoritative, including an empty list. The
 // flattened fields remain supported for previously saved recipe details.
 const programs=Array.isArray(row.programs)?row.programs.filter(validProgram):validProgram(row)?[row]:[];
 if(programs.length)return programs.map(program=>{
  const sourceName=text(program.programName),programKey=text(program.programKey);
  const mode=aliases.get(normalize(sourceName||programKey))||null;
  return {kind:mode?'program':sourceName?'source':'missing',mode,
   label:mode?labels[mode]:sourceName||labels.unknown,sourceName,programKey};
 });
 // A preparation type is not an automatic device program. Generic cooking or
 // opaque STEP_TYPE identifiers cannot establish which mode will be used.
 const type=normalize(row.typeName|| (object(row.type)?row.type.name:row.type));
 for(const mode of ['preparation','serving'])if(Object.values(MODE_TEXT).some(words=>normalize(words[mode])===type)){
  return [{kind:'manual',mode,label:labels[mode],sourceName:'',programKey:''}];
 }
 return [{kind:'missing',mode:null,label:labels.unknown,sourceName:'',programKey:''}];
}

export function decorateStepModes(root,recipe,language='en'){
 if(!root||!Array.isArray(recipe?.steps))return;
 const labels=strings(language);
 for(const node of root.querySelectorAll('[data-v66-step]')){
  const index=Number(node.dataset.v66Step);
  if(!Number.isInteger(index)||index<0||index>=recipe.steps.length)continue;
  // Shared renderer uses original array positions, not the displayed step number.
  // Do not replace the instruction span or any of its existing handlers.
  const content=node.querySelector(':scope > span:not(.step-num)');if(!content)continue;
  node.classList.add('v204-program-step');content.classList.add('v204-step-content');
  content.querySelector(':scope > [data-v204-step-modes]')?.remove();
  const meta=document.createElement('span');meta.className='v204-step-modes';meta.dataset.v204StepModes='';meta.title=labels.help;
  const label=document.createElement('span');label.className='v204-mode-label';label.textContent=labels.label;meta.append(label);
  const modes=document.createElement('span');modes.className='v204-mode-list';meta.append(modes);
  for(const [position,mode] of stepCookingModes(recipe.steps[index],language).entries()){
   if(position){const arrow=document.createElement('span');arrow.className='v204-mode-arrow';arrow.textContent='→';modes.append(arrow);}
   const chip=document.createElement('span');chip.className='v204-mode-chip';chip.dataset.v204Mode=mode.mode||mode.kind;
   const glyph=document.createElement('ha-icon');glyph.setAttribute('icon',mode.kind==='manual'?'mdi:hand-back-right-outline':mode.kind==='missing'?'mdi:help-circle-outline':'mdi:pot-steam');glyph.setAttribute('aria-hidden','true');
   const name=document.createElement('span');name.textContent=mode.label;chip.append(glyph,name);
   const evidence=[mode.sourceName,mode.programKey].filter(Boolean).join(' · ');
   if(evidence)chip.title=labels.source+': '+evidence;
   modes.append(chip);
  }
  content.prepend(meta);
 }
}
export const STEP_MODE_CSS=`
 .rx-v66-steps .step.v204-program-step{display:flex;align-items:flex-start;gap:12px}
 .v204-program-step>.step-num{flex:0 0 auto}.v204-step-content{display:block;min-width:0;flex:1;overflow-wrap:anywhere}
 .v204-step-modes{display:flex;flex-direction:column;align-items:flex-start;gap:5px;margin:0 0 9px;white-space:normal;max-width:100%}
 .v204-mode-label{font-size:.75rem;line-height:1.4;color:var(--secondary-text-color);font-weight:500}
 .v204-mode-list{display:flex;flex-wrap:wrap;align-items:center;gap:6px;max-width:100%}
 .v204-mode-chip{display:inline-flex;align-items:center;gap:6px;max-width:100%;box-sizing:border-box;padding:5px 9px;border-radius:10px;border:1px solid var(--divider-color);background:color-mix(in srgb,var(--primary-color) 9%,var(--card-background-color));color:var(--primary-text-color);font-size:.85rem;font-weight:600;line-height:1.45;white-space:normal;overflow-wrap:anywhere}
 .v204-mode-chip ha-icon{--mdc-icon-size:17px;display:inline-flex;flex:0 0 17px}
 .v204-mode-chip[data-v204-mode=missing],.v204-mode-chip[data-v204-mode=preparation],.v204-mode-chip[data-v204-mode=serving]{background:var(--secondary-background-color,var(--card-background-color));font-weight:400}
 .v204-mode-arrow{color:var(--secondary-text-color)}
 @media(forced-colors:active){.v204-mode-chip{border-color:CanvasText}}
`;
export const RecipeStepModesMixin=Base=>class extends Base{
 _v66Body(recipe,...args){
  const html=super._v66Body(recipe,...args);
  if(!html||!Array.isArray(recipe?.steps)||!recipe.steps.length)return html;
  if(this.shadowRoot&&!this.shadowRoot.querySelector('#stepModesV204')){
   const style=document.createElement('style');style.id='stepModesV204';style.textContent=STEP_MODE_CSS;this.shadowRoot.append(style);
  }
  const holder=document.createElement('template');holder.innerHTML=html;
  decorateStepModes(holder.content,recipe,this._uiIngredientLanguage?.()||this._langCode?.()||'en');
  return holder.innerHTML;
 }
};
