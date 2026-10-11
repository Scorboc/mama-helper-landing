import {useEffect,useState} from 'react';
import {Bookmark} from 'lucide-react';
import {Button} from './ui/button';
import {Input} from './ui/input';
import {Textarea} from './ui/textarea';
import type {ParentState, Message} from '@/lib/parent-model';
import {favoriteAnswer} from '@/lib/family';
import type {Favorite} from '@/lib/family';
import {api} from '@/lib/parent-api';

const categories:Record<string,string>={other:'Без раздела',sleep:'Сон',feeding:'Питание',play:'Игры',mom:'Для мамы','first-aid':'Первая помощь'};
type Props = {state:ParentState; busy:boolean; save:(state:ParentState,notice?:string)=>Promise<boolean>};
export function FavoriteButton({state,busy,save,message}:Props & {message:Message}) {
  const selected = state.favorites?.some(item => item.id === message.id && item.childId === (state.activeChildId || 'primary'));
  return <Button type="button" variant="outline" className="mt-3" disabled={busy || selected || (state.favorites?.length || 0) >= 200} onClick={()=>void save(favoriteAnswer(state,message),'Ответ в избранном')}><Bookmark size={16}/>{selected ? 'В избранном' : 'В избранное'}</Button>;
}
export default function Favorites({state,busy,save}:Props) {
  const [query,setQuery]=useState(''),[category,setCategory]=useState('all'),[child,setChild]=useState('all');
  const favorites=state.favorites || [];
  const [materials,setMaterials]=useState<{id:string;title:string;text:string;category:string}[]>([]);
  useEffect(()=>{let active=true;setMaterials([]);api<{items:typeof materials}>('materials').then(r=>{if(active)setMaterials(r.items||[]);}).catch(()=>{});return()=>{active=false;};},[state.activeChildId,state.profile?.birthDate,state.profile?.stage]);
  const filtered=favorites.filter(item=>(category==='all'||(item.category||'other')===category)&&(child==='all'||item.childId===child)&&`${item.childName} ${item.question} ${item.text} ${item.note||''}`.toLocaleLowerCase('ru').includes(query.toLocaleLowerCase('ru')));
  return <section className="tile"><h2>Моя библиотека</h2><p className="muted">Сохранённые ответы и свои заметки. До 200 записей.</p>
    <Input aria-label="Поиск в избранном" placeholder="Найти ответ или заметку" value={query} onChange={e=>setQuery(e.target.value)}/>
    <div className="my-3 grid gap-3 sm:grid-cols-2"><label>Тема<select className="block w-full rounded-xl border border-border bg-background p-3 text-foreground" value={category} onChange={e=>setCategory(e.target.value)}><option value="all">Все темы</option>{Object.entries(categories).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
    <label>Для кого<select className="block w-full rounded-xl border border-border bg-background p-3 text-foreground" value={child} onChange={e=>setChild(e.target.value)}><option value="all">Вся семья</option>{Array.from(new Map(favorites.map(f=>[f.childId,f.childName])).entries()).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label></div>
    {!favorites.length&&<p className="my-5">Нажмите «В избранное» под ответом в чате — он появится здесь.</p>}
    {favorites.length>0&&!filtered.length&&<p className="my-5">Ничего не найдено. Попробуйте изменить фильтры.</p>}
    {filtered.map(item=><SavedItem key={`${item.childId}:${item.id}`} item={item} busy={busy} onSave={updated=>save({...state,favorites:favorites.map(f=>f.id===item.id&&f.childId===item.childId?updated:f)},'Запись сохранена')} onRemove={()=>void save({...state,favorites:favorites.filter(f=>!(f.id===item.id&&f.childId===item.childId))},'Убрано из избранного')}/>)}
    {materials.length>0&&<div className="mt-6"><h3>Подборка для вас</h3>{materials.map(item=><article className="tile my-4" key={item.id}><h3>{item.title}</h3><p className="whitespace-pre-wrap break-words">{item.text}</p><Button variant="outline" disabled={busy||favorites.length>=200||favorites.some(f=>f.id===item.id&&f.childId===(state.activeChildId||'primary'))} onClick={()=>void save({...state,favorites:[{id:item.id,childId:state.activeChildId||'primary',childName:state.profile?.childName||'Для меня',text:item.text.slice(0,2500),question:item.title,savedAt:new Date().toISOString(),category:item.category},...favorites]},'Материал сохранён')}>Сохранить</Button></article>)}</div>}
  </section>;
}

function SavedItem({item,busy,onSave,onRemove}: {item:Favorite;busy:boolean;onSave:(item:Favorite)=>Promise<boolean>;onRemove:()=>void}) {
  const [editing,setEditing]=useState(false),[note,setNote]=useState(item.note||''),[category,setCategory]=useState(item.category||'other');
  return <article className="tile my-4 min-w-0"><p className="muted">{item.childName} · {categories[item.category||'other']} · {new Date(item.savedAt).toLocaleDateString('ru-RU')}</p>
    {item.question&&<h3 className="break-words">{item.question}</h3>}<p className="whitespace-pre-wrap break-words">{item.text}</p>
    {item.note&&!editing&&<p className="mt-3 whitespace-pre-wrap break-words"><strong>Моя заметка: </strong>{item.note}</p>}
    {editing&&<div className="my-4 space-y-3"><label className="block">Раздел<select className="block w-full rounded-xl border border-border bg-background p-3 text-foreground" value={category} onChange={e=>setCategory(e.target.value)}>{Object.entries(categories).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
      <label className="block">Моя заметка<Textarea value={note} maxLength={1000} onChange={e=>setNote(e.target.value)}/></label>
      <Button disabled={busy} onClick={async()=>{if(await onSave({...item,note,category}))setEditing(false);}}>Сохранить</Button>
      <Button variant="ghost" disabled={busy} onClick={()=>setEditing(false)}>Отмена</Button></div>}
    <div className="mt-3 flex flex-wrap gap-2"><Button variant="outline" disabled={busy} onClick={()=>{setNote(item.note||'');setCategory(item.category||'other');setEditing(true);}}>Раздел и заметка</Button><Button variant="ghost" disabled={busy} onClick={onRemove}>Убрать</Button></div>
  </article>;
}
