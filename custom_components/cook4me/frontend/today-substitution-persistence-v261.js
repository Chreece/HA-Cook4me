export const TodaySubstitutionPersistenceMixin=Base=>class extends Base{
 _snapshotKey(user=this._v54CacheUser||String(this._hass?.user?.id||"anonymous")){
  // v260 compacted Today cards without the diet/substitution proof required by
  // the frontend guard. Use a fresh fast-shell key so an already-open HA frontend
  // cannot resurrect those incomplete cards after this runtime is installed.
  return `cook4me.ui.shell.v261.${user}`;
 }

 _v59CompactMatch(value){
  const out=super._v59CompactMatch?.(value)||{};
  if(!value||typeof value!=="object")return Object.keys(out).length?out:null;
  for(const key of [
   "safe","diet","dietCheckVersion","dietRulesSignature","dietary","violations",
   "requiresSubstitutions","eligibleWithSubstitutions",
   "substitutionCoverageComplete","substitutionCandidateCount",
   "substitutionSources","substitutions","ingredientChanges",
  ]){
   if(value[key]!==undefined){
    try{
     out[key]=typeof structuredClone==="function"
      ?structuredClone(value[key])
      :JSON.parse(JSON.stringify(value[key]));
    }catch(_error){
     out[key]=value[key];
    }
   }
  }
  // Lossless migration for live objects produced by diet rules v76 before the
  // compact cache learned to keep substitutionCoverageComplete.
  if(
   out.substitutionCoverageComplete===undefined&&
   Number(value.dietCheckVersion)===76&&
   value.requiresSubstitutions===true&&
   value.eligibleWithSubstitutions===true
  )out.substitutionCoverageComplete=true;
  return Object.keys(out).length?out:null;
 }
};
