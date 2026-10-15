"""Local feedback triage + aggregate-only AI review. Never export free text.

Original encrypted feedback is read-only. Only enum counters cross the provider
boundary. Rules are proposals; there is deliberately no apply/deploy capability.
"""
from contextlib import contextmanager, closing
from datetime import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
import urllib.request
from zoneinfo import ZoneInfo

import ai_budget
import content_policy
import operations as ops

VERSION = 'feedback-aggregate-review-v1'
KINDS = ('helpful', 'unhelpful', 'unsafe', 'idea')
LABELS = {
    'negative_unspecified': 'Причина отрицательной оценки не уточнена',
    'safety_signal': 'Пользователь отметил ответ как небезопасный',
    'age_conflict': 'В ответе обнаружено возможное несоответствие возрасту профиля',
    'other_profile': 'Возможное предложение подменить возраст или профиль',
    'stale_diary': 'Жалоба на устаревшие записи дневника',
    'unclear_action': 'Неясно, что сделать после ответа',
    'tone': 'Жалоба на тон или отсутствие поддержки',
    'repetition': 'Жалоба на повторение рекомендаций',
    'technical': 'Жалоба на работу интерфейса или сервиса',
    'internal_fields': 'В ответе встречаются технические названия полей',
    'feature_request': 'Предложение функции',
    'unreadable': 'Не удалось разобрать сохранённый отзыв',
}
RULES = {
    'negative_unspecified': 'Сначала выяснить причину отрицательной оценки; не менять рекомендации по одной оценке.',
    'safety_signal': 'Локально проверить ответ и официальные основания. Сам отзыв не подтверждает медицинскую ошибку. Срочная помощь остаётся доступной.',
    'age_conflict': 'Возраст берётся только из активного профиля на момент ответа. Проверять обе границы применимости и навыки; ноль месяцев — известный возраст.',
    'other_profile': 'Возраст из сообщения не заменяет профиль. Для другого ребёнка требуется отдельный профиль и диалог.',
    'stale_diary': 'Использовать актуальные записи после правки или удаления; старые ответы не доказывают текущее состояние дневника.',
    'unclear_action': 'Дать один понятный следующий шаг; объяснить ограничения и существенные условия.',
    'tone': 'Отвечать тепло по запросу, без вины, сравнения, обесценивания или обещания эффекта. Самопомощь добровольна.',
    'repetition': 'Не повторять отвергнутую механику под другим названием; учитывать причину отказа.',
    'technical': 'Сохранять вопрос и историю при сбое. Ошибка сервиса не расходует пользовательский лимит.',
    'internal_fields': 'Названия полей, служебные ключи и JSON не показывать в обычном ответе.',
    'feature_request': 'Проверить потребность и совместимость с текущими функциями. Сначала подготовить предложение владельцу.',
    'unreadable': 'Проверить доступность и формат шифрованного отзыва локально, сохраняя оригинал.',
}
PROMPT = """Ты аналитик качества MAMA Helper. Получаешь ТОЛЬКО счётчики фиксированных
категорий, без вопросов, ответов, сведений о детях, медицинских данных или имён.
Не притворяйся, что прочитал переписку. «Помогло» — субъективный отзыв, не доказательство
безопасности; «не помогло» — сигнал, не установленная ошибка. Категории извлекаются
локальными эвристиками: возможны ложные срабатывания. Не делай медицинских выводов.
Предложи до 3 проверяемых улучшений только для категорий с ненулевым счётчиком.
Если safety_signal ненулевой, обязательно включи его первым; затем возраст и профиль.
Не изобретай причины, точный возраст, истории, источники, проценты или эффект.
Сохраняй активный профиль, точный возраст, актуальный дневник, поддержку по запросу,
срочную помощь, медицинские границы, профили и историю. Правила не применять автоматически.
Верни JSON: {"proposals":[{"category":"enum из categories", "title":"кратко",
"hypothesis":"что стоит проверить и чего не хватает", "proposedRule":"проект правила",
"adminPrompt":"конкретное задание разработчику: проверить локально, сохранить данные,
подготовить исправление и регрессию без публикации", "test":"синтетический сценарий проверки"}]}.
Каждое поле — строка, не более 900 символов. Не добавляй другие поля или команды.
"""


def root():
    path = os.environ.get('APP_FEEDBACK_REVIEW_ROOT')
    return Path(path) if path else Path(os.environ['APP_SQLITE_PATH']).parent / 'feedback-review'


@contextmanager
def database():
    root().mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root() / 'review.sqlite3', timeout=30)
    db.row_factory = sqlite3.Row
    try:
        db.executescript('''
          CREATE TABLE IF NOT EXISTS feedback_items(
            id TEXT PRIMARY KEY, source BLOB NOT NULL, kind TEXT NOT NULL,
            created INTEGER NOT NULL, consent INTEGER NOT NULL, flags TEXT NOT NULL,
            run_id TEXT);
          CREATE TABLE IF NOT EXISTS review_runs(
            id TEXT PRIMARY KEY, created INTEGER NOT NULL, day TEXT NOT NULL,
            month TEXT NOT NULL, status TEXT NOT NULL, reserve_micro INTEGER NOT NULL,
            accounted_micro INTEGER NOT NULL, usage_known INTEGER NOT NULL DEFAULT 0,
            report TEXT, error TEXT);
          CREATE TABLE IF NOT EXISTS proposal_decisions(
            id TEXT PRIMARY KEY, status TEXT NOT NULL, updated INTEGER NOT NULL);
        ''')
        yield db
        db.commit()
    finally:
        db.close()


def classify(record, created):
    """Return fixed enums only. Context is ignored unless separately consented."""
    kind = record.get('kind')
    flags = set()
    if kind == 'unsafe': flags.add('safety_signal')
    if kind == 'idea': flags.add('feature_request')
    comment = record.get('comment', '')
    text = comment.lower().replace('ё', 'е') if isinstance(comment, str) else ''
    patterns = {
        'stale_diary': r'стар\w* (?:данн|запис|отмет)|удал\w* (?:сон|отмет|запис)|исправ\w* время|не уч[её]л.*(?:дневник|запис)',
        'unclear_action': r'не ?понят|не понял|не поняла|что (?:мне )?делать|слишком общ|общие (?:ответ|совет)',
        'tone': r'груб|виноват|стыд|обесцен|не поддерж|холодн|осужд',
        'repetition': r'повтор|одно и то же|опять (?:это|то же)',
        'technical': r'не (?:работ|откры|сохран)|ошибк\w* сервис|долго|завис|кнопк|лимит',
    }
    for flag, pattern in patterns.items():
        if re.search(pattern, text): flags.add(flag)
    if record.get('consentContext') is True:
        context = record.get('context')
        context = context if isinstance(context, dict) else {}
        messages = context.get('messages', [])
        messages = messages if isinstance(messages, list) else []
        target = next((m for m in messages if isinstance(m, dict) and
                       m.get('id') == record.get('messageId') and m.get('role') == 'assistant'), {})
        answer = target.get('text', '')
        answer = answer if isinstance(answer, str) else ''
        q = answer.lower().replace('ё', 'е')
        if re.search(r'(?:назовите|укажите|напишите).*возраст.*(?:друг|любо)|(?:заменим|изменим).*возраст', q):
            flags.add('other_profile')
        if re.search(r'recordedSleepMinutesTotal|sleepIntervals|careSummary|ageMonths', answer):
            flags.add('internal_fields')
        age = content_policy.months(context.get('profile'), datetime.fromtimestamp(created, ZoneInfo('Europe/Saratov')).date())
        if age is not None:
            for number in re.findall(r'(?:вашему (?:ребенку|малышу)|ваш (?:ребенок|малыш)).{0,12}?(\d{1,3})\s*месяц', q):
                if int(number) != age: flags.add('age_conflict')
    if kind == 'unhelpful' and not flags: flags.add('negative_unspecified')
    return sorted(flags)


def collect(limit=500):
    """Read originals without mutation; keep only counters and encrypted locators."""
    import index as app
    key = os.environ['APP_DATA_KEY'].encode()
    added = 0
    with database() as dest, closing(sqlite3.connect('file:' + Path(os.environ['APP_SQLITE_PATH']).as_posix() + '?mode=ro', uri=True)) as src:
        # Chunked scan also catches older imported records; no time cursor omissions.
        for user, request, encrypted, created in src.execute('SELECT user_id,request_id,encrypted_data,created_at FROM mh_feedback ORDER BY created_at,rowid'):
            ident = hmac.new(key, ('feedback-review:' + str(user) + ':' + str(request)).encode(), hashlib.sha256).hexdigest()[:32]
            if dest.execute('SELECT 1 FROM feedback_items WHERE id=?', (ident,)).fetchone(): continue
            try:
                record = app.unseal(encrypted)
                if not isinstance(record, dict) or record.get('kind') not in KINDS: raise ValueError()
                kind, consent = record['kind'], record.get('consentContext') is True
                flags = classify(record, created)
            except Exception:
                kind, consent, flags = 'unreadable', False, ['unreadable']
            locator = app.seal({'user': user, 'request': request})
            dest.execute('INSERT INTO feedback_items VALUES(?,?,?,?,?,?,?)',
                         (ident, locator, kind, created, int(consent), json.dumps(flags), None if flags else 'observed'))
            added += 1
            if added >= limit: break
    return added


def safe_payload(items):
    """Privacy boundary: reconstruct a closed schema, never copy input objects."""
    kinds = {k: 0 for k in KINDS}
    categories = {k: 0 for k in LABELS}
    context_count = 0
    for item in items:
        if item['kind'] in kinds: kinds[item['kind']] += 1
        context_count += int(bool(item['consent']))
        for flag in json.loads(item['flags']):
            if flag in categories: categories[flag] += 1
    return {'version': VERSION, 'counts': kinds, 'categories': categories,
            'contextAvailableLocally': context_count, 'total': len(items),
            'limitations': ['heuristics-not-confirmed-errors', 'no-chat-or-child-data-export',
                            'subjective-feedback-not-medical-validation']}


def validate_proposals(body, payload):
    if not isinstance(body, dict) or set(body) != {'proposals'}: raise ValueError('schema')
    values = body['proposals']
    if not isinstance(values, list) or not 1 <= len(values) <= 3: raise ValueError('schema')
    result = []
    fields = {'category', 'title', 'hypothesis', 'proposedRule', 'adminPrompt', 'test'}
    seen = set()
    for item in values:
        if not isinstance(item, dict) or set(item) != fields: raise ValueError('schema')
        if any(not isinstance(v, str) or not 1 <= len(v.strip()) <= 900 for v in item.values()): raise ValueError('schema')
        category = item['category']
        if category not in LABELS or not payload['categories'].get(category) or category in seen: raise ValueError('category')
        seen.add(category)
        result.append({**item, 'priority': 'P0' if category == 'safety_signal' else 'P1' if category in ('age_conflict', 'other_profile', 'stale_diary') else 'P2',
                       'evidenceCount': payload['categories'][category], 'evidenceStatus': 'signal-not-confirmed',
                       'boundary': RULES[category], 'humanApprovalRequired': True})
    if payload['categories'].get('safety_signal') and 'safety_signal' not in seen: raise ValueError('missing-safety-signal')
    return result


def call_ai(payload):
    """One bounded provider call; all billing remains in the common ledger."""
    if (not isinstance(payload, dict) or set(payload) != {'version','counts','categories','contextAvailableLocally','total','limitations'}
        or payload['version'] != VERSION or set(payload['counts']) != set(KINDS) or set(payload['categories']) != set(LABELS)
        or payload['limitations'] != ['heuristics-not-confirmed-errors','no-chat-or-child-data-export','subjective-feedback-not-medical-validation']
        or any(type(v) is not int or not 0 <= v <= 500 for v in [*payload['counts'].values(), *payload['categories'].values(), payload['contextAvailableLocally'], payload['total']])):
        raise ValueError('aggregate-only-boundary')
    model = os.environ.get('PROXYAPI_CHAT_MODEL', 'z-ai/glm-5.3-flash')
    key = os.environ.get('PROXYAPI_API_KEY', '').strip()
    if not key: raise ValueError('provider-not-configured')
    data = json.dumps({'model': model, 'messages': [{'role': 'system', 'content': PROMPT},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}],
        'temperature': 0.2, 'max_tokens': 1800, 'response_format': {'type': 'json_object'},
        'reasoning_effort': 'low'}, ensure_ascii=False).encode()
    lease = ai_budget.reserve(model, 'feedback-analysis', len(data), 1800)
    usage, status = None, 'error'
    started = time.monotonic()
    try:
        request = urllib.request.Request('https://api.proxyapi.ru/v1/chat/completions', data=data,
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key,
                     'x-data-logging-enabled': 'false', 'Connection': 'close'})
        with urllib.request.urlopen(request, timeout=70) as response:
            body = json.loads(response.read(200000))
        usage = body.get('usage')
        status = 'invalid'
        choice = body['choices'][0]
        if choice.get('finish_reason') == 'length': raise ValueError('truncated')
        proposals = validate_proposals(json.loads(choice['message']['content']), payload)
        status = 'ok'
        return proposals
    finally:
        ai_budget.finish(lease, usage, status)
        ops.ai_call('feedback-analysis', model, status, time.monotonic()-started, usage)


def review():
    added = collect()
    stamp = int(time.time())
    now = datetime.fromtimestamp(stamp, ZoneInfo('Europe/Moscow'))
    day, month = now.date().isoformat(), now.strftime('%Y-%m')
    model = os.environ.get('PROXYAPI_CHAT_MODEL', 'z-ai/glm-5.3-flash')
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        items = db.execute('SELECT * FROM feedback_items WHERE run_id IS NULL ORDER BY created,id LIMIT 500').fetchall()
        payload = safe_payload(items)
        if not any(payload['categories'].values()):
            return {'ok': True, 'state': 'no-new-signals', 'collected': added, 'pending': len(items), 'aiCalled': False}
        if db.execute('SELECT 1 FROM review_runs WHERE day=?', (day,)).fetchone():
            return {'ok': True, 'state': 'waiting-next-day', 'collected': added, 'pending': len(items), 'aiCalled': False}
        # Independent subset cap. Never raise common budgets; count uncertain calls.
        incoming, outgoing, _ = ai_budget.rates(model)
        estimate = ai_budget.price(12000, 1800, incoming, outgoing)
        monthly = db.execute('SELECT COALESCE(SUM(accounted_micro),0) FROM review_runs WHERE month=?', (month,)).fetchone()[0]
        if estimate > 1_000_000 or monthly + estimate > 10_000_000:
            return {'ok': True, 'state': 'review-budget-paused', 'collected': added, 'pending': len(items), 'aiCalled': False}
        if not os.environ.get('PROXYAPI_API_KEY'):
            return {'ok': True, 'state': 'provider-not-configured', 'collected': added, 'pending': len(items), 'aiCalled': False}
        ident = secrets.token_hex(16)
        db.execute('INSERT INTO review_runs VALUES(?,?,?,?,?,?,?,0,NULL,NULL)',
                   (ident, stamp, day, month, 'running', estimate, estimate))
        for item in items: db.execute('UPDATE feedback_items SET run_id=? WHERE id=?', (ident, item['id']))
    try:
        with ai_budget.scope('feedback-review-owner', ident):
            ledger_request = ai_budget.REQUEST.get()
            proposals = call_ai(payload)
        report = {'version': VERSION, 'aggregate': payload, 'proposals': proposals,
                  'humanApprovalRequired': True, 'externalChatExport': False, 'method': 'ai-on-enum-aggregates'}
        with database() as db:
            with ai_budget.database() as ledger:
                row = ledger.execute('SELECT accounted_micro,usage_known FROM ai_spend WHERE request_key=? AND kind=? ORDER BY started DESC LIMIT 1', (ledger_request, 'feedback-analysis')).fetchone()
            amount, known = (row[0], row[1]) if row else (estimate, 0)
            db.execute('UPDATE review_runs SET status=?,accounted_micro=?,usage_known=?,report=? WHERE id=?',
                       ('success', amount, known, json.dumps(report, ensure_ascii=False), ident))
        return {'ok': True, 'state': 'proposals-ready', 'runId': ident, 'proposals': len(proposals), 'aiCalled': True,
                'externalChatExport': False, 'humanApprovalRequired': True}
    except Exception as exc:
        # Do not log provider bodies, feedback or arbitrary exception text.
        code = 'budget-paused' if isinstance(exc, ai_budget.BudgetError) else 'analysis-needs-review'
        with database() as db:
            with ai_budget.database() as ledger:
                row = ledger.execute('SELECT accounted_micro,usage_known FROM ai_spend WHERE request_key=? AND kind=? ORDER BY started DESC LIMIT 1', (locals().get('ledger_request', ''), 'feedback-analysis')).fetchone()
            amount, known = (row[0], row[1]) if row else (0, 1) if code == 'budget-paused' else (estimate, 0)
            db.execute('UPDATE review_runs SET status=?,error=?,accounted_micro=?,usage_known=? WHERE id=?', ('failed', code, amount, known, ident))
            if code == 'budget-paused':
                db.execute('UPDATE feedback_items SET run_id=NULL WHERE run_id=?', (ident,))
        return {'ok': False, 'state': code, 'runId': ident, 'aiCalled': code != 'budget-paused', 'automaticRetry': False}


def summary():
    with database() as db:
        db.execute("UPDATE review_runs SET status='uncertain',error='interrupted-needs-local-review' WHERE status='running' AND created<?", (int(time.time())-300,))
        counts = {row['kind']: row['n'] for row in db.execute('SELECT kind,COUNT(*) n FROM feedback_items GROUP BY kind')}
        pending = db.execute('SELECT COUNT(*) FROM feedback_items WHERE run_id IS NULL').fetchone()[0]
        categories = {k: 0 for k in LABELS}
        for row in db.execute('SELECT flags FROM feedback_items'):
            for flag in json.loads(row[0]):
                if flag in categories: categories[flag] += 1
        proposals, runs = [], []
        for row in db.execute('SELECT * FROM review_runs ORDER BY created DESC LIMIT 30'):
            runs.append({'id': row['id'], 'created': row['created'], 'status': row['status'], 'error': row['error'],
                         'estimatedRub': row['accounted_micro']/1_000_000, 'usageKnown': bool(row['usage_known'])})
            if row['report']:
                report = json.loads(row['report'])
                for i, p in enumerate(report['proposals']):
                    ident = row['id'] + ':' + str(i)
                    decision = db.execute('SELECT status FROM proposal_decisions WHERE id=?', (ident,)).fetchone()
                    refs = [r[0] for r in db.execute('SELECT id FROM feedback_items WHERE run_id=? AND flags LIKE ? LIMIT 10', (row['id'], '%"' + p['category'] + '"%'))]
                    proposals.append({**p, 'id': ident, 'created': row['created'], 'status': decision[0] if decision else 'new', 'localEvidence': refs})
        return {'version': VERSION, 'counts': counts, 'pending': pending, 'runs': runs, 'proposals': proposals,
                'signals': [{'category':k,'label':LABELS[k],'count':v,
                             'localEvidence':[r[0] for r in db.execute('SELECT id FROM feedback_items WHERE flags LIKE ? ORDER BY created DESC LIMIT 10', ('%"'+k+'"%',))]}
                            for k,v in categories.items() if v],
                'schedule': 'Каждые 30 минут; не более одного вызова ИИ в сутки по Москве',
                'limits': {'dailyRub': 1, 'monthlyRub': 10, 'callsPerDay': 1},
                'externalChatExport': False, 'automaticRuleChanges': False}


def decide(body):
    if set(body) != {'id', 'status'} or body['status'] not in ('new', 'planned', 'dismissed'): raise ValueError('Неверный статус')
    if not isinstance(body['id'], str) or not re.fullmatch(r'[0-9a-f]{32}:[0-2]', body['id']): raise ValueError('Предложение не найдено')
    ident, ordinal = body['id'].split(':')
    with database() as db:
        row = db.execute('SELECT report FROM review_runs WHERE id=? AND status=?', (ident, 'success')).fetchone()
        if not row or int(ordinal) >= len(json.loads(row['report'])['proposals']): raise ValueError('Предложение не найдено')
        db.execute('INSERT INTO proposal_decisions VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,updated=excluded.updated', (body['id'], body['status'], int(time.time())))
    return {'ok': True, 'rulesApplied': False}


def evidence(ident):
    """Explicit owner-only local read. No extra access to non-consented dialogs."""
    import index as app
    if not re.fullmatch(r'[0-9a-f]{32}', ident): raise ValueError('Пример не найден')
    with database() as db:
        row = db.execute('SELECT source FROM feedback_items WHERE id=?', (ident,)).fetchone()
    if not row: raise ValueError('Пример не найден')
    locator = app.unseal(row[0])
    with closing(sqlite3.connect('file:' + Path(os.environ['APP_SQLITE_PATH']).as_posix() + '?mode=ro', uri=True)) as db:
        row = db.execute('SELECT encrypted_data FROM mh_feedback WHERE user_id=? AND request_id=?', (locator['user'], locator['request'])).fetchone()
    if not row: return {'available': False, 'reason': 'Оригинал недоступен; данные не восстанавливались.'}
    record = app.unseal(row[0])
    result = {'available': True, 'kind': record.get('kind'), 'comment': record.get('comment', ''),
              'consentContext': record.get('consentContext') is True, 'messages': []}
    if result['consentContext']:
        context = record.get('context', {})
        result['messages'] = [{'role': m.get('role'), 'text': m.get('text', '')} for m in context.get('messages', []) if isinstance(m, dict)][-6:]
    return result


def forget(user_id):
    """Remove private evidence locators on the existing account deletion path."""
    if not (root() / 'review.sqlite3').exists(): return 0
    import index as app
    removed = 0
    with database() as db:
        for row in db.execute('SELECT id,source FROM feedback_items').fetchall():
            if app.unseal(row['source']).get('user') == user_id:
                db.execute('DELETE FROM feedback_items WHERE id=?', (row['id'],)); removed += 1
    return removed
