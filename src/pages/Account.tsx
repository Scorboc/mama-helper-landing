import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Heart, ArrowLeft, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { api, Session, storageMode } from "@/lib/parent-api";
import { Fox } from "@/components/Critters";
import AccountSecurity from "@/components/AccountSecurity";
import RecoveryCodeCard from "@/components/RecoveryCodeCard";
import EmailAccount from "@/components/EmailAccount";

export default function Account() {
  const [params] = useSearchParams();
  const mode = params.get("mode") || "";
  if (mode.startsWith("email-")) return <EmailAccount key={mode} mode={mode} />;
  if (mode === "recover" && params.get("method") !== "code") return <EmailAccount mode="email-request" />;
  return params.get("mode") === "security" ? <AccountSecurity /> : <AccountAccess />;
}

function AccountAccess() {
  const [invite] = useState(
    () =>
      new URLSearchParams(window.location.hash.slice(1)).get("invite") || "",
  );
  const [returnTo] = useState(() => {
    const next = new URLSearchParams(window.location.search).get("next");
    return next &&
      (next === "/cabinet" || next.startsWith("/cabinet?") || next === "/chat")
      ? next
      : "/cabinet";
  });
  const [params, setParams] = useSearchParams();
  const requestedMode = params.get("mode");
  const mode = ["login", "recover", "register"].includes(requestedMode || "")
    ? requestedMode!
    : params.has("next") ? "login" : "register";
  function setMode(next: string) {
    const nextParams = new URLSearchParams(params);
    nextParams.set("mode", next);
    setParams(nextParams);
    setError("");
    setVisible(false);
    setPassword("");
    setConfirmation("");
    setRecovery("");
  }
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [recovery, setRecovery] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [consent, setConsent] = useState(false);
  const [adult, setAdult] = useState(false);
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [newCode, setNewCode] = useState("");
  const [verificationRequired, setVerificationRequired] = useState(false);
  const [storage, setStorage] = useState<"checking" | "server" | "device" | "unavailable">(
    "checking",
  );
  const navigate = useNavigate();
  useEffect(() => {
    void storageMode()
      .then(setStorage)
      .catch(() => setStorage("unavailable"));
  }, []);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (mode !== "login" && password !== confirmation) {
      setError("Пароли не совпадают.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await api<Session>(mode, {
        email,
        password,
        consent,
        adult,
        termsAccepted: consent,
        termsVersion: "account-2026-10-12",
        recoveryCode: recovery,
        ...(mode === "register" && invite ? { invite } : {}),
      });
      setPassword("");
      setConfirmation("");
      setRecovery("");
      if (invite)
        window.history.replaceState(null, "", window.location.pathname);
      if (result.recoveryCode) setNewCode(result.recoveryCode);
      else navigate(result.user.emailVerificationRequired ? "/account?mode=email-await" : returnTo, { replace: true });
      setVerificationRequired(!!result.user.emailVerificationRequired);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="account-page">
      <Link className="back-link" to="/">
        <ArrowLeft size={18} /> На главную
      </Link>
      <div className="account-card tile">
        <Fox className="mx-auto mb-4 h-20 w-20" />
        <h1>{newCode ? "Ваш аккаунт готов" : "Своя маленькая опора"}</h1>
        <p className="muted">
          Личный кабинет для мам и пап. Доступ — 480 ₽ в месяц; бесплатный тест назначает владелец.
        </p>
        {newCode ? (
          <RecoveryCodeCard code={newCode} continueLabel={verificationRequired ? "Код сохранён — подтвердить почту" : undefined} onDone={() => { setNewCode(""); navigate(verificationRequired ? "/account?mode=email-await" : returnTo, { replace: true }); }} />
        ) : (
          <>
            <nav className="account-modes" aria-label="Доступ к аккаунту">
              {[["register", "Регистрация"], ["login", "Вход"], ["recover", "Восстановить"]].map(([id, label]) => (
                <button key={id} type="button" aria-pressed={mode === id} disabled={busy} onClick={() => setMode(id)}>{label}</button>
              ))}
            </nav>
            <form onSubmit={submit} className="space-y-5 mt-6" aria-busy={busy}>
              <label className="form-field">
                Электронная почта
                <Input
                  type={mode === "register" ? "email" : "text"}
                  inputMode={mode === "register" ? "email" : "text"}
                  autoComplete="username"
                  name="email"
                  required
                  maxLength={254}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={
                    mode === "register" ? "you@example.ru" : "Почта или логин"
                  }
                />
              </label>
              {mode === "recover" && (
                <label className="form-field">
                  Личный код восстановления
                  <Input
                    autoComplete="off"
                    autoCapitalize="none"
                    spellCheck={false}
                    name="recovery-code"
                    value={recovery}
                    onChange={(e) => setRecovery(e.target.value)}
                    required
                    maxLength={100}
                  />
                </label>
              )}
              <div className="form-field">
                <label htmlFor="account-password">{mode === "recover" ? "Новый пароль" : "Пароль"}</label>
                <div className="password-field">
                  <Input
                    id="account-password"
                    name="password"
                    type={visible ? "text" : "password"}
                    required
                    minLength={mode === "login" ? 1 : 12}
                    maxLength={128}
                    autoComplete={
                      mode === "login" ? "current-password" : "new-password"
                    }
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setVisible((v) => !v)}
                    aria-label={visible ? "Скрыть пароль" : "Показать пароль"}
                  >
                    {visible ? <EyeOff size={19} /> : <Eye size={19} />}
                  </button>
                </div>
                {mode !== "login" && (
                  <span className="muted text-sm">
                    От 12 символов. Можно использовать длинную фразу.
                  </span>
                )}
              </div>
              {mode !== "login" && <label className="form-field">
                Повторите пароль
                <Input name="password-confirmation" type="password" autoComplete="new-password" required minLength={12} maxLength={128} value={confirmation} onChange={e => setConfirmation(e.target.value)} />
              </label>}
              {mode === "recover" && <p className="muted text-sm">Нужен код, сохранённый при регистрации. После восстановления все прежние сеансы завершатся. Если забыли только код, а пароль помните, войдите и получите новый код в настройках безопасности.</p>}
              {mode === "register" && (
                <div className="space-y-4"><div className="flex gap-3 items-start"><Checkbox id="adult" checked={adult} onCheckedChange={v => setAdult(v === true)} /><label htmlFor="adult" className="text-sm leading-relaxed">Мне исполнилось 18 лет.</label></div><div className="flex gap-3 items-start">
                  <Checkbox
                    id="consent"
                    checked={consent}
                    onCheckedChange={(v) => setConsent(v === true)}
                  />
                  <label htmlFor="consent" className="text-sm leading-relaxed">
                    Принимаю{" "}
                    <Link to="/terms" className="underline">
                      условия аккаунта
                    </Link>
                    .
                  </label>
                </div><p className="text-sm muted">О данных — в <Link className="underline" to="/privacy">отдельной политике</Link>. Эти отметки не являются согласием на сведения о здоровье, рекламу или уведомления.</p></div>
              )}
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              <Button
                className="w-full"
                type="submit"
                disabled={busy || (mode === "register" && (!consent || !adult))}
              >
                {busy
                  ? "Подождите…"
                  : mode === "register"
                    ? "Создать аккаунт"
                    : mode === "login"
                      ? "Войти"
                      : "Восстановить доступ"}
              </Button>
            </form>
            <p className="muted mt-4 text-sm flex gap-2" role="status">
              <Heart size={18} className="shrink-0" />
              {storage === "checking"
                ? "Проверяем режим хранения…"
                : storage === "server"
                  ? "Профиль, переписка и наблюдения сохраняются в вашем аккаунте на сервере."
                  : storage === "device" ? "Локальный режим: профиль и переписка сохраняются только в этом браузере на устройстве." : "Не удалось проверить подключение к аккаунтам. При ошибке регистрации попробуйте ещё раз — данные в аккаунтах сохраняются."}
            </p>
          </>
        )}
        <Link to="/first-aid" className="standalone-link mt-6">Срочная помощь · 112</Link>
      </div>
    </main>
  );
}
