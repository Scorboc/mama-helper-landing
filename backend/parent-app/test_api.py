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
    def test_early_parent_constraints_survive_long_dialogue(self):
        state=app.blank_state();state['messages']=[{'role':'user','text':'Нужна игра без игрушек.'}]
        state['messages'] += [{'role':'assistant' if i%2 else 'user','text':'Другое сообщение'} for i in range(20)]
        self.assertIn('без игрушек',app.chat_history_context(state))
    def test_feedback_privacy_retry_and_validation(self):
        cookie,initial=self.register('feedback@example.test')
        state=initial['state'];state['messages']=[{'id':'answer','role':'assistant','text':'Synthetic answer'}]
        self.call('save',cookie,state=state,revision=initial['revision'])
        data=dict(kind='helpful',messageId='answer',comment='Test',consentContext=False,requestId='f1')
        self.assertEqual(self.call('feedback',cookie,**data)[0]['statusCode'],200)
        self.assertEqual(self.call('feedback',cookie,**data)[0]['statusCode'],200)
        db=app.DB()
        record=app.unseal(db.query('SELECT encrypted_data FROM mh_feedback').fetchone()[0])
        self.assertNotIn('context',record)
        db.close()
        self.assertEqual(self.call('feedback',cookie,**{**data,'comment':'changed'})[0]['statusCode'],409)
        self.assertEqual(self.call('feedback',cookie,**{**data,'messageId':'missing','requestId':'f2'})[0]['statusCode'],400)
        self.assertEqual(self.call('feedback',cookie,**{**data,'consentContext':True,'requestId':'f3'})[0]['statusCode'],200)
        db=app.DB();record=app.unseal(db.query('SELECT encrypted_data FROM mh_feedback WHERE request_id=?',('f3',)).fetchone()[0]);db.close()
        self.assertEqual(record['context']['messages'][0]['text'],'Synthetic answer')

    def test_answer_style_in_context(self):
        state=app.blank_state();state['preferences']['answerStyle']='detail'
        self.assertIn('до 300 слов',app.build_chat_context(state))
        state['preferences']['answerStyle']='steps'
        self.assertIn('пошаговый',app.build_chat_context(state))

    def test_failed_ai_does_not_charge_test_quota(self):
        db=app.DB();uid='test-account-2';pw='long-test-password'
        db.query('INSERT INTO mh_users VALUES(?,?,?,?,?,?)',(uid,'quota@example.test',app.password_hash(pw),app.digest('recovery'),0,'test-v1'))
        db.query('INSERT INTO mh_state VALUES(?,?,0)',(uid,app.seal(app.blank_state())))
        token=app.new_session(db,uid);db.conn.commit();db.close()
        old=app.chat_answer
        def fail(*args,**kwargs): raise app.ChatTimeout()
        app.chat_answer=fail
        try:
            r,b=self.call('chat',app.COOKIE+'='+token,question='Хочу немного поговорить',messageId='q1',revision=0)
            self.assertEqual(r['statusCode'],200,b)
            self.assertEqual(b['quota']['used'],0)
            self.assertNotIn('Учитывай возраст',b['answer'])
        finally:app.chat_answer=old

    def test_family_and_favorites_roundtrip_and_validation(self):
        cookie, original = self.register('family@example.test')
        state = original['state']
        state['messages'] = [{'id':'answer', 'role':'assistant', 'text':'Ответ для первого ребёнка'}]
        state['activeChildId'] = 'primary'
        state['children'] = [{'id':'second', 'data':{'profile':None, 'messages':[], 'medicalCard':[]}}]
        state['favorites'] = [{'id':'answer', 'childId':'primary', 'childName':'Первый', 'text':'Ответ для первого ребёнка', 'question':'Вопрос', 'savedAt':'2026-09-20T12:00:00Z'}]
        response, saved = self.call('save', cookie, state=state, revision=original['revision'])
        self.assertEqual(response['statusCode'], 200, saved)
        _, loaded = self.call('session', cookie)
        self.assertEqual(loaded['state']['children'], state['children'])
        self.assertEqual(loaded['state']['favorites'], state['favorites'])
        self.assertIn('первого ребёнка', app.build_chat_context(loaded['state']))
        invalid = json.loads(json.dumps(state))
        invalid['children'][0]['data']['children'] = []
        with self.assertRaises(app.AppError): app.validate_state(invalid)
        invalid = json.loads(json.dumps(state))
        invalid['children'][0]['id'] = 'primary'
        with self.assertRaises(app.AppError): app.validate_state(invalid)
        invalid = json.loads(json.dumps(state))
        invalid['favorites'][0]['childId'] = 'missing'
        with self.assertRaises(app.AppError): app.validate_state(invalid)

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
    def test_model_routing_for_everyday_and_sensitive_questions(self):
        for question in ('Привет', 'Игры для развития ребенка', 'Во что папе поиграть с малышом?', 'Как выбрать книжку?'):
            self.assertEqual(app.choose_chat_model(question), app.CHAT_SIMPLE_MODEL, question)
        for question in ('Боюсь задержки развития', 'Ребенок не говорит', 'У меня паника', 'Как выбрать лечебную смесь?'):
            self.assertEqual(app.choose_chat_model(question), app.CHAT_DEEP_MODEL, question)

    def test_current_question_is_not_duplicated_in_ai_history(self):
        state=app.blank_state()
        state['messages']=[
            {'id':'old','role':'assistant','text':'Старый ответ'},
            {'id':'new','role':'user','text':'Во что поиграть?'},
        ]
        context=app.build_chat_context(state,'Во что поиграть?')
        self.assertIn('Старый ответ',context)
        self.assertNotIn('Во что поиграть?',context)

    def test_short_test_login(self):
        db=app.DB()
        db.query('INSERT INTO mh_users VALUES(?,?,?,?,?,?)',('beta-test','test01',app.password_hash('qa-pass'),'recovery',0,'test-v1'))
        db.query('INSERT INTO mh_state VALUES(?,?,0)',('beta-test',app.seal(app.blank_state())))
        db.conn.commit();db.close()
        r,b=self.call('login',email='test01',password='qa-pass')
        self.assertEqual(r['statusCode'],200,b)
        self.assertEqual(b['user']['email'],'test01')
        cookie=r['headers']['Set-Cookie'].split(';')[0]
        self.assertEqual(self.call('session',cookie)[1]['user']['email'],'test01')
        self.assertEqual(self.call('login',email='test02',password='anything')[0]['statusCode'],401)
        self.assertEqual(self.call('login',email='test01',password='wrong')[0]['statusCode'],401)

    def test_fifty_question_dialogue_and_migrated_fields_are_preserved(self):
        cookie,session=self.register('qa@example.test')
        state=session['state']
        state['profile']={'role':'mom','stage':'child','birthDate':date.today().isoformat(),'week':20,'weekDate':date.today().isoformat(),'feeding':'mixed','sleep':'','health':'','healthConfirmed':False,'topics':['communication'],'childName':'Тест'}
        state['care']={'tasks':[],'diary':[],'achievements':[],'appointments':[],'checked':[],'followups':True}
        state['conversationTitle']='Проверка 50 вопросов'
        state['messages']=[{'id':f'qa-{i}','role':'user' if i%2==0 else 'assistant','text':'Вопрос родителя?' if i%2==0 else 'Ответ помощника.'} for i in range(100)]
        response,_=self.call('save',cookie,state=state,revision=0)
        self.assertEqual(response['statusCode'],200)
        restored=self.call('session',cookie)[1]['state']
        self.assertEqual(len(restored['messages']),100)
        self.assertEqual(restored['conversationTitle'],'Проверка 50 вопросов')
        self.assertEqual(restored['profile']['childName'],'Тест')
        self.assertIn('care',restored)

    def test_bearer_sessions_work_for_cloudflare_session_migration(self):
        cookie,session=self.register('bearer@example.test')
        token='a'*64
        db=app.DB();db.query('INSERT INTO mh_sessions VALUES(?,?,?)',(app.digest(token),session['user']['id'],int(__import__('time').time())+3600));db.conn.commit();db.close()
        response=app.handler({'httpMethod':'POST','headers':{'Origin':'http://localhost:5173','Content-Type':'application/json','Authorization':f'Bearer {token}'},'body':json.dumps({'action':'session'}),'requestContext':{'identity':{'sourceIp':'127.0.0.1'}}})
        self.assertEqual(response['statusCode'],200)
        self.assertEqual(json.loads(response['body'])['user']['id'],session['user']['id'])
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
    def test_health_config_and_chat_receive_profile(self):
        self.assertEqual(self.call('health')[1],{'ok':True,'database':True})
        config=self.call('config')[1]
        self.assertTrue(config['ok']);self.assertFalse(config['chatConfigured'])
        c,b=self.register('chat@example.test');state=b['state']
        state['profile']={'role':'mom','stage':'child','birthDate':(date.today()-timedelta(days=400)).isoformat(),'week':20,'weekDate':date.today().isoformat(),'feeding':'mixed','sleep':'просыпается ночью','health':'','healthConfirmed':False,'topics':['sleep','play']}
        self.assertEqual(self.call('save',c,state=state,revision=0)[0]['statusCode'],200)
        captured={};original=app.chat_answer
        def fake_answer(question,context_text):
            captured.update(question=question,context_text=context_text)
            return 'Тестовый ответ'
        app.chat_answer=fake_answer
        try:
            response,body=self.call('chat',c,question='Во что поиграть?',messageId='question-1',revision=1)
        finally:
            app.chat_answer=original
        self.assertEqual(response['statusCode'],200);self.assertEqual(body['answer'],'Тестовый ответ')
        self.assertEqual(body['revision'],2)
        self.assertEqual([m['role'] for m in body['state']['messages']],['user','assistant'])
        self.assertEqual(captured['question'],'Во что поиграть?')
        self.assertIn('ребёнку',captured['context_text'])
        self.assertIn('смешанное кормление',captured['context_text'])

    def test_yandex_gpt_chat_uses_metadata_iam_credentials_without_key_text(self):
        previous={k:os.environ.get(k) for k in ('YANDEX_API_KEY','YANDEX_FOLDER_ID','YANDEX_USE_METADATA_IAM')}
        os.environ.pop('YANDEX_API_KEY',None)
        os.environ.update(YANDEX_FOLDER_ID='folder-test',YANDEX_USE_METADATA_IAM='1')
        original_token=app.yandex_metadata_iam_token;original_deadline=app.with_chat_deadline;original_open=app.urllib.request.urlopen
        captured={}
        class Reply:
            def __enter__(self):return self
            def __exit__(self,*_args):return False
            def read(self):return '{"choices":[{"message":{"content":"Ответ YandexGPT"}}]}'.encode()
        def fake_open(request,timeout):
            headers={key.lower():value for key,value in request.header_items()}
            captured['url']=request.full_url;captured['authorization']=headers.get('authorization')
            captured['folder']=headers.get('openai-project');captured['body']=json.loads(request.data)
            return Reply()
        app.yandex_metadata_iam_token=lambda:'temporary-iam-token'
        app.with_chat_deadline=lambda call:call()
        app.urllib.request.urlopen=fake_open
        try:
            answer=app.chat_answer('Привет','контекст')
        finally:
            app.yandex_metadata_iam_token=original_token;app.with_chat_deadline=original_deadline;app.urllib.request.urlopen=original_open
            for key,value in previous.items():
                if value is None:os.environ.pop(key,None)
                else:os.environ[key]=value
        self.assertEqual(answer,'Ответ YandexGPT')
        self.assertEqual(captured['authorization'],'Bearer temporary-iam-token')
        self.assertEqual(captured['folder'],'folder-test')
        self.assertEqual(captured['body']['model'],'gpt://folder-test/yandexgpt/latest')
        self.assertEqual(captured['url'],app.YANDEX_CHAT_API_URL)
    def test_chat_creates_a_medical_card_entry_for_a_reported_fact(self):
        c,_=self.register('card@example.test')
        original=app.chat_answer
        app.chat_answer=lambda question,context_text:'Поняла, сохраню этот факт.'
        try:
            response,body=self.call('chat',c,question='Сегодня были у педиатра и сделали прививку',messageId='card-fact-1',revision=0)
        finally:
            app.chat_answer=original
        self.assertEqual(response['statusCode'],200)
        self.assertEqual(body['cardEntry']['source'],'chat')
        self.assertEqual(body['cardEntry']['text'],'Сегодня были у педиатра и сделали прививку')
        self.assertEqual(body['cardEntry']['date'],date.today().isoformat())
        session=self.call('session',c)[1]
        self.assertEqual(session['revision'],1)
        self.assertEqual(session['state']['pendingMemory'][0]['text'],'Сегодня были у педиатра и сделали прививку')
        self.assertEqual(session['state']['medicalCard'], [])
        self.assertEqual(len(session['state']['messages']),2)

    def test_chat_is_atomic_and_rejects_stale_revision(self):
        c,_=self.register('atomic@example.test')
        original=app.chat_answer
        calls=[]
        app.chat_answer=lambda question,context_text:(calls.append(question) or 'Атомарный ответ')
        try:
            first,body=self.call('chat',c,question='Во что поиграть?',messageId='stable-message-id',revision=0)
            stale,_=self.call('chat',c,question='Другой вопрос',messageId='other-message-id',revision=0)
            retry,retried=self.call('chat',c,question='Во что поиграть?',messageId='stable-message-id',revision=0)
        finally:
            app.chat_answer=original
        self.assertEqual(first['statusCode'],200)
        self.assertEqual(stale['statusCode'],409)
        self.assertEqual(retry['statusCode'],200)
        self.assertEqual(retried['answer'],'Атомарный ответ')
        self.assertEqual(retried['revision'],1)
        self.assertEqual(calls,['Во что поиграть?'])

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
        try:
            reminders.run(db,app.unseal,lambda **kw:sent.append(kw));reminders.run(db,app.unseal,lambda **kw:sent.append(kw))
        finally:
            db.close()
        self.assertEqual(len(sent),1)
        self.assertEqual(json.loads(sent[0]['data']),{'type':'daily-plan','eventId':'child-0'})

    def test_daily_budget_and_disabled_push(self):
        c,b=self.register('budget@example.test'); state=b['state']
        state['preferences']['push']=True
        self.call('save',c,state=state,revision=0)
        self.call('subscribe',c,subscription={'endpoint':'https://fcm.googleapis.com/fcm/send/budget','keys':{'p256dh':'a'*30,'auth':'b'*30}})
        os.environ['VAPID_PRIVATE_KEY']='test';os.environ['VAPID_SUBJECT']='mailto:test@example.test'
        sent=[]; db=app.DB(); original=reminders.due
        try:
            reminders.due=lambda state:[('first',0),('second',0)]
            reminders.run(db,app.unseal,lambda **kw:sent.append(kw))
            reminders.due=lambda state:[('third',0),('fourth',0)]
            reminders.run(db,app.unseal,lambda **kw:sent.append(kw))
            self.assertEqual(len(sent),2)
            db.query('DELETE FROM mh_delivery'); db.conn.commit()
            state['preferences']['push']=False
            self.call('save',c,state=state,revision=1)
            reminders.run(db,app.unseal,lambda **kw:sent.append(kw))
            self.assertEqual(len(sent),2)
        finally:
            reminders.due=original; db.close()

if __name__=='__main__':unittest.main()
