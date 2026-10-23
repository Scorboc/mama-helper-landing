import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "@/lib/parent-api";
import { randomId } from "@/lib/id";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { LegalLinks } from "./Legal";

const kinds = { access: "Сведения об обработке", correct: "Исправить ошибку в данных", withdraw: "Отозвать согласие или прекратить обработку", delete: "Удалить данные", refund: "Оплата или возврат" };
type Request = { id: string; kind: keyof typeof kinds; status: string; createdAt: number };
export default function DataRights() {
  const [items, setItems] = useState<Request[]>([]);
  const [kind, setKind] = useState<keyof typeof kinds>("correct");
  const [text, setText] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [login, setLogin] = useState(false);
  const [requestId, setRequestId] = useState(randomId);
  async function refresh() {
    try { const r = await api<{ items: Request[] }>("data-request-list"); setItems(r.items); setLogin(false); }
    catch (e) { if (e instanceof ApiError && e.status === 401) setLogin(true); else setError(e instanceof Error ? e.message : "Не удалось загрузить обращения."); }
  }
  useEffect(() => { void refresh(); }, []);
  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try { const r = await api<{ notice: string }>("data-request", { kind, text, requestId }); setNotice(r.notice); setText(""); setRequestId(randomId()); await refresh(); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function download(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      const result = await api("data-export", { password });
      const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }));
      const a = document.createElement("a"); a.href = url; a.download = "mama-helper-my-data.json"; a.click(); URL.revokeObjectURL(url);
      setPassword(""); setNotice("Выгрузка готова. Файл содержит личные сведения: храните его у себя.");
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <main className="account-page"><article className="tile mx-auto max-w-2xl p-6 space-y-6">
    <Link className="back-link" to="/cabinet?tab=more">В кабинет</Link>
    <h1 className="font-heading text-3xl">Данные и обращения</h1>
    <p>Можно исправить ошибку в профиле, узнать об обработке данных, запросить удаление или возврат оплаты. Действующий платный доступ для этого не нужен.</p>
    <p className="muted">Не прикладывайте пароль, паспорт, номер карты или медицинские документы. При необходимости владелец отдельно объяснит безопасный способ подтверждения полномочий.</p>
    {login ? <Button asChild><Link to="/account?mode=login">Войти, чтобы отправить личное обращение</Link></Button> : <>
      <form onSubmit={submit} className="space-y-4">
        <label className="form-field">Вид обращения<select value={kind} onChange={e => { setKind(e.target.value as keyof typeof kinds); setRequestId(randomId()); }} className="rounded-xl border bg-background p-3">{Object.entries(kinds).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
        <label className="form-field">Ваш запрос<Textarea aria-label="Ваш запрос" value={text} onChange={e => { setText(e.target.value); setRequestId(randomId()); }} required maxLength={2000} rows={4} /></label>
        <Button type="submit" disabled={busy}>Отправить владельцу</Button>
      </form>
      <section className="space-y-3"><h2 className="font-heading text-xl">Выгрузить свой кабинет</h2><form onSubmit={download} className="space-y-3"><label className="form-field">Текущий пароль<Input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required maxLength={128} /></label><Button variant="outline" type="submit" disabled={busy}>Скачать свои данные</Button></form></section>
      <section><h2 className="font-heading text-xl mb-3">Ваши обращения</h2>{items.length ? <ul className="space-y-3">{items.map(r => <li key={r.id}>{kinds[r.kind]} · {new Date(r.createdAt * 1000).toLocaleDateString("ru-RU")} · {r.status === "done" ? "Рассмотрено" : r.status === "review" ? "На рассмотрении" : "Получено"}<span className="block muted text-sm break-all">Номер: {r.id}</span></li>)}</ul> : <p className="muted">Обращений пока нет.</p>}</section>
    </>}
    {notice && <p role="status">{notice}</p>}{error && <p role="alert" className="form-error">{error}</p>}
    <LegalLinks /><Link className="standalone-link" to="/first-aid">Срочная помощь · 112</Link>
  </article></main>;
}
