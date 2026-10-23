export type BookRecord = {
    id: string;
    kind: string;
    at: string;
    skill?: string;
    value?: string;
    note?: string;
};
export type OldMoment = {
    id?: string;
    kind?: string;
    date: string;
    note?: string;
};
export type Moment = {
    id: string;
    day: string;
    text: string;
    note: string;
    month: number | null;
    age: string;
    sources: string[];
};
const labels: Record<string, string> = { roll: 'Переворачивается', crawl: 'Ползает', stand: 'Встаёт у опоры', walk: 'Ходит', words: 'Первые слова' };
const skillLabel = (key: string) => Object.prototype.hasOwnProperty.call(labels, key) ? labels[key] : '';
export function validDay(day: string) {
    return /^\d{4}-\d{2}-\d{2}$/.test(day) && Number.isFinite(Date.parse(day + 'T00:00:00Z')) && new Date(day + 'T00:00:00Z').toISOString().slice(0, 10) === day;
}
export function formatBookDay(day: string, short = false) {
    if (!validDay(day)) return '';
    const months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
    return `${Number(day.slice(8))} ${months[Number(day.slice(5, 7)) - 1]}${short ? '' : ' ' + day.slice(0, 4)}`;
}
export function familyDay(value: number | string, zone: string) {
    const p = new Intl.DateTimeFormat('en-CA', { timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date(value));
    return ['year', 'month', 'day'].map(k => p.find(v => v.type === k)?.value).join('-');
}
export function anniversary(birth: string, months: number) {
    const [y, m, d] = birth.split('-').map(Number), first = new Date(Date.UTC(y, m - 1 + months, 1));
    const last = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate();
    return new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth(), Math.min(d, last))).toISOString().slice(0, 10);
}
export function lifeAge(birth: string, day: string) {
    if (!validDay(birth) || !validDay(day) || day < birth)
        return null;
    let months = (+day.slice(0, 4) - +birth.slice(0, 4)) * 12 + (+day.slice(5, 7) - +birth.slice(5, 7));
    if (day < anniversary(birth, months))
        months--;
    const days = Math.round((Date.parse(day) - Date.parse(anniversary(birth, months))) / 86400000);
    return { months, days, label: `${months} мес. ${days} дн.` };
}
export function memoryInstant(day: string, zone: string, now = Date.now()) {
    if (!validDay(day) || day > familyDay(now, zone))
        throw new Error('Проверьте дату воспоминания.');
    if (day === familyDay(now, zone))
        return new Date(now).toISOString();
    let t = Date.parse(day + 'T12:00:00Z');
    for (let i = 0; i < 48 && familyDay(t, zone) !== day; i++)
        t += familyDay(t, zone) > day ? -3600000 : 3600000;
    if (familyDay(t, zone) !== day)
        throw new Error('Эта дата недоступна в часовом поясе семьи.');
    return new Date(t).toISOString();
}
export function bookMoments(records: BookRecord[], legacy: OldMoment[], birth = '', zone = 'Europe/Moscow', now = Date.now()): Moment[] {
    const today = familyDay(now, zone), known = validDay(birth), seen = new Map<string, Moment>();
    const rows = [...records.filter(r => r.kind === 'achievement').flatMap(r => {
            if (typeof r.at !== 'string' || !/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.test(r.at) || !validDay(r.at.slice(0, 10)) || !Number.isFinite(Date.parse(r.at)) || Date.parse(r.at) > now)
                return [];
            return [{ id: 'care:' + r.id, day: familyDay(r.at, zone), text: skillLabel(r.skill || '') || r.value || '', note: r.note || '' }];
        }), ...legacy.map((r, i) => ({ id: 'legacy:' + (r.id || i), day: r.date, text: skillLabel(r.kind || ''), note: r.note || '' }))];
    for (const r of rows) {
        if (!validDay(r.day) || r.day > today || (known && (r.day < birth || r.day >= anniversary(birth, 12))))
            continue;
        const text = r.text.trim(), note = r.note.trim();
        if (!text && !note)
            continue;
        const key = JSON.stringify([r.day, text.normalize('NFC'), note.normalize('NFC')]);
        const old = seen.get(key);
        if (old) {
            old.sources.push(r.id);
            continue;
        }
        const age = known ? lifeAge(birth, r.day) : null;
        seen.set(key, { ...r, text, note, month: age?.months ?? null, age: age?.label || '', sources: [r.id] });
    }
    return [...seen.values()].sort((a, b) => a.day.localeCompare(b.day) || a.id.localeCompare(b.id));
}
export function bookMonths(moments: Moment[]) { return [...new Set(moments.map(m => m.month))]; }
export function monthTitle(month: number | null) { return month === null ? 'Сохранённые воспоминания' : `${month + 1}-й месяц жизни`; }
