"""Parent app cloud handler. Chat replies via Cheap AI (household topics only). See DEPLOYMENT.md before publishing."""
import base64
import calendar
import hashlib
import hmac
import json
import os
import re
import secrets
import signal
import sqlite3
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse

from cryptography.fernet import Fernet

PASSWORD_ROUNDS = 600_000
SESSION_AGE = 7 * 86400
COOKIE = 'mh_session'
TOPICS = {'pregnancy', 'feeding', 'sleep', 'care', 'play', 'movement', 'wellbeing', 'dad'}

CHAT_API_URL = 'https://cheapai.io/v1/chat/completions'
# CheapAI uses OpenAI-compatible model ids. Keep it configurable so the model can
# be changed in server secrets without publishing a new frontend build.
CHAT_SIMPLE_MODEL = os.environ.get('CHEAPAI_SIMPLE_MODEL', 'gpt-5.6-luna')
CHAT_DEEP_MODEL = os.environ.get('CHEAPAI_DEEP_MODEL', 'gpt-5.6-sol')
CHAT_LIVE_ENABLED = os.environ.get('CHEAPAI_LIVE_ENABLED', '1') != '0'
CHAT_TIMEOUT = max(2, min(4, int(os.environ.get('CHEAPAI_TIMEOUT_SECONDS', '3'))))
CHAT_SYSTEM_PROMPT = (
    'Ты — тёплый ассистент по бытовым вопросам ухода за ребёнком, беременности и поддержке родителей '
    'в приложении «Мамин помощник». Отвечай по-русски, коротко и по-доброму, только на бытовые темы: '
    'сон, кормление, игры и развитие, режим дня, поддержка родителей, роль папы, уход, покупки. '
    'Никогда не ставь диагнозы, не назначай лечение и не указывай дозировки лекарств. При любых вопросах '
    'о симптомах, здоровье, лекарствах или тревожных признаках мягко направляй обратиться к врачу очно, '
    'не давая медицинских рекомендаций по существу. Если пользователь описывает угрозу жизни, судороги, '
    'потерю сознания, отравление или мысли о самоповреждении — посоветуй немедленно звонить 112.'
)
FEEDING_LABELS = {
    'unknown': 'не указано',
    'breast': 'грудное вскармливание',
    'formula': 'смесь',
    'mixed': 'смешанное кормление',
    'solids': 'есть прикорм',
}
# Fast local guard: answered without calling the external model, matches the client-side wording.
EMERGENCY_PATTERN = re.compile(
    r'не дыш|задыха|судорог|без созн|подавил|подавилась|подавился|отравил|проглотил батарейк|'
    r'сильн.*кровотеч|не хочу жить|суицид|покончить|убить себя|навредить себе|навредить ребен'
)
EMERGENCY_TEXT = (
    'Если прямо сейчас есть угроза жизни, затруднённое дыхание, судороги, потеря сознания, сильное '
    'кровотечение, отравление или риск навредить себе либо ребёнку — звоните 112. Не ждите ответа чата. '
    'Если рядом есть взрослый, которому доверяете, позовите его сейчас.'
)
DEEP_QUESTION_PATTERN = re.compile(
    r'стресс|тревог|депресс|паник|выгоран|срыв|плач|не справля|устал|страшно|'
    r'психолог|отношени|муж|жена|пап|послеродов|лактац|гв|смес|прикорм|'
    r'развит|задерж|не говорит|не ходит|не сидит|не полз|истерик|сон.*плох|'
    r'регресс|адаптац|садик|аутиз|сдвг|невролог'
)


class ChatTimeout(Exception):
    pass


def chat_profile_context(profile):
    if not profile:
        return 'Профиль не заполнен. Если вопрос зависит от возраста или срока, попроси заполнить профиль.'
    if profile['stage'] == 'pregnancy':
        anchor = date.fromisoformat(profile['weekDate'])
        current_week = min(42, profile['week'] + max(0, (date.today() - anchor).days) // 7)
        stage = f'беременность, примерно {current_week} полных недель'
        parts = ['Контекст профиля для ответа:', f'- роль пользователя: {"мама" if profile["role"] == "mom" else "папа"}', f'- этап: {stage}']
        parts.append('Учитывай срок. Если вопрос зависит от врача или обследований, не назначай их сам.')
        return '\n'.join(parts)
    birthday = date.fromisoformat(profile['birthDate'])
    now = date.today()
    anniversary_day = min(birthday.day, calendar.monthrange(now.year, now.month)[1])
    total_months = (now.year - birthday.year) * 12 + now.month - birthday.month
    if now.day < anniversary_day:
        total_months -= 1
    total_months = max(0, total_months)
    years, months = divmod(total_months, 12)
    anchor_year = birthday.year + (birthday.month - 1 + total_months) // 12
    anchor_month = (birthday.month - 1 + total_months) % 12 + 1
    anchor = date(anchor_year, anchor_month, min(birthday.day, calendar.monthrange(anchor_year, anchor_month)[1]))
    days = max(0, (now - anchor).days)
    stage = f'ребёнку {years} г. {months} мес. {days} дн.'
    parts = [
        'Контекст профиля для ответа:',
        f'- роль пользователя: {"мама" if profile["role"] == "mom" else "папа"}',
        f'- этап: {stage}',
        f'- кормление: {FEEDING_LABELS.get(profile["feeding"], "не указано")}',
    ]
    if profile.get('sleep'):
        parts.append(f'- сон: {profile["sleep"][:300]}')
    if profile.get('health') and profile.get('healthConfirmed') is True:
        parts.append(f'- подтверждённые особенности здоровья: {profile["health"][:500]}')
    if profile.get('topics'):
        parts.append(f'- выбранные темы: {", ".join(profile["topics"][:8])}')
    parts.append('Учитывай возраст ребёнка. Если действие рано или рискованно для возраста, скажи об этом.')
    return '\n'.join(parts)


def chat_history_context(state):
    messages = state.get('messages', [])[-10:]
    if not messages:
        return ''
    lines = ['Последние сообщения этого диалога:']
    for message in messages:
        role = 'родитель' if message.get('role') == 'user' else 'помощник'
        text = str(message.get('text', ''))[:700].replace('\n', ' ')
        if text:
            lines.append(f'- {role}: {text}')
    return '\n'.join(lines)


def medical_card_context(state):
    entries = state.get('medicalCard', [])[-12:]
    if not entries:
        return ''
    lines = ['Карта фактов, которые родитель уже сообщил. Не ставь по ним диагнозы и не назначай лечение:']
    for entry in entries:
        text = str(entry.get('text', ''))[:400].replace('\n', ' ')
        date_text = str(entry.get('date', ''))[:10]
        if text:
            lines.append(f'- {date_text}: {text}')
    return '\n'.join(lines)


def build_chat_context(state):
    blocks = [chat_profile_context(state.get('profile'))]
    card = medical_card_context(state)
    history = chat_history_context(state)
    if card:
        blocks.append(card)
    if history:
        blocks.append(history)
    return '\n\n'.join(blocks)


def extract_medical_card_entry(question):
    normalized = question.lower().replace('ё', 'е')
    if not re.search(r'сделал|сделали|прошли|были у|сходили|начал|начала|начали|назначил|назначили|привив|вакцин|анализ|осмотр|педиатр|невролог|узи', normalized):
        return None
    if re.search(r'как|что|почему|можно ли|нужно ли|стоит ли|когда', normalized) and not re.search(r'сделал|сделали|прошли|были у|сходили|начал|начала|начали|назначил|назначили', normalized):
        return None
    text = re.sub(r'\s+', ' ', question).strip()
    return {'id': secrets.token_hex(8), 'date': date.today().isoformat(), 'text': text[:500], 'source': 'chat'}


def choose_chat_model(question):
    normalized = question.lower().replace('ё', 'е')
    if len(normalized) > 350 or DEEP_QUESTION_PATTERN.search(normalized):
        return CHAT_DEEP_MODEL
    return CHAT_SIMPLE_MODEL


def fallback_chat_answer(question, state):
    profile = state.get('profile')
    context = chat_profile_context(profile).replace('Контекст профиля для ответа:\n', '').replace('- ', '')
    normalized = question.lower().replace('ё', 'е')
    prefix = context + '\n\n' if profile else ''
    if re.search(r'стресс|тревог|устал|не справля|плачу|поддержк|выгор', normalized):
        body = (
            'Давайте снизим нагрузку на ближайшие 10 минут.\n\n'
            '1. Сядьте с опорой, сделайте несколько спокойных выдохов и выпейте воды, если можете.\n'
            '2. Выберите одну конкретную просьбу к близкому: 20 минут с ребёнком, еда, прогулка или просто быть рядом.\n'
            '3. Уберите одну необязательную задачу на сегодня.\n'
            '4. Если появляются мысли навредить себе или ребёнку, звоните 112 и зовите взрослого рядом.'
        )
    elif re.search(r'игр|поиграть|развит|занят|игруш', normalized):
        body = (
            'Можно выбрать спокойную игру по возрасту и смотреть на реакцию ребёнка.\n\n'
            '1. Начните с короткого занятия на 5-10 минут.\n'
            '2. Используйте простые предметы: мяч, кубики, книжку, стаканчики, ткань с разной фактурой.\n'
            '3. Комментируйте действия простыми словами: “катится”, “большой”, “спрятали”, “нашли”.\n'
            '4. Если ребёнок устал, отворачивается или капризничает, завершите игру без давления.'
        )
    elif re.search(r'сон|спит|засып|просып', normalized):
        body = (
            'Для сна важнее предсказуемый ритм, чем идеальная таблица.\n\n'
            '1. Повторяйте один спокойный ритуал перед сном.\n'
            '2. Отмечайте несколько дней время сна, пробуждения и настроение ребёнка.\n'
            '3. Не меняйте всё сразу: выберите одну привычку и наблюдайте.\n'
            '4. При вопросах о дыхании, резком ухудшении или необычной сонливости нужен врач.'
        )
    elif re.search(r'смес|прикорм|корм|гв|груд', normalized):
        body = (
            'Питание лучше обсуждать через возраст, переносимость и подтверждённые особенности здоровья.\n\n'
            '1. Не выбирайте смесь или режим по рекламе и отзывам.\n'
            '2. Запишите, что именно беспокоит: объём, стул, срыгивания, сон, кожа, набор веса.\n'
            '3. Лечебные смеси и ограничения не вводят самостоятельно.\n'
            '4. Если есть сильная реакция, повторная рвота, вялость или признаки обезвоживания, обратитесь за медпомощью.'
        )
    else:
        body = (
            'Я понял вопрос. В тестовом режиме дам безопасный общий ориентир.\n\n'
            '1. Сначала учитывайте возраст или срок из профиля.\n'
            '2. Начинайте с мягких бытовых действий без лекарств, диагнозов и резких изменений режима.\n'
            '3. Если вопрос связан с симптомами, болью, анализами, лекарствами или ухудшением состояния, лучше обратиться к врачу.\n'
            '4. Можете уточнить: возраст, что уже пробовали и что именно беспокоит.'
        )
    return prefix + body + '\n\nAI-сервис сейчас не успел ответить, поэтому я показал безопасный резервный ответ для теста.'


def with_chat_deadline(call):
    previous = signal.getsignal(signal.SIGALRM)

    def timeout_handler(signum, frame):
        raise ChatTimeout()

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, CHAT_TIMEOUT)
    try:
        return call()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def chat_answer(question, context_text):
    if not CHAT_LIVE_ENABLED:
        raise ChatTimeout()
    api_key = os.environ.get('CHEAPAI_API_KEY') or os.environ.get('CHEAP_AI_API_KEY')
    if not api_key:
        raise AppError(503, 'Владелец ещё не подключил ключ чат-помощника.')
    payload = json.dumps({
        'model': choose_chat_model(question),
        'messages': [
            {'role': 'system', 'content': CHAT_SYSTEM_PROMPT},
            {'role': 'system', 'content': context_text},
            {'role': 'user', 'content': question},
        ],
        'max_tokens': 450,
        'temperature': 0.5,
    }).encode()
    request = urllib.request.Request(CHAT_API_URL, data=payload, method='POST', headers={
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + api_key,
    })

    def call_provider():
        with urllib.request.urlopen(request, timeout=CHAT_TIMEOUT) as response:
            body = json.loads(response.read().decode())
        return body['choices'][0]['message']['content'].strip()

    return with_chat_deadline(call_provider)


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


def fernet_key():
    secret = os.environ['APP_DATA_KEY'].strip()
    if not secret:
        raise AppError(503, 'Сервис хранения данных не настроен.')
    key = secret.encode()
    try:
        Fernet(key)
        return key
    except (ValueError, TypeError):
        return base64.urlsafe_b64encode(hashlib.sha256(key).digest())


def cipher():
    return Fernet(fernet_key())


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
            schema = os.environ.get('MAIN_DB_SCHEMA', '').replace('"', '')
            options = f'-c search_path="{schema}",public' if schema else None
            sslmode = os.environ.get('PGSSLMODE', 'prefer')
            self.conn = psycopg2.connect(os.environ['DATABASE_URL'], connect_timeout=8, options=options, sslmode=sslmode)

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
        # Платформа переносит Cookie в X-Cookie.
        jar.load(headers.get('cookie') or headers.get('x-cookie', ''))
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
            'preferences': {'repeat': 'never', 'push': False}, 'messages': [], 'medicalCard': []}


def normalize_state(value):
    if not isinstance(value, dict):
        return blank_state()
    state = {**blank_state(), **value}
    if not isinstance(state.get('medicalCard'), list):
        state['medicalCard'] = []
    return state


def validate_state(value):
    value = normalize_state(value)
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
    if not isinstance(value['medicalCard'],list) or len(value['medicalCard']) > 120:
        raise AppError(400, 'Карта наблюдений слишком длинная.')
    for entry in value['medicalCard']:
        if not isinstance(entry,dict) or set(entry) != {'id','date','text','source'}:
            raise AppError(400, 'Неверная запись карты.')
        if not isinstance(entry['id'],str) or not re.fullmatch(r'[a-zA-Z0-9-]{1,80}',entry['id']):
            raise AppError(400, 'Неверная запись карты.')
        try:
            date.fromisoformat(entry['date'])
        except (ValueError, TypeError):
            raise AppError(400, 'Проверьте дату записи карты.')
        if not isinstance(entry['text'],str) or not 1 <= len(entry['text']) <= 500 or entry['source'] not in ('chat','manual'):
            raise AppError(400, 'Проверьте текст записи карты.')
    return value


def payload(db, user):
    row = db.query('SELECT encrypted_data,revision FROM mh_state WHERE user_id=?', (user[0],)).fetchone()
    return {'user': {'id':user[0],'email':user[1]}, 'state':normalize_state(unseal(row[0])), 'revision':row[1]}


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
    if action == 'chat':
        question = data.get('question')
        if not isinstance(question, str) or not question.strip() or len(question) > 2000:
            raise AppError(400, 'Напишите вопрос длиной до 2000 символов.')
        rate_limit(db, 'chat:' + user[0], 30, 900)
        question = question.strip()
        if EMERGENCY_PATTERN.search(question.lower().replace('ё', 'е')):
            return {'answer': EMERGENCY_TEXT}, None
        state_row = db.query('SELECT encrypted_data FROM mh_state WHERE user_id=?', (user[0],)).fetchone()
        state = normalize_state(unseal(state_row[0])) if state_row else blank_state()
        try:
            answer = chat_answer(question, build_chat_context(state))
        except AppError:
            raise
        except (urllib.error.URLError, TimeoutError, ChatTimeout, KeyError, ValueError, IndexError):
            answer = fallback_chat_answer(question, state)
        card_entry = extract_medical_card_entry(question)
        response = {'answer': answer}
        if card_entry:
            response['cardEntry'] = card_entry
        return response, None
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
            return respond(200,{
                'ok': True,
                'pushKey': os.environ.get('VAPID_PUBLIC_KEY',''),
                'chatConfigured': bool(os.environ.get('CHEAPAI_API_KEY') or os.environ.get('CHEAP_AI_API_KEY')),
            })
        if data.get('action') == 'health':
            cipher()
            db = DB()
            db.query('SELECT 1').fetchone()
            return respond(200,{'ok':True,'database':True})
        cipher()  # Fail closed if encryption has not been configured.
        db = DB()
        ip = str(event.get('requestContext',{}).get('identity',{}).get('sourceIp','unknown'))
        result, set_cookie = handle_action(db,data.get('action'),data,headers,ip)
        db.conn.commit()
        if set_cookie:
            response_headers['Set-Cookie'] = set_cookie
            response_headers['X-Set-Cookie'] = set_cookie
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
