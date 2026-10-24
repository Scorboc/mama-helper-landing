import {useEffect, useRef, useState} from 'react';
import type {Profile} from '@/lib/parent-model';
import {playAge} from '@/lib/together-profile';
import './together-games.css';

/** Trusted UI at the same origin, not a security isolation boundary.
 * Messages carry only completed months. Never a DOB,
 * name, child ID, history, health field, auth token or profile object. */
export default function TogetherGames({profile,contextKey='primary',onProfile,active=true}: {
  profile:Profile|null;contextKey?:string;onProfile?:()=>void;active?:boolean;
}) {
  const mode='profile';
  const age=playAge(profile);
  const frame=useRef<HTMLIFrameElement>(null);
  const [ready,setReady]=useState(false);
  const [failed,setFailed]=useState(false);
  const src=import.meta.env.BASE_URL+'together-games/index.html#profile';
  useEffect(()=>{
    setReady(false);setFailed(false);
    let acknowledged=false;
    const timeout=window.setTimeout(()=>{if(!acknowledged)setFailed(true);},12000);
    const send=()=>frame.current?.contentWindow?.postMessage({type:'mama-games-context',mode,ageMonths:age},window.location.origin);
    const receive=(event:MessageEvent)=>{
      if(event.origin!==window.location.origin||event.source!==frame.current?.contentWindow)return;
      if(event.data?.type==='mama-games-request-context')send();
      if(event.data?.type==='mama-games-ready'){acknowledged=true;setFailed(false);setReady(true);window.clearTimeout(timeout);}
    };
    window.addEventListener('message',receive);
    send();
    return()=>{window.clearTimeout(timeout);window.removeEventListener('message',receive);};
  },[age,contextKey,mode]);
  useEffect(()=>{frame.current?.contentWindow?.postMessage({type:'mama-games-activity',active},window.location.origin);},[active,ready]);
  if(age===null)return <section className="together-empty">
    <h3>Для занятий нужен профиль ребёнка</h3>
    <p>Подборка рассчитана на возраст от рождения до 6 лет включительно. Беременность и неизвестный возраст не заменяют профиль родившегося ребёнка.</p>
    {onProfile&&<button type="button" className="glass-btn px-5 py-3" onClick={onProfile}>Открыть профиль</button>}
  </section>;
  return <section className="together-library" aria-label="Библиотека совместных игр и занятий">
    {!ready&&<p role="status">{failed?'Не удалось открыть библиотеку. Обновите страницу.':'Открываем игры и занятия…'}</p>}
    <iframe key={`${mode}:${contextKey}:${age}`} ref={frame} src={src}
      title="Игры и образовательные занятия с мамой"
      className="together-library-frame" referrerPolicy="no-referrer"
      onError={()=>setFailed(true)} onLoad={()=>{frame.current?.contentWindow?.postMessage(
        {type:'mama-games-context',mode,ageMonths:age},window.location.origin);frame.current?.contentWindow?.postMessage({type:'mama-games-activity',active},window.location.origin);}} />
  </section>;
}
