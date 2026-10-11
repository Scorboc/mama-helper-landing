"""Private, small operational store. No prompts, answers, IPs or credentials."""
import contextvars
import hashlib
import hmac
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager

actor = contextvars.ContextVar('operations_actor', default='')
PAGES = {'home','chat','trackers','favorites','more','profile','settings','advisor','card','first-aid'}
ACTIONS = {'session','register','login','chat','save','feedback','daily-plan','daily-feedback','care-put','care-delete','family-invite','subscribe','unsubscribe','page'}


def enabled():
    return bool(os.environ.get('APP_OPS_PATH'))


@contextmanager
def database():
    conn = sqlite3.connect(os.environ['APP_OPS_PATH'], timeout=2)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS events (at INTEGER, actor TEXT, action TEXT, detail TEXT);
        CREATE INDEX IF NOT EXISTS events_at ON events(at);
        CREATE INDEX IF NOT EXISTS events_actor ON events(actor,at);
        CREATE TABLE IF NOT EXISTS ai (at INTEGER, kind TEXT, model TEXT, status TEXT,
          ms INTEGER, input_tokens INTEGER, output_tokens INTEGER, prompt_version TEXT);
        CREATE INDEX IF NOT EXISTS ai_at ON ai(at);
        CREATE TABLE IF NOT EXISTS checks (at INTEGER, target TEXT, ok INTEGER, ms INTEGER);
        CREATE INDEX IF NOT EXISTS checks_at ON checks(at);
        CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, kind TEXT, body TEXT, updated INTEGER);
        ''')
        yield conn
        conn.commit()
    finally:
        conn.close()


def actor_key(uid):
    key = os.environ.get('APP_OPS_HASH_KEY','')
    if not key or not uid:
        return ''
    return hmac.new(key.encode(), uid.encode(), hashlib.sha256).hexdigest()[:32]


def event(action, uid='', detail=''):
    if not enabled() or action not in ACTIONS:
        return
    if action == 'page' and detail not in PAGES:
        return
    try:
        with database() as db:
            db.execute('INSERT INTO events VALUES(?,?,?,?)',
                       (int(time.time()), actor_key(uid), action, detail if action == 'page' else ''))
    except Exception:
        pass  # Observability must never stop the user's request.


def ai_call(kind, model, status, elapsed, usage=None, prompt=''):
    if not enabled():
        return
    try:
        usage = usage or {}
        tokens = [usage.get(k) for k in ('prompt_tokens','completion_tokens')]
        tokens = [v if type(v) is int and v >= 0 else None for v in tokens]
        with database() as db:
            db.execute('INSERT INTO ai VALUES(?,?,?,?,?,?,?,?)',
                (int(time.time()), kind, model[:120], status, int(elapsed*1000), *tokens,
                 hashlib.sha256(prompt.encode()).hexdigest()[:12]))
    except Exception:
        pass


def forget(uid):
    if enabled():
        with database() as db:
            db.execute('DELETE FROM events WHERE actor=?', (actor_key(uid),))


def document(kind, body):
    if kind not in ('content','task') or not isinstance(body,dict):
        raise ValueError('Неверная запись')
    ident = body.get('id') or uuid.uuid4().hex
    if not isinstance(ident,str) or not ident.isalnum() or len(ident)>64:
        raise ValueError('Неверный идентификатор')
    if kind == 'content':
        fields = {'title','text','category','stage','minMonths','maxMonths','source','reviewed','status','id'}
        if set(body)-fields:
            raise ValueError('Лишние поля')
        for name,limit in [('title',160),('text',2500),('source',500)]:
            if not isinstance(body.get(name),str) or not body[name].strip() or len(body[name])>limit:
                raise ValueError('Заполните заголовок, материал и источник')
        if body.get('category') not in ('sleep','feeding','play','mom','first-aid') or body.get('stage') not in ('child','pregnancy','parent'):
            raise ValueError('Укажите тему и этап')
        if body.get('status') not in ('draft','published','archived') or type(body.get('reviewed')) is not bool:
            raise ValueError('Неверный статус')
        if not body['source'].startswith('https://'):
            raise ValueError('Нужна HTTPS-ссылка на источник')
        lo,hi = body.get('minMonths'),body.get('maxMonths')
        if body['stage']=='child' and (type(lo) is not int or type(hi) is not int or not 0<=lo<=hi<=216 or hi-lo>1):
            raise ValueError('Для ребёнка: один или два соседних месяца, 0–216')
        if body['status']=='published' and not body['reviewed']:
            raise ValueError('Перед публикацией подтвердите проверку содержания')
    else:
        if set(body)-{'id','title','text','status'} or body.get('status') not in ('new','planned','done'):
            raise ValueError('Неверная задача')
        if not isinstance(body.get('title'),str) or not 1<=len(body['title'])<=160 or not isinstance(body.get('text'),str) or len(body['text'])>5000:
            raise ValueError('Проверьте текст задачи')
    body = {**body,'id':ident}
    with database() as db:
        existing=db.execute('SELECT kind FROM documents WHERE id=?',(ident,)).fetchone()
        if existing and existing[0]!=kind:
            raise ValueError('Идентификатор занят другой записью')
        db.execute('INSERT INTO documents VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body,updated=excluded.updated WHERE documents.kind=excluded.kind',
            (ident,kind,json.dumps(body,ensure_ascii=False),int(time.time())))
    return body


def documents(kind):
    if not enabled():
        return []
    with database() as db:
        return [json.loads(r[0]) for r in db.execute('SELECT body FROM documents WHERE kind=? ORDER BY updated DESC',(kind,))]


def materials(profile):
    from datetime import date, datetime
    from zoneinfo import ZoneInfo
    profile = profile or {}
    age = None
    if profile.get('stage')=='child':
        try:
            born=date.fromisoformat(profile['birthDate']); today=datetime.now(ZoneInfo('Europe/Moscow')).date()
            age=(today.year-born.year)*12+today.month-born.month-(today.day<born.day)
        except (ValueError,KeyError,TypeError):
            pass
    return [d for d in documents('content') if d['status']=='published' and d['reviewed'] and (
        d['stage']=='parent' or d['stage']=='pregnancy' and profile.get('stage')=='pregnancy' or
        d['stage']=='child' and age is not None and d['minMonths']<=age<=d['maxMonths'])]


def summary(days=7):
    since=int(time.time())-days*86400
    with database() as db:
        events=[{'action':a,'count':n} for a,n in db.execute('SELECT action,count(*) FROM events WHERE at>=? GROUP BY action',(since,))]
        pages=[{'page':p,'views':n,'users':u} for p,n,u in db.execute("SELECT detail,count(*),count(DISTINCT nullif(actor,'')) FROM events WHERE at>=? AND action='page' GROUP BY detail",(since,))]
        ai=[dict(zip(('kind','model','status','calls','inputTokens','outputTokens','averageMs','unknownUsage'),r)) for r in db.execute('SELECT kind,model,status,count(*),sum(input_tokens),sum(output_tokens),round(avg(ms)),sum(input_tokens IS NULL OR output_tokens IS NULL) FROM ai WHERE at>=? GROUP BY kind,model,status',(since,))]
        daily=[{'day':d,'users':n} for d,n in db.execute("SELECT date(at,'unixepoch'),count(DISTINCT nullif(actor,'')) FROM events WHERE at>=? AND action='page' GROUP BY 1",(since,))]
        checks=[{'target':t,'ok':bool(o),'at':a,'ms':m} for t,o,a,m in db.execute('SELECT target,ok,at,ms FROM checks WHERE rowid IN (SELECT max(rowid) FROM checks GROUP BY target)')]
        retention=[]
        for lag in (1,7,30):
            row=db.execute('''WITH visits AS (SELECT DISTINCT actor,cast(at/86400 AS INTEGER) day FROM events WHERE action='page' AND actor!=''),
                first AS (SELECT actor,min(day) day FROM visits GROUP BY actor)
                SELECT count(*),sum(EXISTS(SELECT 1 FROM visits v WHERE v.actor=f.actor AND v.day=f.day+?)) FROM first f WHERE f.day<=?''',
                (lag,int(time.time()/86400)-lag)).fetchone()
            retention.append({'day':lag,'eligible':row[0],'returned':row[1] or 0})
    return {'days':days,'events':events,'pages':pages,'ai':ai,'daily':daily,'checks':checks,'retention':retention,
            'note':'Данные собираются с момента включения. Возвраты — от первого наблюдаемого визита, UTC. Расчёт расходов ИИ и резерв показаны в отдельном разделе.'}


def prune():
    with database() as db:
        for table in ('events','ai','checks'):
            db.execute('DELETE FROM '+table+' WHERE at<?',(int(time.time())-90*86400,))
