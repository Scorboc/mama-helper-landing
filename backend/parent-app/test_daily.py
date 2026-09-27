import copy
import importlib.util
import json
import os
import unittest
from datetime import date, timedelta, datetime
from pathlib import Path
import test_api as base
app=base.app

class DailyTest(unittest.TestCase):
    call=base.AccountsTest.call
    register=base.AccountsTest.register
    def setUp(self):
        base.AccountsTest.setUp(self)
        self.original=app.chat_answer; self.contexts=[]
        def fake(question,context,**kwargs):
            body=json.loads(context); self.contexts.append(body)
            count=1 if body.get('replacement') else 3
            return json.dumps({'ids':[x['id'] for x in body['candidates'][:count]]})
        app.chat_answer=fake
        self.cookie,self.session=self.register('daily@example.test')
        state=self.session['state']
        state['profile']={'childName':'Первый','childSex':'unknown','role':'mom','stage':'child','birthDate':(date.today()-timedelta(days=200)).isoformat(),'week':20,'weekDate':date.today().isoformat(),'feeding':'unknown','sleep':'','health':'','healthConfirmed':False,'topics':[]}
        state['activeChildId']='primary'
        state['children']=[{'id':'second','data':{'profile':{**state['profile'],'childName':'Второй'}}}]
        self.assertEqual(self.call('save',self.cookie,state=state,revision=0)[0]['statusCode'],200)
        self.state=state
    def tearDown(self):
        app.chat_answer=self.original
        base.AccountsTest.tearDown(self)
    def plan(self,cid='primary'):
        response,body=self.call('daily-plan',self.cookie,childId=cid)
        self.assertEqual(response['statusCode'],200,body);return body
    def change(self,plan,**kw):
        return self.call('daily-feedback',self.cookie,childId=plan['childId'],day=plan['day'],version=plan['version'],itemId=plan['items'][0]['id'],requestId='replace-test',**kw)
    def test_stable_daily_plan_and_child_isolation(self):
        first=self.plan(); second=self.plan()
        self.assertEqual(first,second);self.assertEqual(len(self.contexts),1)
        other=self.plan('second')
        self.assertEqual(other['childId'],'second')
        self.assertNotIn('childName',self.contexts[-1]['profile'])
        self.assertIsInstance(self.contexts[-1]['profile']['ageMonths'],int)
        self.assertEqual(self.call('daily-plan',self.cookie,childId='someone-else')[0]['statusCode'],404)
    def test_reason_required_before_ai_and_previous_plan_preserved(self):
        plan=self.plan(); calls=len(self.contexts)
        for detail in ('','  ','коротко'):
            result,_=self.change(plan,kind='replace',reason='materials',detail=detail)
            self.assertEqual(result['statusCode'],400)
        self.assertEqual(len(self.contexts),calls)
        self.assertEqual(self.plan()['items'],plan['items'])
    def test_replacement_feedback_is_encrypted_idempotent_and_reused(self):
        plan=self.plan()
        response,new=self.change(plan,kind='replace',reason='materials',detail='Нет книжек и игрушек, мы сейчас в дороге.')
        self.assertEqual(response['statusCode'],200,new)
        self.assertNotEqual(plan['items'][0]['id'],new['items'][0]['id'])
        self.assertEqual(new['items'][0]['materials'],'Ничего')
        self.assertEqual(self.contexts[-1]['replacement']['reason'],'materials')
        calls=len(self.contexts)
        self.assertEqual(self.change(plan,kind='replace',reason='materials',detail='Нет книжек и игрушек, мы сейчас в дороге.')[0]['statusCode'],200)
        self.assertEqual(len(self.contexts),calls)
        db=app.DB()
        try:
            encrypted=db.query('SELECT encrypted_data FROM mh_daily_feedback').fetchone()[0]
            self.assertNotIn('дороге',encrypted)
            daily,runtime=app.daily_runtime()
            context=daily.context(runtime,db,self.session['user']['id'],self.state)
            self.assertIn('Нет книжек',context)
        finally:db.close()
    def test_ai_failure_does_not_replace_without_analysis(self):
        plan=self.plan()
        app.chat_answer=lambda *a,**k: (_ for _ in ()).throw(TimeoutError())
        self.assertEqual(self.change(plan,kind='replace',reason='hard',detail='Ребёнок пока не умеет это делать самостоятельно.')[0]['statusCode'],503)
        self.assertEqual(self.plan()['items'],plan['items'])
    def test_fallback_is_labelled_and_not_regenerated(self):
        app.chat_answer=lambda *a,**k:'invalid json'
        plan=self.plan();self.assertEqual(plan['source'],'library');self.assertEqual(len(plan['items']),3)
        self.assertEqual(self.plan(),plan)
    def test_hint_dismissal_and_feedback_stale_revision(self):
        plan=self.plan()
        if plan['hint']:
            result,updated=self.change(plan,kind='hint-read')
            self.assertEqual(result['statusCode'],200);self.assertIsNone(updated['hint'])
            result,_=self.call('daily-feedback',self.cookie,childId='primary',day=plan['day'],version=plan['version'],itemId=plan['items'][0]['id'],requestId='stale',kind='liked')
            self.assertEqual(result['statusCode'],409)
    def test_family_push_budget_multi_device_and_read_suppression(self):
        state=copy.deepcopy(self.state);state['preferences'].update(push=True,secondReminder=True)
        self.call('save',self.cookie,state=state,revision=1)
        for name in ('one','two'):
            self.call('subscribe',self.cookie,subscription={'endpoint':'https://fcm.googleapis.com/fcm/send/'+name,'keys':{'p256dh':'a'*30,'auth':'b'*30}})
        os.environ.update(VAPID_PRIVATE_KEY='test',VAPID_SUBJECT='mailto:test@example.test')
        spec=importlib.util.spec_from_file_location('daily_job',Path(__file__).with_name('daily_job.py'));job=importlib.util.module_from_spec(spec);spec.loader.exec_module(job)
        daily,_=app.daily_runtime(); original_now=daily.local_now
        moment=original_now(state).replace(hour=9,minute=0)
        daily.local_now=lambda state:moment
        db=app.DB();sent=[]
        try:
            job.run(app,db,lambda **kw:sent.append(kw));job.run(app,db,lambda **kw:sent.append(kw))
            self.assertEqual(len(sent),1)
            self.assertIn('child=',json.loads(sent[0]['data'])['path'])
            moment=moment.replace(hour=15)
            db.query('UPDATE mh_daily SET viewed=1');db.conn.commit()
            job.run(app,db,lambda **kw:sent.append(kw));self.assertEqual(len(sent),1)
            db.query('UPDATE mh_daily SET viewed=0');db.conn.commit()
            job.run(app,db,lambda **kw:sent.append(kw));job.run(app,db,lambda **kw:sent.append(kw))
            self.assertEqual(len(sent),2)
        finally:daily.local_now=original_now;db.close()

if __name__=='__main__':unittest.main()
