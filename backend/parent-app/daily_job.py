"""Notify from saved plans and reviewed age tips; never generate with AI."""
import importlib.util
import json
import os
import time
import calendar
import care_tools
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

def candidate_key(card, profile, last):
    """Safety, explicit milestones by calendar deadline, then existing rotation."""
    tier = 0 if card['priority'] == 0 else 1 if card.get('milestoneSkill') else 2
    born = date.fromisoformat(profile['birthDate'])
    total = born.year * 12 + born.month - 1 + card['maxMonths']
    year, month = divmod(total, 12)
    month += 1
    closes = date(year, month, min(born.day, calendar.monthrange(year, month)[1]))
    return tier, closes.toordinal(), last, card['priority']


def run(app, db, webpush=None, *, guidance_only=True):
    # Kept for caller compatibility; every background run is guidance-only.
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
            # Check consent, transport, schedule and previous attempts before delivery.
            if not pref.get('push') or not webpush: continue
            slot=0 if now.hour==hour else 1 if pref.get('secondReminder',False) and now.hour==hour+6 else None
            if slot is None: continue
            day=now.date().isoformat(); start=int(now.replace(hour=0,minute=0,second=0,microsecond=0).timestamp())
            old_count=db.query('SELECT COUNT(*) FROM mh_delivery WHERE user_id=? AND sent_at>=?',(uid,start)).fetchone()[0]
            count=db.query('SELECT COUNT(*) FROM mh_daily_push WHERE user_id=? AND day=?',(uid,day)).fetchone()[0]
            if old_count+count>=2 or db.query('SELECT 1 FROM mh_daily_push WHERE user_id=? AND day=? AND slot=?',(uid,day,slot)).fetchone(): continue
            subscription=db.query('SELECT endpoint_hash,encrypted_subscription FROM mh_push WHERE user_id=? ORDER BY endpoint_hash LIMIT 1',(uid,)).fetchone()
            if not subscription: continue
            plans=[]
            for child in daily.children(state):
                if (child['data'].get('profile') or {}).get('stage')!='child': continue
                try:
                    existing=db.query('SELECT encrypted_data,viewed FROM mh_daily WHERE user_id=? AND child_id=? AND day=?',(uid,child['id'],day)).fetchone()
                    # Only current saved plans are eligible for notification.
                    if not existing: continue
                    plan=app.unseal(existing[0])
                    months=daily.age(child['data']['profile'],day)
                    if plan.get('ageMonths')!=months or plan.get('catalogVersion')!=daily.catalog.VERSION: continue
                    key=app.digest(json.dumps(child['data']['profile'],sort_keys=True,ensure_ascii=False))
                    if plan.get('profileKey')!=key: continue
                    plan={**plan,'childId':child['id'],'viewed':bool(existing[1])}
                    if plan.get('items'): plans.append(plan)
                except Exception:
                    db.conn.rollback(); errors+=1
            unread=[p for p in plans if not p['viewed']]
            birthday=None; tip=None
            if not slot:
                birthday=next((c for c in birthdays if not db.query('SELECT 1 FROM mh_guidance_delivery WHERE user_id=? AND child_id=? AND topic=?',(uid,c['childId'],'birthday-'+str(now.year))).fetchone()),None)
                # Priority, closing age window, then fair rotation across children.
                candidates=[]
                for child in daily.children(state):
                    profile=child['data'].get('profile') or {}
                    if profile.get('stage')!='child':continue
                    try: age=daily.age(profile,day)
                    except (ValueError,KeyError,TypeError): continue
                    _,feedback=daily.history(runtime,db,uid,child['id'],day)
                    excluded={str(f.get('baseId') or f.get('itemId') or f.get('id') or '').split('@')[0] for f in feedback if f.get('kind')=='replace' and f.get('reason') in ('dislike','health')}
                    last=db.query('SELECT COALESCE(MAX(sent_at),0) FROM mh_guidance_delivery WHERE user_id=? AND child_id=?',(uid,child['id'])).fetchone()[0]
                    try:
                        records, owned_state = care_tools.milestone_records(app,db,uid,child['id'])
                    except Exception:
                        # A failed read never means "unmarked".
                        db.conn.rollback(); errors+=1
                        records=owned_state=None
                    for card in sorted(daily.guidance.cards(age),key=lambda c:candidate_key(c,profile,last)):
                        if card.get('baseId') in excluded: continue
                        if profile.get('health') and card.get('area') in ('Движение','Координация'): continue
                        skill=daily.guidance.mark_skill(card)
                        if skill and (records is None or care_tools.marked_milestone(records,owned_state,skill)):continue
                        if not db.query('SELECT 1 FROM mh_guidance_delivery WHERE user_id=? AND child_id=? AND topic=?',(uid,child['id'],card['id'])).fetchone():
                            candidates.append((candidate_key(card,profile,last),child,card));break
                if candidates:
                    _,child,card=min(candidates,key=lambda item:item[0]);tip=(child,card)
                    # A birthday never displaces an unsent safety or current-stage tip.
                    # The in-app greeting and gift still appear on the birthday.
                    if card['priority']<=1:birthday=None
            if not unread and not birthday and not tip:continue
            if tip and daily.guidance.mark_skill(tip[1]):
                # Recheck after selection, before claiming the existing slot.
                try:
                    records,owned_state=care_tools.milestone_records(app,db,uid,tip[0]['id'])
                    if care_tools.marked_milestone(records,owned_state,daily.guidance.mark_skill(tip[1])):continue
                    if owned_state['profile'].get('health') and tip[1].get('area')=='Движение':continue
                    if owned_state['profile'].get('stage')!='child':continue
                    current_age=daily.age(owned_state['profile'],day)
                    if not tip[1]['minMonths']<=current_age<tip[1]['maxMonths']:continue
                except Exception:
                    db.conn.rollback();errors+=1;continue
            # A late run delivers at most one notification, never catches up both slots.
            claim=db.query('INSERT INTO mh_daily_push VALUES(?,?,?,?) ON CONFLICT(user_id,day,slot) DO NOTHING',(uid,day,slot,int(time.time())))
            if claim.rowcount!=1:
                db.conn.commit();continue
            lines=['Сегодня есть три коротких занятия. Выберите подходящее, когда будет удобно.', 'Новая подборка игр уже готова. Посмотрите, что подойдёт сегодня.', 'Идеи для времени вместе ждут в «Моём дне». Можно выбрать всего одну.']
            body='Подборка ещё доступна. Возможно, сейчас найдётся время для одной игры.' if slot else lines[now.toordinal()%len(lines)]
            path={'child':unread[0]['childId'],'day':day} if unread else {}
            kind='daily-plan'
            topics=[]
            if birthday:
                body='Семейное поздравление и идея для тёплого праздника уже в чате.'
                if app._birthdays.paid_access(db,uid):body='Вам начислены 5 дополнительных AI-ответов в подарок. Поздравление ждёт в чате.'
                kind='birthday';path={'tab':'chat','child':birthday['childId'],'birthday':day}
                # One family greeting includes all birthday gifts; no second congratulation later.
                topics=[(c['childId'],'birthday-'+str(now.year)) for c in birthdays]
            elif tip:
                child,card=tip;kind='age-guidance';body=daily.guidance.push_text(card,child['data']['profile'])
                path={'tab':'chat','child':child['id'],'topic':card['id']}
                skill=daily.guidance.mark_skill(card)
                if skill:path={'mark':skill,'child':child['id']}
                topics=[(child['id'],card['id'])]
            db.conn.commit()
            try:
                webpush(subscription_info=app.unseal(subscription[1]),data=json.dumps({'type':kind,'body':body,'path':'/cabinet?'+urlencode(path),'eventId':f'daily-{day}-{slot}'}),vapid_private_key=os.environ['VAPID_PRIVATE_KEY'],vapid_claims={'sub':os.environ['VAPID_SUBJECT']},timeout=8)
                # Accepted by the push service is different from a confirmed view.
                # Failed topics remain eligible tomorrow, while today's attempt
                # stays claimed to avoid duplicates after an ambiguous timeout.
                for cid,topic in topics:
                    db.query('INSERT INTO mh_guidance_delivery VALUES(?,?,?,?) ON CONFLICT(user_id,child_id,topic) DO NOTHING',(uid,cid,topic,int(time.time())))
                db.conn.commit()
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
    try: print(json.dumps(run(app,db,guidance_only=True)))
    finally: db.close()
