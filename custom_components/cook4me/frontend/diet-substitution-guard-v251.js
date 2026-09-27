import {
  DietSubstitutionGuardMixin as DietSubstitutionGuardMixinV250,
  dietAdaptation,
} from './diet-substitution-guard-v250.js';

export {dietAdaptation};

const LABELS={
 en:{
  mushroom_stock:'Mushroom stock',oat_cream:'Oat cream',soy_cream:'Soy cream',coconut_cream:'Coconut cream',
  oat_milk:'Oat milk',soy_milk:'Soy milk',rice_milk:'Rice milk',soy_yogurt:'Soy yogurt',
  coconut_yogurt:'Coconut yogurt',soy_sauce:'Soy sauce',coconut_aminos:'Coconut aminos',
  agar:'Agar-agar',microbial_rennet:'Microbial rennet',bentonite:'Food-grade bentonite',
  soy_cheese:'Soy-based plant cheese',cashew_cheese:'Cashew-based plant cheese',
  nutritional_yeast:'Nutritional yeast',flax_egg:'Flax egg',
  aquafaba:'Aquafaba (chickpea brine)',pea_protein:'Pea protein',
 },
 de:{
  mushroom_stock:'Pilzbrühe',oat_cream:'Hafercreme',soy_cream:'Sojacreme',coconut_cream:'Kokoscreme',
  oat_milk:'Hafermilch',soy_milk:'Sojamilch',rice_milk:'Reismilch',soy_yogurt:'Sojajoghurt',
  coconut_yogurt:'Kokosjoghurt',soy_sauce:'Sojasauce',coconut_aminos:'Kokos-Aminos',
  agar:'Agar-Agar',microbial_rennet:'Mikrobielles Lab',bentonite:'Lebensmitteltaugliches Bentonit',
  soy_cheese:'Pflanzlicher Sojakäse',cashew_cheese:'Pflanzlicher Cashewkäse',
  nutritional_yeast:'Hefeflocken',flax_egg:'Leinsamen-Ei',
  aquafaba:'Aquafaba (Kichererbsenwasser)',pea_protein:'Erbsenprotein',
 },
 el:{
  mushroom_stock:'Ζωμός μανιταριών',oat_cream:'Κρέμα βρώμης',soy_cream:'Κρέμα σόγιας',coconut_cream:'Κρέμα καρύδας',
  oat_milk:'Γάλα βρώμης',soy_milk:'Γάλα σόγιας',rice_milk:'Γάλα ρυζιού',soy_yogurt:'Γιαούρτι σόγιας',
  coconut_yogurt:'Γιαούρτι καρύδας',soy_sauce:'Σάλτσα σόγιας',coconut_aminos:'Αμινοξέα καρύδας',
  agar:'Άγαρ-άγαρ',microbial_rennet:'Μικροβιακή πυτιά',bentonite:'Βρώσιμος μπεντονίτης',
  soy_cheese:'Φυτικό τυρί σόγιας',cashew_cheese:'Φυτικό τυρί από κάσιους',
  nutritional_yeast:'Διατροφική μαγιά',flax_egg:'Αυγό λιναρόσπορου',
  aquafaba:'Ακουαφάμπα (νερό ρεβιθιών)',pea_protein:'Πρωτεΐνη αρακά',
 },
};

export function dietReplacementLabel(key,language='en',fallback=''){
 const code=String(language||'en').toLowerCase().replace('_','-').split('-',1)[0];
 return (LABELS[code]||LABELS.en)[key]||LABELS.en[key]||fallback||'';
}

export const DietSubstitutionGuardMixin=Base=>class extends DietSubstitutionGuardMixinV250(Base){
 _v76Text(key){
  const lang=this._uiIngredientLanguage?.()||this._langCode?.()||'en';
  return dietReplacementLabel(key,lang)||super._v76Text(key);
 }
};
