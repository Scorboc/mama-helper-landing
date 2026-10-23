import importlib.util, io, json, os, sqlite3, subprocess, sys, tarfile, tempfile, threading, unittest, urllib.request, urllib.error
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
from cryptography.fernet import Fernet

class AutomationTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        env={'MAMA_AUTOMATION_ROOT':str(self.root),'MAMA_AUTOMATION_TOKEN':'synthetic-token',
             'APP_SQLITE_PATH':str(self.root/'accounts.sqlite3'),'APP_OPS_PATH':str(self.root/'ops.sqlite3')}
        self.env=patch.dict(os.environ,env);self.env.start()
        spec=importlib.util.spec_from_file_location('automation_test',Path(__file__).with_name('automation_bridge.py'))
        self.app=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.app)
        self.key=Fernet.generate_key();(self.root/'backup.key').write_bytes(self.key)
    def tearDown(self):self.env.stop();self.tmp.cleanup()
    def test_no_arbitrary_job(self):
        for name in ['publish','delete','transfer','../backup','shell']:
            with self.assertRaises(ValueError):self.app.run(name)

    def maintenance(self,age=25,restore=None,now=1800000000):
        stamp=self.app.dt.datetime.fromtimestamp(now-age*3600,self.app.dt.timezone.utc).strftime('%Y%m%d-%H%M%S')+'-synthetic'
        self.app.write_json(self.root/'backup-status.json',{'ok':True,'createdAt':stamp})
        if restore is not None:self.app.write_json(self.root/'restore-status.json',restore)

    def test_catchup_threshold_order_and_persistent_throttle(self):
        now=1800000000
        self.maintenance(age=24,now=now)
        calls=[]
        with patch.object(self.app.time,'time',return_value=now), patch.object(self.app,'backup',side_effect=lambda:calls.append('backup') or {'ok':True}), patch.object(self.app.reliability,'restore',side_effect=lambda root:calls.append('restore') or {'ok':True}):
            self.assertEqual(self.app.backup_maintenance()['state'],'fresh')
            self.maintenance(now=now)
            self.assertEqual(self.app.backup_maintenance()['state'],'started')
            self.app.BACKUP_CATCHUP_THREAD.join(3)
            self.assertFalse(self.app.BACKUP_CATCHUP_THREAD.is_alive())
            self.assertEqual(calls,['backup','restore'])
            self.assertEqual(self.app.backup_maintenance()['state'],'throttled')
            self.assertEqual(json.loads((self.root/'restore-status.json').read_text())['ok'],True)
        with patch.object(self.app.time,'time',return_value=now+6*3600), patch.object(self.app,'backup',return_value={'ok':True}) as backup, patch.object(self.app.reliability,'restore',return_value={'ok':True}):
            self.assertEqual(self.app.backup_maintenance()['state'],'started')
            self.app.BACKUP_CATCHUP_THREAD.join(3)
            self.assertFalse(self.app.BACKUP_CATCHUP_THREAD.is_alive())
            backup.assert_called_once()

    def test_catchup_busy_and_failed_attempt_throttled(self):
        self.maintenance()
        with patch.object(self.app.time,'time',return_value=1800000000), patch.object(self.app,'backup',side_effect=RuntimeError('synthetic')) as backup, patch.object(self.app.reliability,'restore') as restore:
            self.app.LOCK.acquire()
            try:self.assertEqual(self.app.backup_maintenance()['state'],'busy')
            finally:self.app.LOCK.release()
            backup.assert_not_called()
            self.assertEqual(self.app.backup_maintenance()['state'],'started')
            self.app.BACKUP_CATCHUP_THREAD.join(3)
            self.assertFalse(self.app.BACKUP_CATCHUP_THREAD.is_alive())
            self.assertFalse(json.loads((self.root/'restore-status.json').read_text())['ok'])
            self.assertEqual(self.app.backup_maintenance()['state'],'throttled')
            restore.assert_not_called()

    def test_backup_alerts_daily_dedup_and_restore_failure(self):
        import telegram_outbox
        self.maintenance(age=27)
        with patch.object(self.app.time,'time',return_value=1800000000), patch.object(self.app,'backup',return_value={'ok':True}), patch.object(self.app.reliability,'restore',side_effect=RuntimeError('private-path-must-not-escape')):
            self.app.backup_maintenance()
            self.app.BACKUP_CATCHUP_THREAD.join(3)
            self.assertFalse(self.app.BACKUP_CATCHUP_THREAD.is_alive())
            self.app.backup_maintenance()
        with closing(telegram_outbox.database(self.root)) as db:
            rows=db.execute('SELECT id,body,state FROM messages').fetchall()
        self.assertEqual(len(rows),2)
        self.assertTrue(all(r['state']=='queued' for r in rows))
        self.assertNotIn('private-path',str([dict(r) for r in rows]))
        self.assertFalse(json.loads((self.root/'restore-status.json').read_text())['ok'])
        telegram_outbox.backup_alerts(self.root,26*3600,{'ok':True},1800086400)
        with closing(telegram_outbox.database(self.root)) as db:self.assertEqual(db.execute('SELECT count(*) FROM messages').fetchone()[0],2)
        telegram_outbox.backup_alerts(self.root,27*3600,{'ok':False},1800086400)
        with closing(telegram_outbox.database(self.root)) as db:self.assertEqual(db.execute('SELECT count(*) FROM messages').fetchone()[0],4)
    def test_monitor_returns_while_catchup_runs_and_second_monitor_is_busy(self):
        import telegram_outbox
        self.maintenance()
        started=threading.Event();release=threading.Event();done=threading.Event()
        calls=[];results=[]
        def slow_backup():
            calls.append('backup');started.set()
            if not release.wait(5):raise RuntimeError('test release timeout')
            return {'ok':True}
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return self.body
        def response(url,**kwargs):
            result=Response()
            result.body=b'<div id="root"></div>' if url.endswith(':5173/') else b'{"ok":true}'
            return result
        with patch.object(self.app.time,'time',return_value=1800000000), patch.object(self.app.urllib.request,'urlopen',side_effect=response), patch.object(telegram_outbox,'backup_alerts'), patch.object(self.app,'backup',side_effect=slow_backup), patch.object(self.app.reliability,'restore',side_effect=lambda root:calls.append('restore') or {'ok':True}):
            def check():
                try:results.append(self.app.run('monitor'))
                finally:done.set()
            monitor=threading.Thread(target=check);monitor.start()
            try:
                self.assertTrue(done.wait(1),'monitor waited for backup')
                self.assertEqual(results[0]['backupMaintenance'],{'state':'started'})
                self.assertTrue(started.wait(1))
                self.assertTrue(self.app.BACKUP_CATCHUP_THREAD.daemon)
                self.assertEqual(self.app.run('monitor')['backupMaintenance'],{'state':'busy'})
                self.assertEqual(calls,['backup'])
            finally:
                release.set();monitor.join(3)
                if self.app.BACKUP_CATCHUP_THREAD:self.app.BACKUP_CATCHUP_THREAD.join(3)
            self.assertFalse(self.app.BACKUP_CATCHUP_THREAD.is_alive())
            self.assertEqual(calls,['backup','restore'])
            self.assertEqual(self.app.backup_maintenance()['state'],'throttled')
            self.assertFalse(self.app.LOCK.locked())

    def test_pending_integrations_are_not_claimed_active(self):
        r=self.app.readiness();self.assertFalse(r['automaticPublication']);self.assertFalse(r['externalChatExport'])
        self.assertEqual(r['integrations']['payments'],'not-configured')
    def test_report_has_no_paid_ai_or_personal_text(self):
        summary={'periodDays':7,'ai':[{'status':'timeout','calls':2,'averageMs':17000}],
                 'feedbackCounts':{'unsafe':1},'readiness':self.app.readiness()}
        with patch.object(self.app,'aggregates',return_value=summary):r=self.app.report(True)
        self.assertEqual(r['proposals'],3);self.assertFalse(r['externalMessagesSent'])
        data=json.loads(next((self.root/'reports').glob('*.json')).read_text(encoding='utf-8'))
        self.assertEqual(data['method'],'deterministic-aggregate-rules-not-ai');self.assertTrue(data['humanApprovalRequired'])
    def test_backup_encrypted_consistent_and_original_unchanged(self):
        for name in ('accounts.sqlite3','ops.sqlite3','budget.sqlite3'):
            with closing(sqlite3.connect(self.root/name)) as db:
                db.execute('CREATE TABLE t(v TEXT)');db.execute('INSERT INTO t VALUES(?)',('SYNTHETIC_PRIVATE_TEXT',));db.commit()
        original=(self.root/'accounts.sqlite3').read_bytes()
        with patch.object(self.app.ai_budget,'location',return_value=self.root/'budget.sqlite3'):result=self.app.backup()
        encrypted=(self.root/'backups'/result['file']).read_bytes();self.assertNotIn(b'SYNTHETIC_PRIVATE_TEXT',encrypted)
        with tarfile.open(fileobj=io.BytesIO(Fernet(self.key).decrypt(encrypted)),mode='r:gz') as tar:
            self.assertIn('accounts.sqlite',tar.getnames());self.assertIn('manifest.json',tar.getnames())
        self.assertEqual(original,(self.root/'accounts.sqlite3').read_bytes());self.assertTrue(result['verified'])
    def test_backup_recovers_hot_journal_without_committing_interrupted_changes(self):
        source=self.root/'automation-journal.sqlite'
        code="""import os,sqlite3,sys
db=sqlite3.connect(sys.argv[1]);db.execute('PRAGMA cache_size=5');db.execute('PRAGMA synchronous=FULL')
db.execute('CREATE TABLE sample(id INTEGER PRIMARY KEY,value TEXT)')
db.executemany('INSERT INTO sample VALUES(?,?)',((i,'committed-'+('x'*1000)) for i in range(120)));db.commit()
db.execute('BEGIN IMMEDIATE');db.execute("UPDATE sample SET value='uncommitted-'+value")
os._exit(0)
"""
        subprocess.run([sys.executable,'-c',code,str(source)],check=True)
        with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)) as db:
            with self.assertRaises(sqlite3.OperationalError) as error:db.execute('SELECT COUNT(*) FROM sample').fetchone()
            self.assertEqual(error.exception.sqlite_errorcode,sqlite3.SQLITE_READONLY_ROLLBACK)
        with patch.object(self.app.ai_budget,'location',return_value=self.root/'absent-budget.sqlite'):
            result=self.app.backup()
        self.assertTrue(result['verified'])
        restored=self.app.reliability.restore(self.root)
        self.assertEqual(restored['databases']['automation']['rows'],120)
        with closing(sqlite3.connect(source)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM sample WHERE value LIKE 'committed-%'").fetchone()[0],120)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_snapshot_does_not_create_a_missing_source(self):
        source=self.root/'missing.sqlite'
        with self.assertRaises(sqlite3.OperationalError):self.app.snapshot_database(source,self.root/'snapshot.sqlite')
        self.assertFalse(source.exists())

    def test_http_auth_origin_and_payload_guards(self):
        # Existing endpoint protection remains mandatory for feedback jobs too.
        server=self.app.ThreadingHTTPServer(('127.0.0.1',0),self.app.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def call(path,headers=None,body=b'{}'):
            req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}'+path,data=body,
                headers={'Host':'127.0.0.1:8792',**(headers or {})})
            try:
                with urllib.request.urlopen(req) as r:return r.status,json.load(r)
            except urllib.error.HTTPError as e:return e.code,json.load(e)
        try:
            self.assertEqual(call('/jobs/readiness')[0],401)
            auth={'Authorization':'Bearer synthetic-token'}
            self.assertEqual(call('/jobs/readiness',auth)[0],200)
            self.assertEqual(call('/jobs/readiness',{**auth,'Origin':'http://evil.test'})[0],403)
            self.assertEqual(call('/jobs/readiness',auth,b'{"chat":"PRIVATE"}')[0],400)
            self.assertEqual(call('/jobs/delete',auth)[0],404)
        finally:server.shutdown();server.server_close();thread.join()

    def test_feedback_review_backup_can_be_restored_in_isolation(self):
        for name in ('accounts.sqlite3','ops.sqlite3','budget.sqlite3','feedback-review/review.sqlite3'):
            path=self.root/name;path.parent.mkdir(exist_ok=True)
            with closing(sqlite3.connect(path)) as db:
                db.execute('CREATE TABLE sample(v TEXT)');db.execute("INSERT INTO sample VALUES('synthetic')");db.commit()
        with patch.object(self.app.ai_budget,'location',return_value=self.root/'budget.sqlite3'):
            self.app.backup()
        restored=self.app.reliability.restore(self.root)
        self.assertIn('feedback-review',restored['databases'])
        self.assertTrue(restored['isolated']);self.assertFalse(restored['workingDatabasesModified'])

    def test_duplicate_and_crash_are_not_reexecuted(self):
        calls=[]
        def action():calls.append(1);return {'ok':True,'value':3}
        r=self.app.reliability
        r.once(self.root,'test-key-01','backup',action)
        self.assertTrue(r.once(self.root,'test-key-01','backup',action)['replayed'])
        self.assertEqual(len(calls),1)
        with self.assertRaises(r.JobConflict):r.once(self.root,'test-key-01','monitor',action)
        def fail():raise RuntimeError('synthetic')
        with self.assertRaises(RuntimeError):r.once(self.root,'test-key-02','backup',fail)
        with self.assertRaises(r.JobConflict):r.once(self.root,'test-key-02','backup',action)
        self.assertEqual(len(calls),1)
        with closing(r.journal(self.root)) as db:
            db.execute("INSERT INTO runs VALUES('crashed-key','backup','running',NULL,0)");db.commit()
        self.assertEqual(r.recover_journal(self.root),1)
        with self.assertRaises(r.JobConflict):r.once(self.root,'crashed-key','backup',action)

    def test_simultaneous_duplicate_does_not_repeat_action(self):
        import concurrent.futures,time
        calls=[]
        def action():calls.append(1);time.sleep(.05);return {'ok':True}
        def attempt():
            try:return self.app.reliability.once(self.root,'parallel-key','backup',action)
            except self.app.reliability.JobConflict:return {'pending':True}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda _:attempt(),range(4)))
        self.assertEqual(len(calls),1)

    def test_failed_result_replays_without_repeating_work(self):
        calls=[]
        def action():calls.append(1);return {'ok':False,'error':'test-timeout'}
        r=self.app.reliability
        r.once(self.root,'failed-result-key','ai-tests',action)
        result=r.once(self.root,'failed-result-key','ai-tests',action)
        self.assertTrue(result['replayed']);self.assertFalse(result['ok'])
        self.assertEqual(result['error'],'test-timeout');self.assertEqual(len(calls),1)

    def test_slow_qa_does_not_block_monitor(self):
        started=threading.Event();release=threading.Event()
        def slow(_):started.set();release.wait(3);return {'ok':True}
        with patch.object(self.app.reliability,'qa',side_effect=slow),patch.object(self.app,'monitor',return_value={'ok':True}):
            worker=threading.Thread(target=lambda:self.app.run('ai-tests'));worker.start()
            self.assertTrue(started.wait(1))
            done=threading.Event()
            check=threading.Thread(target=lambda:(self.app.run('monitor'),done.set()));check.start()
            try:self.assertTrue(done.wait(.7),'monitor blocked by regression runner')
            finally:release.set();worker.join();check.join()
        self.assertIs(self.app.JOB_LOCKS['backup'],self.app.JOB_LOCKS['restore-check'])

    def test_restore_verifies_rows_and_keeps_original(self):
        with closing(sqlite3.connect(self.root/'accounts.sqlite3')) as db:
            db.execute('CREATE TABLE t(v TEXT)');db.execute("INSERT INTO t VALUES('synthetic')");db.commit()
        original=(self.root/'accounts.sqlite3').read_bytes()
        with patch.object(self.app.ai_budget,'location',return_value=self.root/'missing.sqlite'):self.app.backup()
        result=self.app.reliability.restore(self.root)
        self.assertEqual(result['databases']['accounts']['rows'],1)
        self.assertEqual(original,(self.root/'accounts.sqlite3').read_bytes())
        self.assertFalse(any(self.root.glob('restore-drill-*')))
        archive=next((self.root/'backups').glob('*.enc'));archive.write_bytes(b'tampered')
        with self.assertRaises(Exception):self.app.reliability.restore(self.root)

    def test_error_metadata_is_restricted_and_deduplicated(self):
        r=self.app.reliability
        for _ in range(2):r.incident(self.root,{'workflowId':'mamaLocal01','executionId':'123'})
        with closing(r.journal(self.root)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM incidents').fetchone()[0],1)
        with self.assertRaises(ValueError):r.incident(self.root,{'workflowId':'x','executionId':'123','chat':'PRIVATE'})

if __name__=='__main__':unittest.main()
