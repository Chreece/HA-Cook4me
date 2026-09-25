import {recipeCoverage} from './recipe-coverage-v198.js';

const numeric=value=>(typeof value==='number'||typeof value==='string'&&value.trim()!=='')&&Number.isFinite(Number(value))?Number(value):null;
const percentage=value=>Math.round(Math.max(0,Math.min(1,value))*100);
const TEXT={
 en:{home:'Ingredients at home',partial:'Based on known stock amounts; some amounts are unknown',unknown:'Ingredient availability is not known yet'},
 de:{home:'Zutaten zu Hause',partial:'Für bekannte Vorratsmengen; einige Mengen sind unbekannt',unknown:'Die Verfügbarkeit der Zutaten ist noch unbekannt'},
 el:{home:'Υλικά στο σπίτι',partial:'Με βάση τις γνωστές ποσότητες· ορισμένες ποσότητες είναι άγνωστες',unknown:'Η διαθεσιμότητα των υλικών δεν είναι ακόμη γνωστή'}
};

export function recipeStockCoverage(recipe){
 const match=recipe?.match||{},quantity=numeric(match.quantityCoverage),confidence=numeric(match.quantityConfidence);
 const rows=Array.isArray(match.quantityAvailability)?match.quantityAvailability:[];
 const relevant=rows.filter(row=>row?.status!=='staple');
 const known=relevant.filter(row=>numeric(row?.coverage)!==null);
 const unknown=confidence!==null&&confidence<1||Array.isArray(match.quantityUnknown)&&match.quantityUnknown.length>0||known.length<relevant.length;
 // The backend's known-only average can be 100% when all amounts are unknown.
 if(quantity!==null){
  if(confidence===0||relevant.length>0&&!known.length)return {percent:null,partial:false};
  return {percent:percentage(quantity),partial:!!unknown};
 }
 const ingredients=Array.isArray(recipe?.ingredients)?recipe.ingredients:[];
 if(rows.length){
  const amounts=ingredients.length?ingredients.map(item=>recipeCoverage(recipe,item)).filter(row=>row.status!=='staple'):relevant.map(row=>({percent:numeric(row?.coverage)===null?null:percentage(Number(row?.coverage))}));
  const available=amounts.filter(row=>row.percent!==null);
  return {percent:available.length?Math.round(available.reduce((sum,row)=>sum+row.percent,0)/available.length):null,partial:available.length>0&&available.length<amounts.length};
 }
 const pantry=numeric(match.pantryCoverage);
 if(pantry!==null)return {percent:percentage(pantry),partial:false};
 const available=ingredients.map(item=>recipeCoverage(recipe,item));
 const knownPresence=available.filter(row=>row.percent!==null);
 return {percent:knownPresence.length?Math.round(knownPresence.reduce((sum,row)=>sum+row.percent,0)/knownPresence.length):null,partial:knownPresence.length>0&&knownPresence.length<available.length};
}

export function decorateRecipeStock(card,recipe,language){
 const media=card?.querySelector(':scope > .rx-v69-media');
 if(!media||card.hasAttribute('data-v202-recipe-gap'))return;
 const labels=TEXT[String(language||'en').split(/[-_]/)[0]]||TEXT.en;
 const {percent,partial}=recipeStockCoverage(recipe);
 let badge=media.querySelector('[data-v241-stock]');
 if(!badge){badge=document.createElement('span');badge.dataset.v241Stock='';badge.className='v241-stock-badge';media.prepend(badge);}
 const value=percent===null?'—':`${partial?'≈ ':''}${percent}%`;
 badge.dataset.state=percent===null?'unknown':partial?'partial':percent===100?'complete':'known';
 badge.title=percent===null?labels.unknown:`${labels.home}: ${value}${partial?'. '+labels.partial:''}`;
 badge.setAttribute('role','img');badge.setAttribute('aria-label',badge.title);
 badge.replaceChildren();
 const icon=document.createElement('ha-icon');icon.setAttribute('icon','mdi:home-outline');icon.setAttribute('aria-hidden','true');
 const text=document.createElement('span');text.textContent=value;badge.append(icon,text);
 // Keep dietary-change information in the same overlay without covering it.
 const diet=media.querySelector('[data-v76-diet-badge]');
 if(diet){let stack=media.querySelector('.v241-photo-badges');if(!stack){stack=document.createElement('div');stack.className='v241-photo-badges';media.prepend(stack);}stack.append(badge,diet);}
}
