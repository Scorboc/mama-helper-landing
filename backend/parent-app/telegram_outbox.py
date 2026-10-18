"""Owner notifications: fixed templates and aggregates only, durable local outbox."""
from contextlib import closing
import json, re, socket, sqlite3, time, urllib.error, urllib.request
from pathlib import Path
from cryptography.fernet import Fernet

TOPICS={
 'technical':'Проверить технические ошибки сайта и ИИ',
 'tone':'Улучшить понятность и поддерживающий тон ответов',
 'age_conflict':'Проверить соответствие рекомендаций возрасту',
 'other_profile':'Проверить границы активного профиля',
 'stale_diary':'Проверить учёт исправленного дневника',
 'unclear_action':'Сделать следующий шаг в ответе понятнее',
 'safety_signal':'Локально проверить сигналы небезопасных ответов',
 'repetition':'Уменьшить повторение отвергнутых рекомендаций',
 'internal_fields':'Убрать технические поля из обычных ответов',
 'feature_request':'Рассмотреть предложения новых функций',
 'negative_unspecified':'Уточнить причины отрицательных оценок',
 'unreadable':'Проверить чтение сохранённых отзывов',
}

def config(root):
    path=root/'telegram-settings.enc'
    if not path.exists():return None
    value=json.loads(Fernet((root/'backup.key').read_bytes().strip()).decrypt(path.read_bytes()))
    if value.get('username','').lower()!='momf1_bot' or not re.fullmatch(r'\d{6,15}:[A-Za-z0-9_-]{25,80}',value.get('botToken','')):raise ValueError('telegram-config-invalid')
    if not str(value.get('chatId','')).isdigit() or int(value['chatId'])<=0:raise ValueError('private-chat-required')
    if type(value.get('enabledAt')) is not int or value['enabledAt']<=0:raise ValueError('enabled-time-required')
    return value

def database(root):
    db=sqlite3.connect(root/'telegram-outbox.sqlite',timeout=20)
    db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,kind TEXT,body TEXT,priority INTEGER,created INTEGER,state TEXT,attempts INTEGER DEFAULT 0,next_at INTEGER DEFAULT 0,started INTEGER,message_id INTEGER,error_code TEXT)')
    db.commit();return db

def put(root,key,kind,text,priority=10):
    # Only callers in this module construct text. There is no arbitrary-text HTTP API.
    with closing(database(root)) as db:
        db.execute("INSERT OR IGNORE INTO messages(id,kind,body,priority,created,state) VALUES(?,?,?,?,?,'queued')",(key,kind,text[:3500],priority,int(time.time())));db.commit()

def number(value):
    return min(max(value,0),100000000) if type(value) is int else 0

def collect(root):
    cfg=config(root)
    if not cfg:return {'configured':False}
    since=cfg['enabledAt']
    collect_runs(root,since)
    import telegram_billing
    telegram_billing.collect(root)
    import proxy_balance
    proxy_balance.collect(root)
    # Backstop for failures of the error handler itself: metadata only.
    n8n=root/'state/.n8n/database.sqlite'
    if n8n.exists():
        with closing(sqlite3.connect('file:'+n8n.as_posix()+'?mode=ro',uri=True)) as db:
            for workflow,execution,stamp in db.execute("SELECT e.workflowId,e.id,CAST(strftime('%s',e.startedAt) AS INTEGER) FROM execution_entity e JOIN workflow_entity w ON w.id=e.workflowId WHERE w.active=1 AND e.status IN ('error','crashed') AND CAST(strftime('%s',e.startedAt) AS INTEGER)>=?",(since,)):
                if re.fullmatch(r'mamaLocal\d{2}',workflow):put(root,f'error:{workflow}:{stamp//1800}','error',f'MAMA: ошибка схемы {workflow}.\nЗапуск: {number(execution)}. Подробности доступны локально.',100)
    journal=root/'automation-journal.sqlite'
    if journal.exists():
        with closing(sqlite3.connect('file:'+journal.as_posix()+'?mode=ro',uri=True)) as db:
            for workflow,execution,stamp in db.execute('SELECT workflow,execution,at FROM incidents WHERE at>=?',(since,)):
                if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',workflow) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',execution):continue
                put(root,f'error:{workflow}:{stamp//1800}','error',f'MAMA: ошибка автоматизации\nСхема: {workflow}\nЗапуск: {execution}\nПодробности — в локальном n8n на компьютере.\nПовторы одной схемы объединяются на 30 минут.',100)
    reports=root/'reports'
    for path in sorted(reports.glob('*.json')) if reports.exists() else []:
        if not re.fullmatch(r'(daily|weekly)-\d{8}\.json',path.name):continue
        try:
            data=json.loads(path.read_text(encoding='utf-8'))
            from datetime import datetime
            stamp=int(datetime.fromisoformat(data['generatedAt']).timestamp())
            if stamp<since or data.get('method')!='deterministic-aggregate-rules-not-ai':continue
            summary=data.get('summary',{});ai=summary.get('ai',[])
            calls=sum(number(r.get('calls')) for r in ai)
            errors=sum(number(r.get('calls')) for r in ai if r.get('status')!='ok')
            proposals=data.get('proposals',[])
            title='Недельный обзор' if path.name.startswith('weekly') else 'Ежедневный отчёт'
            text=f'MAMA: {title}\nВызовов ИИ за отчётный период: {calls}\nС техническими ошибками: {errors}\nПредложений для проверки: {len(proposals)}\nПереписка и сведения о детях не передаются.'
            put(root,'report:'+path.stem,'report',text)
            ideas=[]
            if errors:ideas.append('• Проверить причины технических ошибок ИИ.')
            if any(type(r.get('averageMs')) in (int,float) and r['averageMs']>15000 for r in ai):ideas.append('• Измерить и сократить ожидание ответа.')
            if number(summary.get('feedbackCounts',{}).get('unsafe')):ideas.append('• Локально проверить сигналы небезопасных ответов.')
            if ideas:
                put(root,'ideas:'+path.stem,'proposal','MAMA: предложения для проверки\n'+'\n'.join(ideas)+'\nИзменения требуют вашего решения; автоматически не применяются.',20)
                import telegram_reviews
                telegram_reviews.offer(root,'aggregate:'+path.stem,'Проверить сигналы отчёта',
                    f'За период: {calls} вызовов ИИ, {errors} технических ошибок. Это агрегаты, причины ещё не установлены.',
                    'Проверить локально сигналы отчёта: '+ ' '.join(ideas) + ' Подтвердить причины синтетическими тестами, затем предложить исправления.')
        except (ValueError,KeyError,TypeError):continue
    feedback=root.parent/'local-runtime/feedback-review/review.sqlite3'
    if feedback.exists():
        with closing(sqlite3.connect('file:'+feedback.as_posix()+'?mode=ro',uri=True)) as db:
            for ident,report in db.execute("SELECT id,report FROM review_runs WHERE status='success' AND created>=?",(since,)):
                try:
                    proposals=json.loads(report)['proposals']
                    topics=[TOPICS[p['category']] for p in proposals if p.get('category') in TOPICS]
                    if topics and re.fullmatch(r'[0-9a-f]{32}',ident):
                        put(root,'feedback:'+ident,'proposal','MAMA: предложения по отзывам\n'+'\n'.join('• '+t for t in topics[:3])+'\nЭто сигналы для проверки, не доказанные ошибки. Подробности доступны локально; решения — за вами.',20)
                        import telegram_reviews
                        telegram_reviews.offer(root,'feedback-review:'+ident,'Проверить сигналы отзывов',
                            'Категории из локального анализа; это сигналы, а не доказанные ошибки. Тексты переписки не передаются.',
                            'Локально проверить: '+ '; '.join(topics[:3]) + '. Подготовить исправление и синтетическую регрессию только для подтверждённых проблем.')
                except (TypeError,ValueError,KeyError):continue
    return {'configured':True}

def send(cfg,text):
    request=urllib.request.Request('https://api.telegram.org/bot'+cfg['botToken']+'/sendMessage',data=json.dumps({'chat_id':cfg['chatId'],'text':text,'allow_paid_broadcast':False,'link_preview_options':{'is_disabled':True}}).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=15) as response:body=json.load(response)
        if body.get('ok') and isinstance(body.get('result',{}).get('message_id'),int):return {'state':'sent','message_id':body['result']['message_id']}
        return {'state':'uncertain','error_code':'unconfirmed-response'}
    except urllib.error.HTTPError as exc:
        if exc.code==429:
            try:wait=min(max(int(json.load(exc).get('parameters',{}).get('retry_after',60)),1),86400)
            except Exception:wait=60
            return {'state':'queued','wait':wait,'error_code':'rate-limited'}
        if exc.code in (400,401,403):return {'state':'dead','error_code':'telegram-rejected-'+str(exc.code)}
        try:rejected=json.load(exc).get('ok') is False
        except Exception:rejected=False
        return {'state':'queued','wait':300,'error_code':'telegram-http-'+str(exc.code)} if rejected else {'state':'uncertain','error_code':'delivery-unconfirmed'}
    except urllib.error.URLError as exc:
        if isinstance(exc.reason,(ConnectionRefusedError,socket.gaierror)):return {'state':'queued','wait':60,'error_code':'connection-unavailable'}
        return {'state':'uncertain','error_code':'delivery-unconfirmed'}
    except (TimeoutError,OSError,ValueError):return {'state':'uncertain','error_code':'delivery-unconfirmed'}

def dispatch(root):
    cfg=config(root)
    if not cfg:return {'ok':True,'configured':False,'sent':0,'state':'token-and-private-chat-required'}
    import telegram_admin
    try:telegram_admin.poll(root,cfg);poll_status='ok'
    except Exception:poll_status='unavailable'
    import telegram_tasks
    telegram_tasks.kick(root)
    collect(root);now=int(time.time())
    with closing(database(root)) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute("UPDATE messages SET state='uncertain',error_code='interrupted-delivery' WHERE state='sending' AND started<?",(now-120,))
        row=db.execute("SELECT * FROM messages WHERE state='queued' AND next_at<=? ORDER BY priority DESC,created,id LIMIT 1",(now,)).fetchone()
        if row:db.execute("UPDATE messages SET state='sending',started=?,attempts=attempts+1 WHERE id=?",(now,row['id']))
        db.commit()
    if row:
        result=send(cfg,row['body'])
        wait=max(result.get('wait',0),min(3600,30*2**min(row['attempts'],7))) if result['state']=='queued' else 0
        with closing(database(root)) as db:
            db.execute('UPDATE messages SET state=?,next_at=?,message_id=?,error_code=? WHERE id=?',(result['state'],now+wait,result.get('message_id'),result.get('error_code'),row['id']));db.commit()
    with closing(database(root)) as db:states={r[0]:r[1] for r in db.execute('SELECT state,COUNT(*) FROM messages GROUP BY state')}
    status={'ok':True,'configured':True,'commands':poll_status,'checkedAt':now,'sent':int(bool(row) and result['state']=='sent'),'counts':states,'deliveryPolicy':'uncertain-deliveries-require-review','externalChildData':False}
    (root/'telegram-status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    return status

def welcome(root):
    put(root,'connection-test-v1','test','MAMA Helper подключён.\nСюда будут приходить ошибки автоматизации, отчёты и предложения по улучшению сайта.\nПереписка мам и сведения о детях не отправляются.\nЭто тестовое сообщение.',200)

def collect_runs(root,since):
    path=root/'automation-journal.sqlite'
    if not path.exists():return
    labels={'backup':'Резервная копия','restore-check':'Проверка восстановления','ai-tests':'Тесты правил ИИ','feedback-analysis':'Анализ отзывов','daily-report':'Ежедневный отчёт','weekly-review':'Недельный обзор','monitor':'Доступность сервисов'}
    with closing(sqlite3.connect('file:'+path.as_posix()+'?mode=ro',uri=True)) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='runs'").fetchone():return
        rows=db.execute("SELECT k,job,state,result,at FROM runs WHERE at>=? AND state IN ('success','failed','uncertain') ORDER BY at,k",(since,)).fetchall()
    for key,job,state,raw,stamp in rows:
        if job not in labels:continue
        try:value=json.loads(raw) if raw else {}
        except ValueError:value={}
        if state!='success' or value.get('ok') is not True:
            put(root,f'job-error:{job}:{stamp//1800}','error','MAMA: '+labels[job]+' — требуется проверка.\nПодробности доступны локально. Повторы объединяются на 30 минут.',100)
        elif job in ('backup','restore-check','ai-tests','feedback-analysis'):
            text='MAMA: '+labels[job]+' — успешно.'
            if job=='ai-tests':text+='\nСинтетических тестов: '+str(number(value.get('tests')))+'. Это не проверка реальной медицинской точности модели.'
            put(root,f'job-ok:{job}:{stamp//86400}','status',text)
    monitor=root/'monitor.json'
    if monitor.exists():
        try:
            value=json.loads(monitor.read_text());stamp=value['checkedAt'];healthy=value.get('ok') is True
            if stamp<since:return
            with closing(database(root)) as db:
                db.execute('CREATE TABLE IF NOT EXISTS notification_state(k TEXT PRIMARY KEY,v TEXT)')
                previous=db.execute("SELECT v FROM notification_state WHERE k='monitor'").fetchone()
                current='ok' if healthy else 'failed'
                if not previous or previous[0]!=current:
                    body='MAMA: сервисы доступны.' if healthy else 'MAMA: проверка доступности обнаружила сбой. Требуется локальная проверка.'
                    db.execute("INSERT OR IGNORE INTO messages(id,kind,body,priority,created,state) VALUES(?,?,?,?,?,'queued')",('monitor-change:'+str(stamp),'status',body,90 if healthy else 100,stamp))
                    db.execute("INSERT OR REPLACE INTO notification_state VALUES('monitor',?)",(current,));db.commit()
        except (ValueError,KeyError,TypeError):pass
