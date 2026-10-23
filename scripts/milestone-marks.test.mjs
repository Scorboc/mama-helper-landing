import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const source=fs.readFileSync(new URL('../src/lib/milestone-marks.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText;
const {detectMilestones,milestoneFromSearch,milestoneQuestions,formatMilestoneDate}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
test('affirmative skill phrases',()=>{
  for(const [text,skill] of [['Она сегодня перевернулась!','roll'],['Малыш перевернулся','roll'],['Поползла сама','crawl'],['Он пополз','crawl'],['Он встал у опоры','stand'],['Она встаёт у опоры','stand'],['Малыш пошёл!','walk'],['Она сделала первые шаги','walk'],['Сказала первое слово','words']]) assert.deepEqual(detectMilestones(text),[skill],text);
});
test('negation, regression, questions and uncertainty suppress offers',()=>{
  for(const text of ['Не переворачивается','Еще не перевернулась','Перестал ползать','Перестала, а раньше ползает','Поползет когда-нибудь?','Когда пошёл','Если пошёл','Почти перевернулась','Кажется, пополз','Как научить: первые шаги','Соседский ребёнок пошёл','Она не ползает, но перевернулась','Раньше пошёл, теперь потерял навык','Сел сам','Пошёл дождь']) {
    assert.deepEqual(detectMilestones(text),[],text);
  }
});
test('URL requires one known skill and one owned child',()=>{
  assert.deepEqual(milestoneFromSearch('?mark=roll&child=primary',['primary']),{skill:'roll',childId:'primary'});
  for(const search of ['?mark=sit&child=primary','?mark=__proto__&child=primary','?mark=roll&child=foreign','?mark=roll','?mark=roll&mark=walk&child=primary','?mark=roll&child=primary&child=primary','?mark=roll&child=..%2Fprimary']) assert.equal(milestoneFromSearch(search,['primary']),null,search);
});
test('ordinary movement by adults and destinations is not a new child skill',()=>{
  for (const text of ['Я пошла гулять','Он пошёл в сад','Муж пошёл на работу','Она пошла спать','Завтра пойдёт','Скоро первые слова']) assert.deepEqual(detectMilestones(text),[],text);
});
const sw=fs.readFileSync(new URL('../public/parent-sw.js',import.meta.url),'utf8');
const sandbox={URL,URLSearchParams,self:{location:{origin:'https://example.test'},addEventListener(){}}};
vm.createContext(sandbox);vm.runInContext(sw,sandbox);
test('worker accepts safe pair and preserves existing notification routes',()=>{
  assert.equal(sandbox.safeCabinetPath('/cabinet?mark=walk&child=primary'),'/cabinet?mark=walk&child=primary');
  assert.equal(sandbox.safeCabinetPath('/cabinet?tab=chat&child=primary&topic=words-fifteen'),'/cabinet?tab=chat&child=primary&topic=words-fifteen');
  for(const path of ['https://evil.test/cabinet','//evil.test/cabinet','/cabinet/../evil','/cabinet?mark=unknown&child=primary','/cabinet?mark=walk&child=primary&redirect=https://evil.test','/cabinet?mark=walk&mark=roll&child=primary']) assert.equal(sandbox.safeCabinetPath(path),'/cabinet',path);
});

test('each milestone has a natural question without deadlines',()=>{
  assert.deepEqual(milestoneQuestions,{
    roll:'Уже получается переворачиваться?',
    crawl:'Уже получается ползать?',
    stand:'Уже получается вставать у опоры?',
    walk:'Уже получается делать первые самостоятельные шаги?',
    words:'Уже появились первые слова?',
  });
});

test('Russian calendar dates preserve the day and show a different year',()=>{
  assert.equal(formatMilestoneDate('2026-10-22','2026-12-31'),'22 октября');
  assert.match(formatMilestoneDate('2025-10-22','2026-10-22'),/^22 октября 2025/);
  assert.equal(formatMilestoneDate('2026-01-01','2026-10-22'),'1 января');
  assert.equal(formatMilestoneDate('2024-02-29','2024-03-01'),'29 февраля');
  for (const day of ['', 'invalid', '2026-02-30']) assert.equal(formatMilestoneDate(day,'2026-10-22'),'');
});
