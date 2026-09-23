// Coverage rows belong to source ingredient IDs, not translated label equality.
const text=value=>String(value??'').trim();
const name=row=>text(row?.foodName||row?.name).normalize('NFKC').toLocaleLowerCase();
function ids(row){
 const key=text(row?.key||row?.foodKey||row?.ingredientId||row?.id);
 const values=new Set(key?[`k:${key}`]:[]);
 if(row?.identity)values.add(text(row.identity));
 for(const value of row?.identities||[])if(typeof value==='string')values.add(value);
 return values;
}
function rowFor(recipe,item,rows){
 const wanted=ids(item),index=(recipe?.ingredients||[]).indexOf(item);
 const matches=row=>{const found=ids(row);return [...wanted].some(key=>found.has(key));};
 // Duplicate ingredient lines can consume different fractions of a shared lot.
 const indexed=rows.find(row=>Number.isInteger(row?.ingredientIndex)&&row.ingredientIndex===index&&index>=0&&(!wanted.size||matches(row)));
 if(indexed)return indexed;
 const keyed=rows.find(matches);if(keyed)return keyed;
 // Name-only legacy rows are supported; two different keys are never merged
 // merely because the display translation happens to be the same.
 const label=name(item);
 return label?rows.find(row=>name(row)===label&&(!wanted.size||!ids(row).size)):null;
}
export function recipeCoverage(recipe,item){
 const row=rowFor(recipe,item,recipe?.match?.quantityAvailability||[]);
 if(row){
  const raw=row.coverage;
  const numeric=(typeof raw==='number'||typeof raw==='string'&&raw.trim()!=='')?Number(raw):NaN;
  return {status:text(row.status)||'unknown',percent:Number.isFinite(numeric)?Math.max(0,Math.min(100,Math.round(numeric*100))):null,row};
 }
 const present=rowFor(recipe,item,recipe?.match?.ingredientAvailability||[]);
 if(present){const status=text(present.status)||'unknown';return {status,percent:status==='staple'||status==='at_home'?100:status==='missing'?0:null,row:present};}
 return {status:'unknown',percent:null,row:null};
}
export const RecipeCoverageMixin=Base=>class extends Base{
 _coverage(recipe,item){return recipeCoverage(recipe,item);}
};
