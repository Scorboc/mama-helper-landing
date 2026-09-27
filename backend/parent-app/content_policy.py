"""Shared age and relevance rules. See CONTENT_RULES.md; never rewrite history."""
import calendar
import importlib.util
import json
import re
from datetime import date
from pathlib import Path

_spec=importlib.util.spec_from_file_location('content_catalog',Path(__file__).with_name('daily_catalog.py'))
catalog=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(catalog)

RULES=(
 ' Обязательная проверка перед каждым советом: возраст активного ребёнка, нижняя и верхняя '
 'границы применимости каждого действия, нужные навыки, здоровье и условия из текущего вопроса. '
 'Проверяй все темы: игры, развитие, питание, сон, уход, гигиену и процедуры. '
 'Персональную подборку ограничивай текущим полным месяцем до двух лет, далее максимум двумя соседними полными месяцами. '
 'Это период подбора занятия, а не срок, к которому ребёнок обязан освоить навык. Не выдумывай новые медицинские процедуры к каждому месяцу. '
 'Не смешивай возраст разных детей, беременность и родившегося ребёнка; старые ответы не задают текущий возраст. '
 'При неизвестном возрасте не угадывай; уточняй только недостающие сведения. Не выдавай будущий этап за текущий. '
 'Возраст не доказывает освоенный навык. Не назначай медицинскую процедуру только из-за календарного возраста. '
 'Проверь логику ответа: решает ли он заданный вопрос, выполним ли сейчас, соблюдены ли все ограничения '
 '(например, без игрушек), не повторяет ли очевидное уже освоенное действие без причины. '
 'Если родитель отверг занятие или оно надоело, не повторяй ту же механику под новым названием '
 '(например, «Где мама?» и прятки после отказа от «ку-ку»). '
 'При поддержке мамы не вставляй детские занятия или возраст, если это не относится к её вопросу. '
 'Совет должен быть самодостаточным. Не добавляй приглашения «проверьте в чате», «напишите в чат», '
 '«обсудите с ИИ», «спросите помощника» или аналогичные призывы; пользователь уже общается с помощником. '
 'Не завершай совет предложением «если надоест/нужны ещё идеи, скажите — предложу другое». '
 'Краткий уточняющий вопрос по существу допустим. Рекомендацию обратиться к врачу давай по ситуации, '
 'а не в качестве шаблонного завершения каждого ответа. Не добавляй источники без прямого запроса.'
)

def months(profile, today=None):
    if not profile or profile.get('stage')!='child':return None
    try:
        born=date.fromisoformat(profile['birthDate']);now=today or date.today()
        if born>now:return None
        return (now.year-born.year)*12+now.month-born.month-(now.day<min(born.day,calendar.monthrange(now.year,now.month)[1]))
    except (ValueError,TypeError,KeyError):return None

def context(profile, question=''):
    age=months(profile)
    if profile and profile.get('stage')=='pregnancy':
        return 'Активный профиль: беременность. Проверяй границы применимости по текущему сроку; не предполагай наличие родившегося ребёнка.'
    if age is None:return 'Точный возраст неизвестен. Персональные действия, зависящие от возраста, до уточнения не предлагать.'
    result=f'Точный возраст активного ребёнка: {age} полных месяцев. Для каждой рекомендации проверь ОБЕ границы: минимальный и максимальный возраст. Не расширяй диапазон из-за просьбы или старого контекста.'
    q=question.lower().replace('ё','е')
    if re.search(r'развит|уход|гигиен|зуб|горш|мыть|умыван',q) and not re.search(r'просто поговорить|не хочу.*(?:совет|план)',q):
        tips=[{k:c[k] for k in ('title','text','minMonths','maxMonths')} for c in catalog.monthly.advice(age) if c['section']!='Советы педиатров']
        result+='\nРедакционная подборка на текущий месяц. Используй только если соответствует вопросу; не выдавай за обязательные навыки или процедуры: '+json.dumps(tips,ensure_ascii=False)
    if re.search(r'игр|поигра|заняти',q) and not re.search(r'не хочу.*(?:план|заняти|игр)|просто поговорить',q):
        pool=catalog.candidates(age)
        if re.search(r'без (?:игруш|предмет)|ничего нет',q):pool=[g for g in pool if g['materials']=='Ничего']
        if (profile or {}).get('health'):pool=[g for g in pool if g['area'] not in ('Движение','Координация')]
        outlines=[dict({k:g[k] for k in ('title','minMonths','maxMonths','goal','steps','materials')}, ageLabel=age_label(g)) for g in pool]
        result+='\nДля игрового запроса выбери подходящий вариант из этого каталога. Название и возрастные границы сохраняй. maxMonths — служебный предел; в ageLabel уже записан последний допустимый полный месяц включительно. Если называешь диапазон возраста, копируй только ageLabel дословно, без оговорок: не переводи месяцы в годы и десятичные числа. Соблюдай ограничения вопроса и не возвращай отвергнутую механику. Если ничего не подходит, уточни конкретное препятствие. Каталог: '+json.dumps(outlines,ensure_ascii=False)
    return result

def age_label(game):
    lo,hi=game['minMonths'],game['maxMonths']-1
    return f'{lo} полных месяцев' if lo==hi else f'{lo}–{hi} полных месяцев включительно'

def play(profile):
    """A fallback must obey the same catalogue boundaries as an AI daily selection."""
    age=months(profile)
    if age is None:return 'Для подбора игры нужна дата рождения в активном профиле. Пока возраст неизвестен, конкретное занятие не предлагаю.'
    pool=[g for g in catalog.candidates(age) if g['materials']=='Ничего' and g['area'] not in ('Движение','Координация')]
    if not pool:return 'Для этого возраста в каталоге пока нет подходящей проверенной игры.'
    item=pool[date.today().toordinal()%len(pool)]
    return f'Игра «{item["title"]}», без предметов. Что развиваем: {item["goal"]}\n\n'+ '\n'.join(item['steps'])

# Only sentences explicitly redirecting the reader to chat are removed. Safety
# wording such as "не ждите ответа чата" and actual follow-up questions survive.
_INVITE=re.compile(r'(?:напиш(?:и|ите)|спрос(?:и|ите)|уточни(?:те)?|проверь(?:те)?|проверить|обсуд(?:и|ите|ить)|задай(?:те)?|задать|обрат(?:ись|итесь)|перей(?:ди|дите)|открой(?:те)?|мож(?:но|ете)\s+(?:написать|спросить|уточнить))[^.!?\n]{0,180}(?:в\s+(?:наш(?:ем)?\s+)?чат(?:е|ах)?|с\s+(?:ии|ai|помощником)|у\s+помощника)',re.I)
_MORE_INVITE=re.compile(r'если[^.!?\n]{0,90}(?:надоест|ещ[её] (?:идеи|идей|вариант)|другой вариант)[^.!?\n]{0,70}(?:скажите|напишите|спросите)[^.!?\n]{0,70}(?:предложу|подберу)',re.I)
_AGE_RANGE=re.compile(r'\b\d+(?:[.,]\d+)?\s*[–—-]\s*\d+(?:[.,]\d+)?\s*(?:полных\s+)?(?:месяц(?:ев|а)?|мес|лет|год(?:а|ов)?)\b(?:\s+включительно)?',re.I)

def clean(answer, profile=None):
    # A model may confuse e.g. 85 months with 8.5 years. For a named catalogue
    # game, render numerical age ranges from its verified bounds, never the model.
    age=months(profile)
    matches=[g for g in catalog.candidates(age) if g['title'].lower() in answer.lower()] if age is not None else []
    if matches and len({(g['minMonths'],g['maxMonths']) for g in matches})==1:
        answer=_AGE_RANGE.sub(age_label(matches[0]),answer)
        answer=re.sub(r'\s*\((?:максимум|верхняя граница) не включается\)', '',answer,flags=re.I)
    kept=[]
    for part in re.split(r'(?<=[.!?])(?=\s)|(?<=\n)',answer):
        if (_INVITE.search(part) or _MORE_INVITE.search(part)) and not re.search(r'не\s+ждите|112|103|врач|педиатр',part,re.I):continue
        kept.append(part)
    return ''.join(kept).strip() or 'Не получилось подготовить содержательный ответ. Попробуйте повторить вопрос.'
