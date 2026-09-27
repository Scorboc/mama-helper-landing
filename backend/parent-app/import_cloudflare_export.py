"""One-shot Cloudflare Durable Object export importer. Run offline on the target host."""
import json
import os
import re
import sys
import time
from pathlib import Path

import index as app


def import_export(path):
    document = json.loads(Path(path).read_text(encoding='utf-8'))
    entries = document.get('entries') if isinstance(document, dict) else None
    if not isinstance(entries, list):
        raise ValueError('unexpected export format')
    records = {}
    for item in entries:
        if not isinstance(item, list) or len(item) != 2 or not isinstance(item[0], str):
            raise ValueError('malformed export entry')
        key, value = item
        if key in records:
            raise ValueError('duplicate export entry')
        records[key] = value

    users = {}
    for key, value in records.items():
        if not key.startswith('u:'):
            continue
        uid = key[2:]
        if not isinstance(value, dict) or value.get('id') != uid:
            raise ValueError('user record does not match its key')
        email = value.get('email')
        if not isinstance(email, str) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise ValueError('invalid user record')
        state = value.get('state')
        if not isinstance(state, dict) or not {'profile','saved','completed','events','preferences','messages','medicalCard'}.issubset(state):
            raise ValueError('incomplete user state')
        if len(json.dumps(state, ensure_ascii=False)) > 500_000:
            raise ValueError('user state exceeds import size limit')
        email_key = records.get('e:' + email)
        if email_key not in (None, uid):
            raise ValueError('email index does not match user record')
        users[uid] = value
    if not users:
        raise ValueError('export contains no users')

    now = int(time.time())
    sessions = []
    for key, value in records.items():
        if not key.startswith('s:'):
            continue
        token = key[2:]
        if not re.fullmatch(r'[a-f0-9]{64}', token) or not isinstance(value, dict):
            raise ValueError('invalid session record')
        uid = value.get('uid')
        expires = value.get('expires')
        if uid not in users or not isinstance(expires, (int, float)):
            continue
        expires = int(expires / 1000) if expires > 10_000_000_000 else int(expires)
        if expires > now:
            sessions.append((app.digest(token), uid, expires))

    app.initialize()
    db = app.DB()
    try:
        existing = db.query('SELECT COUNT(*) FROM mh_users').fetchone()[0]
        if existing:
            raise RuntimeError('target already contains accounts; refusing to overwrite')
        for uid, user in users.items():
            match = re.fullmatch(r'test-account-([1-6])', uid)
            imported_password = app.password_hash(match.group(1)) if match else 'cf-locked$recover-with-existing-code'
            recovery_hash = user.get('recovery') if isinstance(user.get('recovery'), str) else ''
            if recovery_hash and not re.fullmatch(r'[a-f0-9]{64}', recovery_hash):
                raise ValueError('invalid recovery record')
            db.query('INSERT INTO mh_users VALUES(?,?,?,?,?,?)',
                     (uid, user['email'].strip().lower(), imported_password, recovery_hash,
                      now, 'cloudflare-import-v1'))
            db.query('INSERT INTO mh_state VALUES(?,?,?)',
                     (uid, app.seal(user['state']), int(user.get('revision') or 0)))
        for token_hash, uid, expires in sessions:
            db.query('INSERT INTO mh_sessions VALUES(?,?,?)', (token_hash, uid, expires))
        for key, value in records.items():
            if key.startswith('ai-quota-v1:test-account-'):
                uid = key.removeprefix('ai-quota-v1:')
                if uid in users and re.fullmatch(r'test-account-[2-6]', uid) and type(value) is int and 0 <= value <= 70:
                    db.query('INSERT INTO mh_limits(key,count,until_at) VALUES(?,?,?)',
                             ('ai-quota:'+uid, value, 4102444800))
        db.conn.commit()
        return {'users': len(users), 'sessions': len(sessions)}
    except Exception:
        db.conn.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: import_cloudflare_export.py EXPORT_FILE')
    result = import_export(sys.argv[1])
    print(f"Imported {result['users']} accounts and {result['sessions']} active sessions; user data encrypted.")
