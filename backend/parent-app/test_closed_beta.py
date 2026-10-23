"""Closed beta regressions: temporary databases, synthetic users, mocked AI only."""
from decimal import Decimal
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import closed_beta
import ai_budget
import test_billing as base


class ClosedBetaTest(unittest.TestCase):
    call = base.BillingTest.call
    ask = base.BillingTest.ask
    parent = base.BillingTest.parent

    def setUp(self):
        base.BillingTest.setUp(self)
        self.addCleanup(base.BillingTest.tearDown, self)
        os.environ.update(APP_CLOSED_BETA='1', APP_BETA_ANSWER_LIMIT='10',
                          APP_BETA_MONTH_RUB='300', APP_BETA_INVITES_FILE=self.temp.name+'/invites.json',
                          APP_AI_BUDGET_PATH=self.temp.name+'/budget.db')

    def register(self, email='paid@example.test'):
        invite=closed_beta.create_invite(os.environ['APP_BETA_INVITES_FILE'])
        response,body=self.call('register', email=email, password='long-test-password',
            adult=True, termsAccepted=True, termsVersion=base.legal.TERMS_VERSION, invite=invite)
        self.assertEqual(response['statusCode'],200,body)
        return response['headers']['Set-Cookie'].split(';')[0],body

    def test_invitation_required_expired_invalid_replay_and_existing_login(self):
        fields=dict(email='new@example.test',password='long-test-password',adult=True,
                    termsAccepted=True,termsVersion=base.legal.TERMS_VERSION)
        for token in ('','invalid',closed_beta.create_invite(os.environ['APP_BETA_INVITES_FILE'],days=-1)):
            self.assertEqual(self.call('register',invite=token,**fields)[0]['statusCode'],403)
        token=closed_beta.create_invite(os.environ['APP_BETA_INVITES_FILE'])
        self.assertEqual(self.call('register',invite=token,**fields)[0]['statusCode'],200)
        self.assertEqual(self.call('register',invite=token,**{**fields,'email':'other@example.test'})[0]['statusCode'],403)
        self.assertEqual(self.call('login',email=fields['email'],password=fields['password'])[0]['statusCode'],200)
        # An account created before the switch can still log in.
        with patch.dict(os.environ,APP_CLOSED_BETA='0'):
            base.BillingTest.register(self,'existing@example.test')
        self.assertEqual(self.call('login',email='existing@example.test',password=fields['password'])[0]['statusCode'],200)

    def test_public_registration_requires_documents_even_in_beta(self):
        invite=closed_beta.create_invite(os.environ['APP_BETA_INVITES_FILE'])
        with patch.dict(os.environ,APP_LOCAL='0',APP_DB_DRIVER='sqlite'), \
                patch.object(base.legal,'public',return_value={'documentsReady':False}):
            self.assertTrue(closed_beta.enabled())
            response,body=self.call('register',email='public-beta@example.test',
                password='long-test-password',adult=True,termsAccepted=True,
                termsVersion=base.legal.TERMS_VERSION,invite=invite)
        self.assertEqual(response['statusCode'],503,body)

    def test_tenth_answer_eleventh_message_and_emergency(self):
        cookie,uid=self.parent()
        with patch.object(base.app,'chat_answer',return_value='Можно приготовить простой обед.') as ai:
            for i in range(10):
                response,body=self.ask(cookie,'q'+str(i))
                self.assertEqual(response['statusCode'],200,body)
            self.assertEqual(body['quota']['remaining'],0)
            response,body=self.ask(cookie,'q11')
            self.assertEqual(response['statusCode'],429,body)
            self.assertIn('Данные и обращения',body['error'])
            self.assertEqual(ai.call_count,10)
            response,body=self.ask(cookie,'urgent','Ребёнок не дышит')
            self.assertEqual(response['statusCode'],200,body)
            self.assertIn('112',body['answer'])
            self.assertEqual(ai.call_count,10)

    def test_payments_blocked_and_public_configuration(self):
        cookie,_=self.register()
        self.assertTrue(self.call('config')[1]['billing']['closedBeta'])
        self.assertFalse(base.billing.payment_ready())
        with patch.object(base.billing,'vendor') as vendor:
            self.assertEqual(self.call('billing-create',cookie)[0]['statusCode'],409)
            self.assertEqual(self.call('billing-check',cookie,orderId='a'*32)[0]['statusCode'],409)
            vendor.assert_not_called()
        source=(Path(__file__).parents[2]/'src/pages/Billing.tsx').read_text(encoding='utf-8')
        self.assertIn('billing?.paymentConfigured && !billing.closedBeta',source)
        self.assertIn('Оплата откроется позже',source)

    def test_month_cap_overrides_policy_and_blocks_before_provider(self):
        policy=Path(self.temp.name)/'policy.json'
        policy.write_text('{"AI_BUDGET_MONTH_RUB":"1000"}',encoding='utf-8')
        os.environ.update(AI_POLICY_FILE=str(policy),AI_BUDGET_DAY_RUB='1000')
        self.assertEqual(ai_budget.config()[1],300*ai_budget.MICRO)
        with patch.object(ai_budget,'rates',return_value=(Decimal('0'),Decimal('300000000'),'2026-10-21')):
            ai_budget.reserve('synthetic','chat',0,1)
            with self.assertRaises(ai_budget.BudgetError) as error:
                ai_budget.reserve('synthetic','daily',0,1)
            self.assertEqual(error.exception.status,429)
            self.assertIn('112',error.exception.message)


if __name__ == '__main__':
    unittest.main()
