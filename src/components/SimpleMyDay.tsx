import {useEffect, useState} from 'react';
import {Heart, Sparkles, RefreshCw} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {ParentState} from '@/lib/parent-model';
import {dayIdeas, emptyCare, localDay} from '../../ai-proxy/services';
import DailyActivities from './DailyActivities';

const motherTips = [
 ['Пять минут для себя', 'Выберите маленькое удовольствие: любимую песню, несколько страниц книги или чашку чая. Если рядом есть близкий, попросите его немного побыть с ребёнком.'],
 ['Одно дело можно передать', 'Попросите близкого о конкретной помощи: приготовить ужин, сходить за покупками или погулять с ребёнком. Не обязательно справляться со всем самостоятельно.'],
 ['Сегодня можно меньше', 'Выберите одно необязательное дело и отложите его. Освободившееся время можно просто оставить для отдыха.'],
 ['Поболтать с близким', 'Напишите человеку, с которым вам спокойно: «Хочу немного поболтать. Когда тебе удобно?» Разговор не обязательно должен быть о делах.'],
 ['Вспомнить любимое', 'Найдите несколько минут для своего интереса: музыка, рисунок, книга или любимый подкаст. Маленького приятного момента достаточно.'],
 ['Замечать хорошее', 'Вспомните один приятный момент сегодняшнего дня. Не нужно оценивать, сколько вы успели: это просто то, что хочется сохранить в памяти.'],
 ['Попросить время на отдых', 'Договоритесь с близким о небольшом времени, когда заботу о ребёнке возьмёт на себя он. Скажите прямо, когда и какая помощь вам нужна.'],
];
export default function SimpleMyDay({state,onProfile}:{state:ParentState;onProfile:()=>void}) {
 const [day,setDay]=useState(localDay());
 const [momIndex,setMomIndex]=useState(0),[childIndex,setChildIndex]=useState(0);
 useEffect(()=>{const id=window.setInterval(()=>setDay(localDay()),60000);return()=>window.clearInterval(id);},[]);
 useEffect(()=>{setMomIndex(0);setChildIndex(0);},[day,state.profile?.stage,state.profile?.birthDate]);
 const offset=Math.floor(Date.parse(day+'T12:00:00Z')/86400000);
 const tip=motherTips[(offset+momIndex)%motherTips.length];
 const ideas=dayIdeas(state.profile,state.care||emptyCare(),day);
 const unique=ideas.filter((idea,index)=>ideas.findIndex(other=>other.template===idea.template)===index);
 const idea=unique[childIndex%Math.max(1,unique.length)];
 const pregnant=state.profile?.stage==='pregnancy';
 return <div className="simple-day">
  <section className="tile simple-day-card" aria-labelledby="parent-day-title">
   <div className="simple-day-label"><Heart size={22}/><h2 id="parent-day-title">{state.profile?.role==='dad'?'Для папы':'Для мамы'}</h2></div>
   <div className="simple-day-content" aria-live="polite"><h3>{tip[0]}</h3><p>{tip[1]}</p></div>
   <Button variant="outline" onClick={()=>setMomIndex(i=>i+1)}><RefreshCw size={16}/>Другой совет</Button>
  </section>
  <section className="tile simple-day-card" aria-labelledby="child-day-title">
   <div className="simple-day-label"><Sparkles size={22}/><h2 id="child-day-title">Для ребёнка</h2></div>
   {state.profile?.stage==='child'?<DailyActivities key={state.activeChildId || 'primary'} state={state}/>:<>
   <div className="simple-day-content" aria-live="polite">
    {idea?<><span className="simple-day-caption">{pregnant?'Пока ждёте малыша':'Вместе · около 5 минут'}</span><h3>{idea.title}</h3><p>{idea.detail}</p></>:<><h3>Подберём занятие по возрасту</h3><p>Укажите дату рождения ребёнка в профиле. Если вы ждёте малыша, выберите беременность.</p></>}
   </div>
   {idea?<Button variant="outline" disabled={unique.length<2} onClick={()=>setChildIndex(i=>i+1)}><RefreshCw size={16}/>{pregnant?'Другой совет':'Другое занятие'}</Button>:<Button variant="outline" onClick={onProfile}>Заполнить профиль</Button>}
   </>}
  </section>
 </div>;
}
