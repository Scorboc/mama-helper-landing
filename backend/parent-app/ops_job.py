"""Small scheduled operations: backups, checks, aggregate weekly report."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tarfile
import time
import urllib.request
from contextlib import closing
import operations as ops

ROOT = Path(os.environ.get('APP_OPS_ROOT','/var/lib/mama-helper/operations'))


def backup():
    root=ROOT/'backups';root.mkdir(parents=True,exist_ok=True,mode=0o700)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
    stage=root/('backup-'+stamp);stage.mkdir(mode=0o700)
    for name,path in [('app.sqlite',os.environ['APP_SQLITE_PATH']),('operations.sqlite',os.environ['APP_OPS_PATH'])]:
        with closing(sqlite3.connect('file:'+path+'?mode=ro',uri=True)) as source, closing(sqlite3.connect(stage/name)) as dest:
            source.backup(dest)
            dest.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            dest.execute('PRAGMA journal_mode=DELETE')
            if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise RuntimeError('Backup integrity check failed')
    import ai_budget
    ledger=ai_budget.location()
    if ledger.exists():
        with closing(sqlite3.connect('file:'+ledger.as_posix()+'?mode=ro',uri=True)) as source, closing(sqlite3.connect(stage/'ai-budget.sqlite')) as dest:
            source.backup(dest)
            if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise RuntimeError('AI budget backup integrity check failed')
    review=Path(os.environ.get('APP_FEEDBACK_REVIEW_ROOT',str(Path(os.environ['APP_SQLITE_PATH']).parent/'feedback-review')))/'review.sqlite3'
    if review.exists():
        with closing(sqlite3.connect('file:'+review.as_posix()+'?mode=ro',uri=True)) as source, closing(sqlite3.connect(stage/'feedback-review.sqlite3')) as dest:
            source.backup(dest)
            if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Feedback review backup integrity check failed')
    policy=os.environ.get('AI_POLICY_FILE')
    if policy:
        (stage/'ai-policy.json').write_text(json.dumps(ai_budget.settings(),ensure_ascii=False,indent=2),encoding='utf-8')
    # Back up code/content/assets. Secrets stay in existing protected environment files.
    archive=stage/'application.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for source in Path(__file__).parent.iterdir():
            if source.is_file() and (source.suffix in ('.py','.sql','.html','.js') or source.name in ('requirements.txt','answer_scenarios.json','legal_documents.json')):
                tar.add(source,arcname='backend/'+source.name)
        web=Path(os.environ.get('APP_WEB_ROOT','/var/www/mama-helper/current'))
        if web.exists():tar.add(web,arcname='frontend')
    from cryptography.fernet import Fernet
    key_path=os.environ.get('APP_BACKUP_KEY_FILE')
    if key_path:
        # Recovery settings are encrypted with an independent key kept by the owner.
        settings={k:v for k,v in os.environ.items() if k.startswith(('APP_','AI_','PROXYAPI_','CHEAPAI_','CHEAP_AI_','VAPID_','DATA_','STATE_'))}
        (stage/'settings.enc').write_bytes(Fernet(Path(key_path).read_bytes().strip()).encrypt(json.dumps(settings).encode()))
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.iterdir() if p.is_file()}
    (stage/'manifest.json').write_text(json.dumps({'created':stamp,'integrity':'ok','sha256':hashes},indent=2))
    (ROOT/'backup-status.json').write_text(json.dumps({'at':int(time.time()),'ok':True,'path':str(stage),'files':len(hashes)}))
    # Retain 14 daily generations; only remove verified direct children of this root.
    import shutil
    for old in sorted(root.glob('backup-*'))[:-14]:
        if old.is_dir() and not old.is_symlink() and old.resolve().parent==root.resolve():shutil.rmtree(old)
    return {'ok':True,'backup':str(stage)}


def check():
    base=os.environ.get('APP_MONITOR_URL','https://mama-helper-158-160-188-235.sslip.io').rstrip('/')
    checks=[]
    for target,url in [('site',base+'/'),('api','http://127.0.0.1:8787/healthz')]:
        started=time.monotonic();ok=False
        try:
            with urllib.request.urlopen(url,timeout=12) as response:
                body=response.read(500000)
                ok=response.status==200 and (json.loads(body).get('ok') is True if target=='api' else b'<div id="root"' in body)
        except Exception:
            pass
        checks.append({'target':target,'ok':ok,'ms':int((time.monotonic()-started)*1000)})
    with ops.database() as db:
        for c in checks:db.execute('INSERT INTO checks VALUES(?,?,?,?)',(int(time.time()),c['target'],c['ok'],c['ms']))
        incidents=[c['target'] for c in checks if not c['ok'] and
            db.execute('SELECT ok FROM checks WHERE target=? ORDER BY rowid DESC LIMIT 2',(c['target'],)).fetchall()==[(0,),(0,)]]
    existing={d['id'] for d in ops.documents('task')}
    for target in incidents:
        ident='incident'+datetime.date.today().strftime('%Y%m%d')+target
        if ident not in existing:
            ops.document('task',{'id':ident,'title':'Проверить доступность: '+target,
                'text':'Две последовательные проверки завершились ошибкой. Проверить HTTPS, приложение и базу. Данные пользователей не менять.','status':'new'})
    (ROOT/'monitor-status.json').write_text(json.dumps({'at':int(time.time()),'checks':checks}))
    return {'ok':all(c['ok'] for c in checks),'checks':checks}


def feedback_summary():
    import index as app
    counts={k:0 for k in ('helpful','unhelpful','unsafe','idea')}
    db=app.DB()
    try:
        for row in db.query('SELECT encrypted_data FROM mh_feedback WHERE created_at>=?',(int(time.time())-7*86400,)).fetchall():
            record=app.unseal(row[0]);kind=record.get('kind')
            if kind in counts:counts[kind]+=1
    finally:db.close()
    return counts


def report():
    result=ops.summary();result['feedback']=feedback_summary()
    import ai_budget
    result['aiBudget']=ai_budget.summary()
    errors=sum(a['calls'] for a in result['ai'] if a['status']!='ok')
    week=datetime.date.today().strftime('%G%V')
    if errors or result['feedback']['unsafe'] or result['feedback']['unhelpful']:
        ident='weekly'+week
        existing={d['id']:d for d in ops.documents('task')}
        ops.document('task',{'id':ident,'title':'Проверка качества за неделю '+week,
            'text':f"Ошибки ИИ: {errors}. Отзывы: "+json.dumps(result['feedback'],ensure_ascii=False)+'. Проверить причины и подготовить изменения. Публикация после проверки.',
            'status':existing.get(ident,{}).get('status','new')})
    reports=ROOT/'reports';reports.mkdir(exist_ok=True,mode=0o700)
    (reports/('week-'+week+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    ops.prune()
    return {'ok':True,'report':'week-'+week+'.json'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('job',choices=['backup','check','report']);args=parser.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    print(json.dumps(globals()[args.job](),ensure_ascii=False))
