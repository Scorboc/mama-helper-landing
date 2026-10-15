"""Local installation: owned processes only, CLI import and connection verification.

Does not create credentials: reuses mamaBridgeLocalOnly already stored in n8n.
Run --prepare, test the workflow, then --activate. No cloud deployment.
"""
from contextlib import closing
import json,os,socket,sqlite3,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
N8N=ROOT/'private/n8n'
OUT=ROOT/'outputs/qa-feedback-n8n-20261013'
sys.path.insert(0,str(N8N))
from runtime_tools import n8n_env,NODE,CLI
BACKEND=ROOT/'app/backend/parent-app'
FILE=ROOT/'app/automation/n8n/mamaLocal19.json'
DB=N8N/'state/.n8n/database.sqlite'
def cli(args):
    with (N8N/'feedback-setup.log').open('ab') as log:
        result=subprocess.run([str(NODE),str(CLI),*args],env=n8n_env(),cwd=N8N,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError('Local n8n CLI failed: '+args[0])
def verify(published=False):
    expected=json.loads(FILE.read_text(encoding='utf-8'))
    with closing(sqlite3.connect('file:'+DB.as_posix()+'?mode=ro',uri=True)) as db:
        cred=db.execute('SELECT name,type FROM credentials_entity WHERE id=?',('mamaBridgeLocalOnly',)).fetchone()
        assert cred and cred[1]=='httpHeaderAuth','Existing local credential missing'
        row=db.execute('SELECT nodes,connections,settings,active,activeVersionId FROM workflow_entity WHERE id=?',('mamaLocal19',)).fetchone()
        assert row and json.loads(row[0])==expected['nodes'] and json.loads(row[1])==expected['connections']
        assert json.loads(row[2])['errorWorkflow']=='mamaLocal18'
        if published:assert row[3] and row[4]
        return {'connectionsVerified':True,'existingCredentialBound':True,'errorWorkflow':'mamaLocal18','publishedLocally':bool(row[3]),'workflowId':'mamaLocal19'}
def stop_owned_pid(pid,path):
    query=f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}'; if($p){{$p.CommandLine}}"
    command=subprocess.run(['powershell','-NoProfile','-Command',query],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True).stdout.strip()
    if not command:return
    if str(path).lower() not in command.lower():raise RuntimeError('Refusing to stop unrelated process')
    subprocess.run(['powershell','-NoProfile','-Command',f'Stop-Process -Id {int(pid)} -ErrorAction Stop'],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
def restart():
    status=json.loads((N8N/'status.json').read_text())
    stop_owned_pid(status['supervisorPid'],N8N/'launcher.py')
    ports={8787:BACKEND/'local_server.py',8791:BACKEND/'ops_server.py',8792:BACKEND/'automation_bridge.py',5678:CLI}
    query='$p=Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 8787,8791,8792,5678 | Select-Object LocalPort,OwningProcess; ConvertTo-Json -InputObject @($p) -Compress'
    entries=json.loads(subprocess.run(['powershell','-NoProfile','-Command',query],capture_output=True,text=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW).stdout)
    stopped=[]
    for entry in entries:
        stop_owned_pid(entry['OwningProcess'],ports[entry['LocalPort']]);stopped.append(entry['OwningProcess'])
    for _ in range(20):
        open_ports=[]
        for port in ports:
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.2):open_ports.append(port)
            except OSError:pass
        if not open_ports:break
        time.sleep(1)
    else:raise RuntimeError('Owned service did not release port: '+str(open_ports))
    with (N8N/'supervisor.log').open('ab') as log:
        p=subprocess.Popen([sys.executable,str(N8N/'launcher.py')],cwd=N8N,stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(45):
        time.sleep(1)
        try:
            fresh=json.loads((N8N/'status.json').read_text())
            if fresh['supervisorPid']==p.pid and all(fresh['services'].values()):break
        except Exception:pass
    else:raise RuntimeError('Services not ready after local restart')
    processes=json.loads((ROOT/'private/local-runtime/processes.json').read_text())
    for item in processes:
        if item['name'] in fresh['pids']:item['pid']=fresh['pids'][item['name']]
    (ROOT/'private/local-runtime/processes.json').write_text(json.dumps(processes),encoding='utf-8')
    with urllib.request.urlopen('http://127.0.0.1:8791/data',timeout=15) as response:
        assert json.load(response).get('feedbackReview',{}).get('version')=='feedback-aggregate-review-v1','Owner service did not load new module'
    return {'supervisorPid':p.pid,'services':fresh['services'],'stoppedOwnedPids':stopped}
if sys.argv[1]=='--prepare':
    with closing(sqlite3.connect('file:'+DB.as_posix()+'?mode=ro',uri=True)) as db:
        assert db.execute('SELECT type FROM credentials_entity WHERE id=?',('mamaBridgeLocalOnly',)).fetchone()==('httpHeaderAuth',)
    cli(['import:workflow','--input='+str(FILE)])
    result=verify();(OUT/'workflow-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
elif sys.argv[1]=='--activate':
    assert json.loads((OUT/'browser.json').read_text())['ok']
    verify();cli(['publish:workflow','--id=mamaLocal19'])
    result={**verify(True),**restart()}
    (OUT/'activation.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
elif sys.argv[1]=='--restart':
    result={**verify(True),**restart()}
    (OUT/'activation.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
else:raise SystemExit('Use --prepare or --activate')
