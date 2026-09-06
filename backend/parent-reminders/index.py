"""Scheduled delivery; call run(db) from an authenticated cloud scheduler."""
import importlib.util
import calendar
import json
import os
import time
from datetime import date
from pathlib import Path

# Kept next to the function so a single function archive is deployable.
EVENTS = [('pregnancy-12','pregnancy',12,'pregnancy'),('pregnancy-28','pregnancy',28,'dad'),
          ('pregnancy-36','pregnancy',36,'care'),('child-0','child',0,'sleep'),
          ('child-6','child',6,'feeding'),('child-12','child',12,'play'),
          ('child-24','child',24,'play'),('child-36','child',36,'care')]


def due(state, today=None, now=None):
    today = today or date.today()
    now = int(time.time()) if now is None else now
    profile = state.get('profile')
    if not profile or not state['preferences']['push']:
        return []
    if profile['stage']=='child':
        anchor = date.fromisoformat(profile['birthDate'])
        anniversary_day = min(anchor.day,calendar.monthrange(today.year,today.month)[1])
        age = (today.year-anchor.year)*12+today.month-anchor.month-(today.day<anniversary_day)
    else:
        anchor = date.fromisoformat(profile['weekDate'])
        age = profile['week']+(today-anchor).days//7
    result=[]
    repeat = state['preferences']['repeat']
    for eid,stage,moment,topic in EVENTS:
        if stage!=profile['stage'] or age<moment or (profile['topics'] and topic not in profile['topics']):
            continue
        progress=state['events'].get(eid)
        if progress and (progress['status'] in ('read','hidden') or progress['until']>now*1000):
            continue
        result.append((eid,0 if repeat=='never' else 86400 if repeat=='day' else 7*86400))
    return result


def run(db, unseal, webpush=None):
    if not os.environ.get('VAPID_PRIVATE_KEY') or not os.environ.get('VAPID_SUBJECT'):
        raise RuntimeError('Push credentials are not configured')
    if webpush is None:
        from pywebpush import webpush
    now=int(time.time())
    delivered=0
    # Pagination keeps memory bounded; no content is logged.
    cursor=''
    while True:
        rows=db.query('''SELECT p.user_id,p.endpoint_hash,p.encrypted_subscription,s.encrypted_data
          FROM mh_push p JOIN mh_state s ON s.user_id=p.user_id
          WHERE p.endpoint_hash>? ORDER BY p.endpoint_hash LIMIT 100''',(cursor,)).fetchall()
        if not rows:
            break
        for uid,endpoint,encrypted,encrypted_state in rows:
            cursor=endpoint
            for eid,interval in due(unseal(encrypted_state)):
                cur=db.query('''INSERT INTO mh_delivery VALUES(?,?,?,?) ON CONFLICT(user_id,event_id,endpoint_hash)
                  DO UPDATE SET sent_at=? WHERE ? > 0 AND mh_delivery.sent_at<=? RETURNING sent_at''',
                  (uid,eid,endpoint,now,now,interval,now-interval))
                claimed=cur.fetchone()
                db.conn.commit()
                if not claimed:
                    continue
                try:
                    webpush(subscription_info=unseal(encrypted), data=json.dumps({'type':'age-card'}),
                            vapid_private_key=os.environ['VAPID_PRIVATE_KEY'],vapid_claims={'sub':os.environ['VAPID_SUBJECT']},timeout=8)
                    delivered+=1
                except Exception as exc:
                    status=getattr(getattr(exc,'response',None),'status_code',None)
                    if status in (404,410):
                        db.query('DELETE FROM mh_push WHERE user_id=? AND endpoint_hash=?',(uid,endpoint))
                    else:
                        db.query('DELETE FROM mh_delivery WHERE user_id=? AND event_id=? AND endpoint_hash=? AND sent_at=?',(uid,eid,endpoint,now))
                    db.conn.commit()
    return {'delivered':delivered}


def handler(event,context=None):
    import hmac
    expected=os.environ.get('REMINDER_JOB_TOKEN','')
    headers={k.lower():v for k,v in (event.get('headers') or {}).items()}
    token=headers.get('x-task-token','')
    if len(expected)<32 or not hmac.compare_digest(token,expected) or event.get('httpMethod')!='POST':
        return {'statusCode':403,'body':'Forbidden'}
    spec=importlib.util.spec_from_file_location('parent_api',Path(__file__).with_name('app.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    db=None
    try:
        db=module.DB()
        return {'statusCode':200,'body':json.dumps(run(db,module.unseal))}
    except Exception:
        return {'statusCode':503,'body':'Reminder service unavailable'}
    finally:
        if db:db.close()
