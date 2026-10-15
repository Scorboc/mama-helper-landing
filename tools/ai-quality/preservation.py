"""Record hashes only. Never log account rows or credentials."""
import hashlib
import json
import sqlite3
from pathlib import Path


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def database_fingerprint(path: Path) -> dict:
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    try:
        connection.execute('BEGIN')
        names = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        tables = {}
        for name in names:
            quoted = '"' + name.replace('"', '""') + '"'
            rows = connection.execute('SELECT * FROM ' + quoted).fetchall()
            encoded = sorted(repr(row).encode('utf-8') for row in rows)
            digest = hashlib.sha256()
            for row in encoded:
                digest.update(len(row).to_bytes(8, 'big'))
                digest.update(row)
            tables[name] = {'rows': len(rows), 'sha256': digest.hexdigest()}
        return {'tables': tables}
    finally:
        connection.close()


def snapshot(root: Path) -> dict:
    app = root.parents[1]
    workspace = app.parent
    files = {}
    excluded = {'__pycache__', 'node_modules', 'output', 'outputs', '.venv', 'dist'}
    for directory in ('src', 'backend', 'scripts', 'public', 'db_migrations'):
        for path in (app / directory).rglob('*'):
            if path.is_file() and not any(part in excluded for part in path.relative_to(app).parts):
                files[str(path.relative_to(workspace))] = file_hash(path)
    for relative in ('package.json', 'package-lock.json', 'AGENTS.md', 'CONTENT_RULES.md'):
        path = app / relative
        if path.is_file():
            files[str(path.relative_to(workspace))] = file_hash(path)
    databases = {}
    for name in ('accounts.sqlite3', 'ai-budget.sqlite3', 'operations.sqlite3'):
        path = workspace / 'private' / 'local-runtime' / name
        if path.is_file():
            databases[name] = database_fingerprint(path)
    return {'files': files, 'databases': databases}


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    out = root / 'output'
    out.mkdir(exist_ok=True)
    result = snapshot(root)
    (out / 'preservation-before.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'protected_files': len(result['files']), 'databases': len(result['databases'])}))
