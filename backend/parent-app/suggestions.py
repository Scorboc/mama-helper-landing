"""Anonymous weekly product ideas and one-person-one-vote ballots."""
import re
import secrets
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_PRIVATE=re.compile(r'(?:https?://|www\.|@\w+|[\w.+-]+@[\w.-]+\.\w+|(?:\+?7|8)[\s()\-]*\d{3}[\s()\-]*\d{3})',re.I)

def _now(runtime):
    supplied=getattr(runtime,'now',None)
    return supplied() if supplied else datetime.now(ZoneInfo('Europe/Moscow'))

def _week(day):return day.strftime('%G-W%V')

def _phase(day):return 'collecting' if day.weekday()<4 else 'voting'

def _previous_week(day):return _week(day-timedelta(days=7))

def _public(record):
    return {'id':record['id'],'title':record['title'],'detail':record.get('detail',''),'votes':record.get('votes',0)}

def _finalize(runtime,db,day):
    """Close the previous ballot and put every tied winner into the owner queue."""
    week=_previous_week(day)
    rows=db.query('''SELECT s.id,s.encrypted_data,s.status,s.created_at,COUNT(v.suggestion_id)
      FROM mh_product_suggestions s LEFT JOIN mh_suggestion_votes v
      ON v.suggestion_id=s.id AND v.ballot_week=s.week_id
      WHERE s.week_id=? AND s.status='open'
      GROUP BY s.id,s.encrypted_data,s.status,s.created_at ORDER BY s.created_at''',(week,)).fetchall()
    if not rows:return []
    top=max(int(row[4]) for row in rows)
    winners=[]
    for ident,encrypted,status,created,votes in rows:
        won=top>0 and int(votes)==top
        db.query('UPDATE mh_product_suggestions SET status=? WHERE id=?',('planned' if won else 'closed',ident))
        if won:
            data=runtime.unseal(encrypted);data.update(id=ident,votes=int(votes),week=week)
            winners.append(data)
            try:
                runtime.ops.document('task',{
                    'id':'idea'+ident,
                    'title':('Выбранная мамами идея: '+data['title'])[:160],
                    'text':('Итог голосования '+week+f': {votes} голос(ов).\n\n'+data.get('detail',''))[:5000],
                    'status':'new',
                })
            except Exception:
                # The encrypted product record remains the source of truth even
                # if the internal owner dashboard is temporarily unavailable.
                pass
    return winners

def _list(runtime,db,uid,day,new_winners=None):
    week=_week(day);phase=_phase(day)
    rows=db.query('''SELECT s.id,s.encrypted_data,s.owner_id,s.created_at,COUNT(v.suggestion_id)
      FROM mh_product_suggestions s LEFT JOIN mh_suggestion_votes v
      ON v.suggestion_id=s.id AND v.ballot_week=s.week_id
      WHERE s.week_id=? AND s.status='open'
      GROUP BY s.id,s.encrypted_data,s.owner_id,s.created_at ORDER BY s.created_at LIMIT 20''',(week,)).fetchall()
    items=[]
    for ident,encrypted,owner,created,votes in rows:
        data=runtime.unseal(encrypted)
        data.update(id=ident,votes=int(votes))
        items.append(_public(data))
    mine=db.query('SELECT suggestion_id FROM mh_suggestion_votes WHERE ballot_week=? AND user_id=?',(week,uid)).fetchone()
    own_count=db.query('SELECT COUNT(*) FROM mh_product_suggestions WHERE week_id=? AND owner_id=?',(week,uid)).fetchone()[0]
    prior=db.query("SELECT id,encrypted_data FROM mh_product_suggestions WHERE status='planned' ORDER BY created_at DESC LIMIT 3").fetchall()
    winners=[]
    for ident,encrypted in prior:
        item=runtime.unseal(encrypted);item.update(id=ident);winners.append(_public(item))
    return {
        'phase':phase,'week':week,'canSubmit':phase=='collecting' and own_count<3,
        'remainingSubmissions':max(0,3-int(own_count)),'items':items if phase=='voting' else [],
        'submissionCount':len(items),'myVote':mine[0] if mine else None,
        'winners':winners,'newWinnerCount':len(new_winners or []),
    }

def action(runtime,db,uid,data):
    day=_now(runtime)
    new_winners=_finalize(runtime,db,day)
    action=data.get('action')
    if action=='suggestion-list':return _list(runtime,db,uid,day,new_winners)
    if action=='suggestion-create':
        if _phase(day)!='collecting':raise runtime.AppError(400,'Сейчас идёт голосование. Новые идеи можно добавить с понедельника.')
        title=str(data.get('title') or '').strip();detail=str(data.get('detail') or '').strip()
        if not 10<=len(title)<=120 or len(detail)>800:raise runtime.AppError(400,'Заголовок: 10–120 знаков. Описание: до 800 знаков.')
        if _PRIVATE.search(title+' '+detail):raise runtime.AppError(400,'Уберите ссылки, контакты и личные данные. Идеи участвуют в общем голосовании.')
        week=_week(day)
        count=db.query('SELECT COUNT(*) FROM mh_product_suggestions WHERE week_id=? AND owner_id=?',(week,uid)).fetchone()[0]
        if count>=3:raise runtime.AppError(400,'На этой неделе уже добавлены три идеи.')
        ident=secrets.token_hex(12)
        db.query('INSERT INTO mh_product_suggestions VALUES(?,?,?,?,?,?)',(ident,uid,week,runtime.seal({'title':title,'detail':detail}),'open',int(time.time())))
        return _list(runtime,db,uid,day,new_winners)
    if action=='suggestion-vote':
        if _phase(day)!='voting':raise runtime.AppError(400,'Голосование открывается с пятницы по воскресенье.')
        ident=str(data.get('suggestionId') or '')
        if not re.fullmatch(r'[a-f0-9]{24}',ident):raise runtime.AppError(400,'Выберите идею из списка.')
        week=_week(day)
        candidate=db.query("SELECT id FROM mh_product_suggestions WHERE id=? AND week_id=? AND status='open'",(ident,week)).fetchone()
        if not candidate:raise runtime.AppError(400,'Этой идеи нет в текущем голосовании.')
        db.query('''INSERT INTO mh_suggestion_votes VALUES(?,?,?,?)
          ON CONFLICT(ballot_week,user_id) DO UPDATE SET suggestion_id=excluded.suggestion_id,created_at=excluded.created_at''',(week,uid,ident,int(time.time())))
        return _list(runtime,db,uid,day,new_winners)
    raise runtime.AppError(404,'Действие не найдено.')
