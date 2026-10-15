import type { CareSummary, CareRecord } from '@/lib/care-journal';
import { ruCount } from '@/lib/ru-count';

export default function CareWeek({ summary, records, timezone, authors = {} }: { summary?: CareSummary; records: CareRecord[]; timezone: string; authors?: Record<string,{createdByRole:string;updatedByRole:string;updatedAt:string}> }) {
  if (!summary) return null;
  const latest = (kind: string) => records.filter(r => r.kind === kind).sort((a,b) => Date.parse(b.at)-Date.parse(a.at))[0];
  const sleep = latest('sleep'), feeding = latest('feeding');
  const stamp = (at: string) => new Date(at).toLocaleString('ru-RU', { timeZone: summary.timezone || timezone, dateStyle:'short', timeStyle:'short' });
  return <details className="sleep-section care-week">
    <summary>Моя неделя и передача ухода</summary>
    <h3>Что записано</h3>
    <p>{summary.periodStart} — {new Date(summary.periodEnd).toLocaleDateString('ru-RU', {timeZone:summary.timezone || timezone})} · {summary.timezone}</p>
    <p>{ruCount(summary.records,'отметка','отметки','отметок')} в {summary.recordedDays} из {summary.periodDays} дней. Кормлений: {summary.feeding.records}; эпизодов сна: {summary.sleep.sleepRecords}.</p>
    <h3>Что видно из записей</h3>
    <p>{summary.records ? 'Здесь показаны только отмеченные события. Полнота дневника неизвестна: по пропускам нельзя судить о режиме или достаточности питания.' : 'Пока нет отметок за эту неделю. Это отсутствие данных, а не отсутствие сна или кормлений.'}</p>
    <h3>Один вариант следующего шага</h3>
    <p>Если хотите разобраться в конкретном вопросе, отмечайте относящиеся к нему события в удобном объёме. Не нужно вести всё сразу.</p>
    <h3>Другому взрослому</h3>
    <p>{sleep ? `Последний сон: ${stamp(sleep.at)}. ${sleep.end ? `Окончание: ${stamp(sleep.end)}.` : 'Окончание ещё не отмечено.'}` : 'Сон пока не записан.'}</p>
    <p>{feeding ? `Последнее отмеченное кормление: ${stamp(feeding.at)}.` : 'Кормление пока не записано.'}</p>
    {[sleep,feeding].filter(Boolean).map(r => r && <p key={r.id} className="muted">{authors[r.id] ? `Записал: ${authors[r.id].createdByRole}. Последнее сохранение: ${authors[r.id].updatedByRole}, ${stamp(authors[r.id].updatedAt)}.` : 'Автор прежней отметки не сохранялся.'}</p>)}
    <p className="muted">Обновляется после сохранения, исправления и удаления. Передача доступа — в разделе «Семья»; личная переписка и самочувствие родителя остаются закрытыми.</p>
  </details>;
}
