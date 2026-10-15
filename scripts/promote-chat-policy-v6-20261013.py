"""Preserve v5 and promote explicit rules from authorized synthetic QA."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
directory=ROOT/'backend/parent-app/prompts'
old=json.loads((directory/'reviewed-20261013-v5.json').read_text(encoding='utf-8'))
addition='''

### 21. Проверка смысла после расширенного теста

Вопрос «ребёнок не делится игрушками, как реагировать?» требует ответа о поведении,
а не только каталожной игры. Названная игра не разрешает стирать объяснение и границу
безопасности. При прямом игровом запросе выбирай каталог; остальные вопросы отвечай
по существу. Уточнение действительно недостающего факта допустимо; не заканчивай
каждый ответ предложением «хотите, могу подсказать ещё / расскажу подробнее».
До первого дня рождения в кроватке нет мягких игрушек, подушек и свободных одеял.
Перевороты не разрешают мягкий предмет. Белый шум необязателен; устройство как можно
дальше от младенца, вне кроватки, самая низкая громкость, ограниченное время.
Не ставь у изголовья и не обещай безопасную громкость по сравнению с разговором.
Фраза «потом станет легче, и мы увидим новый навык» тоже обещает результат.
Вместо этого: «Сейчас трудно. Можно наблюдать изменения без обещания срока».
Не обещай будущую умелку, улучшение сна или психическое здоровье из одного действия.
Эмпатия не должна отменять неопределённость и своевременную очную помощь.
'''
version='mama-reviewed-20261013-v6'
manifest={'version':version,'approvedAt':'2026-10-13','approval':'Owner-authorized local iterative QA; preserves v5 and records observed meaning/sleep/noise defects.','parts':{}}
for name,item in old['parts'].items():
    source=(directory/item['file']).read_bytes()
    assert hashlib.sha256(source).hexdigest()==item['sha256']
    text=source.decode('utf-8').replace('\r\n','\n')
    if name=='chat':text=text.rstrip()+addition
    data=text.encode('utf-8');file=f'{name}-reviewed-20261013-v6.md'
    target=directory/file
    if target.exists():assert target.read_bytes()==data,'Do not replace an already reviewed version'
    else:target.write_bytes(data)
    manifest['parts'][name]={'file':file,'sha256':hashlib.sha256(data).hexdigest()}
    if name=='chat':chat=text
assert len(chat.encode())<39000
(directory/'reviewed-20261013-v6.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=ROOT/'docs/ai/MAMA_SYSTEM_PROMPT_DRAFT.md';draft=p.read_text(encoding='utf-8')
head,tail=draft.split('## Системный промпт\n',1);_,after=tail.split('## Отдельные режимы:',1)
p.write_text(head+'## Системный промпт\n\n'+chat.strip()+'\n\n## Отдельные режимы:'+after,encoding='utf-8')
for filename in ('backend/parent-app/prompt_policy.py','backend/parent-app/test_prompt_policy.py'):
    p=ROOT/filename;text=p.read_text(encoding='utf-8').replace('mama-reviewed-20261013-v5',version).replace('reviewed-20261013-v5.json','reviewed-20261013-v6.json');p.write_text(text,encoding='utf-8')
print(json.dumps({'version':version,'chatBytes':len(chat.encode())}))
