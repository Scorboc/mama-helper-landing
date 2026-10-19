import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, BillingInfo, Session } from "@/lib/parent-api";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { LegalInfo, LegalLinks } from "./Legal";

export default function Billing() {
  const [params] = useSearchParams();
  const [billing, setBilling] = useState<BillingInfo | null>(null);
  const [legal, setLegal] = useState<LegalInfo | null>(null);
  const [loggedIn, setLoggedIn] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [order, setOrder] = useState(params.get("order") || "");
  const [confirmation, setConfirmation] = useState("");
  useEffect(() => {
    void api<{ billing: BillingInfo; legal: LegalInfo }>("config").then(r => { setBilling(current => current?.mode ? { ...r.billing, ...current } : r.billing); setLegal(r.legal); }).catch(e => setError((e as Error).message));
    void api<Session>("session").then(r => { setLoggedIn(true); if (r.billing) setBilling(r.billing); }).catch(e => { if (e.status !== 401) setError(e.message); });
  }, []);
  async function checkout(check = false) {
    setBusy(true); setError("");
    try {
      const result = await api<{ orderId: string; status: string; confirmationUrl?: string; billing?: BillingInfo }>(check ? "billing-check" : "billing-create", check ? { orderId: order } : { offerAccepted: accepted, offerVersion: legal?.offerVersion });
      setOrder(result.orderId);
      if (result.billing) setBilling(result.billing);
      if (result.status === "succeeded") { setConfirmation(""); setNotice("Оплата подтверждена. Доступ активен."); }
      else if (result.status === "canceled") { setConfirmation(""); setNotice("Оплата отменена. Доступ не начислен."); }
      else if (result.status === "support-required") setNotice("Платёж требует проверки поддержки. Повторно оплачивать не нужно.");
      else { setConfirmation(result.confirmationUrl || ""); setNotice("Заказ сохранён. Перейдите на защищённую страницу оплаты, затем проверьте её статус."); }
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  const active = billing?.mode === "paid" || billing?.mode === "test";
  return <main className="account-page"><article className="tile mx-auto max-w-2xl p-6 space-y-6">
    <Link className="back-link" to="/cabinet?tab=chat">В чат</Link>
    <h1 className="font-heading text-3xl">Доступ и оплата</h1>
    <section className="rounded-2xl bg-inner p-5 space-y-3">
      <h2 className="font-heading text-2xl">480 ₽ за календарный месяц</h2>
      <p>300 ответов и подборок ИИ на аккаунт, для всех ваших детей. Одна ежедневная подборка учитывается целиком; повторное открытие не расходует лимит.</p>
      <p>Трекеры, графики, заметки, избранное и семейные функции. Продление по вашему действию, без автоматических списаний.</p>
      <p className="muted text-sm">Неиспользованные ответы не переносятся. Новый период можно оплатить после окончания текущего. История, отметки и срочная помощь доступны и после окончания доступа.</p>
    </section>
    {active && <p role="status">{billing?.mode === "test" ? "Ваш доступ активен" : "Ваш платный доступ активен"}{billing?.endsAt ? " до " + new Date(billing.endsAt * 1000).toLocaleString("ru-RU", { timeZone: "Europe/Moscow" }) + " МСК" : ""}.</p>}
    {!billing?.paymentConfigured && <p role="status" className="rounded-xl border p-4">Онлайн-оплата пока недоступна. Деньги не списываются.</p>}
    {!loggedIn ? <Button asChild><Link to="/account?mode=login">Войти в аккаунт</Link></Button> : !active && <>
      <div className="flex items-start gap-3"><Checkbox id="offer-accepted" checked={accepted} onCheckedChange={v => setAccepted(v === true)} /><label htmlFor="offer-accepted" className="leading-relaxed">Принимаю <Link className="underline" to="/offer">оферту</Link> на доступ за 480 ₽ и 300 ответов и подборок ИИ на календарный месяц.</label></div>
      <Button onClick={() => void checkout()} disabled={busy || !accepted || !billing?.paymentConfigured}>Открыть оплату · 480 ₽</Button>
    </>}
    {confirmation && <a className="glass-btn inline-block px-5 py-3" href={confirmation}>Перейти на страницу платёжного сервиса</a>}
    {order && <Button variant="outline" onClick={() => void checkout(true)} disabled={busy}>Проверить оплату</Button>}
    {busy && <p role="status">Проверяем заказ…</p>}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert" className="form-error">{error}</p>}
    <Link className="standalone-link" to="/data-rights">Задать вопрос об оплате или запросить возврат</Link>
    <LegalLinks />
    <Link className="standalone-link" to="/first-aid">Срочная помощь · 112</Link>
  </article></main>;
}
