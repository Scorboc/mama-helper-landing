"""Narrow windows, real content changes, retained dislikes, cache and push links."""
import copy,json,unittest
import test_daily as base

app=base.app

class MonthlyContentTest(unittest.TestCase):
    call=base.DailyTest.call
    register=base.DailyTest.register
    setUp=base.DailyTest.setUp
    tearDown=base.DailyTest.tearDown

    def test_every_window_covers_only_one_or_two_complete_months(self):
        daily,_=app.daily_runtime();seen=set()
        for month in range(85):
            cards=daily.guidance.cards(month);games=daily.catalog.candidates(month)
            self.assertEqual(len({c['id'] for c in cards}),len(cards))
            self.assertEqual({c['section'] for c in cards},{'Игры','Развитие','Уход и гигиена','Советы педиатров'})
            for c in cards+games:
                self.assertTrue(c['minMonths']<=month<c['maxMonths'])
                self.assertLessEqual(c['maxMonths']-c['minMonths'],1 if month<24 else 2)
            care=next(c for c in cards if c['id'].startswith('month-care-'))
            if month<24 or month%2==0:
                self.assertNotIn(care['text'],seen)
                seen.add(care['text'])
        for month in (-1,85,None,True,1.5):self.assertEqual(daily.guidance.cards(month),[])

    def test_thirteen_fourteen_and_twentyfour_have_different_actions(self):
        daily,_=app.daily_runtime()
        tips={m:daily.guidance.cards(m) for m in (12,13,14,24)}
        self.assertTrue(any('полотенц' in c['title'].lower() for c in tips[13]))
        self.assertTrue(any('Выбор из двух' in c['title'] for c in tips[13]))
        self.assertTrue(any('один жест' in c['title'] for c in tips[14]))
        for section in ('Развитие','Уход и гигиена'):
            bodies=[next(c['text'] for c in tips[m] if c['id'].startswith('month-') and c['section']==section) for m in tips]
            self.assertEqual(len(set(bodies)),len(bodies))
        a={g['baseId']:g for g in daily.catalog.candidates(13)}
        b={g['baseId']:g for g in daily.catalog.candidates(14)}
        self.assertTrue(all(a[k]['steps']!=b[k]['steps'] for k in a))
        self.assertFalse(set(c['id'] for c in tips[13]) & set(c['id'] for c in tips[14] if c['id'].startswith('month-')))

    def test_dislike_does_not_reset_when_a_monthly_variant_changes(self):
        daily,runtime=app.daily_runtime();pool=daily.catalog.candidates(14)
        child={**self.state,'_ageMonths':14}
        app.chat_answer=lambda *a,**k:'invalid'
        feedback=[{'itemId':'copy-action@m13','kind':'replace','reason':'dislike','detail':'Эта игра уже надоела ребёнку.'}]
        chosen,_=daily.choose(runtime,child,pool,3,[],feedback)
        self.assertNotIn('copy-action',[g['baseId'] for g in chosen])
        chosen,_=daily.choose(runtime,child,pool,3,[{'items':pool}],[])
        self.assertTrue(all(g['familiar'] for g in chosen))

    def test_old_push_window_is_not_shown_after_month_changes(self):
        daily,_=app.daily_runtime()
        current=daily.age(self.state['profile'],daily.local_now(self.state).date().isoformat())
        topic='month-care-'+str(current-1)
        response,body=self.call('age-guidance',self.cookie,childId='primary',topic=topic)
        self.assertEqual(response['statusCode'],200)
        self.assertIsNone(body['selected'])
        self.assertTrue(all(c['minMonths']<=current<c['maxMonths'] for c in body['items']))

if __name__=='__main__':unittest.main()
