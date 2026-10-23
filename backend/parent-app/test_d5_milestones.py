"""D5 contract checks. Temporary test DB, synthetic profiles, fake push only."""
import calendar
import copy
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import age_guidance as guidance
import care_tools
import test_push_delivery as push_base
import test_care_tools as care_base

app, job = push_base.app, push_base.job


def shifted(day, months):
    total = day.year * 12 + day.month - 1 + months
    year, month = divmod(total, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


class D5CatalogTest(unittest.TestCase):
    def test_all_supported_months_and_explicit_metadata(self):
        expected = {6:'roll', 9:'crawl', 11:'stand', 15:'walk'}
        for month in range(85):
            rows = [c for c in guidance.cards(month) if c['id'] in guidance.MILESTONE_WINDOWS]
            self.assertEqual([c['milestoneSkill'] for c in rows], [expected[month]] if month in expected else [], month)
            for card in rows:
                self.assertEqual((card['minMonths'], card['maxMonths']), (month, month+1))
                self.assertEqual((card['area'], card['section']), ('Движение', 'Развитие'))
                self.assertEqual(guidance.mark_skill({**card, 'title':'Совсем другое название'}), expected[month])
                self.assertTrue(card['source'].startswith('https://'))
        for value in (None, -1, 85, True, 6.5):
            self.assertEqual(guidance.cards(value), [])
        self.assertIsNone(guidance.mark_skill({'title':'Играть и ползать', 'section':'Развитие'}))

    def test_all_pushes_start_with_uppercase_letter(self):
        for month in range(85):
            for card in guidance.cards(month):
                text = guidance.push_text(card, {})
                first = next(char for char in text if char.isalpha())
                self.assertEqual(first, first.upper(), (month, card['id'], text))

    def test_words_push_offers_play_and_memory_without_age_norm(self):
        card = guidance.get('words-fifteen')
        text = guidance.push_text(card, {})
        self.assertEqual(text, 'Первые слова: как поддержать их в игре. И можно сохранить новое слово в книгу')
        self.assertNotIn('обычно', text)
        self.assertIn('Называйте предмет', card['text'])

    def test_boundaries_leap_day_month_end_and_timezones(self):
        daily, _ = app.daily_runtime()
        for birth in (date(2024,2,29), date(2025,1,31), date(2025,4,30)):
            for start in (6,9,11,15):
                for month in (start, start+1):
                    boundary = shifted(birth, month)
                    for delta in (-1,0,1):
                        day = boundary + timedelta(days=delta)
                        age = daily.age({'birthDate':birth.isoformat()}, day.isoformat())
                        present = any(c['id'] == guidance.MILESTONE_TOPICS[{6:'roll',9:'crawl',11:'stand',15:'walk'}[start]] for c in guidance.cards(age))
                        self.assertEqual(present, shifted(birth,start) <= day < shifted(birth,start+1))
        instant = datetime(2024,8,28,12,30,tzinfo=timezone.utc)
        for zone, expected in (('Pacific/Kiritimati',True), ('Etc/GMT+12',False)):
            day = instant.astimezone(ZoneInfo(zone)).date().isoformat()
            self.assertEqual(daily.age({'birthDate':'2024-02-29'},day) == 6, expected)

    def test_push_copy_is_private_short_and_without_deadlines(self):
        profile = {'childName':'PRIVATE_NAME','birthDate':'PRIVATE_BIRTH','health':'PRIVATE_HEALTH'}
        for topic in guidance.MILESTONE_WINDOWS:
            card = guidance.get(topic)
            body = guidance.push_text(card,profile)
            self.assertLessEqual(len(body),180)
            for value in profile.values():
                self.assertNotIn(value,body)
            for word in ('должен','норм','обычно','месяц','здоров','диагноз','PRIVATE'):
                self.assertNotIn(word,body)
                self.assertNotIn(word,card['text'])

    def test_shared_predicate_new_canonical_legacy_and_both(self):
        new = {'id':'new','kind':'achievement','skill':'crawl','value':'edited','at':'2026-01-01T00:00:00Z'}
        canonical = {**new,'id':'canonical','skill':None,'value':'Ползает'}
        old = {'care':{'achievements':[{'id':'old','kind':'crawl','date':'2026-01-01'}]}}
        for records,state in (([new],{}),([canonical],{}),([],old),([new],old)):
            self.assertIsNotNone(care_tools.marked_milestone(records,state,'crawl'))
            self.assertIsNone(care_tools.marked_milestone(records,state,'walk'))
        self.assertIsNone(care_tools.marked_milestone([{**new,'kind':'food'}],{},'crawl'))


class D5DeliveryTest(unittest.TestCase):
    # Reuse fixtures, not inherited unrelated account tests.
    call = push_base.PushDeliveryTest.call
    register = push_base.PushDeliveryTest.register
    setUp = push_base.PushDeliveryTest.setUp
    tearDown = push_base.PushDeliveryTest.tearDown
    deliver = push_base.PushDeliveryTest.deliver

    def install(self, month=9, health='', two=False):
        self.moment = self.moment.replace(year=2025,month=month+1 if month<12 else month-11,day=1,hour=9)
        if month>=12:self.moment=self.moment.replace(year=2026)
        self.state['profile'].update(birthDate='2025-01-01',health=health)
        self.state['children'] = [{'id':'second','data':{'profile':copy.deepcopy(self.state['profile'])}}] if two else []
        self.db.query('UPDATE mh_state SET encrypted_data=? WHERE user_id=?',(app.seal(self.state),self.uid))
        self.db.conn.commit()

    def paths(self):
        return [parse_qs(urlparse(s['path']).query) for s in self.sent]

    def test_month_competition_two_children_safety_first_no_catchup(self):
        self.install(two=True)
        end=shifted(self.moment.date(),1)
        skill_days=[]
        while self.moment.date()<end:
            before=len(self.sent)
            job.run(app,self.db,self.deliver)
            job.run(app,self.db,self.deliver)  # cron re-entry cannot duplicate the slot
            self.assertLessEqual(len(self.sent)-before,1)
            if len(self.sent)>before and self.paths()[-1].get('mark')==['crawl']:
                skill_days.append(self.moment.day)
            self.moment+=timedelta(days=1)
        self.assertEqual(skill_days,[3,4])  # battery safety for both children occupies days 1, 2
        self.assertEqual([p.get('topic') for p in self.paths()[:2]],[['button-batteries'],['button-batteries']])
        self.assertEqual(len([p for p in self.paths() if p.get('mark')==['crawl']]),2)
        self.db.query("DELETE FROM mh_guidance_delivery WHERE topic='milestone-crawl'")
        self.db.conn.commit()
        self.sent.clear()
        job.run(app,self.db,self.deliver)
        self.assertFalse(any(p.get('mark')==['crawl'] for p in self.paths()))

    def test_health_and_read_error_skip_milestone(self):
        self.install(health='synthetic restriction')
        for _ in range(5):
            job.run(app,self.db,self.deliver);self.moment+=timedelta(days=1)
        self.assertFalse(any(p.get('mark')==['crawl'] for p in self.paths()))
        self.install()
        self.db.query('DELETE FROM mh_daily_push');self.db.query('DELETE FROM mh_guidance_delivery');self.db.conn.commit()
        self.sent.clear()
        with patch.object(care_tools,'milestone_records',side_effect=ValueError('synthetic unreadable')):
            for _ in range(5):
                result=job.run(app,self.db,self.deliver);self.moment+=timedelta(days=1)
                self.assertGreater(result['errors'],0)
        self.assertFalse(any(p.get('mark')==['crawl'] for p in self.paths()))

    def test_existing_new_legacy_both_suppress_before_selection(self):
        for kind in ('new','canonical','legacy','both'):
            with self.subTest(kind=kind):
                self.install()
                self.state['care']={'achievements':[{'id':'old','kind':'crawl','date':'2025-09-01'}]} if kind in ('legacy','both') else {}
                self.db.query('UPDATE mh_state SET encrypted_data=? WHERE user_id=?',(app.seal(self.state),self.uid))
                self.db.query('DELETE FROM mh_daily_push');self.db.query('DELETE FROM mh_guidance_delivery');self.db.query('DELETE FROM mh_care_records')
                if kind in ('new','canonical','both'):
                    r={'id':'new','kind':'achievement','at':'2025-09-01T00:00:00Z','value':'Ползает'}
                    if kind!='canonical':r['skill']='crawl'
                    self.db.query('INSERT INTO mh_care_records VALUES(?,?,?,?)',(self.uid,'primary','new',app.seal(r)))
                self.db.conn.commit();self.sent.clear()
                for _ in range(5):
                    job.run(app,self.db,self.deliver);self.moment+=timedelta(days=1)
                self.assertFalse(any(p.get('mark')==['crawl'] for p in self.paths()))

    def test_server_topic_mapping_health_and_stale_link(self):
        self.install()
        runtime=app.daily_runtime()[1]
        r=self.daily.action(runtime,self.db,self.uid,self.state,{'action':'age-guidance','childId':'primary','milestoneSkill':'crawl','topic':'milestone-walk'})
        self.assertEqual(r['selected']['id'],'milestone-crawl')
        self.state['profile']['health']='restriction'
        self.assertIsNone(self.daily.action(runtime,self.db,self.uid,self.state,{'action':'age-guidance','milestoneSkill':'crawl'})['selected'])
        self.state['profile']['health']=''
        self.moment+=timedelta(days=40)
        self.assertIsNone(self.daily.action(runtime,self.db,self.uid,self.state,{'action':'age-guidance','milestoneSkill':'crawl'})['selected'])

    def test_no_free_day_means_no_milestone_and_no_catchup(self):
        self.install()
        original=self.daily.guidance.cards
        def busy_cards(month):
            return original(month)+[{'id':'safety-'+self.moment.date().isoformat(),'priority':0,'maxMonths':10,
                'minMonths':9,'pushText':'Уберите опасные предметы.','category':'Безопасность'}]
        with patch.object(self.daily.guidance,'cards',side_effect=busy_cards):
            for _ in range(31):
                job.run(app,self.db,self.deliver);self.moment+=timedelta(days=1)
        self.assertFalse(any(p.get('mark')==['crawl'] for p in self.paths()))
        self.assertEqual(len(self.sent),31)
        self.sent.clear();job.run(app,self.db,self.deliver)
        self.assertFalse(any(p.get('mark')==['crawl'] for p in self.paths()))

    def test_mark_between_selection_and_send_cancels_without_claim(self):
        self.install(month=11)
        real=care_tools.milestone_records(app,self.db,self.uid,'primary')
        marked=([{'id':'race','kind':'achievement','skill':'stand'}],real[1])
        with patch.object(care_tools,'milestone_records',side_effect=[real,marked]):
            job.run(app,self.db,self.deliver)
        self.assertEqual(self.sent,[])
        self.assertEqual(self.db.query('SELECT COUNT(*) FROM mh_daily_push').fetchone()[0],0)

    def test_shared_child_does_not_create_a_guest_push_candidate(self):
        self.install()
        guest,session=self.register('d5-push-guest@example.test')
        invite=self.call('family-invite',self.cookie,permission='write')[1]
        self.call('family-accept',guest,code=invite['code'])
        guest_state=session['state'];guest_state['preferences']['push']=True
        self.call('save',guest,state=guest_state,revision=0)
        self.call('subscribe',guest,subscription={'endpoint':'https://fcm.googleapis.com/fcm/send/guest-synthetic',
            'keys':{'p256dh':'a'*30,'auth':'b'*30}})
        self.state['preferences']['push']=False
        self.db.query('UPDATE mh_state SET encrypted_data=? WHERE user_id=?',(app.seal(self.state),self.uid));self.db.conn.commit()
        for _ in range(4):
            job.run(app,self.db,self.deliver);self.moment+=timedelta(days=1)
        self.assertEqual(self.sent,[])


class D5CareTest(unittest.TestCase):
    setUp = care_base.CareToolsTest.setUp
    tearDown = care_base.CareToolsTest.tearDown
    register = care_base.CareToolsTest.register
    call = care_base.CareToolsTest.call
    setup_parent = care_base.CareToolsTest.setup_parent

    def test_guest_cannot_mark_by_skill_or_canonical_value(self):
        owner,uid=self.setup_parent('d5-owner@example.test')
        guest,_=self.setup_parent('d5-guest@example.test')
        invite=self.call('family-invite',owner,permission='write')[1]
        self.call('family-accept',guest,code=invite['code'])
        record={'id':'guest-mark','kind':'achievement','at':datetime.now(timezone.utc).isoformat(),'value':'Ползает'}
        for r in (record,{**record,'skill':'crawl'}):
            self.assertEqual(self.call('care-put',guest,ownerId=uid,record=r)[0]['statusCode'],403)
        self.assertEqual(self.call('care-list',owner)[1]['records'],[])
        # The guest's account cannot resolve the owner's child through age-guidance.
        self.assertEqual(self.call('age-guidance',guest,childId='not-owned',milestoneSkill='crawl')[0]['statusCode'],404)

    def test_birth_inclusive_before_birth_and_future_server_validation(self):
        owner,_=self.setup_parent('d5-dates@example.test')
        birth=self.call('session',owner)[1]['state']['profile']['birthDate']
        record={'id':'date-mark','kind':'achievement','skill':'roll','at':birth+'T09:00:00+03:00'}
        self.assertEqual(self.call('care-put',owner,record=record)[0]['statusCode'],200)
        self.call('care-delete',owner,id='date-mark')
        for day in (date.fromisoformat(birth)-timedelta(days=1),date.today()+timedelta(days=1)):
            self.assertEqual(self.call('care-put',owner,record={**record,'at':day.isoformat()+'T09:00:00+03:00'})[0]['statusCode'],400)
        self.assertEqual(self.call('care-list',owner)[1]['records'],[])

if __name__ == '__main__':
    unittest.main()
