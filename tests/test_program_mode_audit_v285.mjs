import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const repo=path.resolve(import.meta.dirname,'..');
const script=path.join(repo,'tools/audit_cook4me_program_modes_v285.mjs');
const modes=path.join(repo,'custom_components/cook4me/frontend/recipe-step-modes-v259.js');
const mk=(dir,name,content)=>{
 const p=path.join(dir,name);fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,JSON.stringify(content));return p;
};

test('audit reports exact unresolved source modes, key-only and metadata gaps without exposing recipe titles',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'cook4me-program-audit-'));
 try{
  const integration=path.join(root,'custom_components/cook4me');
  fs.mkdirSync(path.join(integration,'frontend'),{recursive:true});
  fs.copyFileSync(modes,path.join(integration,'frontend/recipe-step-modes-v259.js'));
  const fixture={recipes:[
   {displayVariantId:'private-recipe-123',title:'Private family dinner',steps:[
    {instruction:'Pressure phase',programs:[{programName:'High pressure cooking',programKey:'PROGRAM_1'}]},
    {instruction:'Warm phase',programs:[{programName:'Warm holding',programKey:'PROGRAM_77'}]},
    {instruction:'Mystery',programs:[{programName:'Unpublished SEB mode alpha',programKey:'PROGRAM_99'}]},
    {instruction:'Opaque',programs:[{programKey:'PROGRAM_987'}]},
    {instruction:'No program in source'},
   ]},
   {steps:[{sequences:[
    {applianceGroup:{key:'APPLIANCE_GROUP_1'},operations:[{program:{key:'PROGRAM_X',name:'Unknown oven'}}]},
    {applianceGroup:{key:'APPLIANCE_GROUP_15'},operations:[{program:{key:'PROGRAM_2',name:'Browning'}}]},
   ]}]},
  ]};
  mk(root,'.storage/cook4me/runtime_catalog/merged_catalog.v1.json',fixture);
  const result=path.join(root,'report.json');
  const candidate=path.join(root,'read-only-candidate.js');
  fs.copyFileSync(modes,candidate);
  const ran=spawnSync(process.execPath,[script,'--root',root,'--resolver',candidate,'--json',result],{encoding:'utf8'});
  assert.equal(ran.status,2,'unresolved catalog program is a finding, not a success');
  assert.equal(ran.stderr,'');
  const data=JSON.parse(fs.readFileSync(result,'utf8'));
  assert.equal(data.scan.resolved,3);
  assert.equal(data.scan.unknownNamed,1);
  assert.equal(data.scan.unknownKeyOnly,1);
  assert.equal(data.scan.noStepProgramEvidence,1);
  assert.equal(data.scan.foreignApplianceOperations,0,'explicit Cook4Me sequences take precedence');
  assert.ok(data.unknownPrograms.some(x=>x.programName==='Unpublished SEB mode alpha'));
  assert.ok(data.unknownPrograms.some(x=>x.programKey==='PROGRAM_987'));
  assert.ok(!fs.readFileSync(result,'utf8').includes('Private family dinner'));
  assert.ok(!fs.readFileSync(result,'utf8').includes('private-recipe-123'));
  assert.equal(data.inputs[0].kind,'release_catalog');
  assert.ok(fs.existsSync(candidate),'audit uses separate candidate file without altering installed source');
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});

test('no-step catalog is reported as incomplete coverage, not as fully mapped',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'cook4me-modes-none-'));
 try{
  const integration=path.join(root,'custom_components/cook4me');
  fs.mkdirSync(path.join(integration,'frontend'),{recursive:true});
  fs.copyFileSync(modes,path.join(integration,'frontend/recipe-step-modes-v259.js'));
  mk(root,'.storage/cook4me/runtime_catalog/merged_catalog.v1.json',{recipes:[{title:'Just summary'}]});
  const ran=spawnSync(process.execPath,[script,'--root',root],{encoding:'utf8'});
  assert.equal(ran.status,2);
  const data=JSON.parse(ran.stdout);
  assert.equal(data.scan.steps,0);
  assert.ok(data.warnings.some(x=>x.startsWith('NO_RECIPE_STEPS_OBSERVED')));
  assert.equal(data.coverage.resolvedPercent,null);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
