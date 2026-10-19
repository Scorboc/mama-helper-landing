import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ruCount } from '@/lib/ru-count';
import '@/components/sleep-diary.css';

const articles = [
  ['Записать сон, даже если не отметили сразу', 'В чате можно начать таймер. Если момент пропущен, внесите начало и окончание вручную. Проверьте день и время; переход через полночь должен оставаться одним эпизодом.'],
  ['Исправить ошибку в дневнике', 'Откройте запись в трекере, исправьте время или удалите ошибочную отметку. После сохранения проверьте график. Прежний ответ в чате остаётся частью истории; для новых данных задайте новый вопрос.'],
  ['Неполный дневник тоже можно использовать', 'Выберите один вопрос и отмечайте относящиеся к нему события. Пропуски не означают отсутствие сна или кормлений. Не сравнивайте суммы за дни, которые записаны с разной полнотой.'],
  ['Подготовить вопросы о сне', 'Опишите, что именно происходит при укладывании, когда это началось и что уже пробовали. Добавьте выбранные записи сна. По одним числам нельзя назначить точное время следующего засыпания.'],
  ['Кормления: событие и таймер', 'Отметка сохраняет время события; таймер — начало и окончание. Число записей не показывает, достаточно ли ребёнок получает питания. Записывайте наблюдения, которые хотите обсудить.'],
  ['Передать уход близкому', 'Проверьте последние отметки сна и кормления, договоритесь о конкретной задаче. В разделе «Семья» выберите право просмотра или добавления записей. Личную переписку передавать не нужно; доступ можно отозвать.'],
  ['Игра подходит не только по возрасту', 'Возраст ограничивает подбор, но не доказывает навык. Отмечайте, что ребёнок умеет и какая помощь нужна. Если занятие сложно или нет вещей, укажите причину замены; не нужно выполнять его ради галочки.'],
  ['Когда занятие не понравилось', 'Остановитесь и опишите, какая часть не подошла. Причины «нет материалов», «сложно» и «не понравилось» помогают подобрать другой вариант. Объяснение важнее количества выполненных игр.'],
  ['Собрать записи к специалисту', 'Выберите период и отдельные отметки в разделе «К врачу». Посмотрите предпросмотр, добавьте вопросы и сохраните PDF. Переписка и самочувствие родителя не включаются. Документ — наблюдения, а не диагноз.'],
  ['Поддержка без обязательного плана', 'Можно написать «мне сейчас нужно, чтобы меня выслушали» или попросить небольшой практический шаг. Не обязательно вести дневник настроения. ИИ не заменяет близких, психолога или срочную помощь.'],
  ['Разные дети — разные диалоги', 'Перед вопросом проверьте активный профиль. Для другого ребёнка переключите профиль и откройте его разговор. Возраст в сообщении не заменяет дату рождения профиля.'],
  ['Если нет сети или ответ не пришёл', 'Проверьте соединение и повторите отправку после ошибки. До подтверждения сохранения не считайте отметку записанной. Срочная помощь доступна отдельным разделом; при угрозе жизни звоните 112.'],
];

export default function PublicGuide() {
  const {slug}=useParams();
  const slugs=['record-sleep','correct-diary','incomplete-diary','sleep-questions','feeding-records','shared-care','play-and-skills','replace-game','consultation-summary','parent-support','child-profiles','connection-error'];
  const articleIndex=slug?slugs.indexOf(slug):-1;
  const [start,setStart]=useState(''), [end,setEnd]=useState(''), [nextDay,setNextDay]=useState(false);
  const [episodes,setEpisodes]=useState<number[]>([]), [error,setError]=useState('');
  useEffect(()=>{const old=document.title;document.title=(articleIndex>=0?articles[articleIndex][0]:'Дневник ухода: понятные шаги')+' — Мамин помощник';return()=>{document.title=old;};},[articleIndex]);
  function add() {
    const minutes=(v:string)=>Number(v.slice(0,2))*60+Number(v.slice(3));
    const span=minutes(end)+(nextDay?1440:0)-minutes(start);
    if(!start||!end||span<=0||span>1440){setError('Проверьте начало и окончание. Для сна через полночь отметьте следующий день.');return;}
    setEpisodes([...episodes,span]);setError('');setStart('');setEnd('');setNextDay(false);
  }
  return <main className="public-page mx-auto max-w-3xl px-4 py-8">
    <nav className="flex justify-between gap-4 mb-8"><Link to="/">Мамин помощник</Link><Link to="/first-aid">Срочная помощь · 112</Link></nav>
    {slug ? <><Link className="standalone-link" to="/guide">Все полезные материалы</Link><h1 className="text-3xl my-6">{articleIndex>=0?articles[articleIndex][0]:'Материал не найден'}</h1><p className="leading-relaxed">{articleIndex>=0?articles[articleIndex][1]:'Вернитесь к списку и выберите материал.'}</p><Link className="standalone-link mt-6" to="/account">Открыть свой кабинет</Link></> : <>
    <h1 className="text-3xl mb-4">Забота без лишних шагов</h1>
    <p className="mb-6">Короткие инструкции по дневнику, общению и совместному уходу. Это информационные материалы, не медицинские назначения.</p>
    <section className="sleep-section mb-8"><h2>Посчитать отмеченные эпизоды</h2><p>Без имени ребёнка и регистрации. Данные остаются в памяти этой страницы и исчезнут при её закрытии. Не вводите пересекающиеся эпизоды; сумма не оценивает норму сна.</p>
      <div className="form-grid"><label className="form-field">Начало<Input type="time" value={start} onChange={e=>setStart(e.target.value)}/></label><label className="form-field">Окончание<Input type="time" value={end} onChange={e=>setEnd(e.target.value)}/></label></div>
      <label className="flex gap-3 items-center min-h-11"><input type="checkbox" checked={nextDay} onChange={e=>setNextDay(e.target.checked)}/>Окончание на следующий день</label>
      <Button onClick={add} disabled={episodes.length>=30}>Добавить эпизод</Button>{error&&<p role="alert">{error}</p>}
      <p role="status">{ruCount(episodes.length,'эпизод','эпизода','эпизодов')} · {ruCount(episodes.reduce((a,b)=>a+b,0),'минута','минуты','минут')} в сумме.</p>
      {episodes.map((n,i)=><div className="flex justify-between items-center" key={i}><span>Эпизод {i+1}: {n} мин.</span><Button variant="ghost" aria-label={`Удалить эпизод ${i+1}`} onClick={()=>setEpisodes(episodes.filter((_,j)=>j!==i))}>Удалить</Button></div>)}
    </section>
    {articles.map(([title,text],i)=><details className="sleep-section mb-4" id={`guide-${i+1}`} key={title}><summary>{title}</summary><p className="leading-relaxed mt-3">{text}</p><Link className="standalone-link" to={'/guide/'+slugs[i]}>Открыть отдельную страницу</Link></details>)}
    <Link className="standalone-link" to="/account">Перейти в Мамин помощник</Link>
    </>}
  </main>;
}
