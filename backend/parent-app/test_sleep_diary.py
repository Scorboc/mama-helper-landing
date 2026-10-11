from test_care_tools import CareToolsTest
from datetime import datetime,timezone,timedelta
import sleep_summary
class SleepDiaryTest(CareToolsTest):
    def test_sleep_edit_overlap_and_metadata(self):
        cookie,_=self.setup_parent('sleep-diary@example.test')
        now=datetime.now(timezone.utc)
        def iso(n):return (now-timedelta(minutes=n)).isoformat()
        r={'id':'s1','kind':'sleep','at':iso(120),'end':iso(60),'sleepType':'day','settlingAt':iso(130),'feeling':'calm','note':'Test'}
        self.assertEqual(self.call('care-put',cookie,record=r)[0]['statusCode'],200)
        self.assertEqual(self.call('care-put',cookie,record={**r,'at':iso(125)})[0]['statusCode'],200)
        self.assertEqual(self.call('care-put',cookie,record={**r,'id':'s2','at':iso(90)})[0]['statusCode'],409)
        self.assertEqual(self.call('care-put',cookie,record={**r,'end':r['at']})[0]['statusCode'],400)
        self.assertEqual(self.call('care-put',cookie,record={'id':'w1','kind':'wake','at':iso(50),'wakeType':'morning','note':''})[0]['statusCode'],200)
        self.assertEqual(self.call('care-put',cookie,record={**r,'sleepType':'invented'})[0]['statusCode'],400)
        self.assertEqual(self.call('care-put',cookie,record={**r,'settlingAt':iso(10)})[0]['statusCode'],400)
    def test_summary_midnight_merge_and_unknown_gaps(self):
        now=datetime(2026,10,3,9,tzinfo=timezone.utc)
        records=[{'kind':'sleep','at':'2026-10-02T20:00:00Z','end':'2026-10-03T04:00:00Z'}, {'kind':'sleep','at':'2026-10-03T03:00:00Z','end':'2026-10-03T05:00:00Z'}]
        result=sleep_summary.summary(records,'Europe/Moscow',now)
        self.assertEqual(result['days'][-1]['recordedSleepMinutes'],480)
        self.assertEqual(result['days'][-2]['recordedSleepMinutes'],60)
        self.assertEqual(result['gapsBetweenRecordedSleepsMinutes'],[])
        self.assertIn('не подтверждённый',result['rules'])
