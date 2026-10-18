"""Synthetic owner notifications; no Telegram calls or real account data."""
import io,json,sqlite3,tempfile,time,unittest,urllib.error
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
from cryptography.fernet import Fernet
import telegram_outbox as app

class TelegramTest(unittest.TestCase):
    def setUp(self):
        self.poll_patch=patch('telegram_admin.poll',return_value=0);self.poll_patch.start();self.addCleanup(self.poll_patch.stop)
        self.balance_patch=patch('proxy_balance.collect',return_value=None);self.balance_patch.start();self.addCleanup(self.balance_patch.stop)
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.key=Fernet.generate_key();(self.root/'backup.key').write_bytes(self.key)
        self.cfg={'botToken':'123456789:'+('A'*35),'chatId':'123456','username':'MomF1_bot','enabledAt':1}
        self.save()
    def save(self):
        (self.root/'telegram-settings.enc').write_bytes(Fernet(self.key).encrypt(json.dumps(self.cfg).encode()))
    def tearDown(self):self.tmp.cleanup()
    def test_token_is_encrypted_and_groups_rejected(self):
        self.assertNotIn(self.cfg['botToken'].encode(),(self.root/'telegram-settings.enc').read_bytes())
        self.cfg['chatId']='-100123';self.save()
        with self.assertRaises(ValueError):app.config(self.root)
    def test_missing_configuration_cannot_send(self):
        (self.root/'telegram-settings.enc').unlink()
        with patch.object(app,'send') as send:
            self.assertFalse(app.dispatch(self.root)['configured']);send.assert_not_called()
    def test_duplicate_message_is_sent_once(self):
        app.welcome(self.root);app.welcome(self.root)
        with patch.object(app,'send',return_value={'state':'sent','message_id':77}) as send:
            self.assertEqual(app.dispatch(self.root)['sent'],1)
            self.assertEqual(app.dispatch(self.root)['sent'],0);self.assertEqual(send.call_count,1)
    def test_rejected_request_retries_after_delay(self):
        app.welcome(self.root)
        with patch.object(app.time,'time',return_value=1000),patch.object(app,'send',return_value={'state':'queued','wait':120,'error_code':'rate-limited'}) as send:
            app.dispatch(self.root);app.dispatch(self.root);self.assertEqual(send.call_count,1)
        with patch.object(app.time,'time',return_value=1121),patch.object(app,'send',return_value={'state':'sent','message_id':88}):
            self.assertEqual(app.dispatch(self.root)['sent'],1)
    def test_unknown_delivery_does_not_automatically_duplicate(self):
        app.welcome(self.root)
        with patch.object(app,'send',return_value={'state':'uncertain','error_code':'delivery-unconfirmed'}) as send:
            app.dispatch(self.root);app.dispatch(self.root);self.assertEqual(send.call_count,1)
        with closing(app.database(self.root)) as db:self.assertEqual(db.execute('SELECT state FROM messages').fetchone()[0],'uncertain')
    def test_interrupted_sender_is_not_replayed(self):
        app.welcome(self.root)
        with closing(app.database(self.root)) as db:
            db.execute("UPDATE messages SET state='sending',started=0");db.commit()
        with patch.object(app,'send') as send:
            result=app.dispatch(self.root);send.assert_not_called()
        self.assertEqual(result['counts']['uncertain'],1)
    def test_report_and_error_templates_do_not_export_free_text(self):
        reports=self.root/'reports';reports.mkdir()
        data={'generatedAt':'2026-10-17T10:00:00+00:00','method':'deterministic-aggregate-rules-not-ai','summary':{'ai':[{'status':'error','calls':3,'averageMs':16000,'question':'PRIVATE_CHILD_TEXT'}],'feedbackCounts':{'unsafe':1}},'proposals':[{'prompt':'PRIVATE_CHILD_TEXT'}],'chat':'PRIVATE_CHILD_TEXT'}
        (reports/'daily-20261017.json').write_text(json.dumps(data),encoding='utf-8')
        with closing(sqlite3.connect(self.root/'automation-journal.sqlite')) as db:
            db.execute('CREATE TABLE incidents(workflow TEXT,execution TEXT,at INTEGER)')
            db.executemany('INSERT INTO incidents VALUES(?,?,?)',[('mamaLocal01','12',1801),('mamaLocal01','13',1802)]);db.commit()
        app.collect(self.root);app.collect(self.root)
        with closing(app.database(self.root)) as db:
            rows=db.execute('SELECT kind,body FROM messages').fetchall()
        self.assertEqual(sum(r['kind']=='error' for r in rows),1)
        self.assertNotIn('PRIVATE_CHILD_TEXT',' '.join(r['body'] for r in rows))
        self.assertEqual(len(rows),4)
    def test_telegram_rate_limit_honors_retry_after(self):
        error=urllib.error.HTTPError('redacted',429,'limited',{},io.BytesIO(b'{"ok":false,"parameters":{"retry_after":600}}'))
        with patch.object(app.urllib.request,'urlopen',side_effect=error):result=app.send(self.cfg,'Synthetic test')
        self.assertEqual(result['state'],'queued');self.assertEqual(result['wait'],600)

if __name__=='__main__':unittest.main()
