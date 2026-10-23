import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const js=ts.transpileModule(fs.readFileSync(new URL('../src/lib/quick-wins.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText;
const {quickFromSearch,elapsedLabel,latestCare,canAddQuestion,resetLibraryFilters,recordQuestionContext,hasQuestionBeyondContext,libraryHasNoMatches}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
test('shortcut whitelist rejects unknown, duplicates and redirect values',()=>{
 for(const key of ['sleep','feed','note'])assert.equal(quickFromSearch('?quick='+key),key);
 for(const value of ['', '?quick=Sleep','?quick=__proto__','?quick=https://evil.test','?quick=feed&quick=note','?quick=feed%26next=evil'])assert.equal(quickFromSearch(value),null);
});
test('service worker preserves existing paths and allows only known quick values',()=>{
 const code=fs.readFileSync(new URL('../public/parent-sw.js',import.meta.url),'utf8');
 const context=vm.createContext({URL,URLSearchParams,self:{location:{origin:'https://mama.test'},addEventListener(){}}});
 vm.runInContext(code,context);
 assert.equal(context.safeCabinetPath('/cabinet?quick=feed'),'/cabinet?quick=feed');
 assert.equal(context.safeCabinetPath('/cabinet?quick=unknown'),'/cabinet');
 assert.equal(context.safeCabinetPath('/cabinet?tab=today&child=primary'),'/cabinet?tab=today&child=primary');
 assert.equal(context.safeCabinetPath('/cabinet?mark=roll&child=primary'),'/cabinet?mark=roll&child=primary');
});
test('latest care duration, no records, sleeping, waking and feeding side',()=>{
 const now=Date.parse('2026-10-23T12:00:00Z');
 assert.equal(elapsedLabel(130),'2 ч 10 мин');assert.equal(latestCare([],now),'');
 const feed={kind:'feeding',at:'2026-10-23T09:50:00Z',side:'left'};
 assert.equal(latestCare([feed],now),'Кормление 2 ч 10 мин назад · левая');
 assert.match(latestCare([{...feed,side:'right'}],now),/правая/);assert.match(latestCare([{...feed,side:'bottle'}],now),/бутылочка/);
 assert.match(latestCare([feed,{kind:'sleep',at:'2026-10-23T11:20:00Z'}],now),/Сон: спит 40 мин/);
 assert.match(latestCare([{kind:'sleep',at:'2026-10-23T10:00:00Z',end:'2026-10-23T11:20:00Z'}],now),/сон закончился 40 мин назад/);
 assert.match(latestCare([{kind:'wake',at:'2026-10-23T11:20:00Z'}],now),/сон закончился 40 мин назад/);
 assert.equal(latestCare([{kind:'feeding',at:'bad'}],now),'');
});
test('doctor question duplicate normalization and length/count boundaries',()=>{
 assert.equal(canAddQuestion(['О сне?'],'  о   сне?  '),false);
 assert.equal(canAddQuestion([],'a'.repeat(500)),true);assert.equal(canAddQuestion([],'a'.repeat(501)),false);
 assert.equal(canAddQuestion(Array(30).fill('a'),'b'),false);assert.equal(canAddQuestion([],''),false);
});
test('library reset clears all three filters',()=>assert.deepEqual(resetLibraryFilters(),{query:'',category:'all',child:'all'}));

test('N5 waking respects sex, unknown stays neutral',()=>{
 const records=[{kind:'wake',at:'2026-10-23T11:20:00Z'}], now=Date.parse('2026-10-23T12:00:00Z');
 assert.match(latestCare(records,now,'female'),/проснулась 40 мин назад/);
 assert.match(latestCare(records,now,'male'),/проснулся 40 мин назад/);
 assert.match(latestCare(records,now,'unknown'),/сон закончился 40 мин назад/);
});
test('N6 context includes date, sleep interval or feeding side, requires own question',()=>{
 const context=recordQuestionContext({kind:'sleep',sleepType:'day',at:'2026-10-22T21:36:00Z',end:'2026-10-22T22:56:00Z'});
 assert.equal(context,'Дневной сон 23 октября, 00:36–01:56 — ');
 assert.equal(recordQuestionContext({kind:'feeding',at:'2026-10-22T21:26:00Z',side:'left'}),'Кормление 23 октября, 00:26, левая — ');
 for(const text of ['',context,context.trim(),context.replace(' — ',''),context+' ? '])assert.equal(hasQuestionBeyondContext(text,context),false);
 assert.equal(hasQuestionBeyondContext(context+'Почему так мало?',context),true);
 assert.equal(hasQuestionBeyondContext('Как помочь со сном?',context),true);
});
test('N7 empty library has no duplicate search-empty prompt',()=>{
 assert.equal(libraryHasNoMatches(0,0,true),false);
 assert.equal(libraryHasNoMatches(1,0,true),true);
 assert.equal(libraryHasNoMatches(1,1,true),false);
 assert.equal(libraryHasNoMatches(1,0,false),false);
});
