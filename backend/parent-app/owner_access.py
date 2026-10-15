"""These commands are exposed only in the owner's existing loopback panel."""
import index as app
import billing
import legal
import time
import secrets
import suggestions
from types import SimpleNamespace


def summary():
    db = app.DB()
    try:
        now = int(time.time())
        return {'plan': billing.public_config(), 'legal': legal.public(),
                'suggestions':suggestions.moderation_queue(SimpleNamespace(**vars(app)),db),
                'testers': [{'login': r[0], 'endsAt': r[1], 'answerLimit': r[2], 'active': r[1] > now}
                            for r in db.query('SELECT u.email,t.ends_at,t.answer_limit FROM mh_test_access t JOIN mh_users u ON u.id=t.user_id ORDER BY t.ends_at DESC').fetchall()],
                'requests': [{'id': r[0], 'login': r[1] or 'Аккаунт удалён', 'kind': r[2], 'text': app.unseal(r[3])['text'], 'status': r[4], 'createdAt': r[5]}
                             for r in db.query('SELECT r.id,u.email,r.kind,r.encrypted_text,r.status,r.created_at FROM mh_data_requests r LEFT JOIN mh_users u ON u.id=r.user_id ORDER BY r.created_at DESC LIMIT 200').fetchall()],
                'payments': [{'orderId': r[0], 'status': r[1], 'createdAt': r[2], 'fulfilledAt': r[3]}
                             for r in db.query('SELECT id,status,created_at,fulfilled_at FROM mh_billing_orders ORDER BY created_at DESC LIMIT 200').fetchall()]}
    finally:
        db.close()


def action(path, body):
    db = app.DB()
    try:
        if path == '/suggestion-review':
            result=suggestions.review(SimpleNamespace(**vars(app)),db,body)
            db.conn.commit()
            return result
        if path == '/test-access':
            return billing.owner_grant(db, body.get('login'), body.get('days',30), body.get('answerLimit',300), body.get('revoke',False))
        ident, status, note = body.get('id'), body.get('status'), body.get('note')
        if status not in ('review','done') or not isinstance(note,str) or not 1 <= len(note.strip()) <= 2000 or not isinstance(ident,str):
            raise ValueError('Выберите обращение, статус и внесите результат его рассмотрения.')
        if not db.query('SELECT 1 FROM mh_data_requests WHERE id=?', (ident,)).fetchone():
            raise ValueError('Обращение не найдено.')
        db.query('INSERT INTO mh_data_request_updates VALUES(?,?,?,?,?)', (secrets.token_hex(16), ident, int(time.time()), status, app.seal({'note': note.strip()})))
        db.query('UPDATE mh_data_requests SET status=? WHERE id=?', (status,ident))
        db.conn.commit()
        return {'ok':True}
    finally:
        db.close()
