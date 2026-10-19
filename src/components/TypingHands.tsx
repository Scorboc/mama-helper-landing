import { useEffect, useRef, useState, type MutableRefObject } from 'react';
import type { TypingPulse } from '@/lib/typing-keyboard';
import './typing-hands.css';

export default function TypingHands({ active, pulse }: {active: boolean; pulse: MutableRefObject<TypingPulse[]>}) {
  const host = useRef<HTMLDivElement>(null);
  const activeRef = useRef(active);
  activeRef.current=active;
  const [status,setStatus]=useState('loading');
  useEffect(()=>{
    let disposed=false;
    let release:(()=>void)|undefined;
    void import('@/lib/typing-scene').then(async ({mountTypingScene})=>{
      if(disposed || !host.current) return;
      release=await mountTypingScene(host.current, pulse, ()=>activeRef.current);
      if(disposed) release(); else setStatus('ready');
    }).catch(()=>{if(!disposed)setStatus('unavailable');});
    return()=>{disposed=true;release?.();};
  },[pulse]);
  return <div className="typing-hands" data-active={active} data-status={status} aria-hidden="true">
    <div ref={host} className="typing-hands__canvas" />
    {status==='loading' && <div className="typing-hands__loading"><span /><span /><span /></div>}
  </div>;
}
