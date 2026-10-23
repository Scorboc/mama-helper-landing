import { useLocation, useNavigate } from "react-router-dom";
import { useEffect, useId, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/parent-api";
import { randomId } from "@/lib/id";
import { journalDay, type CareRecord } from "@/lib/care-journal";
import { anniversary, memoryInstant, validDay } from "@/lib/first-year-book";
import { milestoneLabels, milestoneQuestions, formatMilestoneDate, milestoneFromSearch, type MilestoneSkill } from "@/lib/milestone-marks";
import { familyList } from "@/lib/family";
import type { ParentState } from "@/lib/parent-model";
import FirstYearBook from "./FirstYearBook";

export function PushMilestoneMark({ state, search }: { state: ParentState; search: string }) {
  const location = useLocation(), navigate = useNavigate();
  const [opened, setOpened] = useState<ReturnType<typeof milestoneFromSearch>>(null);
  const childIds = familyList(state).map(c => c.id).join(",");
  const activeChild = state.activeChildId || "primary", stage = state.profile?.stage;
  useEffect(() => {
    const mark = milestoneFromSearch(search, childIds.split(","));
    if (!mark || mark.childId !== activeChild || stage !== "child") return;
    setOpened(mark);
    const params = new URLSearchParams(search);
    params.delete("mark"); params.delete("child");
    navigate({ pathname: location.pathname, search: params.toString(), hash: location.hash }, { replace: true });
  }, [search, childIds, activeChild, stage, location.pathname, location.hash, navigate]);
  if (!opened || opened.childId !== activeChild || stage !== "child") return null;
  return <MilestoneMark key={opened.childId + opened.skill} state={state} skill={opened.skill} push onClose={() => {
    setOpened(null);
    document.getElementById("main-content")?.focus({ preventScroll: true });
  }} />;
}

type Listing = {
  records: CareRecord[];
  achievements: { id: string; kind: string; date: string }[];
  permission: string;
  profile: { birthDate: string };
};
type Hint = { title: string; text: string; guidanceText?: string; milestoneSkill?: string };

export default function MilestoneMark({ state, skill, push = false, onClose }: { state: ParentState; skill: MilestoneSkill; push?: boolean; onClose?: () => void }) {
  const childId = state.activeChildId || "primary", label = milestoneLabels[skill];
  const zone = state.preferences.timezone || "Europe/Moscow", today = journalDay(Date.now(), zone);
  const [day, setDay] = useState(today), [record, setRecord] = useState<CareRecord>(), [legacy, setLegacy] = useState(false);
  const [ready, setReady] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const [created, setCreated] = useState(false), [permission, setPermission] = useState("");
  const [birth, setBirth] = useState(state.profile?.birthDate || "");
  const [hint, setHint] = useState<Hint | null>(), [hintError, setHintError] = useState("");
  const [answer, setAnswer] = useState<"question" | "date" | "declined">("question"), [memory, setMemory] = useState(0);
  const lock = useRef(false), alive = useRef(false), id = useRef(randomId());
  const dateId = useId(), errorId = useId();
  useEffect(() => {
    alive.current = true;
    let cancelled = false, ticket = 0;
    setReady(false); setPermission(""); setRecord(undefined); setCreated(false); setMemory(0); setAnswer("question");
    setHint(undefined); setHintError("");
    async function load() {
      const request = ++ticket;
      try {
        // R1 coalesces this read with the book and other journal consumers.
        const result = await api<Listing>("care-list", { childId });
        if (cancelled || request !== ticket) return;
        const found = result.records.find(r => r.kind === "achievement" && (r.skill === skill || r.value === label));
        const old = result.achievements.find(r => r.kind === skill);
        setRecord(found || (old ? { id: old.id, kind: "achievement", at: old.date + "T00:00:00Z", value: label } : undefined));
        setLegacy(!found && !!old); setPermission(result.permission); setBirth(result.profile.birthDate); setReady(true); setError("");
      } catch { if (!cancelled && request === ticket) { setReady(false); setPermission(""); setError("Не удалось проверить отметки. Откройте карточку снова."); } }
    }
    async function loadHint() {
      try {
        // Server maps the allowlisted skill to its stable topic and checks current age/health.
        const result = await api<{ selected: Hint | null }>("age-guidance", { childId, milestoneSkill: skill });
        if (!cancelled) setHint(result.selected?.milestoneSkill === skill ? result.selected : null);
      } catch { if (!cancelled) { setHint(null); setHintError("Не удалось открыть подсказку. Попробуйте открыть её снова."); } }
    }
    void load();
    if (push) void loadHint();
    const refresh = () => { if (!lock.current) void load(); };
    window.addEventListener("care-records-changed", refresh);
    return () => { cancelled = true; alive.current = false; window.removeEventListener("care-records-changed", refresh); };
  }, [childId, skill, label, push]);
  const own = permission === "owner";
  const validDate = validDay(day) && validDay(birth) && day >= birth && day <= today;
  async function change(remove = false) {
    if (lock.current || !ready || !own || (!remove && !validDate)) return;
    lock.current = true; setBusy(true); setError("");
    try {
      const result = remove ? await api("care-delete", { childId, id: record?.id }) : await api<{ record: CareRecord & { legacy?: boolean }; alreadyMarked?: boolean }>("care-put", { childId, record: { id: id.current, kind: "achievement", skill, value: label, at: memoryInstant(day, zone), note: "" } });
      if (!alive.current) return;
      if (remove) { setRecord(undefined); setCreated(false); id.current = randomId(); setAnswer("question"); }
      else { const saved = result as { record: CareRecord & { legacy?: boolean }; alreadyMarked?: boolean }; setRecord(saved.record); setLegacy(!!saved.record.legacy); setCreated(!saved.alreadyMarked && saved.record.id === id.current && !saved.record.legacy); }
      window.dispatchEvent(new Event("care-records-changed"));
    } catch { if (alive.current) setError("Изменение не подтверждено. Можно повторить: повторная отметка не создаётся."); }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  const recordDay = record ? legacy ? record.at.slice(0, 10) : journalDay(record.at, zone) : "";
  const inBook = validDay(birth) && recordDay >= birth && recordDay < anniversary(birth, 12);
  const questionReady = !push || hint !== undefined && !hintError;
  return <section className="milestone-mark min-w-0 rounded-xl border p-4 my-3 space-y-3 break-words" aria-label={`Отметка навыка: ${label}`} aria-busy={busy}>
    {push && <div>{hint === undefined ? <p role="status">Открываем подсказку…</p> : hint ? <><h2 className="font-semibold">{hint.title}</h2><p>{hint.guidanceText || hint.text}</p></> : <p>{hintError || "Эта возрастная подсказка сейчас недоступна. Сохранить реальное наблюдение можно в любой момент."}</p>}</div>}
    {record ? <><p role="status">{created ? `Сохранено: ${formatMilestoneDate(recordDay, today)} — в «Наших открытиях»${inBook ? " и «Книге первого года»" : ""}.` : `Уже отмечено ${formatMilestoneDate(recordDay, today)}`}</p>{created && !legacy && own && <Button className="min-h-11 h-auto whitespace-normal" variant="outline" disabled={busy} aria-label={`Отменить отметку: ${label}`} onClick={() => void change(true)}>Отменить / удалить отметку</Button>}</> : ready && own && questionReady && <>
      {push && answer === "question" && <><p>{milestoneQuestions[skill]}</p><Button className="min-h-11" onClick={() => setAnswer("date")}>Да</Button></>}
      {push && answer === "declined" && <p role="status">Спасибо. Здесь нечего сдавать или догонять. Отметить можно в любой момент в «Наших открытиях».</p>}
      {(!push || answer === "date") && <>
        {push && <fieldset className="space-y-3"><legend>Когда это случилось?</legend><Button className="min-h-11" variant="outline" disabled={busy} onClick={() => setDay(today)}>Сегодня</Button><label htmlFor={dateId} className="form-field">Или своя дата<Input autoFocus id={dateId} className="min-h-11 max-w-full" disabled={busy} type="date" value={day} max={today} min={birth} aria-invalid={!validDate} aria-describedby={error ? errorId : undefined} onChange={e => setDay(e.target.value)} /><span>{formatMilestoneDate(day, today)}</span></label></fieldset>}
        <Button className="min-h-11 h-auto whitespace-normal" disabled={busy || !validDate} aria-label={`Отметить в карточке: ${label}, ${formatMilestoneDate(day, today)}`} onClick={() => void change()}>{push ? "Сохранить" : `Отметить в карточке: ${label} (сегодня)`}</Button>
      </>}
      {push && skill === "crawl" && <Button className="min-h-11 h-auto w-full whitespace-normal" variant="outline" disabled={busy} onClick={() => setMemory(n => n + 1)}>Передвигается по-своему — записать своими словами</Button>}
    </>}
    {ready && !validDay(birth) && <p>Укажите дату рождения в профиле, чтобы сохранить отметку с верной датой.</p>}
    {ready && !own && <p>Отметить навык может владелец профиля.</p>}
    {memory > 0 && own && <FirstYearBook key={childId + memory} context={{ childId }} zone={zone} startAdding />}
    {error && <p id={errorId} role="alert">{error}</p>}
    {push && <div className="flex flex-wrap gap-2">{ready && own && questionReady && !record && answer !== "declined" && <Button className="min-h-11" variant="outline" disabled={busy} onClick={() => setAnswer("declined")}>Пока нет</Button>}<Button className="min-h-11" variant="ghost" disabled={busy} onClick={onClose}>Закрыть</Button></div>}
  </section>;
}
