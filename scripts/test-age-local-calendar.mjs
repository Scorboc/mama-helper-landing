import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

process.env.TZ='Europe/Moscow';
const catalog=JSON.parse(readFileSync(new URL('../ai-proxy/age-play-catalog.json',import.meta.url),'utf8'));
const source=readFileSync(new URL('../src/lib/parent-model.ts',import.meta.url),'utf8')
  .replace("import agePlayCatalog from '../../ai-proxy/age-play-catalog.json';",'const agePlayCatalog='+JSON.stringify(catalog)+';');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022}}).outputText;
const {ageValue,contextLabel,today,dueMilestones,emptyState,defaultProfile}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
const born=day=>({...defaultProfile(),stage:'child',childName:'Тест',birthDate:day});
const afterMidnight=new Date('2026-10-11T21:05:00Z');
assert.equal(today(afterMidnight),'2026-10-12');
assert.equal(ageValue(born('2025-08-12'),new Date('2026-10-11T20:55:00Z')),13);
assert.equal(ageValue(born('2025-08-12'),afterMidnight),14);
assert.equal(contextLabel(born('2025-08-12'),afterMidnight),'Тест · 14 мес. 0 дн.');
assert.equal(contextLabel(born('2026-01-31'),new Date('2026-02-27T21:05:00Z')),'Тест · 1 мес. 0 дн.');
assert.equal(contextLabel(born('2024-02-29'),new Date('2025-02-27T21:05:00Z')),'Тест · 12 мес. 0 дн.');
assert.equal(ageValue({...defaultProfile(),week:20,weekDate:'2026-09-01'},new Date('2026-09-07T21:05:00Z')),21);
assert.ok(dueMilestones({...emptyState(),profile:born('2023-10-12')},afterMidnight).some(m=>m.id==='child-36'));
console.log('Local calendar: midnight, exact age, label, month end, leap day, pregnancy and milestone boundaries PASS.');
