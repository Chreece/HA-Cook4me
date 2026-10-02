// Mirror of catalog_name_search.py. Tests compare all shipped source aliases.
export const NAME_SEARCH_VERSION=270;
const tail=/\s+(?:cut into|cut in|cut to|chopped into|sliced into|diced into|mixed with|combined with|seasoned with|season with|rubbed with|served with|to taste|as needed|as required|for serving|for garnish|for decoration|for finishing|for greasing|zum servieren|zum wurzen|nach geschmack|in wurfel geschnitten|in scheiben geschnitten|pour servir|pour decorer|pour garnir|au gout|selon le gout|para servir|para decorar|al gusto|a gusto|a gosto|per servire|per guarnire|a piacere|για σερβιρισμα|για γαρνιρισμα|για διακοσμηση|κατα προτιμηση)(?:\s|$).*/u;
const note=/^(?:cut |chopped|sliced|diced|peeled|washed|rinsed|drained|for |to taste|as needed|quantity |or |optional|zum |nach geschmack|pour |para |per servire|για |προαιρετικ)/u;
export const normalizeNameSearch=value=>String(value??'').normalize('NFKD').replace(/\p{M}/gu,'').toLowerCase().replaceAll('ς','σ').replaceAll('ß','ss').replace(/[^\p{L}\p{N}]+/gu,' ').trim();
export function foodNameAlias(value){
 const text=String(value??'').trim().replace(/\(([^()]*)\)/g,(full,inner)=>note.test(normalizeNameSearch(inner))?'':full).replace(/(\d),(?=\d)/g,'$1.');
 return normalizeNameSearch(text.split(/[,;；，]|:(?!\d)/,1)[0]).replace(tail,'').trim();
}
const formCompound=/^(?:tiefkuhl|tk|konserven|dosen|trocken|vollkorn|meer|stein|tafel|jod|gewurz|krauter)([a-z]{3,})$/;
// Retain the complete form-qualified name and permit its food stem. Do not
// broaden this to arbitrary infixes such as apple in pineapple.
export function nameSearchWords(alias){
 const words=alias.split(' ');return [...words,...words.map(word=>word.match(formCompound)?.[1]).filter(Boolean)];
}
const rowCache=new WeakMap();
export function nameSearchTokens(row){
 if(!row||typeof row!=='object')return [];
 const source=row.nameSearchVersion===NAME_SEARCH_VERSION&&Array.isArray(row.nameSearchAliases)?row.nameSearchAliases:null;
 const old=rowCache.get(row);
 if(old&&old.source===source&&old.raw===row.searchAliases&&old.name===row.name&&old.canonical===row.canonicalName)return old.tokens;
 const aliases=new Set(source||[...(row.searchAliases||[])].map(foodNameAlias));
 for(const name of [row.name,row.canonicalName])if(name)aliases.add(normalizeNameSearch(name));
 const tokens=[...aliases].filter(Boolean).map(nameSearchWords);
 rowCache.set(row,{source,raw:row.searchAliases,name:row.name,canonical:row.canonicalName,tokens});return tokens;
}
export function ingredientNameScore(row,query){
 const words=Array.isArray(query)?query:normalizeNameSearch(query).split(' ').filter(Boolean);
 if(!words.length)return 1;
 let score=0;
 for(const tokens of nameSearchTokens(row)){
  // All query words must belong to the same food-name alias. Never match an
  // infix ("Pfeffer" in "gepfeffert", "apple" in "pineapple") or mix languages.
  if(!words.every(word=>tokens.some(token=>token.startsWith(word))))continue;
  const exact=tokens.length===words.length&&tokens.every((word,i)=>word===words[i]);
  score=Math.max(score,exact?3:words.every(word=>tokens.includes(word))?2:1);
  if(score===3)break;
 }
 return score;
}
export class IngredientNameIndex{
 constructor(rows,language,identity){
  const collator=new Intl.Collator(language||'en',{sensitivity:'base',numeric:true});
  this.rows=[...new Map(rows.filter(row=>row?.name).map(row=>[identity(row),row])).values()]
   .sort((a,b)=>collator.compare(a.name,b.name));
  this.byId=new Map(this.rows.map(row=>[identity(row),row]));this.queries=new Map();
 }
 search(query){
  const key=normalizeNameSearch(query);if(!key)return this.rows;
  if(this.queries.has(key))return this.queries.get(key);
  const words=key.split(' '),buckets=[[],[],[],[]];
  for(const row of this.rows){const score=ingredientNameScore(row,words);if(score)buckets[score].push(row);}
  const rows=[...buckets[3],...buckets[2],...buckets[1]];
  if(this.queries.size>=32)this.queries.delete(this.queries.keys().next().value);
  this.queries.set(key,rows);return rows;
 }
}
