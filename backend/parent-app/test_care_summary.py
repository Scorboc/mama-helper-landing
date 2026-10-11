import unittest
from datetime import datetime, timezone
import care_summary


class CareSummaryTest(unittest.TestCase):
    now = datetime(2026, 10, 11, 9, tzinfo=timezone.utc)

    def test_calendar_boundary_and_sleep_crossing_period(self):
        records = [
            {'kind':'feeding','at':'2026-10-04T20:59:00Z','value':'OUTSIDE'},
            {'kind':'feeding','at':'2026-10-04T21:00:00Z','value':'INSIDE'},
            {'kind':'sleep','at':'2026-10-04T20:00:00Z','end':'2026-10-04T22:00:00Z'},
            {'kind':'mood','at':'2026-10-11T08:00:00Z','note':'PRIVATE'},
        ]
        result = care_summary.summary(records, 'Europe/Moscow', self.now)
        self.assertEqual(result['periodStart'], '2026-10-05')
        self.assertEqual(result['feeding']['records'], 1)
        self.assertEqual(result['sleep']['days'][0]['recordedSleepMinutes'], 60)
        self.assertEqual(result['records'], 2)
        self.assertNotIn('PRIVATE', str(result))

    def test_empty_days_are_unknown_not_missing_feeds(self):
        result = care_summary.summary([], 'Europe/Moscow', self.now)
        self.assertEqual(result['recordedDays'], 0)
        self.assertEqual(result['completeness'], 'unknown')
        self.assertEqual(len(result['feeding']['days']), 7)
        self.assertIn('отсутствие данных', result['rules'])
        self.assertIn('не определяет достаточность', result['rules'])

    def test_ongoing_timers_and_future_events(self):
        records = [
            {'kind':'feeding','at':'2026-10-11T08:00:00Z','value':'ГВ'},
            {'kind':'feeding','at':'2026-10-11T08:30:00Z','value':'Таймер кормления'},
            {'kind':'feeding','at':'2026-10-12T08:00:00Z','value':'FUTURE'},
            {'kind':'sleep','at':'2026-10-10T22:00:00Z'},
        ]
        result = care_summary.summary(records, 'Europe/Moscow', self.now)
        self.assertEqual(result['feeding']['records'], 2)
        self.assertEqual(result['feeding']['ongoingTimers'], 1)
        self.assertTrue(result['sleep']['ongoing'])
        self.assertIsNone(result['sleep']['lastRecordedSleepEnd'])

    def test_bad_legacy_dates_and_timezone_do_not_invent_data(self):
        result = care_summary.summary([{'kind':'sleep','at':'bad'}], 'Invalid/Zone', self.now)
        self.assertEqual(result['timezone'], 'Europe/Moscow')
        self.assertEqual(result['records'], 0)
