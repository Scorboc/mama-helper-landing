"""Private local journal, isolated restore drill and zero-cost regression runner."""
import hashlib, io, json, os, re, shutil, sqlite3, subprocess, sys, tarfile, tempfile, time
from pathlib import Path
from contextlib import closing
from cryptography.fernet import Fernet

class JobConflict(Exception): pass

def journal(root):
    db=sqlite3.connect(root/'automation-journal.sqlite',timeout=30)
    db.execute('CREATE TABLE IF NOT EXISTS runs(k TEXT PRIMARY KEY,job TEXT,state TEXT,result TEXT,at INTEGER)')
    db.execute('CREATE TABLE IF NOT EXISTS incidents(k TEXT PRIMARY KEY,workflow TEXT,execution TEXT,at INTEGER)')
    db.commit();return db

def once(root,key,job,action):
    if not re.fullmatch(r'[A-Za-z0-9:_\-.]{8,160}',key):raise JobConflict('invalid-idempotency-key')
    with closing(journal(root)) as db:
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT job,state,result FROM runs WHERE k=?',(key,)).fetchone()
        if old:
            db.rollback()
            if old[0]!=job or old[1] not in ('success','failed') or old[2] is None:raise JobConflict('previous-job-needs-review')
            return {**json.loads(old[2]),'replayed':True}
        db.execute('INSERT INTO runs VALUES(?,?,?,?,?)',(key,job,'running',None,int(time.time())));db.commit()
        try:
            result=action()
            state='success' if result.get('ok') else 'failed'
            db.execute('UPDATE runs SET state=?,result=? WHERE k=?',(state,json.dumps(result),key));db.commit()
            return result
        except Exception:
            db.execute("UPDATE runs SET state='failed' WHERE k=?",(key,));db.commit();raise

def incident(root,data):
    if set(data)!={'workflowId','executionId'}:raise ValueError('metadata-only')
    for value in data.values():
        if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',value):raise ValueError('invalid-id')
    with closing(journal(root)) as db:
        db.execute('INSERT OR IGNORE INTO incidents VALUES(?,?,?,?)',(data['workflowId']+':'+data['executionId'],data['workflowId'],data['executionId'],int(time.time())));db.commit()
    return {'ok':True,'recordedLocally':True}

def recover_journal(root):
    """A restarted bridge cannot know whether an interrupted side effect finished."""
    with closing(journal(root)) as db:
        count=db.execute("UPDATE runs SET state='uncertain' WHERE state='running'").rowcount
        db.commit()
    return count

def restore(root):
    candidates=sorted((root/'backups').glob('*.tar.gz.enc'))
    if not candidates:raise RuntimeError('no-backup')
    source=candidates[-1];plain=Fernet((root/'backup.key').read_bytes().strip()).decrypt(source.read_bytes())
    checked={}
    with tempfile.TemporaryDirectory(prefix='restore-drill-',dir=root) as folder, tarfile.open(fileobj=io.BytesIO(plain),mode='r:gz') as archive:
        manifest=json.load(archive.extractfile('manifest.json'))
        for name,digest in manifest['sha256'].items():
            if name not in ('accounts','operations','ai-budget','n8n','automation','feedback-review','telegram-outbox'):raise ValueError('unexpected-database')
            member=archive.getmember(name+'.sqlite')
            if not member.isfile():raise ValueError('unexpected-member')
            content=archive.extractfile(member).read()
            if hashlib.sha256(content).hexdigest()!=digest:raise ValueError('checksum-mismatch')
            target=Path(folder)/(name+'.sqlite');target.write_bytes(content)
            with closing(sqlite3.connect('file:'+target.as_posix()+'?mode=ro',uri=True)) as db:
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('integrity-failed')
                tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
                counts={t:db.execute('SELECT COUNT(*) FROM "'+t.replace('"','""')+'"').fetchone()[0] for t in tables}
                if name in manifest.get('rowCounts',{}) and counts!=manifest['rowCounts'][name]:raise ValueError('row-count-mismatch')
                checked[name]={'tables':len(tables),'rows':sum(counts.values())}
    return {'ok':True,'backup':source.name,'checkedAt':int(time.time()),'databases':checked,'isolated':True,'workingDatabasesModified':False,'scope':'database-restore-not-full-machine-recovery'}

def qa(root):
    backend=Path(__file__).parent
    modules=['test_age_logic','test_monthly_content','test_content_policy','test_prompt_policy','test_parent_support','test_chat_safety','test_chat_context','test_chat_freshness','test_expanded_chat_qa','test_ai_limits','test_profile_lock','test_sleep_diary','test_automation_bridge','test_telegram_outbox']
    modules.append('test_telegram_admin')
    modules.append('test_telegram_tasks')
    modules.extend(['test_telegram_reviews','test_telegram_publication'])
    modules.append('test_telegram_billing')
    modules.append('test_proxy_balance')
    modules=[m for m in modules if (backend/(m+'.py')).exists()]
    # Do not inherit production policy files, limits, provider or push switches.
    allowed={'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','COMSPEC','PATHEXT'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed}
    with tempfile.TemporaryDirectory(prefix='offline-qa-',dir=root) as tmp:
        isolated=Path(tmp)/'app/backend/parent-app'
        shutil.copytree(backend,isolated,ignore=shutil.ignore_patterns('__pycache__','*.sqlite*','*.db','*.log','.env*','*.key','*.enc'))
        docs=backend.parents[1]/'docs/ai'
        if docs.exists():shutil.copytree(docs,Path(tmp)/'app/docs/ai')
        source_hash=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(isolated.rglob('*')) if p.is_file())).hexdigest()
        # Each test fixture changes APP_SQLITE_PATH; its budget must follow it.
        env.pop('APP_AI_BUDGET_PATH',None)
        env.update(PYTHONUTF8='1',APP_SQLITE_PATH=tmp+'/accounts.sqlite',APP_OPS_PATH=tmp+'/ops.sqlite',MAMA_AUTOMATION_ROOT=tmp)
        code="""import socket,unittest,sys
original=socket.socket.connect
def guarded(self,address):
    if not isinstance(address,tuple) or address[0] not in ('127.0.0.1','localhost','::1'):raise RuntimeError('External network blocked during offline QA')
    return original(self,address)
socket.socket.connect=guarded
loaded=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:])
def flatten(suite):
    for test in suite:
        if isinstance(test,unittest.TestSuite):yield from flatten(test)
        else:yield test
seen=set();unique=[];discovered=0
for test in flatten(loaded):
    discovered+=1
    if test.id() not in seen:
        seen.add(test.id());unique.append(test)
print('MAMA_QA_DISCOVERY='+str(discovered)+',UNIQUE='+str(len(unique)),flush=True)
result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(unique))
print('MAMA_QA_SUMMARY='+str(result.testsRun)+','+str(len(result.failures))+','+str(len(result.errors)))
sys.exit(not result.wasSuccessful())
"""
        try:
            proc=subprocess.run([sys.executable,'-c',code,*modules],cwd=isolated,env=env,capture_output=True,text=True,encoding='utf-8',timeout=240)
        except subprocess.TimeoutExpired as exc:
            result={'ok':False,'checkedAt':int(time.time()),'mode':'offline-synthetic-regression','error':'test-timeout','paidCalls':0,'liveModelVerified':False}
            folder=root/'reports';folder.mkdir(exist_ok=True)
            output=(exc.stdout or b'')+(exc.stderr or b'')
            (folder/'ai-regression-latest.log').write_text(output.decode('utf-8',errors='replace') if isinstance(output,bytes) else output,encoding='utf-8')
            (folder/'ai-regression-latest.json').write_text(json.dumps(result),encoding='utf-8')
            return result
    match=re.search(r'MAMA_QA_SUMMARY=(\d+),(\d+),(\d+)',proc.stdout)
    result={'ok':proc.returncode==0,'checkedAt':int(time.time()),'mode':'offline-synthetic-regression','paidCalls':0,'liveModelVerified':False,'isolatedSourceCopy':True,'modules':modules,'tests':int(match[1]) if match else 0,'failures':int(match[2]) if match else None,'errors':int(match[3]) if match else None,'sourceSha256':source_hash}
    log=root/'reports';log.mkdir(exist_ok=True)
    (log/'ai-regression-latest.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
    (log/'ai-regression-latest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
