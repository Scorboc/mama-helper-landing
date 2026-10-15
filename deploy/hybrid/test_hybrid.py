"""Synthetic production-adapter checks. No real accounts, network AI, or mail."""
import http.client
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP / 'backend/parent-app'))
import production_server as server_module


class HybridApiTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='mama-hybrid-synthetic-')
        self.env = patch.dict(os.environ, {
            'APP_LOCAL': '0', 'APP_DB_DRIVER': 'sqlite', 'APP_COOKIE_SECURE': '1',
            'APP_COOKIE_CROSS_SITE': '0', 'APP_BILLING_MODE': 'paid', 'APP_PAYMENTS_ENABLED': '0',
            'APP_SQLITE_PATH': self.directory.name + '/accounts.sqlite3',
            'APP_DATA_KEY': Fernet.generate_key().decode(),
            'APP_ORIGINS': 'https://app.mama.test', 'APP_PUBLIC_URL': 'https://app.mama.test',
            'APP_OPERATOR_NAME': 'Synthetic test operator', 'APP_OPERATOR_INN': '000000000000',
            'APP_OPERATOR_ADDRESS': 'Synthetic fixture', 'APP_SUPPORT_EMAIL': 'support@example.test',
            'APP_DATA_COUNTRY': 'RU', 'APP_LEGAL_APPROVED': '1',
            'MAMA_AUTOMATION_ROOT': self.directory.name + '/automation',
            'MAMA_AUTOMATION_TOKEN': 'synthetic-test-token',
        }, clear=True)
        self.env.start()
        server_module.app.initialize()
        self.server = server_module.AppServer(('127.0.0.1', 0), server_module.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.env.stop(); self.directory.cleanup()

    def request(self, action='config', cookie='', origin='https://app.mama.test', method='POST', **data):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        body = json.dumps({'action': action, **data}) if method == 'POST' else None
        connection.request(method, '/api', body, {'Origin': origin, 'Content-Type': 'application/json',
                           'Cookie': cookie, 'Access-Control-Request-Method': 'POST',
                           'Access-Control-Request-Headers': 'content-type'})
        response = connection.getresponse()
        status, headers, raw = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return status, headers, json.loads(raw) if raw else {}

    def register(self, email):
        status, headers, body = self.request('register', email=email, password='synthetic-long-password',
            consent=True, adult=True, termsAccepted=True, termsVersion='account-2026-10-12')
        self.assertEqual(status, 200, body)
        return headers['Set-Cookie'].split(';')[0], body

    def test_preflight_allows_exact_origin_and_credentials(self):
        status, headers, _ = self.request(method='OPTIONS')
        self.assertEqual(status, 204)
        self.assertEqual(headers['Access-Control-Allow-Origin'], 'https://app.mama.test')
        self.assertEqual(headers['Access-Control-Allow-Credentials'], 'true')
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertIn('Origin', headers['Vary'])

    def test_foreign_origin_is_denied_for_post_and_preflight(self):
        for origin in ('https://evil.mama.test', 'https://app.mama.test.evil.test', 'https://preview.pages.dev'):
            for method in ('POST', 'OPTIONS'):
                status, headers, _ = self.request(origin=origin, method=method)
                self.assertEqual(status, 403)
                self.assertNotIn('Access-Control-Allow-Origin', headers)

    def test_registration_stays_closed_without_approved_operator_documents(self):
        with patch.dict(os.environ, {'APP_LEGAL_APPROVED': '0'}):
            self.assertEqual(self.request('register', email='closed@example.test',
                password='synthetic-long-password', consent=True, adult=True,
                termsAccepted=True, termsVersion='account-2026-10-12')[0], 503)

    def test_session_cookie_is_secure_host_only_and_works_after_reload(self):
        status, headers, body = self.request('register', email='cookie@example.test',
            password='synthetic-long-password', consent=True, adult=True, termsAccepted=True,
            termsVersion='account-2026-10-12')
        self.assertEqual(status, 200, body)
        raw = headers['Set-Cookie']
        for flag in ('HttpOnly', 'Secure', 'SameSite=Lax', 'Path=/'):
            self.assertIn(flag, raw)
        self.assertNotIn('Domain=', raw)
        cookie = raw.split(';')[0]
        status, _, session = self.request('session', cookie)
        self.assertEqual(status, 200)
        self.assertEqual(session['user']['id'], body['user']['id'])
        self.assertEqual(self.request('logout', cookie)[0], 200)
        self.assertEqual(self.request('session', cookie)[0], 401)

    def test_profiles_and_50_question_history_survive_and_remain_isolated(self):
        cookie, first = self.register('first@example.test')
        other_cookie, second = self.register('second@example.test')
        # Synthetic evidence in the isolated test DB only. The real migration
        # never fabricates consents or changes the production legal gate.
        db = server_module.app.DB()
        db.query('INSERT INTO mh_health_consents VALUES(?,?,?,?,?)',
                 (first['user']['id'], 'a' * 64, 'signed-paper', 1, 0))
        db.conn.commit(); db.close()
        state = first['state']
        state['profile'] = {'role': 'mom', 'stage': 'child', 'birthDate': '2026-06-13',
                            'week': 20, 'weekDate': '2026-10-13',
                            'feeding': 'mixed', 'sleep': '', 'health': '', 'healthConfirmed': False,
                            'topics': ['sleep', 'play'], 'childName': 'Synthetic child'}
        state['conversationTitle'] = 'Synthetic 50-question check'
        state['messages'] = [{'id': str(i), 'role': 'user' if i % 2 == 0 else 'assistant',
                              'text': 'Synthetic entry'} for i in range(100)]
        self.assertEqual(self.request('save', cookie, state=state, revision=first['revision'])[0], 200)
        restored = self.request('session', cookie)[2]['state']
        self.assertEqual(restored['messages'], state['messages'])
        self.assertEqual(restored['profile']['birthDate'], '2026-06-13')
        self.assertEqual(self.request('session', other_cookie)[2]['state']['messages'], [])
        self.assertNotEqual(first['user']['id'], second['user']['id'])

    def test_automation_monitor_can_use_deployed_frontend_without_export(self):
        spec = importlib.util.spec_from_file_location('hybrid_bridge', APP / 'backend/parent-app/automation_bridge.py')
        bridge = importlib.util.module_from_spec(spec); spec.loader.exec_module(bridge)
        urls = []
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, *args): return b'<div id="root"></div>' if len(urls) == 1 else b'{"ok":true}'
        def get(url, **kwargs):
            urls.append(url); return Response()
        with patch.dict(os.environ, {'APP_MONITOR_URL': 'https://app.mama.test'}), \
             patch.object(bridge.urllib.request, 'urlopen', side_effect=get):
            self.assertTrue(bridge.monitor()['ok'])
        self.assertEqual(urls, ['https://app.mama.test/', 'http://127.0.0.1:8787/healthz',
                               'http://127.0.0.1:5678/healthz/readiness'])


if __name__ == '__main__':
    unittest.main()
