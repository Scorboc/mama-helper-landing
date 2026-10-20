"""Versioned, locally reviewed first-aid provenance; no network or private logs.

Medical references explain a specific procedure; they are not Russian law or
endorsement/certification of this application. See docs/ai/EMERGENCY_PROTOCOLS_20261020.md.
"""
import hashlib
import re

VERSION = 'emergency-call-only-20261020-v2'
REVIEWED_AT = '2026-10-20'
CALL = 'Немедленно вызовите скорую помощь — 112 или 103. Включите громкую связь или поручите вызов другому взрослому. Не ждите ответа чата. '
SOURCES = {
    'call': ('МЧС России: вызов скорой', 'https://mchs.gov.ru/deyatelnost/bezopasnost-grazhdan/kak-pravilno-vyzvat-skoruyu_5'),
    'pediatric': ('Resuscitation Council UK: Paediatric Life Support, 2025', 'https://www.resus.org.uk/professional-library/2025-resuscitation-guidelines/paediatric-basic-life-support-guidelines'),
    'seizure': ('NHS: помощь при судорожном приступе', 'https://www.nhs.uk/symptoms/what-to-do-if-someone-has-a-seizure-fit/'),
    'battery': ('National Capital Poison Center: button battery', 'https://www.poison.org/battery'),
    'allergy': ('ASCIA: Acute Management of Anaphylaxis', 'https://www.allergy.org.au/hp/anaphylaxis/acute-management-guidelines'),
    'bleeding': ('МЧС России: сильное кровотечение', 'https://mchs.gov.ru/deyatelnost/bezopasnost-grazhdan/silnoe-krovotechenie_7'),
    'burn': ('University Hospitals Sussex NHS: Burns advice', 'https://www.uhsussex.nhs.uk/resources/burns-advice-for-patients-visiting-the-emergency-department/'),
    'poison': ('NHS: Poisoning', 'https://www.nhs.uk/conditions/poisoning/'),
    'adult': ('NHS: симптомы беременности, требующие помощи', 'https://www.nhs.uk/pregnancy/common-symptoms/pregnancy-symptoms-you-need-to-get-help-for/'),
}


REASONS = {
    'pediatric': 'Нарушение дыхания или сознания может быстро привести к недостатку кислорода и угрожать жизни.',
    'seizure': 'Судороги могут сопровождаться нарушением дыхания и потерей сознания; без очной оценки нельзя исключить опасное состояние.',
    'battery': 'Проглоченная батарейка может вызвать тяжёлый внутренний ожог даже без заметных симптомов. Опасно ждать появления симптомов или выхода со стулом.',
    'allergy': 'Отёк с затруднением дыхания может быстро перекрыть дыхательные пути и угрожать жизни.',
    'bleeding': 'Сильная кровопотеря может быстро привести к опасному нарушению кровообращения.',
    'burn': 'Глубокий или обширный ожог может вызвать тяжёлое повреждение тканей; при ожоге лица или шеи возможно опасное нарушение дыхания.',
    'poison': 'Отравление может повредить внутренние органы и нарушить дыхание; опасные проявления иногда возникают не сразу.',
    'adult': 'Сильная боль в груди или выраженное затруднение дыхания могут быть признаками угрожающего жизни состояния; списывать их на тревогу опасно.',
    'harm': 'Есть риск причинения серьёзного вреда себе или ребёнку; откладывать экстренную помощь опасно.',
    'call': 'Описанные признаки могут означать угрозу жизни или тяжёлый вред здоровью. По переписке нельзя безопасно исключить опасность.',
}
SOURCES['harm'] = SOURCES['call']
CALL = 'Немедленно вызовите скорую помощь — 112 или 103. '


def protocol(text):
    q = text.lower().replace('ё', 'е')
    for pattern, key in (
        (r'батарей|батарейк', 'battery'),
        (r'судорог|судорож', 'seizure'),
        (r'кровотеч|кровопотер|кровь.*(?:хлещет|льется|не останавливается)', 'bleeding'),
        (r'ожог|обожг|ошпар', 'burn'),
        (r'отрав|чистящ|таблет|растворител|кислот|щелоч|название вещества', 'poison'),
        (r'отек|опух|автоинъектор', 'allergy'),
        (r'навред|суицид|не хочу жить|убить|причин.*вред|теряю контроль', 'harm'),
        (r'боль в груди|давит в груди|нельзя списывать на стресс', 'adult'),
        (r'дыш|дыхан|созн|подавил|поперх|разбуд|реагир|кислород', 'pediatric'),
    ):
        if re.search(pattern,q):return key
    return 'call'


def finish(previous_answer='', question=''):
    # Discard procedural text, including previously generated/local templates.
    # No model call, diagnosis, treatment, first-aid steps or link to such steps.
    key = protocol(question)
    if key == 'call':key = protocol(previous_answer)
    answer = CALL + REASONS[key] + ' Не ждите ответа чата или записи к врачу.'
    if re.search(r'источник|официальн|основан|ссылк|норм[аыу]',question,re.I):
        ids = list(dict.fromkeys(('call', key)))
        answer += '\n\nОснования: ' + '; '.join('['+SOURCES[k][0]+']('+SOURCES[k][1]+')' for k in ids) + '.'
    return answer


def evidence(answer):
    key = next((k for k,reason in REASONS.items() if reason in answer),'call')
    ids = list(dict.fromkeys(('call',key)))
    return {
        'basis': 'Фиксированный экстренный ответ: вызов скорой и объяснение опасности. Версия '+VERSION+'.',
        'sources': [{'title':SOURCES[k][0],'url':SOURCES[k][1]} for k in ids],
        'protocolVersion': VERSION, 'protocolId': key, 'reviewedAt': REVIEWED_AT,
        'answerSha256': hashlib.sha256(answer.encode('utf-8')).hexdigest(),
        'limitation': 'Не диагноз, не лечение и не инструкция первой помощи. Не гарантирует обнаружение всех опасных состояний.',
    }
