import calendar
from datetime import date, datetime, timedelta, timezone
import json
import os
import time
import unittest
from unittest.mock import patch
import test_api as base
import billing
import legal

app = base.app


class BillingTest(unittest.TestCase):
    call = base.AccountsTest.call
    tearDown = base.AccountsTest.tearDown

    def setUp(self):
        base.AccountsTest.setUp(self)
        os.environ['APP_BILLING_MODE'] = 'paid'
        os.environ['APP_PUBLIC_URL'] = 'https://mama.example.test'

    def register(self, email='paid@example.test'):
        response, body = self.call('register', email=email, password='long-test-password', adult=True, termsAccepted=True, termsVersion=legal.TERMS_VERSION)
        self.assertEqual(response['statusCode'],200,body)
        return response['headers']['Set-Cookie'].split(';')[0],body

    def parent(self, email='paid@example.test'):
        cookie, body = self.register(email)
        state = body['state']
        state['profile']={'childName':'Синтетический','childSex':'unknown','role':'mom','stage':'child','birthDate':(date.today()-timedelta(days=200)).isoformat(),'week':20,'weekDate':date.today().isoformat(),'feeding':'unknown','sleep':'','health':'','healthConfirmed':False,'topics':[]}
        self.assertEqual(self.call('save',cookie,state=state,revision=0)[0]['statusCode'],200)
        return cookie,body['user']['id']

    def ask(self, cookie, ident='q1', question='Что можно приготовить для себя?'):
        session=self.call('session',cookie)[1]
        return self.call('chat',cookie,messageId=ident,question=question,revision=session['revision'])

    def grant(self, email='paid@example.test', **kwargs):
        db=app.DB()
        try: return billing.owner_grant(db,email,**kwargs)
        finally: db.close()

    def payment(self, **changes):
        return {**{'id':'fake-payment-123','status':'pending','paid':False,'test':False,
                   'amount':{'value':'480.00','currency':'RUB'},
                   'confirmation':{'confirmation_url':'https://yoomoney.ru/checkout/payments/v2/contract'},
                   'metadata':{'mama_order':self.order}}, **changes}

    def checkout(self, cookie):
        def fake(method,path,body=None,key=None):
            if method=='POST':
                self.order=key; self.sent=body
            return self.payment()
        with patch.object(billing,'payment_ready',return_value=True), patch.object(billing,'vendor',side_effect=fake):
            return self.call('billing-create',cookie,offerAccepted=True,offerVersion=legal.OFFER_VERSION)

    def test_new_paid_account_has_no_automatic_free_trial_or_test_grant(self):
        cookie,uid=self.parent()
        self.assertEqual(self.call('session',cookie)[1]['billing']['mode'],'none')
        self.assertEqual(self.call('session',cookie)[1]['quota']['remaining'],0)
        with patch.object(app,'chat_answer') as ai:
            self.assertEqual(self.ask(cookie)[0]['statusCode'],402); ai.assert_not_called()
        self.assertEqual(self.call('care-list',cookie)[0]['statusCode'],200)
        self.assertEqual(self.call('grant-test',cookie,login='paid@example.test')[0]['statusCode'],404)

    def test_separate_adult_and_terms_checks_and_versioned_document_receipt(self):
        for fields in ({'adult':False,'termsAccepted':True}, {'adult':True,'termsAccepted':False}, {'consent':True}):
            self.assertEqual(self.call('register',email='no@example.test',password='long-test-password',termsVersion=legal.TERMS_VERSION,**fields)[0]['statusCode'],400)
        cookie,body=self.register()
        db=app.DB()
        row=db.query('SELECT kind,version,document_text FROM mh_contract_receipts WHERE user_id=?',(body['user']['id'],)).fetchone(); db.close()
        self.assertEqual(row[:2],('account',legal.TERMS_VERSION)); self.assertIn('не является согласием',row[2])

    def test_manual_free_grant_can_expire_extend_and_revoke_without_resetting_answers(self):
        cookie,uid=self.parent()
        self.grant(limit=3)
        with patch.object(app,'chat_answer',return_value='Синтетический ответ.'):
            self.assertEqual(self.ask(cookie)[1]['quota']['remaining'],2)
        self.grant(days=45,limit=3)
        self.assertEqual(self.call('session',cookie)[1]['quota']['remaining'],2)
        self.grant(revoke=True)
        self.assertEqual(self.call('session',cookie)[1]['billing']['mode'],'none')
        self.assertEqual(self.ask(cookie,'q2')[0]['statusCode'],402)
        self.assertTrue(self.call('session',cookie)[1]['state']['messages'])

    def test_unpaid_emergency_and_profile_protection_do_not_call_provider(self):
        cookie,uid=self.parent()
        with patch.object(app,'chat_answer') as ai:
            response, body = self.ask(cookie,question='Ребёнок не дышит')
            self.assertEqual(response['statusCode'],200); self.assertIn('112',body['answer']); ai.assert_not_called()

    def test_ai_errors_and_same_message_retries_do_not_spend_extra(self):
        cookie,uid=self.parent(); self.grant(limit=3)
        with patch.object(app,'chat_answer',side_effect=app.AppError(503,'Синтетическая ошибка')):
            self.assertEqual(self.ask(cookie)[0]['statusCode'],503)
        self.assertEqual(self.call('session',cookie)[1]['quota']['used'],0)
        with patch.object(app,'chat_answer',return_value='Синтетический ответ.'):
            self.ask(cookie); self.ask(cookie)
        self.assertEqual(self.call('session',cookie)[1]['quota']['used'],1)

    def test_disconnected_payment_does_not_create_orders(self):
        cookie,body=self.register()
        self.assertEqual(self.call('billing-create',cookie,offerAccepted=True,offerVersion=legal.OFFER_VERSION)[0]['statusCode'],503)
        db=app.DB(); self.assertEqual(db.query('SELECT COUNT(*) FROM mh_billing_orders').fetchone()[0],0); db.close()

    def test_checkout_fixed_price_no_recurring_and_recovers_same_order(self):
        cookie,body=self.register()
        response,order=self.checkout(cookie); self.assertEqual(response['statusCode'],200,order)
        self.assertEqual(self.sent['amount'],{'value':'480.00','currency':'RUB'}); self.assertFalse(self.sent['save_payment_method'])
        with patch.object(billing,'payment_ready',return_value=True), patch.object(billing,'vendor',return_value=self.payment()) as network:
            repeated=self.call('billing-create',cookie,offerAccepted=True,offerVersion=legal.OFFER_VERSION,amount='0.01')[1]
            self.assertEqual(repeated['orderId'],order['orderId']); self.assertEqual(network.call_count,1)
        self.assertEqual(self.call('session',cookie)[1]['billing']['mode'],'none')

    def test_trusted_confirmation_fulfills_once_and_uses_calendar_month(self):
        cookie,body=self.register(); self.checkout(cookie)
        with patch.object(billing,'vendor',return_value=self.payment(status='succeeded',paid=True)):
            response,checked=self.call('billing-check',cookie,orderId=self.order)
            self.assertEqual(response['statusCode'],200,checked)
            self.assertEqual(checked['billing']['mode'],'paid')
            end=checked['billing']['endsAt']
            self.call('billing-check',cookie,orderId=self.order)
            self.assertEqual(self.call('session',cookie)[1]['billing']['endsAt'],end)
        self.assertEqual(self.call('session',cookie)[1]['quota']['remaining'],300)
        jan31=int(datetime(2026,1,31,14,tzinfo=timezone.utc).timestamp())
        self.assertEqual(datetime.fromtimestamp(billing.next_month(jan31),timezone.utc).isoformat(),'2026-02-28T14:00:00+00:00')

    def test_tampered_currency_amount_order_and_test_payment_never_grant_access(self):
        cookie,body=self.register(); self.checkout(cookie)
        for change in ({'amount':{'value':'1.00','currency':'RUB'}},{'amount':{'value':'480.00','currency':'USD'}},{'metadata':{'mama_order':'other'}},{'test':True}):
            with patch.object(billing,'vendor',return_value=self.payment(status='succeeded',paid=True,**change)):
                self.assertEqual(self.call('billing-check',cookie,orderId=self.order)[0]['statusCode'],409)
            self.assertEqual(self.call('session',cookie)[1]['billing']['mode'],'none')

    def test_other_account_cannot_read_or_check_order(self):
        cookie,body=self.register(); self.checkout(cookie)
        other,_=self.register('other@example.test')
        with patch.object(billing,'vendor') as network:
            self.assertEqual(self.call('billing-check',other,orderId=self.order)[0]['statusCode'],404); network.assert_not_called()

    def test_webhook_body_cannot_fake_success(self):
        cookie,body=self.register(); self.checkout(cookie)
        db=app.DB()
        try:
            with patch.object(billing,'payment_ready',return_value=True), patch.object(billing,'vendor',return_value=self.payment(status='pending',paid=False)):
                billing.webhook(app,db,{'event':'payment.succeeded','object':self.payment(status='succeeded',paid=True)})
            db.conn.commit()
        finally: db.close()
        self.assertEqual(self.call('session',cookie)[1]['billing']['mode'],'none')

    def test_deletion_preserves_order_for_financial_review_without_attaching_another_account(self):
        cookie,body=self.register(); self.checkout(cookie)
        self.assertEqual(self.call('delete',cookie,password='long-test-password')[0]['statusCode'],200)
        db=app.DB(); self.assertIsNone(db.query('SELECT user_id FROM mh_billing_orders WHERE id=?',(self.order,)).fetchone()[0]); db.close()

    def test_data_requests_are_encrypted_scoped_and_idempotent(self):
        cookie,body=self.register(); other,_=self.register('other@example.test')
        fields={'kind':'correct','text':'Синтетическая ошибка даты','requestId':'request-1'}
        self.assertEqual(self.call('data-request',cookie,**fields)[0]['statusCode'],200)
        self.assertEqual(self.call('data-request',cookie,**fields)[0]['statusCode'],200)
        self.assertEqual(len(self.call('data-request-list',cookie)[1]['items']),1)
        self.assertFalse(self.call('data-request-list',other)[1]['items'])
        self.assertEqual(self.call('data-request',other,**fields)[0]['statusCode'],409)
        db=app.DB(); raw=db.query('SELECT encrypted_text FROM mh_data_requests').fetchone()[0]; db.close(); self.assertNotIn(fields['text'],raw)

    def test_data_export_needs_current_password_and_contains_no_credentials(self):
        cookie,body=self.register()
        self.assertEqual(self.call('data-export',cookie,password='wrong-password')[0]['statusCode'],401)
        response,result=self.call('data-export',cookie,password='long-test-password')
        self.assertEqual(response['statusCode'],200)
        for secret in ('password_hash','recovery_hash','token_hash',body['recoveryCode']): self.assertNotIn(secret,json.dumps(result))

    def test_withdraw_stops_new_ai_without_erasing_history_and_urgent_help(self):
        cookie,uid=self.parent(); self.grant()
        self.assertEqual(self.call('data-request',cookie,kind='withdraw',text='Синтетический запрос прекращения',requestId='withdraw-1')[0]['statusCode'],200)
        with patch.object(app,'chat_answer') as ai:
            self.assertEqual(self.ask(cookie)[0]['statusCode'],403); ai.assert_not_called()
            self.assertEqual(self.ask(cookie,'urgent','Ребёнок не дышит')[0]['statusCode'],200)
        self.assertEqual(self.call('data-export',cookie,password='long-test-password')[0]['statusCode'],200)

    def test_daily_ai_selection_shares_allowance_cached_and_catalog_do_not_charge(self):
        cookie,uid=self.parent(); self.grant(limit=1)
        def fake(question,context,**kwargs):
            candidates=json.loads(context)['candidates']
            return json.dumps({'ids':[item['id'] for item in candidates[:3]]})
        with patch.object(app,'chat_answer',side_effect=fake) as ai:
            response,empty=self.call('daily-plan',cookie)
            self.assertEqual(response['statusCode'],200,empty)
            self.assertIsNone(empty['plan']); self.assertEqual(empty['quota']['used'],0); ai.assert_not_called()
            response,first=self.call('daily-create',cookie)
            self.assertEqual(response['statusCode'],200,first)
            self.assertEqual(first['source'],'ai'); self.assertEqual(first['quota']['remaining'],0)
            saved=self.call('daily-plan',cookie)[1]
            self.assertEqual(saved['plan']['items'],first['items']); self.assertEqual(saved['quota']['used'],1)
            again=self.call('daily-create',cookie)[1]
            self.assertEqual(again['quota']['used'],1); self.assertEqual(ai.call_count,1)
        self.assertEqual(self.ask(cookie)[0]['statusCode'],429)
        db=app.DB();db.query('DELETE FROM mh_daily WHERE user_id=?',(uid,));db.conn.commit();db.close()
        with patch.object(app,'chat_answer') as ai:
            response,plan=self.call('daily-create',cookie)
            self.assertEqual(response['statusCode'],200,plan); self.assertEqual(plan['source'],'library');ai.assert_not_called()
        self.assertEqual(plan['quota']['used'],1)

    def test_public_registration_is_closed_without_operator_details(self):
        os.environ['APP_LOCAL']='0'
        os.environ['APP_DB_DRIVER']='sqlite'
        self.assertEqual(self.call('register',email='public@example.test',password='long-test-password',adult=True,termsAccepted=True,termsVersion=legal.TERMS_VERSION)[0]['statusCode'],503)

    def test_public_purchase_requires_individual_written_health_authorization(self):
        cookie,body=self.register()
        os.environ.update(APP_LOCAL='0',APP_DB_DRIVER='sqlite')
        with patch.object(billing,'payment_ready',return_value=True),patch.object(billing,'vendor') as provider:
            self.assertEqual(self.call('billing-create',cookie,offerAccepted=True,offerVersion=legal.OFFER_VERSION)[0]['statusCode'],403)
            provider.assert_not_called()

    def test_month_end_uses_contract_moscow_timezone(self):
        stamp=int(datetime(2026,1,29,21,30,tzinfo=timezone.utc).timestamp())
        self.assertEqual(datetime.fromtimestamp(billing.next_month(stamp),timezone.utc).isoformat(),'2026-02-27T21:30:00+00:00')
