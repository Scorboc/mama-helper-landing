"""Generate before notifying. One family-wide claim per time slot, across devices."""
import importlib.util
import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode

def run(app, db, webpush=None):
    daily,runtime=app.daily_runtime()
    if webpush is None and os.environ.get('VAPID_PRIVATE_KEY') and os.environ.get('VAPID_SUBJECT'):
        from pywebpush import webpush
    generated=delivered=errors=0
    cursor=''
    while True:
        rows=db.query('SELECT user_id,encrypted_data FROM mh_state WHERE user_id>? ORDER BY user_id LIMIT 100',(cursor,)).fetchall()
        if not rows: break
        for uid,encrypted in rows:
            cursor=uid; state=app.normalize_state(app.unseal(encrypted)); now=daily.local_now(state)
            pref=state['preferences']; hour=pref.get('morningHour',9)
            birthdays=app._birthdays.grant(db,uid,state,now.date())
            db.conn.commit()
            if now.hour<max(6,hour-1) or now.hour>=21: continue
            plans=[]
            for child in daily.children(state):
                if (child['data'].get('profile') or {}).get('stage')!='child': continue
                try:
                    existing=db.query('SELECT encrypted_data FROM mh_daily WHERE user_id=? AND child_id=? AND day=?',(uid,child['id'],now.date().isoformat())).fetchone()
                    if not existing and generated>=50: continue
                    plan=daily.ensure(runtime,db,uid,state,child['id'])
                    if not existing: generated+=1
                    if plan.get('items'): plans.append(plan)
                except Exception:
                    db.conn.rollback(); errors+=1
            if not pref.get('push') or not webpush or now.hour<hour: continue
            unread=[p for p in plans if not p['viewed']]
            second=pref.get('secondReminder',False) and now.hour>=hour+6
            slot=1 if second else 0
            birthday=None; tip=None
            if not slot:
                birthday=next((c for c in birthdays if not db.query('SELECT 1 FROM mh_guidance_delivery WHERE user_id=? AND child_id=? AND topic=?',(uid,c['childId'],'birthday-'+str(now.year))).fetchone()),None)
                # Priority, closing age window, then fair rotation across children.
                candidates=[]
                for child in daily.children(state):
                    profile=child['data'].get('profile') or {}
                    if profile.get('stage')!='child':continue
                    age=daily.age(profile,now.date().isoformat())
                    last=db.query('SELECT COALESCE(MAX(sent_at),0) FROM mh_guidance_delivery WHERE user_id=? AND child_id=?',(uid,child['id'])).fetchone()[0]
                    for card in daily.guidance.cards(age):
                        if not db.query('SELECT 1 FROM mh_guidance_delivery WHERE user_id=? AND child_id=? AND topic=?',(uid,child['id'],card['id'])).fetchone():
                            candidates.append((card['priority'],card['maxMonths']-age,last,child,card));break
                if candidates:
                    _,_,_,child,card=min(candidates,key=lambda item:item[:3]);tip=(child,card)
                    # A birthday never displaces an unsent safety or current-stage tip.
                    # The in-app greeting and gift still appear on the birthday.
                    if card['priority']<=1:birthday=None
            if not unread and not birthday and not tip:continue
            # A late run delivers at most one notification, never catches up both slots.
            day=now.date().isoformat(); start=int(now.replace(hour=0,minute=0,second=0,microsecond=0).timestamp())
            old_count=db.query('SELECT COUNT(*) FROM mh_delivery WHERE user_id=? AND sent_at>=?',(uid,start)).fetchone()[0]
            count=db.query('SELECT COUNT(*) FROM mh_daily_push WHERE user_id=? AND day=?',(uid,day)).fetchone()[0]
            if old_count+count>=2: continue
            if now.hour != hour+(6 if slot else 0): continue
            subscription=db.query('SELECT endpoint_hash,encrypted_subscription FROM mh_push WHERE user_id=? ORDER BY endpoint_hash LIMIT 1',(uid,)).fetchone()
            if not subscription: continue
            claim=db.query('INSERT INTO mh_daily_push VALUES(?,?,?,?) ON CONFLICT(user_id,day,slot) DO NOTHING',(uid,day,slot,int(time.time())))
            if claim.rowcount!=1:
                db.conn.commit();continue
            lines=['Сегодня есть три коротких занятия. Выберите подходящее, когда будет удобно.', 'Новая подборка игр уже готова. Посмотрите, что подойдёт сегодня.', 'Идеи для времени вместе ждут в «Моём дне». Можно выбрать всего одну.']
            body='Подборка ещё доступна. Возможно, сейчас найдётся время для одной игры.' if slot else lines[now.toordinal()%len(lines)]
            path={'child':unread[0]['childId'],'day':day} if unread else {}
            kind='daily-plan'
            if birthday:
                name=' '.join(birthday['name'].split())[:32]
                body=f'{name}: с днём рождения! Идея для тёплого семейного праздника уже в чате.'
                if app._birthdays.paid_access(db,uid):body=f'{name}: с днём рождения! Вам начислены 5 дополнительных AI-ответов. Откройте поздравление.'
                kind='birthday';path={'tab':'chat','child':birthday['childId'],'birthday':day}
                db.query('INSERT INTO mh_guidance_delivery VALUES(?,?,?,?) ON CONFLICT(user_id,child_id,topic) DO NOTHING',(uid,birthday['childId'],'birthday-'+str(now.year),int(time.time())))
                # One family greeting includes all birthday gifts; no second congratulation later.
                for c in birthdays:
                    db.query('INSERT INTO mh_guidance_delivery VALUES(?,?,?,?) ON CONFLICT(user_id,child_id,topic) DO NOTHING',(uid,c['childId'],'birthday-'+str(now.year),int(time.time())))
            elif tip:
                child,card=tip;kind='age-guidance';body=daily.guidance.push_text(card,child['data']['profile'])
                path={'tab':'chat','child':child['id'],'topic':card['id']}
                db.query('INSERT INTO mh_guidance_delivery VALUES(?,?,?,?) ON CONFLICT(user_id,child_id,topic) DO NOTHING',(uid,child['id'],card['id'],int(time.time())))
            db.conn.commit()
            try:
                webpush(subscription_info=app.unseal(subscription[1]),data=json.dumps({'type':kind,'body':body,'path':'/cabinet?'+urlencode(path),'eventId':f'daily-{day}-{slot}'}),vapid_private_key=os.environ['VAPID_PRIVATE_KEY'],vapid_claims={'sub':os.environ['VAPID_SUBJECT']},timeout=8)
                delivered+=1
            except Exception as exc:
                # Keep an ambiguous attempt claimed: retrying can cause duplicate notifications.
                if getattr(getattr(exc,'response',None),'status_code',None) in (404,410):
                    db.query('DELETE FROM mh_push WHERE endpoint_hash=? AND user_id=?',(subscription[0],uid)); db.conn.commit()
                errors+=1
    return {'generated':generated,'delivered':delivered,'errors':errors}

if __name__=='__main__':
    spec=importlib.util.spec_from_file_location('daily_app',Path(__file__).with_name('index.py'))
    app=importlib.util.module_from_spec(spec); spec.loader.exec_module(app)
    db=app.DB()
    try: print(json.dumps(run(app,db)))
    finally: db.close()
