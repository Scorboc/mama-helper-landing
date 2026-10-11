"""Quota and spend gates with synthetic data and no external provider access."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo
import ai_budget as budget
import test_api as base

app = base.app
MODEL = 'z-ai/glm-5.3-flash'


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mama-budget-qa-')
        self.env = patch.dict(os.environ, {'APP_AI_BUDGET_PATH':str(Path(self.temp.name)/'budget.sqlite3'),
                     'APP_DATA_KEY':'synthetic-key','AI_BUDGET_DAY_RUB':'100','AI_BUDGET_MONTH_RUB':'1000'},clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop(); self.temp.cleanup()

    def test_concurrent_reservations_cannot_spend_the_same_budget(self):
        amount = budget.price(1124, 20, Decimal('10.11'), Decimal('33.68'))
        os.environ.update(AI_BUDGET_DAY_RUB=str(Decimal(amount)/budget.MICRO),AI_MAX_CONCURRENT_CALLS='20')
        def reserve(number):
            try:
                with budget.scope('synthetic-'+str(number),str(number)):
                    return budget.reserve(MODEL,'chat',100,20)
            except budget.BudgetError as error:
                self.assertEqual(error.status,429)
                return None
        with ThreadPoolExecutor(max_workers=12) as pool:
            ids=list(pool.map(reserve,range(12)))
        self.assertEqual(sum(value is not None for value in ids),1)
        with budget.database() as db:
            self.assertEqual(db.execute('SELECT SUM(accounted_micro) FROM ai_spend').fetchone()[0],amount)

    def test_known_usage_reconciles_but_unknown_and_abandoned_keep_reserve(self):
        first=budget.reserve(MODEL,'chat',1000,100)
        budget.finish(first,{'prompt_tokens':100,'completion_tokens':20},'ok')
        second=budget.reserve(MODEL,'daily',1000,100)
        with budget.database() as db:
            reserved=db.execute('SELECT accounted_micro FROM ai_spend WHERE id=?',(second,)).fetchone()[0]
        budget.finish(second,None,'error')
        result=budget.summary()
        self.assertAlmostEqual(result['today']['estimatedRub'],budget.price(100,20,Decimal('10.11'),Decimal('33.68'))/budget.MICRO)
        self.assertEqual(result['today']['reservedRub'],reserved/budget.MICRO)
        self.assertEqual(result['today']['unknownUsage'],1)
        with budget.scope('old-request','old'):
            old=budget.reserve(MODEL,'chat',1000,100)
        with budget.database() as db:
            db.execute('UPDATE ai_spend SET started=started-301 WHERE id=?',(old,))
        with budget.scope('old-request','new'):
            budget.reserve(MODEL,'chat',1000,100)
        with budget.database() as db:
            status,money=db.execute('SELECT status,accounted_micro FROM ai_spend WHERE id=?',(old,)).fetchone()
        self.assertEqual(status,'unknown'); self.assertGreater(money,0)

    def test_month_cap_and_moscow_day_boundary(self):
        amount=budget.price(1124,20,Decimal('10.11'),Decimal('33.68'))
        os.environ['AI_BUDGET_MONTH_RUB']=str(Decimal(amount)/budget.MICRO)
        stamp=lambda text:datetime.fromisoformat(text).replace(tzinfo=ZoneInfo('Europe/Moscow')).timestamp()
        with patch.object(budget.time,'time',return_value=stamp('2026-10-11T23:59:00')):
            budget.reserve(MODEL,'chat',100,20)
        with patch.object(budget.time,'time',return_value=stamp('2026-10-12T00:01:00')):
            with self.assertRaises(budget.BudgetError):budget.reserve(MODEL,'daily',100,20)
        with patch.object(budget.time,'time',return_value=stamp('2026-11-01T00:01:00')):
            budget.reserve(MODEL,'chat',100,20)
        with budget.database() as db:
            self.assertEqual(db.execute('SELECT day FROM ai_spend ORDER BY started').fetchall(),[('2026-10-11',),('2026-11-01',)])

    def test_actor_inflight_size_unknown_model_and_bad_prices_fail_closed(self):
        with budget.scope('synthetic-parent','first'):
            budget.reserve(MODEL,'chat',100,20)
        with budget.scope('synthetic-parent','second'):
            with self.assertRaises(budget.BudgetError) as error:budget.reserve(MODEL,'daily',100,20)
            self.assertEqual(error.exception.status,409)
        with self.assertRaises(budget.BudgetError):budget.reserve(MODEL,'chat',200000,20)
        with self.assertRaises(budget.BudgetError):budget.reserve('unverified-model','chat',100,20)
        with patch.dict(os.environ,AI_BUDGET_DAY_RUB='NaN'):
            with self.assertRaises(budget.BudgetError):budget.reserve(MODEL,'chat',100,20)
        with budget.database() as db:
            rows=str(db.execute('SELECT * FROM ai_spend').fetchall())
        self.assertNotIn('synthetic-parent',rows);self.assertNotIn('first',rows)

    def test_owner_policy_edits_are_validated_and_do_not_reset_spending(self):
        policy=Path(self.temp.name)/'ai-policy.json';policy.write_text('{}',encoding='utf-8')
        os.environ['AI_POLICY_FILE']=str(policy)
        request=budget.reserve(MODEL,'chat',100,20)
        budget.finish(request,{'prompt_tokens':100,'completion_tokens':20},'ok')
        before=budget.summary()['today']['accountedRub']
        updated=budget.write_policy({'dailyLimitRub':0,'monthlyLimitRub':5,'freeChatLimit':3})
        self.assertEqual(updated['today']['accountedRub'],before)
        with self.assertRaises(budget.BudgetError):budget.reserve(MODEL,'chat',100,20)
        for body in ({'dailyLimitRub':-1,'monthlyLimitRub':5,'freeChatLimit':3},
                     {'dailyLimitRub':1,'monthlyLimitRub':5,'freeChatLimit':True},
                     {'dailyLimitRub':1,'monthlyLimitRub':5,'freeChatLimit':3,'path':'bad'}):
            with self.assertRaises(ValueError):budget.write_policy(body)


class QuotaTests(unittest.TestCase):
    setUp=base.AccountsTest.setUp
    tearDown=base.AccountsTest.tearDown
    call=base.AccountsTest.call
    register=base.AccountsTest.register

    def parent(self,email='synthetic-quota@example.test'):
        cookie,session=self.register(email)
        state=session['state']
        state['profile']={'role':'mom','stage':'child','childName':'Тест',
            'birthDate':(date.today()-timedelta(days=180)).isoformat(),'week':20,'weekDate':date.today().isoformat(),
            'feeding':'unknown','sleep':'','health':'','healthConfirmed':False,'topics':[]}
        self.assertEqual(self.call('save',cookie,state=state,revision=0)[0]['statusCode'],200)
        return cookie,session['user']['id']

    def ask(self,cookie,ident,question='Что видно по моим записям сна?'):
        revision=self.call('session',cookie)[1]['revision']
        return self.call('chat',cookie,question=question,messageId=ident,revision=revision)

    def test_ordinary_accounts_are_limited_and_retries_and_emergency_remain_available(self):
        with patch.dict(os.environ,AI_FREE_CHAT_LIMIT='2'):
            cookie,_=self.parent()
            with patch.object(app,'chat_answer',return_value='Учитываем текущие записи.') as provider:
                first=self.ask(cookie,'one')[1]
                self.assertEqual(first['quota']['used'],1)
                second=self.ask(cookie,'two')[1]
                self.assertEqual(second['quota']['remaining'],0)
                self.assertEqual(self.ask(cookie,'three')[0]['statusCode'],429)
                replay=self.ask(cookie,'one')[1]
                self.assertEqual(replay['quota']['used'],2)
                self.assertEqual(provider.call_count,2)
            urgent=self.ask(cookie,'urgent','Ребёнок не дышит')[1]
            self.assertIn('112',urgent['answer']);self.assertEqual(urgent['quota']['used'],2)
            self.assertEqual(self.call('care-list',cookie)[0]['statusCode'],200)

    def test_service_errors_do_not_consume_regular_account_quota(self):
        cookie,_=self.parent()
        for ident,error in [('unavailable',app.AppError(503,'Сервис недоступен')),('timeout',app.ChatTimeout())]:
            with patch.object(app,'chat_answer',side_effect=error):self.ask(cookie,ident)
            self.assertEqual(self.call('session',cookie)[1]['quota']['used'],0)

    def test_deleting_and_registering_same_address_does_not_reset_trial(self):
        cookie,old=self.parent()
        with patch.object(app,'chat_answer',return_value='Тестовый ответ.'):self.ask(cookie,'one')
        self.assertEqual(self.call('delete',cookie,password='long-test-password')[0]['statusCode'],200)
        new,session=self.register('synthetic-quota@example.test')
        self.assertNotEqual(session['user']['id'],old)
        self.assertEqual(session['quota']['used'],1)

    def test_existing_counters_paid_period_and_bonus_are_preserved(self):
        cookie,uid=self.parent()
        db=app.DB()
        db.query('INSERT INTO mh_limits VALUES(?,?,?)',('ai-quota:'+uid,12,4102444800))
        db.query('INSERT INTO mh_paid_access VALUES(?,?,?,?,?)',(uid,'paid-period',0,4102444800,3))
        db.query('INSERT INTO mh_limits VALUES(?,?,?)',('paid-quota:'+uid+':paid-period',3,4102444800))
        db.query('INSERT INTO mh_birthday_gifts VALUES(?,?,?,?)',(uid,'primary',2026,1))
        db.conn.commit();db.close()
        session=self.call('session',cookie)[1]
        self.assertEqual(session['quota']['remaining'],1)
        with patch.object(app,'chat_answer',return_value='Тестовый ответ.'):
            answered=self.ask(cookie,'gift')[1]
        self.assertEqual(answered['quota']['bonusRemaining'],0)
        self.assertEqual(answered['quota']['used'],3)
        db=app.DB();db.query('DELETE FROM mh_paid_access WHERE user_id=?',(uid,));db.conn.commit();db.close()
        self.assertEqual(self.call('session',cookie)[1]['quota']['used'],12)

    def test_switching_child_does_not_grant_extra_answers(self):
        with patch.dict(os.environ,AI_FREE_CHAT_LIMIT='1'):
            cookie,_=self.parent()
            with patch.object(app,'chat_answer',return_value='Тестовый ответ.'):self.ask(cookie,'one')
            session=self.call('session',cookie)[1];state=session['state']
            primary={'profile':state['profile'],'messages':state['messages'],'medicalCard':state['medicalCard']}
            state.update(activeChildId='second',profile={**state['profile'],'childName':'Второй'},messages=[],children=[{'id':'primary','data':primary}])
            self.assertEqual(self.call('save',cookie,state=state,revision=session['revision'])[0]['statusCode'],200)
            self.assertEqual(self.ask(cookie,'second-question')[0]['statusCode'],429)
            self.assertEqual(self.call('session',cookie)[1]['quota']['used'],1)


class ProviderBudgetTests(unittest.TestCase):
    setUp=QuotaTests.setUp
    tearDown=QuotaTests.tearDown
    call=QuotaTests.call
    register=QuotaTests.register
    parent=QuotaTests.parent
    ask=QuotaTests.ask
    def response(self, request, **kwargs):
        payload=json.loads(request.data)
        if payload.get('response_format'):
            context=json.loads(payload['messages'][1]['content'])
            count=1 if context.get('replacement') else 3
            content=json.dumps({'ids':[item['id'] for item in context['candidates'][:count]]})
        else: content='По текущим наблюдениям данных пока мало.'
        response=MagicMock()
        response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':content},'finish_reason':'stop'}],
                    'usage':{'prompt_tokens':100,'completion_tokens':20}}).encode()
        return response

    def test_budget_stops_network_but_keeps_emergency_journal_and_library(self):
        cookie,_=self.parent()
        with patch.dict(os.environ,AI_PROVIDER='proxyapi',PROXYAPI_API_KEY='synthetic-only',AI_BUDGET_DAY_RUB='0'), \
             patch.object(app,'CHAT_LIVE_ENABLED',True), patch.object(app.urllib.request,'urlopen') as network:
            self.assertEqual(self.ask(cookie,'blocked')[0]['statusCode'],429)
            urgent=self.ask(cookie,'urgent','Ребёнок не дышит')[1]
            self.assertIn('112',urgent['answer'])
            plan=self.call('daily-plan',cookie)[1]
            self.assertEqual(plan['source'],'library');self.assertEqual(len(plan['items']),3)
            network.assert_not_called()
        self.assertEqual(self.call('session',cookie)[1]['quota']['used'],0)

    def test_daily_cost_is_counted_once_separately_from_chat_quota(self):
        cookie,_=self.parent()
        with patch.dict(os.environ,AI_PROVIDER='proxyapi',PROXYAPI_API_KEY='synthetic-only'), \
             patch.object(app,'CHAT_LIVE_ENABLED',True), patch.object(app.urllib.request,'urlopen',side_effect=self.response) as network:
            first=self.call('daily-plan',cookie)[1]
            self.assertEqual(first['source'],'ai')
            second=self.call('daily-plan',cookie)[1]
            self.assertEqual(first,second);self.assertEqual(network.call_count,1)
            self.assertEqual(self.call('session',cookie)[1]['quota']['used'],0)
            answered=self.ask(cookie,'chat')[1]
            self.assertEqual(answered['quota']['used'],1)
        report=budget.summary()
        self.assertEqual({item['kind']:item['calls'] for item in report['byKind']},{'chat':1,'daily':1})

    def test_network_errors_and_invalid_billed_output_do_not_charge_answers(self):
        cookie,_=self.parent()
        with patch.dict(os.environ,AI_PROVIDER='proxyapi',PROXYAPI_API_KEY='synthetic-only'),patch.object(app,'CHAT_LIVE_ENABLED',True):
            error=app.urllib.error.HTTPError('https://example.test',500,'Synthetic error',{},io.BytesIO(b'{}'))
            with patch.object(app.urllib.request,'urlopen',side_effect=error):
                self.assertEqual(self.ask(cookie,'http-error')[1]['quota']['used'],0)
            bad=MagicMock()
            bad.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':''},'finish_reason':'length'}],
                                        'usage':{'prompt_tokens':100,'completion_tokens':20}}).encode()
            with patch.object(app.urllib.request,'urlopen',return_value=bad):
                self.assertEqual(self.ask(cookie,'invalid')[1]['quota']['used'],0)
        result=budget.summary()['today']
        self.assertEqual(result['calls'],2);self.assertEqual(result['unknownUsage'],1)
        self.assertGreater(result['estimatedRub'],0);self.assertGreater(result['reservedRub'],0)

    def test_replaying_a_saved_answer_does_not_call_or_bill_provider_twice(self):
        cookie,_=self.parent()
        with patch.dict(os.environ,AI_PROVIDER='proxyapi',PROXYAPI_API_KEY='synthetic-only'), \
             patch.object(app,'CHAT_LIVE_ENABLED',True), patch.object(app.urllib.request,'urlopen',side_effect=self.response) as network:
            first=self.ask(cookie,'same-question')[1]
            again=self.ask(cookie,'same-question')[1]
            self.assertEqual(first['answer'],again['answer']);self.assertEqual(again['quota']['used'],1)
            self.assertEqual(network.call_count,1)
        self.assertEqual(budget.summary()['today']['calls'],1)


if __name__=='__main__':unittest.main()
