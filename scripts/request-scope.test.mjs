import test from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
import fs from 'node:fs';
const source=fs.readFileSync(new URL('../src/lib/request-scope.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText;
const {RequestScope}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
test('slow first child cannot overwrite second child or mark its plan viewed',async()=>{
 const scope=new RequestScope();let visible;const seen=[];
 const load=(child,promise)=>{const ticket=scope.begin(child);return promise.then(plan=>{if(scope.current(ticket)){visible=plan;seen.push(child);}});};
 const first=deferred(),second=deferred();const a=load('baby',first.promise),b=load('preschool',second.promise);
 second.resolve({child:'preschool'});await b;first.resolve({child:'baby'});await a;
 assert.equal(visible.child,'preschool');assert.deepEqual(seen,['preschool']);
});
test('day change invalidates replacement result before next request starts',()=>{
 const scope=new RequestScope();const replacement=scope.begin('child/day1');scope.select('child/day2');assert.equal(scope.current(replacement),false);
});
test('unmount rejects in-flight result',()=>{
 const scope=new RequestScope();const ticket=scope.begin('child/day1');scope.cancel();assert.equal(scope.current(ticket),false);
});
