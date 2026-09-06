"""Parent app cloud handler. No AI calls. See DEPLOYMENT.md before publishing."""
import base64
import calendar
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from datetime import date, timedelta
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse

from cryptography.fernet import Fernet

PASSWORD_ROUNDS = 600_000
SESSION_AGE = 7 * 86400
COOKIE = 'mh_session'
TOPICS = {'pregnancy', 'feeding', 'sleep', 'care', 'play', 'movement', 'wellbeing', 'dad'}


class AppError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def password_hash(value):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', value.encode(), salt.encode(), PASSWORD_ROUNDS).hex()
    return f'{salt}${digest}'


def password_valid(value, saved):
    salt, digest = saved.split('$')
    got = hashlib.pbkdf2_hmac('sha256', value.encode(), salt.encode(), PASSWORD_ROUNDS).hex()
    return hmac.compare_digest(got, digest)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def cipher():
    return Fernet(os.environ['APP_DATA_KEY'].encode())


def seal(value):
    return cipher().encrypt(json.dumps(value, ensure_ascii=False).encode()).decode()


def unseal(value):
    return json.loads(cipher().decrypt(value.encode()))


class DB:
    def __init__(self):
        # Explicit local development only. Never silently replace PostgreSQL with SQLite.
        self.local = os.environ.get('APP_LOCAL') == '1'
        if self.local:
            self.conn = sqlite3.connect(os.environ['APP_SQLITE_PATH'], timeout=15)
            self.conn.execute('PRAGMA foreign_keys=ON')
        else:
            import psycopg2
            self.conn = psycopg2.connect(os.environ['DATABASE_URL'], connect_timeout=8, sslmode='require')
            schema = os.environ.get('MAIN_DB_SCHEMA', '')
            if schema:
                cur = self.conn.cursor()
                cur.execute('SET search_path TO "%s", public' % schema.replace('"', ''))
                self.conn.commit()

    def query(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql if self.local else sql.replace('?', '%s'), params)
        return cur

    def close(self):
        self.conn.close()


def initialize():
    db = DB()
    try:
        for statement in Path(__file__).with_name('schema.sql').read_text().split(';'):
            if statement.strip():
                db.query(statement)
        db.conn.commit()
    finally:
        db.close()


def rate_limit(db, key, maximum, seconds):
    now = int(time.time())
    cur = db.query('''INSERT INTO mh_limits(key,count,until_at) VALUES(?,1,?)
      ON CONFLICT(key) DO UPDATE SET
      count=CASE WHEN mh_limits.until_at<=? THEN 1 ELSE mh_limits.count+1 END,
      until_at=CASE WHEN mh_limits.until_at<=? THEN ? ELSE mh_limits.until_at END
      RETURNING count''', (key, now + seconds, now, now, now + seconds))
    count = cur.fetchone()[0]
    db.conn.commit()
    if count > maximum:
        raise AppError(429, 'Слишком много попыток. Попробуйте позже.')


def checked_password(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 128:
        raise AppError(400, 'Пароль должен содержать от 12 до 128 символов.')
    return value


def checked_email(value):
    if not isinstance(value, str) or len(value) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        raise AppError(400, 'Проверьте адрес электронной почты.')
    return value.strip().lower()


def cookie(value, clear=False):
    local = os.environ.get('APP_LOCAL') == '1'
    same_site = 'None' if os.environ.get('APP_COOKIE_CROSS_SITE') == '1' and not local else 'Lax'
    return f'{COOKIE}={value}; Path=/; HttpOnly; SameSite={same_site}; Max-Age={0 if clear else SESSION_AGE}' + ('' if local else '; Secure')


def new_session(db, user_id):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    db.query('DELETE FROM mh_sessions WHERE expires_at < ?', (now,))
    db.query('INSERT INTO mh_sessions VALUES(?,?,?)', (digest(token), user_id, now + SESSION_AGE))
    return token


def identity(db, headers):
    jar = SimpleCookie()
    try:
        jar.load(headers.get('cookie', ''))
        token = jar[COOKIE].value
    except (KeyError, ValueError):
        raise AppError(401, 'Войдите в аккаунт.')
    row = db.query('''SELECT u.id,u.email FROM mh_sessions s JOIN mh_users u ON u.id=s.user_id
      WHERE s.token_hash=? AND s.expires_at>?''', (digest(token), int(time.time()))).fetchone()
    if not row:
        raise AppError(401, 'Сессия завершилась. Войдите снова.')
    return row, digest(token)


def blank_state():
    return {'profile': None, 'saved': [], 'completed': [], 'events': {},
            'preferences': {'repeat': 'never', 'push': False}, 'messages': []}


def validate_state(value):
    if not isinstance(value, dict) or set(value) != set(blank_state()):
        raise AppError(400, 'Неверный формат данных.')
    p = value['profile']
    if p is not None:
        required = {'role','stage','birthDate','week','weekDate','feeding','sleep','health','healthConfirmed','topics'}
        if not isinstance(p, dict) or set(p) != required:
            raise AppError(400, 'Проверьте профиль.')
        if p['role'] not in ('mom','dad') or p['stage'] not in ('pregnancy','child'):
            raise AppError(400, 'Проверьте этап и роль.')
        today = date.today()
        if p['stage'] == 'child':
            try:
                birthday = date.fromisoformat(p['birthDate'])
                anniversary_day = min(birthday.day, calendar.monthrange(today.year,today.month)[1])
                months = (today.year-birthday.year)*12 + today.month-birthday.month - (today.day < anniversary_day)
                if birthday > today or months > 36:
                    raise ValueError()
            except (ValueError, TypeError):
                raise AppError(400, 'Укажите дату рождения ребёнка от 0 до 3 лет.')
        else:
            try:
                anchor = date.fromisoformat(p['weekDate'])
                if type(p['week']) is not int or not 1 <= p['week'] <= 42 or anchor > today or (today-anchor).days > 294:
                    raise ValueError()
            except (ValueError, TypeError):
                raise AppError(400, 'Проверьте срок беременности.')
        if p['feeding'] not in ('unknown','breast','formula','mixed','solids'):
            raise AppError(400, 'Проверьте тип кормления.')
        if type(p['healthConfirmed']) is not bool or (p['health'] and not p['healthConfirmed']):
            raise AppError(400, 'Особенности здоровья должны быть подтверждены специалистом.')
        for key, limit in [('sleep',300),('health',500)]:
            if not isinstance(p[key],str) or len(p[key]) > limit:
                raise AppError(400, 'Слишком длинное описание.')
        if not isinstance(p['topics'],list) or len(p['topics']) > 8 or any(t not in TOPICS for t in p['topics']):
            raise AppError(400, 'Проверьте темы.')
    for key in ('saved','completed'):
        if not isinstance(value[key],list) or len(value[key]) > 100 or any(not isinstance(v,str) or not re.fullmatch(r'[a-z0-9-]{1,80}',v) for v in value[key]):
            raise AppError(400, 'Неверный список материалов.')
    pref = value['preferences']
    if not isinstance(pref,dict) or set(pref) != {'repeat','push'} or pref['repeat'] not in ('never','day','week') or type(pref['push']) is not bool:
        raise AppError(400, 'Проверьте настройки напоминаний.')
    if not isinstance(value['events'],dict) or len(value['events']) > 100:
        raise AppError(400, 'Неверные события.')
    for key, v in value['events'].items():
        if not isinstance(key,str) or not re.fullmatch(r'[a-z0-9-]{1,80}',key) or not isinstance(v,dict) or set(v) != {'status','until'} or v['status'] not in ('read','hidden','later') or type(v['until']) is not int or not 0 <= v['until'] <= 4102444800000:
            raise AppError(400, 'Неверное состояние напоминания.')
    if not isinstance(value['messages'],list) or len(value['messages']) > 80:
        raise AppError(400, 'История слишком длинная. Начните новый чат.')
    for m in value['messages']:
        if not isinstance(m,dict) or set(m) != {'id','role','text'} or not isinstance(m['id'],str) or len(m['id']) > 100 or m['role'] not in ('user','assistant') or not isinstance(m['text'],str) or len(m['text']) > 2500:
            raise AppError(400, 'Неверный формат сообщения.')
    return value


def payload(db, user):
    row = db.query('SELECT encrypted_data,revision FROM mh_state WHERE user_id=?', (user[0],)).fetchone()
    return {'user': {'id':user[0],'email':user[1]}, 'state':unseal(row[0]), 'revision':row[1]}


def handle_action(db, action, data, headers, ip):
    if action in ('register','login','recover'):
        email = checked_email(data.get('email'))
        rate_limit(db, 'ip:' + digest(ip), 30, 900)
        rate_limit(db, 'account:' + digest(email), 12, 900)
        password = checked_password(data.get('password'))
        row = db.query('SELECT id,email,password_hash,recovery_hash FROM mh_users WHERE email=?', (email,)).fetchone()
        if action == 'register':
            if data.get('consent') is not True:
                raise AppError(400, 'Нужно принять условия тестирования.')
            if row:
                raise AppError(409, 'Не удалось создать аккаунт. Попробуйте войти или восстановить доступ.')
            uid, recovery = secrets.token_hex(16), secrets.token_urlsafe(24)
            db.query('INSERT INTO mh_users VALUES(?,?,?,?,?,?)', (uid,email,password_hash(password),digest(recovery),int(time.time()),'test-v1'))
            db.query('INSERT INTO mh_state VALUES(?,?,0)', (uid,seal(blank_state())))
            token = new_session(db, uid)
            return {**payload(db,(uid,email)), 'recoveryCode':recovery}, cookie(token)
        if action == 'recover':
            code = data.get('recoveryCode','')
            if not isinstance(code,str) or len(code)>100 or not row or not hmac.compare_digest(digest(code),row[3]):
                raise AppError(400, 'Проверьте почту и код восстановления.')
            recovery = secrets.token_urlsafe(24)
            db.query('UPDATE mh_users SET password_hash=?,recovery_hash=? WHERE id=?', (password_hash(password),digest(recovery),row[0]))
            db.query('DELETE FROM mh_sessions WHERE user_id=?',(row[0],))
            token = new_session(db,row[0])
            return {**payload(db,row), 'recoveryCode':recovery}, cookie(token)
        # Same password work for absent accounts, without storing a dummy account.
        valid = password_valid(password,row[2] if row else '0'*32+'$'+'0'*64)
        if not row or not valid:
            raise AppError(401, 'Неверная почта или пароль.')
        return payload(db,row), cookie(new_session(db,row[0]))
    user, token_hash = identity(db,headers)
    if action == 'session':
        return payload(db,user), None
    if action == 'logout':
        db.query('DELETE FROM mh_sessions WHERE token_hash=?',(token_hash,))
        return {'ok':True}, cookie('',True)
    if action == 'save':
        state = validate_state(data.get('state'))
        revision = data.get('revision')
        if type(revision) is not int:
            raise AppError(400,'Неизвестная версия профиля.')
        cur = db.query('UPDATE mh_state SET encrypted_data=?,revision=revision+1 WHERE user_id=? AND revision=?',(seal(state),user[0],revision))
        if cur.rowcount != 1:
            raise AppError(409,'Данные изменились в другой вкладке. Перезагрузите страницу перед сохранением.')
        return {'revision':revision+1}, None
    if action == 'delete':
        row = db.query('SELECT password_hash FROM mh_users WHERE id=?',(user[0],)).fetchone()
        if not password_valid(checked_password(data.get('password')),row[0]):
            raise AppError(401,'Неверный пароль.')
        for table in ('mh_delivery','mh_push','mh_state','mh_sessions'):
            db.query('DELETE FROM %s WHERE user_id=?' % table,(user[0],))
        db.query('DELETE FROM mh_users WHERE id=?',(user[0],))
        return {'ok':True}, cookie('',True)
    if action == 'subscribe':
        subscription = data.get('subscription')
        if not isinstance(subscription,dict) or len(json.dumps(subscription))>4000:
            raise AppError(400,'Неверная подписка.')
        url = urlparse(subscription.get('endpoint',''))
        # Only established browser push services: prevents arbitrary outbound requests.
        allowed = ('fcm.googleapis.com','updates.push.services.mozilla.com','web.push.apple.com','notify.windows.com')
        if url.scheme!='https' or url.port not in (None,443) or url.username or not url.hostname or not any(url.hostname==h or url.hostname.endswith('.'+h) for h in allowed):
            raise AppError(400,'Сервис уведомлений этого браузера пока не поддерживается.')
        keys = subscription.get('keys',{})
        if not all(isinstance(keys.get(k),str) and 10<len(keys[k])<250 for k in ('auth','p256dh')):
            raise AppError(400,'Неверные ключи подписки.')
        endpoint_hash = digest(subscription['endpoint'])
        existing = db.query('SELECT user_id FROM mh_push WHERE endpoint_hash=?',(endpoint_hash,)).fetchone()
        if existing and existing[0] != user[0]:
            raise AppError(409,'Этот браузер уже подписан в другом аккаунте. Сначала отключите там уведомления.')
        db.query('INSERT INTO mh_push VALUES(?,?,?) ON CONFLICT(endpoint_hash) DO UPDATE SET encrypted_subscription=?',(user[0],endpoint_hash,seal(subscription),seal(subscription)))
        return {'ok':True}, None
    if action == 'unsubscribe':
        db.query('DELETE FROM mh_push WHERE user_id=?',(user[0],))
        return {'ok':True}, None
    raise AppError(404,'Действие не найдено.')


def handler(event, context=None):
    headers = {k.lower():v for k,v in (event.get('headers') or {}).items()}
    origin = headers.get('origin','')
    allowed = [v.strip() for v in os.environ.get('APP_ORIGINS','').split(',') if v.strip()]
    response_headers = {'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','Vary':'Origin','X-Content-Type-Options':'nosniff'}
    if origin in allowed:
        response_headers.update({'Access-Control-Allow-Origin':origin,'Access-Control-Allow-Credentials':'true','Access-Control-Allow-Headers':'Content-Type','Access-Control-Allow-Methods':'POST, OPTIONS'})
    def respond(status, body):
        return {'statusCode':status,'headers':response_headers,'isBase64Encoded':False,'body':json.dumps(body,ensure_ascii=False)}
    if origin not in allowed:
        return respond(403,{'error':'Запрос с этого адреса сайта не разрешён.'})
    if event.get('httpMethod') == 'OPTIONS':
        return respond(204,{})
    if event.get('httpMethod') != 'POST' or headers.get('content-type','').split(';')[0] != 'application/json':
        return respond(405,{'error':'Ожидается JSON-запрос POST.'})
    db = None
    try:
        body = event.get('body') or '{}'
        if event.get('isBase64Encoded'):
            body = base64.b64decode(body).decode()
        if len(body.encode()) > 150000:
            raise AppError(413,'Слишком большой запрос.')
        data = json.loads(body)
        if not isinstance(data,dict):
            raise AppError(400,'Неверный запрос.')
        if data.get('action') == 'config':
            return respond(200,{'pushKey':os.environ.get('VAPID_PUBLIC_KEY',''), 'demo':True})
        cipher()  # Fail closed if encryption has not been configured.
        db = DB()
        ip = str(event.get('requestContext',{}).get('identity',{}).get('sourceIp','unknown'))
        result, set_cookie = handle_action(db,data.get('action'),data,headers,ip)
        db.conn.commit()
        if set_cookie:
            response_headers['Set-Cookie'] = set_cookie
        return respond(200,result)
    except AppError as exc:
        if db:
            db.conn.rollback()
        return respond(exc.status,{'error':exc.message})
    except (json.JSONDecodeError,UnicodeError,ValueError,TypeError):
        if db:
            db.conn.rollback()
        return respond(400,{'error':'Проверьте заполненные поля.'})
    except Exception:
        if db:
            db.conn.rollback()
        # Never return/log credentials, health data or database exception messages.
        return respond(503,{'error':'Сервис временно недоступен. Данные не сохранены. Попробуйте позже.'})
    finally:
        if db:
            db.close()


if __name__ == '__main__':
    initialize()