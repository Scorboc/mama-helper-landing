import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import CareTimeField from "./CareTimeField";
import type { CareRecord } from "@/lib/care-journal";
import { randomId } from "@/lib/id";

export default function ManualCareEntry({ kind, record, records, disabled, onSave, onClose }: {
  kind: "sleep" | "feeding";
  record?: CareRecord;
  records: CareRecord[];
  disabled: boolean;
  onSave: (record: CareRecord) => Promise<void>;
  onClose: () => void;
}) {
  const id = useId();
  const form = useRef<HTMLFormElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const [start, setStart] = useState(record?.at || "");
  const [end, setEnd] = useState(record?.end || "");
  const [mode, setMode] = useState(record && !record.end ? kind === "sleep" || record.value === "Таймер кормления" ? "ongoing" : "point" : "interval");
  const [type, setType] = useState(kind === "sleep" ? record ? record.sleepType || "" : "day" : record ? record.side || "other" : "left");
  const [error, setError] = useState("");
  const sleep = kind === "sleep";
  const title = record ? sleep ? "Исправить сон" : "Исправить кормление" : sleep ? "Записать прошедший сон" : "Записать прошедшее кормление";

  useEffect(() => {
    heading.current?.focus({ preventScroll: true });
    form.current?.scrollIntoView({ block: "start" });
  }, []);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (disabled) return;
    const from = new Date(start).getTime();
    const to = mode === "interval" ? new Date(end).getTime() : Infinity;
    if (!Number.isFinite(from) || (mode === "interval" && !Number.isFinite(to))) {
      setError(mode === "interval" ? "Укажите время начала и окончания." : "Укажите время начала.");
      return;
    }
    if (from > Date.now() || (mode === "interval" && to > Date.now())) {
      setError("Укажите время, которое уже наступило.");
      return;
    }
    if (to <= from) {
      setError("Окончание должно быть позже начала. Если событие закончилось после полуночи, выберите другой день окончания.");
      return;
    }
    if (sleep && records.some((other) => other.id !== record?.id && other.kind === "sleep" &&
      from < (other.end ? Date.parse(other.end) : Infinity) && Date.parse(other.at) < to)) {
      setError("Это время пересекается с другим сном в дневнике. Уточните время или исправьте запись в трекере.");
      return;
    }
    if (record?.settlingAt && (Date.parse(record.settlingAt) > from || from - Date.parse(record.settlingAt) > 86400000)) {
      setError("Новое начало сна не согласуется с временем укладывания. Исправьте оба времени в трекере сна.");
      return;
    }
    setError("");
    const details: Partial<CareRecord> = sleep
      ? { sleepType: type === "night" ? "night" : type === "day" ? "day" : undefined }
      : type === "bottle" ? { side: "bottle", value: "Бутылочка" }
      : type === "other" ? { value: "Кормление" }
      : { side: type, value: "ГВ" };
    const sameMethod = type === (record?.side || "other");
    const value = mode === "ongoing" && !sleep ? "Таймер кормления" : mode === "point" && record?.value === "Таймер кормления" ? details.value : !sleep && record && (sameMethod || record.value === "Таймер кормления") ? record.value || details.value : details.value;
    void onSave({ ...record, id: record?.id || randomId(), kind, at: new Date(from).toISOString(), end: mode === "interval" ? new Date(to).toISOString() : undefined, note: record?.note || "", ...details, ...(!sleep ? { value, side: details.side || "" } : {}) });
  }

  return <form ref={form} className="chat-quick-care__manual" onSubmit={submit} aria-labelledby={id + "-title"}>
    <h3 id={id + "-title"} ref={heading} tabIndex={-1}>{title}</h3>
    <p id={id + "-help"}>Выберите часы и минуты прокруткой. Для ночного события можно отдельно выбрать день начала и окончания.</p>
    <div className="form-field">
      <label htmlFor={id + "-type"}>{sleep ? "Вид сна" : "Способ кормления"}</label>
      <select id={id + "-type"} value={type} disabled={disabled} onChange={(event) => setType(event.target.value)}>
        {sleep ? <>{record && <option value="">Не указан</option>}<option value="day">Дневной сон</option><option value="night">Ночной сон</option></>
          : <><option value="left">ГВ · левая грудь</option><option value="right">ГВ · правая грудь</option><option value="bottle">Бутылочка</option><option value="other">Другое кормление</option></>}
      </select>
    </div>
    {record && <div className="form-field">
      <label htmlFor={id + "-mode"}>Состояние записи</label>
      <select id={id + "-mode"} value={mode} disabled={disabled} onChange={(event) => { setMode(event.target.value); setError(""); }}>
        <option value="interval">Завершено · начало и окончание</option>
        <option value="ongoing">{sleep ? "Ещё спит · таймер работает" : "Кормление продолжается · таймер работает"}</option>
        {!sleep && <option value="point">Только время отметки · без длительности</option>}
      </select>
    </div>}
    <div className="chat-quick-care__times">
      <CareTimeField label="Начало" value={start} disabled={disabled} onChange={(value) => { setStart(value || ""); setError(""); }} />
      {mode === "interval" && <CareTimeField label="Окончание" value={end} disabled={disabled} onChange={(value) => { setEnd(value || ""); setError(""); }} />}
    </div>
    {error && <p id={id + "-error"} className="chat-quick-care__validation" role="alert">{error}</p>}
    <div className="chat-quick-care__form-actions">
      <Button type="submit" disabled={disabled}>{sleep ? "Сохранить сон" : "Сохранить кормление"}</Button>
      <Button type="button" variant="ghost" disabled={disabled} onClick={onClose}>Отмена</Button>
    </div>
  </form>;
}
