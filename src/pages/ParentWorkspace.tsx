import { ruCount } from '@/lib/ru-count';
import QuickConveniences from '@/components/QuickConveniences';
import { AskDoctor } from '@/components/DoctorQuestions';
import { conversationList, openConversation } from "@/lib/conversations";
import { confirmAction } from "@/lib/confirm-action";
import SimpleMyDay from "@/components/SimpleMyDay";
import RoomChatWelcome, { RoomChatFeed } from "@/components/RoomChatWelcome";
import RoomChatMenu from "@/components/RoomChatMenu";
import RoomNavigation, { type RoomSection } from "@/components/RoomNavigation";
import RoomChatTools, { type RoomChatPanel } from "@/components/RoomChatTools";
import { Compass } from "lucide-react";
import { isRoomLocation, rememberRoom } from "@/lib/room-experience";
import { ApiError } from "@/lib/parent-api";
import CareTools from "@/components/CareTools";
import AgeGuidance from "@/components/AgeGuidance";
import GuideWelcome from "@/components/GuideWelcome";
import FirstAid from "@/components/FirstAid";
import Favorites, { FavoriteButton } from "@/components/Favorites";
import { familyList, switchChild, addChild } from "@/lib/family";
import { type CSSProperties, FormEvent, useCallback, useEffect, useRef, useState } from "react";
import ProductIdeas from "@/components/ProductIdeas";
import MilestoneMark, { PushMilestoneMark } from "@/components/MilestoneMark";
import { detectMilestones, milestoneFromSearch } from "@/lib/milestone-marks";
import ChatQuickCare from "@/components/ChatQuickCare";
import ChatMessageText from "@/components/ChatMessageText";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  UserRound,
  ArrowLeft,
  Send,
  LogOut,
  ChevronDown,
  Check,
  ArrowUp,
  Ellipsis,
} from "lucide-react";
import { Tabs, TabsContent } from "@/components/ui/tabs";
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
import { api, Session, Quota, BillingInfo, streamChat } from "@/lib/parent-api";
import { randomId } from "@/lib/id";
import { readChatDraft, writeChatDraft, clearChatDrafts } from "@/lib/chat-drafts";
import { localEmergencyNotice } from "@/lib/emergency-notice";
import {
  EvidencePassport,
  VoiceInput,
  ReadAnswer,
} from "@/components/ParentServices";

export default function ParentWorkspace({
  initialTab = "chat",
}: {
  initialTab?: string;
}) {
  const [state, setState] = useState<ParentState>(emptyState);
  const [revision, setRevision] = useState(0);
  const [user, setUser] = useState<Session["user"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionAttempt, setSessionAttempt] = useState(0);
  const location = useLocation();
  const roomScene = isRoomLocation(location.search, location.pathname);
  const navigate = useNavigate();
  const allowedTabs = [
    "home",
    "chat",
    "trackers",
    "more",
    "first-aid",
    "favorites",
    "advisor",
    "card",
    "profile",
    "settings",
  ];
  const requestedTab = new URLSearchParams(location.search).get("tab");
  const tab =
    requestedTab && allowedTabs.includes(requestedTab)
      ? requestedTab
      : initialTab;
  useEffect(() => {
    if (user?.id) void api("event", { page: tab }).catch(() => {});
  }, [tab, user?.id]);
  const tabNavigation = useRef<HTMLDivElement | null>(null);
  const previousTab = useRef(tab);
  const lastProfileTab = useRef("more");
  const detailParents = useRef<Record<string, string>>({});
  const careDrafts = useRef<
    Record<
      string,
      { note: string; value: string; sleepStart?: string; sleepEnd?: string }
    >
  >({});
  const messageDrafts = useRef<Record<string, string>>({});
  const profileDrafts = useRef<Record<string, Profile>>({});
  const profileTabs = [
    "more",
    "profile",
    "settings",
    "advisor",
    "card",
    "first-aid",
  ];
  const sectionTitles: Record<string, string> = {
    home: "Сегодня",
    chat: "Чат",
    trackers: "Записи",
    favorites: "Избранное",
    more: "Профиль",
    profile: "Профиль ребёнка",
    settings: "Настройки",
    advisor: "Советник",
    card: "Наблюдения и память",
    "first-aid": "Первая помощь",
  };
  const [chatRecovery, setChatRecovery] = useState(false);
  const draftKey = `${user?.id || "pending"}:${state.activeChildId || "primary"}:${state.conversationId || "legacy-active"}`;
  const scrollPositions = useRef<Record<string, number>>({});
  const [childPickerOpen, setChildPickerOpen] = useState(false);

  function setTab(next: string) {
    if (next === tab) {
      if (roomScene) window.scrollTo({ top: 0, behavior: "smooth" });
      else tabNavigation.current?.scrollIntoView({
        block: "start",
        behavior: "smooth",
      });
      return;
    }
    scrollPositions.current[tab] = window.scrollY;
    if (profileTabs.includes(next)) {
      lastProfileTab.current = next;
      if (next !== "more" && next !== tab) detailParents.current[next] = tab;
    }
    const params = new URLSearchParams(location.search);
    params.set("tab", next);
    navigate(
      { pathname: location.pathname, search: params.toString() },
      { state: { cabinetSection: true } },
    );
  }
  useEffect(() => {
    if (previousTab.current === tab) return;
    previousTab.current = tab;
    setError("");
    setNotice("");
    const frame = requestAnimationFrame(() =>
      window.scrollTo({
        top:
          scrollPositions.current[tab] ??
          (roomScene ? 0 : (tabNavigation.current?.getBoundingClientRect().top ?? 0) +
            window.scrollY -
            12),
        behavior: "instant",
      }),
    );
    return () => cancelAnimationFrame(frame);
  }, [tab, roomScene]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [chatBusy, setChatBusy] = useState(false);
  const [careVersion, setCareVersion] = useState<string>();
  useEffect(() => {
    let current = true;
    let request = 0;
    setCareVersion(undefined);
    const refresh = async () => {
      if (state.profile?.stage !== "child") return;
      const ticket = ++request;
      try {
        const result = await api<{ contextVersion: string }>("care-list", { childId: state.activeChildId || "primary" });
        if (current && ticket === request) setCareVersion(result.contextVersion);
      } catch { if (current && ticket === request) setCareVersion(undefined); }
    };
    void refresh();
    window.addEventListener("care-records-changed", refresh);
    const visible = () => { if (document.visibilityState === "visible") void refresh(); };
    document.addEventListener("visibilitychange", visible);
    return () => { current = false; window.removeEventListener("care-records-changed", refresh); document.removeEventListener("visibilitychange", visible); };
  }, [state.activeChildId, state.profile?.stage]);
  const [pushBusy, setPushBusy] = useState(false);
  const [quota, setQuota] = useState<Quota>();
  const [billing, setBilling] = useState<BillingInfo>();
  useEffect(() => {
    const update = (event: Event) => setQuota((event as CustomEvent<Quota>).detail);
    window.addEventListener("mh-quota-updated", update);
    return () => window.removeEventListener("mh-quota-updated", update);
  }, []);
  const [birthday, setBirthday] = useState<Session["birthday"]>();
  const guidanceTopic = new URLSearchParams(location.search).get("topic");
  const guidanceChild = new URLSearchParams(location.search).get("child");
  const [partial, setPartial] = useState("");
  const [urgentAnswer, setUrgentAnswer] = useState("");
  const [roomPanel, setRoomPanel] = useState<RoomChatPanel>(null);
  useEffect(() => {
    if (loading || !user || !roomScene) return;
    const params = new URLSearchParams(location.search);
    const panel = params.get("panel");
    if (panel !== "children" && panel !== "options") return;
    if (panel === "children") {
      if (state.profile) setChildPickerOpen(true);
      else params.set("tab", "profile");
    } else setRoomPanel("options");
    params.delete("panel");
    navigate({ pathname: location.pathname, search: params.toString() }, { replace: true });
  }, [loading, user, roomScene, state.profile, location.pathname, location.search, navigate]);
  useEffect(() => setRoomPanel(null), [tab]);
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
  const composer = useRef<HTMLDivElement | null>(null);
  const [composerHeight, setComposerHeight] = useState(80);
  const responseAnchored = useRef(false);
  const [answerMinHeight, setAnswerMinHeight] = useState(0);
  const mountChatLog = useCallback((node: HTMLDivElement | null) => {
    chatLog.current = node;
    if (node) node.scrollTop = node.scrollHeight;
  }, []);
  const [clock, setClock] = useState(Date.now());
  useEffect(() => {
    const node = composer.current;
    if (tab !== "chat" || !node) return;
    const resize = new ResizeObserver(() => setComposerHeight(node.getBoundingClientRect().height));
    resize.observe(node);
    return () => resize.disconnect();
  }, [tab, loading]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api<Session>("session")
      .then(async (s) => {
        rememberRoom();
        if (s.user.emailVerificationRequired) {
          navigate("/account?mode=email-await&next=" + encodeURIComponent(window.location.pathname + window.location.search), { replace: true });
          return;
        }
        const search = new URLSearchParams(window.location.search);
        const requestedChild = search.has("mark")
          ? milestoneFromSearch(window.location.search, familyList(s.state).map(c => c.id))?.childId
          : search.get("child");
        if (
          requestedChild &&
          familyList(s.state).some((child) => child.id === requestedChild) &&
          requestedChild !== (s.state.activeChildId || "primary")
        ) {
          const next = switchChild(s.state, requestedChild);
          const saved = await api<{ revision: number }>("save", {
            state: next,
            revision: s.revision,
          });
          s = { ...s, state: next, revision: saved.revision };
        }
        if (active) {
          setUser(s.user);
          setQuota(s.quota);
          setBilling(s.billing);
          setBirthday(s.birthday);
          setState(s.state);
          setRevision(s.revision);
          setProfileDraft(s.state.profile ?? defaultProfile());
        }
      })
      .catch((e) => {
        if (active && isRoomLocation(window.location.search) && e instanceof ApiError && e.status === 401) {
          navigate("/account?mode=login&next=" + encodeURIComponent(location.pathname + window.location.search), { replace: true });
          return;
        }
        // A guest (401) gets the sign-in card, not an error.
        if (active && !(e instanceof ApiError && e.status === 401)) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [sessionAttempt, navigate, location.pathname]);
  useEffect(() => {
    setDraft(messageDrafts.current[draftKey] ?? (user ? readChatDraft(draftKey) : ""));
    setUrgentAnswer("");
  }, [draftKey, user]);
  useEffect(() => {
    if (tab !== "chat" || loading) return;
    const log = chatLog.current;
    const frame = requestAnimationFrame(() => {
      if (log) {
        const answers = log.querySelectorAll<HTMLElement>(".bubble.assistant");
        const lastAnswer = answers[answers.length - 1];
        log.scrollTop = lastAnswer
          ? lastAnswer.getBoundingClientRect().top - log.getBoundingClientRect().top + log.scrollTop - (roomScene ? 16 : 12)
          : log.scrollHeight;
        if (!roomScene && log.querySelector(".bubble.user"))
          log.scrollIntoView({ block: "start", behavior: "instant" });
      }
    });
    return () => {
      cancelAnimationFrame(frame);
    };
  }, [loading, draftKey, tab, urgentAnswer, roomScene]);
  useEffect(() => {
    if (tab !== "chat" || !chatBusy || responseAnchored.current) return;
    const frame = requestAnimationFrame(() => {
      const log = chatLog.current;
      const answer = responseStart.current;
      if (!log || !answer) return;
      // Anchor once to the start; streaming must not override manual reading.
      log.scrollTop +=
        answer.getBoundingClientRect().top -
        log.getBoundingClientRect().top -
        16;
      if (!roomScene) log.scrollIntoView({ block: "start", behavior: "instant" });
      responseAnchored.current = true;
    });
    return () => cancelAnimationFrame(frame);
  }, [tab, chatBusy, roomScene]);
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
    if (
      !adding &&
      (next.activeChildId || "primary") === (state.activeChildId || "primary")
    )
      return true;
    profileDrafts.current[state.activeChildId || "primary"] = profileDraft;
    if (
      await save(
        next,
        adding ? "Заполните профиль ребёнка" : "Профиль переключён",
      )
    ) {
      setProfileDraft(
        profileDrafts.current[next.activeChildId || "primary"] ||
          next.profile ||
          defaultProfile(),
      );
      setRetryRequest(null);
      setPartial("");
      if (adding || !next.profile) setTab("profile");
      return true;
    }
    return false;
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
    lock.current = true;
    setBusy(true);
    setChatBusy(true);
    responseAnchored.current = false;
    setAnswerMinHeight(Math.max(0, (chatLog.current?.clientHeight || 0) - 32));
    setError("");
    setNotice("");
    // Show the fixed emergency handoff before waiting for network, profile or quota.
    setChatRecovery(false);
    setUrgentAnswer(localEmergencyNotice(q));
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
    messageDrafts.current[draftKey] = "";
    writeChatDraft(draftKey, "");
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
      setUrgentAnswer(result.transientAnswer ? result.answer : "");
      setRevision(result.revision);
      if (result.quota) setQuota(result.quota);
      setRetryRequest(null);
      setPartial("");
      setDraft("");
      messageDrafts.current[draftKey] = "";
      writeChatDraft(draftKey, "");
      setNotice(
        result.sleepContext?.records
          ? `Ответ подготовлен с записями сна: ${result.sleepContext.childName}, последние ${result.sleepContext.days} дней (${ruCount(result.sleepContext.records,"эпизод","эпизода","эпизодов")}).`
          : result.transientAnswer ? "История заполнена. Срочная помощь показана ниже; прежняя переписка сохранена." : "Переписка сохранена",
      );
    } catch (e) {
      const detail = (e as Error).message;
      const needsRecovery = (e instanceof ApiError && e.status === 429) || /истори.*(длин|заполн)|history.*(long|full)/i.test(detail);
      setChatRecovery(needsRecovery);
      setPartial("");
      setDraft((current) => {
        const next = current || q;
        messageDrafts.current[draftKey] = next;
        writeChatDraft(draftKey, next);
        return next;
      });
      setError(
        needsRecovery ? detail : "Ответ не получен. Текст оставлен на экране и в поле ввода — можно отправить повторно. " +
          detail,
      );
    } finally {
      lock.current = false;
      setBusy(false);
      setChatBusy(false);
      setAnswerMinHeight(0);
    }
  }
  async function submitProfile(e: FormEvent) {
    e.preventDefault();
    const p = state.profile
      ? { ...state.profile, childName: profileDraft.childName?.trim() }
      : profileDraft;
    if (p.stage === "child" && !p.childName?.trim()) {
      setError("Укажите имя ребёнка или домашнее имя. Фамилия не нужна.");
      return;
    }
    if (
      p.stage === "child" &&
      (!p.birthDate || p.birthDate > today() || ageValue(p) > 84)
    ) {
      setError(
        "Поддерживаются дети от рождения до 84 полных месяцев включительно. Проверьте дату рождения.",
      );
      return;
    }
    if (p.health && !p.healthConfirmed) {
      setError("Добавляйте только особенности, подтверждённые специалистом.");
      return;
    }
    if (
      !state.profile &&
      !await confirmAction(
        "Проверьте сведения. Профиль ребёнка заполняется один раз: после сохранения можно изменить только имя. Дату рождения, этап, кормление и другие поля изменить самостоятельно нельзя. Продолжить?",
      )
    )
      return;
    if (await save(stateWithProfile(state, p))) setTab("chat");
  }
  async function logout() {
    setBusy(true);
    try {
      await api("logout");
      if (user) clearChatDrafts(user.id);
      setRetryRequest(null);
      setPartial("");
      setDraft("");
      messageDrafts.current[draftKey] = "";
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
    setError("");
    setNotice(
      "Разрешите уведомления в запросе браузера. Если запрос не появился, проверьте настройки разрешений сайта.",
    );
    const timeout = async <T,>(promise: Promise<T>): Promise<T> => {
      let timer: ReturnType<typeof setTimeout>;
      try {
        return await Promise.race([
          promise,
          new Promise<T>((_, reject) => {
            timer = setTimeout(
              () =>
                reject(
                  new Error(
                    "Браузер не завершил подключение уведомлений. Откройте сайт в Chrome, Edge или Safari и разрешите уведомления в настройках сайта.",
                  ),
                ),
              20000,
            );
          }),
        ]);
      } finally {
        clearTimeout(timer!);
      }
    };
    try {
      // Request inside the click gesture, before any network await.
      const permission = await timeout(Notification.requestPermission());
      if (permission !== "granted") {
        setError(
          "Уведомления не разрешены. Изменить это можно в настройках браузера.",
        );
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
        (await timeout(
          registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: bytes,
          }),
        ));
      await api("subscribe", { subscription: subscription.toJSON() });
      await save({
        ...state,
        preferences: { ...state.preferences, push: true },
      });
    } catch (e) {
      const message = (e as Error).message || "";
      setError(
        /push service|registration failed/i.test(message)
          ? "Браузер не смог подключиться к сервису уведомлений. Проверьте интернет и попробуйте ещё раз."
          : message || "Не удалось включить уведомления. Попробуйте ещё раз.",
      );
    } finally {
      setPushBusy(false);
      setNotice("");
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
          <h1>{error ? "Не удалось открыть кабинет" : "Ваш личный кабинет"}</h1>
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
            {error && <Button onClick={() => setSessionAttempt(value => value + 1)}>Повторить загрузку</Button>}
            <Button asChild>
              <Link
                to={
                  "/account?mode=login&next=" +
                  encodeURIComponent(location.pathname + location.search)
                }
              >
                Регистрация и вход
              </Link>
            </Button>
          </div>
          <Link className="standalone-link" to="/first-aid">Срочная помощь · 112</Link>
        </div>
      </main>
    );
  const chatSettings = <>
<div className={state.profile ? "chat-tools compact" : "chat-tools"}>
                <ChatContext
                  state={state}
                  quota={quota}
                  onProfile={() => { setRoomPanel(null); if (state.profile) setChildPickerOpen(true); else setTab("profile"); }}
                />
                <ProductIdeas />
              </div>
              <ConversationControls
                state={state}
                save={async (s, n) => {
                  const ok = await save(s, n);
                  if (ok) {
                    setRetryRequest(null);
                  }
                  return ok;
                }}
                busy={busy || chatBusy}
              />
              {roomScene && <div className="room-account-tools">
                <Link to="/">На главную</Link>
                <a href={`${import.meta.env.BASE_URL}mamin-pomoshchnik-instruction.pdf`} target="_blank" rel="noreferrer">Инструкция — скачать PDF</a>
                <span>Информационный помощник для родителей</span>
              </div>}
  </>;
  return (
    <div
      style={{ "--room-composer-height": `${composerHeight}px` } as CSSProperties}
      className={`parent-workspace ${tab === "trackers" ? "with-tracker-dock" : ""} ${tab === "chat" ? "chat-workspace" : ""}`}
    >
      <a className="skip-link" href="#main-content">К основному содержимому</a>
      {!roomScene && <header className="cabinet-header">
        <div className="brand-theme">
          <Link to="/" className="flex items-center gap-2">
            <img src="/logo-mark.png?v=3" alt="" width={48} height={48} className="site-logo h-12" />
            <strong>Мамин помощник</strong>
          </Link>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/billing" aria-label="Доступ и оплата" className="rounded-full border px-3 py-2 text-xs text-primary">{billing?.mode === "paid" ? "Подписка" : "Доступ"}</Link>
          <Button
            variant="ghost"
            onClick={() => void logout()}
            disabled={busy}
            aria-label="Выйти"
          >
            <LogOut size={18} />
          </Button>
        </div>
      </header>}
      <main id="main-content" tabIndex={-1} className="cabinet-main">
        {roomScene && <RoomChatMenu
          profile={state.profile} disabled={busy || chatBusy}
          onProfile={() => state.profile ? setChildPickerOpen(true) : setTab("profile")} onOptions={() => setRoomPanel("options")}
          onSettings={() => setTab("settings")} onLogout={() => void logout()}
        />}
        <QuickConveniences key={"quick-" + (state.activeChildId || "primary")} state={state} showLatest={tab === "home" || tab === "chat"} onRecords={() => setTab("trackers")} />
        <PushMilestoneMark key={"mark-" + (state.activeChildId || "primary")} state={state} search={location.search} />
        {!roomScene && <Link className="standalone-link" to="/first-aid">Срочная помощь · 112</Link>}
        {roomScene ? <h1 className={tab === "chat" ? "sr-only" : "room-section-title"}>{sectionTitles[tab] || "Ваш кабинет"}</h1> : <div className="cabinet-greeting">
          <div>
            <span className="cap">
              {state.profile?.role === "dad"
                ? "Папа, вы тоже важны"
                : "Забота о малыше начинается с заботы о вас"}
            </span>
            <h1>{sectionTitles[tab] || "Ваш кабинет"}</h1>
            {tab !== "chat" && <p className="muted mt-2">{contextLabel(state.profile)}</p>}
          </div>
          {tab === "chat" ? <Link className="room-replay" to="/?intro=1"><Compass size={17} />Знакомство</Link> : <HeartCloud className="h-24 w-24 hidden sm:block" />}
        </div>}
        {!roomScene && <div className={tab === "chat" ? "chat-daily-actions" : "hidden"}>
          <ChatQuickCare key={state.activeChildId || "primary"} state={state} onTrackers={() => setTab("trackers")} onProfile={() => setChildPickerOpen(true)} profileBusy={busy || chatBusy} />
        </div>}
        {!roomScene && (tab !== "chat" || state.profile?.stage !== "child") && <Button
          className="child-picker"
          aria-label={`Выбрать ребёнка: ${contextLabel(state.profile)}`}
          variant="outline"
          disabled={busy || chatBusy}
          onClick={() => setChildPickerOpen(true)}
        >
          <span className="child-avatar">
            <UserRound size={20} />
          </span>
          <span>
            <small>{tab === "chat" && state.profile ? contextLabel(state.profile).split(" · ").slice(1).join(" · ") : "Сейчас выбран"}</small>
            <strong>
              {state.profile?.childName ||
                (state.profile?.stage === "pregnancy"
                  ? "Ожидание малыша"
                  : "Профиль ребёнка")}
            </strong>
          </span>
          <ChevronDown size={18} />
        </Button>}
        <Dialog open={childPickerOpen} onOpenChange={setChildPickerOpen}>
          <DialogContent className="ios-sheet" onCloseAutoFocus={event => {
            if (!roomScene || document.querySelector('[role="dialog"][data-state="open"]')) return;
            const notch = document.querySelector<HTMLElement>(".room-chat-notch");
            if (notch) { event.preventDefault(); notch.focus(); }
          }}>
            <DialogHeader>
              <DialogTitle>Ваши дети</DialogTitle>
              <DialogDescription>
                Выберите, для кого показать занятия, чат и записи.
              </DialogDescription>
            </DialogHeader>
            <div className="ios-list">
              {familyList(state).map((child, index) => (
                <Button
                  key={child.id}
                  variant="ghost"
                  disabled={busy || chatBusy}
                  onClick={async () => {
                    if (await changeChild(switchChild(state, child.id)))
                      setChildPickerOpen(false);
                  }}
                >
                  <span>
                    {child.data.profile?.childName ||
                      (child.data.profile?.stage === "pregnancy"
                        ? "Ожидание малыша"
                        : `Ребёнок ${index + 1}`)}
                  </span>
                  {child.id === (state.activeChildId || "primary") && (
                    <Check size={20} />
                  )}
                </Button>
              ))}
            </div>
            <Button
              disabled={
                busy ||
                chatBusy ||
                familyList(state).length >= 10 ||
                !state.profile
              }
              onClick={async () => {
                if (await changeChild(addChild(state), true))
                  setChildPickerOpen(false);
              }}
            >
              Добавить ребёнка
            </Button>
          </DialogContent>
        </Dialog>
        {tab !== "chat" && !!birthday?.children.length && (
          <section className="tile birthday-card" role="status">
            <h2>С днём рождения!</h2>
            <p>
              {birthday.children.map((c) => c.name).join(", ")} — поздравляем
              вашу семью! Вспомните вместе любимое событие года и придумайте
              маленькую праздничную традицию.
            </p>
            {birthday.giftPerChild > 0 && (
              <p>
                Подарок: по 5 дополнительных AI-ответов за каждого именинника.
                Подарочных ответов осталось:{" "}
                {quota?.bonusRemaining ?? birthday.giftRemaining}.
              </p>
            )}
          </section>
        )}
        <Tabs
          className="workspace-tabs"
          value={tab}
          onValueChange={(v) => {
            setTab(v);
            setError("");
            setNotice("");
          }}
        >
          <div ref={tabNavigation} className="cabinet-navigation">
            {!["home", "chat", "trackers", "favorites", "more"].includes(
              tab,
            ) && (
              <Button
                type="button"
                variant="ghost"
                className="mb-2"
                onClick={() => location.state?.cabinetSection ? navigate(-1) : setTab(detailParents.current[tab] || "more")}
              >
                <ArrowLeft size={17} />
                Назад
              </Button>
            )}
            <RoomNavigation active={(profileTabs.includes(tab) ? "more" : tab) as RoomSection}
              onNavigate={id => setTab(id === "more" && !profileTabs.includes(tab) ? lastProfileTab.current : id)} />
          </div>
          {error && tab !== "chat" && (
            <p role="alert" className="form-error my-4">
              {error}
            </p>
          )}
          {notice && (
            <p role="status" className="save-notice">
              {notice}
            </p>
          )}
          <TabsContent
            forceMount
            value="home"
            className="workspace-pane data-[state=inactive]:hidden"
          >
            <SimpleMyDay
              active={tab === "home"}
              onNavigate={setTab}
              state={state}
              onProfile={() => setTab("profile")}
            />
          </TabsContent>
          <TabsContent
            forceMount
            value="trackers"
            className="workspace-pane data-[state=inactive]:hidden"
          >
            {state.profile ? (
              <CareTools
                key={state.activeChildId || "primary"}
                active={tab === "trackers"}
                drafts={careDrafts.current}
                state={state}
                onMood={() => {}}
                expanded
              />
            ) : (
              <Button onClick={() => setTab("profile")}>
                Заполнить профиль
              </Button>
            )}
          </TabsContent>
          <TabsContent value="more">
            <section className="tile">
              <h2 className={roomScene ? "sr-only" : undefined}>Профиль</h2>
              <p className="muted">Дети, настройки и полезные материалы</p>
              <Link className="standalone-link" to="/guide">Короткие инструкции и инструмент дневника</Link>
              <div className="workspace-more ios-list">
                {[
                  ["profile", "Профили детей"],
                  ["advisor", "Советник"],
                  ["card", "Наблюдения и память"],
                  ["first-aid", "Первая помощь"],
                  ["settings", "Настройки и уведомления"],
                ].map(([id, label]) => (
                  <Button key={id} variant="ghost" onClick={() => setTab(id)}>
                    <span>{label}</span>
                    <ChevronDown className="-rotate-90" size={18} />
                  </Button>
                ))}
              </div>
            </section>
            <details className="tile mt-4">
              <summary>Как пользоваться сайтом</summary>
              <GuideWelcome key={user.id} />
            </details>
          </TabsContent>
          <TabsContent value="first-aid">
            <FirstAid />
          </TabsContent>
          <TabsContent
            forceMount
            value="favorites"
            className="workspace-pane data-[state=inactive]:hidden"
          >
            <Favorites state={state} busy={busy || chatBusy} save={save} />
          </TabsContent>
          <TabsContent
            forceMount
            value="chat"
            className="workspace-pane data-[state=inactive]:hidden"
          >
            {!roomScene && state.profile?.stage === "child" &&
              guidanceTopic &&
              (!guidanceChild ||
                guidanceChild === (state.activeChildId || "primary")) && (
                <AgeGuidance
                  childId={state.activeChildId || "primary"}
                  topic={guidanceTopic}
                />
              )}
            <section className="tile chat-card" style={{ paddingBottom: composerHeight + 24 }}>
              <h2 className="sr-only">Чат с помощником</h2>
              <RoomChatFeed enabled={roomScene} empty={!state.messages.length} scrollRef={mountChatLog}>
              {!roomScene && chatSettings}
              {roomScene && state.profile?.stage === "child" && guidanceTopic &&
                (!guidanceChild || guidanceChild === (state.activeChildId || "primary")) &&
                <AgeGuidance childId={state.activeChildId || "primary"} topic={guidanceTopic} />}
              <div
                className="chat-log"
                ref={roomScene ? undefined : mountChatLog}
                role="log"
                aria-label="Переписка"
                aria-live="polite"
                tabIndex={0}
              >
                {roomScene && <RoomChatWelcome hasProfile={!!state.profile} compact={state.messages.length > 0} />}
                {!state.messages.length && !roomScene && (
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
                {state.messages.map((m, messageIndex) => (
                  <div
                    key={m.id}
                    className={`bubble ${m.role}`}
                    style={
                      m.role === "assistant" &&
                      m === state.messages[state.messages.length - 1]
                        ? { minHeight: answerMinHeight || undefined }
                        : undefined
                    }
                  >
                    <span className={roomScene ? "room-message-author" : undefined}>{m.role === "user" ? "Вы" : "Мамин помощник"}</span>
                    <p>{m.role === "assistant" ? <ChatMessageText text={m.text} /> : m.text}</p>
                    <AskDoctor key={(state.activeChildId || "primary") + m.id} childId={state.activeChildId || "primary"} text={m.role === "user" ? m.text : [...state.messages.slice(0,messageIndex)].reverse().find(message => message.role === "user")?.text || ""} disabled={busy || chatBusy} />
                    {m.role === "assistant" && messageIndex === state.messages.length - 1 && state.profile?.stage === "child" && state.messages[messageIndex - 1]?.role === "user" && detectMilestones(state.messages[messageIndex - 1].text).map(skill => <MilestoneMark key={(state.activeChildId || "primary") + m.id + skill} state={state} skill={skill} />)}
                    {m.role === "assistant" && m.careVersion && careVersion && m.careVersion !== careVersion && <p className="text-sm muted" role="note">Дневник обновлён после этого ответа.</p>}
                    {m.role === "assistant" && (roomScene ? <details className="room-answer-actions">
                      <summary><Ellipsis size={18} /><span>Действия с ответом</span><ChevronDown size={14} /></summary>
                      <div>                        <EvidencePassport message={m} />
                        <ReadAnswer text={m.text} />
                        <FavoriteButton
                          message={m}
                          state={state}
                          save={save}
                          busy={busy || chatBusy}
                        />
                        <AnswerFeedback message={m} />
</div>
                    </details> : <>                        <EvidencePassport message={m} />
                        <ReadAnswer text={m.text} />
                        <FavoriteButton
                          message={m}
                          state={state}
                          save={save}
                          busy={busy || chatBusy}
                        />
                        <AnswerFeedback message={m} />
</>)}
                  </div>
                ))}
                {urgentAnswer && <section className="bubble assistant" role="alert"><strong>Срочная помощь</strong><p><ChatMessageText text={urgentAnswer} /></p><a href="tel:112">Позвонить 112</a></section>}
                {chatBusy && (
                  <div
                    className="bubble assistant"
                    ref={responseStart}
                    style={{ minHeight: answerMinHeight || undefined }}
                  >
                    <span>Мамин помощник · ответ формируется</span>
                    <p>{partial || "Готовим ответ с учётом вашего профиля…"}</p>
                  </div>
                )}
              </div>
              {!chatBusy && retryRequest && !chatRecovery && (
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
              </RoomChatFeed>
            </section>
              {roomScene && <ChatQuickCare inline key={state.activeChildId || "primary"} state={state} onTrackers={() => setTab("trackers")} profileBusy={busy || chatBusy} />}
              <div ref={composer} className="chat-composer" role="region" aria-label="Написать вопрос">
                {error && <p id="chat-request-error" role="alert" className="form-error chat-request-error">{error}{chatRecovery && <span className="chat-recovery-actions"><Link to="/data-rights">Написать владельцу</Link><Button type="button" variant="outline" disabled={busy || chatBusy || conversationList(state).length >= 21} onClick={async () => {
                  const next = openConversation(state, { title: "Новый чат" });
                  if (next === state) return;
                  const nextKey = `${user?.id || "pending"}:${next.activeChildId || "primary"}:${next.conversationId}`;
                  messageDrafts.current[nextKey] = draft;
                  writeChatDraft(nextKey, draft);
                  if (await save(next, "Новый чат открыт. Черновик сохранён.")) {
                    setRetryRequest(null); setPartial(""); setUrgentAnswer(""); setChatRecovery(false);
                  }
                }}>Новый чат</Button></span>}</p>}
                <VoiceInput
                  disabled={busy || chatBusy}
                  onText={(text) =>
                    setDraft((current) => {
                      const next = (current ? current + " " : "") + text;
                      messageDrafts.current[draftKey] = next;
                      writeChatDraft(draftKey, next);
                      return next;
                    })
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
                    onChange={(e) => {
                      setDraft(e.target.value);
                      messageDrafts.current[draftKey] = e.target.value;
                      writeChatDraft(draftKey, e.target.value);
                    }}
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
                    placeholder="Ваш вопрос…"
                    aria-label="Ваш вопрос"
                    aria-describedby={error ? "chat-request-error" : undefined}
                  />
                  <Button
                    type="submit"
                    disabled={busy || chatBusy || !draft.trim()}
                    aria-label="Отправить"
                  >
                    {roomScene ? <ArrowUp size={22} /> : <Send size={20} />}
                  </Button>
                </form>
                <Link className="chat-emergency-link" to="/first-aid">Срочная помощь · 112</Link>
              </div>
          </TabsContent>
          <TabsContent value="advisor">
            {state.profile?.stage === "child" && (
              <AgeGuidance browse childId={state.activeChildId || "primary"} />
            )}
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
              Карточки соответствуют текущему возрасту ребёнка или сроку
              беременности.
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
                <p>Новая тема появится в подходящем возрастном периоде.</p>
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
          <TabsContent
            forceMount
            value="profile"
            className="workspace-pane data-[state=inactive]:hidden"
          >
            <section className="tile profile-panel">
              <h2>Профиль ребёнка</h2>
              <p className="muted">
                У каждого ребёнка свои диалоги, советы и карта наблюдений.
              </p>
              <form onSubmit={submitProfile} className="mt-6 space-y-5">
                <p role="note" className="rounded-xl border p-4 text-sm">
                  {state.profile
                    ? "Профиль уже заполнен. Можно изменить только имя ребёнка."
                    : "Заполнить профиль можно один раз. Внимательно проверьте сведения: после сохранения можно изменить только имя ребёнка."}{" "}
                  Дата рождения, этап, кормление, сведения о сне и здоровье
                  фиксируются. Возраст рассчитывается автоматически. Для другого
                  своего ребёнка можно добавить отдельный профиль. При ошибке в
                  данных откройте <Link to="/data-rights">«Данные и обращения»</Link> и выберите «Исправить ошибку в данных».
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
                <fieldset
                  disabled={!!state.profile || busy}
                  className="space-y-5 disabled:opacity-70"
                >
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
                        <SelectTrigger aria-label="Кто вы">
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
                        <SelectTrigger aria-label="Этап">
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
                      <label htmlFor="profile-birth-date" className="form-field">
                        Дата рождения ребёнка
                        <Input
                          id="profile-birth-date"
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
                          <SelectTrigger aria-label="Пол">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="unknown">
                              Не указывать
                            </SelectItem>
                            <SelectItem value="female">Девочка</SelectItem>
                            <SelectItem value="male">Мальчик</SelectItem>
                          </SelectContent>
                        </Select>
                      </label>
                    </>
                  ) : (
                    <div className="form-grid">
                      <label htmlFor="profile-pregnancy-week" className="form-field">
                        Полных недель
                        <Input
                          id="profile-pregnancy-week"
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
                      <label htmlFor="profile-pregnancy-week-date" className="form-field">
                        На какую дату указан срок
                        <Input
                          id="profile-pregnancy-week-date"
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
                    Возраст и срок обновляются автоматически. После рождения
                    добавьте отдельный профиль ребёнка с датой рождения.
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
                      <SelectTrigger aria-label="Кормление">
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
                      placeholder="Только сведения, подтверждённые специалистом"
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
                      По моим сведениям, указанные особенности подтверждены
                      специалистом. Помощник не назначает лечение.
                    </label>
                  </div>
                  <p className="muted text-sm">
                    Помощник учитывает все темы, связанные с ребёнком и
                    родительством.
                  </p>
                </fieldset>
                <Button type="submit" disabled={busy}>
                  {busy
                    ? "Сохраняем…"
                    : state.profile
                      ? "Сохранить имя"
                      : "Сохранить профиль один раз"}
                </Button>
              </form>
            </section>
          </TabsContent>
          <TabsContent value="settings">
            <div className="home-grid">
              <section className="tile">
                <h2>Напоминания</h2>
                <p className="muted mt-3">
                  Утром — подсказка по возрасту, поздравление в день рождения
                  или готовые занятия. Не больше двух уведомлений в день на всю
                  семью. Возрастная подсказка открывает чат нужного ребёнка;
                  одинаковые темы не повторяются. Повтор о занятиях не приходит
                  после просмотра подборки.
                </p>
                <label className="form-field mt-4">
                  Часовой пояс
                  <select
                    aria-label="Часовой пояс"
                    value={state.preferences.timezone || "Europe/Moscow"}
                    disabled={busy}
                    onChange={(e) =>
                      void save({
                        ...state,
                        preferences: {
                          ...state.preferences,
                          timezone: e.target.value,
                        },
                      })
                    }
                  >
                    {[
                      "Europe/Kaliningrad",
                      "Europe/Moscow",
                      "Europe/Samara",
                      "Asia/Yekaterinburg",
                      "Asia/Omsk",
                      "Asia/Krasnoyarsk",
                      "Asia/Irkutsk",
                      "Asia/Yakutsk",
                      "Asia/Vladivostok",
                      "Asia/Magadan",
                      "Asia/Kamchatka",
                    ].map((zone) => (
                      <option key={zone} value={zone}>
                        {zone.split("/")[1].replace(/_/g, " ")}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="form-field mt-4">
                  Утреннее уведомление
                  <select
                    aria-label="Утреннее уведомление"
                    value={state.preferences.morningHour ?? 9}
                    disabled={busy}
                    onChange={(e) =>
                      void save({
                        ...state,
                        preferences: {
                          ...state.preferences,
                          morningHour: Number(e.target.value),
                        },
                      })
                    }
                  >
                    {[7, 8, 9, 10, 11, 12].map((hour) => (
                      <option key={hour} value={hour}>
                        {hour}:00
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex items-center gap-3 mt-4">
                  <Checkbox
                    checked={state.preferences.secondReminder || false}
                    disabled={busy}
                    onCheckedChange={(value) =>
                      void save({
                        ...state,
                        preferences: {
                          ...state.preferences,
                          secondReminder: value === true,
                        },
                      })
                    }
                  />
                  Ещё одно напоминание через 6 часов, если подборка не
                  просмотрена
                </label>
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
                    В уведомлении — короткая подсказка без имени, даты рождения
                    и сведений о здоровье. Нужный профиль откроется внутри сайта.
                    Скрыть текст на экране блокировки можно в настройках телефона.
                  </p>
                </div>
              </section>
              <section className="tile">
                <h2>Аккаунт и данные</h2>
                <AnswerFeedback />
                <p className="break-all">{user?.email}</p>
                {/^test-account-/.test(user.id) && (
                  <div className="rounded-xl bg-cream p-4 my-3">
                    <strong>Общий аккаунт</strong>
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
                  базе проекта. У мамы и папы отдельные
                  аккаунты.
                </p>
                <Link to="/privacy" className="standalone-link">
                  Обработка персональных данных
                </Link>
                <div className="mt-4 flex flex-wrap gap-3"><Button asChild variant="outline"><Link to="/billing">Доступ и оплата</Link></Button><Button asChild variant="outline"><Link to="/data-rights">Данные и обращения</Link></Button></div>
                <div className="mt-6">
                  <Button asChild variant="outline" className="mb-3">
                    <Link to="/account?mode=security">Пароль и безопасность</Link>
                  </Button>
                </div>
                <div className="mt-3">
                  <Button variant="outline" onClick={() => setDeleteOpen(true)}>
                    Удалить аккаунт и данные
                  </Button>
                </div>
              </section>
            </div>
          </TabsContent>
        </Tabs>
        {roomScene && <RoomChatTools panel={roomPanel} onPanelChange={setRoomPanel} quickCare={
          <ChatQuickCare key={state.activeChildId || "primary"} state={state} onTrackers={() => { setRoomPanel(null); setTab("trackers"); }} onProfile={() => { setRoomPanel(null); setChildPickerOpen(true); }} profileBusy={busy || chatBusy} />
        }>{chatSettings}</RoomChatTools>}
        {!(roomScene && tab === "chat") && <div className="cabinet-foot">
          <Link to="/">
            <ArrowLeft size={16} />
            На главную
          </Link>
          <a
            href={`${import.meta.env.BASE_URL}mamin-pomoshchnik-instruction.pdf`}
            target="_blank"
            rel="noreferrer"
          >
            Инструкция — скачать PDF
          </a>
          <span>Информационный помощник для родителей</span>
        </div>}
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
                clearChatDrafts(user.id);
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
