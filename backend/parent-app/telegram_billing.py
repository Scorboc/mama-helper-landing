"""Manual recurring expense register; never charges a card or assumes a provider payment."""
import calendar,re
from decimal import Decimal,InvalidOperation
from datetime import date,datetime,timedelta,timezone
from contextlib import closing
import telegram_outbox as outbox

GUIDE=('Расходы и продления\n'
 '/bills — список и план расходов по валютам.\n'
 '/bill_add Название | сумма | валюта | YYYY-MM-DD | monthly\n'
 'Периоды: monthly, yearly, once. Пример (не ваши фактические расходы):\n'
 '/bill_add Сервер | 1500 | RUB | 2026-11-01 | monthly\n'
 '/paid ID YYYY-MM-DD — вручную подтвердить оплату именно указанного срока; бот перенесёт следующий срок.\n'
 '/bill_pause ID — отключить напоминания. Повторный bill_add с тем же названием обновляет запись и включает её.\n'
 'Напоминания: за 7, 3, 1 день, в день оплаты и раз в неделю при просрочке. Если компьютер был выключен — при запуске придёт актуальное напоминание, без пачки старых.\n'
 'Нет доступа к банку: суммы и даты платежей вводите вы. Бот не списывает деньги и не подтверждает банковскую оплату сам. /balance — проверка остатка ProxyAPI при наличии разрешения у ключа; /payments — официальные ссылки. Не присылайте карты и ключи.')

def today():return datetime.now(timezone(timedelta(hours=4))).date()
def prepare(db):
    db.execute('CREATE TABLE IF NOT EXISTS admin_bills(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE COLLATE NOCASE,amount TEXT,currency TEXT,due TEXT,cadence TEXT,anchor INTEGER,enabled INTEGER DEFAULT 1)')
    db.execute('CREATE TABLE IF NOT EXISTS admin_bill_payments(bill_id INTEGER,due TEXT,marked_on TEXT,PRIMARY KEY(bill_id,due))')
def next_due(due,cadence,anchor):
    year=due.year+(1 if cadence=='yearly' or due.month==12 else 0)
    month=due.month if cadence=='yearly' else due.month%12+1
    return date(year,month,min(anchor,calendar.monthrange(year,month)[1]))

def command(db,cmd,tail):
    prepare(db)
    if cmd=='/billing_help':return GUIDE
    if cmd=='/bill_add':
        try:
            name,amount,currency,due,cadence=[x.strip() for x in tail.split('|')]
            if not re.fullmatch(r'[\w .()—–+-]{1,60}',name):raise ValueError()
            value=Decimal(amount.replace(',','.'))
            if not value.is_finite() or value<=0 or value>1000000 or value.as_tuple().exponent < -2:raise ValueError()
            currency=currency.upper()
            if not re.fullmatch('[A-Z]{3}',currency) or cadence not in ('monthly','yearly','once'):raise ValueError()
            day=date.fromisoformat(due)
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',due) or day.year<2020 or day.year>2100:raise ValueError()
            db.execute('INSERT INTO admin_bills(name,amount,currency,due,cadence,anchor,enabled) VALUES(?,?,?,?,?,?,1) ON CONFLICT(name) DO UPDATE SET amount=excluded.amount,currency=excluded.currency,due=excluded.due,cadence=excluded.cadence,anchor=excluded.anchor,enabled=1',(name,str(value),currency,due,cadence,day.day))
            ident=db.execute('SELECT id FROM admin_bills WHERE name=?',(name,)).fetchone()[0]
            db.execute("UPDATE messages SET state='cancelled' WHERE state='queued' AND id LIKE ?",('bill:'+str(ident)+':%',))
            return 'Платёж сохранён по вашим данным. Фактическое списание не проверялось.\n'+listing(db)
        except (ValueError,InvalidOperation):return 'Не удалось прочитать платёж.\n'+GUIDE
    if cmd=='/bills':return listing(db)
    if cmd=='/bill_pause':
        if not tail.strip().isdigit():return 'Укажите /bill_pause ID из /bills.'
        changed=db.execute('UPDATE admin_bills SET enabled=0 WHERE id=?',(int(tail),)).rowcount
        db.execute("UPDATE messages SET state='cancelled' WHERE state='queued' AND id LIKE ?",('bill:'+str(int(tail))+':%',))
        return 'Напоминания отключены; история сохранена.' if changed else 'Запись не найдена.'
    if cmd=='/paid':
        try:
            ident,stamp=tail.split();ident=int(ident);day=date.fromisoformat(stamp)
        except ValueError:return 'Укажите /paid ID YYYY-MM-DD. Дату срока возьмите из /bills; это ручная отметка оплаты.'
        row=db.execute('SELECT * FROM admin_bills WHERE id=?',(ident,)).fetchone()
        if not row:return 'Запись не найдена.'
        if db.execute('SELECT 1 FROM admin_bill_payments WHERE bill_id=? AND due=?',(ident,stamp)).fetchone():return 'Этот срок уже отмечен оплаченным; повтор не изменил следующую дату.'
        if row['due']!=stamp:return 'Дата не совпадает с текущим сроком. Проверьте /bills. Ничего не изменено.'
        db.execute('INSERT INTO admin_bill_payments VALUES(?,?,?)',(ident,stamp,today().isoformat()))
        db.execute("UPDATE messages SET state='cancelled' WHERE state='queued' AND id LIKE ?",('bill:'+str(ident)+':'+stamp+':%',))
        if row['cadence']=='once':db.execute('UPDATE admin_bills SET enabled=0 WHERE id=?',(ident,));return 'Оплата отмечена вами. Разовый платёж закрыт.'
        following=next_due(day,row['cadence'],row['anchor']).isoformat()
        db.execute('UPDATE admin_bills SET due=? WHERE id=?',(following,ident))
        return 'Оплата отмечена вами. Следующий срок: '+following+'. Подтверждение провайдера не проверялось.'
    return GUIDE

def listing(db):
    rows=db.execute('SELECT * FROM admin_bills WHERE enabled=1 ORDER BY due,id').fetchall()
    if not rows:return 'Расходы пока не внесены. /billing_help — инструкция. Добавьте сервер, Codex, ИИ API, домен и остальные оплачиваемые сервисы. Суммы не угаданы.'
    lines=['План по вашим данным (не банковские списания):'];totals={}
    for r in rows[:15]:
        lines.append(f"#{r['id']} {r['name']}: {r['amount']} {r['currency']}; {r['due']}; {r['cadence']}")
    for r in rows:
        if r['cadence']!='once':totals[r['currency']]=totals.get(r['currency'],Decimal(0))+Decimal(r['amount'])/(12 if r['cadence']=='yearly' else 1)
    if len(rows)>15:lines.append('Всего активных записей: '+str(len(rows))+'. Показаны ближайшие 15.')
    if totals:lines.append('Средний план в месяц (годовые /12; без разовых): '+', '.join(f'{v.quantize(Decimal("0.01"))} {k}' for k,v in sorted(totals.items()))+'; валюты не складываются.')
    return '\n'.join(lines)

def collect(root):
    day=today()
    with closing(outbox.database(root)) as db:
        prepare(db);rows=db.execute('SELECT * FROM admin_bills WHERE enabled=1').fetchall();db.commit()
    for r in rows:
        delta=(date.fromisoformat(r['due'])-day).days
        if delta>7:continue
        phase='7' if delta>3 else '3' if delta>1 else '1' if delta==1 else 'due' if delta==0 else 'overdue:'+str((-delta-1)//7)
        label=f'срок через {delta} дн.' if delta>0 else 'срок сегодня' if delta==0 else f'срок прошёл {-delta} дн. назад (оплата не отмечена)'
        outbox.put(root,f"bill:{r['id']}:{r['due']}:{phase}",'billing',f"MAMA: продление сервиса\n{r['name']}: {r['amount']} {r['currency']}\n{label}. Дата: {r['due']}.\nПосле оплаты: /paid {r['id']} {r['due']}\nЭто напоминание по вашему реестру; фактическое списание не проверялось.",130)
