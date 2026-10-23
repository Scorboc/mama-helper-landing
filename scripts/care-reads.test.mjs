import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
const compile = path => ts.transpileModule(fs.readFileSync(new URL(path, import.meta.url), 'utf8'), {compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const uri = js => 'data:text/javascript;base64,' + Buffer.from(js).toString('base64');
const readsUri = uri(compile('../src/lib/care-reads.ts'));
const {CareReads} = await import(readsUri);

test('a 429 from an invalidated read still throttles the same session, never a new session', async()=>{
  let now=0,reject,calls=0;const reads=new CareReads(()=>now);
  const pending=reads.read('owner:a',()=>new Promise((_,r)=>{reject=r;}));await Promise.resolve();
  reads.invalidate();reject(Object.assign(new Error('limited'),{status:429}));await assert.rejects(pending,{status:429});
  await assert.rejects(reads.read('owner:b',async()=>++calls),{status:429});assert.equal(calls,0);
  now=60001;assert.equal(await reads.read('owner:b',async()=>++calls),1);
  const resetReads=new CareReads(()=>now);let rejectOld;
  const old=resetReads.read('a',()=>new Promise((_,r)=>{rejectOld=r;}));await Promise.resolve();
  resetReads.reset();rejectOld(Object.assign(new Error('old rate limit'),{status:429}));await assert.rejects(old);
  assert.equal(await resetReads.read('b',async()=> 'new session'),'new session');
});

test('N concurrent reads share one fetch, cache lasts 2.5 seconds, child/family scopes differ', async () => {
  let now=0, calls=0; const reads=new CareReads(()=>now);
  const fetcher=async()=>++calls;
  assert.deepEqual(await Promise.all(Array.from({length:20},()=>reads.read('owner:a',fetcher))),Array(20).fill(1));
  assert.equal(await reads.read('owner:a',fetcher),1);
  assert.equal(await reads.read('owner:b',fetcher),2);
  assert.equal(await reads.read('guest:a',fetcher),3);
  now=2501; assert.equal(await reads.read('owner:a',fetcher),4);
});
test('invalidation during flight replaces stale snapshot and shares fresh read', async()=>{
  const reads=new CareReads(); let finish; let calls=0;
  const fetcher=()=>++calls===1?new Promise(r=>finish=r):Promise.resolve('fresh');
  const old=reads.read('a',fetcher); await Promise.resolve();
  reads.invalidate(); const fresh=reads.read('a',fetcher); finish('stale');
  assert.deepEqual(await Promise.all([old,fresh]),['fresh','fresh']); assert.equal(calls,2);
});
test('429 blocks polling fetches for a minute, then permits recovery',async()=>{
  let now=0,calls=0; const reads=new CareReads(()=>now);
  const fetcher=async()=>{calls++;throw Object.assign(new Error('limit'),{status:429});};
  await assert.rejects(reads.read('a',fetcher),/Слишком много обновлений/);
  for(let i=0;i<10;i++)await assert.rejects(reads.read('a',fetcher));
  reads.invalidate(); await assert.rejects(reads.read('b',fetcher)); assert.equal(calls,1);
  now=60001; assert.equal(await reads.read('a',async()=> 'recovered'),'recovered');
});
test('session reset rejects an old response instead of sharing it with a new account',async()=>{
  const reads=new CareReads(); let finish;
  const old=reads.read('a',()=>new Promise(r=>finish=r)); await Promise.resolve();
  reads.reset(); finish('old account');
  await assert.rejects(old,{status:409});
  assert.equal(await reads.read('a',async()=> 'new account'),'new account');
});
test('actual API boundary invalidates after writes/events and isolates child/family',async()=>{
  globalThis.window=new EventTarget(); window.setTimeout=setTimeout; window.clearTimeout=clearTimeout;
  globalThis.localStorage={getItem:()=>null,setItem(){},removeItem(){}};
  let calls=0;
  globalThis.fetch=async(url,options)=>{
    if(url==='/app-config.json')return {ok:true,json:async()=>({apiUrl:'http://localhost/api'})};
    const {action}=JSON.parse(options.body);
    if(action==='care-list')calls++;
    return {ok:true,text:async()=>JSON.stringify(action==='care-list'?{records:[calls]}:{ok:true})};
  };
  window.location={origin:'http://localhost'};
  const source=compile('../src/lib/parent-api.ts').replace(/import \{\s*demoAnswer,[\s\S]*?\} from "\.\/parent-model";/,'const demoAnswer=()=>""; const emptyState=()=>({});').replace(/import \{ CareReads \} from "\.\/care-reads";/,`import { CareReads } from '${readsUri}';`).replaceAll('import.meta.env.VITE_APP_API_URL','undefined');
  const {api}=await import(uri(source));
  await Promise.all(Array.from({length:15},()=>api('care-list',{childId:'a'}))); assert.equal(calls,1);
  for(const action of ['care-put','care-delete','care-import','doctor-question-put','doctor-question-delete']){
    await api(action); await api('care-list',{childId:'a'});
  }
  assert.equal(calls,6);
  window.dispatchEvent(new Event('care-records-changed')); await api('care-list',{childId:'a'}); assert.equal(calls,7);
  await api('care-list',{childId:'b'}); await api('care-list',{childId:'a',ownerId:'family'}); assert.equal(calls,9);
});
