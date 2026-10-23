import type { CareRecord } from './care-journal';
export function quickFromSearch(search: string): 'sleep' | 'feed' | 'note' | null {
 const p = new URLSearchParams(search), value = p.get('quick');
 return p.getAll('quick').length === 1 && (value === 'sleep' || value === 'feed' || value === 'note') ? value : null;
}
export function elapsedLabel(minutes: number) {
 const n = Math.max(0, Math.floor(minutes));
 return n >= 60 ? `${Math.floor(n / 60)} ч${n % 60 ? ` ${n % 60} мин` : ''}` : `${n} мин`;
}
export function latestCare(records: CareRecord[], now: number, childSex: 'female' | 'male' | 'unknown' = 'unknown') {
 const valid = records.filter(r => Number.isFinite(Date.parse(r.at)) && Date.parse(r.at) <= now).sort((a,b) => Date.parse(b.at)-Date.parse(a.at));
 const feed = valid.find(r => r.kind === 'feeding');
 const sleep = valid.filter(r => r.kind === 'sleep' || r.kind === 'wake').map(r => ({r, at: Date.parse(r.end || r.at)})).filter(x => x.at <= now).sort((a,b) => b.at-a.at)[0];
 const ago = (at: string) => elapsedLabel((now-Date.parse(at))/60000);
 const side = {left:'левая',right:'правая',bottle:'бутылочка'};
 return [feed ? `Кормление ${ago(feed.at)} назад${side[feed.side as keyof typeof side] ? ' · '+side[feed.side as keyof typeof side] : ''}` : '', sleep ? sleep.r.kind === 'sleep' && !sleep.r.end ? `Сон: спит ${ago(sleep.r.at)}` : `Сон: ${childSex === 'female' ? 'проснулась' : childSex === 'male' ? 'проснулся' : 'сон закончился'} ${ago(sleep.r.end || sleep.r.at)} назад` : ''].filter(Boolean).join(' · ');
}
export function recordQuestionContext(record: CareRecord, timezone = 'Europe/Moscow') {
 const date = new Date(record.at).toLocaleDateString('ru-RU', {timeZone: timezone, day:'numeric',month:'long'});
 const time = (value: string) => new Date(value).toLocaleTimeString('ru-RU', {timeZone: timezone,hour:'2-digit',minute:'2-digit'});
 const label = record.kind === 'sleep' ? record.sleepType === 'day' ? 'Дневной сон' : record.sleepType === 'night' ? 'Ночной сон' : 'Сон' : record.kind === 'feeding' ? 'Кормление' : record.value || 'Запись';
 const sides: Record<string,string> = {left:'левая',right:'правая',bottle:'бутылочка'};
 const side = sides[record.side || ''];
 return `${label} ${date}, ${time(record.at)}${record.end ? '–'+time(record.end) : ''}${side ? ', '+side : ''} — `;
}
export function hasQuestionBeyondContext(text: string, context: string) {
 const value = text.trim();
 const words = (s: string) => s.toLocaleLowerCase('ru').replace(/[^\p{L}\p{N}]/gu,'');
 return !!value && words(value) !== words(context) && /[\p{L}\p{N}]/u.test(value.startsWith(context.trim()) ? value.slice(context.trim().length) : value);
}
export const libraryHasNoMatches = (total: number, filtered: number, hasFilters: boolean) => total > 0 && filtered === 0 && hasFilters;
export const resetLibraryFilters = () => ({query:'',category:'all',child:'all'});
export function questionKey(text: string) { return text.trim().replace(/\s+/g,' ').toLocaleLowerCase('ru'); }
export function canAddQuestion(questions: string[], text: string) { return !!text.trim() && text.trim().length <= 500 && questions.length < 30 && !questions.some(q => questionKey(q) === questionKey(text)); }
