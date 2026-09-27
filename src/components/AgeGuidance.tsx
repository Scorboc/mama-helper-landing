import {useEffect,useState,useRef} from 'react';
import {api} from '@/lib/parent-api';
import {Button} from '@/components/ui/button';
type Card={id:string;category:string;section?:string;title:string;text:string;minMonths:number;maxMonths:number;note:string;priority?:number;priorityLabel?:string};
type Result={childId:string;childName:string;months:number;items:Card[];selected:Card|null;note:string};
export default function AgeGuidance({childId,topic,browse=false}:{childId:string;topic?:string|null;browse?:boolean}){
 const [result,setResult]=useState<Result>();const [error,setError]=useState('');const [retry,setRetry]=useState(0);
 const container=useRef<HTMLElement>(null);
 useEffect(()=>{let active=true;setResult(undefined);setError('');api<Result>('age-guidance',{childId,topic}).then(r=>{if(active)setResult(r);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[childId,topic,retry]);
 useEffect(()=>{if(result&&!browse){const id=requestAnimationFrame(()=>container.current?.scrollIntoView({block:'start'}));return()=>cancelAnimationFrame(id);}},[result,browse]);
 if(error)return <div className="tile" role="alert">{error}<Button variant="outline" onClick={()=>setRetry(x=>x+1)}>Повторить загрузку</Button></div>;
 if(!result)return <p role="status">Открываем подсказки по возрасту…</p>;
 const cards=browse?result.items:result.selected?[result.selected]:[];
 return <section ref={container} className="age-guidance" aria-label="Подсказки по возрасту">
  <h2>{browse?'Сейчас по возрасту':'Подсказка из уведомления'}</h2><p className="muted">{result.childName} · {result.months} мес.</p>
  {!cards.length&&<p>Эта подсказка недоступна. Посмотрите актуальные темы в «Советнике».</p>}
  {(browse?['Игры','Развитие','Уход и гигиена','Советы педиатров']:['Подсказка']).map(section=>{const group=browse?cards.filter(card=>(card.section||'Развитие')===section):cards;return group.length>0&&<div key={section}>
  {browse&&<h3>{section}</h3>}<div className="age-guidance-grid">{group.map(card=><article className="tile age-guidance-card" key={card.id}>
   <small>{card.priorityLabel&&<strong>{card.priorityLabel} · </strong>}{card.category} · Подборка на {card.minMonths===card.maxMonths-1?card.minMonths:`${card.minMonths}–${card.maxMonths-1}`} мес.</small><h3>{card.title}</h3>
   {(result.months<card.minMonths||result.months>=card.maxMonths)&&<p className="muted">Это подсказка для другого возрастного этапа. Проверьте актуальные темы в «Советнике».</p>}
   <p>{card.text}</p>
  </article>)}</div></div>})}<p className="muted text-sm">{result.note}</p>
 </section>;
}
