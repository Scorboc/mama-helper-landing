"""Generate one local scheduled/manual workflow, reusing an existing credential."""
import json,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'app/automation/n8n'
base=json.loads((DEST/'mamaLocal17.json').read_text(encoding='utf-8'))
base.update(id='mamaLocal19',name='MAMA 19 — Анализировать отзывы и подготовить предложения',active=False,
    description='Каждые 30 минут локально классифицирует отзывы. ИИ получает только enum-счётчики, готовит проекты правил владельцу; не более одного вызова в сутки, 1 ₽/день и 10 ₽/месяц внутри общего бюджета. Переписку не экспортирует, правила не меняет.')
for node in base['nodes']:
    node['id']=str(uuid.uuid4())
    if node['type']=='n8n-nodes-base.scheduleTrigger':
        node['parameters']['rule']['interval']=[{'field':'cronExpression','expression':'*/30 * * * *'}]
    elif node['type']=='n8n-nodes-base.httpRequest':
        node['parameters']['url']='http://127.0.0.1:8792/jobs/feedback-analysis'
        node['parameters']['options']['timeout']=100000
        node['notes']='Без входных данных. Токен — в существующем credential mamaBridgeLocalOnly. Idempotency-Key сохраняется при HTTP-повторах; оплаченный вызов ИИ внутри задания не повторяется.'
    elif node['type']=='n8n-nodes-base.stickyNote':
        node['parameters']['content']='### Только предложения владельцу\nКомментарии и разрешённый контекст читаются локально. Внешнему ИИ — только категории и числа. Негативная оценка не доказывает ошибку. Не публикует и не меняет правила. Результат: http://127.0.0.1:8791/#feedback-review'
base['versionId']=str(uuid.uuid4())
(DEST/'mamaLocal19.json').write_text(json.dumps(base,ensure_ascii=False,indent=2),encoding='utf-8')
qa=json.loads(json.dumps(base));qa.update(id='mamaFeedbackQA',name='MAMA QA — Synthetic feedback only',active=False,versionId=str(uuid.uuid4()))
qa['nodes']=[n for n in qa['nodes'] if n['type']!='n8n-nodes-base.scheduleTrigger']
qa['connections'].pop('По расписанию',None)
for node in qa['nodes']:
    if node['type']=='n8n-nodes-base.httpRequest':node['parameters']['url']='http://127.0.0.1:8793/jobs/feedback-analysis'
(ROOT/'outputs/qa-feedback-n8n-20261013/workflow-qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'generated':['mamaLocal19','mamaFeedbackQA'],'secretsInWorkflow':False}))
