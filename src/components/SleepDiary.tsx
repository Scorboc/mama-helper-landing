import { useState } from "react";
import { Button } from "./ui/button";
import CareTimeField from "./CareTimeField";
import { careTime } from "@/lib/care-time";
import { Textarea } from "./ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "./ui/dialog";
import { randomId } from "@/lib/id";
import "./sleep-diary.css";
export type SleepRecord = {
  id: string;
  kind: string;
  at: string;
  end?: string;
  note: string;
  sleepType?: "day" | "night";
  wakeType?: "morning" | "night";
  settlingAt?: string;
  feeling?: string;
  value?: string;
  side?: string;
};
const duration = (n: number) =>
  `${Math.floor(Math.max(0, n) / 60)} ч ${Math.floor(Math.max(0, n) % 60)} мин`;
const name = (r: SleepRecord) =>
  r.kind === "wake"
    ? r.wakeType === "morning"
      ? "Утренний подъём"
      : "Ночное пробуждение"
    : r.sleepType === "day"
      ? "Дневной сон"
      : r.sleepType === "night"
        ? "Ночной сон"
        : "Сон";
export default function SleepDiary({
  records,
  now,
  busy,
  editable,
  mutate,
  childName,
  saveError,
  canDelete,
}: {
  records: SleepRecord[];
  now: number;
  busy: boolean;
  editable: boolean;
  mutate: (action: string, data: object) => Promise<boolean>;
  childName: string;
  saveError: string;
  canDelete: boolean;
}) {
  const [printing, setPrinting] = useState(false);
  const [editor, setEditor] = useState<SleepRecord | null>(null),
    [error, setError] = useState(""),
    [period, setPeriod] = useState(7),
    [questions, setQuestions] = useState("");
  const sleeps = records
    .filter((r) => r.kind === "sleep")
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at));
  const current = sleeps.find((r) => !r.end);
  const latestWake = records
    .filter((r) => r.kind === "wake")
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at))[0];
  const lastEnd = Math.max(
    0,
    ...sleeps.filter((r) => r.end).map((r) => Date.parse(r.end!)),
    latestWake ? Date.parse(latestWake.at) : 0,
  );
  const time = (v: string) =>
    new Date(v).toLocaleTimeString("ru-RU", {
      hour: "2-digit",
      minute: "2-digit",
    });
  const recent = records
    .filter(
      (r) =>
        ["sleep", "wake"].includes(r.kind) &&
        Date.parse(r.end || r.at) >= now - period * 86400000,
    )
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at));
  const days = Array.from({ length: period }, (_, i) => {
    const start = new Date(now);
    start.setHours(0, 0, 0, 0);
    start.setDate(start.getDate() - (period - 1 - i));
    const end = new Date(start);
    end.setDate(end.getDate() + 1);
    return { start: +start, end: +end };
  });
  const spans = (start: number, end: number) =>
    sleeps
      .map((r) => ({
        r,
        a: Math.max(start, Date.parse(r.at)),
        b: Math.min(end, now, Date.parse(r.end || new Date(now).toISOString())),
      }))
      .filter((x) => x.b > x.a);
  const minutes = (start: number, end: number) => {
    const list = spans(start, end).sort((a, b) => a.a - b.a);
    let total = 0,
      last = start;
    for (const x of list) {
      total += Math.max(0, x.b - Math.max(last, x.a));
      last = Math.max(last, x.b);
    }
    return Math.round(total / 60000);
  };
  async function put(record: SleepRecord) {
    return mutate("care-put", { record });
  }
  function edit(r?: SleepRecord) {
    setError("");
    setEditor(
      r
        ? { ...r }
        : {
            id: randomId(),
            kind: "sleep",
            at: new Date(now - 3600000).toISOString(),
            end: new Date(now).toISOString(),
            sleepType: "day",
            note: "",
          },
    );
  }
  async function save() {
    if (!editor) return;
    const a = Date.parse(editor.at),
      b = editor.end ? Date.parse(editor.end) : null,
      settle = editor.settlingAt ? Date.parse(editor.settlingAt) : null;
    if (
      !Number.isFinite(a) ||
      a > Date.now() ||
      (b !== null && (!Number.isFinite(b) || b <= a || b > Date.now())) ||
      (settle !== null && (!Number.isFinite(settle) || settle > a))
    ) {
      setError(
        "Проверьте время: засыпание после начала укладывания, пробуждение после засыпания. Будущее время недоступно.",
      );
      return;
    }
    if (await put(editor)) {
      setEditor(null);
      setError("");
    } else
      setError(
        "Запись не сохранена. Проверьте сообщение об ошибке в дневнике и пересечения сна.",
      );
  }
  async function wake(type: "morning" | "night") {
    if (current) {
      await put({ ...current, end: new Date().toISOString(), wakeType: type });
      return;
    }
    await put({
      id: randomId(),
      kind: "wake",
      at: new Date().toISOString(),
      wakeType: type,
      note: "",
    });
  }
  function printReport() {
    setPrinting(true);
  }

  return (
    <section className="sleep-diary" aria-label="Дневник сна">
      <div className="sleep-hero">
        <span className="sleep-eyebrow">СОН · {childName}</span>
        <h3>
          {current
            ? "Сейчас спит"
            : lastEnd
              ? "После последнего пробуждения"
              : "Начнём с первого наблюдения"}
        </h3>
        <strong className="sleep-clock">
          {current
            ? duration((now - Date.parse(current.at)) / 60000)
            : lastEnd
              ? duration((now - lastEnd) / 60000)
              : "—"}
        </strong>
        <p>
          {current
            ? `Уснул в ${time(current.at)}`
            : lastEnd
              ? "Если пропустили сон, добавьте его — счётчик опирается на записи."
              : "Отметьте пробуждение или начало сна."}
        </p>
        <div className="sleep-actions">
          {current ? (
            <Button
              disabled={busy || !editable}
              onClick={() =>
                void put({ ...current, end: new Date().toISOString() })
              }
            >
              Проснулся
            </Button>
          ) : (
            <>
              <Button
                disabled={busy || !editable}
                onClick={() =>
                  void put({
                    id: randomId(),
                    kind: "sleep",
                    sleepType: "day",
                    at: new Date().toISOString(),
                    note: "",
                  })
                }
              >
                Начать дневной сон
              </Button>
              <Button
                variant="outline"
                disabled={busy || !editable}
                onClick={() =>
                  void put({
                    id: randomId(),
                    kind: "sleep",
                    sleepType: "night",
                    at: new Date().toISOString(),
                    note: "",
                  })
                }
              >
                Начать ночной сон
              </Button>
            </>
          )}
        </div>
        {
          <div className="sleep-actions">
            <Button
              variant="outline"
              disabled={busy || !editable}
              onClick={() => void wake("morning")}
            >
              Утренний подъём
            </Button>
            <Button
              variant="outline"
              disabled={busy || !editable}
              onClick={() => void wake("night")}
            >
              Ночное пробуждение
            </Button>
          </div>
        }
        <Button
          variant="ghost"
          disabled={busy || !editable}
          onClick={() => edit()}
        >
          Добавить прошедший сон
        </Button>
        <p className="muted">
          Таймер сохраняется после закрытия сайта. Ночное пробуждение завершает
          текущий эпизод: следующий сон отметьте снова.
        </p>
      </div>
      <div className="sleep-section">
        <h3>История сна</h3>
        <label>
          Период{" "}
          <select
            aria-label="Период дневника сна"
            value={period}
            onChange={(e) => setPeriod(Number(e.target.value))}
          >
            {[7, 14, 30].map((n) => (
              <option key={n} value={n}>
                {n} дней
              </option>
            ))}
          </select>
        </label>
        <p className="muted">
          Время устройства: {Intl.DateTimeFormat().resolvedOptions().timeZone}.
          Зелёный — дневной, янтарный — ночной, серый — сон без отметки.
          Пустые участки — нет записей.
        </p>
        <div className="sleep-scale">
          <span>00</span>
          <span>06</span>
          <span>12</span>
          <span>18</span>
          <span>24</span>
        </div>
        {days.map((d) => (
          <div className="sleep-day" key={d.start}>
            <span>
              {new Date(d.start).toLocaleDateString("ru-RU", {
                day: "numeric",
                month: "numeric",
              })}
            </span>
            <div
              className="sleep-lane"
              role="img"
              aria-label={`${new Date(d.start).toLocaleDateString("ru-RU")}: ${duration(minutes(d.start, d.end))}`}
            >
              {spans(d.start, d.end).map((x) => (
                <span
                  key={x.r.id}
                  className={`sleep-span ${x.r.sleepType || "unknown"}`}
                  title={`${name(x.r)} ${time(x.r.at)}–${x.r.end ? time(x.r.end) : "сейчас"}`}
                  style={{
                    left: `${((x.a - d.start) / (d.end - d.start)) * 100}%`,
                    width: `${((x.b - x.a) / (d.end - d.start)) * 100}%`,
                  }}
                />
              ))}
            </div>
            <small>{duration(minutes(d.start, d.end))}</small>
          </div>
        ))}
        <p>
          ИИ в чате получает записи активного ребёнка за последнюю неделю и
          рассчитанную сводку. Неполный дневник не позволяет определить точный
          режим или причину трудностей.
        </p>
      </div>
      <details className="sleep-section">
        <summary>Записи и исправления · {recent.length}</summary>
        {recent.map((r) => (
          <article className="sleep-record" key={r.id}>
            <div>
              <strong>{name(r)}</strong>
              <p>
                {careTime(r.at)}
                {r.end
                  ? ` → ${careTime(r.end)} · ${duration((Date.parse(r.end) - Date.parse(r.at)) / 60000)}`
                  : ""}
              </p>
              {r.settlingAt && <p>Укладывание: {time(r.settlingAt)}</p>}
              <p>{r.note}</p>
            </div>
            <div>
              <Button
                variant="outline"
                disabled={busy || !editable}
                onClick={() => edit(r)}
              >
                Исправить
              </Button>
              {canDelete && (
                <Button
                  variant="ghost"
                  disabled={busy}
                  onClick={() => {
                    if (
                      window.confirm("Удалить эту запись сна или пробуждения?")
                    )
                      void mutate("care-delete", { id: r.id });
                  }}
                >
                  Удалить
                </Button>
              )}
            </div>
          </article>
        ))}
      </details>
      <details className="sleep-section">
        <summary>Сводка специалисту</summary>
        <label>
          Ваши вопросы
          <Textarea
            value={questions}
            maxLength={1000}
            onChange={(e) => setQuestions(e.target.value)}
          />
        </label>
        <Button variant="outline" onClick={printReport}>
          Открыть сводку для PDF
        </Button>
        <p className="muted">
          В предпросмотре выберите «Печать / Сохранить как PDF». В документ
          попадут диаграмма, эпизоды и ваши вопросы, без переписки.
        </p>
      </details>
      {error && !editor && <p role="alert">{error}</p>}
      <Dialog open={printing} onOpenChange={setPrinting}>
        <DialogContent className="sleep-print-sheet max-w-4xl" aria-describedby="sleep-report-description">
          <DialogHeader>
            <DialogTitle>Дневник сна · {childName}</DialogTitle>
            <DialogDescription id="sleep-report-description">Сводка записей родителя для печати или сохранения в PDF.</DialogDescription>
          </DialogHeader>
            <div className="sleep-print-actions">
              <Button onClick={() => window.print()}>
                Печать / Сохранить как PDF
              </Button>
              <Button variant="outline" onClick={() => setPrinting(false)}>
                Закрыть сводку
              </Button>
            </div>
            <h2>Дневник сна · {childName}</h2>
            <p>
              Последние {period} дней ·{" "}
              {Intl.DateTimeFormat().resolvedOptions().timeZone}
            </p>
            <p>
              Отмеченные эпизоды сна. Пустые участки — нет записей, не
              подтверждённое бодрствование.
            </p>
            {days.map((d) => (
              <div className="sleep-day" key={d.start}>
                <span>
                  {new Date(d.start).toLocaleDateString("ru-RU", {
                    day: "numeric",
                    month: "numeric",
                  })}
                </span>
                <div className="sleep-lane">
                  {spans(d.start, d.end).map((x) => (
                    <span
                      key={x.r.id}
                      className={`sleep-span ${x.r.sleepType || "unknown"}`}
                      style={{
                        left: `${((x.a - d.start) / (d.end - d.start)) * 100}%`,
                        width: `${((x.b - x.a) / (d.end - d.start)) * 100}%`,
                      }}
                    />
                  ))}
                </div>
                <small>{duration(minutes(d.start, d.end))}</small>
              </div>
            ))}
            <div className="sleep-report-table">
              <table>
                <thead>
                  <tr>
                    <th>Событие</th>
                    <th>Начало</th>
                    <th>Окончание</th>
                    <th>Наблюдения</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((r) => (
                    <tr key={r.id}>
                      <td>{name(r)}</td>
                      <td>{new Date(r.at).toLocaleString("ru-RU")}</td>
                      <td>
                        {r.end ? new Date(r.end).toLocaleString("ru-RU") : "—"}
                        {r.end && (
                          <p>
                            {duration(
                              (Date.parse(r.end) - Date.parse(r.at)) / 60000,
                            )}
                          </p>
                        )}
                      </td>
                      <td>
                        {r.note}
                        {r.settlingAt && (
                          <p>Укладывание: {time(r.settlingAt)}</p>
                        )}
                        {r.feeling && (
                          <p>
                            {
                              {
                                calm: "Спокойно",
                                fussy: "Беспокойно",
                                crying: "Плакал",
                              }[r.feeling]
                            }
                          </p>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <h2>Вопросы специалисту</h2>
            <p style={{ whiteSpace: "pre-wrap" }}>
              {questions || "Не добавлены"}
            </p>
            <p>
              Записи родителя, не медицинское заключение. Переписка не включена.
            </p>
        </DialogContent>
      </Dialog>
      <Dialog
        open={!!editor}
        onOpenChange={(v) => {
          if (!busy && !v) setEditor(null);
        }}
      >
        <DialogContent className="ios-sheet">
          <DialogHeader>
            <DialogTitle>Запись сна и пробуждения</DialogTitle>
            <DialogDescription>
              Исправьте время или добавьте наблюдение. Записи другого ребёнка не
              изменяются.
            </DialogDescription>
          </DialogHeader>
          {editor && (
            <div className="sleep-edit">
              <CareTimeField label={editor.kind === "sleep" ? "Уснул" : "Проснулся"} value={editor.at} disabled={busy} onChange={(value) => { if (value) setEditor({ ...editor, at: value }); }} />
              {editor.kind === "sleep" && (
                <>
                  <label>
                    Вид сна
                    <select
                      value={editor.sleepType || ""}
                      onChange={(e) =>
                        setEditor({
                          ...editor,
                          sleepType: e.target.value as "day" | "night",
                        })
                      }
                    >
                      <option value="">Не указан</option>
                      <option value="day">Дневной</option>
                      <option value="night">Ночной</option>
                    </select>
                  </label>
                  <CareTimeField label="Проснулся" value={editor.end} optional disabled={busy} emptyLabel="Ещё спит · таймер работает" onChange={(value) => setEditor({ ...editor, end: value })} />
                  <CareTimeField label="Начали укладывать · необязательно" value={editor.settlingAt} optional disabled={busy} onChange={(value) => setEditor({ ...editor, settlingAt: value })} />
                  <label>
                    Перед сном
                    <select
                      value={editor.feeling || ""}
                      onChange={(e) =>
                        setEditor({ ...editor, feeling: e.target.value })
                      }
                    >
                      <option value="">Не отмечено</option>
                      <option value="calm">Спокойно</option>
                      <option value="fussy">Беспокойно</option>
                      <option value="crying">Плакал</option>
                    </select>
                  </label>
                </>
              )}
              <label>
                Наблюдение
                <Textarea
                  value={editor.note}
                  maxLength={500}
                  onChange={(e) =>
                    setEditor({ ...editor, note: e.target.value })
                  }
                />
              </label>
              {(error || saveError) && <p role="alert">{saveError || error}</p>}
              <Button disabled={busy || !editable} onClick={() => void save()}>
                Сохранить
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </section>
  );
}
