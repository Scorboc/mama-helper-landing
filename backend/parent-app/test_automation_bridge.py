import importlib.util, io, json, os, sqlite3, tarfile, tempfile, threading, unittest, urllib.request, urllib.error
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
