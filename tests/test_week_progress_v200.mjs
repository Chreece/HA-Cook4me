import test from 'node:test';
import assert from 'node:assert/strict';
import {WEEK_PROGRESS_TEXT,progressClock,recordWeeklyProgress,weeklyStageEstimate,WeeklyProgressMixin} from '../custom_components/cook4me/frontend/weekly-progress-v200.js';

const state=(data={},now=0)=>recordWeeklyProgress(null,{phase:'catalog_index',...data},now);
test('unknown preparation has no synthetic 0/1 or ETA',()=>{
 const s=state();assert.equal(s.completed,null);assert.equal(s.total,null);assert.equal(weeklyStageEstimate(s,90000),null);
});
test('zero completed recipes cannot predict completion',()=>assert.equal(weeklyStageEstimate(state({completed:0,total:17000}),300000),null));
for(const input of [null,undefined,'',false,true,NaN,Infinity,-1])test(`invalid completed value is indeterminate: ${String(input)}`,()=>{
 const s=state({completed:input,total:50});assert.equal(s.completed,null);assert.equal(weeklyStageEstimate(s,1000),null);
});
test('real advancing counts can estimate current stage, not entire plan',()=>{
 let s=state({completed:0,total:100});s=recordWeeklyProgress(s,{phase:'catalog_index',completed:10,total:100},2000);
 assert.equal(weeklyStageEstimate(s,2000),18000);
});
test('same count does not invent work or manufacture rate samples',()=>{
 let s=state({completed:10,total:100});s=recordWeeklyProgress(s,{phase:'catalog_index',completed:10,total:100},30000);
 assert.equal(s.samples.length,1);assert.equal(s.advanced,0);assert.equal(weeklyStageEstimate(s,30000),null);
});
test('elapsed stall removes a previously short estimate',()=>{
 let s=state({completed:95,total:100});s=recordWeeklyProgress(s,{phase:'catalog_index',completed:99,total:100},1000);
 assert.equal(weeklyStageEstimate(s,1000),250);assert.equal(weeklyStageEstimate(s,16001),null);assert.equal(s.completed,99);
});
test('new phase cannot reuse previous throughput',()=>{
 let s=state({completed:0,total:100});s=recordWeeklyProgress(s,{phase:'catalog_index',completed:50,total:100},1000);
 s=recordWeeklyProgress(s,{phase:'nutrition',completed:10,total:100},2000);assert.equal(weeklyStageEstimate(s,2000),null);assert.equal(s.samples.length,1);
});
test('denominator changes reset rate samples even with same phase name',()=>{
 let s=state({completed:0,total:100});s=recordWeeklyProgress(s,{phase:'catalog_index',completed:50,total:100},1000);
 s=recordWeeklyProgress(s,{phase:'catalog_index',completed:1,total:21},2000);assert.equal(weeklyStageEstimate(s,2000),null);
});
test('reset count clears old samples',()=>{
 let s=state({completed:50,total:100});s=recordWeeklyProgress(s,{phase:'catalog_index',completed:20,total:100},1000);assert.equal(s.samples.length,1);
});
test('phase completion does not claim entire plan is finishing in zero seconds',()=>{
 let s=state({completed:0,total:100});s=recordWeeklyProgress(s,{phase:'catalog_index',completed:100,total:100},1000);assert.equal(weeklyStageEstimate(s,1000),null);
});
test('coordinator done waits for actual response and rendering',()=>{
 const s=recordWeeklyProgress(state(),{phase:'done',completed:1,total:1,done:true},1000);assert.equal(s.phase,'results');assert.equal(s.total,null);
});
test('queue status is distinct and has no borrowed ETA',()=>{
 const s=recordWeeklyProgress(state(),{kind:'week_generate_queued',phase:'starting'},1000);assert.equal(s.phase,'queued');assert.equal(weeklyStageEstimate(s,100000),null);
});
test('timing has bounded sample storage and retains exact stage counts',()=>{
 let s=state({completed:0,total:100});for(let i=1;i<100;i++)s=recordWeeklyProgress(s,{phase:'catalog_index',completed:i,total:100},i*1000);
 assert.equal(s.samples.length,10);assert.equal(s.completed,99);assert.equal(progressClock(65000),'1:05');
});
test('Greek German English include the same progress messages',()=>{
 for(const lang of ['el','de'])assert.deepEqual(Object.keys(WEEK_PROGRESS_TEXT[lang]),Object.keys(WEEK_PROGRESS_TEXT.en));
 assert.match(WEEK_PROGRESS_TEXT.el.unknown,/δεν είναι ακόμη γνωστός/);
});

// No real timers or browser calls are needed to verify job ownership/lifecycle.
const timers=new Map();let timerId=0;
globalThis.setInterval=callback=>{timers.set(++timerId,callback);return timerId;};
globalThis.clearInterval=id=>timers.delete(id);
function element(){return {textContent:'',style:{},hidden:false,classList:{toggle(){}}};}
function job(){const nodes=Object.fromEntries(['.rx-v59-op-title','.rx-v59-op-detail','.rx-v59-op-count','.rx-v59-op-bar','span'].map(k=>[k,element()]));
 return {id:'weekly',card:{...element(),isConnected:true,querySelector:k=>nodes[k]},nodes};}
class Boundary {
 constructor(){this._entry='a';this.now=0;this._v63Jobs=new Map();}
 _prefKey(){return this._entry;}_v143Now(){return this.now;}_uiIngredientLanguage(){return 'el';}
 _v143EnsureEtaNode(token){return {hidden:false,querySelector:()=>token.nodes.span};}
 _v59PhaseLabel(phase){return phase;}
 _v143PaintEta(){this.legacyEtaCalls=(this.legacyEtaCalls||0)+1;}
 _v143RecordDuration(){this.legacyHistoryCalls=(this.legacyHistoryCalls||0)+1;}
 _v93SendJobRequest(payload){this.payload=payload;return Promise.resolve({});}
 _v59HandleProgress(event){const data=event.data||event,token=this._v63Jobs.get(data.operationId);if(data.error)this._v59FailProcess(token);else this._v143PaintEta(token);}
 _processEnd(token){if(token)token.ended=true;}
 _v59FailProcess(token){if(token)token.failed=true;}
 disconnectedCallback(){this.disconnected=true;}
}
const Host=WeeklyProgressMixin(Boundary);
function setup(){const h=new Host(),j=job();h._v63Jobs.set(j.id,j);return [h,j];}
test('weekly transport marks job before any progress event and suppresses historical ETA',async()=>{
 const [h,j]=setup();await h._v93SendJobRequest({type:'cook4me/v20/week_generate',__cook4meJobId:j.id});
 assert.ok(j._v200Weekly);assert.equal(j.nodes['.rx-v59-op-count'].textContent,'');h.now=60000;h._v200Tick();
 assert.match(j.nodes.span.textContent,/1:00/);assert.match(j.nodes.span.textContent,/Δεν αναφέρθηκε/);assert.equal(h.legacyEtaCalls,undefined);h._processEnd(j);
});
test('real event counts remain visible while local elapsed clock advances',()=>{
 const [h,j]=setup();h._v59HandleProgress({data:{operationId:j.id,kind:'week_generate',phase:'catalog_index',completed:25,total:200}});
 h.now=2000;h._v200Tick();assert.match(j.nodes['.rx-v59-op-count'].textContent,/25 \/ 200/);assert.match(j.nodes.span.textContent,/0:02/);h._processEnd(j);
});
test('ordinary jobs retain historical ETA code',()=>{const [h,j]=setup();h._v143PaintEta(j);h._v143RecordDuration(j);assert.equal(h.legacyEtaCalls,1);assert.equal(h.legacyHistoryCalls,1);});
test('weekly jobs do not pollute generic duration history',()=>{const [h,j]=setup();h._v200Track(j);h._v143RecordDuration(j);assert.equal(h.legacyHistoryCalls,undefined);h._processEnd(j);});
test('late event cannot revive a cancelled or completed weekly job',()=>{
 const [h,j]=setup();h._v200Track(j);h._processEnd(j);const before=j._v200Weekly;
 h._v59HandleProgress({operationId:j.id,kind:'week_generate',phase:'ranking',completed:20,total:21});assert.equal(j._v200Weekly,before);assert.equal(h._v200Timer,null);
});
test('failure and detached cards clean up progress timer',()=>{
 const [h,j]=setup();h._v200Track(j);h._v59FailProcess(j);assert.equal(h._v200Timer,null);
 const [other,k]=setup();other._v200Track(k);k.card.isConnected=false;other._v200Tick();assert.equal(other._v200Timer,null);
});
test('entry change and disconnect stop local updates',()=>{
 const [h,j]=setup();h._v200Track(j);const before=j.nodes.span.textContent;h._entry='b';h.now=60000;h._v200Tick();assert.equal(j.nodes.span.textContent,before);assert.equal(h._v200Timer,null);
 const [other,k]=setup();other._v200Track(k);other.disconnectedCallback();assert.equal(other._v200Jobs.size,0);assert.equal(other._v200Timer,null);assert.ok(other.disconnected);
});
test('ordinary transport is untouched',async()=>{
 const [h,j]=setup();await h._v93SendJobRequest({type:'cook4me/v33/product_add',__cook4meJobId:j.id});assert.equal(j._v200Weekly,undefined);
});
