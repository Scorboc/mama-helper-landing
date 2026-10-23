"""Synthetic requests only; no Telegram config, keys, network or live databases."""
import os
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import data_rights
import telegram_outbox
import test_api as base


class DataRightsNotificationTest(unittest.TestCase):
    tearDown = base.AccountsTest.tearDown
    call = base.AccountsTest.call
    register = base.AccountsTest.register

    def setUp(self):
        base.AccountsTest.setUp(self)
        os.environ['MAMA_AUTOMATION_ROOT'] = self.temp.name
        self.root = Path(self.temp.name)
        self.cookie, self.session = self.register('synthetic-private@example.test')
        self.request = dict(kind='correct', requestId='qa-request-1',
                            text='Имя ребёнка SYNTHETIC_CHILD; synthetic-private@example.test; SECRET_TEXT')

    def rows(self):
        with closing(telegram_outbox.database(self.root)) as db:
            return db.execute('SELECT id,kind,body,state FROM messages').fetchall()

    def submit(self):
        response, body = self.call('data-request', self.cookie, **self.request)
        self.assertEqual(response['statusCode'], 200, body)
        self.assertEqual(body['id'], self.request['requestId'])

    def test_queued_metadata_only_and_no_duplicate(self):
        self.submit()
        self.submit()
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['id'], 'data-request:qa-request-1')
        self.assertEqual(row['kind'], 'data-request')
        self.assertEqual(row['state'], 'queued')
        for required in ('Исправление данных', 'qa-request-1', 'Дата:',
                         'Крайний срок ответа:', '10 рабочих дней',
                         'уточнить у юриста', 'http://127.0.0.1:8791/'):
            self.assertIn(required, row['body'])
        for private in (self.request['text'], 'synthetic-private@example.test',
                        'SYNTHETIC_CHILD', 'SECRET_TEXT', self.session['user']['id']):
            self.assertNotIn(private, row['body'])

    def test_queue_failure_preserves_request_and_retry_repairs_queue(self):
        with patch.object(telegram_outbox, 'put', side_effect=OSError('synthetic failure')):
            self.submit()
        response, body = self.call('data-request-list', self.cookie)
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual([r['id'] for r in body['items']], ['qa-request-1'])
        self.assertEqual(len(self.rows()), 0)
        self.submit()
        self.submit()
        self.assertEqual(len(self.rows()), 1)

    def test_deadline_skips_weekends(self):
        stamp = int(datetime(2026, 10, 23, 12, tzinfo=ZoneInfo('Europe/Moscow')).timestamp())
        data_rights.notify_owner('access', 'qa-deadline', stamp)
        self.assertIn('Дата: 23.10.2026 12:00', self.rows()[0]['body'])
        self.assertIn('Крайний срок ответа: 06.11.2026', self.rows()[0]['body'])


if __name__ == '__main__':
    unittest.main()