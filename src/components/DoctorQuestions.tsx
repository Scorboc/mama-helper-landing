import { canAddQuestion, hasQuestionBeyondContext } from '@/lib/quick-wins';
import { useEffect, useRef, useState } from 'react';
import { confirmAction } from '@/lib/confirm-action';
import { api } from '@/lib/parent-api';
import { randomId } from '@/lib/id';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
export type DoctorQuestion = {id:string;note:string};
export function AskDoctor({childId, ownerId, text, context, disabled=false}: {childId:string;ownerId?:string;text:string;context?:string;disabled?:boolean}) {
 const [busy,setBusy]=useState(false), [notice,setNotice]=useState(''), [undo,setUndo]=useState(''), [undoToken,setUndoToken]=useState('');
 const [draft,setDraft]=useState(text.slice(0,500));
 const [composing,setComposing]=useState(false);
 const questionText=context || text.trim().length>500?draft:text;
 const valid=canAddQuestion([],questionText)&&(!context||hasQuestionBeyondContext(questionText,context));
 const lock=useRef(false), generation=useRef(0);
 useEffect(()=>{const ticket=++generation.current;setNotice('');setUndo('');setUndoToken('');setComposing(false);setDraft(text.slice(0,500));setBusy(false);lock.current=false;return()=>{generation.current=ticket+1;};},[childId,ownerId,text,context]);
 async function act(remove=false) {
  if(lock.current||(!remove&&!valid))return;lock.current=true;setBusy(true);const ticket=generation.current;
  try { const id=remove?undo:randomId();const result=await api<{duplicate?:boolean;id:string;undoToken?:string}>(remove?'doctor-question-delete':'doctor-question-put',{childId,ownerId,id,undoToken:remove?undoToken:undefined,text:questionText.trim()});
   window.dispatchEvent(new Event('doctor-questions-changed'));
   if(ticket!==generation.current)return;
   setNotice(remove?'Добавление отменено':result.duplicate?'Этот вопрос уже в списке':'Добавлено в вопросы врачу');setUndo(!remove&&!result.duplicate?id:'');setUndoToken(result.undoToken || '');
  } catch(e){if(ticket===generation.current)setNotice((e as Error).message);} finally {if(ticket===generation.current){lock.current=false;setBusy(false);}}
 }
 return <div className="my-2 min-w-0"><Button className="min-h-11 whitespace-normal" variant="ghost" disabled={disabled||busy||(!context&&!valid)} onClick={()=>context?setComposing(true):void act()}>Спросить у врача</Button>{(text.trim().length>500||composing)&&<label className="block">Вопрос врачу · до 500 символов<Textarea autoFocus={composing} value={draft} maxLength={500} disabled={busy||disabled} onChange={e=>setDraft(e.target.value)}/></label>}{composing&&<><Button className="min-h-11" disabled={disabled||busy||!valid} onClick={()=>void act()}>Добавить</Button><Button className="min-h-11" variant="ghost" disabled={busy} onClick={()=>{setComposing(false);setDraft(text.slice(0,500));}}>Отмена</Button></>}<p className="text-sm muted">Видят взрослые, у которых есть доступ к профилю ребёнка</p>{notice&&<p role="status" className="break-words">{notice}</p>}{undo&&<Button className="min-h-11" variant="outline" disabled={busy} onClick={()=>void act(true)}>Отменить добавление</Button>}</div>;
}
export function DoctorQuestionList({questions,permission,onChange}: {questions:DoctorQuestion[];permission:string;onChange:(id:string,text?:string)=>Promise<boolean>}) {
 const [editing,setEditing]=useState(''),[text,setText]=useState(''),[busy,setBusy]=useState(false);
 const lock=useRef(false);
 async function change(id:string,value?:string){if(lock.current)return;lock.current=true;setBusy(true);try{if(value===undefined&&!await confirmAction('Удалить этот вопрос из общего списка вопросов врачу?'))return;if(await onChange(id,value))setEditing('');}finally{lock.current=false;setBusy(false);}}
 return <div><h3>Ваши вопросы врачу · {questions.length}/30</h3><p className="text-sm muted">Видят взрослые, у которых есть доступ к профилю ребёнка</p>{!questions.length&&<p>Сохранённые вопросы появятся здесь.</p>}{questions.map(q=><div key={q.id} className="border-b py-3 break-words">{editing===q.id?<div><label>Вопрос<Textarea value={text} maxLength={500} onChange={e=>setText(e.target.value)}/></label><Button className="min-h-11" disabled={busy||!text.trim()} onClick={()=>void change(q.id,text)}>Сохранить</Button><Button className="min-h-11" variant="ghost" disabled={busy} onClick={()=>setEditing('')}>Отмена</Button></div>:<><p className="whitespace-pre-wrap">{q.note}</p>{permission!=='read'&&<Button className="min-h-11" variant="ghost" disabled={busy} onClick={()=>{setEditing(q.id);setText(q.note);}}>Изменить</Button>}{permission==='owner'&&<Button className="min-h-11" variant="ghost" disabled={busy} onClick={()=>void change(q.id)}>Удалить</Button>}</>}</div>)}</div>;
}
