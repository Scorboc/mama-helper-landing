import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { api } from '@/lib/parent-api';
import { randomId } from '@/lib/id';
import { formatBookDay, anniversary, bookMoments, bookMonths, familyDay, memoryInstant, monthTitle, validDay, type BookRecord, type OldMoment, type Moment } from '@/lib/first-year-book';
import { renderPostcard } from '@/lib/book-postcard';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import './first-year-book.css';
type Listing = {
    summary?: { timezone: string };
    records: BookRecord[];
    achievements: OldMoment[];
    permission: string;
    profile: {
        stage: string;
        childName: string;
        birthDate: string;
    };
};
export default function FirstYearBook({ context, zone: fallbackZone, startAdding = false }: {
    context: {
        childId: string;
        ownerId?: string;
    };
    zone: string;
    startAdding?: boolean;
}) {
    const [data, setData] = useState<Listing>(), [error, setError] = useState(''), [busy, setBusy] = useState(false), [month, setMonth] = useState('all'), [adding, setAdding] = useState(startAdding), [card, setCard] = useState(false), [printing, setPrinting] = useState(false);
    const [saved, setSaved] = useState(false);
    const [saveError, setSaveError] = useState('');
    const [retry, setRetry] = useState(0);
    const zone = data?.summary?.timezone || fallbackZone;
    const [note, setNote] = useState(''), [day, setDay] = useState(familyDay(Date.now(), fallbackZone));
    const alive = useRef(false), lock = useRef(false), saveId = useRef(randomId()), pending = useRef<{
        id: string;
        kind: string;
        at: string;
        note: string;
    }>(), loadId = useRef(0);
    useEffect(() => {
        alive.current = true;
        let cancelled = false;
        async function load() { const ticket = ++loadId.current; try {
            const r = await api<Listing>('care-list', context);
            if (!cancelled && alive.current && ticket === loadId.current) {
                setData(r);
                setError('');
            }
        }
        catch (e) {
            if (!cancelled && alive.current && ticket === loadId.current)
                setError((e as { status?: number }).status === 429 ? 'Слишком много обновлений, попробуйте через минуту' : 'Не удалось открыть книгу. Попробуйте открыть её снова.');
        } }
        void load();
        window.addEventListener('care-records-changed', load);
        return () => { cancelled = true; alive.current = false; window.removeEventListener('care-records-changed', load); }; // Context values define the request scope; the parent remounts on a scope change.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [context.childId, context.ownerId, retry]);
    const moments = data ? bookMoments(data.records, data.achievements, data.profile.birthDate, zone) : [], months = bookMonths(moments), own = data?.permission === 'owner';
    const list = (items: Moment[]) => <ol>{items.map(m => <li key={m.id}><time dateTime={m.day}>{formatBookDay(m.day)}</time>{m.age && <> · {m.age}</>}<p>{[m.text, m.note].filter(Boolean).join(' — ')}</p></li>)}</ol>;
    const sections = <>{months.map(n => <section key={String(n)} className="book-month"><h3>{monthTitle(n)}</h3>{list(moments.filter(m => m.month === n))}</section>)}</>;
    return <section className="first-year-book space-y-4"><h2>Книга первого года</h2>{saved && <p role="status">Сохранено</p>}{error && <><p role="alert">{error}</p><Button variant="outline" onClick={() => setRetry(n => n + 1)}>Попробовать снова</Button></>}{!data ? (!error && <p role="status">Открываем воспоминания…</p>) : data.profile.stage !== 'child' ? <p>Книга появится после рождения ребёнка и обновления профиля.</p> : <>
 <p>Выбранный ребёнок: {data.profile.childName || 'Ребёнок'}</p><p>Моменты, которые хочется сохранить.</p>
 {!validDay(data.profile.birthDate) && <p>Чтобы распределить воспоминания по месяцам жизни, укажите дату рождения в профиле. Сейчас показаны даты записей.</p>}
 <div className="flex flex-wrap gap-2"><Button disabled={data.permission === 'read'} onClick={() => {setDay(familyDay(Date.now(),zone));pending.current=undefined;saveId.current=randomId();setSaveError('');setAdding(true);}}>Добавить воспоминание</Button>{own && <Button variant="outline" onClick={() => setPrinting(true)}>Печать / PDF</Button>}</div>
 {!!months.length && <label className="form-field">Месяц жизни<select value={month} onChange={e => setMonth(e.target.value)}><option value="all">Все воспоминания</option>{months.map(n => <option key={String(n)} value={String(n)}>{monthTitle(n)}</option>)}</select></label>}
 {!moments.length && <p>Здесь появятся сохранённые воспоминания первого года.</p>}
 {months.filter(n => month === 'all' || String(n) === month).map(n => <section key={String(n)} className="book-month"><h3>{monthTitle(n)}</h3>{list(moments.filter(m => m.month === n))}{own && n !== null && <Button variant="outline" onClick={() => { setMonth(String(n)); setCard(true); }}>Собрать открытку месяца</Button>}</section>)}
 {own && card && <Postcard key={month} name={data.profile.childName} title={monthTitle(Number(month))} moments={moments.filter(m => String(m.month) === month)} onClose={() => setCard(false)}/>}
 <Dialog open={adding} onOpenChange={v => { if (!busy)
            setAdding(v); }}><DialogContent className="book-dialog"><DialogHeader><DialogTitle>Добавить воспоминание</DialogTitle><DialogDescription>Запишите то, что хочется запомнить, своими словами.</DialogDescription></DialogHeader><form className="space-y-4" onSubmit={async (e) => { e.preventDefault(); if (lock.current)
            return; lock.current = true; setBusy(true); setSaveError(''); try {
            if (!pending.current) {
                if (validDay(data.profile.birthDate) && (day < data.profile.birthDate || day >= anniversary(data.profile.birthDate, 12)))
                    throw new Error('Выберите дату первого года жизни.');
                pending.current = { id: saveId.current, kind: 'achievement', at: memoryInstant(day, zone), note: note.trim() };
            }
            await api('care-put', { ...context, record: pending.current });
            if (alive.current) {
                setAdding(false);
                setMonth('all');
                setSaved(true);
                setNote('');
                saveId.current = randomId();
                pending.current = undefined;
                window.dispatchEvent(new Event('care-records-changed'));
            }
        }
        catch (e) {
            if (alive.current)
                setSaveError((e as Error).message || 'Сохранение не подтверждено. Попробуйте ещё раз.');
        }
        finally {
            lock.current = false;
            if (alive.current)
                setBusy(false);
        } }}>
 <label className="form-field">Что хочется запомнить · до 500 символов<Textarea disabled={busy} required maxLength={500} value={note} onChange={e => { setNote(e.target.value); pending.current = undefined; saveId.current = randomId(); }}/></label><label className="form-field">Дата<Input disabled={busy} type="date" required min={data.profile.birthDate || undefined} max={familyDay(Date.now(), zone)} value={day} onChange={e => { setDay(e.target.value); pending.current = undefined; saveId.current = randomId(); }}/></label>{saveError && <p role="alert">{saveError}</p>}<Button disabled={busy || !note.trim()}>Сохранить</Button><Button type="button" variant="outline" disabled={busy} onClick={() => setAdding(false)}>Отмена</Button></form></DialogContent></Dialog>
 {own && printing && <PrintBook name={data.profile.childName} onClose={() => setPrinting(false)}>{sections}</PrintBook>}
 </>}</section>;
}
function Postcard({ name, title, moments, onClose }: {
    name: string;
    title: string;
    moments: Moment[];
    onClose: () => void;
}) {
    const [chosen, setChosen] = useState<string[]>(() => moments.map(m => m.id)), [caption, setCaption] = useState(''), [photo, setPhoto] = useState<File>(), [showName, setShowName] = useState(true), [dates, setDates] = useState(true), [brand, setBrand] = useState(() => { try {
        return localStorage.getItem('mh_book_brand') !== 'off';
    }
    catch {
        return true;
    } }), [blob, setBlob] = useState<Blob>(), [url, setUrl] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState('');
    const alive = useRef(true);
    useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
    useEffect(() => { if (!blob) {
        setUrl('');
        return;
    } const u = URL.createObjectURL(blob); setUrl(u); return () => URL.revokeObjectURL(u); }, [blob]);
    const file = blob ? new File([blob], 'Воспоминания.png', { type: 'image/png' }) : null;
    const share = !!file && typeof navigator.canShare === 'function' && navigator.canShare({ files: [file] });
    return <Dialog open onOpenChange={v => { if (!v)
        onClose(); }}><DialogContent className="book-dialog first-year-book"><DialogHeader><DialogTitle>{blob ? 'Предпросмотр открытки' : 'Собрать открытку месяца'}</DialogTitle><DialogDescription>Фото остаётся в памяти вкладки только на время сборки. После закрытия выберите его заново.</DialogDescription></DialogHeader>{blob ? <><img src={url} alt="Предпросмотр выбранных воспоминаний" className="w-full"/>{share && <Button onClick={async () => { try {
            await navigator.share({ files: [file!] });
        }
        catch (e) {
            if ((e as Error).name !== 'AbortError')
                setError('Не удалось поделиться. Можно сохранить картинку.');
        } }}>Поделиться</Button>}<Button onClick={() => { const a = document.createElement('a'); a.href = url; a.download = 'Воспоминания.png'; a.click(); }}>Сохранить картинку</Button><Button variant="outline" onClick={() => setBlob(undefined)}>Вернуться к сборке</Button></> : <>
 <fieldset><legend>Моменты для открытки</legend>{moments.map(m => <label key={m.id} className="book-check"><input type="checkbox" checked={chosen.includes(m.id)} onChange={e => setChosen(ids => e.target.checked ? [...ids, m.id] : ids.filter(id => id !== m.id))}/><span>{formatBookDay(m.day)} · {[m.text, m.note].filter(Boolean).join(' — ')}</span></label>)}</fieldset>
 <label className="form-field">Ваша подпись · до 200 символов<Textarea maxLength={200} value={caption} onChange={e => setCaption(e.target.value)}/></label><label className="form-field">Одно фото с телефона · необязательно<Input type="file" accept="image/*" onChange={e => { setPhoto(e.target.files?.[0]); e.target.value = ''; }}/></label>{photo && <Button variant="outline" onClick={() => setPhoto(undefined)}>Убрать фото</Button>}
 <label className="book-check"><input type="checkbox" checked={showName} onChange={e => setShowName(e.target.checked)}/>Показывать имя</label><label className="book-check"><input type="checkbox" checked={dates} onChange={e => setDates(e.target.checked)}/>Показывать даты</label><label className="book-check"><input type="checkbox" checked={brand} onChange={e => { setBrand(e.target.checked); try {
            localStorage.setItem('mh_book_brand', e.target.checked ? 'on' : 'off');
        }
        catch { /* optional preference */ } }}/>Подпись «Мамин помощник»</label>
 <Button disabled={busy || !chosen.length} onClick={async () => { setBusy(true); setError(''); try {
            const result = await renderPostcard({ title, name: showName ? name : '', moments: moments.filter(m => chosen.includes(m.id)), caption, dates, brand, photo });
            if (alive.current)
                setBlob(result);
        }
        catch (e) {
            if (alive.current)
                setError((e as Error).message || 'Не удалось прочитать фото. Попробуйте JPEG или PNG.');
        }
        finally {
            if (alive.current)
                setBusy(false);
        } }}>Предпросмотр</Button></>}
 <p>Отправленную картинку нельзя отозвать</p>{error && <p role="alert">{error}</p>}<Button variant="outline" onClick={onClose}>Отмена</Button></DialogContent></Dialog>;
}
function PrintBook({ name, children, onClose }: {
    name: string;
    children: React.ReactNode;
    onClose: () => void;
}) {
    const ref = useRef<HTMLDialogElement>(null);
    useEffect(() => { const previous = document.activeElement as HTMLElement | null; ref.current?.showModal(); return () => previous?.focus(); }, []);
    return createPortal(<dialog ref={ref} className="book-print-overlay" aria-label="Предпросмотр печати книги первого года" onCancel={onClose}><div className="book-print-actions"><Button onClick={() => window.print()}>Печать / сохранить PDF</Button><Button variant="outline" onClick={onClose}>Закрыть</Button></div><article className="book-print-document"><h1>Книга первого года</h1><h2>{name}</h2>{children}</article></dialog>, document.body);
}
