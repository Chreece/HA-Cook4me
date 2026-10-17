// Navigate from the live cooker to the EXACT loaded recipe edition. Never
// resolve a recipe by its title or infer another step's program from text.
import {MODE_TEXT,stepCookingModes} from './recipe-step-modes-v259.js';

const str=value=>typeof value==='string'?value.trim():'';
const isObj=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const langCode=value=>{
 const code=str(value).toLowerCase().split(/[-_]/)[0];
 return MODE_TEXT[code]?code:'en';
};
const LABELS={
 en:{open:'Open loaded recipe fullscreen',live:'Live cooker program',recipe:'Recipe'},
 de:{open:'Geladenes Rezept im Vollbild öffnen',live:'Aktuelles Geräteprogramm',recipe:'Rezept'},
 el:{open:'Άνοιγμα φορτωμένης συνταγής σε πλήρη οθόνη',live:'Τρέχον πρόγραμμα συσκευής',recipe:'Συνταγή'},
 fr:{open:'Ouvrir la recette chargée en plein écran',live:'Programme actuel de l’appareil',recipe:'Recette'},
};

export function loadedRecipeTarget(entry,view){
 if(view?.live!==true||entry?.accessible===false)return null;
 const state=view.state;
 if(!isObj(state))return null;
 const variant=str(state.variantFunctionalId);
 // Names are not unique. Without an explicit live variant identity the
 // apparent title must remain read-only, not open a guessed recipe.
 if(!variant)return null;
 const title=str(state.recipeTitle)||str(entry?.loadedRecipe?.title)||'';
 return {variant,title};
}

export function loadedRecipeStep(recipe,entry){
 if(!isObj(recipe)||!Array.isArray(recipe.steps)||!recipe.steps.length||entry?.accessible===false||entry?.connected!==true)return -1;
 const state=entry.state;
 if(!isObj(state))return -1;
 const liveVariant=str(state.variantFunctionalId);
 if(!liveVariant)return -1;
 const displayed=[recipe.displayVariantId,recipe.selectedDisplayVariantId,recipe.searchVariantId,recipe.variantFunctionalId]
  .map(str).filter(Boolean);
 if(!displayed.includes(liveVariant))return -1;
 const stepId=str(state.stepFunctionalId);
 if(stepId){
  // Step ID is stronger evidence than positional index. If it disagrees,
  // never label a different recipe step using the current device program.
  return recipe.steps.findIndex(row=>str(row?.functionalId||row?.stepFunctionalId)===stepId);
 }
 const index=Number(state.stepIndex);
 if(state.stepIndex===null||state.stepIndex===undefined||state.stepIndex===''||!Number.isInteger(index)||index<0)return -1;
 return recipe.steps.findIndex((row,pos)=>Number(row?.stepIndex??pos)===index);
}

export function liveModeForRecipeStep(recipe,entry,index,language='en'){
 if(loadedRecipeStep(recipe,entry)!==index)return null;
 const programName=str(entry.state?.programName);
 if(!programName)return null;
 const mode=stepCookingModes({programName},langCode(language))[0];
 return mode?.mode?{...mode,source:'live_device',sourceName:programName}:null;
}

export const LoadedDeviceRecipeMixin=Base=>class extends Base{
 _v284Text(key){
  const code=langCode(this._langCode?.()||'en');
  return LABELS[code]?.[key]||LABELS.en[key]||key;
 }
 _v81RenderInfo(...args){
  const result=super._v81RenderInfo(...args);
  const dialog=this._v81InfoDialog,view=this._v81View?.(),entry=this._entry?.();
  const target=loadedRecipeTarget(entry,view);
  if(!dialog?.isConnected||!target)return result;
  const details=dialog.querySelector('[data-v81-details]');
  const dt=[...details?.querySelectorAll('dt')||[]]
   .find(node=>node.textContent===this._v81Text('recipe'));
  const cell=dt?.nextElementSibling;
  if(cell?.tagName!=='DD')return result;
  const old=cell.querySelector('[data-v284-loaded-recipe]');
  // _v81RenderInfo caches the canonical row HTML, so the same button survives
  // regular device subscriptions and retains keyboard focus.
  if(old?.dataset.variant===target.variant&&old?.textContent===(target.title||this._v284Text('recipe')))return result;
  const button=document.createElement('button');
  button.type='button';button.className='v284-loaded-recipe';
  button.dataset.v284LoadedRecipe='';
  button.dataset.variant=target.variant;
  button.textContent=target.title||this._v284Text('recipe');
  button.setAttribute('aria-label',this._v284Text('open')+': '+button.textContent);
  button.title=this._v284Text('open');
  const entryId=this._entryId,scope=this._prefKey?.(),user=this._hass?.user?.id;
  const open=()=>{
   const current=loadedRecipeTarget(this._entry?.(),this._v81View?.());
   if(!current||current.variant!==target.variant||entryId!==this._entryId||scope!==this._prefKey?.()||user!==this._hass?.user?.id)return;
   this._v81CloseInfo();
   // The existing official recipe path loads exact-detail data and opens the
   // established fullscreen (nutrition, steps, controls, active-step sync).
   void this._showRecipe({
    title:current.title||target.title,
    displayVariantId:current.variant,
    searchVariantId:current.variant,
    variantFunctionalId:current.variant,
   },false);
  };
  button.addEventListener('click',open);
  cell.replaceChildren(button);
  this._v284Styles();
  return result;
 }
 _v66Body(recipe,...args){
  const html=super._v66Body(recipe,...args);
  if(!html||!Array.isArray(recipe?.steps)||!recipe.steps.length)return html;
  const entry=this._entry?.();
  const index=loadedRecipeStep(recipe,entry);
  if(index<0)return html;
  const sourceMode=liveModeForRecipeStep(recipe,entry,index,this._langCode?.()||'en');
  if(!sourceMode)return html;
  const doc=this.ownerDocument||globalThis.document;
  if(!doc?.createElement)return html;
  const holder=doc.createElement('template');
  holder.innerHTML=html;
  const step=holder.content.querySelector('[data-v66-step="'+index+'"]');
  if(!step)return html;
  const content=step.querySelector(':scope > span:not(.step-num)');
  if(!content)return html;
  let meta=content.querySelector('[data-v204-step-modes]');
  const chips=[...(meta?.querySelectorAll('[data-v204-mode]')||[])];
  // Never overwrite a known source program or a multi-operation sequence.
  if(chips.length>1||chips.some(chip=>!['source','missing'].includes(chip.dataset.v204Mode)))return html;
  const code=langCode(this._langCode?.()||'en');
  const labels=MODE_TEXT[code];
  if(!meta){
   meta=doc.createElement('span');
   meta.dataset.v204StepModes='';
   meta.className='v204-step-modes';
   const title=doc.createElement('span');
   title.className='v204-mode-label';title.textContent=labels.label;
   meta.append(title);
   const list=doc.createElement('span');list.className='v204-mode-list';meta.append(list);
   content.prepend(meta);
  }
  const list=meta.querySelector('.v204-mode-list');
  if(!list)return html;
  const chip=doc.createElement('span');
  chip.className='v204-mode-chip';
  chip.dataset.v204Mode=sourceMode.mode;
  chip.dataset.v284LiveMode='';
  chip.title=this._v284Text('live')+': '+sourceMode.sourceName;
  const icon=doc.createElement('ha-icon');
  icon.setAttribute('icon','mdi:pot-steam');
  icon.setAttribute('aria-hidden','true');
  const text=doc.createElement('span');text.textContent=sourceMode.label;
  chip.append(icon,text);
  list.replaceChildren(chip);
  meta.title=this._v284Text('live');
  step.classList.add('v204-program-step');
  content.classList.add('v204-step-content');
  return holder.innerHTML;
 }
 _v284Styles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v284DeviceRecipeStyles'))return;
  const style=document.createElement('style');
  style.id='v284DeviceRecipeStyles';
  style.textContent='.v284-loaded-recipe{border:0;background:none;padding:0;color:var(--primary-color);'+
   'font:inherit;font-weight:650;text-align:start;text-decoration:underline;'+
   'text-underline-offset:3px;cursor:pointer;max-width:100%;overflow-wrap:anywhere}'+
   '.v284-loaded-recipe:hover{text-decoration-thickness:2px}'+
   '.v284-loaded-recipe:focus-visible{outline:2px solid var(--primary-color);'+
   'outline-offset:4px;border-radius:3px}';
  this.shadowRoot.append(style);
 }
};
