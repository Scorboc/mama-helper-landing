import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const read=name=>fs.readFileSync(new URL('../'+name,import.meta.url),'utf8');
const sandbox={window:{}};
for(const file of ['catalog.js','game-core.js','library-rules.js'])vm.runInNewContext(read('public/together-games/'+file),sandbox);
const C=sandbox.window.TogetherCatalog,G=sandbox.window.TogetherGames,L=sandbox.window.TogetherLibrary;

test('every month has the declared reserve, including honest smaller newborn pools',()=>{
 assert.equal(C.cards.length,879);assert.equal(new Set(C.cards.map(c=>c.id)).size,879);
 for(let age=0;age<84;age++){
  const pool=L.select(C.cards,age);assert.ok(pool.length>=(age<3?12:16),`month ${age}`);
  assert.ok(L.select(C.cards,age,{stationary:true}).length>=(age<3?11:15));
  assert.ok(L.select(C.cards,age,{noMaterials:true}).length>=4);
  assert.ok(new Set(pool.map(c=>c.category)).size>=3);
  for(const c of pool){assert.ok(c.minMonths<=age&&age<c.maxMonths);assert.ok(c.maxMonths-c.minMonths<=(c.minMonths<24?1:2));}
 }
 for(const age of [null,undefined,true,'36',-1,84,NaN,35.5])assert.equal(L.select(C.cards,age).length,0);
});
test('new authored content has explicit two-participant actions and narrow monthly readiness',()=>{
 const rows=read('content/learning-mechanics.tsv').split('\n').filter(x=>x&&!x.startsWith('#'));
 assert.equal(rows.length,84);assert.ok(rows.every(x=>x.split('|').length===9));
 for(const c of C.cards){assert.ok(c.steps.length>=3&&c.adult&&c.child&&c.readiness&&c.safety);assert.ok(!JSON.stringify(c).includes('\ufffd'));assert.ok(c.maxMonths<=84);}
 assert.equal(C.cards.filter(c=>c.id.startsWith('learning-')).length,420);
});
test('a complete pass through each age pool shows every card before wrapping',()=>{
 for(let age=0;age<84;age++){
  const pool=L.select(C.cards,age),seen=new Set();let cursor=0;
  do{const p=L.page(pool,cursor);for(const c of p.items){assert.ok(!seen.has(c.id));seen.add(c.id);}cursor=p.next;}while(cursor);
  assert.equal(seen.size,pool.length);assert.equal(L.page(pool,999).start,0);assert.equal(L.page(pool,0,true).items.length,pool.length);
 }
 assert.equal(L.page([]).items.length,0);
});
test('filters intersect without falling back to an older child or hidden motor requirement',()=>{
 for(let age=0;age<84;age++)for(const area of new Set(L.select(C.cards,age).map(c=>c.category))){
  for(const c of L.select(C.cards,age,{area,stationary:true,noMaterials:true})){
   assert.equal(c.category,area);assert.equal(c.stationary,true);assert.equal(c.noMaterials,true);
  }
 }
 assert.equal(L.select(C.cards,24,{area:'not-a-real-category'}).length,0);
});
test('frame context rejects another origin, window, invalid mode and non-numeric ages',()=>{
 const data={type:'mama-games-context',mode:'profile',ageMonths:36};
 assert.equal(L.context(data,'https://other.invalid','https://mama.invalid',true),null);
 assert.equal(L.context(data,'https://mama.invalid','https://mama.invalid',false),null);
 assert.equal(L.context({...data,mode:'admin'},'a','a',true),null);
 for(const age of [null,'36',true,-1,84,NaN])assert.equal(L.context({...data,ageMonths:age},'a','a',true).ageMonths,null);
 assert.equal(L.context(data,'a','a',true).ageMonths,36);
});
test('profile calendar validation uses production ageValue and rejects pregnancy and invalid dates',()=>{
 function fn(file,name){const source=ts.createSourceFile(file,read(file),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);const node=source.statements.find(n=>ts.isFunctionDeclaration(n)&&n.name?.text===name);assert.ok(node);return ts.transpileModule(node.getText(source).replace(/^export /,''),{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText;}
 const playAge=Function(fn('src/lib/parent-model.ts','ageValue')+'\n'+fn('src/lib/together-profile.ts','playAge')+';return playAge;')();
 const now=new Date(2026,9,23,12);const p={stage:'child',birthDate:'2023-10-24'};
 assert.equal(playAge(p,now),35);assert.equal(playAge({...p,birthDate:'2023-10-23'},now),36);
 assert.equal(playAge({...p,stage:'pregnancy'},now),null);
 for(const birthDate of ['','2026-02-30','bad','2026-10-24','2019-10-23'])assert.equal(playAge({...p,birthDate},now),null);
 assert.equal(playAge({...p,birthDate:'2019-10-24'},now),83);
});
test('cooperative game engines finish and remain bounded through mixed actions',()=>{
 for(const age of [36,48,60,72,83]){
  const m=G.memory(age);for(const id of new Set(m.cards)){const indices=m.cards.map((x,i)=>x===id?i:-1).filter(i=>i>=0);G.tap(m,indices[0]);G.tap(m,indices[1]);if(!m.done)G.next(m);}assert.equal(m.done,true);
  const p=G.pattern(age,0);G.put(p,0);G.put(p,1);G.handover(p);G.put(p,2);G.put(p,3);assert.equal(G.compare(p),false);assert.equal(p.done,true);
  const s=G.story(age,0,1);for(let i=0;i<3;i++)G.choose(s,i);assert.equal(s.done,true);assert.equal(G.choose(s,4),false);
  const d=G.detective(age);assert.equal(G.setClue(d,0),false);G.readyDetective(d);G.setClue(d,0);G.found(d);assert.equal(G.found(d),false);G.detectiveNext(d);G.setClue(d,1);G.found(d);assert.equal(d.done,true);
  for(let i=0;i<500;i++){G.tap(m,i%12);G.next(m);G.put(p,i%4);G.choose(s,i%12);G.found(d);}assert.ok(m.open.length<=2&&p.answer.length<=2&&s.chosen.length<=3&&d.round===2);
 }
 for(let n=0;n<36;n++){assert.equal(G.memory(n),null);assert.equal(G.story(n),null);}
});
test('runtime stores no profile or progress and uses no paid generation, microphone or network',()=>{
 const code=['app.js','game-core.js','library-rules.js'].map(n=>read('public/together-games/'+n)).join('\n');
 assert.doesNotMatch(code,/\bfetch\s*\(|XMLHttpRequest|localStorage|sessionStorage|getUserMedia|sendBeacon|setInterval\s*\(/);
 const frame=read('src/components/TogetherGames.tsx');
 assert.doesNotMatch(frame,/postMessage\(profile|postMessage\(state|JSON\.stringify|targetOrigin:\s*['"]\*/);
 assert.match(frame,/event\.source!==frame\.current\?\.contentWindow/);assert.match(frame,/key=\{`\$\{mode\}:\$\{contextKey\}:\$\{age\}`\}/);
});
