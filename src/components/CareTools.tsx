import SleepDiary from "./SleepDiary";
import CareWeek from "./CareWeek";
import FoodPreparation from "./FoodPreparation";
import CareImport from "./CareImport";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useSearchParams } from "react-router-dom";
import { api } from "@/lib/parent-api";
import { ParentState } from "@/lib/parent-model";
import { randomId } from "@/lib/id";
import { buildConsultationReport, recordInPeriod } from "@/lib/care-journal";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import ManualCareEntry from "./ManualCareEntry";
import type { CareRecord } from "@/lib/care-journal";
import { careTime } from "@/lib/care-time";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";

type RecordItem = {
  id: string;
  kind: "sleep" | "wake" | "feeding" | "food" | "achievement" | "mood";
  at: string;
  end?: string;
  note: string;
  value?: string;
  side?: string;
};
type Access = {
  isOwner: boolean;
  id: string;
  ownerId: string;
  childId: string;
  guestId: string | null;
  permission: "read" | "write";
  childName: string;
};
type Listing = {
  summary?: import("@/lib/care-journal").CareSummary;
  contextVersion: string;
  authors?: Record<string,{createdByRole:string;updatedByRole:string;updatedAt:string}>;
  daily: { id: string; title: string; goal: string; steps: string[] }[];
  records: RecordItem[];
  profile: { childName: string; stage: string; birthDate: string };
  permission: string;
  achievements: { date: string; note: string }[];
  appointments: {
    date: string;
    reason: string;
    questions: string;
    instructions: string;
  }[];
};
const labels = {
  wake: "Пробуждение",
  sleep: "Сон",
  feeding: "Кормление",
  food: "Прикорм",
  achievement: "Новое умение",
  mood: "Самочувствие родителя",
};
const moods: Record<string, string> = {
  calm: "Спокойно",
  tired: "Устала / устал",
  anxious: "Тревожно",
};
export const moodTips: Record<string, string[]> = {
  calm: [
    "Время для любимого",
    "Оставьте несколько минут для того, что нравится именно вам: музыка, книга или разговор с близким.",
  ],
  tired: [
    "Снизить нагрузку сегодня",
    "Отложите одно необязательное дело. Если есть близкий, попросите взять конкретную задачу и договоритесь о времени для вашего отдыха.",
  ],
  anxious: [
    "Небольшая опора сейчас",
    "Сядьте удобно и спокойно подышите без задержек дыхания. Запишите, что тревожит больше всего, и одну посильную просьбу к близкому. Если тревога держится и мешает жить, обратитесь за профессиональной помощью.",
  ],
};
function exportText(name: string, text: string) {
  const url = URL.createObjectURL(
    new Blob([text], { type: "text/plain;charset=utf-8" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function TrackerSummary({
  records,
  now,
}: {
  records: RecordItem[];
  now: number;
}) {
  const cutoff = now - 86400000;
  const minutes = (start: number, end: number) =>
    Math.round(
      records
        .filter((r) => r.kind === "sleep")
        .reduce(
          (sum, r) =>
            sum +
            Math.max(
              0,
              Math.min(end, r.end ? Date.parse(r.end) : now) -
                Math.max(start, Date.parse(r.at)),
            ),
          0,
        ) / 60000,
    );
  const current = minutes(cutoff, now),
    previous = minutes(cutoff - 86400000, cutoff);
  const feeds = records.filter(
    (r) => r.kind === "feeding" && Date.parse(r.at) >= cutoff,
  );
  const last = records.find((r) => r.kind === "feeding");
  const week = Array.from({ length: 7 }, (_, i) => {
    const end = now - (6 - i) * 86400000;
    return {
      label: new Date(end).toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "numeric",
      }),
      minutes: minutes(end - 86400000, end),
    };
  });
  const max = Math.max(1, ...week.map((d) => d.minutes));
  return (
    <section
      className="tracker-summary"
      aria-label="Записано за последние сутки"
    >
      <h3>Последние 24 часа</h3>
      <div className="tracker-numbers">
        <div>
          <strong>
            {Math.floor(current / 60)} ч {current % 60} мин
          </strong>
          <span>записанного сна</span>
        </div>
        <div>
          <strong>{feeds.length}</strong>
          <span>кормлений в дневнике</span>
        </div>
      </div>
      {last && (
        <p>Последнее кормление: {new Date(last.at).toLocaleString("ru-RU")}.</p>
      )}
      {feeds.length > 1 && (
        <p>
          Между двумя последними записями кормления:{" "}
          {Math.round(
            (Date.parse(feeds[0].at) - Date.parse(feeds[1].at)) / 60000,
          )}{" "}
          мин. Это наблюдение, а не рекомендуемый интервал.
        </p>
      )}
      {current > 0 && previous > 0 && (
        <p>
          Сна в записях на {Math.abs(current - previous)} мин{" "}
          {current >= previous ? "больше" : "меньше"}, чем за предыдущие сутки.
          Сравнивайте только дни с одинаково полными записями.
        </p>
      )}
      <div
        className="sleep-week"
        aria-label="Записанный сон: семь периодов по 24 часа"
      >
        {week.map((d) => (
          <div key={d.label}>
            <span>{Math.round((d.minutes / 60) * 10) / 10} ч</span>
            <div
              className="sleep-bar"
              style={{ height: Math.max(2, (d.minutes / max) * 70) }}
            />
            <small>{d.label}</small>
          </div>
        ))}
      </div>
      <p className="muted">
        Сводка отражает ваши записи. Она не определяет норму сна, достаточность
        питания или причину изменений.
      </p>
    </section>
  );
}
export default function CareTools({
  state,
  onMood,
  expanded = false,
  active = true,
  drafts = {},
}: {
  state: ParentState;
  onMood: (mood: string) => void;
  expanded?: boolean;
  active?: boolean;
  drafts?: Record<
    string,
    { note: string; value: string; sleepStart?: string; sleepEnd?: string }
  >;
}) {
  const cid = state.activeChildId || "primary";
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedPanel = searchParams.get("tracker");
  const panelIds = ["track", "growth", "development", "food", "mood", "doctor", "family"];
  const bodyRef = useRef<HTMLDivElement>(null);
  const [listing, setListing] = useState<Listing>(),
    [access, setAccess] = useState<Access[]>([]),
    [target, setTarget] = useState(""),
    [localPanel, setLocalPanel] = useState(expanded ? "track" : ""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const panel = expanded ? (panelIds.includes(requestedPanel || "") ? requestedPanel! : "track") : localPanel;
  const previousPanel = useRef(panel);
  useEffect(() => {
    if (!active || previousPanel.current === panel) return;
    previousPanel.current = panel;
    const frame = requestAnimationFrame(() => {
      bodyRef.current?.focus({ preventScroll: true });
      bodyRef.current?.scrollIntoView({ block: "start", behavior: "instant" });
    });
    return () => cancelAnimationFrame(frame);
  }, [panel, active]);
  const [note, setNote] = useState(""),
    [value, setValue] = useState(""),
    [side, setSide] = useState("left"),
    [code, setCode] = useState(""),
    [invite, setInvite] = useState(""),
    [permission, setPermission] = useState("read"),
    [days, setDays] = useState(7),
    [selected, setSelected] = useState<string[]>([]);
  const [now, setNow] = useState(Date.now());
  const scope = useRef(0);
  const selectionInitialized = useRef(false);
  const [sleepStart, setSleepStart] = useState(""),
    [sleepEnd, setSleepEnd] = useState("");
  const shared = access.find((a) => a.id === target);
  const context = {
    childId: shared?.childId || cid,
    ...(shared ? { ownerId: shared.ownerId } : {}),
  };
  const contextKey = JSON.stringify(context);
  const contextRef = useRef(contextKey);
  contextRef.current = contextKey;
  const draftKey = `${contextKey}:${panel}`;
  const draftKeyRef = useRef(draftKey);
  draftKeyRef.current = draftKey;
  const [status, setStatus] = useState("");
  const [feedingEditor, setFeedingEditor] = useState<CareRecord | null>(null);
  useEffect(() => { setFeedingEditor(null); }, [contextKey]);
  const [includeVisits, setIncludeVisits] = useState(false);
  const [printingReport, setPrintingReport] = useState(false);
  const [includeAchievements, setIncludeAchievements] = useState(false);
  const lastDraft = useRef({ note, value, sleepStart, sleepEnd });
  lastDraft.current = { note, value, sleepStart, sleepEnd };
  useEffect(() => {
    const saved = drafts[draftKey];
    setNote(saved?.note || "");
    setValue(saved?.value || "");
    setSleepStart(saved?.sleepStart || "");
    setSleepEnd(saved?.sleepEnd || "");
    return () => {
      drafts[draftKey] = lastDraft.current;
    };
  // The draft store is shared and keyed by draftKey; only a key change should re-seed the form.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftKey]);
  function changePanel(id: string) {
    drafts[draftKey] = lastDraft.current;
    if (expanded) {
      const params = new URLSearchParams(searchParams);
      params.set("tracker", id);
      setSearchParams(params, { state: { cabinetSection: true } });
    } else setLocalPanel(id);
    setError("");
    setStatus("");
  }
  const editable = listing?.permission !== "read";
  const own = listing?.permission === "owner";
  async function load() {
    const ticket = ++scope.current,
      key = contextKey;
    try {
      const result = await api<Listing>("care-list", context);
      if (ticket !== scope.current || key !== contextRef.current) return;
      setListing(result);
      if (!selectionInitialized.current) {
        setSelected(
          result.records
            .filter(
              (r) =>
                r.kind !== "mood" &&
                recordInPeriod(r, days, Date.now(), state.preferences.timezone),
            )
            .map((r) => r.id),
        );
        selectionInitialized.current = true;
      } else {
        setSelected((ids) =>
          ids.filter((id) => result.records.some((r) => r.id === id)),
        );
      }
      if (!shared) {
        const day = new Intl.DateTimeFormat("en-CA", {
          timeZone: state.preferences.timezone || "Europe/Moscow",
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
        }).format(new Date());
        const mood = result.records.find(
          (r) =>
            r.kind === "mood" &&
            new Intl.DateTimeFormat("en-CA", {
              timeZone: state.preferences.timezone || "Europe/Moscow",
              year: "numeric",
              month: "2-digit",
              day: "2-digit",
            }).format(new Date(r.at)) === day,
        );
        onMood(mood?.value || "");
      }
    } catch (e) {
      if (ticket === scope.current) setError((e as Error).message);
    }
  }
  async function families() {
    try {
      const r = await api<{ items: Access[] }>("family-list");
      setAccess(r.items);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    selectionInitialized.current = false;
    setSelected([]);
    setListing(undefined);
    setError("");
    setInvite("");
    setIncludeVisits(false);
    setIncludeAchievements(false);
    onMood("");
    void load();
    return () => {
      // Invalidate in-flight loads for the previous context. Reading the counter here is intended.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      scope.current++;
    };
  // load is recreated every render; listing it would reset the list on each render.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contextKey]);
  useEffect(() => {
    if (!active || !panel) return;
    const update = () => {
      if (document.visibilityState === "visible") void load();
    };
    update();
    const timer = setInterval(update, 30000);
    window.addEventListener("care-records-changed", update);
    document.addEventListener("visibilitychange", update);
    return () => {
      clearInterval(timer);
      window.removeEventListener("care-records-changed", update);
      document.removeEventListener("visibilitychange", update);
    };
  // load is recreated every render; the poll re-runs on context, panel and visibility changes only.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contextKey, panel, active]);
  useEffect(() => {
    void families();
    const timer = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(timer);
  }, []);
  async function mutate(action: string, data: object) {
    if (busy) return false;
    setBusy(true);
    setError("");
    const key = contextKey,
      originDraft = draftKey;
    try {
      await api(action, { ...context, ...data });
      if (key === contextRef.current) {
        await load();
        await families();
        drafts[originDraft] = { note: "", value: "" };
        if (draftKeyRef.current === originDraft) {
          setNote("");
          setValue("");
          setStatus(action === "care-delete" ? "Запись удалена" : "Сохранено");
        }
        window.dispatchEvent(new Event("care-records-changed"));
        return true;
      }
      return false;
    } catch (e) {
      if (key === contextRef.current) setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }
  function add(kind: RecordItem["kind"], extra: Partial<RecordItem> = {}) {
    return mutate("care-put", {
      record: {
        id: randomId(),
        kind,
        at: new Date().toISOString(),
        note,
        ...extra,
      },
    });
  }
  const records = listing?.records || [];
  const moodRecords = own ? records.filter(r => r.kind === "mood").sort((a, b) => Date.parse(b.at) - Date.parse(a.at)) : [];
  const latestMood = moodRecords[0];
  const moodDate = (at: string) => new Intl.DateTimeFormat("ru-RU", {
    timeZone: state.preferences.timezone || "Europe/Moscow", dateStyle: "medium", timeStyle: "short",
  }).format(new Date(at));
  const localDay = (at: string | number) => new Intl.DateTimeFormat("en-CA", {
    timeZone: state.preferences.timezone || "Europe/Moscow", year: "numeric", month: "2-digit", day: "2-digit",
  }).format(new Date(at));
  const child = listing?.profile.stage === "child";
  const feedingTimer = records.find(
    (r) => r.kind === "feeding" && r.value === "Таймер кормления" && !r.end,
  );
  const cutoff = now - days * 86400000;
  const recent = records.filter(
    (r) => recordInPeriod(r, days, now, state.preferences.timezone),
  );
  const sleepMinutes = Math.round(
    records
      .filter((r) => r.kind === "sleep" && r.end)
      .reduce(
        (sum, r) =>
          sum +
          Math.max(
            0,
            Math.min(now, Date.parse(r.end!)) -
              Math.max(cutoff, Date.parse(r.at)),
          ),
        0,
      ) / 60000,
  );
  const meals = recent.filter((r) => r.kind === "feeding").length;
  function reportText() {
    return buildConsultationReport({
      profile: listing?.profile || { stage: "child" }, records, selected, days,
      timezone: state.preferences.timezone, now, questions: note,
      appointments: includeVisits ? (listing?.appointments || []).filter((a) => Date.parse(a.date + "T12:00:00Z") >= cutoff && Date.parse(a.date + "T00:00:00Z") <= now) : [],
      achievements: includeAchievements ? (listing?.achievements || []).filter((a) => Date.parse(a.date + "T12:00:00Z") >= cutoff && Date.parse(a.date + "T00:00:00Z") <= now) : [],
    });
  }
  return (
    <details
      open={expanded || undefined}
      className="tile care-journal mt-5"
      onToggle={(e) => {
        if (e.currentTarget.open) void load();
      }}
    >
      <summary
        className={expanded ? "sr-only" : "cursor-pointer font-semibold"}
        onClick={(e) => {
          if (expanded) e.preventDefault();
        }}
      >
        {expanded ? "Трекеры и наблюдения" : "Дневник и семейная забота"}
      </summary>
      {active &&
        createPortal(
          <nav
            aria-label="Разделы трекеров"
            className="care-journal-nav tracker-dock"
          >
            {[
              ["track", "Сон и кормления"],
              ["growth", "Скачки роста"],
              ["development", "Наши открытия"],
              ["food", "Прикорм"],
              ["mood", "Как я сегодня"],
              ["doctor", "К врачу"],
              ["family", "Семья"],
            ].map(([id, label]) => (
              <Button
                key={id}
                aria-pressed={panel === id}
                variant={panel === id ? "default" : "outline"}
                onClick={() => changePanel(id)}
              >
                {label}
              </Button>
            ))}
          </nav>,
          document.body,
        )}
      <div
        ref={bodyRef}
        className="care-journal-body tracker-content"
        tabIndex={-1}
      >
        <h2 className="tracker-panel-title">
          {
            {
              track: "Сон и кормления",
              growth: "Скачки роста",
              development: "Наши открытия",
              food: "Прикорм",
              mood: "Как я сегодня",
              doctor: "К врачу",
              family: "Семья",
            }[panel]
          }
        </h2>
        {status && (
          <p role="status" className="save-notice">
            {status}
          </p>
        )}
        {(access.some((a) => a.guestId && !a.isOwner) || !!target) && <label className="form-field">
          Чьи записи
          <select aria-label="Чьи записи" value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value="">Мой активный ребёнок</option>
            {access
              .filter((a) => a.guestId && !a.isOwner)
              .map((a) => (
                <option key={a.id} value={a.id}>
                  {a.childName} · семейный доступ
                </option>
              ))}
          </select>
        </label>}
        {shared &&
          listing?.daily.map((item) => (
            <article key={item.id} className="border-b py-3">
              <h3>{item.title}</h3>
              <p>{item.goal}</p>
              <ol>
                {item.steps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            </article>
          ))}
        {error && (
          <p role="alert" className="form-error">
            {error}{" "}
            <Button type="button" variant="outline" onClick={() => void load()}>
              Повторить
            </Button>
          </p>
        )}
        {!listing && !error && <p role="status">Загружаем записи…</p>}
        {panel === "track" && child && (
          <SleepDiary
            key={contextKey}
            records={records}
            now={now}
            busy={busy}
            editable={editable}
            mutate={mutate}
            saveError={error}
            canDelete={own}
            childName={listing?.profile.childName || "Ребёнок"}
          />
        )}
        {panel === "track" && child && (
          <details className="sleep-section">
            <summary>Общая сводка сна и кормлений</summary>
            <TrackerSummary records={records} now={now} />
            <CareWeek authors={listing?.authors} summary={listing?.summary} records={records} timezone={state.preferences.timezone || "Europe/Moscow"} />
          </details>
        )}
        {panel === "track" && child && own && listing && <CareImport key={`import:${contextKey}`} childId={cid} version={listing.contextVersion} records={records} onSaved={load} />}
        {panel === "track" && child && (
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={busy || !editable}
              variant="outline"
              onClick={() =>
                void (feedingTimer
                  ? mutate("care-put", {
                      record: {
                        ...feedingTimer,
                        end: new Date().toISOString(),
                      },
                    })
                  : add("feeding", { side, value: "Таймер кормления" }))
              }
            >
              {feedingTimer
                ? `Закончить кормление · ${Math.max(0, Math.floor((now - Date.parse(feedingTimer.at)) / 60000))} мин.`
                : "Начать таймер кормления"}
            </Button>
            <p className="muted">
              Таймер сохраняется после закрытия страницы. Для новой записи
              выбирайте грудь или бутылочку ниже.
            </p>
          </div>
        )}

        {panel === "growth" && child && (
          <>
            <h3>Изменения, которые вы заметили</h3>
            <p>
              Более частые кормления, новые умения и перемены сна можно записать
              здесь. По календарю нельзя установить причину изменения поведения.
              Эти наблюдения помогут увидеть историю вашего ребёнка.
            </p>
            <label className="form-field">
              Что изменилось
              <Input value={value} maxLength={120} onChange={(e) => setValue(e.target.value)} placeholder="Сон, аппетит или поведение" />
            </label>
            <label className="form-field">
              Когда заметили и что помогло · необязательно
              <Textarea value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} />
            </label>
            <Button
              disabled={busy || !editable || !value.trim()}
              onClick={() =>
                void add("achievement", {
                  value: "Наблюдение роста: " + value.slice(0, 100),
                })
              }
            >
              Сохранить наблюдение
            </Button>
            {records
              .filter(
                (r) =>
                  r.kind === "achievement" &&
                  r.value?.startsWith("Наблюдение роста:"),
              )
              .map((r) => (
                <article key={r.id} className="border-b py-3">
                  <strong>{r.value}</strong>
                  <p>
                    {new Date(r.at).toLocaleDateString("ru-RU")} · {r.note}
                  </p>
                </article>
              ))}
          </>
        )}
        {panel === "mood" && own && (
          <>
            <p>Как вы сегодня? Запись видна только вам.</p>
            {latestMood ? <p role="status">Последняя отметка: <strong>{moods[latestMood.value || ""] || latestMood.value}</strong> · {moodDate(latestMood.at)}</p> : <p>Пока нет отметок самочувствия.</p>}
            <div className="flex gap-2 flex-wrap">
              {Object.entries(moods).map(([id, label]) => (
                <Button
                  key={id}
                  disabled={busy}
                  variant="outline"
                  aria-pressed={!!latestMood && localDay(latestMood.at) === localDay(now) && latestMood.value === id}
                  onClick={() => void add("mood", { value: id })}
                >
                  {label}
                </Button>
              ))}
            </div>
            {moodRecords.length > 0 && <details className="mt-4">
              <summary className="cursor-pointer py-3 font-semibold">История самочувствия</summary>
              <ol aria-label="История самочувствия">
                {moodRecords.slice(0, 60).map(record => <li key={record.id} className="border-b py-3">
                  <strong>{moods[record.value || ""] || record.value}</strong> · <time dateTime={record.at}>{moodDate(record.at)}</time>
                  {record.note && <p>{record.note}</p>}
                </li>)}
              </ol>
              {moodRecords.length > 60 && <p className="text-sm muted">Показаны последние 60 отметок. Полная история доступна в выгрузке данных.</p>}
            </details>}
          </>
        )}
        {panel === "mood" && !own && (
          <p>Самочувствие родителя доступно только владельцу аккаунта.</p>
        )}
        {panel === "track" && child && (
          <>
            <p>
              Отмечайте только то, что полезно вам. Записи не оценивают
              достаточность питания или сна.
            </p>
            <label className="form-field">
              Кормление
              <select value={side} onChange={(e) => setSide(e.target.value)}>
                <option value="left">Левая грудь</option>
                <option value="right">Правая грудь</option>
                <option value="bottle">Бутылочка</option>
              </select>
            </label>
            <label className="form-field">
              Объём или заметка · необязательно
              <Input value={value} maxLength={120} onChange={(e) => setValue(e.target.value)} />
            </label>
            <Button
              disabled={busy || !editable}
              onClick={() => void add("feeding", { side, value })}
            >
              Записать кормление
            </Button>
            <p className="mt-3">
              За {days} дней: записано {sleepMinutes} минут сна и {meals}{" "}
              кормлений. Неполные записи не отражают весь режим.
            </p>
          </>
        )}
        {panel === "development" && child && (
          <>
            <p>
              Записывайте то, что заметили сами. Навыки не обязаны появляться к
              определённому дню.
            </p>
            <label className="form-field">
              Новое умение или понравившаяся игра
              <Input maxLength={120} value={value} onChange={(e) => setValue(e.target.value)} />
            </label>
            <label className="form-field">
              Как получилось и какая помощь понадобилась · необязательно
              <Textarea maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
            </label>
            <Button
              disabled={busy || !editable || !value.trim()}
              onClick={() => void add("achievement", { value })}
            >
              Сохранить открытие
            </Button>
            {listing?.achievements.map((a, i) => (
              <p key={i}>
                {a.date} · {a.note}
              </p>
            ))}
          </>
        )}
        {panel === "food" && child && (
          <>
            <FoodPreparation key={`food:${contextKey}`} profile={shared ? listing?.profile as ParentState["profile"] : state.profile} />
            <p>
              Дневник уже предложенных продуктов и наблюдений. Он не назначает
              начало прикорма, порции или лечение.
            </p>
            <label className="form-field">
              Продукт
              <Input maxLength={120} value={value} onChange={(e) => setValue(e.target.value)} />
            </label>
            <label className="form-field">
              Как предложили и что наблюдали · необязательно
              <Textarea maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
            </label>
            <Button
              disabled={busy || !editable || !value.trim()}
              onClick={() => void add("food", { value })}
            >
              Записать продукт
            </Button>
          </>
        )}
        {["track", "food", "development", "growth"].includes(panel) &&
          listing &&
          !child && (
            <p>
              Записи ребёнка появятся после заполнения профиля родившегося
              малыша.
            </p>
          )}
        {panel === "doctor" && own && (
          <>
            <p>
              Выберите записи и проверьте сводку перед передачей специалисту.
              Переписка и самочувствие родителя не включаются. Скачивание сохраняет
              документ на вашем устройстве; сайт не отправляет его врачу.
            </p>
            <select
              aria-label="Период сводки"
              value={days}
              onChange={(e) => {
                const n = Number(e.target.value);
                setDays(n);
                setSelected(
                  records
                    .filter(
                      (r) =>
                        r.kind !== "mood" &&
                        recordInPeriod(r, n, now, state.preferences.timezone),
                    )
                    .map((r) => r.id),
                );
              }}
            >
              {[7, 14, 30].map((n) => (
                <option key={n} value={n}>
                  {n} дней
                </option>
              ))}
            </select>
            <label className="flex items-center gap-3 min-h-11">
              <input type="checkbox" checked={includeVisits} onChange={(e) => setIncludeVisits(e.target.checked)} />
              Добавить мои записи о приёмах за этот период
            </label>
            <label className="flex items-center gap-3 min-h-11">
              <input type="checkbox" checked={includeAchievements} onChange={(e) => setIncludeAchievements(e.target.checked)} />
              Добавить сохранённые наблюдения о развитии
            </label>
            <label className="form-field">
              Ваши вопросы врачу · необязательно
              <Textarea value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} />
            </label>
            {recent.map((r) => (
              <label key={r.id} className="flex items-start gap-3 py-3 min-h-11">
                <input
                  type="checkbox"
                  checked={selected.includes(r.id)}
                  onChange={(e) =>
                    setSelected(
                      e.target.checked
                        ? [...selected, r.id]
                        : selected.filter((id) => id !== r.id),
                    )
                  }
                />{" "}
                <span>{new Date(r.at).toLocaleString("ru-RU", { timeZone: state.preferences.timezone || "Europe/Moscow" })} · {labels[r.kind]} · {r.value} {r.note}</span>
              </label>
            ))}
            <label className="block mt-4">
              Предпросмотр сводки
              <Textarea
                aria-label="Предпросмотр сводки"
                readOnly
                value={reportText()}
                className="min-h-64"
              />
            </label>
            <Button
              onClick={() => exportText("Наблюдения-к-врачу.txt", reportText())}
            >
              Скачать сводку
            </Button>
            <Button variant="outline" onClick={() => setPrintingReport(true)}>Печать / PDF выбранных записей</Button>
            <Dialog open={printingReport} onOpenChange={setPrintingReport}><DialogContent className="sleep-print-sheet max-w-4xl"><DialogHeader><DialogTitle>Выбранные записи для специалиста</DialogTitle><DialogDescription>Проверьте документ перед печатью. Переписка и самочувствие родителя не включены.</DialogDescription></DialogHeader><div className="sleep-print-actions"><Button onClick={() => window.print()}>Печать / Сохранить PDF</Button><Button variant="outline" onClick={() => setPrintingReport(false)}>Закрыть</Button></div><div style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{reportText()}</div></DialogContent></Dialog>
          </>
        )}
        {panel === "family" && (
          <>
            <CareWeek authors={listing?.authors} summary={listing?.summary} records={records} timezone={state.preferences.timezone || "Europe/Moscow"} />
            <p>
              Приглашение действует 24 часа и используется один раз. Получатель
              входит в свой аккаунт. Доступ открывает записи ребёнка; переписка,
              избранное и самочувствие родителя приватны.
            </p>
            {own && (
              <>
                <select
                  aria-label="Права приглашённого"
                  value={permission}
                  onChange={(e) => setPermission(e.target.value)}
                >
                  <option value="read">Только просмотр</option>
                  <option value="write">Просмотр и добавление записей</option>
                </select>
                <Button
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      const r = await api<{ code: string }>("family-invite", {
                        childId: cid,
                        permission,
                      });
                      setInvite(r.code);
                      await families();
                    } catch (e) {
                      setError((e as Error).message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Создать приглашение
                </Button>
                {invite && (
                  <p className="break-all">
                    Передайте близкому этот код: <strong>{invite}</strong>
                  </p>
                )}
              </>
            )}
            <label className="form-field">
              Код приглашения от близкого
              <Input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                autoComplete="off"
                placeholder="Вставьте полученный код"
              />
            </label>
            <Button
              disabled={busy || !code.trim()}
              onClick={() =>
                void mutate("family-accept", { code: code.trim() })
              }
            >
              Принять приглашение
            </Button>
            {access.map((a) => (
              <div key={a.id} className="my-3">
                {a.childName} ·{" "}
                {a.guestId ? "Доступ активен" : "Ожидает принятия"} ·{" "}
                {a.permission === "read" ? "просмотр" : "добавление записей"}{" "}
                <Button
                  variant="ghost"
                  disabled={busy}
                  onClick={() => void mutate("family-revoke", { id: a.id })}
                >
                  {a.isOwner ? "Отозвать доступ" : "Выйти из доступа"}
                </Button>
              </div>
            ))}
          </>
        )}
        {["track", "food", "development"].includes(panel) && (
          <div>
            {records
              .filter((r) =>
                panel === "track"
                  ? ["feeding"].includes(r.kind)
                  : r.kind === (panel === "food" ? "food" : "achievement"),
              )
              .slice(0, 60)
              .map((r) => (
                <div key={r.id} className="border-b py-3">
                  <strong>{labels[r.kind]}</strong> ·{" "}
                  {r.kind === "feeding" ? careTime(r.at) + (r.end ? " — " + careTime(r.end) : "") : new Date(r.at).toLocaleString("ru-RU")}
                  <p>
                    {r.value}{" "}
                    {r.side === "left"
                      ? "левая грудь"
                      : r.side === "right"
                        ? "правая грудь"
                        : r.side === "bottle"
                          ? "бутылочка"
                          : ""}{" "}
                    {r.note}
                    {r.end
                      ? " · " +
                        Math.round(
                          (Date.parse(r.end) - Date.parse(r.at)) / 60000,
                        ) +
                        " мин."
                      : ""}
                  </p>
                  {r.kind === "feeding" && <Button variant="outline" disabled={busy || !editable} onClick={() => { setError(""); setFeedingEditor({ ...r }); }}>Исправить</Button>}
                  {own && (
                    <Button
                      variant="ghost"
                      disabled={busy}
                      onClick={() => {
                        if (window.confirm("Удалить эту запись?"))
                          void mutate("care-delete", { id: r.id });
                      }}
                    >
                      Удалить
                    </Button>
                  )}
                </div>
              ))}
          </div>
        )}
      </div>
      <Dialog open={!!feedingEditor} onOpenChange={(value) => { if (!busy && !value) setFeedingEditor(null); }}>
        <DialogContent className="ios-sheet">
          <DialogHeader><DialogTitle>Запись кормления</DialogTitle><DialogDescription>Исправьте время выбранной отметки. Остальные записи сохранятся.</DialogDescription></DialogHeader>
          {feedingEditor && <ManualCareEntry key={contextKey + feedingEditor.id} kind="feeding" record={feedingEditor} records={records} disabled={busy || !editable} onSave={async (record) => { if (await mutate("care-put", { record })) setFeedingEditor(null); }} onClose={() => setFeedingEditor(null)} />}
          {error && <p role="alert">{error}</p>}
        </DialogContent>
      </Dialog>
    </details>
  );
}
