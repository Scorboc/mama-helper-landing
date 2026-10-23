from test_care_tools import CareToolsTest
from test_api import app


class CareRateLimitsTest(CareToolsTest):
    def test_read_exhaustion_does_not_block_writes(self):
        cookie, uid = self.setup_parent('read-limit@example.test')
        db = app.DB()
        try:
            for _ in range(600):
                app.rate_limit(db, 'care-read:' + uid, 600, 900)
        finally:
            db.close()
        for action in ('care-list', 'family-list'):
            self.assertEqual(self.call(action, cookie)[0]['statusCode'], 429)
        self.assertEqual(self.call('doctor-question-put', cookie, id='q', text='Synthetic question')[0]['statusCode'], 200)
        self.assertEqual(self.call('care-delete', cookie, id='missing')[0]['statusCode'], 200)

    def test_write_exhaustion_does_not_block_reads_or_other_users(self):
        cookie, uid = self.setup_parent('write-limit@example.test')
        other, _ = self.setup_parent('separate-limit@example.test')
        db = app.DB()
        try:
            for _ in range(120):
                app.rate_limit(db, 'care:' + uid, 120, 900)
        finally:
            db.close()
        for action in ('care-put', 'care-delete', 'care-import', 'family-invite', 'family-accept', 'family-revoke', 'doctor-question-put', 'doctor-question-delete'):
            self.assertEqual(self.call(action, cookie)[0]['statusCode'], 429, action)
        for action in ('care-list', 'family-list'):
            self.assertEqual(self.call(action, cookie)[0]['statusCode'], 200)
        self.assertEqual(self.call('doctor-question-put', other, id='q', text='Synthetic question')[0]['statusCode'], 200)
