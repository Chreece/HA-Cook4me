import {dietReplacementLabel} from './diet-substitution-guard-v253.js';

const TEXT={
 en:{
  title:'Diet substitutions',
  help:'These replacement candidates belong to this catalog ingredient. Recipes mount only the candidates compatible with the selected diet and active exclusions.',
  diets:'Compatible diets',
  contexts:'Uses',
  components:'Made from'
 },
 de:{
  title:'Ernährungsersatz',
  help:'Diese Ersatzkandidaten gehören zu dieser Katalogzutat. Rezepte übernehmen nur Kandidaten, die zur gewählten Ernährung und den aktiven Ausschlüssen passen.',
  diets:'Geeignete Ernährungsformen',
  contexts:'Verwendung',
  components:'Besteht aus'
 },
 el:{
  title:'Διατροφικές αντικαταστάσεις',
  help:'Αυτές οι εναλλακτικές ανήκουν σε αυτό το υλικό καταλόγου. Οι συνταγές χρησιμοποιούν μόνο όσες είναι συμβατές με την επιλεγμένη διατροφή και τους ενεργούς αποκλεισμούς.',
  diets:'Συμβατές διατροφές',
  contexts:'Χρήσεις',
  components:'Αποτελείται από'
 }
};

export const IngredientSubstitutionInfoMixin=Base=>class extends Base{
 _v253SubInfoText(key){
  const lang=String(this._uiIngredientLanguage?.()||this._langCode?.()||'en').split(/[-_]/)[0];
  return (TEXT[lang]||TEXT.en)[key]||TEXT.en[key]||key;
 }
 _v253SubstitutionLabel(row){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return dietReplacementLabel(row?.key,lang,row?.name||row?.key||'');
 }
 _v253SubstitutionRows(ingredient){
  const info=this._v66IngredientInfo;
  const rows=info?.catalogSubstitutions||info?.ingredient?.substitutions||ingredient?.substitutions||[];
  return Array.isArray(rows)?rows.filter(row=>row&&typeof row==='object'):[];
 }
 _v253DecorateIngredientSubstitutions(ingredient){
  const overlay=this.shadowRoot?.querySelector?.('[data-ingredient-dialog]');
  const dialog=overlay?.querySelector?.('.rx-dialog');
  if(!dialog||dialog.querySelector('[data-v253-ingredient-substitutions]'))return;
  const rows=this._v253SubstitutionRows(ingredient);
  if(!rows.length)return;

  const section=document.createElement('section');
  section.dataset.v253IngredientSubstitutions='';
  const heading=document.createElement('h3');heading.textContent=this._v253SubInfoText('title');
  const help=document.createElement('p');help.className='muted';help.textContent=this._v253SubInfoText('help');
  const list=document.createElement('div');list.className='v253-sub-info-list';
  section.append(heading,help,list);

  for(const row of rows){
   const card=document.createElement('article');card.className='v253-sub-info-card';
   card.dataset.v253SubstitutionKey=String(row.key||'');
   const title=document.createElement('strong');title.textContent=this._v253SubstitutionLabel(row);
   card.append(title);

   const meta=document.createElement('div');meta.className='v253-sub-info-meta';
   const diets=Array.isArray(row.compatibleDiets)?row.compatibleDiets.filter(Boolean):[];
   if(diets.length){
    const span=document.createElement('span');
    span.textContent=`${this._v253SubInfoText('diets')}: ${diets.join(', ')}`;
    meta.append(span);
   }
   const contexts=Array.isArray(row.contexts)?row.contexts.filter(Boolean):[];
   if(contexts.length){
    const span=document.createElement('span');
    span.textContent=`${this._v253SubInfoText('contexts')}: ${contexts.join(', ')}`;
    meta.append(span);
   }
   if(meta.childNodes.length)card.append(meta);

   const components=Array.isArray(row.components)?row.components:[];
   if(components.length){
    const wrap=document.createElement('div');wrap.className='v253-sub-info-components';
    const label=document.createElement('small');label.textContent=this._v253SubInfoText('components');
    const ul=document.createElement('ul');
    for(const component of components){
     const target=component?.target||{};
     const li=document.createElement('li');
     const amount=[component?.quantity,component?.unit].filter(value=>value!==undefined&&value!==null&&String(value).trim()).join(' ');
     li.textContent=`${amount?amount+' · ':''}${target.canonicalName||target.name||target.ingredientId||''}`;
     ul.append(li);
    }
    wrap.append(label,ul);card.append(wrap);
   }
   list.append(card);
  }

  const stock=dialog.querySelector('[data-v249-stock-assignment]');
  const usage=overlay.querySelector('[data-use]')?.closest('section');
  dialog.insertBefore(section,stock||usage||null);
  this._v253SubInfoStyles();
 }
 async _showIngredientInfo(ingredient,recipe){
  const result=await super._showIngredientInfo(ingredient,recipe);
  this._v253DecorateIngredientSubstitutions(ingredient);
  return result;
 }
 _v253SubInfoStyles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v253SubInfoStyles'))return;
  const style=document.createElement('style');style.id='v253SubInfoStyles';style.textContent=`
   [data-v253-ingredient-substitutions]{border-top:1px solid var(--divider-color);padding-top:12px}
   .v253-sub-info-list{display:grid;gap:8px}
   .v253-sub-info-card{padding:10px 12px;border:1px solid var(--divider-color);border-radius:10px;background:var(--secondary-background-color,var(--card-background-color))}
   .v253-sub-info-card>strong{display:block;margin-bottom:5px}
   .v253-sub-info-meta{display:flex;flex-wrap:wrap;gap:6px 12px;color:var(--secondary-text-color);font-size:12px}
   .v253-sub-info-components{margin-top:7px}
   .v253-sub-info-components small{font-weight:600}
   .v253-sub-info-components ul{margin:4px 0 0;padding-left:20px}
  `;this.shadowRoot.append(style);
 }
};
