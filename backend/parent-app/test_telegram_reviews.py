"""Synthetic owner report -> revision -> selected chat -> acknowledged result."""
from contextlib import closing
import json
from pathlib import Path
import tempfile
import time
import unittest

import telegram_admin as admin
import telegram_outbox as outbox
import telegram_reviews as reviews


class ReviewTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.thread = '00000000-0000-0000-0000-000000000001'
        (self.root / 'chat-handoff-settings.json').write_text(json.dumps({'enabled': True, 'threadId': self.thread}))
        self.cfg = {'chatId': '123456', 'enabledAt': 1}

    def offer(self):
        return reviews.offer(self.root, 'synthetic:1', 'Тест передачи', 'Искусственный сигнал, не ошибка сайта.', 'Подготовить синтетическую проверку.', True)

    def update(self, number, text, owner=123456, reply=None):
        msg = {'date': int(time.time()), 'chat': {'id': owner, 'type': 'private'}, 'from': {'id': owner}, 'text': text}
        if reply:
            msg['reply_to_message'] = {'message_id': reply}
        return {'update_id': number, 'message': msg}

    def state(self, ident):
        with closing(outbox.database(self.root)) as db:
            return dict(db.execute('SELECT * FROM admin_reviews WHERE id=?', (ident,)).fetchone())

    def test_complete_chain_and_latest_revision(self):
        ident = self.offer()
        admin.process(self.root, self.cfg, [self.update(1, '/revise ' + ident + ' Первый вариант'),
                                           self.update(2, '/revise ' + ident + ' Только исправить подпись'),
                                           self.update(3, '/send ' + ident)])
        pending = reviews.pending(self.root, self.thread)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['revision'], 2)
        self.assertIn('Только исправить подпись', pending[0]['prompt'])
        self.assertNotIn('Первый вариант', pending[0]['prompt'])
        reviews.claim(self.root, ident, self.thread)
        reviews.finish(self.root, ident, self.thread, 'Синтетическая проверка выполнена, сайт не изменён.')
        self.assertEqual(self.state(ident)['state'], 'done')
        with closing(outbox.database(self.root)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM messages WHERE kind='review-status'").fetchone()[0], 2)

    def test_reports_deduplicate(self):
        ident = self.offer()
        self.assertEqual(self.offer(), ident)
        with closing(outbox.database(self.root)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM admin_reviews').fetchone()[0], 1)

    def test_owner_can_reply_to_delivered_report(self):
        ident = self.offer()
        with closing(outbox.database(self.root)) as db:
            db.execute("UPDATE messages SET state='sent',message_id=711 WHERE id=?", ('review:' + ident,))
            db.commit()
        admin.process(self.root, self.cfg, [self.update(1, 'Моя полная редакция', reply=711)])
        self.assertEqual(self.state(ident)['edited'], 'Моя полная редакция')

    def test_reply_to_unrelated_message_does_not_create_task(self):
        ident = self.offer()
        admin.process(self.root, self.cfg, [self.update(1, 'Не задание', reply=999)])
        self.assertEqual(self.state(ident)['state'], 'draft')

    def test_plain_owner_edit_uses_only_unambiguous_open_report_without_execution(self):
        ident = self.offer()
        admin.process(self.root, self.cfg, [self.update(1, 'Моя полная редакция без команды')])
        self.assertEqual(self.state(ident)['state'], 'edited')
        self.assertEqual(reviews.pending(self.root, self.thread), [])
        reviews.offer(self.root, 'synthetic:2', 'Второй', 'Тест', 'Проверить второй')
        admin.process(self.root, self.cfg, [self.update(2, 'Не выбираю за пользователя')])
        self.assertEqual(self.state(ident)['revision'], 1)

    def test_editing_telegram_message_revises_draft_but_never_executes(self):
        ident = self.offer()
        edited = self.update(1, '/revise ' + ident + ' Исправленная редакция')
        edited['edited_message'] = edited.pop('message')
        edited['edited_message']['edit_date'] = int(time.time())
        admin.process(self.root, self.cfg, [edited])
        self.assertEqual(self.state(ident)['edited'], 'Исправленная редакция')
        execute = self.update(2, '/send ' + ident)
        execute['edited_message'] = execute.pop('message')
        admin.process(self.root, self.cfg, [execute])
        self.assertEqual(self.state(ident)['state'], 'edited')

    def test_other_user_and_forwarded_command_ignored(self):
        ident = self.offer()
        forwarded = self.update(2, '/revise ' + ident + ' Пересланная команда')
        forwarded['message']['forward_origin'] = {'type': 'user'}
        admin.process(self.root, self.cfg, [self.update(1, '/revise ' + ident + ' Чужая задача', owner=77), forwarded])
        self.assertEqual(self.state(ident)['state'], 'draft')

    def test_cannot_send_unedited_or_repeat_or_change_queued_version(self):
        ident = self.offer()
        admin.process(self.root, self.cfg, [self.update(1, '/send ' + ident)])
        self.assertEqual(self.state(ident)['state'], 'draft')
        admin.process(self.root, self.cfg, [self.update(2, '/revise ' + ident + ' Проверить кнопку'), self.update(3, '/send ' + ident),
                                           self.update(4, '/send ' + ident), self.update(5, '/revise ' + ident + ' Другая задача')])
        self.assertEqual(len(reviews.pending(self.root, self.thread)), 1)
        self.assertEqual(self.state(ident)['edited'], 'Проверить кнопку')

    def test_cancellation_prevents_claim(self):
        ident = self.offer()
        admin.process(self.root, self.cfg, [self.update(1, '/revise ' + ident + ' Проверить'), self.update(2, '/send ' + ident),
                                           self.update(3, '/cancel_review ' + ident)])
        with self.assertRaises(ValueError):
            reviews.claim(self.root, ident, self.thread)
        self.assertEqual(reviews.pending(self.root, self.thread), [])

    def test_wrong_chat_and_double_claim_rejected(self):
        ident = self.offer()
        admin.process(self.root, self.cfg, [self.update(1, '/revise ' + ident + ' Проверить'), self.update(2, '/send ' + ident)])
        self.assertEqual(reviews.pending(self.root, 'other'), [])
        with self.assertRaises(ValueError):
            reviews.claim(self.root, ident, 'other')
        reviews.claim(self.root, ident, self.thread)
        with self.assertRaises(ValueError):
            reviews.claim(self.root, ident, self.thread)
        with self.assertRaises(ValueError):
            reviews.finish(self.root, ident, 'other', 'Не мой результат')

    def test_missing_configuration_does_not_claim_delivery(self):
        ident = self.offer()
        (self.root / 'chat-handoff-settings.json').unlink()
        admin.process(self.root, self.cfg, [self.update(1, '/revise ' + ident + ' Проверить'), self.update(2, '/send ' + ident)])
        self.assertEqual(self.state(ident)['state'], 'edited')

    def test_secrets_rejected_and_report_says_synthetic(self):
        ident = self.offer()
        secret = '123456789:' + 'A' * 35
        admin.process(self.root, self.cfg, [self.update(1, '/revise ' + ident + ' ' + secret)])
        self.assertEqual(self.state(ident)['state'], 'draft')
        with closing(outbox.database(self.root)) as db:
            bodies = '\n'.join(r[0] for r in db.execute('SELECT body FROM messages'))
        self.assertNotIn(secret, bodies)
        self.assertIn('ТЕСТ', bodies)

    def test_maximum_edit_fits_telegram_message(self):
        ident = self.offer()
        admin.process(self.root, self.cfg, [self.update(1, '/revise ' + ident + ' ' + 'я' * 1600)])
        with closing(outbox.database(self.root)) as db:
            self.assertLessEqual(len(db.execute("SELECT body FROM messages WHERE id='admin:1'").fetchone()[0]), 4096)
        self.assertLessEqual(len(admin.HELP), 4096)


if __name__ == '__main__':
    unittest.main()
