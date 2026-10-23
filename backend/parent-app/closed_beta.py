import hashlib
import json
import os
from pathlib import Path
import secrets
import time

LIMIT_MESSAGE = 'Лимит ответов в тестировании исчерпан. Напишите владельцу через «Данные и обращения». История, трекеры и срочная помощь · 112 остаются доступны.'
BUDGET_MESSAGE = 'Ответы помощника временно на паузе. Попробуйте в следующем месяце или напишите владельцу через «Данные и обращения». История, трекеры и срочная помощь · 112 доступны всегда.'


def enabled():
    return os.environ.get('APP_CLOSED_BETA') == '1'


def limit():
    value = int(os.environ.get('APP_BETA_ANSWER_LIMIT', '10'))
    if not 0 <= value <= 10000:
        raise ValueError('Invalid beta limit')
    return value


def consume_invite(app, db, token):
    try:
        if not isinstance(token, str) or not 20 <= len(token) <= 100:
            raise ValueError()
        digest = hashlib.sha256(token.encode()).hexdigest()
        records = json.loads(Path(os.environ['APP_BETA_INVITES_FILE']).read_text(encoding='utf-8'))
        expiry = records[digest]
        if type(expiry) is not int or expiry <= int(time.time()):
            raise ValueError()
    except (KeyError, OSError, ValueError, TypeError):
        raise app.AppError(403, 'Регистрация открыта по приглашению. Попросите владельца прислать новую ссылку; если аккаунт уже есть, войдите в него.') from None
    result = db.query('INSERT INTO mh_limits(key,count,until_at) VALUES(?,1,?) ON CONFLICT(key) DO NOTHING', ('beta-invite:'+digest, expiry))
    if result.rowcount != 1:
        raise app.AppError(403, 'Приглашение уже использовано. Войдите в свой аккаунт или попросите владельца новую ссылку.')


def create_invite(path, days=7):
    path = Path(path)
    records = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    token = secrets.token_urlsafe(32)
    records[hashlib.sha256(token.encode()).hexdigest()] = int(time.time()) + days*86400
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(records, indent=2), encoding='utf-8')
    os.replace(temporary, path)
    return token


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Local owner command; no database or credentials are opened. Run serially.')
    parser.add_argument('--file', required=True)
    parser.add_argument('--days', type=int, default=7)
    args = parser.parse_args()
    if not 1 <= args.days <= 365:
        parser.error('days must be 1..365')
    print('/account?mode=register#invite='+create_invite(args.file, args.days))
