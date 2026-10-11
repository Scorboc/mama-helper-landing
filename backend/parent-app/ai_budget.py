"""Persistent spend guard. Stores no questions, answers, profiles or credentials.

The ledger uses a separate SQLite transaction, so concurrent provider calls reserve
their budget before network access even while the application database is busy.
Rubles are represented as integer millionths; unknown usage retains the reservation.
"""
import contextvars
from contextlib import contextmanager
from datetime import datetime, date
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from zoneinfo import ZoneInfo

MICRO = 1_000_000
ACTOR = contextvars.ContextVar('ai_budget_actor', default='')
REQUEST = contextvars.ContextVar('ai_budget_request', default='')
PRICE_SOURCE = 'https://proxyapi.ru/models/z-ai/glm-5.3-flash'
DEFAULT_RATES = {'z-ai/glm-5.3-flash': {'inputPerMillion':'10.11', 'outputPerMillion':'33.68',
                                     'checkedAt':'2026-10-11', 'source':PRICE_SOURCE}}


class BudgetError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def decimal(value):
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError()
    return result


def settings():
    path = os.environ.get('AI_POLICY_FILE')
    if not path:
        return {}
    try:
        result = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except (OSError, ValueError, TypeError):
        raise BudgetError(503, 'Не удалось прочитать настройки расходов ИИ. Обратитесь к владельцу.') from None


def setting(name, default):
    return settings().get(name, os.environ.get(name, default))


def config():
    try:
        policy = settings()
        value = lambda key, default: policy.get(key, os.environ.get(key,default))
        daily = int((decimal(value('AI_BUDGET_DAY_RUB', '100'))*MICRO).to_integral_value(rounding=ROUND_CEILING))
        monthly = int((decimal(value('AI_BUDGET_MONTH_RUB', '1000'))*MICRO).to_integral_value(rounding=ROUND_CEILING))
        maximum_input = int(value('AI_MAX_INPUT_BYTES', '131072'))
        concurrency = int(value('AI_MAX_CONCURRENT_CALLS', '4'))
        if maximum_input < 1024 or maximum_input > 1_000_000 or not 1 <= concurrency <= 20:
            raise ValueError()
        return daily, monthly, maximum_input, concurrency
    except (ValueError, InvalidOperation, TypeError):
        raise BudgetError(503, 'Контроль расходов ИИ настроен неверно. Обратитесь к владельцу.') from None


def location():
    target = os.environ.get('APP_AI_BUDGET_PATH')
    if not target and os.environ.get('APP_SQLITE_PATH'):
        target = str(Path(os.environ['APP_SQLITE_PATH']).with_suffix('.ai-budget.sqlite3'))
    if not target:
        raise BudgetError(503, 'Учёт расходов ИИ не настроен. Обратитесь к владельцу.')
    return Path(target)


@contextmanager
def database():
    path = location()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    try:
        # SQLite can report BUSY immediately when several first requests switch
        # a newly created ledger to WAL. Retry that setup only; never retry a
        # provider call or a committed reservation.
        deadline = time.monotonic()+15
        while True:
            try:
                db.execute('PRAGMA journal_mode=WAL')
                break
            except sqlite3.OperationalError as exc:
                if not any(word in str(exc).lower() for word in ('locked','busy')) or time.monotonic()>=deadline:
                    raise
                time.sleep(.03)
        db.execute('PRAGMA synchronous=FULL')
        db.executescript('''CREATE TABLE IF NOT EXISTS ai_spend (
          id TEXT PRIMARY KEY, actor TEXT NOT NULL, request_key TEXT NOT NULL,
          kind TEXT NOT NULL, model TEXT NOT NULL, day TEXT NOT NULL, month TEXT NOT NULL,
          started INTEGER NOT NULL, status TEXT NOT NULL, reserved_micro INTEGER NOT NULL,
          accounted_micro INTEGER NOT NULL, input_tokens INTEGER, output_tokens INTEGER,
          usage_known INTEGER NOT NULL DEFAULT 0, input_price TEXT NOT NULL,
          output_price TEXT NOT NULL, price_checked TEXT NOT NULL);
          CREATE INDEX IF NOT EXISTS ai_spend_day ON ai_spend(day);
          CREATE INDEX IF NOT EXISTS ai_spend_month ON ai_spend(month);
          CREATE INDEX IF NOT EXISTS ai_spend_pending ON ai_spend(status,started);
        ''')
        yield db
        db.commit()
    finally:
        db.close()


@contextmanager
def scope(uid, ident):
    # Identity hashes use the application encryption key, never an API key.
    secret = os.environ.get('APP_DATA_KEY', '').encode()
    actor = hmac.new(secret, str(uid).encode(), hashlib.sha256).hexdigest()
    request = hmac.new(secret, (actor+':'+str(ident)).encode(), hashlib.sha256).hexdigest()
    a, r = ACTOR.set(actor), REQUEST.set(request)
    try:
        yield
    finally:
        ACTOR.reset(a); REQUEST.reset(r)


def rates(model):
    try:
        configured = json.loads(os.environ['AI_COST_RATES_JSON']) if os.environ.get('AI_COST_RATES_JSON') else DEFAULT_RATES
        rate = configured[model]
        incoming, outgoing = decimal(rate['inputPerMillion']), decimal(rate['outputPerMillion'])
        checked = date.fromisoformat(rate['checkedAt'])
        today = datetime.now(ZoneInfo('Europe/Moscow')).date()
        if not 0 <= (today-checked).days <= 31:
            raise ValueError()
        return incoming, outgoing, checked.isoformat()
    except (KeyError, ValueError, TypeError, InvalidOperation):
        raise BudgetError(503, 'Для модели ИИ нужно проверить и обновить тариф в настройках расходов.') from None


def price(incoming, outgoing, input_price, output_price):
    # Price per million tokens * token count == millionths of a ruble.
    return int((Decimal(incoming)*input_price+Decimal(outgoing)*output_price).to_integral_value(rounding=ROUND_CEILING))


def reserve(model, kind, input_bytes, maximum_output):
    daily, monthly, maximum_input, concurrency = config()
    if input_bytes > maximum_input:
        raise BudgetError(413, 'Контекст вопроса слишком большой. Начните новый диалог; прежняя история сохранится.')
    incoming, outgoing, checked = rates(model)
    # UTF-8 JSON bytes plus per-message headroom are a conservative input estimate.
    estimate = price(input_bytes+1024, maximum_output, incoming, outgoing)
    stamp = int(time.time())
    now = datetime.fromtimestamp(stamp, ZoneInfo('Europe/Moscow'))
    day, month = now.date().isoformat(), now.strftime('%Y-%m')
    actor, request = ACTOR.get(), REQUEST.get()
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        # Owner edits acquire this same lock before replacing the policy file.
        daily, monthly, maximum_input, concurrency = config()
        # Never return money for abandoned requests: their billing is unknown.
        db.execute("UPDATE ai_spend SET status='unknown' WHERE status='pending' AND started<?", (stamp-300,))
        if actor and db.execute("SELECT 1 FROM ai_spend WHERE actor=? AND status='pending'", (actor,)).fetchone():
            raise BudgetError(409, 'Для аккаунта уже готовится ответ или подборка. Дождитесь завершения и повторите запрос.')
        if db.execute("SELECT COUNT(*) FROM ai_spend WHERE status='pending'").fetchone()[0] >= concurrency:
            raise BudgetError(429, 'ИИ сейчас занят. Ваш вопрос сохранён; повторите отправку немного позже.')
        day_used = db.execute('SELECT COALESCE(SUM(accounted_micro),0) FROM ai_spend WHERE day=?', (day,)).fetchone()[0]
        month_used = db.execute('SELECT COALESCE(SUM(accounted_micro),0) FROM ai_spend WHERE month=?', (month,)).fetchone()[0]
        if day_used+estimate > daily or month_used+estimate > monthly:
            raise BudgetError(429, 'ИИ временно приостановлен: достигнут общий бюджет сервиса. История и трекеры доступны; срочная помощь — по ссылке ниже.')
        ident = secrets.token_hex(16)
        db.execute('INSERT INTO ai_spend VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (ident,actor,request,kind,model,day,month,stamp,'pending',estimate,estimate,None,None,0,str(incoming),str(outgoing),checked))
    return ident


def finish(ident, usage, status):
    usage = usage if isinstance(usage,dict) else {}
    tokens = [usage.get(key) for key in ('prompt_tokens','completion_tokens')]
    known = all(type(value) is int and value >= 0 for value in tokens)
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT reserved_micro,input_price,output_price,status FROM ai_spend WHERE id=?', (ident,)).fetchone()
        if not row or row[3] not in ('pending','unknown'):
            return
        amount = price(*tokens, Decimal(row[1]), Decimal(row[2])) if known else row[0]
        db.execute('UPDATE ai_spend SET status=?,accounted_micro=?,input_tokens=?,output_tokens=?,usage_known=? WHERE id=?',
                   (status if known else 'unknown', amount, tokens[0] if known else None, tokens[1] if known else None, int(known),ident))


def summary():
    daily, monthly, maximum_input, concurrency = config()
    now = datetime.now(ZoneInfo('Europe/Moscow'))
    day, month = now.date().isoformat(), now.strftime('%Y-%m')
    result = {'timezone':'Europe/Moscow','day':day,'month':month,'dailyLimitRub':daily/MICRO,
              'monthlyLimitRub':monthly/MICRO,'inputBytesLimit':maximum_input,'concurrencyLimit':concurrency,
              'freeChatLimit':int(setting('AI_FREE_CHAT_LIMIT','70')),'policyEditable':bool(os.environ.get('AI_POLICY_FILE')),
              'note':'Расчёт по тарифу без скидки за кэш. Не является выпиской ProxyAPI. Запросы без данных о токенах учитываются резервом.'}
    with database() as db:
        for label, field, period, cap in (('today','day',day,daily),('monthToDate','month',month,monthly)):
            row = db.execute(f'''SELECT COALESCE(SUM(CASE WHEN usage_known=1 THEN accounted_micro ELSE 0 END),0),
                      COALESCE(SUM(CASE WHEN usage_known=0 THEN accounted_micro ELSE 0 END),0),COUNT(*),
                      SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END),SUM(CASE WHEN usage_known=0 AND status!='pending' THEN 1 ELSE 0 END)
                      FROM ai_spend WHERE {field}=?''', (period,)).fetchone()
            accounted = row[0]+row[1]
            result[label] = {'estimatedRub':row[0]/MICRO,'reservedRub':row[1]/MICRO,'accountedRub':accounted/MICRO,
                             'remainingRub':max(0,cap-accounted)/MICRO,'calls':row[2], 'pending':row[3] or 0,
                             'unknownUsage':row[4] or 0, 'warning':accounted >= cap*.8, 'exhausted':accounted>=cap}
        result['byKind']=[{'kind':r[0],'calls':r[1],'estimatedRub':r[2]/MICRO,'reservedRub':r[3]/MICRO}
                         for r in db.execute('''SELECT kind,COUNT(*),COALESCE(SUM(CASE WHEN usage_known=1 THEN accounted_micro ELSE 0 END),0),
                         COALESCE(SUM(CASE WHEN usage_known=0 THEN accounted_micro ELSE 0 END),0) FROM ai_spend WHERE month=? GROUP BY kind''',(month,))]
    return result


def write_policy(body):
    path = os.environ.get('AI_POLICY_FILE')
    if not path:
        raise ValueError('Редактирование настроек расходов не подключено.')
    if not isinstance(body,dict) or set(body)!={'dailyLimitRub','monthlyLimitRub','freeChatLimit'}:
        raise ValueError('Проверьте поля настроек расходов.')
    try:
        daily, monthly = decimal(body['dailyLimitRub']), decimal(body['monthlyLimitRub'])
        free = body['freeChatLimit']
        if type(free) is not int or not 0<=free<=10000 or daily>1_000_000 or monthly>1_000_000:
            raise ValueError()
    except (ValueError, TypeError, InvalidOperation):
        raise ValueError('Проверьте бюджет и лимит: значения не могут быть отрицательными.') from None
    destination = Path(path)
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        policy = settings()
        policy.update(AI_BUDGET_DAY_RUB=str(daily), AI_BUDGET_MONTH_RUB=str(monthly), AI_FREE_CHAT_LIMIT=str(free))
        temporary = destination.with_name(destination.name+'.'+secrets.token_hex(4)+'.tmp')
        try:
            temporary.write_text(json.dumps(policy,ensure_ascii=False,indent=2),encoding='utf-8')
            os.replace(temporary,destination)
        finally:
            if temporary.exists(): temporary.unlink()
    return summary()
