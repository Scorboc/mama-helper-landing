"""Synthetic exact-version publication gates; no GitHub/network calls."""
from contextlib import closing
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import telegram_outbox as outbox
import telegram_publication as publication
import telegram_reviews as reviews
import telegram_tasks as tasks


class PublicationTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.thread = '00000000-0000-0000-0000-000000000001'
        (self.root / 'github-publication-settings.json').write_text(json.dumps({'enabled': True, 'repository': publication.REPO, 'branch': 'main'}))
        (self.root / 'chat-handoff-settings.json').write_text(json.dumps({'enabled': True, 'threadId': self.thread}))
        self.app = self.root / 'app'
        (self.app / 'src').mkdir(parents=True)
        (self.app / 'src/a.ts').write_text('export const test = 1;')
        self.patch = patch.object(tasks, 'APP', self.app)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        artifact = self.root / 'tasks/1'
        (artifact / 'work/app/src').mkdir(parents=True)
        (artifact / 'work/app/src/a.ts').write_text('export const test = 1;')
        (artifact / 'verified.json').write_text(json.dumps({'files': ['src/a.ts'], 'build': True, 'tests': 3}))
        (artifact / 'baseline.json').write_text('{}')
        with closing(outbox.database(self.root)) as db:
            tasks.prepare(db)
            db.execute("INSERT INTO admin_tasks(update_id,idea,status,created) VALUES(1,'Тест','applied',1)")
            db.commit()

    def submit(self, text='T1'):
        with closing(outbox.database(self.root)) as db:
            result = publication.submit(self.root, db, text)
            db.commit()
            return result

    def test_queues_exact_immutable_snapshot_once(self):
        self.assertIn('поставлена в очередь', self.submit())
        self.assertIn('уже зарегистрирована', self.submit())
        rows = reviews.pending(self.root, self.thread)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['kind'], 'publish')
        ident = rows[0]['id']
        self.assertTrue((self.root / 'publications' / ident / 'files/src/a.ts').exists())

    def test_unverified_and_changed_sources_stop(self):
        with closing(outbox.database(self.root)) as db:
            db.execute("UPDATE admin_tasks SET status='failed'")
            db.commit()
        self.assertIn('не проверена', self.submit())
        with closing(outbox.database(self.root)) as db:
            db.execute("UPDATE admin_tasks SET status='applied'")
            db.commit()
        (self.app / 'src/a.ts').write_text('concurrent edit')
        self.assertIn('уже изменилась', self.submit())

    def test_wrong_repo_or_branch_cannot_enable(self):
        path = self.root / 'github-publication-settings.json'
        path.write_text(json.dumps({'enabled': True, 'repository': 'someone/else', 'branch': 'main'}))
        self.assertIn('не настроена', self.submit())

    def test_requires_exact_task_identifier(self):
        for text in ('', 'T1; run command', '../1', '1', 'T0'):
            self.assertIn('/publish T123', self.submit(text))

    def test_publish_requires_claim_and_detects_tampered_snapshot(self):
        self.submit()
        ident = reviews.pending(self.root, self.thread)[0]['id']
        with patch.object(publication, 'run') as runner:
            with self.assertRaisesRegex(ValueError, 'not-claimed'):
                publication.publish(self.root, ident, self.thread)
            reviews.claim(self.root, ident, self.thread)
            (self.root / 'publications' / ident / 'files/src/a.ts').write_text('tampered')
            with self.assertRaisesRegex(ValueError, 'changed-snapshot'):
                publication.publish(self.root, ident, self.thread)
            runner.assert_not_called()

    def git_probe(self, concurrent=False):
        """Real Git clone/commit/push against a disposable local bare repository."""
        bare = self.root / 'remote.git'
        seed = self.root / 'seed'
        def git(*argv, cwd=None):
            p = subprocess.run(['git', *argv], cwd=cwd, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr.decode(errors='replace'))
            return p.stdout
        git('init', '--bare', str(bare))
        git('init', '-b', 'main', str(seed))
        git('config', 'user.name', 'Synthetic Test', cwd=seed)
        git('config', 'user.email', 'test@example.invalid', cwd=seed)
        (seed / 'README.md').write_text('Synthetic repository only.')
        git('add', 'README.md', cwd=seed)
        git('commit', '-m', 'Synthetic baseline', cwd=seed)
        git('remote', 'add', 'origin', str(bare), cwd=seed)
        git('push', '-u', 'origin', 'main', cwd=seed)
        self.submit()
        ident = reviews.pending(self.root, self.thread)[0]['id']
        reviews.claim(self.root, ident, self.thread)
        original = publication.run
        def isolated(argv, cwd=None, acceptable=(0,)):
            if argv[:2] == ['git', 'clone']:
                argv = [str(bare) if a == 'https://github.com/' + publication.REPO + '.git' else a for a in argv]
            if argv[:3] == ['gh', 'api', 'user']:
                return subprocess.CompletedProcess(argv, 0, b'{"id":1,"login":"synthetic"}', b'')
            if argv[:2] == ['gh', 'api']:
                commit = argv[2].rsplit('/', 1)[1]
                git('--git-dir=' + str(bare), 'cat-file', '-e', commit + '^{commit}')
                return subprocess.CompletedProcess(argv, 0, json.dumps({'sha': commit}).encode(), b'')
            if concurrent and argv[:1] == ['git'] and 'push' in argv:
                (seed / 'README.md').write_text('Concurrent remote change must survive.')
                git('add', 'README.md', cwd=seed)
                git('commit', '-m', 'Concurrent change', cwd=seed)
                git('push', 'origin', 'main', cwd=seed)
            self.assertNotIn('--force', argv)
            return original(argv, cwd, acceptable)
        with patch.object(publication, 'run', side_effect=isolated):
            if concurrent:
                with self.assertRaisesRegex(ValueError, 'publication-command-failed'):
                    publication.publish(self.root, ident, self.thread)
                self.assertIn(b'Concurrent remote', git('--git-dir=' + str(bare), 'show', 'main:README.md'))
                p = subprocess.run(['git', '--git-dir=' + str(bare), 'show', 'main:src/a.ts'], capture_output=True)
                self.assertNotEqual(p.returncode, 0)
            else:
                result = publication.publish(self.root, ident, self.thread)
                self.assertTrue(result['ok'])
                self.assertTrue(result['sourceOnly'])
                self.assertEqual(git('--git-dir=' + str(bare), 'show', 'main:src/a.ts'), (self.app / 'src/a.ts').read_bytes())

    def test_real_local_git_publication(self):
        self.git_probe()

    def test_concurrent_remote_push_is_not_overwritten(self):
        self.git_probe(concurrent=True)


if __name__ == '__main__':
    unittest.main()
