"""Run on the VM; exercise the real provider using a disposable account."""
import json
import secrets
import urllib.request
import urllib.error
from datetime import date, timedelta

token=''
def call(action,expected=200,**data):
    global token
    request=urllib.request.Request('http://127.0.0.1:8787/api',data=json.dumps(dict(action=action,**data)).encode(),headers={'Content-Type':'application/json','Origin':'https://mama-helper-158-160-188-235.sslip.io','Cookie':token})
    try: response=urllib.request.urlopen(request,timeout=70)
    except urllib.error.HTTPError as exc: response=exc
    body=json.load(response)
    if response.headers.get('Set-Cookie'): token=response.headers['Set-Cookie'].split(';')[0]
    assert response.status==expected, (action,response.status,body.get('error'))
    return body

password=secrets.token_urlsafe(24)
session=call('register',email='daily-qa-'+secrets.token_hex(6)+'@example.test',password=password,consent=True)
try:
    state=session['state']
    state['profile']={'childName':'Проверка','childSex':'unknown','role':'mom','stage':'child','birthDate':(date.today()-timedelta(days=100)).isoformat(),'week':20,'weekDate':date.today().isoformat(),'feeding':'unknown','sleep':'','health':'','healthConfirmed':False,'topics':[]}
    call('save',state=state,revision=session['revision'])
    plan=call('daily-plan',childId='primary')
    assert len(plan['items'])==3
    assert plan['source']=='ai', 'Real AI daily selection unavailable'
    assert call('daily-plan',childId='primary')['items']==plan['items']
    request=dict(childId='primary',day=plan['day'],version=plan['version'],itemId=plan['items'][0]['id'],kind='replace',requestId=secrets.token_hex(12),reason='materials')
    call('daily-feedback',expected=400,**request,detail='')
    changed=call('daily-feedback',**request,detail='Нет книг и игрушек, нужна спокойная игра без предметов.')
    assert changed['items'][0]['id']!=plan['items'][0]['id']
    assert changed['items'][0]['selection']=='ai'
    assert changed['items'][0]['materials']=='Ничего'
    retried=call('daily-feedback',**request,detail='Нет книг и игрушек, нужна спокойная игра без предметов.')
    assert retried['version']==changed['version']
    assert call('daily-plan',childId='primary')['items']==changed['items']
    print('PASS: real YandexGPT selection and reason analysis; required explanation; saved plan; idempotent replacement',flush=True)
finally:
    call('delete',password=password)
    print('Disposable account removed',flush=True)
