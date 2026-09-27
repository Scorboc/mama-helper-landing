import {useState} from 'react';
import {Bookmark} from 'lucide-react';
import {Button} from './ui/button';
import {Input} from './ui/input';
import type {ParentState, Message} from '@/lib/parent-model';
import {favoriteAnswer} from '@/lib/family';
type Props = {state:ParentState; busy:boolean; save:(state:ParentState,notice?:string)=>Promise<boolean>};
export function FavoriteButton({state,busy,save,message}:Props & {message:Message}) {
  const selected = state.favorites?.some(item => item.id === message.id && item.childId === (state.activeChildId || 'primary'));
  return <Button type="button" variant="outline" className="mt-3" disabled={busy || selected || (state.favorites?.length || 0) >= 200} onClick={()=>void save(favoriteAnswer(state,message),'Ответ в избранном')}><Bookmark size={16}/>{selected ? 'В избранном' : 'В избранное'}</Button>;
}
export default function Favorites({state,busy,save}:Props) {
  const [query,setQuery]=useState('');
  const favorites=state.favorites || [];
  const filtered=favorites.filter(item=>`${item.childName} ${item.question} ${item.text}`.toLocaleLowerCase('ru').includes(query.toLocaleLowerCase('ru')));
  return <section className="tile"><h2>Избранное</h2><p className="muted">Полезные ответы для всей семьи. До 200 сохранённых ответов.</p><Input aria-label="Поиск в избранном" placeholder="Найти ответ или имя ребёнка" value={query} onChange={e=>setQuery(e.target.value)}/>{!favorites.length && <p className="my-5">Нажмите «В избранное» под ответом в чате — он появится здесь.</p>}{favorites.length > 0 && !filtered.length && <p className="my-5">Ничего не найдено. Попробуйте другое слово.</p>}{filtered.map(item=><article className="tile my-4" key={`${item.childId}:${item.id}`}><p className="muted">{item.childName} · {new Date(item.savedAt).toLocaleDateString('ru-RU')}</p>{item.question && <h3>{item.question}</h3>}<p style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{item.text}</p><Button variant="ghost" disabled={busy} onClick={()=>void save({...state,favorites:favorites.filter(f=>!(f.id===item.id && f.childId===item.childId))},'Убрано из избранного')}>Убрать из избранного</Button></article>)}</section>;
}
