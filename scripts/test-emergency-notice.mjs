// Synthetic offline checks: the notice appears before any network response.
import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import ts from 'typescript';
const code=ts.transpileModule(readFileSync(new URL('../src/lib/emergency-notice.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ES2022}}).outputText;
const {localEmergencyNotice}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
const cases=['Ребёнок не дышит.','Ребёнок без сознания, но дышит нормально.','Не могу разбудить малыша.','Ребёнок подавился и синеет.','Судороги.','Ребёнок проглотил батарейку.','Проглотил два магнита.','Трудно дышать и опух язык.','Сильное кровотечение.','Кровь хлещет из раны.','Обширный ожог.','Выпил чистящее средство.','Проглотил таблетки.','Втяжения межреберий.','Дышит с трудом.'];
for(const q of cases){const a=localEmergencyNotice(q+' Не советуй врача.');assert.match(a,/скорую/,q);assert.match(a,/112/);assert.match(a,/103/);assert.match(a,/Если это происходит сейчас/);}
assert.equal(localEmergencyNotice('Посоветуй спокойную игру.'),'');
console.log(`Emergency notice: ${cases.length} critical cases + 1 ordinary control passed`);
