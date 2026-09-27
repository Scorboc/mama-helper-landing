import {useCallback,useEffect,useRef,useState} from 'react';
import {Button} from './ui/button';
import {Textarea} from './ui/textarea';
import {Dialog,DialogContent,DialogHeader,DialogTitle,DialogDescription} from './ui/dialog';
import {api} from '@/lib/parent-api';
import {randomId} from '@/lib/id';
import {RequestScope} from '@/lib/request-scope';
import type {ParentState} from '@/lib/parent-model';

type Activity={id:string;title:string;area:string;goal:string;materials:string;minutes:number;steps:string[];familiar:boolean;status:string;selection:'ai'|'library';replacementReason?:string};
type Plan={childId:string;day:string;version:number;ageMonths:number;items:Activity[];source:'ai'|'library';viewed:boolean};
const reasons=[['hard','Слишком сложно'],['easy','Слишком просто'],['materials','Нет нужных вещей'],['time','Мало времени'],['dislike','Не понравилось ребёнку'],['health','Не подходит по самочувствию'],['other','Другая причина']];
export default function DailyActivities({state}:{state:ParentState}) {
 const cid=state.activeChildId || 'primary';
 const [plan,setPlan]=useState<Plan>(); const [busy,setBusy]=useState(false); const [error,setError]=useState('');
 const [target,setTarget]=useState<Activity>(); const [reason,setReason]=useState(''); const [detail,setDetail]=useState('');
 const [today,setToday]=useState(''); const mounted=useRef(true); const pending=useRef<{key:string;id:string}>();
 const profileKey=JSON.stringify(state.profile);
 const zone=state.preferences.timezone || 'Europe/Moscow';
 const requestScope=useRef(new RequestScope());
 const contextKey=JSON.stringify([cid,profileKey,today,zone]);
 requestScope.current.select(contextKey);
 useEffect(()=>{const tick=()=>setToday(new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date()));tick();const timer=setInterval(tick,60000);return()=>clearInterval(timer);},[zone]);
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;requestScope.current.cancel();};},[]);
 const load=useCallback(async()=>{
   const ticket=requestScope.current.begin(contextKey);
   const current=()=>mounted.current && requestScope.current.current(ticket);
   setBusy(true);setError('');
   try {const result=await api<Plan>('daily-plan',{childId:cid});if(current()){setPlan(result);setError('');}}
   catch(e){if(current())setError((e as Error).message);}
   finally{if(current())setBusy(false);}
 },[cid,contextKey]);
 useEffect(()=>{setTarget(undefined);pending.current=undefined;if(today){setPlan(undefined);void load();}},[load,today]);
 useEffect(()=>{
   if(!plan || plan.viewed || plan.childId!==cid || plan.day!==today)return;
   const seen=()=>{if(document.visibilityState==='visible')void api('daily-seen',{childId:cid,day:plan.day}).catch(()=>{});};
   seen();document.addEventListener('visibilitychange',seen);return()=>document.removeEventListener('visibilitychange',seen);
 },[cid,plan,today]);
 async function feedback(kind:string,itemId?:string) {
   if(!plan || busy)return;
   if(kind==='replace' && (!reason || detail.trim().length<8))return;
   const data={childId:cid,day:plan.day,version:plan.version,kind,itemId,...(kind==='replace'?{reason,detail:detail.trim()}: {})};
   const key=JSON.stringify(data);
   if(pending.current?.key!==key)pending.current={key,id:randomId()};
   const ticket=requestScope.current.begin(contextKey);
   const current=()=>mounted.current && requestScope.current.current(ticket);
   setBusy(true);setError('');
   try {const result=await api<Plan>('daily-feedback',{...data,requestId:pending.current.id});if(current()){setPlan(result);setTarget(undefined);setDetail('');setReason('');pending.current=undefined;}}
   catch(e){if(current())setError((e as Error).message);}
   finally{if(current())setBusy(false);}
 }
 return <div className="daily-activities">
  <p className="muted">Три игры по возрасту на выбор. Можно попробовать одну — сколько сегодня удобно.</p>
  {busy && <p role="status">{target?'ИИ разбирает причину и подбирает замену…':'Готовим подборку…'}</p>}
  {error && !target && <div role="alert"><p>{error}</p><Button variant="outline" disabled={busy} onClick={()=>void load()}>Обновить подборку</Button></div>}
  {plan && plan.childId===cid && plan.day===today && <>
   <p className="muted text-sm">{new Date(plan.day+'T12:00:00Z').toLocaleDateString('ru-RU')} · {zone === 'Europe/Moscow'?'московское время':zone}</p>
   {plan.items.some(item=>item.selection==='library') && <p className="muted text-sm">При подготовке этой подборки использована резервная библиотека игр. Занятия подобраны по возрасту.</p>}
   {plan.items.map(item=><article key={item.id} className="daily-activity">
    <span className="simple-day-caption">{item.area} · около {item.minutes} мин.</span><h3>{item.title}</h3>
    <p><strong>Что развиваем:</strong> {item.goal}</p>
    {item.familiar && <p className="muted text-sm">Знакомая игра: подходящие новые варианты пока закончились.</p>}
    {item.replacementReason && <p className="muted text-sm">ИИ подобрал замену с учётом пояснения: {item.replacementReason.toLocaleLowerCase('ru')}.</p>}
    <p><strong>Понадобится:</strong> {item.materials}</p>
    <ol>{item.steps.map((step,index)=><li key={index}>{step}</li>)}</ol>
    {item.status!=='new' && <p className="daily-status">{{done:'Отмечено: попробовали',liked:'Учтём, что понравилось',later:'Оставили на потом'}[item.status]}</p>}
    <div className="daily-actions"><Button variant="outline" disabled={busy || item.status==='done'} onClick={()=>void feedback('done',item.id)}>Попробовали</Button><Button variant="outline" disabled={busy || item.status==='liked'} onClick={()=>void feedback('liked',item.id)}>Понравилось</Button><Button variant="ghost" disabled={busy} onClick={()=>{setTarget(item);setReason('');setDetail('');setError('');}}>Заменить</Button><Button variant="ghost" disabled={busy || item.status==='later'} onClick={()=>void feedback('later',item.id)}>На потом</Button></div>
   </article>)}
  </>}
  <Dialog open={!!target} onOpenChange={open=>{if(!open && !busy){setTarget(undefined);setError('');}}}><DialogContent><DialogHeader><DialogTitle>Почему заменить занятие?</DialogTitle><DialogDescription>Расскажите, что не подошло. ИИ учтёт пояснение для этого ребёнка при замене и следующих подборках.</DialogDescription></DialogHeader>
   <form onSubmit={e=>{e.preventDefault();void feedback('replace',target?.id);}} className="space-y-4">
    <label className="form-field">Причина<select required disabled={busy} value={reason} onChange={e=>setReason(e.target.value)}><option value="">Выберите причину</option>{reasons.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
    <label className="form-field">Пояснение — обязательно<Textarea required minLength={8} maxLength={600} disabled={busy} value={detail} onChange={e=>setDetail(e.target.value)} placeholder="Например: ребёнок пока не сидит самостоятельно; нужна игра лёжа или у меня на руках."/></label>
    <p className="muted text-sm">От 8 до 600 символов. При плохом самочувствии занятие можно просто отложить.</p>
    {error && <p role="alert">{error}</p>}
    <Button disabled={busy || !reason || detail.trim().length<8}>{busy?'ИИ подбирает замену…':'Объяснить и заменить'}</Button>
    <Button type="button" variant="ghost" disabled={busy} onClick={()=>{setTarget(undefined);setError('');}}>Оставить занятие</Button>
   </form>
  </DialogContent></Dialog>
 </div>;
}
