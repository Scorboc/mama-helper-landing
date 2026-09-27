"""Production QA with isolated synthetic data; never modifies existing conversations."""
import copy, importlib.util, json, secrets, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

spec=importlib.util.spec_from_file_location('app',Path(sys.argv[1])/'index.py')
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
report={'checks':[], 'chat':[]}
class Client:
    def __init__(self, ip='198.51.100.21'): self.cookie='';self.ip=ip
    def call(self, action, expected=200, **data):
        req=urllib.request.Request('http://127.0.0.1:8787/api',data=json.dumps({'action':action,**data}).encode(),headers={'Content-Type':'application/json','Origin':'https://mama-helper-158-160-188-235.sslip.io','Cookie':self.cookie,'X-Real-IP':self.ip})
        try: res=urllib.request.urlopen(req,timeout=75)
        except urllib.error.HTTPError as error: res=error
        body=json.load(res)
        if res.headers.get('Set-Cookie'): self.cookie=res.headers['Set-Cookie'].split(';')[0]
        assert res.status==expected,(action,res.status,body.get('error'))
        return body

def mark(text): report['checks'].append(text);print('PASS: '+text,flush=True)

clients=[]; tokens=[]
try:
    for n in range(2):
        client=Client(f'198.51.100.{21+n}');password=secrets.token_urlsafe(24); email='qa-'+secrets.token_hex(8)+'@example.test'
        session=client.call('register',email=email,password=password,consent=True)
        clients.append((client,email,password))
        state=session['state']
        state['profile']=dict(childName='QA',childSex='unknown',role='mom',stage='child',birthDate=(date.today()-timedelta(days=400)).isoformat(),week=20,weekDate=date.today().isoformat(),feeding='unknown',sleep='',health='',healthConfirmed=False,topics=[])
        client.call('save',state=state,revision=0)
    c,email,password=clients[0]
    s=c.call('session');state=s['state']
    modified=copy.deepcopy(state);modified['profile']['birthDate']='2023-01-01'
    c.call('save',expected=403,state=modified,revision=s['revision'])
    modified=copy.deepcopy(state);modified['profile']=None
    c.call('save',expected=403,state=modified,revision=s['revision'])
    state['profile']['childName']='QA renamed'
    state['children']=[{'id':'second','data':{'profile':None,'messages':[],'medicalCard':[]}}]
    c.call('save',state=state,revision=s['revision'])
    assert clients[1][0].call('session')['state']['profile']['childName']=='QA'
    mark('profile lock, name change, new child and account isolation')
    c.call('save',expected=409,state=state,revision=s['revision'])
    mark('stale write rejected')
    plan=c.call('daily-plan',childId='primary');assert len(plan['items'])==3 and plan['source']=='ai'
    assert c.call('daily-plan',childId='primary')['items']==plan['items']
    c.call('daily-feedback',expected=400,childId='primary',day=plan['day'],version=plan['version'],itemId=plan['items'][0]['id'],kind='replace',reason='time',detail='',requestId='qa-replace')
    c.call('daily-seen',childId='primary',day=plan['day'])
    mark('real AI daily plan, stable reload, replacement explanation and seen status')
    records=json.loads(Path(sys.argv[2]).read_text())
    db=app.DB()
    for row in records:
        token=app.new_session(db,row['id']);tokens.append(token)
    db.conn.commit();db.close()
    def read_session(pair):
        idx,token=pair;client=Client(f'203.0.113.{idx+1}');client.cookie=app.COOKIE+'='+token
        started=time.monotonic();result=client.call('session')
        assert result['user']['id']==records[idx]['id'] and result['state']['profile'] is None
        return time.monotonic()-started
    with ThreadPoolExecutor(max_workers=50) as pool: times=list(pool.map(read_session,enumerate(tokens)))
    report['concurrent_sessions']={'success':len(times),'p95_seconds':round(sorted(times)[47],3),'max_seconds':round(max(times),3)}
    mark('50 concurrent individual sessions returned only their own empty profiles')
    questions=json.loads(Path(sys.argv[3]).read_text())
    def chat_batch(pair):
        group,client=pair;results=[]
        for index in range(group*25,(group+1)*25):
            s=client.call('session');started=time.monotonic()
            body=client.call('chat',question=questions[index],messageId=secrets.token_hex(12),revision=s['revision'])
            answer=body.get('answer','')
            fallback='безопасный резервный ответ' in answer or 'не успел ответить' in answer
            results.append({'number':index+1,'seconds':round(time.monotonic()-started,2),'ok':bool(answer) and not fallback,'question':questions[index],'answer':answer})
            print('CHAT '+str(index+1)+' '+('OK' if results[-1]['ok'] else 'FALLBACK'),flush=True)
        return results
    with ThreadPoolExecutor(max_workers=2) as pool:
        for rows in pool.map(chat_batch,[(0,clients[0][0]),(1,clients[1][0])]):report['chat'].extend(rows)
    s=c.call('session');state=s['state'];answer=next(m for m in state['messages'] if m['role']=='assistant')
    state['favorites']=[dict(id=answer['id'],childId='primary',childName='QA renamed',text=answer['text'][:2500],question='QA',savedAt=date.today().isoformat()+'T12:00:00Z')]
    c.call('save',state=state,revision=s['revision'])
    assert len(c.call('session')['state']['favorites'])==1
    c.call('logout');c.call('session',expected=401)
    c.call('login',email=email,password=password)
    assert len(c.call('session')['state']['messages'])==50
    mark('favorites, 25 question/answer pairs preserved after logout and login')
finally:
    for client,email,password in clients:
        try: client.call('delete',password=password)
        except Exception: print('QA account cleanup needs inspection',flush=True)
    db=app.DB()
    for token in tokens: db.query('DELETE FROM mh_sessions WHERE token_hash=?',(app.digest(token),))
    db.conn.commit();db.close()
    report['chat_success']=sum(x['ok'] for x in report['chat'])
    Path('/tmp/beta-qa-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='chat'},ensure_ascii=False),flush=True)
