"""Build the public joint-play library from versioned editorial inputs.

Narrow age windows are data, not milestones or medical recommendations.
Broad source bands are never used as the final selection boundaries.
"""
import json
import runpy
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
daily = runpy.run_path(str(ROOT/'backend/parent-app/daily_catalog.py'))
monthly = daily['monthly']
VERSION = 'together-20261023-v2'
SAFETY = ('Взрослый рядом всё время. Только целые предметы по возрасту, без мелких деталей, магнитов, '
          'батареек, шнуров, пакетов, воды и еды. Не надевайте коробки на голову. '
          'Не удерживайте позу и не направляйте движения силой. Закончите при усталости, отказе или дискомфорте.')
new=[]
for line in (ROOT/'content/learning-mechanics.tsv').read_text(encoding='utf-8').splitlines():
    if not line or line.startswith('#'):
        continue
    start,stop,slug,title,area,materials,adult,child,simpler=line.split('|')
    new.append(dict(start=int(start),stop=int(stop),slug=slug,title=title,area=area,
                    materials=materials,adult=adult,child=child,simpler=simpler))
assert len(new)==84 and len({(x['start'],x['slug']) for x in new})==84
cards=[]
moving={'tummy-face','tummy-toy','animal-walk','march-stop','freeze-slow','movement-route'}
def common(lo,hi,mechanic,title,area,materials,adult,child,steps,readiness,origin):
    return dict(id=f'{mechanic}@m{lo}',mechanicId=mechanic,minMonths=lo,maxMonths=hi,title=title,
                domain=area,materials=materials,adult=adult,child=child,steps=steps,readiness=readiness,
                safety=SAFETY,origin=origin,catalogVersion=VERSION,icon='♡',education=False,
                noMaterials=materials=='Ничего',stationary=True)
for lo in list(range(24))+list(range(24,84,2)):
    _,hi=monthly.window(lo)
    support=monthly.play_support(lo)
    foundation=next(rows for a,b,rows in daily['FOUNDATION_BANDS'] if a<=lo<b)
    for slug,area,title,materials,minutes,goal,body in foundation:
        c=common(lo,hi,'library-'+slug,title,area,materials,
                 'Предложите действие один раз и дайте время на ответ. Следуйте инициативе ребёнка.',
                 'Ребёнок выбирает, пробует или отвечает удобным способом: взглядом, жестом, звуком или словом.',
                 [body,support,'Предложите партнёру выбрать продолжение. Можно повторить знакомое или остановиться.'],
                 'Возраст не означает освоенного навыка. Начните только с уже удобного действия. '+support,
                 'Существующая библиотека MAMA · возрастная адаптация')
        c.update(minutes=minutes,goal=goal,stationary=slug not in moving,sourceId=slug)
        if slug=='object-request':c['title']='Передай знакомую игрушку рядом'
        cards.append(c)
    additions=[x for x in new if x['start']<=lo<x['stop']]
    assert len(additions)==(4 if lo<3 else 8),lo
    for x in additions:
        c=common(lo,hi,f"learning-{x['start']}-{x['slug']}",x['title'],x['area'],x['materials'],
             x['adult'],x['child'],[x['adult'],x['child'],x['simpler']],
             x['simpler']+' '+support+' Возраст не означает обязательного навыка.',
             'Редакция MAMA · новая основа или вариация')
        c['roleBased']=True
        c['education']=True
        cards.append(c)

# The 21 explicitly authored joint scripts approved in the separate workshop.
# The 54 monthly adaptations remain support for the library; they are not
# counted again as new games or duplicated in the visible list.
for c in json.loads((ROOT/'content/together-reviewed.json').read_text(encoding='utf-8')):
    c.update(mechanicId=c['id'],education=False,noMaterials=c['materials']=='Ничего',stationary=True)
    if c['minMonths']<24:
        for month in range(c['minMonths'],c['maxMonths']):
            adapted=deepcopy(c)
            adapted.update(id=f"{c['id']}@m{month}",minMonths=month,maxMonths=month+1)
            adapted['readiness']+=' '+monthly.play_support(month)
            cards.append(adapted)
    else:
        cards.append(c)

def category(area):
    if any(x in area.lower() for x in ['слух','слуш','ритм']):return 'Слушание и ритм'
    if any(x in area.lower() for x in ['движ','коорд','ощущ']):return 'Движение и ощущения'
    if any(x in area.lower() for x in ['простран','форм','сравн']):return 'Формы и пространство'
    if any(x in area.lower() for x in ['воображ','творч','эмоц','чувств']):return 'Творчество и эмоции'
    if any(x in area.lower() for x in ['речь','общен','речи','описан','рассказ','подраж','очеред','очерёд']):return 'Речь и общение'
    return 'Внимание и мышление'
for c in cards:c['category']=category(c['domain'])
assert len(cards)==879 and len({c['id'] for c in cards})==len(cards)
stats=[]
for age in range(84):
    pool=[c for c in cards if c['minMonths']<=age<c['maxMonths']]
    stats.append(dict(month=age,choices=len(pool),stationary=sum(c['stationary'] for c in pool),
                      noMaterials=sum(c['noMaterials'] for c in pool)))
    assert len(pool)>=(12 if age<3 else 16) and sum(c['stationary'] for c in pool)>=(11 if age<3 else 15),(age,'coverage')
    assert sum(c['noMaterials'] for c in pool)>=4,(age,'materials')
assert all(0<=c['minMonths']<c['maxMonths']<=84 and c['maxMonths']-c['minMonths']<=2 for c in cards)
data=dict(version=VERSION,cards=cards,coverage=stats,
          note='879 возрастных карточек не означают 879 разных механик. Повторы знакомого добровольны.')
destination=ROOT/'public/together-games'
destination.mkdir(parents=True,exist_ok=True)
(destination/'catalog.js').write_text('window.TogetherCatalog = '+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
(ROOT/'content/together-coverage.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Built',len(cards),'age cards;',min(x['choices'] for x in stats),'minimum choices;',
      min(x['stationary'] for x in stats),'stationary;',min(x['noMaterials'] for x in stats),'without materials.')
