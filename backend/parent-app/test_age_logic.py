"""Age boundaries, stale persisted plans and safety of AI selection."""
import calendar
import copy
import json
import unittest
from datetime import date
import test_daily as base

app=base.app

class AgeLogicTest(unittest.TestCase):
    call=base.DailyTest.call
    register=base.DailyTest.register
    setUp=base.DailyTest.setUp
    tearDown=base.DailyTest.tearDown

    def test_every_supported_month_has_only_eligible_play_and_all_advice_sections(self):
        daily,_=app.daily_runtime()
        ids=[row[0] for row in daily.catalog.ROWS]
        self.assertEqual(len(ids),len(set(ids)))
        for month in range(85):
            with self.subTest(month=month):
                games=daily.catalog.candidates(month)
                self.assertGreaterEqual(len(games),8)
                self.assertGreaterEqual(len({g['area'] for g in games}),3)
                self.assertGreaterEqual(len([g for g in games if g['area'] not in ('Движение','Координация')]),3)
                for game in games:
                    self.assertTrue(game['minMonths']<=month<game['maxMonths'])
                    self.assertLessEqual(game['maxMonths']-game['minMonths'],1 if month<24 else 2)
                    self.assertTrue(game['goal'] and game['steps'])
                    self.assertNotRegex(game['title'].lower(),r'купани|прикорм|массаж|чистка зубов')
                if month>=12:self.assertNotIn('peek',[g['baseId'] for g in games])
                cards=daily.guidance.cards(month)
                self.assertEqual({c['section'] for c in cards},{'Игры','Развитие','Уход и гигиена','Советы педиатров'})
                self.assertTrue(all(c['minMonths']<=month<c['maxMonths'] for c in cards))
                self.assertTrue(all(c['maxMonths']-c['minMonths']<=2 for c in cards))
                if month>=3:self.assertNotIn('bath-supervision',[c['id'] for c in cards])
        for month in (-1,85,120,None,1.2,True):self.assertEqual(daily.catalog.candidates(month),[])

    def test_actual_daily_generation_for_all_85_months_and_cached_repeat(self):
        daily,runtime=app.daily_runtime();db=app.DB();uid=self.session['user']['id']
        state=copy.deepcopy(self.state);state['children']=[]
        today=daily.local_now(state).date()
        try:
            for month in range(85):
                with self.subTest(month=month):
                    ym=today.year*12+today.month-1-month;year,zero_month=divmod(ym,12)
                    state['profile']['birthDate']=date(year,zero_month+1,min(today.day,calendar.monthrange(year,zero_month+1)[1])).isoformat()
                    self.assertEqual(daily.age(state['profile'],today.isoformat()),month)
                    plan=daily.ensure(runtime,db,uid,state,'primary')
                    self.assertEqual(plan['ageMonths'],month)
                    self.assertIsNone(plan['hint'])
                    self.assertEqual(len(plan['items']),3)
                    self.assertTrue(all(g['minMonths']<=month<g['maxMonths'] for g in plan['items']))
                    count=len(self.contexts)
                    self.assertEqual(plan,daily.ensure(runtime,db,uid,state,'primary'))
                    self.assertEqual(count,len(self.contexts))
        finally:db.close()

    def test_old_cached_recommendation_replaced_without_changing_profile(self):
        daily,runtime=app.daily_runtime();db=app.DB();uid=self.session['user']['id']
        try:
            plan=daily.ensure(runtime,db,uid,self.state,'primary')
            stale={**plan,'catalogVersion':'old','items':[{'id':'picture','title':'old','status':'liked'}],'hint':{'id':'bath-supervision'},'replacements':2}
            db.query('UPDATE mh_daily SET encrypted_data=? WHERE user_id=?',(app.seal(stale),uid));db.conn.commit()
            context=json.loads(daily.context(runtime,db,uid,self.state).split(':\n',1)[1])
            self.assertIsNone(context['today'])
            # Filtering for chat must not rewrite saved history.
            saved=app.unseal(db.query('SELECT encrypted_data FROM mh_daily WHERE user_id=?',(uid,)).fetchone()[0])
            self.assertEqual(saved,stale)
            updated=daily.ensure(runtime,db,uid,self.state,'primary')
            self.assertNotIn('picture',[g['id'] for g in updated['items']])
            self.assertEqual(updated['catalogVersion'],daily.catalog.VERSION)
            self.assertEqual(updated['replacements'],2)
            self.assertIsNone(updated['hint'])
            current=app.unseal(db.query('SELECT encrypted_data FROM mh_state WHERE user_id=?',(uid,)).fetchone()[0])
            self.assertEqual(current['profile'],self.state['profile'])
        finally:db.close()

    def test_ai_cannot_choose_out_of_age_ids_and_health_applies_to_fallback(self):
        daily,runtime=app.daily_runtime()
        app.chat_answer=lambda *a,**kw:json.dumps({'ids':['peek','face-pause','tummy-face']})
        for month in range(85):
            child={**self.state,'profile':{**self.state['profile'],'health':'Ограничения движений'},'_ageMonths':month}
            chosen,source=daily.choose(runtime,child,daily.catalog.candidates(month),3,[],[])
            self.assertEqual(len(chosen),3)
            self.assertTrue(all(g['minMonths']<=month<g['maxMonths'] for g in chosen))
            self.assertTrue(all(g['area'] not in ('Движение','Координация') for g in chosen))

    def test_month_calculation_leap_day_and_end_of_month(self):
        daily,_=app.daily_runtime()
        for born,day,expected in [('2024-02-29','2025-02-28',12),('2025-01-31','2025-02-28',1),('2025-01-31','2025-03-30',1),('2025-01-31','2025-03-31',2),('2025-07-21','2026-09-21',14)]:
            self.assertEqual(daily.age({'birthDate':born},day),expected)

    def test_notification_card_is_eligible_and_old_link_is_not_recommended(self):
        daily,_=app.daily_runtime();month=daily.age(self.state['profile'],daily.local_now(self.state).date().isoformat())
        topic=daily.guidance.cards(month)[0]['id']
        r,b=self.call('age-guidance',self.cookie,childId='primary',topic=topic)
        self.assertEqual(r['statusCode'],200)
        self.assertEqual(b['selected']['id'],topic)
        r,b=self.call('age-guidance',self.cookie,childId='primary',topic='bath-supervision')
        self.assertIsNone(b['selected'])

    def test_chat_applies_age_context_and_removes_invitation_before_saving(self):
        captured={}
        def answer(question,context,**kw):
            captured['context']=context
            return 'Повторите звук ребёнка и дождитесь реакции. Напишите в чат за другими играми.'
        app.chat_answer=answer
        response,body=self.call('chat',self.cookie,question='Как поддержать общение с ребёнком?',messageId='content-rule-check',revision=1)
        self.assertEqual(response['statusCode'],200,body)
        self.assertEqual(body['answer'],'Повторите звук ребёнка и дождитесь реакции.')
        self.assertEqual(body['state']['messages'][-1]['text'],body['answer'])
        self.assertIn('ОБЕ границы',captured['context'])
        self.assertIn('6 полных месяцев',captured['context'])

    def test_provider_failure_uses_an_age_checked_fallback(self):
        app.chat_answer=lambda *args,**kw: (_ for _ in ()).throw(TimeoutError())
        response,body=self.call('chat',self.cookie,question='Во что поиграть?',messageId='age-fallback',revision=1)
        self.assertEqual(response['statusCode'],200,body)
        daily,_=app.daily_runtime()
        self.assertTrue(any('«'+g['title']+'»' in body['answer'] for g in daily.catalog.candidates(6)))
        self.assertIn('резервный ответ',body['answer'])

if __name__=='__main__':unittest.main()
