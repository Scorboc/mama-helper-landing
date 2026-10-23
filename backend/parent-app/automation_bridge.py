"""Narrow loopback-only n8n bridge. No chat/profile export, no arbitrary actions."""
import datetime as dt
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import sqlite3
import tarfile
import threading
import time
import uuid
import automation_reliability as reliability
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contextlib import closing
from cryptography.fernet import Fernet
import operations as ops
import ops_job
import ai_budget

ROOT=Path(os.environ['MAMA_AUTOMATION_ROOT'])
ROOT.mkdir(parents=True,exist_ok=True)
LOCK=threading.Lock()
BACKUP_CATCHUP_THREAD=None
PORT=int(os.environ.get('MAMA_AUTOMATION_PORT','8792'))
HOSTS={f'127.0.0.1:{PORT}',f'localhost:{PORT}'}
JOBS={'monitor','backup','daily-report','weekly-review','readiness','restore-check','ai-tests','feedback-analysis','telegram-dispatch'}
JOB_LOCKS={name:threading.Lock() for name in JOBS}
# A slow regression/provider call must never hold up health checks or reports.
# Backup and restore share a lock so restore cannot read an unfinished archive.
JOB_LOCKS['backup']=LOCK
JOB_LOCKS['restore-check']=LOCK

def write_json(path,data):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)

def readiness():
    telegram='configured' if (ROOT/'telegram-settings.enc').exists() else 'not-configured'
    import telegram_publication, telegram_reviews
    return {'ok':True,'localOnly':True,'automaticPublication':False,'externalChatExport':False,
            'githubSourcePublication':bool(telegram_publication.settings(ROOT)),
            'ownerEditedChatHandoff':bool(telegram_reviews.settings(ROOT)),
            'integrations':{'telegram':telegram,'smtp':'not-configured','payments':'not-configured',
                            'instagram':'not-configured','taxes':'owner-registration-and-provider-required',
                            'aiReview':'local-feedback-triage-and-aggregate-ai-proposals'},
            'available':['monitor','encrypted-backup','aggregate-report','review-proposals','isolated-restore-check','offline-ai-regression','idempotency-journal','local-error-log','feedback-analysis']}

def monitor():
    checks=[]
    site_url=os.environ.get('APP_MONITOR_URL','http://127.0.0.1:5173/').rstrip('/')+'/'
    for name,url in [('site',site_url),('accounts','http://127.0.0.1:8787/healthz'),('n8n','http://127.0.0.1:5678/healthz/readiness')]:
        start=time.monotonic();ok=False
        try:
            with urllib.request.urlopen(url,timeout=8) as r:
                b=r.read(500000)
                ok=r.status==200 and (b'id="root"' in b if name=='site' else json.loads(b).get('ok',False) if name=='accounts' else True)
        except Exception:pass
        checks.append({'target':name,'ok':bool(ok),'ms':round((time.monotonic()-start)*1000)})
    now=int(time.time());result={'ok':all(c['ok'] for c in checks),'checkedAt':now,'checks':checks}
    previous=ROOT/'monitor.json'
    old=json.loads(previous.read_text(encoding='utf-8')) if previous.exists() else {}
    failed={c['target'] for c in old.get('checks',[]) if not c['ok']}
    incidents=[c['target'] for c in checks if not c['ok'] and c['target'] in failed]
    if incidents:write_json(ROOT/'attention.json',{'at':now,'reason':'two-consecutive-failures','targets':incidents,'delivery':'local-only'})
    write_json(previous,result)
    result['backupMaintenance']=backup_maintenance()
    return result


def backup_maintenance():
    """Monitor backstop; share the scheduled backup lock and never dispatch Telegram."""
    global BACKUP_CATCHUP_THREAD
    def read(name):
        try:
            value=json.loads((ROOT/name).read_text(encoding='utf-8'))
            return value if isinstance(value,dict) else {}
        except (OSError,ValueError):return {}
    now=int(time.time())
    status=read('backup-status.json')
    try:
        created=dt.datetime.strptime(status['createdAt'][:15],'%Y%m%d-%H%M%S').replace(tzinfo=dt.timezone.utc).timestamp()
        age=now-created if status.get('ok') is True else float('inf')
    except (KeyError,TypeError,ValueError):age=float('inf')
    import telegram_outbox
    telegram_outbox.backup_alerts(ROOT,age,read('restore-status.json'),now)
    if age<=24*3600:return {'state':'fresh'}
    if not LOCK.acquire(blocking=False):return {'state':'busy'}
    try:
        try:hours=max(1,float(os.environ.get('MAMA_BACKUP_CATCHUP_HOURS','6')))
        except ValueError:hours=6
        if not 1<=hours<=8760:hours=6
        last=read('backup-catchup.json').get('attemptedAt',0)
        if isinstance(last,(int,float)) and now-last<hours*3600:
            LOCK.release()
            return {'state':'throttled'}
    except Exception:
        LOCK.release()
        raise
    def catchup():
        try:
            write_json(ROOT/'backup-catchup.json',{'attemptedAt':now})
            result=backup()
            restored=reliability.restore(ROOT) if result.get('ok') else {'ok':False,'checkedAt':now}
            write_json(ROOT/'restore-status.json',restored)
            telegram_outbox.backup_alerts(ROOT,0 if result.get('ok') else age,restored,now)
        except Exception:
            restored={'ok':False,'checkedAt':now}
            write_json(ROOT/'restore-status.json',restored)
            telegram_outbox.backup_alerts(ROOT,age,restored,now)
        finally:LOCK.release()
    try:
        BACKUP_CATCHUP_THREAD=threading.Thread(target=catchup,name='backup-catchup',daemon=True)
        BACKUP_CATCHUP_THREAD.start()
    except Exception:
        LOCK.release()
        raise
    return {'state':'started'}

def aggregates():
    summary=ops.summary()
    # Explicit allowlist: no actor keys, names, text, medical fields or profile dates.
    ai=[{'kind':r['kind'],'status':r['status'],'calls':r['calls'],'averageMs':r['averageMs'],
         'unknownUsage':r['unknownUsage']} for r in summary['ai']]
    budget=ai_budget.summary()
    return {'periodDays':summary['days'],'events':summary['events'],'ai':ai,
            'feedbackCounts':ops_job.feedback_summary(),'budget':budget,'readiness':readiness()}

def report(weekly=False):
    summary=aggregates();ideas=[]
    errors=sum(r['calls'] for r in summary['ai'] if r['status']!='ok')
    if errors:ideas.append({'priority':'P1','observation':f'{errors} вызовов ИИ с ошибкой за период.',
        'prompt':'Проверь технические причины ошибок ИИ по обезличенным кодам. Не выводи содержимое диалогов. Сохрани данные и функции. Подготовь исправление локально и тест возврата лимита при ошибке. Не публикуй автоматически.'})
    if any(r['averageMs'] and r['averageMs']>15000 for r in summary['ai']):ideas.append({'priority':'P2','observation':'Среднее время ответа одной группы выше 15 секунд.',
        'prompt':'Исследуй задержку ответа: ожидание провайдера, очередь, размер контекста. Уменьшай расходы без потери активного профиля и свежего дневника. Измерь p50/p95 на синтетических сценариях. Не меняй лимиты и модель без расчёта.'})
    if summary['feedbackCounts'].get('unsafe',0):ideas.append({'priority':'P0','observation':'Есть оценки небезопасного ответа; это сигнал для проверки, а не доказательство ошибки.',
        'prompt':'Локально проверь отмеченные ответы с разрешённым доступом. Различай проверенную ошибку и гипотезу. Сверь медицинские основания с официальными рекомендациями, подготовь правило и синтетический регрессионный тест. Не отправляй медицинские сведения внешним инструментам.'})
    try:
        import marketing_control
        marketing_digest=marketing_control.summary(ROOT)
    except Exception:
        marketing_digest='Контроль продвижения временно недоступен; основной отчёт сохранён.'
    result={'ok':True,'generatedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'method':'deterministic-aggregate-rules-not-ai',
            'summary':summary,'proposals':ideas,'marketingControl':marketing_digest,
            'humanApprovalRequired':True,'externalMessagesSent':False}
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d')
    name=('weekly' if weekly else 'daily')+'-'+stamp
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    write_json(reports/(name+'.json'),result)
    text=['# Отчёт MAMA',result['generatedAt'],'','Метод: агрегированные технические показатели; ИИ не вызывался.','']
    text += [f"## {p['priority']}: {p['observation']}\n\nПромпт администратору:\n{p['prompt']}\n" for p in ideas]
    text += ['','Подключения: Telegram, оплаты, Instagram и налоги требуют настройки владельца.','Исходные переписки и данные детей не экспортировались.']
    (reports/(name+'.md')).write_text('\n'.join(text),encoding='utf-8')
    return {'ok':True,'report':name,'proposals':len(ideas),'method':result['method'],'externalMessagesSent':False}

def snapshot_database(path, target):
    # A hot rollback journal needs SQLite's normal recovery. Retry only that
    # explicit error, never permissions/corruption, and never create a source.
    for mode in ('ro', 'rw'):
        try:
            with closing(sqlite3.connect(path.resolve().as_uri()+'?mode='+mode,uri=True,timeout=30)) as source, closing(sqlite3.connect(target)) as dest:
                source.backup(dest)
                if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Backup integrity failed')
                tables=[r[0] for r in dest.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
                return {t:dest.execute('SELECT COUNT(*) FROM "'+t.replace('"','""')+'"').fetchone()[0] for t in tables}
        except sqlite3.OperationalError as error:
            if mode!='ro' or getattr(error,'sqlite_errorcode',None)!=sqlite3.SQLITE_READONLY_ROLLBACK:
                raise

def backup():
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
    buf=io.BytesIO();manifest={};counts={}
    with tarfile.open(fileobj=buf,mode='w:gz') as tar:
        for name,path in [('accounts',os.environ['APP_SQLITE_PATH']),('operations',os.environ['APP_OPS_PATH']),('ai-budget',str(ai_budget.location())),
                          ('n8n',str(ROOT/'state/.n8n/database.sqlite')),('automation',str(ROOT/'automation-journal.sqlite')),('telegram-outbox',str(ROOT/'telegram-outbox.sqlite')),
                          ('feedback-review',str(Path(os.environ.get('APP_FEEDBACK_REVIEW_ROOT',str(Path(os.environ['APP_SQLITE_PATH']).parent/'feedback-review')))/'review.sqlite3'))]:
            path=Path(path)
            if not path.exists():continue
            temp=ROOT/(name+'-snapshot.sqlite')
            try:
                counts[name]=snapshot_database(path,temp)
                content=temp.read_bytes();manifest[name]=hashlib.sha256(content).hexdigest()
                info=tarfile.TarInfo(name+'.sqlite');info.size=len(content);tar.addfile(info,io.BytesIO(content))
            finally:
                if temp.exists():temp.unlink()
        for name,path in [('n8n-settings.json',ROOT/'settings.json'),('telegram-settings.enc',ROOT/'telegram-settings.enc'),('app-settings.json',Path(os.environ['APP_SQLITE_PATH']).parent/'settings.json'),
                          ('chat-handoff-settings.json',ROOT/'chat-handoff-settings.json'),('github-publication-settings.json',ROOT/'github-publication-settings.json'),
                          ('ai-settings.enc',Path(os.environ['APP_SQLITE_PATH']).parent/'ai-settings.enc')]:
            if path.exists():
                content=path.read_bytes();info=tarfile.TarInfo(name);info.size=len(content);tar.addfile(info,io.BytesIO(content))
        app_root=Path(__file__).resolve().parents[2]
        safe_roots=[app_root/'backend',app_root/'src',app_root/'public',app_root/'automation',app_root/'docs']
        for source_root in safe_roots:
            for path in source_root.rglob('*'):
                if not path.is_file() or path.is_symlink() or any(p in ('__pycache__','node_modules','outputs','output','.git') for p in path.parts):continue
                if path.name.startswith('.env') or path.suffix in ('.sqlite','.sqlite3','.db','.pyc','.log','.enc','.key'):continue
                if path.stat().st_size>20_000_000:continue
                tar.add(path,arcname='app/'+path.relative_to(app_root).as_posix())
        for path in ROOT.glob('*.py'):tar.add(path,arcname='n8n-runtime/'+path.name)
        for name in ('package.json','package-lock.json'):
            path=ROOT/'runtime'/name
            if path.exists():tar.add(path,arcname='n8n-runtime/'+name)
        content=json.dumps({'created':stamp,'sha256':manifest,'rowCounts':counts}).encode();info=tarfile.TarInfo('manifest.json');info.size=len(content);tar.addfile(info,io.BytesIO(content))
    key=(ROOT/'backup.key').read_bytes().strip()
    out=ROOT/'backups'/('mama-'+stamp+'.tar.gz.enc');out.parent.mkdir(exist_ok=True)
    out.write_bytes(Fernet(key).encrypt(buf.getvalue()))
    if Fernet(key).decrypt(out.read_bytes())!=buf.getvalue():raise RuntimeError('Backup verification failed')
    result={'ok':True,'createdAt':stamp,'databases':list(manifest),'encrypted':True,'verified':True,'file':out.name}
    write_json(ROOT/'backup-status.json',result)
    return result

def run(name):
    if name not in JOBS:raise ValueError('Unsupported job')
    with JOB_LOCKS[name]:
        def feedback_review():
            import feedback_analysis
            return feedback_analysis.review()
        def telegram_dispatch():
            import telegram_outbox
            return telegram_outbox.dispatch(ROOT)
        result={'monitor':monitor,'backup':backup,'daily-report':report,'weekly-review':lambda:report(True),'readiness':readiness,'restore-check':lambda:reliability.restore(ROOT),'ai-tests':lambda:reliability.qa(ROOT),'feedback-analysis':feedback_review,'telegram-dispatch':telegram_dispatch}[name]()
        if name=='restore-check':write_json(ROOT/'restore-status.json',result)
        return result

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,status,body):
        payload=json.dumps(body,ensure_ascii=False).encode();self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(payload)))
        try:
            self.end_headers();self.wfile.write(payload)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):
            # Result is already committed to the journal; a retry can replay it.
            pass
    def do_GET(self):
        if self.headers.get('Host') not in HOSTS:return self.send(403,{'error':'host'})
        if self.path=='/healthz':return self.send(200,{'ok':True,'service':'mama-automation','localOnly':True})
        return self.send(404,{'error':'not-found'})
    def do_POST(self):
        if self.headers.get('Host') not in HOSTS or self.headers.get('Origin'):return self.send(403,{'error':'origin'})
        expected='Bearer '+os.environ['MAMA_AUTOMATION_TOKEN']
        if not hmac.compare_digest(self.headers.get('Authorization',''),expected):return self.send(401,{'error':'unauthorized'})
        name=self.path.removeprefix('/jobs/')
        if self.path=='/events/error':
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=256:raise ValueError()
                return self.send(200,reliability.incident(ROOT,json.loads(self.rfile.read(length))))
            except (ValueError,TypeError):return self.send(400,{'error':'metadata-only'})
        if self.path!='/jobs/'+name or name not in JOBS:return self.send(404,{'error':'not-found'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<=length<=128:return self.send(400,{'error':'no-input-data-allowed'})
            if length and json.loads(self.rfile.read(length))!={}:return self.send(400,{'error':'no-input-data-allowed'})
            key=self.headers.get('Idempotency-Key','')
            if name!='readiness' and not key:return self.send(400,{'error':'idempotency-key-required'})
            result=reliability.once(ROOT,key,name,lambda:run(name)) if key else run(name)
            self.send(200 if result.get('ok') else 503,result)
        except reliability.JobConflict:self.send(409,{'error':'job-needs-review','job':name})
        except (ValueError,TypeError):self.send(400,{'error':'invalid-request','job':name})
        except Exception:self.send(503,{'error':'job-failed','job':name})

if __name__=='__main__':
    reliability.recover_journal(ROOT)
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
