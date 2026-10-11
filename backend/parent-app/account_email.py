"""Single-use email actions and encrypted delivery queue; no user content in mail."""
import hashlib
import hmac
import os
import re
import secrets
import time
from urllib.parse import urlsplit


def configured():
    if os.environ.get('APP_MAIL_DRIVER') == 'local':
        return os.environ.get('APP_LOCAL') == '1' and bool(os.environ.get('APP_MAIL_LOCAL_DIR'))
    return bool(os.environ.get('APP_SMTP_HOST') and os.environ.get('APP_EMAIL_FROM') and
                os.environ.get('APP_SMTP_USER') and os.environ.get('APP_SMTP_PASSWORD'))


def enabled():
    return os.environ.get('APP_EMAIL_VERIFICATION_REQUIRED') == '1'


def status(db, uid):
    row = db.query('SELECT required,verified_at FROM mh_email_status WHERE user_id=?', (uid,)).fetchone()
    return {'emailVerified': bool(row and row[1]), 'emailVerificationRequired': bool(row and row[0] and not row[1])}


def version(row):
    return hashlib.sha256((row[2] + ':' + row[3]).encode()).hexdigest()


def ready(app):
    if not configured():
        raise app.AppError(503, 'Отправка писем пока не подключена. Личный код восстановления продолжает работать.')
    base = os.environ.get('APP_PUBLIC_URL', '').rstrip('/')
    parsed = urlsplit(base)
    local = os.environ.get('APP_LOCAL') == '1' and parsed.hostname in ('localhost', '127.0.0.1')
    if (not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ('', '/') or (parsed.scheme != 'https' and not (local and parsed.scheme == 'http'))):
        raise app.AppError(503, 'Адрес сайта для писем пока не настроен.')
    return base


def issue(app, db, row, kind):
    base = ready(app)
    token = secrets.token_urlsafe(32)
    token_hash = app.digest(token)
    now = int(time.time())
    expiry = now + (86400 if kind == 'verify' else 1800)
    mode = 'email-verify' if kind == 'verify' else 'email-reset'
    link = base + '/account?mode=' + mode + '#token=' + token
    subject = 'Подтвердите почту — MAMA Helper' if kind == 'verify' else 'Новый пароль — MAMA Helper'
    text = ('Подтвердите адрес почты для вашего аккаунта MAMA Helper. Ссылка действует 24 часа.' if kind == 'verify'
            else 'Вы запросили восстановление пароля MAMA Helper. Ссылка действует 30 минут.')
    text += '\n\n' + link + '\n\nЕсли вы не запрашивали это письмо, ничего делать не нужно. Никому не пересылайте ссылку.'
    db.query('DELETE FROM mh_email_tokens WHERE user_id=? AND kind=?', (row[0], kind))
    db.query("UPDATE mh_email_outbox SET status='superseded',encrypted_message=? WHERE user_id=? AND kind=? AND status='pending'",
             (app.seal({}), row[0], kind))
    db.query('INSERT INTO mh_email_tokens VALUES(?,?,?,?,?,?)', (token_hash, row[0], kind, version(row), expiry, now))
    db.query('INSERT INTO mh_email_outbox VALUES(?,?,?,?,?,?,?,?,?)',
             (token_hash, row[0], kind, app.seal({'to': row[1], 'subject': subject, 'text': text}), expiry, 0, 0, 0, 'pending'))


def consume(app, db, data, kind):
    token = data.get('token')
    invalid = 'Ссылка недействительна или устарела. Запросите новое письмо.'
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        raise app.AppError(400, invalid)
    token_hash = app.digest(token)
    found = db.query('SELECT user_id FROM mh_email_tokens WHERE token_hash=? AND kind=?', (token_hash, kind)).fetchone()
    if not found:
        raise app.AppError(400, invalid)
    row = app.locked_credentials(db, uid=found[0])
    # Re-read after acquiring the user lock; a parallel request may have consumed it.
    found = db.query('SELECT credential_hash,expires_at FROM mh_email_tokens WHERE token_hash=? AND kind=?', (token_hash, kind)).fetchone()
    if not row or not found or found[1] <= int(time.time()) or not hmac.compare_digest(found[0], version(row)):
        raise app.AppError(400, invalid)
    if kind == 'verify':
        db.query('INSERT INTO mh_email_status VALUES(?,0,?) ON CONFLICT(user_id) DO UPDATE SET verified_at=?',
                 (row[0], int(time.time()), int(time.time())))
        result = {'ok': True}
    else:
        password = app.checked_password(data.get('password'))
        recovery = secrets.token_urlsafe(24)
        db.query('UPDATE mh_users SET password_hash=?,recovery_hash=? WHERE id=?', (app.password_hash(password), app.digest(recovery), row[0]))
        # For a newly registered account, a reset link also proves mailbox ownership.
        db.query('UPDATE mh_email_status SET verified_at=? WHERE user_id=? AND required=1', (int(time.time()), row[0]))
        result = {'ok': True, 'recoveryCode': recovery}
    db.query('DELETE FROM mh_sessions WHERE user_id=?', (row[0],))
    db.query('DELETE FROM mh_email_tokens WHERE user_id=?', (row[0],))
    db.query("UPDATE mh_email_outbox SET status='superseded',encrypted_message=? WHERE user_id=? AND status='pending'", (app.seal({}), row[0]))
    return result, app.cookie('', True)


def public_action(app, db, action, data, ip):
    app.rate_limit(db, 'email-ip:' + app.digest(ip), 20, 3600)
    if action == 'email-request-reset':
        email = app.checked_email(data.get('email'))
        app.rate_limit(db, 'email-reset:' + app.digest(email), 3, 900)
        ready(app)  # Same service-state result for existing and unknown addresses.
        row = app.locked_credentials(db, email=email)
        eligible = db.query('SELECT required,verified_at FROM mh_email_status WHERE user_id=?', (row[0],)).fetchone() if row else None
        if row and eligible and (eligible[0] or eligible[1]):
            issue(app, db, row, 'reset')
        return {'ok': True, 'message': 'Если для адреса доступно почтовое восстановление, мы отправим письмо со ссылкой. Проверьте также папку «Спам».'}, None
    return consume(app, db, data, 'verify' if action == 'email-verify' else 'reset')


def resend(app, db, user, headers, ip):
    app.rate_limit(db, 'email-verify-ip:' + app.digest(ip), 20, 3600)
    app.rate_limit(db, 'email-verify-user:' + user[0], 3, 900)
    ready(app)
    row = app.locked_credentials(db, uid=user[0])
    app.identity(db, headers)  # Session may have been revoked while waiting for the lock.
    app.checked_email(row[1])
    current = status(db, user[0])
    if current['emailVerified']:
        return {'ok': True, 'alreadyVerified': True}, None
    db.query('INSERT INTO mh_email_status VALUES(?,0,0) ON CONFLICT(user_id) DO NOTHING', (user[0],))
    issue(app, db, row, 'verify')
    return {'ok': True, 'message': 'Письмо поставлено в очередь. Ссылка действует 24 часа.'}, None
