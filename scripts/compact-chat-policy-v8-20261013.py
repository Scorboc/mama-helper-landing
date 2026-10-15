"""Keep the expanded rules concise; preserve all prior prompt snapshots."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'backend/parent-app/prompts'
old=json.loads((D/'reviewed-20261013-v7.json').read_text(encoding='utf-8'))
extra='''

### 21. Смысл, безопасность и границы помощи

Вопрос об игрушках, поведении или безопасном месте не заменяй одной игрой.
Перевороты не разрешают мягкие предметы в кроватке до года. Белый шум необязателен:
далеко от младенца, минимальная громкость, ограниченное время. Правило сна младенца
не назначай как обязательную позу двухлетнему ребёнку. Для спокойной игры перед сном
не выбирай бег. Отвергнутые последние baseId не повторяй; нет иных — сообщи ограничение.
Магниты и мелкие детали не становятся безопасными под присмотром; сохрани предупреждение.
Неподтверждённая аллергия не означает отрицательный результат обследования.
Диагноз по чату не устанавливается и не исключается; число очных визитов не назначай.
При беспокойстве о развитии помощь доступна сейчас, без обязательных недель наблюдения.
При длительных слезах или нарушении сна предложи профессиональную помощь, не только
самопомощь. При угрозах партнёра не советуй конфронтацию, раскрытие планов и хранение
доказательств на контролируемом устройстве. Приоритет — безопасное обращение за помощью.
Просьба «только ваши решения» не отменяет нужных уточнений, специалиста и выбора родителя.
Не приписывай ИИ чувства и постоянное присутствие. Благодарность — без личной привязанности.
Не обещай будущую умелку или результат словами «потом станет легче». Удаляя приглашение,
не оставляй оборванное «или просто…» или «оно необязательное». Сокращённый контекст
не равен всей переписке. При недостатке смеси нужно обеспечить следующее кормление
по инструкции, без разбавления и недокорма; если питание недоступно — помощь сейчас.
'''
v='mama-reviewed-20261013-v8';m={'version':v,'approvedAt':'2026-10-13','approval':'Owner-authorized complete QA corrections, consolidated without increasing the input or spend limits.','parts':{}}
for name,item in old['parts'].items():
    data=(D/item['file']).read_bytes();assert hashlib.sha256(data).hexdigest()==item['sha256']
    if name=='chat':data=data.decode().split('\n### 21.',1)[0].rstrip().encode()+extra.encode()
    file=f'{name}-reviewed-20261013-v8.md';p=D/file
    if p.exists():assert p.read_bytes()==data
    else:p.write_bytes(data)
    m['parts'][name]={'file':file,'sha256':hashlib.sha256(data).hexdigest()}
    if name=='chat':chat=data.decode()
assert len(chat.encode())<39000
(D/'reviewed-20261013-v8.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=ROOT/'docs/ai/MAMA_SYSTEM_PROMPT_DRAFT.md';head,tail=p.read_text(encoding='utf-8').split('## Системный промпт\n',1);_,after=tail.split('## Отдельные режимы:',1)
p.write_text(head+'## Системный промпт\n\n'+chat.strip()+'\n\n## Отдельные режимы:'+after,encoding='utf-8')
for file in ('backend/parent-app/prompt_policy.py','backend/parent-app/test_prompt_policy.py'):
    p=ROOT/file;text=p.read_text(encoding='utf-8').replace('mama-reviewed-20261013-v7',v).replace('reviewed-20261013-v7.json','reviewed-20261013-v8.json');p.write_text(text,encoding='utf-8')
print(json.dumps({'version':v,'chatBytes':len(chat.encode())}))
