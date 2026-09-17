import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
const code=ts.transpileModule(readFileSync(new URL('../src/lib/conversations.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText;
const {conversationList,openConversation}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
const initial=()=>({messages:[{id:'q',role:'user',text:'Старая переписка'}],conversationTitle:'Проверка 50 вопросов',conversations:[],profile:null});
test('named empty conversations survive switching and reload',()=>{
  let s=openConversation(initial(),{title:' Сон малыша '},()=> 'sleep');
  assert.equal(s.conversationTitle,'Сон малыша');
  s=openConversation(s,{title:'Игры'},()=> 'games');
  assert.deepEqual(conversationList(s).map(t=>t.title),['Проверка 50 вопросов','Сон малыша','Игры']);
  s=openConversation(JSON.parse(JSON.stringify(s)),{id:'sleep'});
  assert.equal(s.conversationTitle,'Сон малыша');assert.deepEqual(s.messages,[]);
  s=openConversation(s,{id:'legacy-active'});assert.equal(s.messages[0].text,'Старая переписка');
  assert.deepEqual(conversationList(s).map(t=>t.id),['legacy-active','sleep','games']);
});
test('messages stay with their conversation and active click is a no-op',()=>{
  let s=openConversation(initial(),{title:'Сон'},()=> 'sleep');
  s.messages=[{id:'sleep-q',role:'user',text:'Только сон'}];
  assert.equal(openConversation(s,{id:'sleep'}),s);
  s=openConversation(s,{id:'legacy-active'});assert.equal(s.messages[0].id,'q');
  s=openConversation(s,{id:'sleep'});assert.equal(s.messages[0].id,'sleep-q');
});
test('invalid targets and blank names cannot erase a conversation',()=>{
  const s=initial();assert.equal(openConversation(s,{title:'  '}),s);assert.equal(openConversation(s,{id:'missing'}),s);
});
test('archive limit permits switching but not additional creation',()=>{
  let s=initial();for(let i=0;i<20;i++)s=openConversation(s,{title:'Диалог '+i},()=>String(i));
  assert.equal(s.conversations.length,20);assert.equal(openConversation(s,{title:'Лишний'}),s);
  assert.equal(openConversation(s,{id:'legacy-active'}).conversationTitle,'Проверка 50 вопросов');
});
