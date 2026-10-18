import unittest,tempfile
from pathlib import Path
from contextlib import closing
from datetime import date
from unittest.mock import patch
import telegram_billing as app
import telegram_outbox as outbox
import telegram_admin

class BillingTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def test_month_anchor_and_leap_year(self):
        self.assertEqual(app.next_due(date(2026,1,31),'monthly',31),date(2026,2,28))
        self.assertEqual(app.next_due(date(2026,2,28),'monthly',31),date(2026,3,31))
        self.assertEqual(app.next_due(date(2024,2,29),'yearly',29),date(2025,2,28))
    def test_manual_payment_idempotency(self):
        with closing(outbox.database(self.root)) as db:
            app.command(db,'/bill_add','Codex | 100 | USD | 2026-10-31 | monthly')
            app.command(db,'/paid','1 2026-10-31');app.command(db,'/paid','1 2026-10-31')
            self.assertEqual(db.execute('SELECT due FROM admin_bills').fetchone()[0],'2026-11-30')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM admin_bill_payments').fetchone()[0],1)
    def test_invalid_amount_and_wrong_date(self):
        with closing(outbox.database(self.root)) as db:
            for amount in ('NaN','Infinity','-1','1000001'):
                app.command(db,'/bill_add',f'Test | {amount} | RUB | 2026-10-31 | monthly')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM admin_bills').fetchone()[0],0)
            app.command(db,'/bill_add','Server | 500 | RUB | 2026-10-31 | monthly')
            self.assertIn('не совпадает',app.command(db,'/paid','1 2026-10-30'))
    def test_reminders_dedup_pause_and_totals(self):
        with closing(outbox.database(self.root)) as db:
            app.command(db,'/bill_add','Server | 1500 | RUB | 2026-11-01 | monthly')
            app.command(db,'/bill_add','Annual | 120 | USD | 2026-11-01 | yearly');db.commit()
            listing=app.command(db,'/bills','');self.assertIn('10.00 USD',listing);self.assertIn('1500.00 RUB',listing)
        with patch.object(app,'today',return_value=date(2026,10,25)):
            app.collect(self.root);app.collect(self.root)
        with closing(outbox.database(self.root)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM messages').fetchone()[0],2)
            app.command(db,'/bill_pause','1');db.commit()
        with patch.object(app,'today',return_value=date(2026,10,31)):app.collect(self.root)
        with closing(outbox.database(self.root)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM messages').fetchone()[0],3)
    def test_help_fits_message_and_covers_scope(self):
        self.assertLess(len(telegram_admin.HELP),3500)
        for token in ('/task','/status','/paid','/bills','НЕ останавливает','/publish T123','GitHub','сервера аккаунтов'):self.assertIn(token,telegram_admin.HELP)
    def test_paid_cancels_pending_reminder(self):
        with closing(outbox.database(self.root)) as db:
            app.command(db,'/bill_add','Server | 1000 | RUB | 2026-11-01 | monthly');db.commit()
        with patch.object(app,'today',return_value=date(2026,10,31)):app.collect(self.root)
        with closing(outbox.database(self.root)) as db:
            app.command(db,'/paid','1 2026-11-01');db.commit()
            self.assertEqual(db.execute('SELECT state FROM messages').fetchone()[0],'cancelled')

if __name__=='__main__':unittest.main()
