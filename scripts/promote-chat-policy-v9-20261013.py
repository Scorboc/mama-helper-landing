"""Record the observed UI and furniture corrections without modifying old versions."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'backend/parent-app/prompts'
old=json.loads((D/'reviewed-20261013-v8.json').read_text(encoding='utf-8'))
extra='''

### 22. Проверенные пути и обстановка

Push отключают: «Профиль → Настройки и уведомления → Отключить push».
«Данные и обращения» не экран управления напоминаниями. Разрешение браузера
отдельно меняется в настройках сайта браузера. Не советуй поднимать тяжёлую мебель
на высоту: её закрепляют по инструкции производителя, доступ к опасной зоне закрывают.
'''
v='mama-reviewed-20261013-v9';m={'version':v,'approvedAt':'2026-10-13','approval':'Owner-authorized QA corrections for actual reminder controls and furniture safety.','parts':{}}
for name,item in old['parts'].items():
    data=(D/item['file']).read_bytes();assert hashlib.sha256(data).hexdigest()==item['sha256']
    if name=='chat':data=data.decode().rstrip().encode()+extra.encode()
    file=f'{name}-reviewed-20261013-v9.md';p=D/file
    if p.exists():assert p.read_bytes()==data
    else:p.write_bytes(data)
    m['parts'][name]={'file':file,'sha256':hashlib.sha256(data).hexdigest()}
    if name=='chat':chat=data.decode()
assert len(chat.encode())<39000
(D/'reviewed-20261013-v9.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=ROOT/'docs/ai/MAMA_SYSTEM_PROMPT_DRAFT.md';head,tail=p.read_text(encoding='utf-8').split('## Системный промпт\n',1);_,after=tail.split('## Отдельные режимы:',1)
p.write_text(head+'## Системный промпт\n\n'+chat.strip()+'\n\n## Отдельные режимы:'+after,encoding='utf-8')
for file in ('backend/parent-app/prompt_policy.py','backend/parent-app/test_prompt_policy.py'):
    p=ROOT/file;text=p.read_text(encoding='utf-8').replace('mama-reviewed-20261013-v8',v).replace('reviewed-20261013-v8.json','reviewed-20261013-v9.json');p.write_text(text,encoding='utf-8')
print(json.dumps({'version':v,'chatBytes':len(chat.encode())}))
