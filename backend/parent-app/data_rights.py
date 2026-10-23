"""Authenticated data requests; descriptions are encrypted and stay on the owner's server."""
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import telegram_outbox
import re
import time

KINDS = ('access', 'correct', 'withdraw', 'delete', 'refund')
# Preliminary response target; weekends excluded, public holidays not yet configured.
RESPONSE_WORKING_DAYS = 10  # уточнить у юриста
OWNER_PANEL_URL = 'http://127.0.0.1:8791/'
KIND_LABELS = dict(access='Сведения об обработке', correct='Исправление данных',
                   withdraw='Отзыв согласия / прекращение обработки',
                   delete='Удаление данных', refund='Оплата / возврат')


def notify_owner(kind, ident, created_at):
    created = datetime.fromtimestamp(created_at, ZoneInfo('Europe/Moscow'))
    deadline = created.date()
    remaining = RESPONSE_WORKING_DAYS
    while remaining:
        deadline += timedelta(days=1)
        if deadline.weekday() < 5:
            remaining -= 1
    # No description, account identifier, email, or child/profile information.
    body = (f'MAMA: новое обращение\nВид: {KIND_LABELS[kind]}\nНомер: {ident}'
            f'\nДата: {created:%d.%m.%Y %H:%M} (Москва)'
            f'\nКрайний срок ответа: {deadline:%d.%m.%Y}'
            f'\n{RESPONSE_WORKING_DAYS} рабочих дней — уточнить у юриста; '
            'пока исключены только суббота и воскресенье.'
            f'\nЛокальная панель: {OWNER_PANEL_URL}')
    telegram_outbox.put(Path(os.environ['MAMA_AUTOMATION_ROOT']),
                        'data-request:' + ident, 'data-request', body, 150)


def action(app, db, user, action, data, headers, ip):
    uid = user[0]
    if action == 'data-request-list':
        return {'items': [{'id': r[0], 'kind': r[1], 'status': r[2], 'createdAt': r[3]}
                          for r in db.query('SELECT id,kind,status,created_at FROM mh_data_requests WHERE user_id=? ORDER BY created_at DESC', (uid,)).fetchall()]}
    if action == 'data-export':
        app.reauthenticate(db, user, headers, ip, data.get('password'))
        state = app.payload(db, user)['state']
        records = [app.unseal(r[0]) for r in db.query('SELECT encrypted_data FROM mh_care_records WHERE owner_id=?', (uid,)).fetchall()]
        records = [{k: v for k, v in record.items() if k not in ('undoToken', 'addedBy')} for record in records]
        authors = [{'childId':r[0],'recordId':r[1],**app.unseal(r[2])} for r in db.query('SELECT child_id,record_id,encrypted_data FROM mh_care_authorship WHERE owner_id=?',(uid,)).fetchall()]
        return {'createdAt': int(time.time()), 'email': user[1], 'state': state, 'careRecords': records, 'careAuthorship':authors,
                'note': 'Выгрузка личного кабинета. Для сведений о получателях, основаниях и сроках обработки отправьте запрос доступа.'}
    app.rate_limit(db, 'data-rights:'+uid, 10, 900)
    kind, text, ident = data.get('kind'), data.get('text'), data.get('requestId')
    if kind not in KINDS or not isinstance(text, str) or not 1 <= len(text.strip()) <= 2000 or not isinstance(ident, str) or not re.fullmatch(r'[a-zA-Z0-9-]{1,100}', ident):
        raise app.AppError(400, 'Выберите вид обращения и опишите запрос: до 2000 символов.')
    old = db.query('SELECT user_id,kind,encrypted_text FROM mh_data_requests WHERE id=?', (ident,)).fetchone()
    if old:
        if old[0] != uid or old[1] != kind or app.unseal(old[2]) != {'text': text.strip()}:
            raise app.AppError(409, 'Номер уже использован для другого обращения.')
    else:
        db.query("INSERT INTO mh_data_requests VALUES(?,?,?,?,'new',?)", (ident, uid, kind, app.seal({'text': text.strip()}), int(time.time())))
        if kind in ('withdraw','delete'):
            db.query('INSERT INTO mh_processing_restrictions VALUES(?,?,?) ON CONFLICT(user_id) DO NOTHING', (uid,kind,int(time.time())))
            db.query('UPDATE mh_health_consents SET revoked_at=? WHERE user_id=?',(int(time.time()),uid))
    # Commit the request before touching the separate notification queue.
    db.conn.commit()
    created_at = db.query('SELECT created_at FROM mh_data_requests WHERE id=?', (ident,)).fetchone()[0]
    try:
        # A retry can repair a queue failure; INSERT OR IGNORE prevents duplicate alerts.
        notify_owner(kind, ident, created_at)
    except Exception:
        logging.getLogger(__name__).warning('Data request saved; owner notification queue unavailable')
    return {'ok': True, 'id': ident, 'notice': 'Обращение сохранено. Новые обращения к ИИ приостановлены до решения вопроса об обработке данных; выгрузка и срочная помощь доступны.' if kind in ('withdraw','delete') else 'Обращение сохранено. Это запрос владельцу сервиса; данные и оплаты не изменены автоматически.'}


def require_analysis(app, db, uid):
    if db.query('SELECT 1 FROM mh_processing_restrictions WHERE user_id=?',(uid,)).fetchone():
        raise app.AppError(403,'Новые обращения к ИИ остановлены по вашему запросу об обработке данных. Обратитесь к владельцу в разделе «Данные и обращения».')
