"""Notification regressions using temporary accounts and a fake push transport."""
import copy
import importlib.util
import json
import os
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
import test_daily as base

app = base.app
spec = importlib.util.spec_from_file_location('push_delivery_job', Path(__file__).with_name('daily_job.py'))
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


class PushDeliveryTest(unittest.TestCase):
    call = base.DailyTest.call
    register = base.DailyTest.register

    def setUp(self):
        base.DailyTest.setUp(self)
        self.daily, _ = app.daily_runtime()
        self.state = copy.deepcopy(self.state)
        self.state['preferences'].update(push=True, secondReminder=True)
        self.call('save', self.cookie, state=self.state, revision=1)
        self.call('subscribe', self.cookie, subscription={
            'endpoint': 'https://fcm.googleapis.com/fcm/send/synthetic-push',
            'keys': {'p256dh': 'a' * 30, 'auth': 'b' * 30}})
        os.environ.update(VAPID_PRIVATE_KEY='test', VAPID_SUBJECT='mailto:test@example.test')
        self.original_now = self.daily.local_now
        self.moment = self.original_now(self.state).replace(hour=9, minute=0)
        self.daily.local_now = lambda state: self.moment
        self.db = app.DB()
        self.uid = self.session['user']['id']
        self.sent = []

    def tearDown(self):
        self.daily.local_now = self.original_now
        self.db.close()
        base.DailyTest.tearDown(self)

    def deliver(self, **kwargs):
        self.sent.append(json.loads(kwargs['data']))

    def test_disabled_push_never_generates_plans(self):
        self.state['preferences']['push'] = False
        self.db.query('UPDATE mh_state SET encrypted_data=? WHERE user_id=?', (app.seal(self.state), self.uid))
        self.db.conn.commit()
        with patch.object(self.daily, 'ensure', side_effect=AssertionError('Unexpected generation')) as ensure:
            result = job.run(app, self.db, self.deliver)
        self.assertEqual(ensure.call_count, 0)
        self.assertEqual(result, {'generated': 0, 'delivered': 0, 'errors': 0})

    def test_no_subscription_or_wrong_hour_never_generates(self):
        self.moment = self.moment.replace(hour=8)
        with patch.object(self.daily, 'ensure') as ensure:
            job.run(app, self.db, self.deliver)
            self.moment = self.moment.replace(hour=9)
            self.db.query('DELETE FROM mh_push')
            self.db.conn.commit()
            job.run(app, self.db, self.deliver)
        self.assertEqual(ensure.call_count, 0)
        self.assertEqual(self.sent, [])

    def test_failed_delivery_does_not_consume_topic(self):
        def fail(**kwargs):
            raise TimeoutError('synthetic timeout')
        result = job.run(app, self.db, fail)
        self.assertEqual(result['errors'], 1)
        self.assertEqual(self.db.query('SELECT COUNT(*) FROM mh_guidance_delivery').fetchone()[0], 0)
        job.run(app, self.db, self.deliver)
        self.assertEqual(self.sent, [])  # An ambiguous attempt occupies today's slot.
        self.moment += timedelta(days=1)
        job.run(app, self.db, self.deliver)
        self.assertEqual(len(self.sent), 1)

    def test_expired_subscription_removed_without_losing_topic(self):
        class Gone(Exception):
            response = type('Response', (), {'status_code': 410})()
        def fail(**kwargs):
            raise Gone()
        job.run(app, self.db, fail)
        self.assertEqual(self.db.query('SELECT COUNT(*) FROM mh_push').fetchone()[0], 0)
        self.assertEqual(self.db.query('SELECT COUNT(*) FROM mh_guidance_delivery').fetchone()[0], 0)

    def test_all_age_payloads_hide_profile_and_include_safe_sleep_action(self):
        profile = {'childName': 'PRIVATE_CHILD', 'birthDate': 'PRIVATE_DATE', 'health': 'PRIVATE_HEALTH'}
        for months in range(85):
            for card in self.daily.guidance.cards(months):
                body = self.daily.guidance.push_text(card, profile)
                for private in profile.values():
                    self.assertNotIn(private, body)
                self.assertLessEqual(len(body), 180)
        body = self.daily.guidance.push_text(self.daily.guidance.get('safe-sleep'), profile)
        self.assertIn('спину', body)
        self.assertIn('твёрд', body)

    def test_guidance_only_has_no_provider_calls_and_no_repeat(self):
        with patch.object(self.daily, 'ensure', side_effect=AssertionError('Unexpected generation')) as ensure:
            job.run(app, self.db, self.deliver, guidance_only=True)
            job.run(app, self.db, self.deliver, guidance_only=True)
            self.moment += timedelta(days=1)
            job.run(app, self.db, self.deliver, guidance_only=True)
        self.assertEqual(ensure.call_count, 0)
        self.assertEqual(len(self.sent), 2)
        self.assertNotEqual(self.sent[0]['path'], self.sent[1]['path'])
        self.assertEqual(self.db.query('SELECT COUNT(*) FROM mh_daily').fetchone()[0], 0)

    def test_month_boundary_uses_new_age_and_profile_link(self):
        self.state['children'] = []
        self.state['profile']['birthDate'] = '2026-05-13'
        self.db.query('UPDATE mh_state SET encrypted_data=? WHERE user_id=?', (app.seal(self.state), self.uid))
        self.db.conn.commit()
        self.moment = self.moment.replace(year=2026, month=10, day=12)
        job.run(app, self.db, self.deliver, guidance_only=True)
        self.assertNotIn('topic=feeding-six-months', self.sent[-1]['path'])
        self.moment += timedelta(days=1)
        job.run(app, self.db, self.deliver, guidance_only=True)
        self.assertIn('topic=feeding-six-months', self.sent[-1]['path'])
        self.assertIn('child=primary', self.sent[-1]['path'])
        self.assertIn('около 6 месяцев', self.sent[-1]['body'])

    def test_unsubscribe_stops_delivery(self):
        self.assertEqual(self.call('unsubscribe', self.cookie)[0]['statusCode'], 200)
        job.run(app, self.db, self.deliver, guidance_only=True)
        self.assertEqual(self.sent, [])

    def test_second_slot_does_not_generate_or_send_without_existing_plan(self):
        self.moment = self.moment.replace(hour=15)
        job.run(app, self.db, self.deliver)
        self.assertEqual(self.sent, [])
        self.assertEqual(len(self.contexts), 0)

    def test_invalid_age_does_not_guess_or_mix_profiles(self):
        self.state['profile']['birthDate'] = ''
        self.state['children'] = []
        self.db.query('UPDATE mh_state SET encrypted_data=? WHERE user_id=?', (app.seal(self.state), self.uid))
        self.db.conn.commit()
        job.run(app, self.db, self.deliver, guidance_only=True)
        self.assertEqual(self.sent, [])

    def test_local_worker_reuses_one_thread_and_requires_explicit_config(self):
        import push_delivery
        with patch.dict(os.environ, {'APP_LOCAL_PUSH_ENABLED': '0'}):
            self.assertIsNone(push_delivery.start(app))
        with patch.dict(os.environ, {'APP_LOCAL_PUSH_ENABLED': '1', 'VAPID_PUBLIC_KEY': 'test'}), \
                patch.object(push_delivery, '_thread', None), patch.object(push_delivery.threading, 'Thread') as thread:
            thread.return_value.is_alive.return_value = True
            self.assertIs(push_delivery.start(app), thread.return_value)
            self.assertIs(push_delivery.start(app), thread.return_value)
            self.assertEqual(thread.call_count, 1)

    def test_timezone_changes_calendar_age_and_hour_from_same_instant(self):
        from datetime import datetime, timezone
        self.state['profile']['birthDate'] = '2026-05-13'
        self.state['children'] = []
        self.state['preferences']['timezone'] = 'Asia/Kamchatka'
        self.state['preferences']['morningHour'] = 9
        self.db.query('UPDATE mh_state SET encrypted_data=? WHERE user_id=?', (app.seal(self.state), self.uid))
        self.db.conn.commit()
        from zoneinfo import ZoneInfo
        instant = datetime(2026, 10, 12, 21, tzinfo=timezone.utc)
        self.daily.local_now = lambda state: instant.astimezone(ZoneInfo(state['preferences']['timezone']))
        job.run(app, self.db, self.deliver, guidance_only=True)
        self.assertEqual(len(self.sent), 1)
        self.assertIn('topic=feeding-six-months', self.sent[0]['path'])
        self.state['preferences']['timezone'] = 'Europe/Moscow'
        self.db.query('UPDATE mh_state SET encrypted_data=? WHERE user_id=?', (app.seal(self.state), self.uid))
        self.db.conn.commit()
        job.run(app, self.db, self.deliver, guidance_only=True)
        self.assertEqual(len(self.sent), 1)  # At the same instant Moscow is midnight.

    def test_push_games_respect_health_and_rejected_mechanics(self):
        from urllib.parse import urlparse, parse_qs
        self.state['children'] = []
        self.state['profile']['health'] = 'Synthetic limitation'
        self.db.query('UPDATE mh_state SET encrypted_data=? WHERE user_id=?', (app.seal(self.state), self.uid))
        cards = self.daily.guidance.cards(self.daily.age(self.state['profile'], self.moment.date().isoformat()))
        games = [c for c in cards if c['category']=='Игры' and c['area'] not in ('Движение','Координация')]
        denied = games[0]
        feedback = {'kind':'replace','reason':'dislike','baseId':denied['baseId']}
        self.db.query('INSERT INTO mh_daily_feedback VALUES(?,?,?,?,?)', (self.uid,'synthetic-rejection','primary',self.moment.date().isoformat(),app.seal(feedback)))
        for card in cards:
            if card['category']!='Игры':
                self.db.query('INSERT INTO mh_guidance_delivery VALUES(?,?,?,?)', (self.uid,'primary',card['id'],1))
        self.db.conn.commit()
        job.run(app, self.db, self.deliver, guidance_only=True)
        self.assertEqual(len(self.sent), 1)
        topic = parse_qs(urlparse(self.sent[0]['path']).query)['topic'][0]
        selected = next(c for c in cards if c['id']==topic)
        self.assertNotIn(selected['area'], ('Движение','Координация'))
        self.assertNotEqual(selected['baseId'], denied['baseId'])


if __name__ == '__main__':
    unittest.main()
