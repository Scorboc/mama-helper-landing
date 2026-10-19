import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, ApiError, Session } from "@/lib/parent-api";
import RecoveryCodeCard from "./RecoveryCodeCard";
import { workspaceReturn } from "@/lib/room-experience";

export default function EmailAccount({ mode }: { mode: string }) {
  const navigate = useNavigate();
  const returnTo = workspaceReturn(new URLSearchParams(window.location.search).get("next"));
  const nextQuery = "&next=" + encodeURIComponent(returnTo);
  const [token] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get("token") || "");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [code, setCode] = useState("");
  useEffect(() => {
    if (token) window.history.replaceState(null, "", window.location.pathname + window.location.search);
    if (mode === "email-await") void api<Session>("session").then(session => {
      setEmail(session.user.email);
      if (session.user.emailVerified) setStatus("Почта уже подтверждена. Можно открыть кабинет.");
    }).catch(e => { if (e instanceof ApiError && e.status === 401) navigate("/account?mode=login" + nextQuery, { replace: true }); else setError(e.message); });
  }, [mode, navigate, token, nextQuery]);
  async function submit(e: FormEvent) {
    e.preventDefault(); if (busy) return;
    setError(""); setStatus("");
    if (mode === "email-reset" && password !== confirmation) { setError("Пароли не совпадают."); return; }
    setBusy(true);
    try {
      if (mode === "email-await") {
        const result = await api<{ message?: string; alreadyVerified?: boolean }>("email-resend");
        setStatus(result.alreadyVerified ? "Почта уже подтверждена. Можно открыть кабинет." : result.message || "Письмо поставлено в очередь.");
      } else if (mode === "email-request") {
        const result = await api<{ message: string }>("email-request-reset", { email });
        setStatus(result.message);
      } else {
        const result = await api<{ ok: boolean; recoveryCode?: string }>(mode, { token, password });
        setPassword(""); setConfirmation("");
        if (result.recoveryCode) setCode(result.recoveryCode);
        else setStatus("Почта подтверждена. Войдите в аккаунт — прежние сеансы завершены.");
      }
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  const title = mode === "email-await" || mode === "email-verify" ? "Подтверждение почты" : "Восстановление пароля";
  return <main className="account-page">
    <Link className="back-link" to={"/account?mode=login" + nextQuery}><ArrowLeft size={18} /> К входу</Link>
    <section className="account-card tile">
      <h1>{code ? "Пароль изменён" : title}</h1>
      {code ? <RecoveryCodeCard code={code} continueLabel="Код сохранён — войти в аккаунт" onDone={() => navigate("/account?mode=login" + nextQuery, { replace: true })} /> : <>
        {mode === "email-await" && <p className="muted mt-4">Подтвердите адрес{email ? ` ${email}` : ""} по ссылке из письма Мамин помощник. Она действует 24 часа. Если письма нет, проверьте «Спам» или отправьте его кнопкой ниже.</p>}
        {mode === "email-request" && <p className="muted mt-4">Отправим ссылку на подтверждённый адрес вашего аккаунта. Она действует 30 минут. После смены пароля прежние сеансы завершатся.</p>}
        {mode === "email-verify" && <p className="muted mt-4">Нажмите кнопку, чтобы подтвердить адрес из письма. После подтверждения войдите в аккаунт заново.</p>}
        <form onSubmit={submit} className="space-y-5 mt-6" aria-busy={busy}>
          {mode === "email-request" && <label className="form-field">Электронная почта<Input name="email" type="email" inputMode="email" autoComplete="email" required maxLength={254} value={email} onChange={e => setEmail(e.target.value)} /></label>}
          {mode === "email-reset" && <>
            <label className="form-field">Новый пароль<Input name="new-password" type="password" autoComplete="new-password" required minLength={12} maxLength={128} value={password} onChange={e => setPassword(e.target.value)} /></label>
            <label className="form-field">Повторите пароль<Input name="confirm-password" type="password" autoComplete="new-password" required minLength={12} maxLength={128} value={confirmation} onChange={e => setConfirmation(e.target.value)} /></label>
            <p className="muted text-sm">От 12 до 128 символов. Можно использовать длинную фразу.</p>
          </>}
          {error && <p role="alert" className="form-error">{error}</p>}
          {status && <p role="status">{status}</p>}
          {!status || mode === "email-await" ? <Button className="w-full" type="submit" disabled={busy || ((mode === "email-verify" || mode === "email-reset") && !token)}>{busy ? "Подождите…" : mode === "email-await" ? "Отправить письмо повторно" : mode === "email-request" ? "Получить ссылку" : mode === "email-verify" ? "Подтвердить почту" : "Сохранить новый пароль"}</Button> : <Link className="standalone-link" to={(mode === "email-verify" ? "/account?mode=login" : "/account?mode=email-request") + nextQuery}>{mode === "email-verify" ? "Войти в аккаунт" : "Запросить новое письмо"}</Link>}
          {(mode === "email-verify" || mode === "email-reset") && !token && <p role="alert">Откройте полную ссылку из письма. Если она устарела, запросите новую.</p>}
        </form>
        {mode === "email-await" && <Link className="standalone-link mt-4" to={returnTo}>Проверить подтверждение</Link>}
        {(mode === "email-request" || mode === "email-reset") && <Link className="standalone-link mt-4" to={"/account?mode=recover&method=code" + nextQuery}>Восстановить по личному коду</Link>}
        {mode === "email-reset" && error && <Link className="standalone-link mt-4" to={"/account?mode=email-request" + nextQuery}>Запросить новое письмо</Link>}
        {mode === "email-verify" && error && <Link className="standalone-link mt-4" to={"/account?mode=email-await" + nextQuery}>Получить новое письмо</Link>}
      </>}
      <Link to="/first-aid" className="standalone-link mt-6">Срочная помощь · 112</Link>
    </section>
  </main>;
}
