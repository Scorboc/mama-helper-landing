"""Deliver encrypted queue through TLS SMTP, or explicit private local test files."""
from email.message import EmailMessage
from email.utils import formatdate
import os
from pathlib import Path
import smtplib
import ssl
import threading
import time


def send(message, ident):
    mail = EmailMessage()
    mail['From'] = os.environ.get('APP_EMAIL_FROM', 'MAMA Helper <local@example.test>')
    mail['To'] = message['to']
    mail['Subject'] = message['subject']
    mail['Date'] = formatdate(localtime=False)
    mail.set_content(message['text'])
    if os.environ.get('APP_MAIL_DRIVER') == 'local':
        if os.environ.get('APP_LOCAL') != '1':
            raise RuntimeError('Local mail is forbidden outside local mode')
        root = Path(os.environ['APP_MAIL_LOCAL_DIR'])
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = root/(ident + '.eml')
        # A retried lease writes the same private test file, rather than duplicates.
        with target.open('wb') as file:
            file.write(mail.as_bytes())
        target.chmod(0o600)
        return
    host = os.environ['APP_SMTP_HOST']
    port = int(os.environ.get('APP_SMTP_PORT', '465'))
    mode = os.environ.get('APP_SMTP_SECURITY', 'ssl')
    context = ssl.create_default_context()
    if mode == 'ssl':
        connection = smtplib.SMTP_SSL(host, port, timeout=10, context=context)
    elif mode == 'starttls':
        connection = smtplib.SMTP(host, port, timeout=10)
    else:
        raise RuntimeError('TLS SMTP configuration required')
    with connection:
        if mode == 'starttls':
            connection.ehlo(); connection.starttls(context=context); connection.ehlo()
        connection.login(os.environ['APP_SMTP_USER'], os.environ['APP_SMTP_PASSWORD'])
        connection.send_message(mail)


def deliver(app, maximum=10):
    delivered = 0
    for _ in range(maximum):
        db = app.DB()
        now = int(time.time())
        try:
            db.query("UPDATE mh_email_outbox SET status='expired',encrypted_message=? WHERE status='pending' AND expires_at<=?", (app.seal({}), now))
            db.query('DELETE FROM mh_email_tokens WHERE expires_at<=?', (now,))
            row = db.query("SELECT id,encrypted_message,attempts FROM mh_email_outbox WHERE status='pending' AND expires_at>? AND lease_until<=? ORDER BY expires_at LIMIT 1", (now, now)).fetchone()
            if not row:
                db.conn.commit(); break
            claimed = db.query("UPDATE mh_email_outbox SET lease_until=?,attempts=attempts+1 WHERE id=? AND status='pending' AND lease_until<=?", (now+120, row[0], now))
            db.conn.commit()
            if claimed.rowcount != 1:
                continue
            try:
                send(app.unseal(row[1]), row[0])
            except Exception:
                failed = row[2] + 1 >= 5
                db.query("UPDATE mh_email_outbox SET status=?,lease_until=?,encrypted_message=? WHERE id=? AND status='pending'",
                         ('failed' if failed else 'pending', now + min(300, 30 * 2**row[2]), app.seal({}) if failed else row[1], row[0]))
            else:
                db.query("UPDATE mh_email_outbox SET status='sent',delivered_at=?,encrypted_message=? WHERE id=? AND status='pending'", (int(time.time()), app.seal({}), row[0]))
                delivered += 1
            db.conn.commit()
        finally:
            db.close()
    return {'delivered': delivered}


def start(app):
    def worker():
        while True:
            try:
                deliver(app)
            except Exception:
                pass  # Never log message bodies, tokens, credentials or SMTP exceptions.
            time.sleep(5)
    thread = threading.Thread(target=worker, name='mama-mail-delivery', daemon=True)
    thread.start()
    return thread
