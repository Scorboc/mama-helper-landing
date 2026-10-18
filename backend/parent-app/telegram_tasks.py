"""Durable owner task queue. Telegram input is data, never a shell command."""
import hashlib,json,os,re,shutil,sqlite3,subprocess,sys,time
from contextlib import closing
from pathlib import Path
import telegram_outbox as outbox

APP=Path(__file__).resolve().parents[2]
def prepare(db):
    db.execute('CREATE TABLE IF NOT EXISTS admin_tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,update_id INTEGER UNIQUE,idea TEXT,status TEXT,created INTEGER,summary TEXT,artifact TEXT)')

def submit(db,ident,idea):
    prepare(db)
    if not idea.strip():return 'Напишите /task и описание задачи одним сообщением.'
    if len(idea)>1600:return 'Опишите задачу в пределах 1600 символов.'
    if re.search(r'\b\d{6,15}:[A-Za-z0-9_-]{25,80}\b|\bsk-[A-Za-z0-9_-]{15,}',idea):return 'Похоже, указан секрет. Задача не принята. Отправьте описание без ключей.'
    old=db.execute('SELECT id FROM admin_tasks WHERE update_id=?',(ident,)).fetchone()
    if old:return 'Задача №'+str(old[0])+' уже принята.'
    if db.execute("SELECT COUNT(*) FROM admin_tasks WHERE status IN ('queued','running')").fetchone()[0]>=5:return 'В очереди уже пять задач. Дождитесь выполнения.'
    if db.execute('SELECT COUNT(*) FROM admin_tasks WHERE created>?',(int(time.time())-86400,)).fetchone()[0]>=10:return 'Лимит автоматизации: 10 задач за 24 часа. Остальные можно подготовить через /prompt.'
    cursor=db.execute("INSERT INTO admin_tasks(update_id,idea,status,created) VALUES(?,?,'queued',?)",(ident,idea.strip(),int(time.time())))
    return 'Задача №'+str(cursor.lastrowid)+' принята. Выполню локально в отдельной копии, проверю и пришлю результат. Используются лимиты вашего Codex. Автопубликации нет. После проверки можно отдельно отправить исходники в GitHub: /publish T'+str(cursor.lastrowid)+'.'

def status(db):
    prepare(db);rows=db.execute('SELECT id,status FROM admin_tasks ORDER BY id DESC LIMIT 5').fetchall()
    names={'queued':'в очереди','running':'выполняется','applied':'проверена и применена локально','review':'нужна проверка','failed':'не выполнена','interrupted':'прервана, нужен разбор'}
    return '\n'.join('№'+str(r[0])+': '+names.get(r[1],r[1]) for r in rows) or 'Задач пока нет.'

def kick(root):
    if not (root/'task-runner-enabled.json').exists():return
    with closing(outbox.database(root)) as db:
        prepare(db);waiting=db.execute("SELECT 1 FROM admin_tasks WHERE status IN ('queued','running') LIMIT 1").fetchone();db.commit()
    if not waiting:return
    env=clean_env();env['MAMA_TASK_ROOT']=str(root)
    with (root/'task-worker.log').open('ab') as log:
        subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'worker'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

def clean_env():
    allowed={'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','COMSPEC','PATHEXT','PROGRAMFILES','PROGRAMFILES(X86)'}
    return {k:v for k,v in os.environ.items() if k.upper() in allowed}

SKIP={'node_modules','dist','output','outputs','.git','.codex','__pycache__','deploy','deferred-backend','.github','db_migrations'}
EXT={'.py','.ts','.tsx','.js','.mjs','.cjs','.css','.json','.md','.html','.svg','.txt','.toml','.sql','.webmanifest'}
def sources(app):
    result={}
    for folder,dirs,files in os.walk(app,followlinks=False):
        dirs[:]=[d for d in dirs if d not in SKIP and not d.startswith('.') and not (Path(folder)/d).is_symlink()]
        for name in files:
            p=Path(folder)/name
            if p.is_symlink() or name.startswith('.') or p.suffix not in EXT or p.stat().st_size>2_000_000:continue
            if re.search(r'(?i)(secret|credential|settings\.json|token|\.env)',name):continue
            result[p.relative_to(app).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    return result

def allowed_change(name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name:return False
    if name.startswith('src/') and p.suffix in {'.ts','.tsx','.css'}:return True
    if name.startswith('public/') and p.suffix=='.svg':return True
    if name.startswith('docs/') and p.suffix=='.md':return True
    if name.startswith('backend/parent-app/') and p.suffix=='.py':
        return not re.search(r'(telegram_|proxy_balance|automation_|local_server|operations|ops_server|ai_budget|password|auth|payment)',p.name)
    return False

def changes(base,after):
    return sorted(k for k in set(base)|set(after) if base.get(k)!=after.get(k))

def apply_checked(app,candidate,base,after,artifact):
    changed=changes(base,after)
    if len(changed)>40 or any(k not in after or not allowed_change(k) for k in changed):raise ValueError('manual-review-required-for-scope-or-deletion')
    if sources(app)!=base:raise ValueError('working-source-changed-during-task')
    rollback=artifact/'rollback';rollback.mkdir(exist_ok=True)
    for key in changed:
        source=app/key;target=candidate/key
        if target.is_symlink() or not target.resolve().is_relative_to(candidate.resolve()):raise ValueError('unsafe-path')
        if source.exists():
            backup=rollback/key;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
    applied=[]
    try:
        for key in changed:
            dest=app/key;dest.parent.mkdir(parents=True,exist_ok=True)
            tmp=dest.with_suffix(dest.suffix+'.mama-task-tmp');tmp.write_bytes((candidate/key).read_bytes());os.replace(tmp,dest);applied.append(key)
    except Exception:
        for key in reversed(applied):
            if key in base:shutil.copy2(rollback/key,app/key)
            else:(app/key).unlink(missing_ok=True)
        raise
    return changed

def backup(root):
    import urllib.request
    cfg=json.loads((root/'settings.json').read_text())
    req=urllib.request.Request('http://127.0.0.1:8792/jobs/backup',data=b'{}',headers={'Authorization':'Bearer '+cfg['bridgeToken'],'Content-Type':'application/json','Idempotency-Key':'task-backup-'+str(time.time_ns())})
    with urllib.request.urlopen(req,timeout=120) as response:result=json.load(response)
    if result.get('ok') is not True:raise ValueError('backup-not-confirmed')

def execute(root,ident,idea):
    artifact=root/'tasks'/str(ident);artifact.mkdir(parents=True,exist_ok=False)
    candidate=artifact/'work/app';candidate.mkdir(parents=True)
    base=sources(APP)
    for key in base:
        dest=candidate/key;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(APP/key,dest)
    for folder in ('src','public'):
        for asset in (APP/folder).rglob('*'):
            if asset.is_file() and not asset.is_symlink() and asset.suffix.lower() in {'.png','.jpg','.jpeg','.webp','.woff','.woff2','.ico'}:
                dest=candidate/asset.relative_to(APP);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(asset,dest)
    (artifact/'baseline.json').write_text(json.dumps(base),encoding='utf-8')
    backup(root)
    codex=shutil.which('codex')
    if not codex:raise ValueError('codex-not-found')
    # No inherited MAMA/APP/provider secrets, desktop tool pipe, or external MCP configuration.
    schema={'type':'object','properties':{'summary':{'type':'string'},'ready':{'type':'boolean'},'needs_files':{'type':'array','items':{'type':'string'}},'files':{'type':'array','items':{'type':'object','properties':{'path':{'type':'string'},'content':{'type':'string'}},'required':['path','content'],'additionalProperties':False}}},'required':['summary','ready','needs_files','files'],'additionalProperties':False}
    schema_path=artifact/'schema.json';schema_path.write_text(json.dumps(schema),encoding='utf-8')
    home=artifact/'codex-home';home.mkdir()
    auth=Path.home()/'.codex/auth.json'
    if not auth.exists():raise ValueError('chatgpt-cli-auth-file-unavailable')
    shutil.copy2(auth,home/'auth.json')
    runner_env=clean_env();runner_env['CODEX_HOME']=str(home)
    args=[codex,'--ask-for-approval','never','exec','--ignore-user-config','--ephemeral','--sandbox','read-only','--skip-git-repo-check','--cd',str(candidate),'--output-schema',str(schema_path),'--output-last-message',str(artifact/'result.json'),'-']
    instructions=('Работай только в текущей копии app. Прочитай AGENTS.md и CONTENT_RULES.md. '
      'Это подготовка патча БЕЗ вызова инструментов. НИКАКИЕ инструменты не используй, даже для чтения или тестов. '
      'Нужные исходники предоставляет локальный контроллер. Если не хватает файлов, верни ready=false, needs_files=[точные пути из списка], files=[]. '
      'Только изучив исходники изменяемых существующих файлов, подготовь полный патч; не выдумывай их содержимое. '
      'Правила уже включены ниже как проверенный контекст контроллера. Верни JSON по схеме. '
      'files содержит относительный путь от app и ПОЛНОЕ новое содержимое каждого изменяемого файла. '
      'ready=true только если задача реализована полностью. При вопросах или недостатке доступа верни ready=false и пояснение в summary. '
      'Выполни задачу владельца ниже. Не читай файлы вне копии, домашний каталог, ключи, реальные базы и историю пользователей. '
      'Не используй MCP, сеть, публикацию, git push, платежи или установку зависимостей. Не меняй файлы управления автоматизацией, авторизацию, зависимости, миграции. '
      'Не удаляй существующие файлы. При необходимости таких действий объясни, что нужна проверка владельца. '
      'Сохрани функции, медицинские границы, активный профиль и точный возраст. Проверь затронутые сценарии синтетическими данными. '
      'Если требуются уточнения, ничего не меняй и перечисли вопросы. Итоговый отчёт по-русски: изменения, проверки, ограничения. '
      'Независимый исполнитель после тебя выполнит сборку и синтетические тесты; не заявляй их заранее.\nЗадача:\n'+idea)
    selected={k for k in ('AGENTS.md','CONTENT_RULES.md','package.json') if k in base}
    inventory='\n'.join(sorted(base))
    try:
        with (artifact/'codex.log').open('w',encoding='utf-8') as log:
            for turn in range(4):
                context='\n\n'.join('FILE '+k+'\n'+(candidate/k).read_text(encoding='utf-8',errors='replace') for k in sorted(selected))
                if len(context)>350000:raise ValueError('requested-context-too-large')
                proc=subprocess.run(args,input=instructions+'\nДоступные пути:\n'+inventory+'\n\nКонтекст исходников:\n'+context,text=True,encoding='utf-8',env=runner_env,stdout=log,stderr=log,timeout=600)
                if proc.returncode:raise ValueError('codex-failed-see-local-log')
                result=json.loads((artifact/'result.json').read_text(encoding='utf-8'))
                needed=result.get('needs_files',[])
                if not needed:break
                if not isinstance(needed,list) or len(needed)>20 or any(k not in base for k in needed):raise ValueError('requested-source-not-allowlisted')
                if set(needed).issubset(selected):raise ValueError('source-request-loop')
                selected.update(needed)
            else:raise ValueError('source-round-limit')
    finally:(home/'auth.json').unlink(missing_ok=True)
    # Agent report is untrusted. Only independently checked files may reach the working tree.
    result=json.loads((artifact/'result.json').read_text(encoding='utf-8'))
    (artifact/'report.md').write_text(result['summary'],encoding='utf-8')
    if result.get('ready') is not True:return 'review','Нужны уточнения или ручная проверка.\n'+result['summary'][:900],str(artifact)
    files=result.get('files',[])
    if not isinstance(files,list) or len(files)>40:raise ValueError('invalid-patch-size')
    seen=set()
    for entry in files:
        key=entry['path'];content=entry['content']
        if not isinstance(key,str) or key in seen or '\\' in key or '..' in Path(key).parts or Path(key).is_absolute() or not allowed_change(key):raise ValueError('patch-path-not-allowed')
        dest=candidate/key
        if not dest.resolve().is_relative_to(candidate.resolve()) or dest.is_symlink():raise ValueError('patch-path-escape')
        if not isinstance(content,str) or len(content.encode('utf-8'))>500000:raise ValueError('patch-file-too-large')
        if key in base and key not in selected:raise ValueError('existing-source-not-read')
        seen.add(key);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(content,encoding='utf-8')
    after=sources(candidate);changed=changes(base,after)
    if not changed:return 'review','Изменений нет; уточнения или результат анализа доступны в локальном отчёте.',str(artifact)
    if any(not allowed_change(k) or k not in after for k in changed):return 'review','Изменения требуют ручной проверки области доступа; рабочие файлы не менялись.',str(artifact)
    # Agent has no tool execution or filesystem writes; the trusted builder can reuse installed packages.
    # pnpm links form a graph: recursively dereferencing them would duplicate dependencies indefinitely.
    linked=subprocess.run(['cmd.exe','/c','mklink','/J',str(candidate/'node_modules'),str(APP/'node_modules')],capture_output=True,timeout=15)
    if linked.returncode:raise ValueError('dependency-junction-failed')
    node=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
    with (artifact/'build.log').open('wb') as log:
        result=subprocess.run([str(node),str(candidate/'node_modules/vite/bin/vite.js'),'build'],cwd=candidate,env=clean_env(),stdout=log,stderr=log,timeout=180)
    if result.returncode:raise ValueError('build-failed-see-local-log')
    # Run the trusted baseline harness against the candidate, not a candidate-edited harness.
    import importlib.util
    spec=importlib.util.spec_from_file_location('mama_trusted_qa',APP/'backend/parent-app/automation_reliability.py');qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
    qa.__file__=str(candidate/'backend/parent-app/automation_reliability.py')
    testroot=artifact/'qa';testroot.mkdir();result=qa.qa(testroot)
    if not result.get('ok'):raise ValueError('regression-failed-see-local-log')
    # Any concurrent edits cause a stop, preserving the user's newer source.
    changed=apply_checked(APP,candidate,base,after,artifact)
    (artifact/'verified.json').write_text(json.dumps({'files':changed,'tests':result.get('tests'),'build':True,'serverPublished':False},ensure_ascii=False,indent=2),encoding='utf-8')
    description=(artifact/'report.md').read_text(encoding='utf-8')[:900]
    description=re.sub(r'\b\d{6,15}:[A-Za-z0-9_-]{25,80}\b|\bsk-[A-Za-z0-9_-]{15,}','[секрет скрыт]',description)
    runtime_note='\nИзменены Python исходники: требуется отдельный перезапуск и проверка backend; работа нового backend пока не подтверждена.' if any(k.endswith('.py') for k in changed) else ''
    return 'applied','Исходники применены локально. Файлов: '+str(len(changed))+'. Сборка успешна. Синтетических тестов: '+str(result.get('tests'))+'. Публикации ещё нет; для GitHub: /publish T'+str(ident)+'.'+runtime_note+'\nОписание исполнителя:\n'+description+'\nОтчёт: private/n8n/tasks/'+str(ident)+'/report.md',str(artifact)

def worker(root):
    import ctypes
    handle=ctypes.windll.kernel32.CreateMutexW(None,False,'Local\\MAMA-Telegram-task-worker')
    if ctypes.windll.kernel32.GetLastError()==183:return
    with closing(outbox.database(root)) as db:
        prepare(db);db.execute('BEGIN IMMEDIATE')
        # A previous process died: never silently replay an uncertain task.
        interrupted=db.execute("SELECT id FROM admin_tasks WHERE status='running'").fetchall()
        db.execute("UPDATE admin_tasks SET status='interrupted',summary='Worker interrupted; inspect local files before retry' WHERE status='running'")
        row=db.execute("SELECT id,idea FROM admin_tasks WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
        if row:db.execute("UPDATE admin_tasks SET status='running' WHERE id=?",(row[0],))
        db.commit()
    for r in interrupted:outbox.put(root,'task-interrupted:'+str(r[0]),'task','Задача №'+str(r[0])+' прервана. Требуется локальная проверка перед повтором.',150)
    if not row:return
    ident,idea=row;outbox.put(root,'task-start:'+str(ident),'task','Задача №'+str(ident)+' выполняется локально. Для публикации результата нужна отдельная команда /publish T'+str(ident)+'.',150)
    try:state,summary,artifact=execute(root,ident,idea)
    except Exception as exc:
        import traceback
        failure=root/'tasks'/str(ident);failure.mkdir(parents=True,exist_ok=True)
        (failure/'failure.log').write_text(traceback.format_exc(),encoding='utf-8')
        state,summary,artifact='failed','Выполнение остановлено ('+type(exc).__name__+'). Подробности сохранены локально в private/n8n/tasks/'+str(ident)+'. Проверка не подтверждена; публикации нет.',''
    with closing(outbox.database(root)) as db:
        db.execute('UPDATE admin_tasks SET status=?,summary=?,artifact=? WHERE id=?',(state,summary,artifact,ident));db.commit()
    outbox.put(root,'task-result:'+str(ident),'task','Задача №'+str(ident)+'\n'+summary,150)

if __name__=='__main__':worker(Path(os.environ['MAMA_TASK_ROOT']).resolve())
