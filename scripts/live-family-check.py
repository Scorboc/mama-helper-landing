"""Exercise production persistence only with a disposable synthetic account."""
import copy
import http.cookiejar
import json
import secrets
import os
import subprocess
import tempfile
import urllib.request
from datetime import date

base = 'https://mama-helper-158-160-188-235.sslip.io'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
temp = tempfile.TemporaryDirectory()
def call(action, **data):
    result=subprocess.run(['curl.exe' if os.name == 'nt' else 'curl','--noproxy','*','--max-time','20','--fail-with-body','-sS','-b',temp.name+'/cookies','-c',temp.name+'/cookies','-H','Content-Type: application/json','-H','Origin: '+base,'--data-binary','@-',base+'/api'],input=json.dumps({'action':action,**data}).encode(),capture_output=True)
    if result.returncode: raise RuntimeError('Production request failed: '+str(result.returncode))
    return json.loads(result.stdout)
email='family-qa-'+secrets.token_hex(6)+'@example.test'
password=secrets.token_urlsafe(24)
session=call('register',email=email,password=password,consent=True)
try:
    first=copy.deepcopy(session['state'])
    first['profile']={'childName':'Тест Первый','childSex':'unknown','role':'mom','stage':'child','birthDate':'2025-01-01','week':20,'weekDate':date.today().isoformat(),'feeding':'unknown','sleep':'','health':'','healthConfirmed':False,'topics':[]}
    first['messages']=[{'id':'qa-question','role':'user','text':'Тестовый вопрос'}, {'id':'qa-answer','role':'assistant','text':'Тестовый сохранённый ответ'}]
    second=copy.deepcopy(first)
    second['profile']['childName']='Тест Второй'
    second['messages']=[]
    first['activeChildId']='primary'
    child_keys=['profile','messages','medicalCard','pendingMemory','conversations','conversationTitle','conversationId','conversationOrder','events','care','saved','completed']
    first['children']=[{'id':'second','data':{k:v for k,v in second.items() if k in child_keys}}]
    first['favorites']=[{'id':'qa-answer','childId':'primary','childName':'Тест Первый','text':'Тестовый сохранённый ответ','question':'Тестовый вопрос','savedAt':'2026-09-20T12:00:00Z'}]
    revision=call('save',state=first,revision=session['revision'])['revision']
    second={**first, **first['children'][0]['data'], 'activeChildId':'second','children':[{'id':'primary','data':{k:v for k,v in first.items() if k in child_keys}}]}
    call('save',state=second,revision=revision)
    call('logout')
    loaded=call('login',email=email,password=password)['state']
    assert loaded['profile']['childName']=='Тест Второй'
    assert loaded['messages']==[]
    assert loaded['children'][0]['data']['messages']==first['messages']
    assert loaded['favorites']==first['favorites']
    print('PASS: HTTPS production register/save/switch/relogin; first child history and favorites preserved')
finally:
    call('delete',password=password)
    print('Disposable test account removed')
    temp.cleanup()
