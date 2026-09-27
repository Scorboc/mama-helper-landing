import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
const catalog=JSON.parse(readFileSync(new URL('../ai-proxy/age-play-catalog.json',import.meta.url),'utf8'));
const source=readFileSync(new URL('../src/lib/parent-model.ts',import.meta.url),'utf8').replace("import agePlayCatalog from '../../ai-proxy/age-play-catalog.json';",'const agePlayCatalog='+JSON.stringify(catalog)+';');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022}}).outputText;
const {ageValue,dueMilestones,stateWithProfile,emptyState,defaultProfile,demoAnswer}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const born=day=>({...defaultProfile(),stage:'child',birthDate:day});
assert.equal(ageValue(born('2026-01-31'),new Date('2026-02-28T12:00:00Z')),1);
assert.equal(ageValue(born('2024-02-29'),new Date('2025-02-28T12:00:00Z')),12);
assert.equal(ageValue({...defaultProfile(),week:20,weekDate:'2026-09-01'},new Date('2026-09-08T00:00:00Z')),21);
let state={...emptyState(),profile:born('2026-03-06')};
assert.ok(dueMilestones(state,new Date('2026-09-06T12:00:00Z')).some(x=>x.id==='child-6'));
state.events={'child-6':{status:'later',until:Date.parse('2026-10-07T00:00:00Z')}};
assert.ok(!dueMilestones(state,new Date('2026-10-06T00:00:00Z')).some(x=>x.id==='child-6'));
assert.ok(dueMilestones(state,new Date('2026-10-07T00:00:00Z')).some(x=>x.id==='child-6'));
state.events['child-6']={status:'read',until:0};
assert.ok(!dueMilestones(state,new Date('2026-10-08T00:00:00Z')).some(x=>x.id==='child-6'));
state.profile.topics=['wellbeing'];assert.ok(!dueMilestones(state,new Date('2026-10-08T00:00:00Z')).some(x=>x.id==='child-0'));
const almostSixMonths={...emptyState(),profile:born('2026-03-13')};
assert.ok(!dueMilestones(almostSixMonths,new Date('2026-09-06T12:00:00Z')).some(x=>x.id==='child-6'));
const initialized=stateWithProfile(emptyState(),born('2024-01-01'));
assert.equal(initialized.events['child-0'].status,'hidden');
assert.match(demoAnswer('Я хочу навредить себе'),/112/);
assert.match(demoAnswer('Дайте дозировку лекарства'),/не рассчитываю дозы/);
assert.match(demoAnswer('Мне нужна поддержка'),/маленький шаг/);
console.log('Parent model checks passed: dates, exact age boundaries, postponement, all topics and safe demo fallback.');

for(let month=0;month<85;month++){
 const now=new Date(), p=born(new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth()-month,1)).toISOString().slice(0,10));
 const answer=demoAnswer('Игра без игрушек',p), eligible=catalog.filter(g=>month>=g.min&&month<g.max);
 assert.ok(eligible.some(g=>answer.includes('«'+g.title+'»')), 'Demo age '+month);
 assert.doesNotMatch(answer,/напишите в чат|проверьте в чате|обсудите с ИИ/i);
}
assert.match(demoAnswer('Игра для развития',null),/нужен возраст/);
