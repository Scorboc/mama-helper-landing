import io,json,tempfile,unittest,urllib.error
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
import proxy_balance as app
import telegram_outbox as outbox

class BalanceTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def rows(self):
        with closing(outbox.database(self.root)) as db:return db.execute('SELECT * FROM messages').fetchall()
    def test_permission_denied_not_zero(self):
        with patch.object(app,'fetch',return_value={'ok':False,'error':'permission-required'}):app.collect(self.root)
        with closing(outbox.database(self.root)) as db:
            text=app.command(db,'/balance','');self.assertIn('неизвестен',text);self.assertNotIn('0 ₽',text)
        self.assertIn('403',self.rows()[0]['body'])
    def test_ttl_and_no_duplicate_low_alert(self):
        with patch.object(app,'fetch',return_value={'ok':True,'balance':'190','scope':'account','currency':'RUB'}) as fetch,patch.object(app.time,'time',return_value=100000):
            app.collect(self.root);app.collect(self.root);self.assertEqual(fetch.call_count,1)
        with patch.object(app,'fetch',return_value={'ok':True,'balance':'190','scope':'account','currency':'RUB'}),patch.object(app.time,'time',return_value=101000):app.collect(self.root)
        self.assertEqual(len(self.rows()),1)
    def test_key_budget_is_labelled_and_recovery(self):
        with patch.object(app,'fetch',return_value={'ok':True,'balance':'20','scope':'key-budget','currency':'RUB'}),patch.object(app.time,'time',return_value=100000):app.collect(self.root)
        self.assertIn('не баланс аккаунта',self.rows()[0]['body'])
        with patch.object(app,'fetch',return_value={'ok':True,'balance':'900','scope':'key-budget','currency':'RUB'}),patch.object(app.time,'time',return_value=101000):app.collect(self.root)
        self.assertEqual(len(self.rows()),2)
    def test_bad_thresholds_and_payment_links(self):
        with closing(outbox.database(self.root)) as db:
            self.assertIn('три убывающих',app.command(db,'/balance_alerts','50 200 500'))
            app.command(db,'/balance_alerts','1000 300 100');self.assertEqual(app.get(db,'thresholds'),[1000,300,100])
            self.assertIn(app.CONSOLE,app.command(db,'/payments',''))
    def test_fetch_403_is_sanitized(self):
        error=urllib.error.HTTPError('https://api.proxyapi.ru',403,'forbidden',{},io.BytesIO(b'PRIVATE_PROVIDER_BODY'))
        with patch.object(app.urllib.request,'build_opener') as build:
            build.return_value.open.side_effect=error;result=app.fetch('SECRET')
        self.assertEqual(result['error'],'permission-required');self.assertNotIn('SECRET',str(result));self.assertNotIn('PRIVATE',str(result))

if __name__=='__main__':unittest.main()
