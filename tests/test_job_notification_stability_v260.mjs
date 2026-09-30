import test from 'node:test';
import assert from 'node:assert/strict';
import {JobNotificationStabilityMixin} from '../custom_components/cook4me/frontend/job-notification-stability-v260.js';

test('retiring job card becomes invisible before DOM removal',()=>{
  const order=[];
  globalThis.matchMedia=()=>({matches:true});
  globalThis.requestAnimationFrame=callback=>{order.push('raf');callback();return 1;};

  const card={
    isConnected:true,
    classList:{add:name=>order.push('class:'+name)},
    style:{setProperty:(name,value)=>order.push('style:'+name+'='+value)},
    addEventListener(){},
    removeEventListener(){},
    remove(){order.push('remove');this.isConnected=false;},
  };
  class Base{}
  const instance=new (JobNotificationStabilityMixin(Base))();
  instance._v260RemoveJobCard({card});

  assert.ok(order.includes('class:v260-retiring'));
  const hidden=order.indexOf('style:visibility=hidden');
  const removed=order.indexOf('remove');
  assert.ok(hidden>=0);
  assert.ok(removed>hidden);
});

test('source isolates progress stack from fullscreen paint invalidation',async()=>{
  const {readFile}=await import('node:fs/promises');
  const source=await readFile(new URL('../custom_components/cook4me/frontend/job-notification-stability-v260.js',import.meta.url),'utf8');
  assert.match(source,/contain:layout paint style/);
  assert.match(source,/isolation:isolate/);
  assert.match(source,/visibility','hidden/);
  assert.match(source,/requestAnimationFrame\(\(\)=>card\.remove\(\)\)/);
  assert.match(source,/v260-retiring/);
});
