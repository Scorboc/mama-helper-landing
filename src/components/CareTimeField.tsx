import { useEffect, useId, useRef, useState } from "react";
import { Button } from "./ui/button";
import { careDay, careTime } from "@/lib/care-time";
import "./care-time.css";

const ROW = 44;
function Wheel({ label, value, count, disabled, onChange }: { label: string; value: number; count: number; disabled: boolean; onChange: (value: number) => void }) {
  const list = useRef<HTMLDivElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => {
    if (list.current && Math.abs(list.current.scrollTop - value * ROW) > 1) list.current.scrollTop = value * ROW;
  }, [value]);
  useEffect(() => () => clearTimeout(timer.current), []);
  function choose(next: number) {
    if (disabled) return;
    clearTimeout(timer.current);
    const number = (next + count) % count;
    if (list.current) list.current.scrollTop = number * ROW;
    onChange(number);
  }
  return <div ref={list} className="care-wheel" role="spinbutton" tabIndex={disabled ? -1 : 0}
    aria-label={label} aria-valuemin={0} aria-valuemax={count - 1} aria-valuenow={value} aria-valuetext={String(value).padStart(2, "0")} aria-disabled={disabled}
    onKeyDown={(event) => {
      const next = event.key === "ArrowUp" ? value + 1 : event.key === "ArrowDown" ? value - 1 : event.key === "Home" ? 0 : event.key === "End" ? count - 1 : null;
      if (next !== null) { event.preventDefault(); choose(next); }
    }}
    onScroll={() => {
      clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        if (list.current && !disabled) onChange(Math.max(0, Math.min(count - 1, Math.round(list.current.scrollTop / ROW))));
      }, 100);
    }}>
    {Array.from({ length: count }, (_, number) => <div key={number} aria-hidden="true" className={number === value ? "care-wheel__number selected" : "care-wheel__number"} onClick={() => choose(number)}>{String(number).padStart(2, "0")}</div>)}
  </div>;
}

export default function CareTimeField({ label, value, disabled = false, onChange, optional = false, emptyLabel = "Выбрать время" }: {
  label: string; value?: string; disabled?: boolean; onChange: (value: string | undefined) => void; optional?: boolean; emptyLabel?: string;
}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(new Date());
  const trigger = useRef<HTMLButtonElement>(null);
  const hours = useRef<HTMLDivElement>(null);
  const picker = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (open) {
      hours.current?.querySelector<HTMLElement>("[role=spinbutton]")?.focus({ preventScroll: true });
      picker.current?.scrollIntoView({ block: "nearest" });
    }
  }, [open]);
  function update(unit: "hour" | "minute", value: number) {
    // Scrolling either column must not overwrite a newer change in the other.
    setDraft((previous) => {
      const next = new Date(previous); next.setHours(unit === "hour" ? value : previous.getHours(), unit === "minute" ? value : previous.getMinutes(), 0, 0); return next;
    });
  }
  function moveDay(offset: number) {
    const next = new Date(draft); next.setDate(next.getDate() + offset); setDraft(next);
  }
  function selectDay(offset: number) {
    const next = new Date(); next.setDate(next.getDate() - offset); next.setHours(draft.getHours(), draft.getMinutes(), 0, 0); setDraft(next);
  }
  function close() { setOpen(false); trigger.current?.focus({ preventScroll: true }); }
  return <div className="care-time-field">
    <span id={id + "-label"}>{label}</span>
    <Button ref={trigger} type="button" variant="outline" disabled={disabled} aria-labelledby={id + "-label " + id + "-value"} aria-expanded={open} aria-controls={id + "-picker"}
      onClick={() => { setDraft(value ? new Date(value) : new Date()); setOpen(!open); }}><span id={id + "-value"}>{value ? careTime(value) : emptyLabel}</span></Button>
    {open && <div ref={picker} id={id + "-picker"} className="care-time-picker" role="group" aria-label={label + ": выбрать время"}>
      <div className="care-time-picker__day">
        <Button type="button" variant="ghost" disabled={disabled} onClick={() => selectDay(0)}>Сегодня</Button>
        <Button type="button" variant="ghost" disabled={disabled} onClick={() => selectDay(1)}>Вчера</Button>
      </div>
      <div className="care-time-picker__date">
        <Button type="button" variant="ghost" disabled={disabled} aria-label={label + ": предыдущий день"} onClick={() => moveDay(-1)}>−1 день</Button>
        <span aria-live="polite">{careDay(draft.toISOString())}</span>
        <Button type="button" variant="ghost" disabled={disabled || new Date(draft).setHours(0, 0, 0, 0) >= new Date().setHours(0, 0, 0, 0)} aria-label={label + ": следующий день"} onClick={() => moveDay(1)}>+1 день</Button>
      </div>
      <div ref={hours} className="care-time-picker__wheels">
        <Wheel label={label + ": часы"} value={draft.getHours()} count={24} disabled={disabled} onChange={(hour) => update("hour", hour)} />
        <span aria-hidden="true">:</span>
        <Wheel label={label + ": минуты"} value={draft.getMinutes()} count={60} disabled={disabled} onChange={(minute) => update("minute", minute)} />
      </div>
      <p>Прокрутите часы и минуты. Можно использовать стрелки на клавиатуре.</p>
      <div className="care-time-picker__footer">
        <Button type="button" disabled={disabled} onClick={() => {
          // Read the final scroll position even if the last scroll event has not settled.
          const wheels = hours.current?.querySelectorAll<HTMLElement>("[role=spinbutton]");
          const chosen = new Date(draft);
          if (wheels?.length === 2) chosen.setHours(Math.max(0, Math.min(23, Math.round(wheels[0].scrollTop / ROW))), Math.max(0, Math.min(59, Math.round(wheels[1].scrollTop / ROW))), 0, 0);
          onChange(chosen.toISOString()); close();
        }}>Готово</Button>
        <Button type="button" variant="ghost" disabled={disabled} onClick={close}>Отменить выбор</Button>
        {optional && value && <Button type="button" variant="ghost" disabled={disabled} onClick={() => { onChange(undefined); close(); }}>Убрать время</Button>}
      </div>
    </div>}
  </div>;
}
