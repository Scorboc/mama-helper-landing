import json
import unittest
from datetime import datetime, timezone, timedelta, date
from unittest.mock import patch
from test_api import AccountsTest, app


class ChatFreshnessTest(AccountsTest):
    def test_deadline_supports_platform_without_posix_timer(self):
        with patch.object(app.signal, 'setitimer', None, create=True):
            self.assertEqual(app.with_chat_deadline(lambda: 'completed'), 'completed')

    def parent(self, email):
        cookie, body = self.register(email)
        state = body['state']
        state['profile'] = {'role':'mom','stage':'child','birthDate':(date.today()-timedelta(days=120)).isoformat(),'week':20,'weekDate':date.today().isoformat(),'feeding':'unknown','sleep':'','health':'','healthConfirmed':False,'topics':[]}
        self.assertEqual(self.call('save',cookie,state=state,revision=0)[0]['statusCode'],200)
        return cookie, body['user']['id']

    def ask(self, cookie, ident='question'):
        revision=self.call('session',cookie)[1]['revision']
        return self.call('chat',cookie,question='Что видно по моим отметкам сна и кормлений?',messageId=ident,revision=revision)

    def test_changed_and_deleted_records_replace_ai_snapshot_and_old_conclusions(self):
        cookie,uid=self.parent('snapshot@example.test')
        now=datetime.now(timezone.utc)
        record={'id':'sleep-snapshot','kind':'sleep','at':(now-timedelta(hours=3)).isoformat(),'end':(now-timedelta(hours=2)).isoformat(),'note':'OLD_RECORD_NOTE'}
        feed={'id':'feed-snapshot','kind':'feeding','at':(now-timedelta(hours=1)).isoformat(),'note':'DELETED_FEED_NOTE','value':'ГВ'}
        for item in (record,feed):self.call('care-put',cookie,record=item)
        snapshots=[]
        def answer(question,context,*args,**kwargs):
            snapshots.append(context)
            return 'OLD_AI_CONCLUSION' if len(snapshots)==1 else 'Нужно учитывать только текущий дневник.'
        with patch.object(app,'chat_answer',side_effect=answer):
            first=self.ask(cookie,'first')[1]
            old_version=first['state']['messages'][-1]['careVersion']
            updated={**record,'end':(now-timedelta(hours=2,minutes=30)).isoformat(),'note':'CURRENT_RECORD_NOTE'}
            self.call('care-put',cookie,record=updated)
            second=self.ask(cookie,'second')[1]
            self.assertNotEqual(second['state']['messages'][-1]['careVersion'],old_version)
            self.assertIn('CURRENT_RECORD_NOTE',snapshots[-1])
            self.assertNotIn('OLD_RECORD_NOTE',snapshots[-1])
            self.assertNotIn('OLD_AI_CONCLUSION',snapshots[-1])
            self.assertEqual(second['state']['messages'][1]['text'],'OLD_AI_CONCLUSION')
            self.call('care-delete',cookie,id=feed['id'])
            self.call('care-delete',cookie,id=record['id'])
            third=self.ask(cookie,'third')[1]
            summary=json.loads(snapshots[-1].split('Рассчитанная сводка сна и кормлений: ',1)[1])
            self.assertEqual(summary['sleep']['sleepRecords'],0)
            self.assertEqual(summary['feeding']['records'],0)
            self.assertNotIn('CURRENT_RECORD_NOTE',snapshots[-1])
            self.assertNotIn('DELETED_FEED_NOTE',snapshots[-1])
            self.assertEqual(third['sleepContext']['records'],0)
            self.assertEqual(len(self.call('care-list',cookie)[1]['records']),0)
            self.assertEqual(len(third['state']['messages']),6)

    def test_version_changes_only_with_contents_and_remains_child_scoped(self):
        cookie,uid=self.parent('version@example.test')
        now=datetime.now(timezone.utc)
        before=self.call('care-list',cookie)[1]['contextVersion']
        record={'id':'version-feed','kind':'feeding','at':(now-timedelta(hours=1)).isoformat(),'note':''}
        self.call('care-put',cookie,record=record)
        after=self.call('care-list',cookie)[1]['contextVersion']
        self.assertNotEqual(before,after)
        self.call('care-put',cookie,record=record)
        self.assertEqual(self.call('care-list',cookie)[1]['contextVersion'],after)
        db=app.DB()
        db.query('INSERT INTO mh_care_records VALUES(?,?,?,?)',(uid,'other','hidden',app.seal({**record,'id':'hidden','note':'OTHER_CHILD_NOTE'})))
        db.conn.commit();db.close()
        self.assertEqual(self.call('care-list',cookie)[1]['contextVersion'],after)
        self.call('care-delete',cookie,id=record['id'])
        self.assertEqual(self.call('care-list',cookie)[1]['contextVersion'],before)
        self.call('care-delete',cookie,id=record['id'])
        self.assertEqual(self.call('care-list',cookie)[1]['contextVersion'],before)

    def test_journal_change_during_response_rejects_obsolete_answer(self):
        cookie,_=self.parent('race@example.test')
        record={'id':'changing','kind':'feeding','at':datetime.now(timezone.utc).isoformat(),'note':''}
        self.call('care-put',cookie,record=record)
        def answer(*args,**kwargs):
            result,_=self.call('care-delete',cookie,id=record['id'])
            self.assertEqual(result['statusCode'],200)
            return 'Must not be saved after journal changed'
        with patch.object(app,'chat_answer',side_effect=answer):
            response,body=self.ask(cookie)
        self.assertEqual(response['statusCode'],409,body)
        self.assertIn('Дневник изменился',body['error'])
        self.assertEqual(self.call('session',cookie)[1]['state']['messages'],[])

    def test_legacy_assistant_numbers_are_not_forwarded_as_current(self):
        state=app.blank_state()
        state['messages']=[{'id':'u','role':'user','text':'Я уже пробовала спокойный ритуал.'},{'id':'a','role':'assistant','text':'OUTDATED_NUMBERS'}]
        context=app.build_chat_context(state,'Что теперь по дневнику?',care_version='a'*64)
        self.assertIn('спокойный ритуал',context)
        self.assertNotIn('OUTDATED_NUMBERS',context)
        self.assertEqual(state['messages'][1]['text'],'OUTDATED_NUMBERS')

    def test_disabled_ai_returns_error_instead_of_fake_generated_answer(self):
        cookie,_=self.parent('disabled@example.test')
        with patch.object(app,'CHAT_LIVE_ENABLED',False):
            response,body=self.ask(cookie)
        self.assertEqual(response['statusCode'],503)
        self.assertIn('ИИ отключён',body['error'])
        self.assertEqual(self.call('session',cookie)[1]['state']['messages'],[])

    def test_service_errors_do_not_charge_and_retry_is_idempotent(self):
        cookie,uid=self.parent('quota-freshness@example.test')
        db=app.DB()
        db.query('INSERT INTO mh_users VALUES(?,?,?,?,?,?)',('test-account-2','limited-context@example.test',app.password_hash('synthetic-long-password'),app.digest('synthetic-recovery'),0,'test-v1'))
        row=db.query('SELECT encrypted_data,revision FROM mh_state WHERE user_id=?',(uid,)).fetchone()
        db.query('INSERT INTO mh_state VALUES(?,?,?)',('test-account-2',row[0],row[1]))
        token=app.new_session(db,'test-account-2')
        db.conn.commit();db.close()
        cookie=app.COOKIE+'='+token
        with patch.object(app,'chat_answer',side_effect=app.AppError(503,'Synthetic provider unavailable')):
            self.assertEqual(self.ask(cookie,'failed')[0]['statusCode'],503)
        db=app.DB();row=db.query('SELECT count FROM mh_limits WHERE key=?',('ai-quota:test-account-2',)).fetchone();db.close()
        self.assertTrue(row is None or row[0]==0)
        with patch.object(app,'chat_answer',side_effect=app.ChatTimeout()):
            response,body=self.ask(cookie,'timeout')
        self.assertEqual(response['statusCode'],200)
        self.assertEqual(body['quota']['used'],0)
        with patch.object(app,'chat_answer',return_value='Короткий ответ по текущим наблюдениям.') as provider:
            response,body=self.ask(cookie,'success')
            self.assertEqual(body['quota']['used'],1)
            response,replayed=self.ask(cookie,'success')
            self.assertEqual(response['statusCode'],200)
            self.assertEqual(provider.call_count,1)
            self.assertEqual(len(replayed['state']['messages']),4)
        db=app.DB();count=db.query('SELECT count FROM mh_limits WHERE key=?',('ai-quota:test-account-2',)).fetchone()[0];db.close()
        self.assertEqual(count,1)


if __name__=='__main__':unittest.main()
