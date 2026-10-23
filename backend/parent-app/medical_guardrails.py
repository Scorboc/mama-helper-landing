"""Reviewed local boundaries, independent of model availability. No stored-data edits.

Sources and limitations: docs/ai/CHAT_QA_RULES_20261017.md.
These narrow rules are not a diagnostic or comprehensive triage system.
"""
import re
import emergency_protocols

def norm(text):return str(text or '').lower().replace('ё','е')

def mentions_swaddling(text):
    # Match swaddling forms, excluding пеленальный (a changing table).
    return bool(re.search(r'\b(?:пелен(?!аль)(?:ать\w*|а[юеийлв]\w*|ан[ин]\w*|ыва\w*)|(?:за|рас|пере|с)пелен(?!аль)\w*|пеленк\w*\s+для\s+сна)\b', norm(text)))

def unwanted_thought_without_intent(text):
    q=norm(text)
    thought=bool(re.search(r'навязчив|пуга\w*[^.!?\n]{0,40}мысл|страшн\w*[^.!?\n]{0,30}(?:мысл|картин)|мысль[^.!?\n]{0,40}пуга',q))
    denial=bool(re.search(r'не хочу|не собираюсь|не желаю|намерения нет|нет намерения|этого не хочу',q))
    acute=bool(re.search(r'теряю контроль|не могу останов|сейчас[^.!?\n]{0,45}(?:ударю|убью|сделаю)|есть план|уже (?:ударил|ударила|начал)',q))
    return thought and denial and not acute

def choking(text):
    q=norm(text)
    return bool(re.search(r'поперх|подавил|удуш|не может[^.!?\n]{0,50}кашля|не может[^.!?\n]{0,50}вдох',q))

def choking_reply(age):
    return emergency_protocols.finish('', 'Ребёнок подавился')


def emergency_reply(question,age=None):
    return emergency_protocols.finish('', question)


def battery_ingestion(question):
    q=norm(question)
    return bool(re.search(r'батаре[йя]',q) and re.search(r'проглот|съе[лс]|во рту|пропал|не хватает|не могу найти',q))


def battery_reply():
    return emergency_protocols.finish('', 'Проглотил батарейку')


def boundary_request(question):
    q=norm(question)
    return bool(re.search(r'врач|педиатр|специалист|осмотр',q) and re.search(r'перестать|не обращаться|не ходить|отказаться|заменит|вместо врача|можно без',q))

def boundary_reply():
    return ('ИИ может помочь понять информацию и подготовить вопросы, но не заменяет осмотр и оценку здоровья ребёнка врачом. '
            'Не отказывайтесь от назначенного наблюдения или обследования на основании ответа чата. Если общение с врачом не подходит, '
            'можно получить второе мнение. При новых тревожных симптомах обращение нельзя откладывать ради переписки.')

def review(answer,state,age):
    """Replace a detected unsafe paragraph, keeping the rest of the useful reply."""
    q=norm(next((m.get('text','') for m in reversed(state.get('messages',[])) if m.get('role')=='user'),''))
    if boundary_request(q):return boundary_reply()
    parts=re.split(r'\n\s*\n',answer)
    result=[]
    for part in parts:
        a=norm(part)
        if age is not None and age<12 and re.search(r'накрой|укрой|накрыть|укрыть',a) and re.search(r'плед|одеял|покрывал',a) and not re.search(r'не (?:накры|укры)|нельзя|не нужно',a):
            part='Для сна оставьте твёрдый ровный матрас свободным от пледов, одеял и других мягких предметов. Для тепла подойдёт одежда или спальный мешок по размеру без утяжеления.'
        if age is not None and age<60 and re.search(r'яблок',a) and re.search(r'давайте|дайте|предложите|можно дать',a) and re.search(r'сыр|тверд|крупн\w* кус|половин|держател',a) and not re.search(r'не (?:давайте|дайте|предлагайте)|нельзя',a):
            part='Твёрдое сырое яблоко крупным куском не подходит для тренировки жевания. Выбирайте безопасную по навыкам текстуру: приготовленное до мягкости или мелко натёртое яблоко. При повторных трудностях жевания или глотания обсудите питание с педиатром.'
        if re.search(r'поперх|давится',a) and re.search(r'практик|навык[^.!?]{0,40}(?:придет|дойдет)|обычно[^.!?]{0,40}справля',a):
            part='При повторных поперхиваниях даже маленькими глотками остановите кормление и обсудите глотание с педиатром. Не продолжайте через трудности ради тренировки. Если ребёнок не может дышать или эффективно кашлять, нужна немедленная первая помощь и вызов 112.'
        if age is not None and age<12 and mentions_swaddling(a) and re.search(r'постепенн|одного[^.!?]{0,30}сна',a) and re.search(r'переворач|перевер',q):
            part='При попытках переворачиваться пеленание прекращают сразу для каждого сна; постепенный переход с сохранением пеленания на другие сны не подходит.'
        if re.search(r'если[^.!?]{0,50}(?:что-то|что-либо|люб\w*)[^.!?]{0,60}(?:перечислен|замет)',a) and re.search(r'в ближайшее время',a) and re.search(r'посинен|синие губ|паузы в дыхании',norm(answer)):
            part='При посинении, паузах с изменением цвета или затруднении дыхания звоните 112 немедленно. Менее выраженные стойкие изменения дыхания обсудите с педиатром; по переписке их причину не определить.'
        if re.search(r'ребен|малыш|на кормление',a) and re.search(r'трудно разбудить|не удается разбудить|не просыпается',a) and re.search(r'сегодня|в ближайшее время|запишитесь',a):
            part=('Если ребёнка трудно разбудить или он не реагирует как обычно, звоните 112 немедленно; не ждите записи к врачу. '
                  'Заметное уменьшение мочеиспусканий или ослабление кормления также требуют медицинской оценки сегодня. '
                  'При нарушении дыхания, посинении или потере сознания — немедленно 112.')
        if re.search(r'право[^.!?]{0,100}не всегда',a) and re.search(r'объя|поцел|телесн',q):
            part='Ребёнок может отказаться от объятий и поцелуев. Предложите другое приветствие и помогите взрослым уважать его отказ.'
        if re.search(r'зафиксир\w* руки|обнять сзади',a) and re.search(r'бьет|куса|истер|удар',q):
            part='Отойдите на безопасное расстояние, уберите опасные предметы и мягко преградите удар, если это нужно для защиты. Не фиксируйте руки и не удерживайте силой ради прекращения эмоций.'
        result.append(part)
    answer='\n\n'.join(result)
    a=norm(answer)
    if age is not None and age<12 and mentions_swaddling(a) and not re.search(r'попытк\w* переворач|при переворот|прекратите пелен|пеленание прекращ',a):
        answer+='\n\nПри первых попытках переворачиваться пеленание прекращают.'
    if re.search(r'машин|автомобил|дорог',q) and re.search(r'корм|еда|есть|перекус',q):
        answer='Для еды сначала остановите автомобиль в безопасном разрешённом месте. Не кормите ребёнка в движении; во время еды нужны устойчивое вертикальное положение и наблюдение взрослого.\n\n'+answer
        answer=re.sub(r'[^.!?\n]*если есть риск поперхнуться[^.!?\n]*[.!?]?', '',answer,flags=re.I)
    return answer

def valid_language(answer,question):
    # Reject corrupted output instead of silently deleting a possibly vital term.
    if re.search(r'[A-Za-z]+[А-Яа-яЁё]+|[А-Яа-яЁё]+[A-Za-z]+',answer):return False
    if re.search(r'[\u3400-\u9fff]',answer) and not re.search(r'[\u3400-\u9fff]|китайск|японск|переведи',question,re.I):return False
    return True
