import { useEffect, useRef, useState } from 'react';
import { Bell, Heart, MessageCircle, Send, ShieldCheck, UserRound } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { assistant, Profile, Reply } from '@/lib/assistant';
import './workspace.css';


type Message = { id: number; who: 'user' | 'assistant'; text: string; reply?: Reply };
const welcome: Message = { id: 0, who: 'assistant', text: 'Здравствуйте! Выберите готовый вопрос или напишите свой. Пока это демо без AI — я не ставлю диагнозы и не назначаю лечение.' };
export default function DemoChat() {
  const [tab, setTab] = useState('chat');
  const [profile, setProfile] = useState<Profile>({ stage: 'child', age: 6, role: 'Мама' });
  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState<Message[]>([welcome]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [reminder, setReminder] = useState<'new' | 'read' | 'hidden'>('new');
  const [repeat, setRepeat] = useState('manual');
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ block: 'nearest' }); }, [messages, tab]);
  const milestone = profile.stage === 'child' && profile.age === 6;
  const context = profile.stage === 'child' ? `Ребёнку ${profile.age} мес.` : `Беременность · ${profile.age} нед.`;
  async function send(text: string) {
    const question = text.trim(); if (!question || busy) return;
    setDraft(''); setBusy(true);
    setMessages(previous => [...previous, { id: Date.now(), who: 'user', text: question }]);
    try { const reply = await assistant.reply(question, profile); setMessages(previous => [...previous, { id: Date.now() + 1, who: 'assistant', text: reply.text, reply }]); }
    catch { setMessages(previous => [...previous, { id: Date.now() + 1, who: 'assistant', text: 'Не получилось получить ответ. Попробуйте ещё раз. При угрозе жизни звоните 112.' }]); }
    finally { setBusy(false); }
  }
  async function testNotification() {
    if (!('Notification' in window)) { setNotice('Этот браузер не поддерживает уведомления. Напоминания доступны внутри сайта.'); return; }
    try {
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') { setNotice('Разрешение не получено. Его можно изменить в настройках браузера.'); return; }
      const notification = new Notification('Мама рядом · тест', { body: 'Это тест уведомления, не медицинская рекомендация.' });
      notification.onclick = () => { window.focus(); setTab('advisor'); notification.close(); };
      setNotice('Тестовое уведомление отправлено. Фоновые push пока не подключены.');
    } catch { setNotice('Системное уведомление недоступно в этом браузере. Внутренние напоминания работают.'); }
  }
  function changeProfile(next: Profile) { setProfile(next); setReminder('new'); }
  return <div className="parent-app">
    <header className="app-header"><a className="brand" href="/"><Heart fill="currentColor" aria-hidden="true" /> Мама рядом</a><span className="demo-badge">Демо · без AI API</span></header>
    <div className="workspace"><aside className="intro"><span className="eyebrow">ДЛЯ МАМ И ПАП</span><h1>Вы не одни.<br />Давайте по шагам.</h1><p>От ожидания малыша до первых трёх лет. Поддержка, полезные ориентиры и место для ваших вопросов.</p><div className="profile-summary"><UserRound /><div><strong>{profile.role}</strong><p>{context}</p></div></div><div className="safety-note"><ShieldCheck /><p>Помощник не заменяет врача. При угрозе жизни — <a href="tel:112">112</a>. Демо не умеет надёжно распознавать опасные состояния.</p></div><p className="small">Не вводите ФИО, контакты и медицинские документы. Данные этой страницы исчезнут после перезагрузки.</p></aside>
      <main className="main-panel"><Tabs value={tab} onValueChange={setTab}><TabsList className="app-tabs"><TabsTrigger value="chat"><MessageCircle size={18} />Чат</TabsTrigger><TabsTrigger value="advisor"><Bell size={18} />Советник</TabsTrigger><TabsTrigger value="profile"><UserRound size={18} />Профиль</TabsTrigger></TabsList>
        <TabsContent value="chat"><div className="panel-heading"><div><h2>Можно спросить</h2><p>Готовые сценарии для знакомства с помощником</p></div><Button variant="ghost" onClick={() => setMessages([welcome])}>Новый чат</Button></div>
          {milestone && reminder === 'new' && <button className="milestone" onClick={() => setTab('advisor')}><Bell size={18} /><span>6 месяцев · Ориентир по началу прикорма</span><span>Открыть</span></button>}
          <div className="messages" role="log" aria-label="Переписка" aria-live="polite">{messages.map(message => <article key={message.id} className={`message ${message.who}`}><span className="message-label">{message.who === 'user' ? 'Вы' : 'Мама рядом · готовый ответ'}</span><p>{message.text}</p>{message.reply && <span className="route-label">{message.reply.mode === 'urgent' ? 'Сценарий безопасности' : message.reply.mode === 'deep' ? 'Будущий режим: углублённый' : 'Будущий режим: быстрый'}</span>}</article>)}<div ref={end} /></div>
          <div className="suggestions">{['Мне нужна поддержка', 'Когда вводить прикорм?', 'Как папе помочь?'].map(question => <button key={question} disabled={busy} onClick={() => void send(question)}>{question}</button>)}</div><form className="composer" onSubmit={event => { event.preventDefault(); void send(draft); }}><Textarea aria-label="Ваш вопрос" placeholder="Напишите вопрос…" value={draft} maxLength={2000} onChange={event => setDraft(event.target.value)} /><Button disabled={busy || !draft.trim()} type="submit" aria-label="Отправить"><Send size={20} /></Button></form><p className="small below">Без генерации AI. Готовый ответ может не соответствовать вашей ситуации.</p>
        </TabsContent>
        <TabsContent value="advisor"><div className="panel-heading"><div><h2>Возрастной советник</h2><p>{context} · без ежедневных рассылок</p></div></div><div className="section-body"><p>Возраст — ориентир, а не назначение процедур. В демо подключён один пример события: 6 месяцев.</p>{milestone && reminder !== 'hidden' ? <article className="advice-card"><span className="eyebrow">6 МЕСЯЦЕВ · ПИТАНИЕ</span><h3>Обсудить начало прикорма</h3><p>ВОЗ рекомендует начало прикорма в 6 месяцев. При особенностях здоровья обсудите индивидуальный план с педиатром.</p><div className="actions"><Button onClick={() => { setTab('chat'); setReminder('read'); void send('Когда вводить прикорм?'); }}>Открыть в чате</Button><Button variant="outline" onClick={() => setReminder('hidden')}>Скрыть</Button></div>{reminder === 'read' && <p className="small">Прочитано</p>}</article> : <div className="empty-state"><Bell /><h3>{reminder === 'hidden' ? 'Напоминание скрыто' : 'Для этого возраста пока нет карточек'}</h3><p>Это ограничение демонстрационной базы, а не отсутствие важных событий.</p>{reminder === 'hidden' && <Button variant="outline" onClick={() => setReminder('new')}>Вернуть напоминание</Button>}</div>}<label className="field">Непрочитанные напоминания<Select value={repeat} onValueChange={setRepeat}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="manual">Повторять только по моему запросу</SelectItem><SelectItem value="never">Не повторять</SelectItem></SelectContent></Select></label>{repeat === 'manual' && milestone && <Button variant="outline" onClick={() => setReminder('new')}>Повторить карточку в чате</Button>}<hr /><h3>Уведомления браузера</h3><p>Сейчас доступен только ручной тест на открытой странице. Доставка при закрытом сайте требует сервера.</p><Button variant="outline" onClick={() => void testNotification()}>Проверить уведомление</Button><p role="status">{notice}</p></div></TabsContent>
        <TabsContent value="profile"><div className="panel-heading"><div><h2>Ваш тестовый профиль</h2><p>Один ребёнок · без общего доступа</p></div></div><div className="section-body"><p>Это не аккаунт. Настройки хранятся только в памяти открытой страницы и не отправляются на сервер помощника.</p><label className="field">Кто вы<Select value={profile.role} onValueChange={role => changeProfile({ ...profile, role })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{['Мама','Папа'].map(role => <SelectItem key={role} value={role}>{role}</SelectItem>)}</SelectContent></Select></label><label className="field">Ваш этап<Select value={profile.stage} onValueChange={stage => changeProfile({ ...profile, stage: stage as Profile['stage'], age: stage === 'child' ? 6 : 20 })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="pregnancy">Ожидаем малыша</SelectItem><SelectItem value="child">Ребёнок родился</SelectItem></SelectContent></Select></label><label className="field">{profile.stage === 'child' ? 'Полных месяцев (0–36)' : 'Полных недель беременности (1–42)'}<Input type="number" min={profile.stage === 'child' ? 0 : 1} max={profile.stage === 'child' ? 36 : 42} value={profile.age} onChange={event => { const age = Number(event.target.value); if (Number.isInteger(age) && age >= (profile.stage === 'child' ? 0 : 1) && age <= (profile.stage === 'child' ? 36 : 42)) changeProfile({ ...profile, age }); }} /></label><p className="small">Возраст задаётся вручную для теста. Автоматический расчёт по дате рождения и защищённые аккаунты ещё не подключены.</p><Button onClick={() => setTab('chat')}>Вернуться к помощнику</Button></div></TabsContent>
        
      </Tabs></main></div><footer className="app-footer">Мама рядом · тестовая версия без оплаты и внешних AI-запросов</footer>
  </div>;
}
