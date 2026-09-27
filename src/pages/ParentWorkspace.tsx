import SimpleMyDay from '@/components/SimpleMyDay';
import AgeGuidance from '@/components/AgeGuidance';
import GuideWelcome from '@/components/GuideWelcome';
import FirstAid from "@/components/FirstAid";
import Favorites, {FavoriteButton} from '@/components/Favorites';
import {familyList, switchChild, addChild} from '@/lib/family';
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import ThemeControl from "@/components/ThemeControl";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Bell,
  Heart,
  MessageCircle,
  UserRound,
  Settings,
  ArrowLeft,
  Send,
  LogOut,
  ClipboardList,
  Cross,
} from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Fox } from "@/components/Critters";
import { HeartCloud, Rattle } from "@/components/BabyIcons";
import {
  ageValue,
  contextLabel,
  defaultProfile,
  dueMilestones,
  emptyState,
  milestones,
  ParentState,
  Profile,
  stateWithProfile,
  today,
} from "@/lib/parent-model";
import {
  ChatContext,
  AnswerFeedback,
  ConversationControls,
  MemoryReview,
} from "@/components/ChatCare";
import { api, Session, Quota, streamChat } from "@/lib/parent-api";
import { randomId } from "@/lib/id";
import {
  EvidencePassport,
  VoiceInput,
  ReadAnswer,
} from "@/components/ParentServices";
import "./parent-app.css";

export default function ParentWorkspace({
  initialTab = "home",
}: {
  initialTab?: string;
}) {
  const [state, setState] = useState<ParentState>(emptyState);
  const [revision, setRevision] = useState(0);
  const [user, setUser] = useState<Session["user"] | null>(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();
  const allowedTabs = ['home','chat','first-aid','favorites','advisor','card','profile','settings'];
  const requestedTab = new URLSearchParams(location.search).get('tab');
  const tab = requestedTab && allowedTabs.includes(requestedTab) ? requestedTab : initialTab;
  const tabNavigation = useRef<HTMLDivElement | null>(null);
  const previousTab = useRef(tab);
  function setTab(next: string) {
    if(next === tab) {
      tabNavigation.current?.scrollIntoView({block:'start',behavior:'smooth'});
      return;
    }
    const params = new URLSearchParams(location.search);
    params.set('tab',next);
    navigate({pathname:location.pathname,search:params.toString()}, {state:{cabinetSection:true}});
  }
  useEffect(()=>{
    if(previousTab.current===tab)return;
    previousTab.current=tab;
    setError('');setNotice('');
    const frame=requestAnimationFrame(()=>tabNavigation.current?.scrollIntoView({block:'start',behavior:'auto'}));
    return()=>cancelAnimationFrame(frame);
  },[tab]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [chatBusy, setChatBusy] = useState(false);
  const [pushBusy, setPushBusy] = useState(false);
  const [quota, setQuota] = useState<Quota>();
  const [birthday,setBirthday]=useState<Session['birthday']>();
  const guidanceTopic=new URLSearchParams(location.search).get('topic');
  const guidanceChild=new URLSearchParams(location.search).get('child');
  const [partial, setPartial] = useState("");
  const [retryRequest, setRetryRequest] = useState<{
    question: string;
    messageId: string;
    revision: number;
  } | null>(null);
  const [draft, setDraft] = useState("");
  const [profileDraft, setProfileDraft] = useState<Profile>(defaultProfile);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const chatLog = useRef<HTMLDivElement | null>(null);
  const responseStart = useRef<HTMLDivElement | null>(null);
  const responseAnchored = useRef(false);
  const [answerMinHeight,setAnswerMinHeight] = useState(0);
  const mountChatLog = useCallback((node: HTMLDivElement | null) => {
    chatLog.current = node;
    if (node) node.scrollTop = node.scrollHeight;
  }, []);
  const [clock, setClock] = useState(Date.now());
  useEffect(() => {
    let active = true;
    api<Session>("session")
      .then(async (s) => {
        const requestedChild=new URLSearchParams(window.location.search).get('child');
        if(requestedChild && familyList(s.state).some(child=>child.id===requestedChild) && requestedChild!==(s.state.activeChildId || 'primary')) {
          const next=switchChild(s.state,requestedChild);
          const saved=await api<{revision:number}>('save',{state:next,revision:s.revision});
          s={...s,state:next,revision:saved.revision};
        }
        if (active) {
          setUser(s.user);
          setQuota(s.quota);
          setBirthday(s.birthday);
          setState(s.state);
          setRevision(s.revision);
          setProfileDraft(s.state.profile ?? defaultProfile());
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (tab !== "chat" || loading) return;
    const frame = requestAnimationFrame(() => {
      const log = chatLog.current;
      if (log) log.scrollTop = log.scrollHeight;
    });
    return () => cancelAnimationFrame(frame);
  }, [loading, state.activeChildId, state.conversationId, tab]);
  useEffect(() => {
    if(tab !== 'chat' || !chatBusy || responseAnchored.current)return;
    const frame=requestAnimationFrame(()=>{
      const log=chatLog.current;
      const answer=responseStart.current;
      if(!log || !answer)return;
      // Anchor once to the start; streaming must not override manual reading.
      log.scrollTop += answer.getBoundingClientRect().top-log.getBoundingClientRect().top-16;
      responseAnchored.current=true;
    });
    return()=>cancelAnimationFrame(frame);
  },[tab,chatBusy]);
  useEffect(() => {
    const tick = () => setClock(Date.now());
    const timer = window.setInterval(tick, 60000);
    window.addEventListener("focus", tick);
    return () => {
      clearInterval(timer);
      window.removeEventListener("focus", tick);
    };
  }, []);
  const due = dueMilestones(state, new Date(clock));
  async function changeChild(next: ParentState, adding = false) {
    if (await save(next, adding ? 'Заполните профиль ребёнка' : 'Профиль переключён')) {
      setProfileDraft(next.profile || defaultProfile());
      setDraft(''); setRetryRequest(null); setPartial('');
      if (adding || !next.profile) setTab('profile');
    }
  }
  async function save(next: ParentState, success = "Сохранено") {
    if (lock.current) return false;
    lock.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const r = await api<{ revision: number }>("save", {
        state: next,
        revision,
      });
      setRevision(r.revision);
      setState(next);
      setNotice(success);
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  async function send(question: string) {
    const q = question.trim();
    if (!q || busy || chatBusy || lock.current) return;
    const last = state.messages[state.messages.length - 1];
    const retry = last?.role === "user" && last.text === q;
    if (state.messages.length >= 118 && !retry) {
      setError("Начните новый чат, чтобы продолжить.");
      return;
    }
    lock.current = true;
    setBusy(true);
    setChatBusy(true);
    responseAnchored.current=false;
    setAnswerMinHeight(Math.max(0,(chatLog.current?.clientHeight || 0)-32));
    setError("");
    setNotice("");
    const messageId =
      retryRequest?.question === q
        ? retryRequest.messageId
        : retry
          ? last.id
          : randomId();
    const request = {
      question: q,
      messageId,
      revision: retryRequest?.question === q ? retryRequest.revision : revision,
    };
    setRetryRequest(request);
    setPartial("");
    setDraft("");
    const withUser = retry
      ? state
      : {
          ...state,
          messages: [
            ...state.messages,
            { id: messageId, role: "user" as const, text: q },
          ],
        };
    setState(withUser);
    try {
      const result = await streamChat(request, (text) =>
        setPartial((current) => current + text),
      );
      setState(result.state);
      setRevision(result.revision);
      if (result.quota) setQuota(result.quota);
      setRetryRequest(null);
      setPartial("");
      setDraft("");
      setNotice("Переписка сохранена");
    } catch (e) {
      const detail = (e as Error).message;
      setPartial("");
      setDraft((current) => current || q);
      setError(
        "Ответ не получен. Текст оставлен на экране и в поле ввода — можно отправить повторно. " +
          detail,
      );
    } finally {
      lock.current = false;
      setBusy(false);
      setChatBusy(false);
    }
  }
  async function submitProfile(e: FormEvent) {
    e.preventDefault();
    const p = state.profile ? {...state.profile, childName: profileDraft.childName?.trim()} : profileDraft;
    if (p.stage === "child" && !p.childName?.trim()) {
      setError("Укажите имя ребёнка или домашнее имя. Фамилия не нужна.");
      return;
    }
    if (
      p.stage === "child" &&
      (!p.birthDate || p.birthDate > today() || ageValue(p) >= 84)
    ) {
      setError(
        "Укажите дату рождения ребёнка от рождения до 6 лет включительно (младше 7 лет).",
      );
      return;
    }
    if (p.health && !p.healthConfirmed) {
      setError("Добавляйте только особенности, подтверждённые специалистом.");
      return;
    }
    if (!state.profile && !window.confirm('Проверьте сведения. Профиль ребёнка заполняется один раз: после сохранения можно изменить только имя. Дату рождения, этап, кормление и другие поля изменить самостоятельно нельзя. Продолжить?')) return;
    if (await save(stateWithProfile(state, p)))
      setTab("home");
  }
  async function logout() {
    setBusy(true);
    try {
      await api("logout");
      setRetryRequest(null);
      setPartial("");
      setDraft("");
      setUser(null);
      setState(emptyState());
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function pushToggle(enable: boolean) {
    if (pushBusy) return;
    if (!enable) {
      try {
        await api("unsubscribe");
        await save({
          ...state,
          preferences: { ...state.preferences, push: false },
        });
      } catch (e) {
        setError((e as Error).message);
      }
      return;
    }
    if (
      !("serviceWorker" in navigator) ||
      !("PushManager" in window) ||
      !("Notification" in window)
    ) {
      setError(
        "Этот браузер не поддерживает push. На iPhone сайт нужно добавить на экран «Домой». Напоминания внутри кабинета доступны всегда.",
      );
      return;
    }
    setPushBusy(true);
    setError('');
    setNotice('Разрешите уведомления в запросе браузера. Если запрос не появился, проверьте настройки разрешений сайта.');
    const timeout = async <T,>(promise: Promise<T>): Promise<T> => {
      let timer: ReturnType<typeof setTimeout>;
      try {
        return await Promise.race([promise, new Promise<T>((_, reject) => {
          timer = setTimeout(() => reject(new Error('Браузер не завершил подключение уведомлений. Откройте сайт в Chrome, Edge или Safari и разрешите уведомления в настройках сайта.')), 20000);
        })]);
      } finally { clearTimeout(timer!); }
    };
    try {
      // Request inside the click gesture, before any network await.
      const permission = await timeout(Notification.requestPermission());
      if (permission !== 'granted') {
        setError('Уведомления не разрешены. Изменить это можно в настройках браузера.');
        return;
      }
      const { pushKey } = await api<{ pushKey: string }>("config");
      if (!pushKey) {
        setError(
          "Владелец ещё не включил фоновые уведомления. Карточки внутри кабинета работают.",
        );
        return;
      }
      const registration =
        await navigator.serviceWorker.register("/parent-sw.js");
      await timeout(navigator.serviceWorker.ready);
      const bytes = Uint8Array.from(
        atob(pushKey.replace(/-/g, "+").replace(/_/g, "/")),
        (c) => c.charCodeAt(0),
      );
      const subscription =
        (await registration.pushManager.getSubscription()) ??
        (await timeout(registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: bytes,
        })));
      await api("subscribe", { subscription: subscription.toJSON() });
      await save({
        ...state,
        preferences: { ...state.preferences, push: true },
      });
    } catch (e) {
      setError((e as Error).message || "Не удалось включить уведомления.");
    } finally {
      setPushBusy(false);
      setNotice('');
    }
  }
  const markEvent = (id: string, status: "read" | "hidden" | "later") =>
    save({
      ...state,
      events: {
        ...state.events,
        [id]: {
          status,
          until:
            status === "later"
              ? Date.now() +
                (state.preferences.repeat === "week" ? 7 : 1) * 86400000
              : 0,
        },
      },
    });
  if (loading)
    return (
      <main className="account-page">
        <p role="status">Открываем ваш кабинет…</p>
      </main>
    );
  if (!user)
    return (
      <main className="account-page">
        <div className="tile account-card">
          <Fox className="h-20 w-20 mx-auto" />
          <h1>Ваш личный кабинет</h1>
          <p>
            Войдите, чтобы профиль, чат и настройки сохранялись между
            посещениями.
          </p>
          {error && (
            <p role="alert" className="form-error mt-4">
              {error}
            </p>
          )}
          <div className="flex flex-wrap gap-3 mt-6">
            <Button asChild>
              <Link to={'/account?next='+encodeURIComponent('/cabinet'+location.search)}>Регистрация и вход</Link>
            </Button>
          </div>
        </div>
      </main>
    );
  return (
    <div className="parent-workspace">
      <header className="cabinet-header">
        <div className="brand-theme">
          <Link to="/" className="flex items-center gap-2">
            <img src="/logo-mark.png" alt="" className="site-logo h-12" />
            <strong>Мамин помощник</strong>
          </Link>
          <ThemeControl />
        </div>
        <div className="flex items-center gap-3">
          <span className="test-pill">Тест без оплаты</span>
          <Button
            variant="ghost"
            onClick={() => void logout()}
            disabled={busy}
            aria-label="Выйти"
          >
            <LogOut size={18} />
          </Button>
        </div>
      </header>
      <main className="cabinet-main">
        <GuideWelcome key={user.id} />
        <div className="cabinet-greeting">
          <div>
            <span className="cap">
              {state.profile?.role === "dad"
                ? "Папа, вы тоже важны"
                : "Забота о малыше начинается с заботы о вас"}
            </span>
            <h1>
              {state.profile ? "Рады, что вы здесь" : "Давайте познакомимся"}
            </h1>
            <p className="muted mt-2">{contextLabel(state.profile)}</p>
          </div>
          <HeartCloud className="h-24 w-24 hidden sm:block" />
        </div>
        <div className="flex flex-wrap items-center gap-3 mb-5">
          <label className="flex items-center gap-2">Ребёнок
            <select aria-label="Выбрать ребёнка" className="rounded-lg border p-2 bg-background max-w-full" value={state.activeChildId || 'primary'} disabled={busy || chatBusy} onChange={e=>void changeChild(switchChild(state,e.target.value))}>
              {familyList(state).map((child,index)=><option key={child.id} value={child.id}>{child.data.profile?.childName || (child.data.profile?.stage === 'pregnancy' ? 'Ожидание малыша' : `Ребёнок ${index+1}`)}</option>)}
            </select>
          </label>
          <Button variant="outline" disabled={busy || chatBusy || familyList(state).length >= 10 || !state.profile} onClick={()=>void changeChild(addChild(state),true)}>Добавить ребёнка</Button>
        </div>
        {!!birthday?.children.length&&<section className="tile birthday-card" role="status"><h2>С днём рождения!</h2><p>{birthday.children.map(c=>c.name).join(', ')} — поздравляем вашу семью! Вспомните вместе любимое событие года и придумайте маленькую праздничную традицию.</p>{birthday.giftPerChild>0&&<p>Подарок: по 5 дополнительных AI-ответов за каждого именинника. Подарочных ответов осталось: {quota?.bonusRemaining ?? birthday.giftRemaining}.</p>}</section>}
        <Tabs
          value={tab}
          onValueChange={(v) => {
            setTab(v);
            setError("");
            setNotice("");
          }}
        >
          <div ref={tabNavigation} className="cabinet-navigation">
            {tab!=='home'&&<Button type="button" variant="ghost" className="mb-2" onClick={()=>location.state?.cabinetSection ? navigate(-1) : setTab('home')}><ArrowLeft size={17}/>Назад</Button>}
          <TabsList className="cabinet-tabs" aria-label="Разделы личного кабинета">
            <TabsTrigger value="home">
              <Heart size={18} />
              Мой день
            </TabsTrigger>
            <TabsTrigger value="chat">
              <MessageCircle size={18} />
              Чат
            </TabsTrigger>
            <TabsTrigger value="first-aid">
              <Cross size={18} />
              Первая помощь
            </TabsTrigger>
            <TabsTrigger value="favorites"><Heart size={18}/>Избранное</TabsTrigger>
            <TabsTrigger value="advisor">
              <Bell size={18} />
              Советник
              {due.length > 0 && <span className="count">{due.length}</span>}
            </TabsTrigger>
            <TabsTrigger value="card">
              <ClipboardList size={18} />
              Карта
              {state.medicalCard.length > 0 && (
                <span className="count">{state.medicalCard.length}</span>
              )}
            </TabsTrigger>
            <TabsTrigger value="profile">
              <UserRound size={18} />
              Профиль
            </TabsTrigger>
            <TabsTrigger value="settings">
              <Settings size={18} />
              Настройки
            </TabsTrigger>
          </TabsList>
          </div>
          {error && (
            <p role="alert" className="form-error my-4">
              {error}
            </p>
          )}
          {notice && (
            <p role="status" className="save-notice">
              {notice}
            </p>
          )}
          <TabsContent value="home">
            <SimpleMyDay state={state} onProfile={() => setTab("profile")} />
          </TabsContent>
          <TabsContent value="first-aid">
            <FirstAid />
          </TabsContent>
          <TabsContent value="favorites">
            <Favorites state={state} busy={busy || chatBusy} save={save}/>
          </TabsContent>
          <TabsContent value="chat">
            {state.profile?.stage==='child'&&guidanceTopic&&(!guidanceChild||guidanceChild===(state.activeChildId||'primary'))&&<AgeGuidance childId={state.activeChildId||'primary'} topic={guidanceTopic}/>}
            <section className="tile chat-card">
              <h2>Здесь можно спросить и выдохнуть</h2>
              <ChatContext
                state={state}
                quota={quota}
                onProfile={() => setTab("profile")}
              />
              <ConversationControls
                state={state}
                save={async (s, n) => {
                  const ok = await save(s, n);
                  if (ok) {
                    setRetryRequest(null);
                    setDraft("");
                  }
                  return ok;
                }}
                busy={busy || chatBusy}
              />
              <div
                className="chat-log"
                ref={mountChatLog}
                role="log"
                aria-label="Переписка"
                aria-live="polite"
              >
                {!state.messages.length && (
                  <div className="bubble assistant">
                    <span>Мамин помощник</span>
                    <p>
                      Помогу обсудить сон, кормление, игры, уход, детский сад,
                      подготовку к школе и то, как вы сами себя чувствуете. Маме
                      и папе тоже нужна поддержка. Для советов по возрасту
                      заполните профиль. Диагнозы и назначения — к врачу.
                    </p>
                  </div>
                )}
                {state.messages.map((m) => (
                  <div key={m.id} className={`bubble ${m.role}`} style={m.role==='assistant' && m===state.messages[state.messages.length-1] ? {minHeight:answerMinHeight || undefined} : undefined}>
                    <span>{m.role === "user" ? "Вы" : "Мамин помощник"}</span>
                    <p>{m.text}</p>
                    {m.role === "assistant" && (
                      <>
                        <EvidencePassport message={m} />
                        <ReadAnswer text={m.text} />
                        <FavoriteButton
                          message={m}
                          state={state}
                          save={save}
                          busy={busy || chatBusy}
                        />
                        <AnswerFeedback message={m} />
                      </>
                    )}
                  </div>
                ))}
                {chatBusy && (
                  <div className="bubble assistant" ref={responseStart} style={{minHeight:answerMinHeight || undefined}}>
                    <span>Мамин помощник · ответ формируется</span>
                    <p>{partial || "Готовим ответ с учётом вашего профиля…"}</p>
                  </div>
                )}
              </div>
              {!chatBusy && retryRequest && (
                <Button
                  className="my-3"
                  variant="outline"
                  disabled={busy}
                  onClick={() => void send(retryRequest.question)}
                >
                  Повторить отправку
                </Button>
              )}
              <MemoryReview state={state} save={save} busy={busy} pendingOnly />
              <div className="flex items-end gap-2">
                <VoiceInput
                  disabled={busy || chatBusy}
                  onText={(text) =>
                    setDraft((current) => (current ? current + " " : "") + text)
                  }
                />
                <form
                  className="chat-form flex-1"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void send(draft);
                  }}
                >
                  <Textarea
                    value={draft}
                    maxLength={2000}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (
                        e.key === "Enter" &&
                        !e.shiftKey &&
                        !e.nativeEvent.isComposing
                      ) {
                        e.preventDefault();
                        void send(draft);
                      }
                    }}
                    placeholder="Напишите свой вопрос…"
                    aria-label="Ваш вопрос"
                  />
                  <Button
                    type="submit"
                    disabled={busy || chatBusy || !draft.trim()}
                    aria-label="Отправить"
                  >
                    <Send size={20} />
                  </Button>
                </form>
              </div>
              <p className="muted text-sm mt-3">
                Enter — отправить, Shift+Enter — новая строка. Ошибки сервиса не
                расходуют лимит.
              </p>
            </section>
          </TabsContent>
          <TabsContent value="advisor">
            {state.profile?.stage==='child'&&<AgeGuidance browse childId={state.activeChildId||'primary'}/>}
            <div className="section-title">
              <div>
                <h2>Важное — в своё время</h2>
                <p className="muted">
                  Карточки открываются к подходящему периоду
                </p>
              </div>
              <Rattle className="h-16 w-16" />
            </div>
            <p className="mb-5">
              Карточки соответствуют текущему возрасту ребёнка или сроку беременности.
            </p>
            {!state.profile && (
              <Button onClick={() => setTab("profile")}>
                Указать возраст или срок
              </Button>
            )}
            <div className="guide-grid">
              {due.map((m) => (
                <article key={m.id} className="tile bg-cream">
                  <span className="cap">
                    {m.age} {m.stage === "child" ? "мес." : "нед."}
                  </span>
                  <h3>{m.title}</h3>
                  <p>{m.text}</p>
                  <div className="flex flex-wrap gap-2 mt-4">
                    <Button
                      variant="outline"
                      disabled={busy}
                      onClick={() => void markEvent(m.id, "later")}
                    >
                      Отложить{" "}
                      {state.preferences.repeat === "week"
                        ? "на неделю"
                        : "на день"}
                    </Button>
                    <Button
                      variant="ghost"
                      disabled={busy}
                      onClick={() => void markEvent(m.id, "hidden")}
                    >
                      Скрыть
                    </Button>
                  </div>
                </article>
              ))}
            </div>
            {state.profile && due.length === 0 && (
              <div className="tile my-5">
                <h3>Новых карточек нет</h3>
                <p>
                  Новая тема появится в подходящем возрастном периоде.
                </p>
              </div>
            )}
            {Object.keys(state.events).length > 0 && (
              <>
                <h3 className="mt-8 mb-3">Отложенное и скрытое</h3>
                {Object.entries(state.events).map(([id, v]) => {
                  const m = milestones.find((item) => item.id === id);
                  return (
                    <div className="event-row" key={id}>
                      <span>
                        {m?.title ?? id}
                        <small>
                          {v.status === "hidden"
                            ? "Скрыто"
                            : `До ${new Date(v.until).toLocaleDateString("ru-RU")}`}
                        </small>
                      </span>

                    </div>
                  );
                })}
              </>
            )}
          </TabsContent>
          <TabsContent value="card">
            <section className="tile">
              <h2>Карта наблюдений</h2>
              <p className="muted">
                Только заметки, которые вы решили сохранить. Это не медицинская
                карта клиники и не диагнозы AI. Старые записи без отметки
                требуют вашей проверки.
              </p>
              <MemoryReview state={state} save={save} busy={busy} />
              {!state.medicalCard.length && !state.pendingMemory?.length && (
                <p className="my-4">
                  Расскажите в чате о событии — помощник предложит заметку.
                  Перед сохранением её можно исправить.
                </p>
              )}
            </section>
          </TabsContent>
          <TabsContent value="profile">
            <section className="tile profile-panel">
              <h2>Профиль ребёнка</h2>
              <p className="muted">
                У каждого ребёнка свои диалоги, советы и карта наблюдений.
              </p>
              <form onSubmit={submitProfile} className="mt-6 space-y-5">
                <p role="note" className="rounded-xl border p-4 text-sm">
                  {state.profile ? 'Профиль уже заполнен. Можно изменить только имя ребёнка.' : 'Заполнить профиль можно один раз. Внимательно проверьте сведения: после сохранения можно изменить только имя ребёнка.'}
                  {' '}Дата рождения, этап, кормление, сведения о сне и здоровье фиксируются. Возраст рассчитывается автоматически. Для другого своего ребёнка можно добавить отдельный профиль. При ошибке в данных обратитесь через «Предложить улучшение» в настройках.
                </p>
                <label className="form-field">
                  Имя ребёнка или домашнее имя
                  {profileDraft.stage === "pregnancy"
                    ? " · необязательно"
                    : " · обязательно"}
                  <Input
                    required={profileDraft.stage === "child"}
                    maxLength={60}
                    value={profileDraft.childName ?? ""}
                    onChange={(e) =>
                      setProfileDraft({
                        ...profileDraft,
                        childName: e.target.value,
                      })
                    }
                    placeholder="Например, Миша. Фамилия не нужна."
                  />
                </label>
                <fieldset disabled={!!state.profile || busy} className="space-y-5 disabled:opacity-70">
                <div className="form-grid">
                  <label className="form-field">
                    Кто вы
                    <Select
                      value={profileDraft.role}
                      onValueChange={(v) =>
                        setProfileDraft({
                          ...profileDraft,
                          role: v as Profile["role"],
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="mom">Мама</SelectItem>
                        <SelectItem value="dad">Папа</SelectItem>
                      </SelectContent>
                    </Select>
                  </label>
                  <label className="form-field">
                    Ваш этап
                    <Select
                      value={profileDraft.stage}
                      onValueChange={(v) =>
                        setProfileDraft({
                          ...profileDraft,
                          stage: v as Profile["stage"],
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pregnancy">
                          Ожидаем малыша
                        </SelectItem>
                        <SelectItem value="child">Ребёнок родился</SelectItem>
                      </SelectContent>
                    </Select>
                  </label>
                </div>
                {profileDraft.stage === "child" ? (
                  <>
                  <label className="form-field">
                    Дата рождения ребёнка
                    <Input
                      type="date"
                      required
                      max={today()}
                      value={profileDraft.birthDate}
                      onChange={(e) =>
                        setProfileDraft({
                          ...profileDraft,
                          birthDate: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label className="form-field">
                    Пол ребёнка · необязательно
                    <Select
                      value={profileDraft.childSex || "unknown"}
                      onValueChange={(v) =>
                        setProfileDraft({
                          ...profileDraft,
                          childSex: v as Profile["childSex"],
                        })
                      }
                    >
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="unknown">Не указывать</SelectItem>
                        <SelectItem value="female">Девочка</SelectItem>
                        <SelectItem value="male">Мальчик</SelectItem>
                      </SelectContent>
                    </Select>
                  </label>
                  </>
                ) : (
                  <div className="form-grid">
                    <label className="form-field">
                      Полных недель
                      <Input
                        type="number"
                        min={1}
                        max={42}
                        required
                        value={profileDraft.week}
                        onChange={(e) =>
                          setProfileDraft({
                            ...profileDraft,
                            week: Number(e.target.value),
                          })
                        }
                      />
                    </label>
                    <label className="form-field">
                      На какую дату указан срок
                      <Input
                        type="date"
                        max={today()}
                        required
                        value={profileDraft.weekDate}
                        onChange={(e) =>
                          setProfileDraft({
                            ...profileDraft,
                            weekDate: e.target.value,
                          })
                        }
                      />
                    </label>
                  </div>
                )}
                <p className="muted text-sm">
                  Возраст и срок обновляются автоматически. После рождения добавьте отдельный профиль ребёнка с датой рождения.
                </p>
                <label className="form-field">
                  Кормление · необязательно
                  <Select
                    value={profileDraft.feeding}
                    onValueChange={(v) =>
                      setProfileDraft({
                        ...profileDraft,
                        feeding: v as Profile["feeding"],
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {[
                        ["unknown", "Не указывать"],
                        ["breast", "Грудное"],
                        ["formula", "Смесь"],
                        ["mixed", "Смешанное"],
                        ["solids", "С прикормом"],
                      ].map(([v, t]) => (
                        <SelectItem key={v} value={v}>
                          {t}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </label>
                <label className="form-field">
                  Что учитывать о сне · необязательно
                  <Textarea
                    maxLength={300}
                    value={profileDraft.sleep}
                    onChange={(e) =>
                      setProfileDraft({
                        ...profileDraft,
                        sleep: e.target.value,
                      })
                    }
                    placeholder="Кратко, без личных документов"
                  />
                </label>
                <label className="form-field">
                  Подтверждённые особенности здоровья · необязательно
                  <Textarea
                    maxLength={500}
                    value={profileDraft.health}
                    onChange={(e) =>
                      setProfileDraft({
                        ...profileDraft,
                        health: e.target.value,
                      })
                    }
                    placeholder="Для теста используйте вымышленные данные"
                  />
                </label>
                <div className="flex items-start gap-3">
                  <Checkbox
                    id="health-confirm"
                    checked={profileDraft.healthConfirmed}
                    onCheckedChange={(v) =>
                      setProfileDraft({
                        ...profileDraft,
                        healthConfirmed: v === true,
                      })
                    }
                  />
                  <label htmlFor="health-confirm" className="text-sm">
                    Указанные особенности подтверждены специалистом. Демо не
                    использует их для медицинских назначений.
                  </label>
                </div>
                <p className="muted text-sm">
                  Помощник учитывает все темы, связанные с ребёнком и
                  родительством.
                </p>
                </fieldset>
                <Button type="submit" disabled={busy}>
                  {busy ? "Сохраняем…" : state.profile ? "Сохранить имя" : "Сохранить профиль один раз"}
                </Button>
              </form>
            </section>
          </TabsContent>
          <TabsContent value="settings">
            <div className="home-grid">
              <section className="tile">
                <h2>Напоминания</h2>
                <p className="muted mt-3">Утром — подсказка по возрасту, поздравление в день рождения или готовые занятия. Не больше двух уведомлений в день на всю семью. Возрастная подсказка открывает чат нужного ребёнка; одинаковые темы не повторяются. Повтор о занятиях не приходит после просмотра подборки.</p>
                <label className="form-field mt-4">Часовой пояс
                  <select value={state.preferences.timezone || 'Europe/Moscow'} disabled={busy} onChange={e=>void save({...state,preferences:{...state.preferences,timezone:e.target.value}})}>
                    {['Europe/Kaliningrad','Europe/Moscow','Europe/Samara','Asia/Yekaterinburg','Asia/Omsk','Asia/Krasnoyarsk','Asia/Irkutsk','Asia/Yakutsk','Asia/Vladivostok','Asia/Magadan','Asia/Kamchatka'].map(zone=><option key={zone} value={zone}>{zone.split('/')[1].replace(/_/g,' ')}</option>)}
                  </select>
                </label>
                <label className="form-field mt-4">Утреннее уведомление
                  <select value={state.preferences.morningHour ?? 9} disabled={busy} onChange={e=>void save({...state,preferences:{...state.preferences,morningHour:Number(e.target.value)}})}>
                    {[7,8,9,10,11,12].map(hour=><option key={hour} value={hour}>{hour}:00</option>)}
                  </select>
                </label>
                <label className="flex items-center gap-3 mt-4"><Checkbox checked={state.preferences.secondReminder || false} disabled={busy} onCheckedChange={value=>void save({...state,preferences:{...state.preferences,secondReminder:value===true}})}/>Ещё одно напоминание через 6 часов, если подборка не просмотрена</label>
                <div className="mt-6">
                  <Button
                    variant="outline"
                    disabled={busy || pushBusy}
                    onClick={() => void pushToggle(!state.preferences.push)}
                  >
                    {state.preferences.push
                      ? "Отключить push"
                      : "Включить push"}
                  </Button>
                  <p className="muted text-sm mt-3">
                    В уведомлении могут быть имя ребёнка и возрастная тема. Сведения о здоровье не включаются. Скрыть текст на экране блокировки можно в настройках уведомлений телефона.
                  </p>
                </div>
              </section>
              <section className="tile">
                <h2>Аккаунт и данные</h2>
                <AnswerFeedback />
                <p className="break-all">{user?.email}</p>
                {/^test-account-/.test(user.id) && (
                  <div className="rounded-xl bg-cream p-4 my-3">
                    <strong>Общий тестовый аккаунт</strong>
                    <p>
                      Используйте только вымышленные сведения: другие участники
                      с этим логином видят те же данные. Для личной переписки
                      создайте собственный аккаунт с отдельным паролем.
                    </p>
                    <Button asChild variant="outline">
                      <Link to="/account">Создать личный аккаунт</Link>
                    </Button>
                  </div>
                )}
                <p>
                  Профиль, переписка и карта наблюдений сохраняются в серверной
                  базе проекта. Оплата отключена. У мамы и папы отдельные
                  аккаунты.
                </p>
                <Link to="/privacy" className="text-primary underline">
                  Условия тестирования и данные
                </Link>
                <div className="mt-6">
                  <Button variant="outline" onClick={() => setDeleteOpen(true)}>
                    Удалить аккаунт и данные
                  </Button>
                </div>
              </section>
            </div>
          </TabsContent>
        </Tabs>
        <div className="cabinet-foot">
          <Link to="/">
            <ArrowLeft size={16} />
            На главную
          </Link>
          <a href="/mamin-pomoshchnik-instruction.pdf" target="_blank" rel="noreferrer">Инструкция — скачать PDF</a>
          <span>Информационный помощник для родителей</span>
        </div>
      </main>
      <Dialog
        open={deleteOpen}
        onOpenChange={(v) => {
          setDeleteOpen(v);
          if (!v) setDeletePassword("");
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Удалить аккаунт?</DialogTitle>
            <DialogDescription>
              Профиль, переписка и подписки на уведомления будут удалены из
              рабочей базы. Это действие нельзя отменить.
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              try {
                await api("delete", { password: deletePassword });
                setDeleteOpen(false);
                setDeletePassword("");
                setState(emptyState());
                setUser(null);
              } catch (err) {
                setError((err as Error).message);
                setDeleteOpen(false);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label className="form-field">
              Подтвердите паролем
              <Input
                type="password"
                required
                autoComplete="current-password"
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
              />
            </label>
            <div className="flex gap-3 mt-5">
              <Button type="submit" variant="destructive" disabled={busy}>
                Удалить навсегда
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => setDeleteOpen(false)}
              >
                Отмена
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

