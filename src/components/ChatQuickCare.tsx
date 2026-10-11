import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/parent-api";
import { randomId } from "@/lib/id";
import { RequestScope } from "@/lib/request-scope";
import { contextLabel, ParentState } from "@/lib/parent-model";
import type { CareRecord, CareSummary } from "@/lib/care-journal";
import ManualCareEntry from "./ManualCareEntry";
import { careTime } from "@/lib/care-time";

type Listing = { records: CareRecord[]; summary?: CareSummary; permission: string };
type Write = { action: "care-put"; record: CareRecord } | { action: "care-delete"; id: string };

export default function ChatQuickCare({ state, onTrackers, onProfile, profileBusy = false }: { state: ParentState; onTrackers: () => void; onProfile?: () => void; profileBusy?: boolean }) {
  const childId = state.activeChildId || "primary";
  const scope = useRef(new RequestScope());
  scope.current.select(childId);
  const mutations = useRef(new RequestScope());
  mutations.current.select(childId);
  const alive = useRef(false);
  const lock = useRef(false);
  const pendingRef = useRef<Write | null>(null);
  const [listing, setListing] = useState<Listing>();
  const [open, setOpen] = useState<"sleep" | "feeding" | "note" | "manual-sleep" | "manual-feeding" | null>(null);
  const [editing, setEditing] = useState<CareRecord | null>(null);
  const [deleting, setDeleting] = useState<CareRecord | null>(null);
  const recentSummary = useRef<HTMLElement>(null);
  const manualButtons = useRef<{ sleep: HTMLButtonElement | null; feeding: HTMLButtonElement | null }>({ sleep: null, feeding: null });
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [pending, setPending] = useState<Write | null>(null);
  const [note, setNote] = useState("");
  const [now, setNow] = useState(Date.now());
  const editable = state.profile?.stage === "child";
  const ready = !!listing && !error;

  const load = useCallback(async () => {
    if (!editable) return false;
    const ticket = scope.current.begin(childId);
    try {
      const result = await api<Listing>("care-list", { childId }, 15000);
      if (!alive.current || !scope.current.current(ticket)) return false;
      setListing(result);
      setError("");
      return true;
    } catch (e) {
      if (alive.current && scope.current.current(ticket)) setError((e as Error).message);
      return false;
    }
  }, [childId, editable]);

  useEffect(() => {
    const requests = scope.current;
    const writes = mutations.current;
    alive.current = true;
    lock.current = false;
    pendingRef.current = null;
    setPending(null);
    setBusy(false);
    setStatus("");
    setSaveError("");
    setListing(undefined);
    setOpen(null);
    setEditing(null);
    setDeleting(null);
    setError("");
    void load();
    const refresh = () => {
      if (document.visibilityState === "visible" && !lock.current && !pendingRef.current) void load();
    };
    const timer = window.setInterval(() => { setNow(Date.now()); refresh(); }, 30000);
    window.addEventListener("care-records-changed", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      alive.current = false;
      requests.cancel();
      writes.cancel();
      window.removeEventListener("care-records-changed", refresh);
      document.removeEventListener("visibilitychange", refresh);
      window.clearInterval(timer);
    };
  }, [load]);

  if (!editable) return null;
  const records = listing?.records || [];
  const currentSleep = records.find((r) => r.kind === "sleep" && !r.end);
  const feedingTimer = records.find((r) => r.kind === "feeding" && r.value === "Таймер кормления" && !r.end);
  const disabled = busy || !ready || !!pending || listing?.permission === "read";
  const minutes = (r: CareRecord) => Math.max(0, Math.floor((now - Date.parse(r.at)) / 60000));

  function chooseOpen(next: typeof open) { setOpen(next); setEditing(null); setDeleting(null); }
  const put = (record: CareRecord) => write({ action: "care-put", record });
  async function write(change: Write) {
    if (lock.current) return;
    lock.current = true;
    const ticket = mutations.current.begin(childId);
    setBusy(true);
    setStatus("");
    setError("");
    setSaveError("");
    try {
      await api(change.action, { childId, ...(change.action === "care-put" ? { record: change.record } : { id: change.id }) }, 15000);
      if (!alive.current || !mutations.current.current(ticket)) return;
      setPending(null);
      pendingRef.current = null;
      setNote("");
      setOpen(null);
      setEditing(null);
      setDeleting(null);
      const record = change.action === "care-put" ? change.record : null;
      setStatus(record ? record.end ? (record.kind === "sleep" ? "Запись сна" : "Запись кормления") + " сохранена в дневнике: " + careTime(record.at) + " — " + careTime(record.end) : "Отметка сохранена в дневнике" : "Отметка удалена из дневника");
      if (editing || deleting) recentSummary.current?.focus({ preventScroll: true });
      if (open === "manual-sleep" || open === "manual-feeding") {
        manualButtons.current[open === "manual-sleep" ? "sleep" : "feeding"]?.focus();
      }
      await load();
      window.dispatchEvent(new Event("care-records-changed"));
    } catch (e) {
      if (alive.current && mutations.current.current(ticket)) {
        if (!(e instanceof ApiError) || e.status >= 500) {
          // Same ID and timestamps after a lost response: no duplicate event.
          setPending(change);
          pendingRef.current = change;
        } else {
          setPending(null);
          pendingRef.current = null;
        }
        setSaveError((e as Error).message);
      }
    } finally {
      if (alive.current && mutations.current.current(ticket)) {
        lock.current = false;
        setBusy(false);
      }
    }
  }
  const record = (kind: CareRecord["kind"], extra: Partial<CareRecord> = {}): CareRecord => ({ id: randomId(), kind, at: new Date().toISOString(), note: "", ...extra });

  return <section className="chat-quick-care" aria-label="Быстрые отметки" aria-busy={busy || (!listing && !error)}>
    <div className="chat-quick-care__head">
      {onProfile && <Button className="quick-care-profile" type="button" variant="ghost" disabled={busy || profileBusy} onClick={onProfile} aria-haspopup="dialog" aria-label={`Выбрать ребёнка: ${contextLabel(state.profile)}`}><span>{contextLabel(state.profile)}</span><ChevronDown size={16} aria-hidden="true" className="shrink-0" /></Button>}
      <strong>{currentSleep ? "Спит · " + minutes(currentSleep) + " мин." : feedingTimer ? "Кормление · " + minutes(feedingTimer) + " мин." : "Отметить сейчас"}</strong>
      <Button type="button" variant="ghost" onClick={onTrackers}>Графики</Button>
    </div>
    {!listing && !error && <p role="status">Загружаем дневник…</p>}
    {status && <p role="status">{status}</p>}
    {(error || saveError) && <div className="chat-quick-care__error">
      <p role="alert">{pending ? "Изменение не подтверждено. " : saveError ? "Не удалось изменить запись. " : "Не удалось обновить дневник. "}{saveError || error}</p>
      <Button type="button" variant="outline" disabled={busy} onClick={() => pending ? void write(pending) : void load()}>{pending ? "Повторить изменение" : "Обновить дневник"}</Button>
      {pending && <Button type="button" variant="ghost" disabled={busy} onClick={() => { setPending(null); pendingRef.current = null; setSaveError(""); setStatus("Проверьте дневник: изменение могло сохраниться при потере связи"); void load(); }}>Проверить записи</Button>}
    </div>}
    <div className="chat-quick-care__actions">
      {currentSleep ? <Button type="button" variant="outline" disabled={disabled} onClick={() => void put({ ...currentSleep, end: new Date().toISOString() })}>Проснулся</Button> : <Button type="button" variant="outline" aria-expanded={open === "sleep"} disabled={disabled} onClick={() => chooseOpen(open === "sleep" ? null : "sleep")}>Сон</Button>}
      {feedingTimer ? <Button type="button" variant="outline" disabled={disabled} onClick={() => void put({ ...feedingTimer, end: new Date().toISOString() })}>Закончить кормление</Button> : <Button type="button" variant="outline" aria-expanded={open === "feeding"} disabled={disabled} onClick={() => chooseOpen(open === "feeding" ? null : "feeding")}>Кормление</Button>}
      <Button type="button" variant="outline" disabled={disabled || !!currentSleep} onClick={() => void put(record("wake", { wakeType: "morning" }))}>Утренний подъём</Button>
      <Button type="button" variant="outline" aria-expanded={open === "note"} disabled={disabled} onClick={() => chooseOpen(open === "note" ? null : "note")}>Заметка</Button>
    </div>
    {open === "sleep" && <div className="chat-quick-care__sheet" role="group" aria-label="Выберите вид сна">
      <Button type="button" disabled={disabled} onClick={() => void put(record("sleep", { sleepType: "day" }))}>Дневной сон</Button>
      <Button type="button" variant="outline" disabled={disabled} onClick={() => void put(record("sleep", { sleepType: "night" }))}>Ночной сон</Button>
    </div>}
    {open === "feeding" && <div className="chat-quick-care__sheet" role="group" aria-label="Выберите способ кормления">
      <Button type="button" disabled={disabled} onClick={() => void put(record("feeding", { side: "left", value: "ГВ" }))}>ГВ · левая</Button>
      <Button type="button" variant="outline" disabled={disabled} onClick={() => void put(record("feeding", { side: "right", value: "ГВ" }))}>ГВ · правая</Button>
      <Button type="button" variant="outline" disabled={disabled} onClick={() => void put(record("feeding", { side: "bottle", value: "Бутылочка" }))}>Бутылочка</Button>
      <Button type="button" variant="outline" disabled={disabled} onClick={() => void put(record("feeding", { value: "Таймер кормления" }))}>Таймер кормления</Button>
    </div>}
    {open === "note" && <form className="chat-quick-care__note" onSubmit={(e) => { e.preventDefault(); if (note.trim()) void put(record("achievement", { value: "Наблюдение", note: note.trim() })); }}>
      <label htmlFor="quick-care-note">Что хотите отметить?</label>
      <Textarea id="quick-care-note" autoFocus value={note} maxLength={500} disabled={busy || !!pending} onChange={(e) => setNote(e.target.value)} />
      <Button type="submit" disabled={disabled || !note.trim()}>Сохранить заметку</Button>
    </form>}
    <div className="chat-quick-care__past">
      <p>Если не отметили сразу</p>
      <div className="chat-quick-care__manual-options">
        <Button ref={(button) => { manualButtons.current.sleep = button; }} type="button" variant="ghost" disabled={disabled} aria-expanded={open === "manual-sleep"} aria-controls="quick-manual-entry" onClick={() => chooseOpen(open === "manual-sleep" ? null : "manual-sleep")}>Сон вручную</Button>
        <Button ref={(button) => { manualButtons.current.feeding = button; }} type="button" variant="ghost" disabled={disabled} aria-expanded={open === "manual-feeding"} aria-controls="quick-manual-entry" onClick={() => chooseOpen(open === "manual-feeding" ? null : "manual-feeding")}>Кормление вручную</Button>
      </div>
    </div>
    <div id="quick-manual-entry">
      {(editing || open === "manual-sleep" || open === "manual-feeding") && <ManualCareEntry key={childId + (editing?.id || open)} kind={editing?.kind === "sleep" || open === "manual-sleep" ? "sleep" : "feeding"} record={editing || undefined} records={records} disabled={disabled} onSave={put} onClose={() => { const kind = open === "manual-sleep" ? "sleep" : "feeding"; setOpen(null); setEditing(null); if (editing) recentSummary.current?.focus(); else manualButtons.current[kind]?.focus(); }} />}
    </div>
    {records.some((r) => r.kind === "sleep" || r.kind === "feeding") && <details className="chat-quick-care__recent">
      <summary ref={recentSummary}>Последние отметки · исправить или удалить</summary>
      {records.filter((r) => r.kind === "sleep" || r.kind === "feeding").slice(0, 8).map((r) => <div key={r.id} className="chat-quick-care__record" data-record-id={r.id}>
        <strong>{r.kind === "sleep" ? r.sleepType === "night" ? "Ночной сон" : r.sleepType === "day" ? "Дневной сон" : "Сон" : "Кормление"}</strong>
        <p>{careTime(r.at)}{r.end ? " — " + careTime(r.end) : r.kind === "sleep" || r.value === "Таймер кормления" ? " · таймер работает" : ""}</p>
        <div className="care-record-actions">
          <Button type="button" variant="ghost" disabled={disabled} aria-label={"Исправить " + (r.kind === "sleep" ? "сон" : "кормление") + ": " + careTime(r.at)} onClick={() => { setOpen(null); setDeleting(null); setEditing(r); setSaveError(""); }}>Исправить</Button>
          {listing?.permission === "owner" && <Button type="button" variant="ghost" disabled={disabled} aria-label={"Удалить " + (r.kind === "sleep" ? "сон" : "кормление") + ": " + careTime(r.at)} onClick={() => { setEditing(null); setOpen(null); setDeleting(r); setSaveError(""); }}>Удалить</Button>}
        </div>
        {deleting?.id === r.id && <div className="chat-quick-care__delete" role="group" aria-label="Подтверждение удаления">
          <p>Удалить эту отметку{!r.end && (r.kind === "sleep" || r.value === "Таймер кормления") ? " и остановить её таймер" : ""}? Восстановить её можно будет вручную.</p>
          <div className="care-record-actions"><Button type="button" variant="destructive" disabled={disabled} onClick={() => void write({ action: "care-delete", id: r.id })}>Удалить отметку</Button><Button type="button" variant="outline" autoFocus disabled={disabled} onClick={() => { setDeleting(null); recentSummary.current?.focus({ preventScroll: true }); }}>Оставить отметку</Button></div>
        </div>}
      </div>)}
      <Button type="button" variant="ghost" onClick={onTrackers}>Весь дневник в трекерах</Button>
    </details>}
    {!!listing?.summary?.records && <details className="chat-quick-care__summary">
      <summary>Записи за 7 дней · {listing.summary.records}</summary>
      <p>Эпизодов сна: {listing.summary.sleep.sleepRecords}. Отметок кормлений: {listing.summary.feeding.records}. ИИ может учитывать эти наблюдения активного профиля. Полнота дневника неизвестна — по числу записей нельзя оценить норму сна или питания.</p>
    </details>}
  </section>;
}
