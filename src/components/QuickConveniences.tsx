import {useEffect,useState} from 'react';
import {useLocation,useNavigate} from 'react-router-dom';
import type {ParentState} from '@/lib/parent-model';
import type {CareRecord} from '@/lib/care-journal';
import {api} from '@/lib/parent-api';
import {latestCare,quickFromSearch} from '@/lib/quick-wins';
import ChatQuickCare from './ChatQuickCare';
import {Button} from './ui/button';
import {Dialog,DialogContent,DialogHeader,DialogTitle,DialogDescription} from './ui/dialog';
export default function QuickConveniences({state,onRecords,showLatest}: {state:ParentState;onRecords:()=>void;showLatest:boolean}) {
 const location=useLocation(),navigate=useNavigate();
 const [quick,setQuick]=useState<ReturnType<typeof quickFromSearch>>(null),[records,setRecords]=useState<CareRecord[]>([]),[now,setNow]=useState(Date.now());
 const cid=state.activeChildId||'primary';
 useEffect(()=>{if(!new URLSearchParams(location.search).has('quick'))return;setQuick(quickFromSearch(location.search));const p=new URLSearchParams(location.search);p.delete('quick');navigate({pathname:location.pathname,search:p.toString(),hash:location.hash},{replace:true});},[location.search,location.pathname,location.hash,navigate]);
 useEffect(()=>{let active=true;setRecords([]);const load=()=>{if(state.profile?.stage==='child')void api<{records:CareRecord[]}>('care-list',{childId:cid}).then(r=>{if(active)setRecords(r.records);}).catch(()=>{});};load();window.addEventListener('care-records-changed',load);const timer=setInterval(()=>setNow(Date.now()),60000);return()=>{active=false;clearInterval(timer);window.removeEventListener('care-records-changed',load);};},[cid,state.profile?.stage]);
 const label=state.profile?.stage==='child'?latestCare(records,now,state.profile.childSex):'';
 return <>{showLatest&&label&&<Button className="min-h-11 h-auto w-full whitespace-normal break-words text-left justify-start my-2" variant="outline" onClick={onRecords}>{label}</Button>}<Dialog open={!!quick} onOpenChange={open=>{if(!open)setQuick(null);}}><DialogContent className="max-h-[85dvh] overflow-y-auto"><DialogHeader><DialogTitle>{quick==='sleep'?'Начать сон':quick==='feed'?'Кормление':'Записать'}</DialogTitle><DialogDescription>Выберите отметку и подтвердите сохранение.</DialogDescription></DialogHeader>{state.profile?.stage==='child'?<ChatQuickCare key={cid+quick} state={state} initialQuick={quick} onTrackers={()=>{setQuick(null);onRecords();}}/>:<p>Быстрые записи ухода доступны в профиле ребёнка после рождения.</p>}</DialogContent></Dialog></>;
}
