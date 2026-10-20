"""Versioned, locally reviewed first-aid provenance; no network or private logs.

Medical references explain a specific procedure; they are not Russian law or
endorsement/certification of this application. See docs/ai/EMERGENCY_PROTOCOLS_20261020.md.
"""
import hashlib
import re

VERSION = 'first-aid-20261020-v1'
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


def protocol(answer):
    a = answer.lower().replace('ё', 'е')
    # Match trusted template markers, not instructions/data supplied by the user.
    for marker, key in (('между лопатками', 'pediatric'), ('не разжимайте зубы', 'seizure'),
                        ('проглотил батарейку', 'battery'), ('автоинъектор', 'allergy'),
                        ('наружном кровотечении', 'bleeding'), ('обожженный участок', 'burn'),
                        ('название вещества', 'poison'), ('нельзя списывать на стресс', 'adult')):
        if marker in a:return key
    return 'pediatric' if 'ребен' in a else 'call'


def finish(answer, question=''):
    # Never ask a generative model to paraphrase the reviewed urgent template.
    if not answer.startswith('Немедленно вызовите скорую'):
        answer = CALL + answer
    if re.search(r'источник|официальн|основан|ссылк|норм[аыу]',question,re.I):
        ids = list(dict.fromkeys(('call', protocol(answer))))
        answer += '\n\nОснования: ' + '; '.join('['+SOURCES[k][0]+']('+SOURCES[k][1]+')' for k in ids) + '. Адаптация MAMA; источники не сертифицировали приложение.'
    return answer


def evidence(answer):
    key = protocol(answer)
    return {
        'basis': 'Проверенная локальная памятка первой помощи. Версия '+VERSION+', раздел '+key+'. Основания: '+
                 '; '.join(SOURCES[k][0]+': '+SOURCES[k][1] for k in dict.fromkeys(('call',key))),
        'sources': [{'title':SOURCES[k][0],'url':SOURCES[k][1]} for k in dict.fromkeys(('call',key))],
        'protocolVersion': VERSION, 'protocolId': key, 'reviewedAt': REVIEWED_AT,
        'answerSha256': hashlib.sha256(answer.encode('utf-8')).hexdigest(),
        'limitation': 'Это первая помощь до бригады, не диагноз и не назначение лечения. Дата сверки источников — '+REVIEWED_AT+
                      '; независимая клиническая и юридическая экспертиза приложения не выполнена. Следуйте диспетчеру.',
    }
