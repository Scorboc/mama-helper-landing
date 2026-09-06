import importlib.util
import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from cryptography.fernet import Fernet

spec=importlib.util.spec_from_file_location('parent_api',Path(__file__).with_name('index.py'))
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
spec2=importlib.util.spec_from_file_location('reminders',Path(__file__).with_name('reminders.py'))
reminders=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(reminders)

class AccountsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.previous=dict(os.environ)
        os.environ.update(APP_LOCAL='1',APP_SQLITE_PATH=self.temp.name+'/test.db',APP_DATA_KEY=Fernet.generate_key().decode(),APP_ORIGINS='http://localhost:5173')
        app.initialize()
    def tearDown(self):
        os.environ.clear();os.environ.update(self.previous);self.temp.cleanup()
    def call(self,action,cookie='',origin='http://localhost:5173',**data):
        result=app.handler({'httpMethod':'POST','headers':{'Origin':origin,'Content-Type':'application/json','Cookie':cookie},'body':json.dumps({'action':action,**data}),'requestContext':{'identity':{'sourceIp':'127.0.0.1'}}})
        return result,json.loads(result['body'])
    def register(self,email):
        r,b=self.call('register',email=email,password='long-test-password',consent=True)
        self.assertEqual(r['statusCode'],200,b)
        return r['headers']['Set-Cookie'].split(';')[0],b
    def test_registration_login_logout_and_recovery(self):
        cookie,b=self.register('mom@example.test')
        r,got=self.call('session',cookie);self.assertEqual(got['user']['id'],b['user']['id'])
        self.call('logout',cookie)
        self.assertEqual(self.call('session',cookie)[0]['statusCode'],401)
        self.assertEqual(self.call('login',email='mom@example.test',password='incorrect-password')[0]['statusCode'],401)
        r,login=self.call('login',email='MOM@example.test',password='long-test-password');self.assertEqual(r['statusCode'],200)
        old_cookie=r['headers']['Set-Cookie'].split(';')[0]
        r,recovered=self.call('recover',email='mom@example.test',password='different-test-password',recoveryCode=b['recoveryCode'])
        self.assertEqual(r['statusCode'],200);self.assertNotEqual(recovered['recoveryCode'],b['recoveryCode'])
        self.assertEqual(self.call('session',old_cookie)[0]['statusCode'],401)
        self.assertEqual(self.call('recover',email='mom@example.test',password='another-test-password',recoveryCode=b['recoveryCode'])[0]['statusCode'],400)
    def test_isolation_encryption_and_conflict(self):
        a,first=self.register('a@example.test');b,second=self.register('b@example.test')
        state=first['state'];state['messages']=[{'id':'1','role':'user','text':'private content unique'}]
        r,_=self.call('save',a,state=state,revision=0,user_id=second['user']['id']);self.assertEqual(r['statusCode'],200)
        self.assertEqual(self.call('session',b)[1]['state']['messages'],[])
        self.assertEqual(self.call('session',a)[1]['state']['messages'][0]['text'],'private content unique')
        self.assertEqual(self.call('save',a,state=state,revision=0)[0]['statusCode'],409)
        db=app.DB();raw=db.query('SELECT encrypted_data FROM mh_state WHERE user_id=?',(first['user']['id'],)).fetchone()[0];db.close()
        self.assertNotIn('private content',raw)
        self.assertEqual(self.call('save',state=state,revision=0)[0]['statusCode'],401)
        self.assertEqual(self.call('session',a,origin='https://evil.example')[0]['statusCode'],403)
    def test_profile_validation_and_delete(self):
        c,b=self.register('profile@example.test');state=b['state']
        state['profile']={'role':'mom','stage':'child','birthDate':(date.today()+timedelta(days=1)).isoformat(),'week':20,'weekDate':date.today().isoformat(),'feeding':'mixed','sleep':'','health':'','healthConfirmed':False,'topics':[]}
        self.assertEqual(self.call('save',c,state=state,revision=0)[0]['statusCode'],400)
        state['profile']['birthDate']=date.today().isoformat();state['profile']['health']='test condition'
        self.assertEqual(self.call('save',c,state=state,revision=0)[0]['statusCode'],400)
        state['profile']['healthConfirmed']=True
        self.assertEqual(self.call('save',c,state=state,revision=0)[0]['statusCode'],200)
        self.assertEqual(self.call('delete',c,password='incorrect-password')[0]['statusCode'],401)
        self.assertEqual(self.call('delete',c,password='long-test-password')[0]['statusCode'],200)
        self.assertEqual(self.call('session',c)[0]['statusCode'],401)
        db=app.DB();self.assertEqual(db.query('SELECT COUNT(*) FROM mh_state').fetchone()[0],0);db.close()
    def test_limits_and_push_url_validation(self):
        c,b=self.register('push@example.test')
        self.assertEqual(self.call('subscribe',c,subscription={'endpoint':'https://127.0.0.1/admin','keys':{}})[0]['statusCode'],400)
        for _ in range(13):r,_=self.call('login',email='push@example.test',password='wrong-test-password')
        self.assertEqual(r['statusCode'],429)
    def test_missing_server_secret_fails_closed(self):
        os.environ.pop('APP_DATA_KEY')
        r,_=self.call('register',email='no@example.test',password='long-test-password',consent=True)
        self.assertEqual(r['statusCode'],503)
    def test_events_and_deduplication(self):
        c,b=self.register('push2@example.test');state=b['state']
        state['profile']={'role':'dad','stage':'child','birthDate':date.today().isoformat(),'week':20,'weekDate':date.today().isoformat(),'feeding':'unknown','sleep':'','health':'','healthConfirmed':False,'topics':[]}
        state['preferences']['push']=True
        self.assertEqual(reminders.due(state)[0][0],'child-0')
        state['events']['child-0']={'status':'hidden','until':0};self.assertEqual(reminders.due(state),[])
        state['events']={};self.call('save',c,state=state,revision=0)
        self.call('subscribe',c,subscription={'endpoint':'https://fcm.googleapis.com/fcm/send/test','keys':{'p256dh':'a'*30,'auth':'b'*30}})
        os.environ['VAPID_PRIVATE_KEY']='test';os.environ['VAPID_SUBJECT']='mailto:test@example.test'
        sent=[];db=app.DB()
        reminders.run(db,app.unseal,lambda **kw:sent.append(kw));reminders.run(db,app.unseal,lambda **kw:sent.append(kw))
        self.assertEqual(len(sent),1);self.assertEqual(sent[0]['data'],'{"type": "age-card"}');db.close()

if __name__=='__main__':unittest.main()
