import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
const source=fs.readFileSync(new URL('../src/lib/care-journal.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText;
const {buildConsultationReport,recordInPeriod,journalDay}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const now=Date.parse('2026-10-11T09:00:00Z');
const profile={stage:'child',childName:'Тестовый профиль',birthDate:'2026-04-11'};
test('report exports only selected current-period child records without private mood',()=>{
 const records=[
  {id:'yes',kind:'feeding',at:'2026-10-10T08:00:00Z',value:'ГВ'},
  {id:'no',kind:'feeding',at:'2026-10-10T09:00:00Z',note:'NOT_SELECTED'},
  {id:'mood',kind:'mood',at:'2026-10-10T10:00:00Z',note:'PRIVATE_MOOD'},
  {id:'old',kind:'sleep',at:'2026-09-01T10:00:00Z',end:'2026-09-01T11:00:00Z',note:'OUTSIDE_PERIOD'},
 ];
 const report=buildConsultationReport({profile,records,selected:['yes','mood','old'],days:7,now});
 assert.match(report,/отметок кормлений: 1/);
 assert.match(report,/длительность не указана/);
 for(const text of ['PRIVATE_MOOD','NOT_SELECTED','OUTSIDE_PERIOD'])assert.ok(!report.includes(text));
 assert.match(report,/Полнота дневника неизвестна/);
});
test('calendar period includes local midnight and intersecting sleep, rejects future',()=>{
 assert.equal(journalDay('2026-10-04T21:00:00Z'),'2026-10-05');
 assert.equal(recordInPeriod({kind:'feeding',at:'2026-10-04T21:00:00Z'},7,now),true);
 assert.equal(recordInPeriod({kind:'feeding',at:'2026-10-04T20:59:00Z'},7,now),false);
 assert.equal(recordInPeriod({kind:'sleep',at:'2026-10-04T20:00:00Z',end:'2026-10-05T01:00:00Z'},7,now),true);
 assert.equal(recordInPeriod({kind:'sleep',at:'2026-10-12T08:00:00Z'},7,now),false);
});
test('sleep report preserves type, settling time and lack of end without prediction',()=>{
 const report=buildConsultationReport({profile,records:[{id:'s',kind:'sleep',sleepType:'night',at:'2026-10-10T22:00:00Z',settlingAt:'2026-10-10T21:45:00Z'}],selected:['s'],days:7,now,questions:'Что ещё отметить?'});
 assert.match(report,/Ночной сон/);assert.match(report,/Начало укладывания/);
 assert.match(report,/Окончание не отмечено/);assert.match(report,/Что ещё отметить/);
 assert.match(report,/не определяют норму сна/);
});
test('visit notes and saved development observations are absent unless explicitly supplied',()=>{
 const base={profile,records:[],selected:[],days:7,now};
 const plain=buildConsultationReport(base);assert.ok(!plain.includes('VISIT_PRIVATE'));
 const opted=buildConsultationReport({...base,appointments:[{date:'2026-10-10',reason:'VISIT_PRIVATE',questions:'QUESTION',instructions:'REPORTED_INSTRUCTIONS'}]});
 assert.match(opted,/Со слов родителя/);assert.match(opted,/VISIT_PRIVATE/);
});
