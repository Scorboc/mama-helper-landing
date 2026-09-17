import { useState } from 'react';
import { conversationList, openConversation } from '@/lib/conversations';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { api, Quota } from '@/lib/parent-api';
import { contextLabel, MedicalCardEntry, Message, ParentState } from '@/lib/parent-model';

type Save=(next:ParentState,notice?:string)=>Promise<boolean>;
export function ChatContext({state,quota,onProfile}:{state:ParentState;quota?:Quota;onProfile:()=>void}) {
  return <div className="rounded-2xl border bg-cream p-4 my-4 flex flex-wrap justify-between gap-3 items-center"><div><strong>{contextLabel(state.profile)}</strong><p className="text-sm muted">Учитываем профиль, подтверждённые вами заметки и текущий диалог.</p>{quota&&<p className="text-sm mt-1" role="status">Осталось {quota.remaining} из {quota.limit} AI-ответов на тест.</p>}</div><Button variant="outline" onClick={onProfile}>Исправить профиль</Button></div>;
}

export function AnswerFeedback({message}:{message?:Message}) {
  const [kind,setKind]=useState(''),[comment,setComment]=useState(''),[consent,setConsent]=useState(false),[busy,setBusy]=useState(false),[status,setStatus]=useState('');
  async function submit(){setBusy(true);setStatus('');try{await api('feedback',{kind,messageId:message?.id,comment,consentContext:consent,requestId:crypto.randomUUID()});setKind('');setComment('');setConsent(false);setStatus('Спасибо! Отзыв сохранён для разработчика.');}catch(e){setStatus((e as Error).message);}finally{setBusy(false);}}
  return <div className="mt-3 text-sm"><div className="flex flex-wrap gap-2">{(message?[['helpful','Помогло'],['unhelpful','Не помогло'],['unsafe','Неверный / опасный совет']]:[['idea','Предложить улучшение']]).map(([value,title])=><button type="button" className="rounded-lg border px-3 py-2 hover:bg-cream" key={value} onClick={()=>{setKind(value);setStatus('');}}>{title}</button>)}</div>{status&&<p role="status" className="mt-2">{status}</p>}<Dialog open={!!kind} onOpenChange={v=>{if(!busy&&!v)setKind('');}}><DialogContent><DialogHeader><DialogTitle>Обратная связь разработчику</DialogTitle><DialogDescription>Обращения хранятся приватно. Не используйте форму для срочной помощи.</DialogDescription></DialogHeader><label>Комментарий — необязательно<Textarea value={comment} maxLength={1000} onChange={e=>setComment(e.target.value)} placeholder="Что улучшить? Не указывайте контакты и личные сведения."/></label><label className="flex gap-3 items-start text-sm"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>Разрешаю приложить профиль и последние сообщения этого диалога, включая сведения о здоровье. Без согласия отправятся только моя оценка, комментарий и технические идентификаторы.</label>{status&&<p role="alert">{status}</p>}<Button disabled={busy} onClick={()=>void submit()}>{busy?'Отправляем…':'Отправить'}</Button></DialogContent></Dialog></div>;
}

export function ConversationControls({state,save,busy}:{state:ParentState;save:Save;busy:boolean}) {
  const [title,setTitle]=useState('');
  const [creating,setCreating]=useState(false);
  const [saving,setSaving]=useState(false);
  const locked=busy||saving;
  const threads=conversationList(state);
  const activeId=state.conversationId || 'legacy-active';
  async function change(request:{id:string}|{title:string}){
    if(locked)return;
    const next=openConversation(state,request);
    if(next===state)return;
    setSaving(true);
    try { if(await save(next,'Диалог открыт')){setTitle('');setCreating(false);} }
    finally {setSaving(false);}
  }
  return <div className="space-y-3 mb-4">
    <nav aria-label="Диалоги" className="flex flex-wrap gap-2">
      {threads.map(t=><button type="button" key={t.id} aria-current={t.id===activeId?'page':undefined}
        disabled={locked} onClick={()=>void change({id:t.id})}
        className={`min-h-11 max-w-full rounded-xl border px-4 py-2 text-left text-sm break-words transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${t.id===activeId?'bg-primary text-primary-foreground border-primary':'bg-background/40 hover:bg-secondary'}`}>{t.title}</button>)}
      <Button type="button" variant="outline" disabled={locked||threads.length>=21} onClick={()=>setCreating(v=>!v)} aria-expanded={creating}>+ Новый диалог</Button>
    </nav>
    {creating&&<form className="flex flex-wrap gap-2" onSubmit={e=>{e.preventDefault();void change({title});}}>
      <Input autoFocus className="max-w-xs" value={title} maxLength={80} disabled={locked} onChange={e=>setTitle(e.target.value)} placeholder="Например: Сон малыша" aria-label="Название нового диалога"/>
      <Button type="submit" disabled={locked||!title.trim()}>Создать</Button>
      <Button type="button" variant="ghost" disabled={locked} onClick={()=>setCreating(false)}>Отмена</Button>
    </form>}
    {threads.length>=21&&<p className="text-sm muted">Достигнут лимит: 21 диалог. Удалите ненужный в списке ниже.</p>}
    <div className="flex flex-wrap gap-2 items-center">
      <label className="text-sm">Формат ответа <select aria-label="Формат ответа" className="rounded-lg border bg-background p-2" disabled={locked} value={state.preferences.answerStyle || 'short'} onChange={e=>void save({...state,preferences:{...state.preferences,answerStyle:e.target.value as 'short'|'steps'|'detail'}},'Формат сохранён')}>
        <option value="short">Коротко</option><option value="steps">По шагам</option><option value="detail">Подробнее</option>
      </select></label>
      {!!state.conversations?.length&&<details className="text-sm"><summary className="cursor-pointer p-2">Удаление диалогов</summary>
        <div className="flex flex-wrap gap-2 p-2">{state.conversations.map(t=><Button key={t.id} type="button" variant="ghost" disabled={locked} aria-label={`Удалить диалог ${t.title}`} onClick={()=>{if(window.confirm(`Удалить диалог «${t.title}»?`))void save({...state,conversations:state.conversations?.filter(x=>x.id!==t.id),conversationOrder:state.conversationOrder?.filter(id=>id!==t.id)},'Диалог удалён');}}>Удалить «{t.title}»</Button>)}</div>
      </details>}
    </div>
  </div>;
}

function MemoryItem({entry,pending,onSave,onRemove,busy}:{entry:MedicalCardEntry;pending:boolean;onSave:(entry:MedicalCardEntry)=>void;onRemove:()=>void;busy:boolean}) {
  const [text,setText]=useState(entry.text),[confirmation,setConfirmation]=useState<'parent'|'doctor'>(entry.confirmation==='doctor'?'doctor':'parent');
  return <div className="rounded-xl border p-4 space-y-3"><p className="text-sm muted">{pending?'Предложение — пока не в памяти':new Date(entry.date).toLocaleDateString('ru-RU')}</p><Textarea aria-label="Текст заметки" value={text} maxLength={500} onChange={e=>setText(e.target.value)} disabled={busy}/><label className="text-sm flex gap-2 items-start"><input type="checkbox" checked={confirmation==='doctor'} onChange={e=>setConfirmation(e.target.checked?'doctor':'parent')} disabled={busy}/>По моим сведениям, это подтверждено врачом. Без отметки запись остаётся наблюдением родителя, не диагнозом.</label><div className="flex gap-2"><Button disabled={busy||!text.trim()} onClick={()=>onSave({...entry,text:text.trim(),confirmation})}>{pending?'Подтвердить и сохранить':'Сохранить изменения'}</Button><Button variant="ghost" disabled={busy} onClick={onRemove}>{pending?'Не сохранять':'Удалить'}</Button></div></div>;
}
export function MemoryReview({state,save,busy,pendingOnly=false}:{state:ParentState;save:Save;busy:boolean;pendingOnly?:boolean}) {
  const pending=state.pendingMemory || [];
  if(pendingOnly&&!pending.length)return null;
  return <div className="space-y-3 my-4">{!!pending.length&&<><h3>Сохранить в память?</h3><p className="muted text-sm">Проверьте формулировку. Пока вы не подтвердили, эти предложения не входят в карту. Исходное сообщение остаётся в истории текущего разговора.</p>{pending.map(e=><MemoryItem key={e.id} entry={e} pending busy={busy} onSave={entry=>void save({...state,medicalCard:[entry,...state.medicalCard].slice(0,120),pendingMemory:pending.filter(x=>x.id!==e.id)},'Заметка подтверждена')} onRemove={()=>void save({...state,pendingMemory:pending.filter(x=>x.id!==e.id)},'Предложение удалено')}/>)}</>}{!pendingOnly&&state.medicalCard.map(e=><MemoryItem key={e.id} entry={e} pending={false} busy={busy} onSave={entry=>void save({...state,medicalCard:state.medicalCard.map(x=>x.id===e.id?entry:x)})} onRemove={()=>void save({...state,medicalCard:state.medicalCard.filter(x=>x.id!==e.id)},'Заметка удалена')}/>)}</div>;
}
