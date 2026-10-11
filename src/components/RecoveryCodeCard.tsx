import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

export default function RecoveryCodeCard({ code, onDone, continueLabel = "Код сохранён — перейти в кабинет" }: { code: string; onDone: () => void; continueLabel?: string }) {
  const [saved, setSaved] = useState(false);
  const [status, setStatus] = useState("");
  return <div className="space-y-4 mt-6">
    <h2>Сохраните код восстановления</h2>
    <p>Код позволяет сменить пароль без письма. Храните его в менеджере паролей или другом безопасном месте и никому не передавайте.</p>
    <code className="recovery-code">{code}</code>
    <Button variant="outline" className="w-full" onClick={async () => {
      try { await navigator.clipboard.writeText(code); setStatus("Код скопирован. Сохраните его в безопасном месте."); }
      catch { setStatus("Не удалось скопировать автоматически. Выделите код и скопируйте его вручную."); }
    }}>Скопировать код</Button>
    {status && <p role="status" className="muted text-sm">{status}</p>}
    <p className="muted text-sm">Код показывается один раз. Новый код заменяет прежний. Сохраните его как запасной способ доступа.</p>
    <div className="flex gap-3 items-start">
      <Checkbox id="recovery-saved" checked={saved} onCheckedChange={v => setSaved(v === true)} />
      <label htmlFor="recovery-saved" className="text-sm leading-relaxed">Код сохранён в безопасном месте</label>
    </div>
    <Button className="w-full" disabled={!saved} onClick={onDone}>{continueLabel}</Button>
  </div>;
}
