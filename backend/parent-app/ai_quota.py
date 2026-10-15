"""Account-wide answer quota; child/profile changes never reset it."""
import hashlib
import hmac
import os
import ai_budget
import billing


def free_limit(app):
    try:
        limit = int(ai_budget.setting('AI_FREE_CHAT_LIMIT', '70'))
        if not 0 <= limit <= 10000:
            raise ValueError()
        return limit
    except (ValueError, TypeError):
        raise app.AppError(503, 'Лимит ответов настроен неверно. Обратитесь к владельцу.') from None
    except ai_budget.BudgetError as exc:
        raise app.AppError(exc.status,exc.message) from None


def read(app, db, user):
    access = billing.access(db, user[0])
    paid = app._birthdays.paid_access(db, user[0])
    test = access['mode'] == 'test'
    key = ('test-quota:'+user[0]+':'+access['periodKey'] if test else
           'paid-quota:'+user[0]+':'+paid[0] if paid else 'ai-quota:'+user[0])
    # Keep old counters and an independent, opaque email counter. Re-registering
    # the same address does not restore a free trial after account deletion.
    stable = None
    if not paid and not test:
        identity = hmac.new(app.fernet_key(), ('free-trial:'+user[1].strip().lower()).encode(), hashlib.sha256).hexdigest()
        stable = 'free-trial:'+identity
    row = db.query('SELECT count FROM mh_limits WHERE key=?', (key,)).fetchone()
    used = int(row[0]) if row else 0
    if stable:
        row = db.query('SELECT count FROM mh_limits WHERE key=?', (stable,)).fetchone()
        used = max(used, int(row[0]) if row else 0)
    base = int(paid[1]) if paid else access['answerLimit'] if test else 0 if billing.enabled() else free_limit(app)
    bonus = app._birthdays.balance(db, user[0]) if paid else 0
    return {'key':key, 'stableKey':stable, 'used':used, 'base':base, 'bonus':bonus, 'paid':bool(paid), 'accessMode':access['mode'], 'endsAt':access.get('endsAt')}


def public(quota):
    extra = quota['bonus']
    result = {'limit':quota['base']+extra, 'used':quota['used'],
              'remaining':max(0, quota['base']-quota['used'])+extra, 'accessMode':quota.get('accessMode','legacy')}
    if quota['paid']:
        result.update(paid=True, bonusRemaining=extra)
    return result


def charge(app, db, user, quota):
    # The caller already holds the state write lock. Re-read here so parallel
    # requests cannot both spend the last answer from an earlier snapshot.
    quota.update(read(app, db, user))
    if quota['used'] >= quota['base'] and quota['bonus'] == 0:
        raise app.AppError(429, 'Доступные AI-ответы закончились. Обратитесь к организатору.')
    if quota['paid'] and quota['used'] >= quota['base']:
        if not app._birthdays.consume(db, user[0]):
            raise app.AppError(409, 'Баланс изменился. Повторите запрос.')
        quota['bonus'] -= 1
        return
    quota['used'] += 1
    expiry = int(quota['endsAt'])+365*86400 if billing.enabled() and quota.get('endsAt') else 4102444800
    for key in (quota['key'], quota['stableKey']):
        if key:
            db.query('INSERT INTO mh_limits(key,count,until_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET count=excluded.count,until_at=excluded.until_at',
                     (key, quota['used'], expiry))


def forget(app, db, user):
    if not billing.enabled():
        return
    for prefix in ('paid-quota:'+user[0]+':', 'test-quota:'+user[0]+':'):
        db.query('DELETE FROM mh_limits WHERE substr(key,1,?)=?',(len(prefix),prefix))
    identity=hmac.new(app.fernet_key(),('free-trial:'+user[1].strip().lower()).encode(),hashlib.sha256).hexdigest()
    db.query('DELETE FROM mh_limits WHERE key IN (?,?)',('ai-quota:'+user[0],'free-trial:'+identity))
