"""Server-authorized monthly access. Free testers are assigned only by the owner."""
import base64
import calendar
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
import json
import os
import re
import secrets
import time
import urllib.request
from urllib.parse import urlparse
import legal
import closed_beta

PRICE_RUB = 480
ANSWER_LIMIT = 300
PLAN = 'family-month-480-300-v1'


def enabled():
    return os.environ.get('APP_BILLING_MODE', 'paid') == 'paid'


def next_month(stamp):
    dt = datetime.fromtimestamp(stamp, ZoneInfo('Europe/Moscow'))
    year, month = (dt.year+1, 1) if dt.month == 12 else (dt.year, dt.month+1)
    return int(dt.replace(year=year, month=month, day=min(dt.day, calendar.monthrange(year, month)[1])).timestamp())


def payment_ready():
    if closed_beta.enabled():
        return False
    url = urlparse(os.environ.get('APP_PUBLIC_URL', ''))
    return bool(os.environ.get('YOOKASSA_SHOP_ID') and os.environ.get('YOOKASSA_SECRET_KEY')
                and url.scheme == 'https' and url.hostname and legal.public()['documentsReady']
                and os.environ.get('APP_PAYMENTS_ENABLED') == '1')


def public_config():
    return {'closedBeta': closed_beta.enabled(), 'betaAnswerLimit': closed_beta.limit() if closed_beta.enabled() else None, 'enabled': enabled(), 'priceRub': PRICE_RUB, 'answerLimit': ANSWER_LIMIT,
            'plan': PLAN, 'period': 'calendar-month', 'autoRenew': False,
            'paymentConfigured': payment_ready()}


def access(db, uid, now=None):
    now = int(time.time()) if now is None else now
    if closed_beta.enabled():
        return {'mode': 'test', 'periodKey': 'closed-beta-v1', 'answerLimit': closed_beta.limit(), 'endsAt': None}
    paid = db.query('SELECT period_key,answer_limit,ends_at FROM mh_paid_access WHERE user_id=? AND starts_at<=? AND ends_at>?', (uid, now, now)).fetchone()
    if paid:
        return {'mode': 'paid', 'periodKey': paid[0], 'answerLimit': int(paid[1]), 'endsAt': paid[2]}
    free = db.query('SELECT period_key,answer_limit,ends_at FROM mh_test_access WHERE user_id=? AND starts_at<=? AND ends_at>?', (uid, now, now)).fetchone()
    if free:
        return {'mode': 'test', 'periodKey': free[0], 'answerLimit': int(free[1]), 'endsAt': free[2]}
    return {'mode': 'none' if enabled() else 'legacy', 'answerLimit': 0, 'endsAt': None}


def status(db, uid):
    return {**public_config(), **access(db, uid)}


def owner_grant(db, login, days=30, limit=ANSWER_LIMIT, revoke=False):
    if not isinstance(login, str) or not login.strip() or type(days) is not int or not 1 <= days <= 365 or type(limit) is not int or not 0 <= limit <= 10000 or type(revoke) is not bool:
        raise ValueError('Укажите логин, срок от 1 до 365 дней и лимит ответов.')
    user = db.query('SELECT id FROM mh_users WHERE email=?', (login.strip().lower(),)).fetchone()
    if not user:
        raise ValueError('Аккаунт с этим логином не найден.')
    now, uid = int(time.time()), user[0]
    old = db.query('SELECT period_key,starts_at,ends_at FROM mh_test_access WHERE user_id=?', (uid,)).fetchone()
    period = old[0] if old and old[2] > now else 'test-'+secrets.token_hex(12)
    start = old[1] if old and old[2] > now else now
    end = now if revoke else now+days*86400
    db.query('INSERT INTO mh_test_access VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET period_key=excluded.period_key,starts_at=excluded.starts_at,ends_at=excluded.ends_at,answer_limit=excluded.answer_limit', (uid, period, start, end, limit))
    db.query('INSERT INTO mh_access_audit VALUES(?,?,?,?,?)', (secrets.token_hex(12), uid, now, 'revoke-test' if revoke else 'grant-test', json.dumps({'days': days, 'answerLimit': limit, 'period': period})))
    db.conn.commit()
    return {'ok': True, 'endsAt': end, 'answerLimit': limit, 'revoked': revoke}


def vendor(method, path, body=None, key=None):
    # Fixed provider host, verified HTTPS. No user-controlled network destination.
    credentials = base64.b64encode((os.environ['YOOKASSA_SHOP_ID']+':'+os.environ['YOOKASSA_SECRET_KEY']).encode()).decode()
    headers = {'Authorization': 'Basic '+credentials, 'Content-Type': 'application/json'}
    if key:
        headers['Idempotence-Key'] = key
    req = urllib.request.Request('https://api.yookassa.ru/v3/'+path,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read(300000))


def apply_payment(app, db, order, payment):
    oid, uid, pid, _, _, _, _, period = order
    amount = payment.get('amount', {})
    if (payment.get('id') != pid or amount.get('currency') != 'RUB'
        or Decimal(str(amount.get('value', '-1'))) != PRICE_RUB
        or payment.get('metadata', {}).get('mama_order') != oid
        or bool(payment.get('test')) != (os.environ.get('APP_PAYMENTS_TEST') == '1')):
        raise app.AppError(409, 'Платёж не совпадает с заказом. Обратитесь в поддержку.')
    if payment.get('status') == 'succeeded' and payment.get('paid') is True:
        # Credential/state lock serializes fulfillment against account deletion.
        if uid:
            app.locked_credentials(db, uid=uid)
        changed = db.query("UPDATE mh_billing_orders SET status='succeeded' WHERE id=? AND fulfilled_at=0", (oid,))
        if changed.rowcount and uid and db.query('SELECT 1 FROM mh_users WHERE id=?', (uid,)).fetchone():
            now = int(time.time())
            previous = db.query('SELECT period_key,starts_at,ends_at,answer_limit FROM mh_paid_access WHERE user_id=?', (uid,)).fetchone()
            if previous and previous[2] > now:
                raise app.AppError(409, 'Подписка уже активна. Новый платёж требует проверки поддержки.')
            db.query('INSERT INTO mh_paid_access VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET period_key=excluded.period_key,starts_at=excluded.starts_at,ends_at=excluded.ends_at,answer_limit=excluded.answer_limit', (uid, period, now, next_month(now), ANSWER_LIMIT))
            db.query('UPDATE mh_billing_orders SET fulfilled_at=? WHERE id=?', (now, oid))
        elif changed.rowcount:
            db.query("UPDATE mh_billing_orders SET status='support-required' WHERE id=?", (oid,))
    elif payment.get('status') == 'canceled':
        db.query("UPDATE mh_billing_orders SET status='canceled' WHERE id=? AND fulfilled_at=0", (oid,))


def order_row(db, oid, uid=None):
    return db.query('SELECT id,user_id,payment_id,status,created_at,fulfilled_at,confirmation_url,period_key FROM mh_billing_orders WHERE id=?'+(' AND user_id=?' if uid is not None else ''), (oid, uid) if uid is not None else (oid,)).fetchone()


def sync(app, db, oid, uid=None):
    order = order_row(db, oid, uid)
    if not order:
        raise app.AppError(404, 'Заказ не найден.')
    if order[2] and order[3] not in ('canceled', 'support-required'):
        try:
            apply_payment(app, db, order, vendor('GET', 'payments/'+order[2]))
        except app.AppError:
            raise
        except Exception:
            raise app.AppError(503, 'Не удалось проверить оплату. Повторите проверку позже; повторно платить не нужно.') from None
    fresh = order_row(db, oid, uid)
    return {'orderId': oid, 'status': fresh[3], 'confirmationUrl': fresh[6] or None}


def action(app, db, user, action, data):
    uid = user[0]
    if action == 'billing-status':
        return status(db, uid)
    if closed_beta.enabled():
        raise app.AppError(409, 'Оплата откроется позже. По вопросам тестирования напишите владельцу через «Данные и обращения».')
    app.rate_limit(db, 'billing:'+uid, 12, 900)
    if action == 'billing-check':
        oid = data.get('orderId', '')
        if not isinstance(oid, str) or not re.fullmatch(r'[a-f0-9]{32}', oid):
            raise app.AppError(400, 'Неверный номер заказа.')
        return {**sync(app, db, oid, uid), 'billing': status(db, uid)}
    if not payment_ready():
        raise app.AppError(503, 'Оплата ещё не подключена. Деньги не списываются.')
    legal.require_health_authorization(app,db,uid)
    if data.get('offerAccepted') is not True or data.get('offerVersion') != legal.OFFER_VERSION:
        raise app.AppError(400, 'Примите действующую оферту перед оплатой.')
    app.locked_credentials(db, uid=uid)
    if access(db, uid)['mode'] in ('paid', 'test'):
        raise app.AppError(409, 'У вас уже есть действующий доступ. Новая оплата пока не нужна.')
    old = db.query("SELECT id FROM mh_billing_orders WHERE user_id=? AND status IN ('creating','pending') ORDER BY created_at DESC LIMIT 1", (uid,)).fetchone()
    if old:
        row = order_row(db, old[0], uid)
    else:
        oid = secrets.token_hex(16)
        db.query("INSERT INTO mh_billing_orders VALUES(?,?,NULL,'creating',?,0,'',?,?)", (oid, uid, int(time.time()), 'paid-'+oid, legal.OFFER_VERSION))
        legal.receipt(app, db, uid, 'offer', legal.OFFER_VERSION)
        row = order_row(db, oid, uid)
    # Persist the idempotency key before network access; retries recover the same payment.
    db.conn.commit()
    if not row[2]:
        try:
            payment = vendor('POST', 'payments', {
                'amount': {'value': '480.00', 'currency': 'RUB'}, 'capture': True,
                'confirmation': {'type': 'redirect', 'return_url': os.environ['APP_PUBLIC_URL'].rstrip('/')+'/billing?order='+row[0]},
                'description': 'Мамин помощник: доступ на один календарный месяц',
                'metadata': {'mama_order': row[0]}, 'save_payment_method': False,
            }, row[0])
            pid = payment.get('id', '')
            url = payment.get('confirmation', {}).get('confirmation_url', '')
            parsed = urlparse(url)
            if not re.fullmatch(r'[a-zA-Z0-9-]{10,80}', pid) or parsed.scheme != 'https' or parsed.hostname != 'yoomoney.ru' or parsed.username or parsed.password:
                raise ValueError()
            db.query("UPDATE mh_billing_orders SET payment_id=?,status='pending',confirmation_url=? WHERE id=? AND payment_id IS NULL", (pid, url, row[0]))
            db.conn.commit()
        except Exception:
            raise app.AppError(503, 'Не удалось открыть оплату. Повторите позже; заказ сохранён, повторного счёта не будет.') from None
    return {**sync(app, db, row[0], uid), 'billing': status(db, uid)}


def webhook(app, db, data):
    # Never trust webhook amount/status; request the object again with merchant credentials.
    if not payment_ready():
        raise app.AppError(503, 'Приём платежей отключён.')
    pid = data.get('object', {}).get('id', '') if isinstance(data.get('object'), dict) else ''
    if not isinstance(pid, str) or not re.fullmatch(r'[a-zA-Z0-9-]{10,80}', pid):
        raise app.AppError(400, 'Неверное уведомление.')
    order = db.query('SELECT id FROM mh_billing_orders WHERE payment_id=?', (pid,)).fetchone()
    if order:
        sync(app, db, order[0])
    return {'ok': True}
