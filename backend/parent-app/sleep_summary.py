"""Deterministic sleep context. Gaps are not assumed to be confirmed wakefulness."""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

def summary(records, timezone_name='Europe/Moscow', now=None):
    now=now or datetime.now(timezone.utc)
    try: zone=ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError,TypeError): zone=ZoneInfo('Europe/Moscow')
    def dt(v): return datetime.fromisoformat(v.replace('Z','+00:00'))
    cutoff=datetime.combine(now.astimezone(zone).date()-timedelta(days=6),datetime.min.time(),zone)
    intervals=[];settling=[];count=0;ongoing=False
    for r in records:
        if r.get('kind')!='sleep':continue
        a=dt(r['at']);b=min(dt(r['end']),now) if r.get('end') else now
        if a>now or b<cutoff:continue
        count+=1;ongoing=ongoing or not r.get('end')
        if b>a:intervals.append((a,b,r.get('sleepType','unspecified')))
        if r.get('settlingAt'):
            minutes=round((a-dt(r['settlingAt'])).total_seconds()/60)
            if 0<=minutes<=1440:settling.append(minutes)
    days=[]
    for i in range(6,-1,-1):
        date=now.astimezone(zone).date()-timedelta(days=i)
        start=datetime.combine(date,datetime.min.time(),zone);end=start+timedelta(days=1)
        spans=sorted((max(a,start),min(b,end,now)) for a,b,_ in intervals if a<end and b>start)
        merged=[]
        for a,b in spans:
            if b<=a:continue
            if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
            else:merged.append((a,b))
        days.append({'date':str(date),'recordedSleepMinutes':round(sum((b-a).total_seconds()/60 for a,b in merged)),'episodesIntersectingDay':len(spans)})
    ordered=sorted(intervals)
    gaps=[round((b[0]-a[1]).total_seconds()/60) for a,b in zip(ordered,ordered[1:]) if b[0]>=a[1]]
    last_end=max((b for a,b,_ in intervals),default=None)
    total=round(sum((b-a).total_seconds()/60 for day in range(7)
                    for a,b in _merged_for_day(intervals,cutoff+timedelta(days=day),now)))
    return {'periodDays':7,'timezone':str(zone),'sleepRecords':count,'ongoing':ongoing,'days':days,
            'recordedSleepMinutesTotal':total,
            'gapsBetweenRecordedSleepsMinutes':gaps[-20:], 'settlingMinutes':settling[-20:],
            'lastRecordedSleepEnd':last_end.astimezone(zone).isoformat() if last_end and not ongoing else None,
            'rules':'При обсуждении сна: это неполные записи родителя, не подтверждённый полный режим. Промежутки между записями не доказывают бодрствование. Не назначай точное окно сна и не обещай сдвиг подъёма. Учитывай точный возраст, уточняй полноту дневника и время укладывания. При недостатке данных сообщи об этом. Описывай наблюдения с числами и датами, не выдумывай причины или календарные скачки. Предложи одно мягкое изменение и способ проверить результат.'}

def _merged_for_day(intervals,start,now):
    end=start+timedelta(days=1); merged=[]
    for a,b in sorted((max(a,start),min(b,end,now)) for a,b,_ in intervals if a<end and b>start):
        if b<=a:continue
        if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else:merged.append((a,b))
    return merged
