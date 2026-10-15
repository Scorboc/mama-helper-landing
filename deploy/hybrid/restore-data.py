"""Verify and restore a migration archive into a NEW directory only.

Run on the Russian server after the owner approves the provider. The key is
read from a protected file, never passed as a command-line value or printed.
"""
import argparse
from contextlib import closing
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sqlite3
import sys
import tarfile
from cryptography.fernet import Fernet


def restore(archive, key_file, destination=None):
    raw = Fernet(key_file.read_bytes().strip()).decrypt(archive.read_bytes())
    if len(raw) > 512_000_000:
        raise ValueError('Archive exceeds the configured migration limit')
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tar:
        members = tar.getmembers()
        names = [m.name for m in members]
        if len(set(names)) != len(names): raise ValueError('Duplicate archive paths')
        if sum(m.size for m in members) > 512_000_000: raise ValueError('Expanded archive too large')
        for member in members:
            path = PurePosixPath(member.name)
            if not member.isfile() or path.is_absolute() or '..' in path.parts or '\\' in member.name:
                raise ValueError('Unsafe archive entry')
            if member.name != 'manifest.json' and not member.name.startswith('data/'):
                raise ValueError('Unapproved archive root')
        manifest = json.loads(tar.extractfile('manifest.json').read())
        if set(names) != set(manifest['sha256']) | {'manifest.json'}:
            raise ValueError('Archive entries differ from the allowlist')
        data = {}
        databases = 0
        for name, expected in manifest['sha256'].items():
            content = tar.extractfile(name).read()
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError('File hash mismatch')
            if name.endswith(('.sqlite3', '.sqlite')):
                with closing(sqlite3.connect(':memory:')) as db:
                    db.deserialize(content)
                    if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise ValueError('Database integrity check failed')
                    table_counts = {table: db.execute('SELECT COUNT(*) FROM "' + table.replace('"', '""') + '"').fetchone()[0]
                                    for table in manifest['rowCounts'][name.removeprefix('data/')]}
                    if table_counts != manifest['rowCounts'][name.removeprefix('data/')]:
                        raise ValueError('Database row counts differ')
                databases += 1
            data[name] = content
    if destination is not None:
        if destination.exists(): raise ValueError('Refusing to overwrite an existing directory')
        if destination.parent.resolve() != destination.parent.absolute():
            raise ValueError('Destination parent must not use symlinks')
        destination.mkdir(mode=0o700)
        root = destination.resolve()
        for name, content in data.items():
            path = root / name
            if not path.resolve().is_relative_to(root): raise ValueError('Destination escape')
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            for parent in path.parents:
                if parent == root: break
                parent.chmod(0o700)
            with path.open('xb') as file: file.write(content)
            path.chmod(0o600)
    result = {'ok': True, 'verifiedDatabases': databases, 'filesVerified': len(data),
              'restored': destination is not None, 'existingFilesOverwritten': False}
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--key-file', type=Path, required=True)
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    try:
        restore(args.archive, args.key_file, args.destination)
    except Exception as exc:
        print(json.dumps({'ok': False, 'errorType': type(exc).__name__}), file=sys.stderr)
        sys.exit(1)
