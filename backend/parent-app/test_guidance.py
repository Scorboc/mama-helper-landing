import copy,importlib.util,json,os,time,unittest
from datetime import date,timedelta
from pathlib import Path
import test_daily as base
app=base.app
class GuidanceTest(unittest.TestCase):
    call=base.DailyTest.call
    register=base.DailyTest.register
    setUp=base.DailyTest.setUp
    tearDown=base.DailyTest.tearDown
    def test_age_cards_child_access_and_no_ai_charge(self):
        calls=len(self.contexts)
        r,b=self.call('age-guidance',self.cookie,childId='second',topic='two-words')
        self.assertEqual(r['statusCode'],200,b);self.assertEqual(b['childName'],'Второй')
        self.assertIsNone(b['selected']);self.assertEqual(len(self.contexts),calls)
        self.assertEqual(self.call('age-guidance',self.cookie,childId='stranger')[0]['statusCode'],404)
        daily,_=app.daily_runtime()
        for month in range(84):
            cards=daily.guidance.cards(month)
            self.assertTrue(cards)
            for card in cards:
                self.assertTrue(card['source'].startswith('https://'))
                self.assertLessEqual(len(daily.guidance.push_text(card,{'childName':'Настя'})),180)
    def test_birthday_free_paid_idempotency_and_expiry(self):
        state=copy.deepcopy(self.state);today=date(2026,9,21)
        state['profile']['birthDate']='2024-09-21';state['children'][0]['data']['profile']['birthDate']='2022-09-21'
        db=app.DB();uid=self.session['user']['id'];b=app._birthdays
        try:
            self.assertEqual(len(b.grant(db,uid,state,today)),2);self.assertEqual(b.balance(db,uid),0)
            db.query('INSERT INTO mh_paid_access VALUES(?,?,?,?,?)',(uid,'test',0,int(time.time())+500,0))
            b.grant(db,uid,state,today);b.grant(db,uid,state,today)
            self.assertEqual(b.balance(db,uid),10)
            for _ in range(10):self.assertTrue(b.consume(db,uid))
            self.assertFalse(b.consume(db,uid));b.grant(db,uid,state,today);self.assertEqual(b.balance(db,uid),0)
            db.query('UPDATE mh_paid_access SET ends_at=1');b.grant(db,uid,state,date(2027,9,21));self.assertEqual(b.balance(db,uid),0)
            state['profile']['birthDate']='2024-02-29';state['children']=[]
            self.assertEqual(len(b.children_today(state,date(2025,2,28))),1)
            self.assertEqual(len(b.children_today(state,date(2028,2,28))),0)
            self.assertEqual(len(b.children_today(state,date(2028,2,29))),1)
        finally:db.close()
    def test_priority_promotes_age_window_and_safety(self):
        daily,_=app.daily_runtime();g=daily.guidance
        self.assertEqual(len({r[0] for r in g.ROWS}),len(g.ROWS))
        for months in range(84):
            cards=g.cards(months)
            self.assertEqual([c['priority'] for c in cards],sorted(c['priority'] for c in cards))
        self.assertEqual(g.priority(g.get('two-words'),24),1)
        self.assertEqual(g.priority(g.get('two-words'),28),2)
        self.assertLess(g.priority(g.get('feeding-six-months'),6),g.priority(g.get('touch'),6))
        self.assertEqual(g.cards(0)[0]['id'],'safe-sleep')
    def test_push_topic_rotation_budget_and_birthday_even_viewed(self):
        state=copy.deepcopy(self.state);state['preferences'].update(push=True,secondReminder=True)
        self.call('save',self.cookie,state=state,revision=1)
        self.call('subscribe',self.cookie,subscription={'endpoint':'https://fcm.googleapis.com/fcm/send/guidance','keys':{'p256dh':'a'*30,'auth':'b'*30}})
        os.environ.update(VAPID_PRIVATE_KEY='test',VAPID_SUBJECT='mailto:test@example.test')
        spec=importlib.util.spec_from_file_location('job',Path(__file__).with_name('daily_job.py'));job=importlib.util.module_from_spec(spec);spec.loader.exec_module(job)
        daily,_=app.daily_runtime();old=daily.local_now;moment=old(state).replace(hour=9,minute=0);daily.local_now=lambda _:moment
        db=app.DB();sent=[];uid=self.session['user']['id']
        try:
            deliver=lambda **kw:sent.append(json.loads(kw['data']))
            job.run(app,db,deliver);job.run(app,db,deliver)
            self.assertEqual(len(sent),1);self.assertEqual(sent[0]['type'],'age-guidance');self.assertIn('tab=chat',sent[0]['path'])
            self.assertIn('Первый',sent[0]['body'])
            moment+=timedelta(days=1);job.run(app,db,deliver)
            self.assertIn('child=second',sent[-1]['path'])
            moment+=timedelta(days=1);job.run(app,db,deliver)
            self.assertNotEqual(sent[0]['path'],sent[-1]['path'])
            moment+=timedelta(days=1)
            state['profile']['birthDate']=moment.date().replace(year=moment.year-1).isoformat()
            db.query('UPDATE mh_state SET encrypted_data=? WHERE user_id=?',(app.seal(state),uid));db.conn.commit()
            plan=daily.ensure(app.daily_runtime()[1],db,uid,state,'primary')
            db.query('UPDATE mh_daily SET viewed=1');db.conn.commit()
            # Consume the current safety/stage queue, then a birthday may be sent.
            for child in daily.children(state):
                months=daily.age(child['data']['profile'],moment.date().isoformat())
                for card in daily.guidance.cards(months):
                    if card['priority']<=1:
                        db.query('INSERT INTO mh_guidance_delivery VALUES(?,?,?,?) ON CONFLICT(user_id,child_id,topic) DO NOTHING',(uid,child['id'],card['id'],int(time.time())))
            db.conn.commit()
            job.run(app,db,deliver);job.run(app,db,deliver)
            self.assertEqual(sent[-1]['type'],'birthday');self.assertNotIn('5 дополнительных',sent[-1]['body'])
            self.assertEqual(len(sent),4)
            db.query('UPDATE mh_daily SET viewed=1');db.conn.commit()
            moment=moment.replace(hour=15);job.run(app,db,deliver);self.assertEqual(len(sent),4)
        finally:daily.local_now=old;db.close()
    def test_paid_gift_charge_retry_failure_and_limit(self):
        uid=self.session['user']['id'];db=app.DB()
        db.query('INSERT INTO mh_paid_access VALUES(?,?,?,?,?)',(uid,'test',0,int(time.time())+500,0))
        db.query('INSERT INTO mh_birthday_gifts VALUES(?,?,?,?)',(uid,'primary',2026,5));db.conn.commit();db.close()
        app.chat_answer=lambda *a,**k:'Спокойно обсудим вашу ситуацию.'
        for i in range(5):
            r,b=self.call('chat',self.cookie,question='Хочу поговорить о повседневных делах',messageId='gift'+str(i),revision=1+i)
            self.assertEqual(r['statusCode'],200,b);self.assertEqual(b['quota']['remaining'],4-i)
        self.assertEqual(self.call('chat',self.cookie,question='Хочу поговорить о повседневных делах',messageId='gift4',revision=6)[0]['statusCode'],200)
        self.assertEqual(self.call('chat',self.cookie,question='Хочу поговорить о повседневных делах',messageId='extra',revision=6)[0]['statusCode'],429)

    def test_important_topic_beats_family_rotation(self):
        state=copy.deepcopy(self.state);state['preferences'].update(push=True)
        self.call('save',self.cookie,state=state,revision=1)
        self.call('subscribe',self.cookie,subscription={'endpoint':'https://fcm.googleapis.com/fcm/send/priority','keys':{'p256dh':'a'*30,'auth':'b'*30}})
        os.environ.update(VAPID_PRIVATE_KEY='test',VAPID_SUBJECT='mailto:test@example.test')
        spec=importlib.util.spec_from_file_location('priority_job',Path(__file__).with_name('daily_job.py'));job=importlib.util.module_from_spec(spec);spec.loader.exec_module(job)
        daily,_=app.daily_runtime();old=daily.local_now;moment=old(state).replace(hour=9,minute=0);daily.local_now=lambda _:moment
        db=app.DB();sent=[];uid=self.session['user']['id']
        try:
            for child in daily.children(state):
                for card in daily.guidance.cards(daily.age(child['data']['profile'],moment.date().isoformat())):
                    keep='parent-pause' if child['id']=='primary' else 'feeding-six-months'
                    if card['id']!=keep:db.query('INSERT INTO mh_guidance_delivery VALUES(?,?,?,?)',(uid,child['id'],card['id'],1 if child['id']=='primary' else 999))
            db.conn.commit()
            job.run(app,db,lambda **kw:sent.append(json.loads(kw['data'])))
            self.assertEqual(len(sent),1)
            self.assertIn('child=second',sent[0]['path']);self.assertIn('topic=feeding-six-months',sent[0]['path'])
        finally:daily.local_now=old;db.close()

if __name__=='__main__':unittest.main()
