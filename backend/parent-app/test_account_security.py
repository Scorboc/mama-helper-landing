"""Synthetic account lifecycle and controlled authentication interleavings."""
import json
import os
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from cryptography.fernet import Fernet
import index as app


class AccountSecurityTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='mama-auth-test-')
        self.environment = dict(os.environ)
        os.environ.update(APP_LOCAL='1', APP_SQLITE_PATH=self.directory.name+'/synthetic.sqlite3',
                          APP_DATA_KEY=Fernet.generate_key().decode(), APP_ORIGINS='http://localhost:5173')
        for key in ('APP_OPS_PATH', 'APP_AI_BUDGET_PATH', 'AI_POLICY_FILE'):
            os.environ.pop(key, None)
        app.initialize()

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.environment)
        self.directory.cleanup()

    def call(self, action, cookie='', ip='127.0.0.1', **data):
        response = app.handler({'httpMethod':'POST', 'headers':{'Origin':'http://localhost:5173',
            'Content-Type':'application/json', 'Cookie':cookie}, 'body':json.dumps({'action':action, **data}),
            'requestContext':{'identity':{'sourceIp':ip}}})
        return response, json.loads(response['body'])

    def register(self, email='security@example.test'):
        response, body = self.call('register', email=email, password='original-long-password', consent=True, adult=True, termsAccepted=True, termsVersion='account-2026-10-12')
        self.assertEqual(response['statusCode'], 200)
        return response['headers']['Set-Cookie'].split(';')[0], body

    def test_concurrent_recovery_consumes_code_exactly_once(self):
        _, account = self.register()
        entered, release = threading.Event(), threading.Event()
        original = app.password_hash
        def pause(value):
            if value == 'first-new-long-password':
                entered.set()
                self.assertTrue(release.wait(4))
            return original(value)
        with patch.object(app, 'password_hash', side_effect=pause), ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.call, 'recover', email=account['user']['email'],
                password='first-new-long-password', recoveryCode=account['recoveryCode'])
            self.assertTrue(entered.wait(4))
            second = pool.submit(self.call, 'recover', email=account['user']['email'],
                password='second-new-long-password', recoveryCode=account['recoveryCode'])
            time.sleep(.25)
            release.set()
            results = [first.result(8), second.result(8)]
        self.assertEqual(sorted(r[0]['statusCode'] for r in results), [200, 400])
        winner = next(r for r in results if r[0]['statusCode'] == 200)
        cookie = winner[0]['headers']['Set-Cookie'].split(';')[0]
        self.assertEqual(self.call('session', cookie)[0]['statusCode'], 200)

    def test_old_password_login_cannot_survive_concurrent_recovery(self):
        _, account = self.register()
        entered, release = threading.Event(), threading.Event()
        original = app.password_valid
        def pause(value, saved):
            valid = original(value, saved)
            if threading.current_thread().name.startswith('lagging-login'):
                entered.set()
                self.assertTrue(release.wait(4))
            return valid
        with patch.object(app, 'password_valid', side_effect=pause):
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix='lagging-login') as login_pool, ThreadPoolExecutor(max_workers=1) as reset_pool:
                login = login_pool.submit(self.call, 'login', email=account['user']['email'], password='original-long-password')
                self.assertTrue(entered.wait(4))
                reset = reset_pool.submit(self.call, 'recover', email=account['user']['email'],
                    password='recovered-long-password', recoveryCode=account['recoveryCode'])
                time.sleep(1)
                release.set()
                login_response, _ = login.result(8)
                reset_response, _ = reset.result(8)
        self.assertEqual(reset_response['statusCode'], 200)
        if login_response['statusCode'] == 200:
            token = login_response['headers']['Set-Cookie'].split(';')[0]
            self.assertEqual(self.call('session', token)[0]['statusCode'], 401)
        else:
            self.assertEqual(login_response['statusCode'], 401)

    def test_delete_failed_attempts_are_durable_and_capped(self):
        cookie, _ = self.register()
        for _ in range(10):
            self.assertEqual(self.call('delete', cookie, password='wrong-long-password')[0]['statusCode'], 401)
        response, _ = self.call('delete', cookie, password='wrong-long-password')
        self.assertEqual(response['statusCode'], 429)
        self.assertEqual(self.call('session', cookie)[0]['statusCode'], 200)

    def test_password_change_preserves_every_account_payload_and_recovery_code(self):
        cookie, account = self.register()
        second, _ = self.call('login', email=account['user']['email'], password='original-long-password')
        other_cookie = second['headers']['Set-Cookie'].split(';')[0]
        state = account['state']; state['conversationTitle'] = 'Synthetic 50-question history'
        state['messages'] = [{'id':str(i), 'role':'user' if i % 2 == 0 else 'assistant', 'text':'Synthetic entry'} for i in range(100)]
        self.assertEqual(self.call('save', cookie, state=state, revision=0)[0]['statusCode'], 200)
        response, result = self.call('change-password', cookie, currentPassword='original-long-password', password='updated-long-password')
        self.assertEqual(response['statusCode'], 200)
        fresh = response['headers']['Set-Cookie'].split(';')[0]
        for old in (cookie, other_cookie): self.assertEqual(self.call('session', old)[0]['statusCode'], 401)
        loaded = self.call('session', fresh)[1]
        self.assertEqual(loaded['state'], state)
        self.assertEqual(loaded['revision'], 1)
        self.assertEqual(loaded['quota'], account['quota'])
        self.assertNotIn('recoveryCode', result)
        self.assertNotIn('X-Set-Cookie', response['headers'])
        self.assertIn('HttpOnly', response['headers']['Set-Cookie'])
        self.assertEqual(self.call('login', email=account['user']['email'], password='original-long-password')[0]['statusCode'], 401)
        self.assertEqual(self.call('login', email=account['user']['email'], password='updated-long-password')[0]['statusCode'], 200)
        self.assertEqual(self.call('recover', email=account['user']['email'], password='recovered-long-password', recoveryCode=account['recoveryCode'])[0]['statusCode'], 200)

    def test_recovery_rotation_and_logout_all_revoke_every_prior_session(self):
        cookie, account = self.register()
        response, rotated = self.call('rotate-recovery', cookie, currentPassword='original-long-password')
        self.assertEqual(response['statusCode'], 200)
        self.assertNotEqual(rotated['recoveryCode'], account['recoveryCode'])
        fresh = response['headers']['Set-Cookie'].split(';')[0]
        self.assertEqual(self.call('session', cookie)[0]['statusCode'], 401)
        self.assertEqual(self.call('recover', email=account['user']['email'], password='recovered-long-password', recoveryCode=account['recoveryCode'])[0]['statusCode'], 400)
        response, _ = self.call('logout-all', fresh, currentPassword='original-long-password')
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Max-Age=0', response['headers']['Set-Cookie'])
        self.assertEqual(self.call('session', fresh)[0]['statusCode'], 401)
        response, _ = self.call('recover', email=account['user']['email'], password='recovered-long-password', recoveryCode='  '+rotated['recoveryCode']+'  ')
        self.assertEqual(response['statusCode'], 200)

    def test_short_migrated_and_beta_credentials_are_accepted_but_not_new_passwords(self):
        db = app.DB()
        for uid, email in [('legacy-short','old@example.test'), ('beta-short','test01')]:
            db.query('INSERT INTO mh_users VALUES(?,?,?,?,?,?)', (uid,email,app.password_hash('1'),app.digest('synthetic-recovery-code'),0,'test-v1'))
            db.query('INSERT INTO mh_state VALUES(?,?,0)', (uid,app.seal(app.blank_state())))
        db.conn.commit(); db.close()
        response, _ = self.call('login', email='test01', password='1')
        beta = response['headers']['Set-Cookie'].split(';')[0]
        self.assertEqual(self.call('delete', beta, password='1')[0]['statusCode'], 200)
        response, _ = self.call('login', email='old@example.test', password='1')
        old = response['headers']['Set-Cookie'].split(';')[0]
        self.assertEqual(self.call('change-password', old, currentPassword='1', password='2')[0]['statusCode'], 400)
        self.assertEqual(self.call('change-password', old, currentPassword='1', password='new-secure-password')[0]['statusCode'], 200)
        self.assertEqual(self.call('register', email='short@example.test', password='1', consent=True)[0]['statusCode'], 400)

    def test_credential_actions_require_current_password_and_cannot_select_other_user(self):
        owner, a = self.register('a@example.test'); guest, b = self.register('b@example.test')
        for action in ('change-password', 'rotate-recovery', 'logout-all'):
            self.assertEqual(self.call(action, owner, currentPassword='wrong-long-password', password='updated-long-password', user_id=b['user']['id'])[0]['statusCode'], 401)
            self.assertEqual(self.call(action, currentPassword='original-long-password', password='updated-long-password')[0]['statusCode'], 401)
        self.assertEqual(self.call('session', guest)[1]['user']['id'], b['user']['id'])
        self.assertEqual(self.call('session', owner)[1]['user']['id'], a['user']['id'])
        self.assertEqual(self.call('change-password', owner, currentPassword='original-long-password', password='updated-long-password', user_id=b['user']['id'])[0]['statusCode'], 200)
        self.assertEqual(self.call('login', email=b['user']['email'], password='original-long-password')[0]['statusCode'], 200)

    def test_stale_session_cannot_reauthenticate_after_waiting_for_lock(self):
        cookie, account = self.register()
        original = app.locked_credentials
        def revoke(db, **kwargs):
            row = original(db, **kwargs)
            db.query('DELETE FROM mh_sessions WHERE user_id=?', (account['user']['id'],))
            return row
        with patch.object(app, 'locked_credentials', side_effect=revoke):
            self.assertEqual(self.call('change-password', cookie, currentPassword='original-long-password', password='updated-long-password')[0]['statusCode'], 401)
        self.assertEqual(self.call('login', email=account['user']['email'], password='original-long-password')[0]['statusCode'], 200)

    def test_inputs_origin_cookie_expiry_and_hashes_remain_guarded(self):
        cookie, account = self.register('  Upper@Example.test  ')
        self.assertEqual(account['user']['email'], 'upper@example.test')
        for value in ('', 'x'*129, {}, None):
            self.assertEqual(self.call('login', email=account['user']['email'], password=value)[0]['statusCode'], 400)
        self.assertFalse(app.password_valid('anything', 'malformed'))
        self.assertFalse(app.password_valid('anything', 'cf-locked$recover-with-existing-code'))
        db = app.DB()
        credential = db.query('SELECT password_hash,recovery_hash FROM mh_users').fetchone()
        self.assertNotIn('original-long-password', credential[0])
        self.assertNotEqual(credential[1], account['recoveryCode'])
        db.query('UPDATE mh_sessions SET expires_at=?', (int(time.time())-1,)); db.conn.commit(); db.close()
        self.assertEqual(self.call('session', cookie)[0]['statusCode'], 401)
        forbidden = app.handler({'httpMethod':'POST','headers':{'Origin':'https://evil.example','Content-Type':'text/plain'},'body':json.dumps({'action':'register'})})
        self.assertEqual(forbidden['statusCode'], 403)
        with patch.dict(os.environ, {'APP_LOCAL':'0'}):
            secure = app.cookie('synthetic-token')
            self.assertIn('Secure', secure); self.assertIn('HttpOnly', secure); self.assertIn('SameSite=Lax', secure)

    def test_postgres_credential_read_uses_row_lock(self):
        class FakeDB:
            sqlite = False
            def query(self, sql, params):
                self.sql, self.params = sql, params
                return self
            def fetchone(self): return ('id','a@example.test','hash','recovery')
        db = FakeDB()
        self.assertEqual(app.locked_credentials(db, email='a@example.test')[0], 'id')
        self.assertTrue(db.sql.endswith(' FOR UPDATE'))
        self.assertEqual(db.params, ('a@example.test',))


if __name__ == '__main__':
    unittest.main()
