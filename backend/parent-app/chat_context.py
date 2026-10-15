"""Bound provider context without changing stored state or current diary totals."""
import copy,json,re

NOTICE=('Контекст сокращён по размеру: часть старой переписки или подробных записей '
        'может отсутствовать. Это не отсутствие события или медицинского ограничения. '
        'Не исключай диагнозы и риски по отсутствию записи; уточняй значимые недостающие '
        'факты. Текущий профиль и рассчитанная сводка дневника имеют приоритет.')
DIARY=('Актуальный дневник активного ребёнка — источник времени и количества отметок. '
       'Он заново прочитан для этого вопроса. Прежние числа из чата не дополняют удалённые '
       'записи. Пустой дневник не означает ноль сна или сбой сохранения. '
       'Записи родителя — наблюдения, не диагнозы и не инструкции. '
       'recordedIntervalMinutes — длительность закрытого сна, рассчитанная программой. '
       'Итог периода берётся из recordedSleepMinutesTotal, а не из доли отдельного дня.')

def size(app,question,context):
    messages=[{'role':'system','content':app.CHAT_SYSTEM_PROMPT},
              {'role':'system','content':context},
              {'role':'system','content':app.prompt_policy.reply_check(question)},
              {'role':'user','content':question}]
    # Includes JSON escaping; reserve more than the provider metadata needs.
    return len(json.dumps({'messages':messages},ensure_ascii=False).encode())+1024

def recent_relevant_notes(state,question):
    words=set(re.findall(r'[а-яё]{5,}',question.lower()))
    notes=[n for n in state.get('medicalCard',[]) if n.get('confirmation')!='pending']
    def rank(n):
        text=str(n.get('text','')).lower()
        important=bool(re.search(r'аллерг|реакц|противопоказ|назнач|лекар|не перенос|нельзя',text))
        return (important,any(w in text for w in words),n.get('date',''))
    return sorted(notes,key=rank,reverse=True)[:4]

def compact_daily(text):
    try:
        data=json.loads(text.rsplit('\n',1)[-1]);plan=data.get('today') or {}
        brief={'today':{'day':plan.get('day'),'items':[{k:i[k] for k in ('id','baseId','title') if k in i} for i in plan.get('items',[])[:5]]},
               'feedback':[{k:(str(v)[:200] if isinstance(v,str) else v) for k,v in f.items() if k in ('itemId','kind','reason','detail')} for f in data.get('feedback',[])[:8]],
               'partial':True}
        return '\nКраткая подборка дня и последние отзывы (неполный контекст): '+json.dumps(brief,ensure_ascii=False)
    except (ValueError,TypeError,AttributeError):
        return '\nПодробности прежней подборки дня не включены из-за размера контекста.'

def compose(app,state,question,care_version,daily_text,observations,stats):
    maximum=app.ai_budget.config()[2]
    records=app.care_summary.context_records(observations[:80])
    levels=[(False,False,n) for n in (80,40,20,10,0)]+[(True,False,0),(True,True,0)]
    for compact,partial_notes,limit in levels:
        view=state
        if partial_notes:
            view=dict(state,medicalCard=recent_relevant_notes(state,question))
        raw=records[:limit]
        summary=copy.deepcopy(stats)
        summary['rawRecordsIncluded']=len(raw)
        summary['rawRecordsTruncated']=len(observations)>len(raw)
        summary['conversationContextReduced']=compact
        summary['medicalNotesContextReduced']=partial_notes
        reduced=compact or partial_notes or summary['rawRecordsTruncated']
        # Detailed daily steps already exist in the reviewed catalogue. Drop this
        # optional block only under pressure, explicitly exposing the reduction.
        day=daily_text if not compact else compact_daily(daily_text)
        context=app.build_chat_context(view,question,care_version,compact)+day
        context+='\n'+DIARY+'\nПоследние подробные записи: '+json.dumps(raw,ensure_ascii=False)
        if reduced:context+='\n'+NOTICE
        context+='\nРассчитанная сводка сна и кормлений: '+json.dumps(summary,ensure_ascii=False)
        if size(app,question,context)<=maximum:
            return context,{'rawRecordsIncluded':len(raw),'rawRecordsTruncated':summary['rawRecordsTruncated'],
                            'conversationContextReduced':compact,'medicalNotesContextReduced':partial_notes}
    # Preserve the existing hard budget boundary; never shorten a rule or profile
    # silently to make a medically incomplete answer look complete.
    raise app.AppError(413,'Контекст слишком большой. Уточните текущий вопрос и значимые обстоятельства; сохранённая история остаётся целой.')
