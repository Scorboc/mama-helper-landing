import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import RecoveryCodeCard from "./RecoveryCodeCard";
import { api, ApiError, Session, storageMode } from "@/lib/parent-api";

type Action = "change-password" | "rotate-recovery" | "logout-all";
export default function AccountSecurity() {
  const navigate = useNavigate();
  const [email, setEmail] = useState<string | null>(null);
  const [mode, setMode] = useState<Action>("change-password");
  const [device, setDevice] = useState(false);
  const [emailVerified, setEmailVerified] = useState(false);
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [code, setCode] = useState("");
  const load = useCallback(async () => {
    setError("");
    try {
      const [session, storage] = await Promise.all([api<Session>("session"), storageMode()]);
      setEmail(session.user.email); setDevice(storage === "device");
      setEmailVerified(!!session.user.emailVerified);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) navigate("/account?mode=login&next=%2Fcabinet%3Ftab%3Dsettings", { replace: true });
      else setError((e as Error).message);
    }
  }, [navigate]);
  useEffect(() => { void load(); }, [load]);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setError(""); setStatus("");
    if (mode === "change-password" && password !== confirmation) { setError("Новые пароли не совпадают."); return; }
    setBusy(true);
    try {
      const result = await api<{ ok: boolean; recoveryCode?: string }>(mode, { currentPassword: current, password });
      setCurrent(""); setPassword(""); setConfirmation("");
      if (mode === "logout-all") navigate("/account?mode=login", { replace: true });
      else if (result.recoveryCode) setCode(result.recoveryCode);
      else setStatus(device ? "Пароль изменён на этом устройстве." : "Пароль изменён. На других устройствах нужно войти заново. Код восстановления остаётся прежним.");
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setError("Проверьте текущий пароль. Если сессия закончилась, войдите заново.");
      else setError((e as Error).message);
    } finally { setBusy(false); }
  }
  return <main className="account-page">
    <Link to="/cabinet?tab=settings" className="back-link"><ArrowLeft size={18} /> Назад в настройки</Link>
    <section className="account-card tile">
      <h1>Безопасность аккаунта</h1>
      {email && <p className="muted break-all mt-2">{email}</p>}
      {code ? <RecoveryCodeCard code={code} onDone={() => { setCode(""); navigate("/cabinet?tab=settings", { replace: true }); }} /> : email ? <>
        {!device && email.includes("@") && <section className="email-security-status" aria-label="Подтверждение почты">
          <p>{emailVerified ? "Почта подтверждена. Пароль можно восстановить письмом." : "Подтвердите почту, чтобы восстанавливать пароль письмом."}</p>
          {!emailVerified && <Link className="standalone-link" to="/account?mode=email-await">Подтвердить почту</Link>}
        </section>}
        <nav className="account-modes" aria-label="Настройки безопасности">
          {([["change-password", "Пароль"], ["rotate-recovery", "Код доступа"], ["logout-all", "Выход"]] as const).map(([action, label]) =>
            <button key={action} type="button" disabled={busy} aria-pressed={mode === action} onClick={() => {
              setMode(action); setCurrent(""); setPassword(""); setConfirmation(""); setError(""); setStatus("");
            }}>{label}</button>)}
        </nav>
        <h2 className="mt-6">{mode === "change-password" ? "Сменить пароль" : mode === "rotate-recovery" ? "Новый код восстановления" : "Выйти на всех устройствах"}</h2>
        <p className="muted mt-2">{mode === "rotate-recovery" ? (device ? "Прежний код перестанет работать. Новый будет показан один раз. Изменение действует в этом браузере." : "Прежний код перестанет работать. Новый будет показан один раз. Другие устройства выйдут из аккаунта.") : mode === "logout-all" ? (device ? "Выйдете из аккаунта в этом браузере. Другие устройства в локальном режиме не связаны." : "Завершатся все сеансы, включая этот. Профили, диалоги и записи сохранятся.") : "Новый пароль — от 12 до 128 символов. Можно использовать длинную фразу."}</p>
        <form onSubmit={submit} className="space-y-5 mt-6" aria-busy={busy}>
          <label className="form-field">Текущий пароль<Input name="current-password" type="password" autoComplete="current-password" required maxLength={128} value={current} onChange={e => setCurrent(e.target.value)} /></label>
          {mode === "change-password" && <>
            <label className="form-field">Новый пароль<Input name="new-password" type="password" autoComplete="new-password" required minLength={12} maxLength={128} value={password} onChange={e => setPassword(e.target.value)} /></label>
            <label className="form-field">Повторите новый пароль<Input name="confirm-password" type="password" autoComplete="new-password" required minLength={12} maxLength={128} value={confirmation} onChange={e => setConfirmation(e.target.value)} /></label>
          </>}
          {error && <p className="form-error" role="alert">{error}</p>}
          {status && <p role="status">{status}</p>}
          <Button className="w-full" type="submit" disabled={busy}>{busy ? "Сохраняем…" : mode === "change-password" ? "Сменить пароль" : mode === "rotate-recovery" ? "Получить новый код" : "Выйти на всех устройствах"}</Button>
        </form>
      </> : <>
        <p className="mt-4" role={error ? "alert" : "status"}>{error || "Проверяем доступ…"}</p>
        {error && <Button variant="outline" className="mt-4" onClick={() => void load()}>Повторить</Button>}
      </>}
      <Link to="/first-aid" className="standalone-link mt-6">Срочная помощь · 112</Link>
    </section>
  </main>;
}
