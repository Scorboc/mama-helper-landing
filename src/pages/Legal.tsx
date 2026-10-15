import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/parent-api";
import documents from "../../backend/parent-app/legal_documents.json";

export type LegalInfo = {
  operator: { name: string; inn: string; address: string; email: string };
  documentsReady: boolean;
  termsVersion: string;
  offerVersion: string;
};
export function LegalLinks() {
  return <nav aria-label="Документы сервиса" className="flex flex-wrap gap-x-5 gap-y-3 text-sm">
    <Link className="underline" to="/terms">Условия аккаунта</Link>
    <Link className="underline" to="/offer">Оферта</Link>
    <Link className="underline" to="/privacy">Персональные данные</Link>
    <Link className="underline" to="/data-rights">Данные и обращения</Link>
  </nav>;
}
export default function Legal({ kind }: { kind: keyof typeof documents }) {
  const [info, setInfo] = useState<LegalInfo | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { void api<{ legal: LegalInfo }>("config").then(r => setInfo(r.legal)).catch(() => setError("Реквизиты сервиса сейчас не загрузились. Повторите позже.")); }, []);
  const document = documents[kind];
  return <main className="account-page"><article className="tile mx-auto max-w-3xl space-y-6 p-6 sm:p-9">
    <Link className="back-link" to="/cabinet">В кабинет</Link>
    <h1 className="font-heading text-3xl">{document.title}</h1>
    <p className="muted text-sm">Редакция от 12 октября 2026 года · {document.version}</p>
    {!info?.documentsReady && <p role="status" className="rounded-xl border p-4">Проект документа для локальной проверки. Приём оплаты закрыт до заполнения реквизитов и утверждения условий обработки данных.</p>}
    {error && <p role="alert" className="form-error">{error}</p>}
    {info && <section className="rounded-xl bg-inner p-4 space-y-2"><h2 className="font-heading text-xl">Реквизиты</h2>
      <p>{info.operator.name || "ФИО исполнителя ещё не заполнено"}</p>
      <p>ИНН: {info.operator.inn || "не заполнен"} · плательщик НПД</p>
      <p>Адрес для обращений: {info.operator.address || "не заполнен"}</p>
      {info.operator.email ? <a className="underline" href={"mailto:" + info.operator.email}>{info.operator.email}</a> : <p>Почта поддержки ещё не заполнена</p>}
    </section>}
    {document.sections.map(([heading, text]) => <section key={heading} className="space-y-2"><h2 className="font-heading text-xl">{heading}</h2><p className="leading-relaxed">{text}</p></section>)}
    <LegalLinks />
    <Link className="standalone-link" to="/first-aid">Срочная помощь · 112</Link>
  </article></main>;
}
