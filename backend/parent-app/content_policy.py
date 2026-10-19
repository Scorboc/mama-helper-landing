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
 'Чат обслуживает только активный профиль. Никогда не проси назвать возраст другого ребёнка и не принимай '
 'возраст или срок из сообщения как замену профилю. Если вопрос относится к другому ребёнку или возраст '
 'из сообщения не совпадает с активным профилем, направь родителя создать или выбрать отдельный профиль. '
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

def game_constraints(question, messages=None):
    """Carry explicit constraints within this child's current conversation only."""
    texts=[str(m.get('text','')) for m in (messages or [])[-30:] if m.get('role')=='user']+[question]
    no_objects=False
    for text in texts:
        q=text.lower().replace('ё','е')
        if re.search(r'теперь (?:есть|можно использовать) (?:игруш|мяч|предмет)|игрушки появились',q):
            no_objects=False
        if re.search(r'нет игруш|игрушек нет|без (?:игруш|предмет|материал)|ничего нет|нет материал|(?:предмет|материал|игруш)[^.!?]{0,60}недоступн',q):
            no_objects=True
        if re.search(r'не подош|не подход',q) and re.search(r'тянет[^.!?]{0,40}в рот',q):
            no_objects=True
    rejected_sounds=any(re.search(r'(?:повторени\w* звук|звуков)[^.!?]{0,50}(?:не понрав|не нрав|надоел)',t.lower()) for t in texts)
    return question+(' Без предметов и игрушек.' if no_objects else '')+(' Не хочу повторять звуки.' if rejected_sounds else '')


def context(profile, question='', messages=None, compact=False):
    age=months(profile)
    if profile and profile.get('stage')=='pregnancy':
        return 'Активный профиль: беременность. Проверяй границы применимости по текущему сроку; не предполагай наличие родившегося ребёнка.'
    if age is None:return 'Точный возраст неизвестен. Персональные действия, зависящие от возраста, до уточнения не предлагать.'
    result=f'Точный возраст активного ребёнка: {age} полных месяцев. Для каждой рекомендации проверь ОБЕ границы: минимальный и максимальный возраст. Не расширяй диапазон из-за просьбы или старого контекста.'
    q=question.lower().replace('ё','е')
    if not compact and re.search(r'развит|уход|гигиен|зуб|горш|мыть|умыван',q) and not re.search(r'просто поговорить|не хочу.*(?:совет|план)',q):
        tips=[{k:c[k] for k in ('title','text','minMonths','maxMonths')} for c in catalog.monthly.advice(age) if c['section']!='Советы педиатров']
        result+='\nРедакционная подборка на текущий месяц. Используй только если соответствует вопросу; не выдавай за обязательные навыки или процедуры: '+json.dumps(tips,ensure_ascii=False)
    if game_intent(q,messages):
        pool=eligible_games(profile,game_constraints(q,messages),messages)
        if compact:pool=pool[:4]  # A small eligible choice, never clipped instructions.
        outlines=[dict({k:g[k] for k in ('id','baseId','title','minMonths','maxMonths','goal','steps','materials')}, ageLabel=age_label(g)) for g in pool]
        if compact:
            for outline in outlines:outline.pop('steps',None)
            result+='\nВ сокращённом каталоге выбери название; проверенные шаги добавит приложение. Не придумывай шаги.'
        result+='\nДля игрового запроса выбери подходящий вариант из этого каталога. Название и возрастные границы сохраняй. maxMonths — служебный предел; в ageLabel уже записан последний допустимый полный месяц включительно. Если называешь диапазон возраста, копируй только ageLabel дословно, без оговорок: не переводи месяцы в годы и десятичные числа. Соблюдай ограничения вопроса и не возвращай отвергнутую механику. Если ничего не подходит, уточни конкретное препятствие. Каталог: '+json.dumps(outlines,ensure_ascii=False)
    return result

def game_request(question):
    q=str(question or '').lower().replace('ё','е')
    if re.search(r'не хочу.*(?:план|заняти|игр)|просто поговорить|не нужны советы',q):return False
    if re.search(r'(?:можно|стоит|нужно|надо)\s+(?:ли\s+)?предложить\s+(?:ребенку|ему|ей)[^.!?\n]{0,180}(?:заняться тем|параллельн|то же)',q):return False
    return bool(re.search(r'\bигр(?!уш)\w*|поигра|заняти|занять|рисов|сенсорн\w*\s+короб|голосом|жестами|материал|механик|повторять вчера|выбрать иную|вместо лечебного массажа',q))

def game_safety_question(question):
    q=str(question or '').lower().replace('ё','е')
    return bool(re.search(r'исключить|избегать|опасн|безопасн|можно ли|почему нельзя',q) and re.search(r'игр|занят|предмет|детал|тянет|бусин|магнит|батарей',q))

def game_intent(question,messages=None):
    """A short refusal belongs to the current game exchange, not every old game."""
    q=str(question or '').lower().replace('ё','е')
    if re.search(r'просто поговор|не нрав\w* совет|не (?:нужны|хочу) совет|без совет|для мамы|мне[^.!?]{0,30}(?:тревож|груст|плохо)',q):return False
    if game_safety_question(q):return False
    if game_request(q):return True
    if not re.search(r'не подход|не подош|не нрав|надоел|недоступн|без предмет|без игруш|мелкие предмет|предлож\w* друг|друг\w* вариант|еще вариант',q):return False
    for m in reversed((messages or [])[-12:]):
        if m.get('role')!='user' or m.get('text')==question:continue
        text=str(m.get('text',''))
        if game_request(text) and not game_safety_question(text):return True
        if not re.search(r'не подход|не подош|не нрав|надоел|недоступн|без предмет|без игруш|мелкие предмет|предлож\w* друг|друг\w* вариант|еще вариант',text,re.I):return False
    return False

def eligible_games(profile,question,messages=None):
    q=question.lower().replace('ё','е');pool=catalog.candidates(months(profile))
    if re.search(r'картонн\w* короб|из короб',q):pool=[g for g in pool if 'короб' in g['materials'].lower()]
    if re.search(r'игр\w* с картин|игр\w*[^.!?]{0,30}картинк',q):pool=[g for g in pool if re.search(r'картин|книг',g['materials'].lower())]
    if 'не хочу повторять звуки' in q:pool=[g for g in pool if g['baseId'] not in ('animal-voice','sound-dialogue','two-sounds','sound-answer','word-sound')]
    if re.search(r'без (?:игруш|предмет|материал)|нет игруш|игрушек нет|нет материал|ничего нет|голосом и жест',q):pool=[g for g in pool if g['materials']=='Ничего']
    if (profile or {}).get('health') or re.search(r'не ходит|не сидит|не ползает|вместо лечебного массажа',q):pool=[g for g in pool if g['area'] not in ('Движение','Координация')]
    if re.search(r'ку-ку[^.!?]{0,30}(?:надоел|не нрав|не хочу)|(?:надоел|не хочу)[^.!?]{0,30}ку-ку',q):pool=[g for g in pool if 'peek' not in g['baseId']]
    if re.search(r'сортир[^.!?]{0,60}(?:не нрав|надоел)|не хочу[^.!?]{0,40}сортир',q):pool=[g for g in pool if 'sort' not in g['baseId']]
    if re.search(r'вкладыван[^.!?]{0,60}(?:надоел|не нрав)|не хочу[^.!?]{0,40}вклады',q):pool=[g for g in pool if g['baseId']!='box-delivery']
    if re.search(r'тих\w* игр|спокойн\w* игр|перед сном|перед засып',q):
        pool=[g for g in pool if g['area'] not in ('Движение','Координация')]
    if re.search(r'надоел|не нрав|не подход|не подош|не хочу повтор|друг\w* механик',q):
        previous=next((str(m.get('text','')) for m in reversed(messages or []) if m.get('role')=='assistant'),'')
        used={g['baseId'] for g in catalog.candidates(months(profile)) if game_named(g['title'],previous)}
        pool=[g for g in pool if g['baseId'] not in used]
    # Keep all explicit rejections in the recent game exchange, not only the last.
    previous='';rejected=set()
    for message in (messages or [])[-30:]:
        text=str(message.get('text',''));lower=text.lower().replace('ё','е')
        if message.get('role')=='assistant':previous=text
        elif re.search(r'надоел|не нрав|не понрав|не подход|не подош|недоступн|не хочу повтор|друг\w* механик',lower):
            rejected.update(g['baseId'] for g in catalog.candidates(months(profile)) if game_named(g['title'],previous))
        elif not game_request(text):
            rejected.clear();previous=''
    pool=[g for g in pool if g['baseId'] not in rejected]
    return pool

def game_named(title, answer):
    def canonical(text):return re.sub(r'["«»“”!?]', '',text.casefold())
    return canonical(title) in canonical(answer)


def render_game_answer(answer,profile,question,messages=None):
    """The model selects a reviewed title; game steps come only from the catalogue."""
    q=question.lower().replace('ё','е')
    if game_safety_question(q):return answer
    if re.search(r'температур|лихорад|рвот|вялый|болен|задыха|судорог|сейчас[^.!?]*болит',q):
        return answer  # A game renderer must never replace illness guidance with play.
    if re.search(r'уже пробовал\w*[^.!?]{0,40}игр',q) and not re.search(r'друг|замен|иначе',q):
        return 'Как прошла игра и что именно хочется изменить — сложность, материалы или само действие?'
    if re.search(r'магнит|батарей|бусин|воздушн\w* шар|мелк\w* детал|безопасн\w* игров\w* мест|мест\w* для игр',q):
        return answer  # Preserve the actual safety question and its warning.
    named_game=any(game_named(g['title'],answer) for g in catalog.candidates(months(profile))) if months(profile) is not None else False
    explicit=bool(re.search(r'предлож|придум|подбер|выбер|игровой способ|во что|чем занять|что можно (?:сделать|делать)|(?:нужна|хочу|хочется).*игр|какие.*игр|новая игра|дай.*игр|игр\w*\s+вместо|вместо лечебного массажа',q))
    previous=[str(m.get('text','')) for m in (messages or [])[-30:] if m.get('role')=='user' and m.get('text')!=question]
    followup=bool(re.search(r'надоел|не нрав|не понрав|не подход|не подош|недоступн|друг\w*|механик|материал|без игруш|нет игруш',q)) and any(game_request(text) for text in previous)
    # A named game in an answer does not make a behavioural question a game request.
    direct=game_intent(q,messages) and (explicit or followup or not game_request(q))
    if not direct:return answer
    if months(profile) is None:
        if (profile or {}).get('stage')=='pregnancy':
            return 'Активный профиль — беременность. Занятия для родившегося ребёнка сейчас не подбираю. После рождения можно добавить его отдельный профиль.'
        return 'Для конкретной игры нужна дата рождения в активном профиле ребёнка. Заполните профиль; возраст из сообщения не заменяет его данные.'
    q=game_constraints(q,messages)
    pool=eligible_games(profile,q,messages)
    selected=[g for g in pool if game_named(g['title'],answer)][:3]
    if not selected:
        if not pool and re.search(r'игр\w* с картин|игр\w*[^.!?]{0,30}картинк',q):
            return 'В проверенной подборке для текущего возраста пока нет игры именно с картинками. Не буду выдавать другую механику за ваш запрос. Можно выбрать занятие без предметов, если вам подойдёт такой вариант.'
        if not pool and re.search(r'картонн\w* короб|из короб',q):
            return 'Для игры именно с картонной коробкой на текущий месяц в проверенной подборке нет подходящего варианта. Не буду придумывать занятие без проверки возрастных условий. Можно выбрать занятие без предметов или с другими доступными вещами.'
        if not pool:return 'Для этих условий в проверенной подборке пока нет другой подходящей игры. Сохраню ваши ограничения: не буду повторять отвергнутые действия или предлагать недоступные материалы.'
        selected=pool[:1]
    intro=('Лечебный массаж назначает врач по показаниям. Возраст сам по себе не требует такой процедуры. '
           'Для обычного общения можно выбрать короткую игру без требования ходить или сидеть.\n\n' if 'вместо лечебного массажа' in q else '')
    if re.search(r'мне[^.!?]{0,25}скучно|самой скучно',q):
        intro+='Не обязательно долго развлекать ребёнка. Можно попробовать по одной короткой реплике или действию с вашей стороны и закончить, если вам скучно.\n\n'
    if re.search(r'сейчас спит|малыш спит|новорожденн\w*[^.!?]{0,25}спит',q):
        intro+='Не будите ребёнка ради игры. Следующие варианты — для спокойного бодрствования, когда он сам проснётся.\n\n'
    if re.search(r'врач|педиатр|оценк\w* слух|обследован',q) and re.search(r'вместо|замен|отмен',q):
        intro+='Игры не заменяют предложенную врачом оценку или лечение. Сохраните его рекомендации; следующие варианты — только обычное общение, если оно сейчас подходит ребёнку.\n\n'
    if re.search(r'тянет[^.!?]{0,40}в рот',q) and all(g['materials']=='Ничего' for g in selected):
        intro+='Вы написали, что ребёнок тянет предметы в рот, поэтому выберем игру без предметов.\n\n'
    elif re.search(r'надоел|не нрав|не подош|не подход|друг\w* механик',q):
        intro+='Вы написали, что прежняя механика не подходит или надоела, поэтому выберем другое действие.\n\n'
    if re.search(r'нет материал|без (?:предмет|игруш|материал)|голосом и жест',q):intro+='Эти варианты не требуют дополнительных предметов.\n\n'
    return intro+'\n\n'.join(f'**«{g["title"]}»**\nЦель: {g["goal"]}\nНужно: {g["materials"]}.\n'+'\n'.join(g['steps']) for g in selected)

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
_UNSOLICITED_OFFER=re.compile(r'если[^.!?\n]{0,120}(?:хотите|захотите|расскажете|скажите|скажете|назовите|назов[её]те|напишите|напишете)[^.!?\n]{0,100}(?:могу\s+(?:отдельно\s+)?(?:предложить|помочь|подобрать|подробнее|подсказать|рассказать|составить)|можно\s+подумать|предложу|подбер[её]м|подберу|подскажу|помогу|разбер[её]м|тогда\s+я\s+смогу)',re.I)
_DIRECT_OFFER=re.compile(r'^\s*хотите\s*[,—-]\s*(?:я\s+)?(?:помогу|подберу|предложу|подскажу|расскажу|разбер[её]м|могу\s+(?:помочь|предложить|подобрать|подсказать|рассказать))',re.I)
_AGE_RANGE=re.compile(r'\b\d+(?:[.,]\d+)?\s*[–—-]\s*\d+(?:[.,]\d+)?\s*(?:полных\s+)?(?:месяц(?:ев|а)?|мес|лет|год(?:а|ов)?)\b(?:\s+включительно)?',re.I)
_OTHER_CHILD=re.compile(r'(?:друг(?:ой|ого|ому)\s+(?:младш(?:ий|его|ему)\s+|старш(?:ий|его|ему)\s+)?реб[её]н|реб[её]н(?:ок|ка|ку)\s+(?:подруг|сестр|брата)|племян|внук)',re.I)
_ASK_OTHER_AGE=re.compile(r'(?:уточн(?:и|ите|ить)|назов(?:и|ите|ать)|укаж(?:и|ите|ать)|напиш(?:и|ите|ите)?)\s+[^.!?\n]{0,70}(?:возраст|сколько\s+(?:лет|месяц))',re.I)
_EXPLICIT_AGE=re.compile(r'(?:реб[её]н(?:ку|ок|ка)|ему|ей|для\s+реб[её]нка|если\s+реб[её]нку)\s*(?:сейчас\s*)?(\d{1,3})\s*(месяц(?:ев|а)?|мес\.?|лет|год(?:а|ов)?)',re.I)

def _scope_text(profile):
    name=str((profile or {}).get('childName') or 'активного ребёнка')[:60]
    age=months(profile)
    if (profile or {}).get('stage')=='pregnancy':
        return ('Этот чат отвечает только по активному профилю беременности. Срок из сообщения не заменяет '
                'данные профиля. Для другого профиля добавьте или выберите его и задайте вопрос там.')
    label=f'{age} полных месяцев' if age is not None else 'возраст из профиля'
    return (f'Этот чат отвечает только для профиля «{name}»: {label}. Возраст из сообщения не заменяет '
            'данные профиля. Для другого ребёнка добавьте отдельный профиль, переключитесь на него и задайте вопрос в его чате.')

def profile_scope_reply(question, profile):
    """Stop an alternate child/age from being smuggled into the active chat."""
    if not profile:return None
    q=str(question or '').replace('ё','е')
    if other_profile_reference(q):return _scope_text(profile)
    age=months(profile)
    if age is None:return None
    for value,unit in _EXPLICIT_AGE.findall(q):
        stated=int(value)
        if re.match(r'(?:лет|год)',unit,re.I):
            if not stated*12 <= age < (stated+1)*12:return _scope_text(profile)
        elif stated != age:return _scope_text(profile)
    return None

def other_profile_reference(text, allow_observation=False, allow_social=False):
    # Another child can be the object of the active child's social behaviour.
    q=text.lower().replace('ё','е')
    other=_OTHER_CHILD.search(q)
    if not other:return False
    if allow_observation and re.search(r'(?:опишите|назовите|прокомментируйте),?\s+что\s+делает\s+другой\s+ребенок\s*:\s*[«"]',q):
        return False  # An illustrated social cue, never an alternate input profile.
    if allow_social and re.search(r'(?:интерес|наблюда|подражан|взгляд|игра|общени|контакт)[^.!?\n]{0,90}друг(?:ой|ого|ому|им)\s+ребен',q) and not re.search(r'питан|корм|смес|препарат|болит|температур|леч|диагноз|назнач|доз|возраст',q):
        return False  # Interest in peers is about the active child's social behaviour.
    if allow_social and re.search(r'очеред|взять|игруш|играет|подел|делит|машин|попрос|передать|совместн|договор',q) and not re.search(r'питан|корм|смес|препарат|болит|температур|леч|диагноз|назнач|доз|возраст',q):
        return False  # Another participant in sharing/turn-taking, not a care profile.
    social=re.search(r'(?:бьет|ударил|ударяет|толкает|кусает|играет с|ссорится с)[^.!?\n]{0,50}друг(?:ого|ому|им)\s+ребен|(?:предложить|предложите|помогите)\s+(?:ребенку|ему|ей)[^.!?\n]{0,100}(?:занят|делает|играет)\s+другой\s+ребен',q)
    return not (social and social.start()<other.start())


def clean(answer, profile=None, question=None):
    social_context=bool(question and profile and profile_scope_reply(question,profile) is None and re.search(r'общени|сверстник|делит\w* игруш|делиться|очеред|жаднича',question,re.I))
    # Internal diary names belong to the evidence record, not the parent's reply.
    fields={'recordedSleepMinutesTotal':'отмеченная длительность сна за период',
            'recordedIntervalMinutes':'длительность отмеченного сна',
            'sleepRecords':'количество записей сна','careVersion':'версия дневника',
            'rawRecordsIncluded':'количество подробных записей в контексте',
            'rawRecordsTruncated':'часть подробных записей не включена в контекст'}
    for key,label in fields.items():
        answer=re.sub(r'\s*\(\s*`?'+re.escape(key)+r'`?\s*\)', '',answer)
        answer=re.sub(r'`?\b'+re.escape(key)+r'\b`?',label,answer)
    if profile and answer.strip()==_scope_text(profile):
        return answer.strip()
    # A model may confuse e.g. 85 months with 8.5 years. For a named catalogue
    # game, render numerical age ranges from its verified bounds, never the model.
    age=months(profile)
    matches=[g for g in catalog.candidates(age) if g['title'].lower() in answer.lower()] if age is not None else []
    if matches and len({(g['minMonths'],g['maxMonths']) for g in matches})==1:
        answer=_AGE_RANGE.sub(age_label(matches[0]),answer)
        answer=re.sub(r'\s*\((?:максимум|верхняя граница) не включается\)', '',answer,flags=re.I)
    answer=re.sub(r'(?m)^\s*Мне приятно[^.!?\n]*[.!?]?', 'Спасибо за обратную связь.',answer,flags=re.I)
    answer=re.sub(r'(?m)^\s*Рад[а]?[,]?\s+что\s+(?:это|разговор)[^.!?\n]*(?:полезно|полезным|помог)[^.!?\n]*[.!?]?', 'Спасибо за обратную связь.',answer,flags=re.I)
    answer=re.sub(r'Если\s+(?:захочется|захотите)[^.!?\n]{0,180}(?:вернуться|поделиться)[^.!?\n]{0,180}я\s+здесь[.!?]?', '',answer,flags=re.I)
    answer=re.sub(r'Спасибо,\s+что\s+сказали\s+это\s*[—–-]\s*приятно\s+слышать[^.!?\n]*[.!?]?', 'Спасибо за обратную связь.',answer,flags=re.I)
    kept=[]
    removed_scope_prompt=False
    removed_offer=False
    for part in re.split(r'(?<=[.!?])(?=\s)|(?<=\n)',answer):
        if removed_offer and re.match(r'\s*(?:Или просто расскажите|Оно необязательное)',part,re.I):continue
        if (_UNSOLICITED_OFFER.search(part) or _DIRECT_OFFER.search(part)) and not re.search(r'не\s+ждите|112|103',part,re.I):
            removed_offer=True
            continue
        if re.match(r'\s*Могу помочь (?:сформулировать|составить|подобрать|разобрать|выбрать)',part,re.I) or re.search(r'если захочется вернуться[^.!?]{0,120}просто напишите',part,re.I):
            removed_offer=True
            continue
        if (_INVITE.search(part) or _MORE_INVITE.search(part)) and not re.search(r'не\s+ждите|112|103|врач|педиатр',part,re.I):continue
        # Reporting age to a dispatcher/clinician is not changing the chat profile.
        medical_handoff=bool(re.search(r'112|103|(?:сообщ|назов|укаж|скаж)[^.!?\n]{0,140}(?:диспетчер|токсиколог|медицинск\w*\s+работник|врачу)',part,re.I))
        if profile and not medical_handoff and (_ASK_OTHER_AGE.search(part) or other_profile_reference(part,allow_observation=True,allow_social=social_context)):
            removed_scope_prompt=True
            continue
        kept.append(part)
    result=re.sub(r'(?m)^\s*\d+[.)]\s*$', '', ''.join(kept)).strip()
    if removed_scope_prompt:
        result=(result+'\n\n'+_scope_text(profile)).strip()
    return result or 'Не получилось подготовить содержательный ответ. Попробуйте повторить вопрос.'
