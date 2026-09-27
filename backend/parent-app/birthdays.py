"""Birthday gifts require server-verified paid access, never client profile flags."""
import calendar
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

def today_for(state):
    return datetime.now(ZoneInfo(state.get('preferences',{}).get('timezone','Europe/Moscow'))).date()

def children_today(state,today=None):
    today=today or today_for(state)
    profiles=[(state.get('activeChildId','primary'),state.get('profile'))]
    profiles += [(c['id'],c.get('data',{}).get('profile')) for c in state.get('children',[])]
    found={}
    for cid,p in profiles:
        if not p or p.get('stage')!='child':continue
        born=date.fromisoformat(p['birthDate'])
        anniversary=date(today.year,born.month,min(born.day,calendar.monthrange(today.year,born.month)[1]))
        if today==anniversary and today.year>born.year:
            found[cid]={'childId':cid,'name':p.get('childName') or 'Ваш ребёнок','years':today.year-born.year}
    return list(found.values())

def paid_access(db,uid,now=None):
    now=int(time.time()) if now is None else now
    return db.query('SELECT period_key,answer_limit FROM mh_paid_access WHERE user_id=? AND starts_at<=? AND ends_at>?',(uid,now,now)).fetchone()

def grant(db,uid,state,today=None):
    today=today or today_for(state)
    children=children_today(state,today)
    if paid_access(db,uid):
        for child in children:
            db.query('INSERT INTO mh_birthday_gifts(user_id,child_id,year,remaining) VALUES(?,?,?,5) ON CONFLICT(user_id,child_id,year) DO NOTHING',(uid,child['childId'],today.year))
    return children

def balance(db,uid):
    return int(db.query('SELECT COALESCE(SUM(remaining),0) FROM mh_birthday_gifts WHERE user_id=?',(uid,)).fetchone()[0])

def consume(db,uid):
    row=db.query('SELECT child_id,year FROM mh_birthday_gifts WHERE user_id=? AND remaining>0 ORDER BY year,child_id LIMIT 1',(uid,)).fetchone()
    return bool(row and db.query('UPDATE mh_birthday_gifts SET remaining=remaining-1 WHERE user_id=? AND child_id=? AND year=? AND remaining>0',(uid,*row)).rowcount==1)

def summary(db,uid,state):
    children=grant(db,uid,state)
    paid=bool(paid_access(db,uid))
    return {'children':children,'giftPerChild':5 if paid else 0,'giftRemaining':balance(db,uid) if paid else 0}
