import {IngredientSubstitutionInfoMixin as IngredientSubstitutionInfoMixinV253} from './ingredient-substitution-info-v253.js';
import {dietReplacementLabel} from './diet-substitution-guard-v254.js';

const TEXT={
 en:{
  title:'Diet & allergy substitutions',
  help:'These reviewed replacement candidates belong to this catalog ingredient. Recipes mount only candidates compatible with the selected diet and active exclusions.',
  diets:'Compatible diets',contexts:'Uses',components:'Made from',
  allergies:'Used for exclusions',caution:'For allergies, verify the exact packaged-product label and cross-contact information before use.'
 },
 de:{
  title:'Ernährungs- & Allergieersatz',
  help:'Diese geprüften Ersatzkandidaten gehören zu dieser Katalogzutat. Rezepte übernehmen nur Kandidaten, die zur gewählten Ernährung und den aktiven Ausschlüssen passen.',
  diets:'Geeignete Ernährungsformen',contexts:'Verwendung',components:'Besteht aus',
  allergies:'Für Ausschlüsse',caution:'Bei Allergien immer das Etikett des konkreten Produkts und Hinweise zu Kreuzkontakten prüfen.'
 },
 el:{
  title:'Αντικαταστάσεις διατροφής & αλλεργιών',
  help:'Αυτές οι ελεγμένες εναλλακτικές ανήκουν σε αυτό το υλικό καταλόγου. Οι συνταγές χρησιμοποιούν μόνο όσες είναι συμβατές με την επιλεγμένη διατροφή και τους ενεργούς αποκλεισμούς.',
  diets:'Συμβατές διατροφές',contexts:'Χρήσεις',components:'Αποτελείται από',
  allergies:'Για αποκλεισμούς',caution:'Για αλλεργίες, ελέγχετε πάντα την ετικέτα του συγκεκριμένου προϊόντος και τις πληροφορίες για πιθανή διασταυρούμενη επαφή.'
 }
};

const ALLERGENS={
 en:{gluten:'gluten',milk:'milk',lactose:'lactose',egg:'egg',fish:'fish',shellfish:'shellfish',peanut:'peanut',tree_nut:'tree nuts',soy:'soy',sesame:'sesame',celery:'celery',mustard:'mustard',sulfites:'sulfites',lupin:'lupin'},
 de:{gluten:'Gluten',milk:'Milch',lactose:'Laktose',egg:'Ei',fish:'Fisch',shellfish:'Krusten-/Schalentiere',peanut:'Erdnuss',tree_nut:'Schalenfrüchte',soy:'Soja',sesame:'Sesam',celery:'Sellerie',mustard:'Senf',sulfites:'Sulfite',lupin:'Lupine'},
 el:{gluten:'γλουτένη',milk:'γάλα',lactose:'λακτόζη',egg:'αυγό',fish:'ψάρι',shellfish:'οστρακοειδή/μαλάκια',peanut:'αράπικο φιστίκι',tree_nut:'ξηροί καρποί',soy:'σόγια',sesame:'σουσάμι',celery:'σέλινο',mustard:'μουστάρδα',sulfites:'θειώδη',lupin:'λούπινο'}
};

export const IngredientSubstitutionInfoMixin=Base=>class extends IngredientSubstitutionInfoMixinV253(Base){
 _v253SubInfoText(key){
  const lang=String(this._uiIngredientLanguage?.()||this._langCode?.()||'en').split(/[-_]/)[0];
  return (TEXT[lang]||TEXT.en)[key]||TEXT.en[key]||key;
 }
 _v253SubstitutionLabel(row){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return dietReplacementLabel(row?.key,lang,row?.name||row?.key||'');
 }
 _v253DecorateIngredientSubstitutions(ingredient){
  super._v253DecorateIngredientSubstitutions(ingredient);
  const section=this.shadowRoot?.querySelector?.('[data-v253-ingredient-substitutions]');
  if(!section||section.dataset.v254AllergyInfo!==undefined)return;
  section.dataset.v254AllergyInfo='';
  const info=this._v66IngredientInfo;
  const triggers=info?.catalogSubstitutionAllergens||info?.ingredient?.substitutionAllergens||ingredient?.substitutionAllergens||[];
  const rows=Array.isArray(triggers)?[...new Set(triggers.filter(Boolean).map(value=>String(value).toLowerCase()))]:[];
  const lang=String(this._uiIngredientLanguage?.()||this._langCode?.()||'en').split(/[-_]/)[0];
  const list=section.querySelector('.v253-sub-info-list');
  if(rows.length){
   const trigger=document.createElement('p');
   trigger.className='muted v254-sub-allergies';
   const labels=ALLERGENS[lang]||ALLERGENS.en;
   trigger.textContent=`${this._v253SubInfoText('allergies')}: ${rows.map(key=>labels[key]||key.replaceAll('_',' ')).join(', ')}`;
   section.insertBefore(trigger,list||null);
  }
  if(rows.length){
   const warning=document.createElement('p');
   warning.className='v254-sub-warning';
   warning.textContent=this._v253SubInfoText('caution');
   section.insertBefore(warning,list||null);
  }
  this._v254SubInfoStyles();
 }
 _v254SubInfoStyles(){
  if(!this.shadowRoot||this.shadowRoot.querySelector('#v254SubInfoStyles'))return;
  const style=document.createElement('style');style.id='v254SubInfoStyles';style.textContent=`
   .v254-sub-allergies{margin:6px 0}
   .v254-sub-warning{margin:6px 0 10px;padding:8px 10px;border-radius:9px;border:1px solid var(--warning-color,#b7791f);background:color-mix(in srgb,var(--warning-color,#b7791f) 10%,var(--card-background-color));font-size:12px;line-height:1.4}
  `;this.shadowRoot.append(style);
 }
};
