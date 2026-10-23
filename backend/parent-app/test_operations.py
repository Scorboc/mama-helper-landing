import datetime
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import operations as ops


class OperationsTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,APP_OPS_PATH=str(Path(self.tmp.name)/'ops.sqlite'),APP_OPS_HASH_KEY='unit-test-only')
        self.env.start()

    def tearDown(self):
        self.env.stop();self.tmp.cleanup()

    def content(self,**kw):
        return {'title':'Материал','text':'Описание','category':'play','stage':'child','minMonths':12,'maxMonths':13,
                'source':'https://example.org/source','reviewed':True,'status':'published',**kw}

    def test_no_personal_text_in_telemetry(self):
        ops.event('page','user-secret','chat');ops.event('page','user-secret','private question')
        with ops.database() as db:
            rows=db.execute('SELECT * FROM events').fetchall()
        self.assertEqual(len(rows),1);self.assertNotIn('user-secret',str(rows));self.assertNotIn('private question',str(rows))
        ops.forget('user-secret')
        with ops.database() as db:self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],0)

    def test_utm_allowlist_and_additive_migration(self):
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(os.environ['APP_OPS_PATH'])) as db, db:
            db.execute('CREATE TABLE events(at INTEGER,actor TEXT,action TEXT,detail TEXT)')
            db.execute("INSERT INTO events VALUES(1,'','register','')")
        tags = {'utm_source':'valid_1', 'utm_medium':'invalid space', 'utm_campaign':'x'*65,
                'utm_content':'UPPER', 'url':'https://example.test/private', 'email':'discard'}
        ops.event('register','synthetic',utm=tags)
        ops.event('chat','synthetic',utm={'utm_source':'ignored'})
        with ops.database() as db:
            rows = db.execute('SELECT * FROM events ORDER BY at,rowid').fetchall()
        self.assertEqual(rows[0], (1,'','register','',None,None,None,None))
        self.assertEqual(rows[1][4:], ('valid_1',None,None,None))
        self.assertEqual(rows[2][4:], (None,None,None,None))
        self.assertNotIn('https://',str(rows))
        self.assertEqual(ops.clean_utm({'utm_source':['duplicate'], 'utm_medium':None,
                                     'utm_campaign':'', 'utm_content':'ok-2'}), {'utm_content':'ok-2'})
        self.assertEqual(ops.clean_utm('arbitrary URL'), {})

    def test_unknown_ai_usage_is_not_zero(self):
        ops.ai_call('chat','test/model','error',1)
        row=ops.summary()['ai'][0]
        self.assertIsNone(row['inputTokens']);self.assertEqual(row['unknownUsage'],1)

    def test_publish_requires_review_and_tight_age_window(self):
        for values in ({'reviewed':False},{'maxMonths':15},{'minMonths':-1},{'source':'javascript:alert(1)'}):
            with self.assertRaises(ValueError):ops.document('content',self.content(**values))
        ops.document('content',self.content(status='draft',reviewed=False))
        self.assertEqual(ops.materials({}),[])

    def test_age_bounds_unknown_and_pregnancy(self):
        today=datetime.date.today()
        born=today.replace(year=today.year-1).isoformat()
        ops.document('content',self.content())
        self.assertEqual(len(ops.materials({'stage':'child','birthDate':born})),1)
        self.assertEqual(ops.materials({'stage':'child','birthDate':today.isoformat()}),[])
        self.assertEqual(ops.materials({'stage':'pregnancy','birthDate':born}),[])
        self.assertEqual(ops.materials({'stage':'child'}),[])

    def test_retention_only_eligible_observed_users(self):
        import time
        now=int(time.time())
        with ops.database() as db:
            for stamp,uid in [(now-86400,'a'),(now,'a'),(now,'b')]:db.execute('INSERT INTO events(at,actor,action,detail) VALUES(?,?,?,?)',(stamp,uid,'page','chat'))
        r=ops.summary()['retention'];self.assertEqual(r[0],{'day':1,'eligible':1,'returned':1});self.assertEqual(r[1]['eligible'],0)

    def test_existing_favorites_remain_valid_and_notes_are_bounded(self):
        import index as app
        state=app.blank_state();state['favorites']=[{'id':'a','childId':'primary','childName':'Ребёнок','text':'Ответ','question':'Вопрос','savedAt':'2026-10-03T12:00:00Z'}]
        app.validate_state(state)
        state['favorites'][0].update(category='sleep',note='Заметка');app.validate_state(state)
        state['favorites'][0]['note']='x'*1001
        with self.assertRaises(app.AppError):app.validate_state(state)

    def test_owner_panel_rejects_foreign_hosts_and_origins(self):
        from types import SimpleNamespace
        from ops_server import Handler
        def allowed(headers,write=False):return Handler.allowed(SimpleNamespace(headers=headers),write)
        self.assertFalse(allowed({'Host':'attacker.example'}))
        self.assertFalse(allowed({'Host':'localhost:18791','Origin':'https://attacker.example','Content-Type':'application/json'},True))
        self.assertFalse(allowed({'Host':'localhost:18791','Sec-Fetch-Site':'cross-site'}))
        self.assertTrue(allowed({'Host':'localhost:18791','Origin':'http://localhost:18791','Content-Type':'application/json'},True))

    def test_updates_and_type_collision(self):
        first=ops.document('content',self.content(id='example'))
        ops.document('content',{**first,'status':'archived'})
        self.assertEqual(ops.documents('content')[0]['status'],'archived')
        with self.assertRaises(ValueError):ops.document('task',{'id':'example','title':'Test','text':'','status':'new'})


if __name__=='__main__':unittest.main()
