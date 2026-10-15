"""Encrypted, child-scoped records and explicitly granted family access."""
import hashlib
import json
import re
import secrets
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
import care_summary

KINDS = {'sleep','wake','feeding','food','achievement','mood'}

def version(records):
    # A snapshot identifier, not a copy of private journal contents.
    canonical=json.dumps(sorted(records,key=lambda r:r['id']),sort_keys=True,ensure_ascii=False,separators=(',',':'))
    return hashlib.sha256(canonical.encode()).hexdigest()

def current_version(app,db,uid,cid):
    rows=db.query('SELECT encrypted_data FROM mh_care_records WHERE owner_id=? AND child_id=?',(uid,cid)).fetchall()
    return version([app.unseal(r[0]) for r in rows])

def child(app, db, uid, cid):
    row=db.query('SELECT encrypted_data FROM mh_state WHERE user_id=?',(uid,)).fetchone()
    state=app.unseal(row[0]) if row else {}
    data=state if state.get('activeChildId','primary')==cid else next((c['data'] for c in state.get('children',[]) if c['id']==cid),None)
    if not data or not data.get('profile'): raise app.AppError(404,'Профиль ребёнка не найден.')
    return data

def initialize(db):
    db.query('CREATE TABLE IF NOT EXISTS mh_care_records (owner_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE, child_id TEXT NOT NULL, id TEXT NOT NULL, encrypted_data TEXT NOT NULL, PRIMARY KEY(owner_id,child_id,id))')
    db.query('CREATE TABLE IF NOT EXISTS mh_family_access (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE, child_id TEXT NOT NULL, guest_id TEXT REFERENCES mh_users(id) ON DELETE CASCADE, token_hash TEXT UNIQUE, expires_at BIGINT NOT NULL, permission TEXT NOT NULL)')
    db.query('CREATE TABLE IF NOT EXISTS mh_care_authorship (owner_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE, child_id TEXT NOT NULL, record_id TEXT NOT NULL, encrypted_data TEXT NOT NULL, PRIMARY KEY(owner_id,child_id,record_id))')

def access(app,db,uid,data):
    owner=data.get('ownerId') or uid; cid=data.get('childId','primary')
    if not isinstance(owner,str) or not isinstance(cid,str) or not re.fullmatch(r'[a-zA-Z0-9-]{1,100}',cid):raise app.AppError(400,'Неверный профиль.')
    permission='owner'
    if owner!=uid:
        row=db.query('SELECT permission FROM mh_family_access WHERE owner_id=? AND child_id=? AND guest_id=?',(owner,cid,uid)).fetchone()
        if not row:raise app.AppError(403,'Доступ к этому ребёнку не предоставлен.')
        permission=row[0]
    return owner,cid,permission,child(app,db,owner,cid)

def action(app,db,uid,data):
    initialize(db)
    name=data['action']
    if name=='family-list':
        rows=db.query('SELECT id,owner_id,child_id,guest_id,permission,expires_at FROM mh_family_access WHERE owner_id=? OR guest_id=?',(uid,uid)).fetchall()
        return {'items':[{'id':r[0],'ownerId':r[1],'childId':r[2],'guestId':r[3],'permission':r[4],'expiresAt':r[5], 'isOwner':r[1]==uid, 'childName':child(app,db,r[1],r[2])['profile'].get('childName','Ребёнок')} for r in rows]}
    if name=='family-accept':
        token=data.get('code','')
        if not isinstance(token,str) or not 20<=len(token)<=100:raise app.AppError(400,'Проверьте код приглашения.')
        digest=hashlib.sha256(token.encode()).hexdigest()
        row=db.query('SELECT id,owner_id,child_id FROM mh_family_access WHERE token_hash=? AND guest_id IS NULL AND expires_at>?',(digest,int(time.time()))).fetchone()
        if not row or row[1]==uid:raise app.AppError(400,'Приглашение истекло или уже использовано.')
        if db.query('SELECT id FROM mh_family_access WHERE owner_id=? AND child_id=? AND guest_id=?',(row[1],row[2],uid)).fetchone():raise app.AppError(409,'У вас уже есть доступ к этому ребёнку.')
        cur=db.query('UPDATE mh_family_access SET guest_id=?,token_hash=NULL WHERE id=? AND guest_id IS NULL',(uid,row[0]))
        if cur.rowcount!=1:raise app.AppError(409,'Приглашение уже использовано.')
        return {'ok':True}
    if name=='family-revoke':
        db.query('DELETE FROM mh_family_access WHERE id=? AND (owner_id=? OR guest_id=?)',(data.get('id'),uid,uid))
        return {'ok':True}
    owner,cid,permission,state=access(app,db,uid,data)
    if db.sqlite:
        db.query('UPDATE mh_state SET revision=revision WHERE user_id=?',(owner,))
    else:
        db.query('SELECT user_id FROM mh_state WHERE user_id=? FOR UPDATE',(owner,)).fetchone()
    owner,cid,permission,state=access(app,db,uid,data)
    if name=='family-invite':
        if permission!='owner':raise app.AppError(403,'Приглашать может владелец профиля.')
        if data.get('permission') not in ('read','write'):raise app.AppError(400,'Выберите права доступа.')
        count=db.query('SELECT COUNT(*) FROM mh_family_access WHERE owner_id=?',(uid,)).fetchone()[0]
        if count>=20:raise app.AppError(400,'Удалите ненужные приглашения: максимум 20.')
        token=secrets.token_urlsafe(24); ident=secrets.token_hex(16)
        db.query('INSERT INTO mh_family_access VALUES(?,?,?,NULL,?,?,?)',(ident,uid,cid,hashlib.sha256(token.encode()).hexdigest(),int(time.time())+86400,data['permission']))
        return {'code':token,'id':ident}
    rows=db.query('SELECT encrypted_data FROM mh_care_records WHERE owner_id=? AND child_id=?',(owner,cid)).fetchall()
    records=[app.unseal(r[0]) for r in rows]
    # Parent feelings are private even when child care has been shared.
    if permission!='owner':records=[r for r in records if r['kind']!='mood']
    if name=='care-list':
        care=state.get('care') or {}
        daily=[]
        if state['profile']['stage']=='child':
            spec=__import__('importlib.util',fromlist=['util']);path=__import__('pathlib').Path(__file__).with_name('daily.py');sp=spec.spec_from_file_location('care_daily',path);mod=spec.module_from_spec(sp);sp.loader.exec_module(mod)
            day=mod.local_now(state).date().isoformat()
            row=db.query('SELECT encrypted_data FROM mh_daily WHERE user_id=? AND child_id=? AND day=?',(owner,cid,day)).fetchone()
            if row:
                plan=app.unseal(row[0]);months=mod.age(state['profile'],day)
                if plan.get('catalogVersion')==mod.catalog.VERSION and plan.get('ageMonths')==months:
                    daily=plan.get('items',[])
        authors={r[0]:app.unseal(r[1]) for r in db.query('SELECT record_id,encrypted_data FROM mh_care_authorship WHERE owner_id=? AND child_id=?',(owner,cid)).fetchall() if any(v['id']==r[0] for v in records)}
        return {'daily':daily,'records':sorted(records,key=lambda r:r['at'],reverse=True),'authors':authors,'contextVersion':version(records),
                'summary':care_summary.summary(records,state.get('preferences',{}).get('timezone') or 'Europe/Moscow'),
                'profile':{'childName':state['profile'].get('childName',''),'stage':state['profile']['stage'],'birthDate':state['profile']['birthDate']},'permission':permission,'achievements':care.get('achievements',[]),'appointments':care.get('appointments',[]) if permission=='owner' else []}
    if permission=='read':raise app.AppError(403,'Предоставлен только просмотр.')
    if name=='care-import':
        if permission!='owner':raise app.AppError(403,'Импорт доступен владельцу профиля.')
        batch=data.get('records')
        if not isinstance(batch,list) or not 1<=len(batch)<=100:raise app.AppError(400,'Выберите от 1 до 100 записей.')
        if data.get('contextVersion')!=version(records):raise app.AppError(409,'Дневник изменился. Откройте предпросмотр ещё раз.')
        keys=('kind','at','end','side','value','note','sleepType','wakeType','settlingAt','feeling')
        def fingerprint(r):
            value={k:r.get(k,'') for k in keys}
            for key in ('at','end','settlingAt'):
                parsed=care_summary.parse(value[key])
                if parsed is not None:value[key]=parsed.astimezone(timezone.utc).isoformat()
            return json.dumps(value,sort_keys=True,ensure_ascii=False)
        known={fingerprint(r) for r in records}; added=[]; skipped=0
        for record in batch:
            if not isinstance(record,dict) or record.get('kind') not in ('sleep','wake','feeding','food','achievement'):
                raise app.AppError(400,'Импортируйте только записи ребёнка.')
            if fingerprint(record) in known:skipped+=1;continue
            fresh={**record,'id':secrets.token_hex(16)}
            action(app,db,uid,{**data,'action':'care-put','record':fresh})
            added.append(fresh['id']);known.add(fingerprint(record))
        return {'added':len(added),'skipped':skipped,'ids':added}
    if name=='care-delete':
        if permission!='owner':raise app.AppError(403,'Удалять записи может владелец.')
        db.query('DELETE FROM mh_care_records WHERE owner_id=? AND child_id=? AND id=?',(owner,cid,data.get('id')))
        db.query('DELETE FROM mh_care_authorship WHERE owner_id=? AND child_id=? AND record_id=?',(owner,cid,data.get('id')))
        return {'ok':True}
    if name=='care-put':
        r=data.get('record')
        if not isinstance(r,dict) or set(r)-{'id','kind','at','end','note','value','side','sleepType','settlingAt','feeling','wakeType'}:raise app.AppError(400,'Проверьте запись.')
        if not isinstance(r.get('id'),str) or not re.fullmatch(r'[a-zA-Z0-9-]{1,100}',r['id']) or r.get('kind') not in KINDS:raise app.AppError(400,'Проверьте запись.')
        if r['kind']=='mood' and permission!='owner':raise app.AppError(403,'Самочувствие родителя приватно.')
        if r['kind']!='mood' and state['profile']['stage']!='child':raise app.AppError(400,'Этот дневник доступен после рождения ребёнка.')
        for key in ('at','end'):
            if key=='end' and not r.get(key):continue
            try:
                v=datetime.fromisoformat(r.get(key,'').replace('Z','+00:00'))
                if v.tzinfo is None or v.timestamp()>time.time()+60:raise ValueError()
            except (ValueError,TypeError,AttributeError):raise app.AppError(400,'Проверьте время записи.')
        if r.get('end') and datetime.fromisoformat(r['end'].replace('Z','+00:00'))<datetime.fromisoformat(r['at'].replace('Z','+00:00')):raise app.AppError(400,'Окончание раньше начала.')
        if not isinstance(r.get('note',''),str) or len(r.get('note',''))>500:raise app.AppError(400,'Запись до 500 символов.')
        if not isinstance(r.get('value',''),str) or len(r.get('value',''))>120 or r.get('side','') not in ('','left','right','bottle'):raise app.AppError(400,'Проверьте поля записи.')
        if r.get('sleepType','') not in ('','day','night') or r.get('wakeType','') not in ('','morning','night') or r.get('feeling','') not in ('','calm','fussy','crying'):
            raise app.AppError(400,'Проверьте вид сна и самочувствие.')
        if r.get('settlingAt'):
            try:
                settling=datetime.fromisoformat(r['settlingAt'].replace('Z','+00:00'))
                start=datetime.fromisoformat(r['at'].replace('Z','+00:00'))
                if settling.tzinfo is None or not 0 <= (start-settling).total_seconds() <= 86400:raise ValueError()
            except (ValueError,TypeError,AttributeError):raise app.AppError(400,'Начало укладывания должно быть до засыпания, в пределах суток.')
        if r['kind']=='sleep':
            start=datetime.fromisoformat(r['at'].replace('Z','+00:00')).timestamp()
            end=datetime.fromisoformat(r['end'].replace('Z','+00:00')).timestamp() if r.get('end') else float('inf')
            if end<=start:raise app.AppError(400,'Окончание сна должно быть позже начала.')
            for x in records:
                if x['kind']!='sleep' or x['id']==r['id']:continue
                a=datetime.fromisoformat(x['at'].replace('Z','+00:00')).timestamp()
                b=datetime.fromisoformat(x['end'].replace('Z','+00:00')).timestamp() if x.get('end') else float('inf')
                if start<b and a<end:raise app.AppError(409,'Этот сон пересекается с другой записью. Исправьте время или завершите текущий сон.')
        exists=db.query('SELECT encrypted_data FROM mh_care_records WHERE owner_id=? AND child_id=? AND id=?',(owner,cid,r['id'])).fetchone()
        if exists:
            previous=app.unseal(exists[0])
            if previous['kind']!=r['kind'] or (previous['at']!=r['at'] and r['kind'] not in ('sleep','wake','feeding')):raise app.AppError(409,'Нельзя менять тип или начало записи.')
        elif len(rows)>=1500:raise app.AppError(400,'Достигнут лимит 1500 записей. Выгрузите историю и удалите ненужное.')
        if r['kind']=='sleep' and not r.get('end') and any(x['kind']=='sleep' and not x.get('end') and x['id']!=r['id'] for x in records):raise app.AppError(409,'Сон уже запущен. Обновите записи.')
        if r['kind']=='feeding' and r.get('value')=='Таймер кормления' and not r.get('end') and any(x['kind']=='feeding' and x.get('value')=='Таймер кормления' and not x.get('end') and x['id']!=r['id'] for x in records):raise app.AppError(409,'Таймер кормления уже запущен. Обновите записи.')
        db.query('INSERT INTO mh_care_records VALUES(?,?,?,?) ON CONFLICT(owner_id,child_id,id) DO UPDATE SET encrypted_data=excluded.encrypted_data',(owner,cid,r['id'],app.seal(r)))
        author_row=db.query('SELECT encrypted_data FROM mh_care_authorship WHERE owner_id=? AND child_id=? AND record_id=?',(owner,cid,r['id'])).fetchone()
        role='Владелец профиля' if permission=='owner' else 'Приглашённый взрослый'
        author=app.unseal(author_row[0]) if author_row else {'createdByRole':'Не сохранено для прежней записи' if exists else role}
        author.update(updatedByRole=role,updatedAt=datetime.now(timezone.utc).isoformat())
        db.query('INSERT INTO mh_care_authorship VALUES(?,?,?,?) ON CONFLICT(owner_id,child_id,record_id) DO UPDATE SET encrypted_data=excluded.encrypted_data',(owner,cid,r['id'],app.seal(author)))
        return {'ok':True}
    raise app.AppError(400,'Неизвестное действие.')


def observations(app,db,uid,cid,limit=80,with_version=False):
    rows=db.query('SELECT encrypted_data FROM mh_care_records WHERE owner_id=? AND child_id=?',(uid,cid)).fetchall()
    records=sorted([app.unseal(r[0]) for r in rows],key=lambda r:r['at'],reverse=True)
    row=db.query('SELECT encrypted_data FROM mh_state WHERE user_id=?',(uid,)).fetchone()
    state=app.unseal(row[0]) if row else {}
    try: zone=ZoneInfo(state.get('preferences',{}).get('timezone') or 'Europe/Moscow')
    except (ZoneInfoNotFoundError,TypeError,ValueError): zone=ZoneInfo('Europe/Moscow')
    recent=care_summary.period(records,str(zone))
    result=[]
    for r in recent[:limit]:
        item={k:r.get(k,'') for k in ('kind','at','note','value','side','end','sleepType','settlingAt','feeling','wakeType')}
        for key in ('at','end','settlingAt'):
            if item[key]:item[key]=datetime.fromisoformat(item[key].replace('Z','+00:00')).astimezone(zone).isoformat()
        result.append(item)
    return (result,version(records)) if with_version else result
