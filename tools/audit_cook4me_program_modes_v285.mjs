#!/usr/bin/env node
/**
 * Read-only cooking-mode evidence audit. Uses the production mode classifier,
 * never infers PROGRAM_n IDs and never writes HA storage, catalog or recipes.
 * Outputs aggregate, sanitized program keys/names and hashed example IDs.
 *
 * node tools/audit_cook4me_program_modes_v285.mjs
 * node tools/audit_cook4me_program_modes_v285.mjs --root /path/to/config --json /tmp/modes.json
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {gzipSync, gunzipSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';

const args=process.argv.slice(2);
function argument(flag,defaultValue){
 const index=args.indexOf(flag);
 if(index<0)return defaultValue;
 if(!args[index+1])throw Error('Missing value for '+flag);
 return args[index+1];
}
const root=argument('--root','/home/chreece/homeassistant/config');
const reportPath=argument('--json','');
const integration=argument('--integration',path.join(root,'custom_components/cook4me'));
const maxSize=128*1024*1024, maxNodes=900000;
const hash=value=>createHash('sha256').update(String(value)).digest('hex').slice(0,12);
function readJSON(file){
 const st=fs.lstatSync(file);
 if(!st.isFile()||st.size>maxSize)throw Error('Unsupported JSON input size or type');
 const raw=fs.readFileSync(file);
 const plain=file.endsWith('.gz')?gunzipSync(raw):raw;
 if(plain.length>maxSize)throw Error('Expanded JSON exceeds safe input limit');
 return JSON.parse(plain.toString('utf8'));
}
function findCatalog(){
 const options=[
  path.join(root,'.storage/cook4me/runtime_catalog/merged_catalog.v1.json.gz'),
  path.join(root,'.storage/cook4me/runtime_catalog/merged_catalog.v1.json'),
  path.join(integration,'catalog/merged_catalog.v1.json.gz'),
  path.join(integration,'catalog/merged_catalog.v1.json'),
 ];
 return options.find(file=>fs.existsSync(file))||null;
}
const modePath=path.join(integration,'frontend/recipe-step-modes-v259.js');
const source=fs.readFileSync(modePath,'utf8');
// The source module is loaded unchanged, not reimplemented in a second language.
const resolver=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const {stepCookingModes}=resolver;
if(typeof stepCookingModes!=='function')throw Error('Cook4Me mode resolver unavailable');
const summary={
 schema:1, source:'Cook4Me production recipe-step resolver', timestamp:new Date().toISOString(),
 inputs:[], scan:{objects:0,recipeContainers:0,recipesWithSteps:0,steps:0,programReferences:0,
  resolved:0,unknownNamed:0,unknownKeyOnly:0,noStepProgramEvidence:0,
  manualSteps:0,opaqueKeys:0},
 modes:{},unknownPrograms:{},sourceKeyConflicts:{},samples:[],
 warnings:[],
};
const counts=summary.scan;
const seenStepSignatures=new Set();
const groups=new Map(),conflicts=new Map();
const acceptable=s=>typeof s==='string'?s.trim():'';
function programRow(step){
 const p=Array.isArray(step.programs)?step.programs:
  (step.programName||step.programKey)?[step]:[];
 return p.filter(x=>x&&typeof x==='object'&&!Array.isArray(x));
}
function recordStep(step,recipeIdentity,fileId,index){
 if(!step||typeof step!=='object'||Array.isArray(step))return;
 const programs=programRow(step);
 counts.steps++;
 const res=stepCookingModes(step,'en');
 const group=programs.length?programs:[{}];
 if(!programs.length){
  counts.noStepProgramEvidence++;
  if(res[0]?.kind==='manual')counts.manualSteps++;
 }
 for(let j=0;j<group.length;j++){
  const row=group[j];
  const evidence=programs.length?row:null;
  if(!evidence)continue;
  const name=acceptable(row.programName),key=acceptable(row.programKey);
  const resolved=res[j]||stepCookingModes(row,'en')[0];
  // If the UI skips foreign appliance groups, follow its effective output.
  const kind=resolved?.kind||'missing',mode=resolved?.mode||null;
  const rawIdentity=name+'|'+key+'|'+(row.applianceGroup||'');
  const anonymous=hash(fileId+':'+recipeIdentity+':'+index+':'+j);
  counts.programReferences++;
  if(mode){
   counts.resolved++;summary.modes[mode]=(summary.modes[mode]||0)+1;
  }else if(name)counts.unknownNamed++;
  else counts.unknownKeyOnly++;
  if(/^PROGRAM[_ -]?\d+$/i.test(key))counts.opaqueKeys++;
  if(mode)continue;
  const label=name||'(no programName)';
  const identity=(name||'')+'\u0000'+key;
  const record=groups.get(identity)||{programName:label,programKey:key||null,
    occurrences:0,examples:[],reason:name?'unknown_named_program':'key_only_or_opaque'};
  record.occurrences++;
  if(record.examples.length<3)record.examples.push(anonymous);
  groups.set(identity,record);
 }
}
function inspectPayload(payload,fileId){
 let visited=0;
 const queue=[{value:payload,identity:'root'}];
 const visitedReferences=new WeakSet();
 while(queue.length){
  const {value,identity}=queue.pop();
  if(!value||typeof value!=='object')continue;
  if(visitedReferences.has(value))continue;
  visitedReferences.add(value);
  visited++;counts.objects++;
  if(visited>maxNodes){summary.warnings.push('SCAN_NODE_LIMIT_REACHED '+fileId);break;}
  if(Array.isArray(value)){
   for(let i=value.length-1;i>=0;i--)if(value[i]&&typeof value[i]==='object')queue.push({value:value[i],identity:identity+'/'+i});
   continue;
  }
  if(Array.isArray(value.steps)&&value.steps.length&&
    value.steps.some(x=>x&&typeof x==='object'&&
      ('programName' in x||'programKey' in x||'programs' in x||'sequences' in x))){
   counts.recipeContainers++;counts.recipesWithSteps++;
   const ident=acceptable(value.displayVariantId)||acceptable(value.searchVariantId)||
    acceptable(value.variantFunctionalId)||acceptable(value.functionalId)||identity;
   for(let i=0;i<value.steps.length;i++)recordStep(value.steps[i],ident,fileId,i);
   // Do not also walk steps as standalone recipe containers.
   for(const [key,v] of Object.entries(value))if(key!=='steps'&&v&&typeof v==='object')
    queue.push({value:v,identity:identity+'/'+key});
   continue;
  }
  for(const [key,v] of Object.entries(value)){
   if(!v||typeof v!=='object')continue;
   // Runtime stock, credentials and user profiles are unrelated to device recipe programs.
   if(['houseIngredients','pantry','stock','users','userUiPreferences','ingredients',
       'nutrition','allergies','householdMembers','settings','credentials','secrets',
       'profiles','tokens','auth','receiptScannerReceipts','scannerReceipts'].includes(key))continue;
   queue.push({value:v,identity:identity+'/'+key});
  }
 }
}
const storesDir=path.join(root,'.storage');
let stores=[];
try{stores=fs.readdirSync(storesDir).filter(name=>/^cook4me\..+\.recipe_cache$/.test(name)).sort();}catch(e){summary.warnings.push('STORAGE_DIRECTORY_UNREADABLE');}
for(const name of stores){
 try{
  const data=readJSON(path.join(storesDir,name));
  const bucket=data?.data?.detail;
  if(!bucket||typeof bucket!=='object'){summary.warnings.push('NO_DETAIL_BUCKET '+hash(name));continue;}
  let records=0;
  for(const [key,record] of Object.entries(bucket)){
   if(record?.value&&typeof record.value==='object'){
    inspectPayload(record.value,hash(name)+':'+hash(key));records++;
   }
  }
  summary.inputs.push({kind:'recipe_cache',storeHash:hash(name),detailRecords:records});
 }catch(e){summary.warnings.push('RECIPE_CACHE_READ_ERROR '+hash(name)+' '+e.constructor.name);}
}
const catalog=findCatalog();
if(catalog){
 try{
  const obj=readJSON(catalog);
  inspectPayload(obj,'release_catalog');
  summary.inputs.push({kind:'release_catalog',compressed:catalog.endsWith('.gz'),
   bytesOnDisk:fs.statSync(catalog).size});
 }catch(e){summary.warnings.push('CATALOG_READ_ERROR '+e.constructor.name);}
}else summary.warnings.push('RELEASE_CATALOG_NOT_FOUND');
const ranked=[...groups.values()].sort((a,b)=>b.occurrences-a.occurrences||a.programName.localeCompare(b.programName));
summary.uniqueUnknownPrograms=ranked.length;
summary.unknownPrograms=ranked.slice(0,250);
summary.unknownOverflowGroups=Math.max(0,ranked.length-summary.unknownPrograms.length);
summary.coverage={
 recipesWithSteps:counts.recipesWithSteps,
 observedProgramReferences:counts.programReferences,
 resolvedPercent:counts.programReferences?Math.round(counts.resolved*10000/counts.programReferences)/100:null,
 note:'Catalog summaries without step operation metadata are not proof that their cooking modes were resolved.',
};
if(!counts.steps)summary.warnings.push('NO_RECIPE_STEPS_OBSERVED: Cannot claim zero missing cooking modes.');
if(reportPath){
 fs.mkdirSync(path.dirname(reportPath),{recursive:true,mode:0o700});
 fs.writeFileSync(reportPath,JSON.stringify(summary,null,2)+'\n',{mode:0o600,flag:'wx'});
}
console.log(JSON.stringify(summary,null,2));
if(ranked.length||summary.warnings.length)process.exitCode=2;
