"""Read-only ProxyAPI balance monitor. Fixed HTTPS endpoint; no model calls or payments."""
import json,os,time,urllib.request,urllib.error
from contextlib import closing
from decimal import Decimal,InvalidOperation
import telegram_outbox as outbox

CONSOLE='https://console.proxyapi.ru/'
DOCS='https://proxyapi.ru/docs/balance'
PAYMENTS=('Оплаты и пополнения\nProxyAPI: '+CONSOLE+' → Баланс. По документации доступны банковская карта и СБП; подходящий способ проверяйте на странице оплаты.\n'
 'Codex: https://chatgpt.com/ → настройки подписки. Цену, налоги и доступные способы оплаты проверяйте в вашем аккаунте.\n'
 'Локальный n8n: отдельная подписка не требуется. Новый сервер: провайдер и платёжная ссылка ещё не заданы.\n'
 'Какую вашу карту использовать, сколько денег на ней и как её пополнить — пока неизвестно. Можно сохранить понятное название карты без номера, а инструкции выдавать по подтверждённым вами данным. Ключ ProxyAPI не даёт доступа к картам.\n'
 'Бот не переводит деньги, не пополняет карты и не включает автосписания. Баланс ProxyAPI и баланс банковской карты — разные вещи. Официальная инструкция: '+DOCS)

def prepare(db):db.execute('CREATE TABLE IF NOT EXISTS proxy_balance_state(k TEXT PRIMARY KEY,v TEXT)')
def get(db,key,default=None):
    row=db.execute('SELECT v FROM proxy_balance_state WHERE k=?',(key,)).fetchone();return json.loads(row[0]) if row else default
def setv(db,key,value):db.execute('INSERT OR REPLACE INTO proxy_balance_state VALUES(?,?)',(key,json.dumps(value)))

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def fetch(key):
    if not key:return {'ok':False,'error':'key-missing'}
    req=urllib.request.Request('https://api.proxyapi.ru/proxyapi/balance',headers={'Authorization':'Bearer '+key,'Accept':'application/json'})
    try:
        opener=urllib.request.build_opener(NoRedirect())
        with opener.open(req,timeout=12) as response:raw=json.loads(response.read(16384),parse_float=Decimal)
        if not isinstance(raw,dict):raise ValueError('invalid-response')
        amount=raw.get('balance')
        if isinstance(amount,bool) or not isinstance(amount,(int,Decimal)):raise ValueError('invalid-amount')
        value=Decimal(amount)
        if not value.is_finite() or abs(value)>Decimal('1000000000000'):raise ValueError('invalid-amount')
        return {'ok':True,'balance':str(value),'scope':'key-budget' if isinstance(raw.get('budget'),dict) else 'account','currency':'RUB'}
    except urllib.error.HTTPError as exc:return {'ok':False,'error':'permission-required' if exc.code==403 else 'authentication-failed' if exc.code==401 else 'rate-limited' if exc.code==429 else 'provider-unavailable','httpStatus':exc.code}
    except (urllib.error.URLError,OSError,ValueError,InvalidOperation):return {'ok':False,'error':'provider-unavailable'}

def collect(root):
    now=int(time.time())
    with closing(outbox.database(root)) as db:
        prepare(db);db.execute('BEGIN IMMEDIATE');previous=get(db,'latest',{});refresh=get(db,'refresh',False)
        interval=900 if previous.get('ok',True) else 3600
        if now-get(db,'last_attempt',0)<(60 if refresh else interval):return
        old_low=get(db,'low',False);thresholds=get(db,'thresholds',[500,200,50])
        # Reserve the polling slot before network I/O so parallel collectors do not fan out.
        setv(db,'last_attempt',now);setv(db,'refresh',False);db.commit()
    result=fetch(os.environ.get('PROXYAPI_API_KEY'));result['checkedAt']=now
    with closing(outbox.database(root)) as db:
        setv(db,'latest',result)
        if result['ok']:
            setv(db,'last_success',result);amount=Decimal(result['balance']);level=sum(amount<=Decimal(t) for t in thresholds)
            setv(db,'low',level>0)
        db.commit()
    if not result['ok']:
        reason='Для ключа включите «Запрос баланса» в разделе Ключи API. Ответ 403 не доказывает, что баланс нулевой.' if result['error']=='permission-required' else 'Проверка недоступна; остаток неизвестен. Проверьте доступ к API и ключ локально.'
        outbox.put(root,'proxy-check-error:'+result['error']+':'+str(now//86400),'balance','MAMA: баланс ProxyAPI не проверен.\n'+reason+'\n'+CONSOLE,170);return
    label='Остаток бюджета ключа (не баланс аккаунта)' if result['scope']=='key-budget' else 'Баланс аккаунта'
    if level:
        action='Проверьте бюджет ключа и общий баланс в кабинете; одно пополнение аккаунта может не снять лимит ключа.' if result['scope']=='key-budget' else 'Пополнить: кабинет → Баланс → карта или СБП.'
        outbox.put(root,'proxy-low:'+result['scope']+':'+str(level)+':'+str(now//86400),'balance',f'MAMA: мало средств ProxyAPI\n{label}: {result["balance"]} ₽.\nПороги предупреждений: '+', '.join(str(t)+' ₽' for t in thresholds)+'\n'+action+'\n'+CONSOLE+'\nКарта для оплаты не выбрана; списания не выполняются.',180+level)
    elif old_low:
        outbox.put(root,'proxy-recovered:'+str(now),'balance',f'MAMA: остаток ProxyAPI снова выше порога предупреждения.\n{label}: {result["balance"]} ₽. Это не подтверждение банковской операции.',120)

def command(db,cmd,tail):
    prepare(db)
    if cmd=='/payments':return PAYMENTS
    if cmd=='/balance_alerts':
        try:
            values=[int(x) for x in tail.split()]
            if len(values)!=3 or not (1000000>=values[0]>values[1]>values[2]>0):raise ValueError()
            setv(db,'thresholds',values);return 'Пороги сохранены: '+', '.join(str(v)+' ₽' for v in values)+'. Проверка примерно каждые 15 минут; при ошибке — раз в час. /balance — статус.'
        except ValueError:return 'Укажите три убывающих порога в рублях. Пример: /balance_alerts 500 200 50'
    setv(db,'refresh',True);latest=get(db,'latest',{});success=get(db,'last_success',{})
    if not latest:return 'Первый запрос баланса запланирован. Повторите /balance примерно через минуту. /payments — ссылки и способы оплаты.'
    if not latest.get('ok'):
        reason='нужно разрешение «Запрос баланса» для ключа' if latest.get('error')=='permission-required' else 'проверка недоступна'
        text='Текущий баланс неизвестен: '+reason+'.\n'+CONSOLE
        if success:text+='\nПоследнее успешное значение: '+success['balance']+' ₽; сейчас может быть неактуально.'
        return text+'\nПовторная проверка запрошена. /payments — помощь.'
    age=max(0,int(time.time())-latest['checkedAt'])//60
    label='Остаток бюджета ключа, НЕ баланс аккаунта' if latest['scope']=='key-budget' else 'Баланс аккаунта'
    return f'{label}: {latest["balance"]} ₽.\nПроверено {age} мин. назад. Обновление запрошено.\nПороги: '+', '.join(str(t)+' ₽' for t in get(db,'thresholds',[500,200,50]))+'\n'+CONSOLE+'\n/payments — способы оплаты.'
