"""Separate public static assets from an encrypted, local-only migration archive.

No upload, service restart, purchase, or live AI request is performed here.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import closing
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from cryptography.fernet import Fernet

APP = Path(__file__).resolve().parents[2]
ROOT = APP.parent
LOCAL = ROOT / 'private/local-runtime'
N8N = ROOT / 'private/n8n'
DATABASES = {
    'local-runtime/accounts.sqlite3': LOCAL / 'accounts.sqlite3',
    'local-runtime/operations.sqlite3': LOCAL / 'operations.sqlite3',
    'local-runtime/ai-budget.sqlite3': LOCAL / 'ai-budget.sqlite3',
    'local-runtime/feedback-review/review.sqlite3': LOCAL / 'feedback-review/review.sqlite3',
    'n8n/state/.n8n/database.sqlite': N8N / 'state/.n8n/database.sqlite',
    'n8n/automation-journal.sqlite': N8N / 'automation-journal.sqlite',
}
STATIC_SUFFIXES = {'.html', '.js', '.css', '.json', '.svg', '.png', '.jpg', '.jpeg', '.webp',
                   '.gif', '.ico', '.woff', '.woff2', '.ttf', '.otf', '.webmanifest', '.txt', '.pdf'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def table_rows(db):
    result = {}
    for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        rows = []
        for row in db.execute('SELECT * FROM "' + name.replace('"', '""') + '"'):
            encoded = json.dumps([v.hex() if isinstance(v, bytes) else v for v in row],
                                 ensure_ascii=False, separators=(',', ':')).encode()
            rows.append(sha(encoded))
        result[name] = sorted(rows)
    return result


def snapshot(path):
    # WAL snapshots need an on-disk destination before converting their journal
    # header to DELETE. Serializing an in-memory WAL copy cannot restore reliably.
    private = (ROOT / 'private').resolve()
    with tempfile.TemporaryDirectory(prefix='hybrid-snapshot-', dir=private) as temporary:
        if Path(temporary).resolve().parent != private:
            raise RuntimeError('Snapshot directory escaped the private workspace')
        target = Path(temporary) / 'snapshot.sqlite3'
        with closing(sqlite3.connect('file:' + path.as_posix() + '?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(target)) as dest:
                source.backup(dest)
                dest.execute('PRAGMA journal_mode=DELETE')
                if dest.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('Database integrity check failed')
                rows = table_rows(dest)
        return target.read_bytes(), rows


def append(tar, name, data):
    info = tarfile.TarInfo(name)
    info.size, info.mode, info.mtime = len(data), 0o600, int(time.time())
    tar.addfile(info, io.BytesIO(data))


def backup():
    stamp = time.strftime('%Y%m%d-%H%M%S')
    destination = ROOT / 'private' / ('hybrid-migration-' + stamp)
    destination.mkdir(mode=0o700, exist_ok=False)
    buffer = io.BytesIO()
    evidence = {}
    files = {}
    with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
        for name, path in DATABASES.items():
            if not path.exists():
                raise RuntimeError('Required migration database is missing: ' + name)
            data, rows = snapshot(path)
            append(tar, 'data/' + name, data)
            files['data/' + name] = sha(data)
            evidence[name] = rows
        configs = {
            'local-runtime/settings.json': LOCAL / 'settings.json',
            'local-runtime/ai-policy.json': LOCAL / 'ai-policy.json',
            'n8n/settings.json': N8N / 'settings.json',
            'n8n/backup.key': N8N / 'backup.key',
        }
        for name in ('ai-settings.enc', 'push-settings.enc', 'mail-settings.enc',
                     'server-settings-recovered-20261003.enc'):
            if (LOCAL / name).exists():
                configs['local-runtime/' + name] = LOCAL / name
        # Local app configuration and n8n credentials keep their original keys.
        for name, path in configs.items():
            data = path.read_bytes()
            append(tar, 'data/' + name, data)
            files['data/' + name] = sha(data)
        for directory, prefix in ((LOCAL / 'operations', 'data/local-runtime/operations'),
                                  (LOCAL / 'feedback-review', 'data/local-runtime/feedback-review'),
                                  (N8N / 'state/.n8n', 'data/n8n/state/.n8n')):
            if not directory.exists():
                continue
            for path in sorted(directory.rglob('*')):
                if not path.is_file() or path.is_symlink():
                    continue
                relative = path.relative_to(directory)
                if any(p in ('backups', 'node_modules', '.git', '__pycache__') for p in relative.parts):
                    continue
                if path.suffix in ('.sqlite', '.sqlite3', '.db', '.pyc', '.log') or path.name.endswith(('-wal', '-shm')):
                    continue
                name = prefix + '/' + relative.as_posix()
                data = path.read_bytes()
                append(tar, name, data)
                files[name] = sha(data)
        manifest = {'createdAt': stamp, 'sha256': files,
                    'rowCounts': {name: {t: len(r) for t, r in tables.items()} for name, tables in evidence.items()},
                    'original50QuestionTestSha256': sha((APP / 'scripts/live-qa-50.mjs').read_bytes()),
                    'destinationRestriction': 'Russian data server only; never Cloudflare or GitHub'}
        append(tar, 'manifest.json', json.dumps(manifest, indent=2).encode())
    key = (N8N / 'backup.key').read_bytes().strip()
    sealed = Fernet(key).encrypt(buffer.getvalue())
    archive = destination / 'data.tar.gz.enc'
    archive.write_bytes(sealed)
    if Fernet(key).decrypt(sealed) != buffer.getvalue():
        raise RuntimeError('Encrypted archive verification failed')
    # Verify actual restored SQLite bytes, not just the encryption operation.
    with tarfile.open(fileobj=io.BytesIO(Fernet(key).decrypt(archive.read_bytes())), mode='r:gz') as tar:
        for name, original in evidence.items():
            data = tar.extractfile('data/' + name).read()
            if sha(data) != files['data/' + name]:
                raise RuntimeError('Restored file hash mismatch')
            with closing(sqlite3.connect(':memory:')) as db:
                db.deserialize(data)
                if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or table_rows(db) != original:
                    raise RuntimeError('Restored database contents mismatch')
    (destination / 'row-evidence.json').write_text(json.dumps(evidence), encoding='utf-8')
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    result = {'archive': str(archive), 'encrypted': True, 'restorationVerified': True,
              'databases': len(evidence), 'sha256': sha(sealed)}
    (destination / 'status.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


def verify_preservation(folder):
    before = json.loads((folder / 'row-evidence.json').read_text(encoding='utf-8'))
    # n8n execution and monitoring journals can change while services are running.
    # Original account/profile/dialog rows must remain byte-for-byte present.
    _, current = snapshot(LOCAL / 'accounts.sqlite3')
    preserved = all(not (Counter(rows) - Counter(current.get(table, [])))
                    for table, rows in before['local-runtime/accounts.sqlite3'].items())
    test_hash = sha((APP / 'scripts/live-qa-50.mjs').read_bytes())
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    result = {'accountRowsPreserved': preserved,
              'original50QuestionTestPreserved': test_hash == manifest['original50QuestionTestSha256']}
    (folder / 'preservation-final.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    if not all(result.values()):
        raise RuntimeError('Preservation check failed')
    print(json.dumps(result))


def domain_origins(domain, test=False):
    domain = domain.lower().strip().encode('idna').decode()
    if not re.fullmatch(r'(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', domain):
        raise ValueError('Use an owned base domain without URL, port, or path')
    if not test and domain.endswith(('.test', '.invalid', '.example', '.localhost')):
        raise ValueError('Reserved test domain cannot be published')
    return 'https://app.' + domain, 'https://api.' + domain


def known_secrets():
    config = json.loads((LOCAL / 'settings.json').read_text(encoding='utf-8'))
    secrets = [config['data_key']]
    for name in ('ai-settings.enc', 'push-settings.enc', 'mail-settings.enc'):
        path = LOCAL / name
        if path.exists():
            settings = json.loads(Fernet(config['data_key']).decrypt(path.read_bytes()))
            secrets.extend(str(v) for k, v in settings.items()
                           if any(word in k for word in ('KEY', 'PASSWORD', 'TOKEN', 'SECRET')) and 'PUBLIC' not in k)
    settings = json.loads((N8N / 'settings.json').read_text(encoding='utf-8'))
    secrets.extend(str(v) for v in settings.values())
    return [v.encode() for v in secrets if len(v) >= 12]


def audit_static(directory):
    allowed_root = set(p.name for p in (APP / 'public').iterdir() if p.is_file()) | {'index.html', '_headers', '_redirects', 'api-error.json'}
    secrets = known_secrets()
    result = []
    for path in sorted(directory.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(directory)
        if path.is_symlink() or len(rel.parts) > 1 and rel.parts[0] not in ('assets', 'fonts'):
            raise RuntimeError('Unapproved static directory')
        if len(rel.parts) == 1 and rel.name not in allowed_root:
            raise RuntimeError('Unapproved root static asset')
        if path.name not in ('_headers', '_redirects') and path.suffix not in STATIC_SUFFIXES:
            raise RuntimeError('Unapproved static file type')
        data = path.read_bytes()
        if any(value in data for value in secrets):
            raise RuntimeError('Private credential found in static output; do not upload')
        if len(data) > 25_000_000:
            raise RuntimeError('Cloudflare Pages file size exceeded')
        result.append({'path': rel.as_posix(), 'bytes': len(data), 'sha256': sha(data)})
    if len(result) > 1000:
        raise RuntimeError('Direct upload file count exceeded')
    return result


def source_package(destination):
    if destination.exists():
        raise RuntimeError('Use a new source package path')
    destination.parent.mkdir(parents=True, exist_ok=True)
    secrets = known_secrets()
    allow = {'.py', '.sql', '.html', '.js', '.mjs', '.ts', '.tsx', '.css', '.json', '.md',
             '.txt', '.template', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.ico',
             '.woff', '.woff2', '.ttf', '.otf', '.webmanifest', '.pdf', '.cjs', '.lock'}
    roots = [APP / name for name in ('backend', 'docs', 'automation', 'scripts', 'src', 'public', 'deploy')]
    paths = [p for p in APP.iterdir() if p.is_file() and p.suffix in allow]
    for root in roots:
        paths.extend(p for p in root.rglob('*') if p.is_file())
    manifest = {}
    with tarfile.open(destination, 'w:gz') as tar:
        for path in sorted(paths):
            relative = path.relative_to(APP)
            if path.is_symlink() or any(p in ('node_modules', '__pycache__', '.git', 'outputs', 'private') for p in relative.parts):
                continue
            if path.name.startswith('.env') or path.suffix not in allow:
                continue
            data = path.read_bytes()
            if any(value in data for value in secrets):
                raise RuntimeError('Private credential found in application source package')
            name = 'app/' + relative.as_posix()
            append(tar, name, data)
            manifest[name] = sha(data)
        append(tar, 'source-manifest.json', json.dumps(manifest, indent=2).encode())
    result = {'sourcePackage': str(destination), 'files': len(manifest), 'bytes': destination.stat().st_size,
              'secretsFound': False, 'intendedDestination': 'Russian server, not Cloudflare'}
    print(json.dumps(result))


def stage(domain, node, destination, test):
    frontend, api = domain_origins(domain, test)
    if destination.exists():
        raise RuntimeError('Use a new output directory; existing release is preserved')
    if any(p.name not in ('.env.example', '.env.local.example') for p in APP.glob('.env*')):
        raise RuntimeError('Review local Vite environment files before staging public assets')
    destination.mkdir(parents=True)
    static = destination / 'public'
    env = {k: v for k, v in os.environ.items() if not k.startswith('VITE_')}
    completed = subprocess.run([str(node), str(APP / 'node_modules/vite/bin/vite.js'), 'build',
                                '--outDir', str(static)], cwd=APP, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
    (destination / 'build.log').write_text(completed.stdout, encoding='utf-8')
    if completed.returncode:
        raise RuntimeError('Frontend build failed; inspect local build.log')
    (static / 'app-config.json').write_text(json.dumps({'apiUrl': api + '/api'}) + '\n', encoding='utf-8')
    index = static / 'index.html'
    text = index.read_text(encoding='utf-8')
    text = re.sub(r'https://mama-helper-158-160-188-235\.sslip\.io', frontend, text)
    index.write_text(text, encoding='utf-8')
    # SPA routing is native Pages behavior when no top-level 404.html is present.
    # Do not rewrite asset/config files to HTML. Reserved API paths are denied.
    (static / 'api-error.json').write_text('{"error":"Use the configured Russian API endpoint"}\n', encoding='utf-8')
    (static / '_redirects').write_text('/api /api-error.json 200\n/api/* /api-error.json 200\n/payment-notification /api-error.json 200\n', encoding='utf-8')
    headers = (Path(__file__).parent / 'pages-headers.template').read_text(encoding='utf-8').replace('@API_ORIGIN@', api)
    (static / '_headers').write_text(headers, encoding='utf-8')
    files = audit_static(static)
    result = {'frontendOrigin': frontend, 'apiOrigin': api, 'files': len(files),
              'bytes': sum(f['bytes'] for f in files), 'secretsFound': False,
              'testDomain': test, 'published': False, 'apiVerified': False,
              'privateDataIncluded': False, 'workerFunctionsIncluded': False}
    (destination / 'static-manifest.json').write_text(json.dumps(files, indent=2), encoding='utf-8')
    (destination / 'status.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    if not test:
        with zipfile.ZipFile(destination / 'cloudflare-static.zip', 'w', zipfile.ZIP_DEFLATED) as zip:
            for path in static.rglob('*'):
                if path.is_file():
                    zip.write(path, path.relative_to(static).as_posix())
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('backup')
    source = commands.add_parser('source')
    source.add_argument('--output', required=True, type=Path)
    preservation = commands.add_parser('verify-preservation')
    preservation.add_argument('folder', type=Path)
    build = commands.add_parser('stage')
    build.add_argument('--domain', required=True)
    build.add_argument('--node', required=True, type=Path)
    build.add_argument('--output', required=True, type=Path)
    build.add_argument('--test', action='store_true')
    arguments = parser.parse_args()
    try:
        if arguments.command == 'backup': backup()
        elif arguments.command == 'source': source_package(arguments.output.resolve())
        elif arguments.command == 'verify-preservation': verify_preservation(arguments.folder)
        else: stage(arguments.domain, arguments.node, arguments.output.resolve(), arguments.test)
    except Exception as exc:
        # Exception messages are controlled here; never echo decrypted credentials.
        print(json.dumps({'ok': False, 'errorType': type(exc).__name__}), file=sys.stderr)
        sys.exit(1)
