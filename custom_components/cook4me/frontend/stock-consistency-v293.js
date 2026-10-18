import {recipeCoverage} from './recipe-coverage-v198.js';

// Final availability presentation. The general v292 filter and finite-stock
// matcher remains intact; these helpers consistently recognize verified
// unlimited packages across the last recipe/card render boundaries.
const WORDS={
 en:{unlimited:'Unlimited stock',summary:'Ingredients at home',uncertain:'Some ingredient quantities need verification'},
 de:{unlimited:'Unbegrenzter Vorrat',summary:'Zutaten zu Hause',uncertain:'Einige Zutatenmengen müssen geprüft werden'},
 el:{unlimited:'Απεριόριστο απόθεμα',summary:'Υλικά στο σπίτι',uncertain:'Ορισμένες ποσότητες υλικών χρειάζονται επαλήθευση'}
};
const percent=value=>typeof value==='number'&&Number.isFinite(value)?Math.max(0,Math.min(100,value)):null;
export const physicallyStored=row=>{
 if(row?.unlimited===true)return true;
 if(Array.isArray(row?.lots)&&row.lots.length){
  return row.lots.some(lot=>{
   const n=Number(lot?.quantity);
   return lot?.quantity!==''&&lot?.quantity!=null&&Number.isFinite(n)&&n>0;
  });
 }
 const n=Number(row?.quantity);
 return row?.quantity!==''&&row?.quantity!=null&&Number.isFinite(n)&&n>0;
};
export function unlimitedIngredientCoverage(coverage,stock,words){
 if(!coverage||!Array.isArray(stock)||!stock.some(row=>row?.unlimited===true))return coverage;
 // Unlimited is explicit physical stock; it does not require the publisher's
 // recipe quantity and is not an assumption about other pantry ingredients.
 return {...coverage,status:'enough',percent:100,unlimited:true,
  displayLabel:'∞',displayTitle:words.unlimited};
}
export function aggregateIngredientCoverage(results){
 if(!Array.isArray(results)||!results.length)return {percent:null,partial:false};
 const entries=results.filter(row=>row?.status!=='staple');
 if(!entries.length)return {percent:100,partial:false};
 const known=entries.map(row=>percent(row?.percent)).filter(value=>value!==null);
 if(!known.length)return {percent:null,partial:false};
 return {percent:Math.round(known.reduce((sum,value)=>sum+value,0)/known.length),
  partial:known.length<entries.length};
}
const lang=value=>String(value||'en').toLowerCase().split(/[-_]/)[0];

export const StockConsistencyMixin=Base=>class extends Base{
 _v293Words(){
  return WORDS[lang(this._langCode?.()||this._uiIngredientLanguage?.()||this._hass?.language)]||WORDS.en;
 }
 _v293Stock(item){
  return typeof this._v292Stock==='function'?this._v292Stock(item):[];
 }
 _coverage(recipe,item){
  let result=super._coverage(recipe,item);
  const rows=this._v293Stock(item);
  // A cached total can be positive even when all actual physical lots have
  // been depleted. A false legacy presence must not override the source.
  if(result?.status==='at_home_quantity_unverified'&&!rows.some(physicallyStored))
   result=recipeCoverage(recipe,item);
  return unlimitedIngredientCoverage(result,rows,this._v293Words());
 }
 _v66Body(recipe,custom,state,slot=null){
  const html=super._v66Body(recipe,custom,state,slot);
  if(typeof html!=='string'||!recipe?.ingredients?.length)return html;
  const root=document.createElement('div');root.innerHTML=html;
  const words=this._v293Words();
  for(const button of root.querySelectorAll('[data-v66-ingredient]')){
   const index=Number(button.dataset.v66Ingredient);
   if(!Number.isInteger(index)||index<0||index>=recipe.ingredients.length)continue;
   const coverage=this._coverage(recipe,recipe.ingredients[index]);
   if(!coverage||coverage.status==='at_home_quantity_unverified')continue;
   const label=coverage.unlimited?'∞':coverage.displayLabel||
    (percent(coverage.percent)===null?'—':Math.round(percent(coverage.percent))+'%');
   // The final v79/price/storage layer can replace an earlier v66 coverage
   // badge with a stale "—". Synchronize only the existing HOME badge,
   // preserving the physical storage location and all price metadata.
   let chip=[...button.querySelectorAll('.chip')].find(el=>
    !!el.querySelector('ha-icon[icon="mdi:home-outline"]'));
   if(!chip){
    chip=document.createElement('span');chip.className='chip';
    const icon=document.createElement('ha-icon');
    icon.setAttribute('icon','mdi:home-outline');icon.setAttribute('aria-hidden','true');
    chip.append(icon);button.append(chip);
   }
   for(const child of [...chip.childNodes])if(child.nodeType===Node.TEXT_NODE)child.remove();
   for(const span of [...chip.querySelectorAll(':scope > span')])span.remove();
   chip.append(document.createTextNode(label));
   const original=String(chip.getAttribute('title')||'');
   // Old cards append their actual place as "Stored in pantry: —".
   // Keep the place, but strip only the trailing obsolete amount marker.
   const place=original.replace(/\s*[:：]\s*(?:—|–|-|∞|\d+(?:[.,]\d+)?\s*%)\s*$/u,'').trim();
   const annotation=coverage.unlimited?words.unlimited:
     coverage.displayTitle||words.summary+': '+label;
   const fullTitle=[place,annotation].filter(Boolean).join(' · ');
   chip.title=fullTitle;chip.setAttribute('aria-label',fullTitle);
   if(coverage.unlimited)chip.dataset.v293Unlimited='true';
   else chip.dataset.v293Available=String(coverage.percent!==null);
  }
  return root.innerHTML;
 }
 _bindCards(container,...args){
  const result=super._bindCards(container,...args);
  for(const card of container?.querySelectorAll?.('[data-v66-ref]')||[]){
   const recipe=this._v66Refs?.get(card.dataset.v66Ref)?.recipe;
   if(!recipe?.ingredients?.length)continue;
   const coverage=recipe.ingredients.map(item=>this._coverage(recipe,item));
   if(!coverage.some(row=>row?.unlimited))continue;
   const badge=card.querySelector('[data-v241-stock]');
   if(!badge)continue;
   const summary=aggregateIngredientCoverage(coverage);
   const text=summary.percent===null?'—':(summary.partial?'≈ ':'')+summary.percent+'%';
   const words=this._v293Words();
   badge.dataset.state=summary.percent===null?'unknown':summary.partial?'partial':
     summary.percent===100?'complete':'known';
   badge.title=words.summary+': '+text+(summary.partial?' · '+words.uncertain:'');
   badge.setAttribute('aria-label',badge.title);
   let value=badge.querySelector('span');
   if(!value){value=document.createElement('span');badge.append(value);}
   value.textContent=text;
   badge.dataset.v293Audited='true';
  }
  return result;
 }
};
