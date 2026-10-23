import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
function model(date='2026-10-23T12:00:00Z') {
  const ctx=vm.createContext({Intl,Date});
  for(const f of ['demo-content.js','demo-model.js']) vm.runInContext(fs.readFileSync(new URL('../deploy/pages/'+f,import.meta.url),'utf8'),ctx);
  return ctx.MamaDemoModel.createDemo(()=>Date.parse(date),ctx.MamaDemoHints);
}
const call=(m,action,data={})=>m.dispatch({action,...data});
test('demo journal and doctor questions work in memory and reset with a new tab',()=>{
  const m=model();assert.equal(call(m,'care-list').body.records.length,3);
  assert.equal(call(m,'care-put',{record:{id:'qa-memory',kind:'achievement',at:'2026-10-22T12:00:00Z',note:'Тест'}}).status,200);
  assert.equal(call(m,'care-list').body.records.length,4);
  assert.equal(call(m,'doctor-question-put',{id:'q1',text:'Тестовый вопрос'}).status,200);
  assert.equal(call(m,'doctor-question-put',{id:'q2',text:' тестовый   вопрос '}).body.duplicate,true);
  assert.equal(call(m,'doctor-question-put',{id:'q1',text:'Исправленный вопрос'}).status,200);
  assert.equal(call(m,'care-list').body.doctorQuestions[0].note,'Исправленный вопрос');
  call(m,'doctor-question-delete',{id:'q1'});assert.equal(call(m,'care-list').body.doctorQuestions.length,0);
  assert.equal(call(model(),'care-list').body.records.length,3);
});
test('demo validates questions, isolates children and rejects unavailable real services',()=>{
  const m=model();
  assert.equal(call(m,'care-list',{ownerId:'other'}).status,403);
  assert.equal(call(m,'care-list',{childId:'other'}).status,404);
  assert.equal(call(m,'doctor-question-put',{id:'x',text:'x'.repeat(501)}).status,400);
  for(let n=0;n<30;n++) assert.equal(call(m,'doctor-question-put',{id:'q'+n,text:'Вопрос '+n}).status,200);
  assert.equal(call(m,'doctor-question-put',{id:'q30',text:'Лишний вопрос'}).status,400);
  for(const action of ['login','register','chat','billing-checkout','family-invite']) assert.equal(call(m,action).status,409);
});
test('approved milestone windows use calendar months, including clamped month end',()=>{
  const m=model('2026-02-28T12:00:00Z');const session=call(m,'session').body;
  session.state.profile.birthDate='2025-08-31';call(m,'save',{state:session.state,revision:session.revision});
  assert.equal(call(m,'age-guidance',{milestoneSkill:'roll'}).body.months,6);
  assert.equal(call(m,'age-guidance',{milestoneSkill:'roll'}).body.selected.milestoneSkill,'roll');
  assert.equal(call(m,'age-guidance',{milestoneSkill:'walk'}).body.selected,null);
  const s=call(m,'session').body;s.state.profile.birthDate='';call(m,'save',{state:s.state,revision:s.revision});
  assert.equal(call(m,'age-guidance',{milestoneSkill:'roll'}).body.selected,null);
});
