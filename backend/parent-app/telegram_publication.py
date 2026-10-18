"""Publish an owner-selected, verified task snapshot to one GitHub source branch.

Telegram only queues an intent. The designated Codex chat claims it and executes
this publisher. Normal fast-forward Git push rejects concurrent remote changes.
"""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid

import telegram_outbox as outbox
import telegram_reviews as reviews
import telegram_tasks as tasks

REPO = 'Scorboc/mama-helper-landing'


def settings(root):
    path = root / 'github-publication-settings.json'
    if not path.exists():
        return None
    cfg = json.loads(path.read_text(encoding='utf-8'))
    return cfg if cfg.get('enabled') is True and cfg.get('repository') == REPO and cfg.get('branch') == 'main' else None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def submit(root, db, text):
    cfg = settings(root)
    chat = reviews.settings(root)
    if not cfg or not chat:
        return 'Публикация в GitHub ещё не настроена; подтверждение не сохраняется для будущих версий.'
    if not re.fullmatch(r'T[1-9][0-9]{0,8}', text):
        return 'Публикация исходников: /publish T123 — результат проверенной /task №123. Сначала /status. Данные и ключи не отправляются. Сервер аккаунтов этой командой не запускается.'
    tasks.prepare(db)
    row = db.execute('SELECT status FROM admin_tasks WHERE id=?', (int(text[1:]),)).fetchone()
    if not row or row['status'] != 'applied':
        return 'Эта задача не проверена и не применена локально. Публикация не поставлена в очередь.'
    artifact = root / 'tasks' / text[1:]
    try:
        verified = json.loads((artifact / 'verified.json').read_text(encoding='utf-8'))
        base = json.loads((artifact / 'baseline.json').read_text(encoding='utf-8'))
        files = verified['files']
        if verified.get('build') is not True or type(verified.get('tests')) is not int or verified['tests'] <= 0:
            raise ValueError('unverified-task')
        if not isinstance(files, list) or not 1 <= len(files) <= 40 or len(set(files)) != len(files):
            raise ValueError('invalid-files')
        candidate = artifact / 'work/app'
        hashes = {}
        for name in files:
            if not tasks.allowed_change(name):
                raise ValueError('scope')
            path = candidate / name
            if path.is_symlink() or not path.resolve().is_relative_to(candidate.resolve()) or path.stat().st_size > 500000:
                raise ValueError('unsafe-source')
            content = path.read_text(encoding='utf-8')
            if reviews.SECRET.search(content):
                raise ValueError('secret')
            if digest(tasks.APP / name) != digest(path):
                raise ValueError('local-source-changed')
            previous = artifact / 'rollback' / name
            normalized = None
            if previous.exists() and digest(previous) == base.get(name):
                normalized = hashlib.sha256(previous.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            hashes[name] = {'sha256': digest(path), 'base': base.get(name), 'baseNormalized': normalized}
    except (OSError, ValueError, KeyError, TypeError):
        return 'Проверенная версия недоступна, содержит запрещённые файлы или уже изменилась. Сначала повторная локальная проверка; публикации нет.'
    fingerprint = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    key = 'publication:' + text + ':' + fingerprint
    reviews.prepare(db)
    old = db.execute('SELECT id FROM admin_reviews WHERE source_key=?', (key,)).fetchone()
    if old:
        return 'Публикация уже зарегистрирована: ' + old['id'] + '. Повтор не создан.'
    ident = 'R' + uuid.uuid4().hex[:12]
    folder = root / 'publications' / ident
    folder.mkdir(parents=True)
    for name in files:
        dest = folder / 'files' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidate / name, dest)
    manifest = {'id': ident, 'task': text, 'repository': REPO, 'branch': 'main', 'files': hashes,
                'build': True, 'tests': verified['tests'], 'fingerprint': fingerprint}
    (folder / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    prompt = (f'Владелец командой /publish {text} разрешил публикацию конкретного проверенного снимка {ident} '
              f'в {REPO}, ветка main. Это исходники; GitHub Pages/backend отдельно не переключать. '
              'Запусти telegram_publication.py с --root private/n8n, --thread ID_ЭТОГО_ЧАТА, --id ' + ident + '. '
              'Модуль проверяет снимок, сравнивает удалённые исходники с базой задачи, сохраняет старый commit '
              'и выполняет обычный push без force. При конфликте остановись, не перезаписывай удалённые правки. '
              'Не публикуй дополнительные файлы, private/, базы или секреты. Результат проверь через GitHub API; '
              'затем запиши finish в очереди и сообщи commit. Не утверждай, что сайт развёрнут, по одному push.')
    db.execute('''INSERT INTO admin_reviews
      (id,source_key,title,observation,proposal,edited,revision,state,created,target_thread,prompt,synthetic,kind)
      VALUES(?,?,?,?,?,?,1,'queued',?,?,?,0,'publish')''',
      (ident, key, 'Публикация ' + text, 'Сборка и локальные тесты подтверждены контроллером.',
       REPO + '/main', text, int(time.time()), chat['threadId'], prompt))
    return f'{ident}: точная версия {text} поставлена в очередь чата MAMA для публикации в GitHub. Файлов: {len(files)}. Отдельное подтверждение приёма и результат придут в бот.'


def run(argv, cwd=None, acceptable=(0,)):
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=120)
    if proc.returncode not in acceptable:
        raise ValueError('publication-command-failed:' + argv[0])
    return proc


def publish(root, ident, thread):
    if not settings(root) or not reviews.settings(root) or reviews.settings(root)['threadId'] != thread or not reviews.ID.fullmatch(ident):
        raise ValueError('publication-disabled-or-wrong-target')
    with closing(outbox.database(root)) as db:
        reviews.prepare(db)
        row = db.execute('SELECT state,kind,target_thread,source_key FROM admin_reviews WHERE id=?', (ident,)).fetchone()
    if not row or row['state'] != 'running' or row['kind'] != 'publish' or row['target_thread'] != thread:
        raise ValueError('not-claimed-by-target-chat')
    folder = root / 'publications' / ident
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('repository') != REPO or manifest.get('branch') != 'main' or manifest.get('id') != ident:
        raise ValueError('wrong-publication-target')
    entries = manifest['files']
    fingerprint = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
    if fingerprint != manifest.get('fingerprint') or row['source_key'] != 'publication:' + manifest.get('task', '') + ':' + fingerprint or not 1 <= len(entries) <= 40:
        raise ValueError('changed-manifest')
    for name, entry in entries.items():
        source = folder / 'files' / name
        if not tasks.allowed_change(name) or source.is_symlink() or not source.resolve().is_relative_to((folder / 'files').resolve()):
            raise ValueError('unsafe-source')
        if digest(source) != entry['sha256'] or reviews.SECRET.search(source.read_text(encoding='utf-8')):
            raise ValueError('changed-snapshot-or-secret')
    checkout = folder / 'checkout'
    if checkout.exists():
        raise ValueError('existing-attempt-requires-review')
    run(['git', 'clone', '--single-branch', '--branch', 'main', 'https://github.com/' + REPO + '.git', str(checkout.resolve())])
    before = run(['git', 'rev-parse', 'HEAD'], checkout).stdout.decode().strip()
    (folder / 'remote-before.txt').write_text(before, encoding='utf-8')
    for name, entry in entries.items():
        old = run(['git', 'show', 'HEAD:' + name], checkout, (0, 128))
        previous = hashlib.sha256(old.stdout).hexdigest() if old.returncode == 0 else None
        normalized = hashlib.sha256(old.stdout.replace(b'\r\n', b'\n')).hexdigest() if old.returncode == 0 else None
        if previous != entry['base'] and not (entry.get('baseNormalized') is not None and normalized == entry['baseNormalized']):
            raise ValueError('remote-source-differs-from-task-baseline:' + name)
        dest = checkout / name
        if dest.is_symlink() or not dest.resolve().is_relative_to(checkout.resolve()):
            raise ValueError('unsafe-checkout-path')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(folder / 'files' / name, dest)
    run(['git', 'add', '--', *entries], checkout)
    identity = json.loads(run(['gh', 'api', 'user', '--jq', '{id,login}']).stdout)
    email = str(identity['id']) + '+' + identity['login'] + '@users.noreply.github.com'
    run(['git', '-c', 'user.name=' + identity['login'], '-c', 'user.email=' + email,
         'commit', '-m', 'MAMA: publish verified ' + manifest['task']], checkout)
    commit = run(['git', 'rev-parse', 'HEAD'], checkout).stdout.decode().strip()
    run(['git', '-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential',
         'push', 'origin', 'HEAD:refs/heads/main'], checkout)
    # The immutable commit must be reachable in GitHub, even if main advances again.
    remote = json.loads(run(['gh', 'api', 'repos/' + REPO + '/commits/' + commit, '--jq', '{sha}']).stdout)
    if remote.get('sha') != commit:
        raise ValueError('remote-verification-failed')
    result = {'ok': True, 'commit': commit, 'previousCommit': before, 'files': len(entries),
              'url': 'https://github.com/' + REPO + '/commit/' + commit, 'sourceOnly': True}
    (folder / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--thread', required=True)
    parser.add_argument('--id', required=True)
    args = parser.parse_args()
    print(json.dumps(publish(args.root.resolve(), args.id, args.thread), ensure_ascii=False))
