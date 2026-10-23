import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
const read=p=>fs.readFileSync(new URL(p,import.meta.url),'utf8');
const load=async p=>import('data:text/javascript;base64,'+Buffer.from(ts.transpileModule(read(p).replace("import { formatBookDay } from './first-year-book';", () => "const formatBookDay = " + formatBookDay.toString() + "; const validDay = " + validDay.toString() + ";"),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2020}}).outputText).toString('base64'));
const {formatBookDay,validDay,anniversary,lifeAge,bookMoments,bookMonths,memoryInstant,familyDay}=await load('../src/lib/first-year-book.ts');
const now=Date.parse('2026-10-23T12:00:00Z');
const row=(id,at,value='',note='',skill)=>({id,kind:'achievement',at,value,note,skill});
test('monthly anniversaries clamp from original birthday, including leap day',()=>{
 assert.equal(anniversary('2024-01-31',1),'2024-02-29');assert.equal(anniversary('2024-01-31',2),'2024-03-31');
 assert.equal(anniversary('2024-02-29',12),'2025-02-28');assert.equal(anniversary('2023-01-31',1),'2023-02-28');
 assert.deepEqual(lifeAge('2024-01-31','2024-03-30'),{months:1,days:30,label:'1 мес. 30 дн.'});
 assert.equal(lifeAge('2024-01-31','2024-03-31').months,2);
 assert.equal(lifeAge('2026-01-01','2026-06-13').label,'5 мес. 12 дн.');
 assert.equal(lifeAge('','2026-06-13'),null);assert.equal(lifeAge('2026-02-30','2026-06-13'),null);assert.equal(lifeAge('2026-06-14','2026-06-13'),null);
});
test('both sources, canonical skill/value, exact duplicates and distinct notes',()=>{
 const records=[row('a','2026-03-01T09:00:00Z','Переворачивается','На коврике','roll'),row('b','2026-03-01T10:00:00Z','Переворачивается','На коврике'),row('c','2026-03-01T10:00:00Z','Переворачивается','На даче'),row('d','2026-04-01T10:00:00Z','','Прогулка')];
 const old=[{id:'old',kind:'roll',date:'2026-03-01',note:'На коврике'},{id:'custom',kind:'custom',date:'2026-04-01',note:'Прогулка'}];
 const frozen=JSON.stringify([records,old]);const result=bookMoments(records,old,'2026-01-01','Europe/Moscow',now);
 assert.equal(result.length,3);assert.equal(result[0].sources.length,3);assert.equal(result[2].sources.length,2);assert.equal(JSON.stringify([records,old]),frozen);
 assert.deepEqual(bookMonths(result),[2,3]);assert.deepEqual(bookMonths([]),[]);
});
test('first year is half-open, remains available for older child',()=>{
 const result=bookMoments([],['2024-02-28','2024-02-29','2025-02-27','2025-02-28'].map((date,i)=>({id:String(i),date,note:'Память'})),'2024-02-29','Europe/Moscow',now);
 assert.deepEqual(result.map(m=>m.day),['2024-02-29','2025-02-27']);assert.equal(result[0].month,0);assert.equal(result[1].month,11);
});
test('future instants, future days, invalid calendar values and unrelated records excluded',()=>{
 const records=[row('bad','2026-02-30T12:00:00Z','x'),row('future','2026-10-23T13:00:00Z','x'),row('bad2','nonsense','x'),row('hour','2026-01-01T24:00:00Z','x'),row('null',null,'x'),{...row('mood','2026-01-01T00:00:00Z','private'),kind:'mood'},row('local','2026-01-01T12:00:00','x')];
 assert.deepEqual(bookMoments(records,[{date:'2026-10-24',note:'x'},{date:'2026-02-30',note:'x'}],'2026-01-01','Europe/Moscow',now),[]);
});
test('family calendar day determines month independently from device timezone',()=>{
 const records=[row('x','2026-01-31T23:30:00Z','Память')];
 assert.equal(bookMoments(records,[],'2026-01-01','Pacific/Kiritimati',now)[0].month,1);
 assert.equal(bookMoments(records,[],'2026-01-01','Etc/GMT+12',now)[0].month,0);
 for(const zone of ['Pacific/Kiritimati','Etc/GMT+12','America/New_York','Europe/Moscow'])for(const day of ['2026-01-01','2026-03-08','2026-10-23'])assert.equal(familyDay(memoryInstant(day,zone,now),zone),day);
 assert.throws(()=>memoryInstant('2026-02-30','Europe/Moscow',now));assert.throws(()=>memoryInstant('2026-10-24','Europe/Moscow',now));
});
test('unknown birthday keeps dates without inventing months or age',()=>{
 const result=bookMoments([],[{date:'2026-01-01',note:'Память'}],'','Europe/Moscow',now);assert.equal(result.length,1);assert.equal(result[0].month,null);assert.equal(result[0].age,'');
});
test('book copy avoids developmental pressure and renderer has no network or persistence',()=>{
 const component=read('../src/components/FirstYearBook.tsx'),renderer=read('../src/lib/book-postcard.ts');
 assert.doesNotMatch(component+renderer,/ещ[её] не умеет|догнать|процент|серия дней|сравнени|норма развития/ui);
 assert.doesNotMatch(renderer,/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|indexedDB|localStorage|caches\.|console\./);
 assert.match(renderer,/bitmap.close\(\)/);assert.match(component,/revokeObjectURL/);
});
test('renderer creates bounded PNG, closes decoded photo, refuses overflowing text',async()=>{
 let closed=0,options,canvas; const drawn=[],texts=[];
 const ctx={save(){},restore(){},beginPath(){},roundRect(){},stroke(){},fill(){},clip(){},arc(){},font:'',measureText:s=>({width:s.length*20}),fillRect(){},fillText(...args){texts.push(args);},drawImage(...args){drawn.push(args);}};
 const originalDocument=globalThis.document,originalBitmap=globalThis.createImageBitmap,originalFetch=globalThis.fetch,originalStyle=globalThis.getComputedStyle;
 globalThis.fetch=()=>{throw new Error('Network forbidden');};
 globalThis.document={fonts:{ready:Promise.resolve()},documentElement:{},createElement:()=>canvas={getContext:()=>ctx,toBlob:fn=>fn(new Blob(['png'],{type:'image/png'}))}};
 globalThis.createImageBitmap=async(file,opts)=>{options=opts;return {width:1600,height:1200,close(){closed++;}};};
 try{
 globalThis.getComputedStyle=()=>({fontFamily:'Onest, sans-serif'});
 const {renderPostcard}=await load('../src/lib/book-postcard.ts');
 const base={title:'Месяц',name:'Ребёнок',moments:[{day:'2026-01-02',text:'Память',note:''}],caption:'',dates:true,brand:true};
 const blob=await renderPostcard({...base,photo:new File(['x'],'photo.jpg',{type:'image/jpeg'})});
 assert.equal(blob.type,'image/png');assert.equal(closed,1);assert.equal(options.imageOrientation,'from-image');assert.equal(canvas.width,1080);assert.equal(canvas.height,1350);assert.equal(drawn[0][1]+drawn[0][3]/2,540);assert.ok(drawn[0][3]>=920&&drawn[0][4]>=720);assert.ok(texts.some(t=>t[0]==='2 января'));
 await assert.rejects(()=>renderPostcard({...base,moments:Array(6).fill(base.moments[0])}),/много текста/);
 await assert.rejects(()=>renderPostcard({...base,caption:'я'.repeat(4000)}),/много текста/);
 await assert.rejects(()=>renderPostcard({...base,photo:new File(['x'],'x.svg',{type:'image/svg+xml'})}),/Выберите фото/);
 ctx.roundRect=undefined;
 await assert.rejects(()=>renderPostcard(base),/Обновите браузер/);
 }finally{globalThis.document=originalDocument;globalThis.createImageBitmap=originalBitmap;globalThis.fetch=originalFetch;globalThis.getComputedStyle=originalStyle;}
});

test('source files contain no corrupted question-mark runs',()=>{
 for(const entry of fs.readdirSync(new URL('../src/',import.meta.url),{recursive:true,withFileTypes:true})) {
  if(entry.isFile() && /\.(ts|tsx|css)$/.test(entry.name)) {
   const path=entry.parentPath+'/'+entry.name;
   assert.doesNotMatch(fs.readFileSync(path,'utf8'),/\?{4,}/,path);
  }
 }
});
test('Russian book dates have genitive month and no timezone shift',()=>{
 assert.equal(formatBookDay('2026-07-03'),'3 июля 2026');
 assert.equal(formatBookDay('2026-07-03',true),'3 июля');
 assert.equal(formatBookDay('2024-02-29'),'29 февраля 2024');
 assert.equal(formatBookDay('2026-02-30'),'');
});
test('postcard wraps words, splits only oversized words and preserves paragraphs',async()=>{
 const {wrapBookText}=await load('../src/lib/book-postcard.ts');
 assert.deepEqual(wrapBookText('Мия любит гулять',10,s=>s.length),['Мия любит','гулять']);
 assert.deepEqual(wrapBookText('абвгдежз',3,s=>s.length),['абв','где','жз']);
 assert.deepEqual(wrapBookText('Первый\nВторой',20,s=>s.length),['Первый','Второй']);
});
test('saving resets month and announces success; all monthly moments selected initially',()=>{
 const source=read('../src/components/FirstYearBook.tsx');
 assert.match(source,/setAdding\(false\);\s*setMonth\('all'\);\s*setSaved\(true\)/);
 assert.match(source,/<p role="status">Сохранено<\/p>/);
 assert.match(source,/useState<string\[\]>\(\(\) => moments.map\(m => m.id\)\)/);
});
