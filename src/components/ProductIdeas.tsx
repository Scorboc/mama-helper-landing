import { FormEvent, useEffect, useState } from "react";
import { Lightbulb, Vote } from "lucide-react";
import { api } from "@/lib/parent-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type Idea = { id: string; title: string; detail: string; votes: number };
type IdeasState = {
  phase: "collecting" | "voting";
  week: string;
  canSubmit: boolean;
  remainingSubmissions: number;
  submissionCount: number;
  items: Idea[];
  myVote: string | null;
  winners: Idea[];
};

export default function ProductIdeas() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<IdeasState | null>(null);
  const [title, setTitle] = useState("");
  const [detail, setDetail] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);

  async function load() {
    setLoading(true);
    setLoadFailed(false);
    setStatus("");
    try {
      setData(await api<IdeasState>("suggestion-list"));
    } catch (error) {
      setLoadFailed(true);
      setStatus((error as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setStatus("");
    try {
      const next = await api<IdeasState>("suggestion-create", { title, detail });
      setData(next);
      setTitle("");
      setDetail("");
      setStatus("Идея добавлена анонимно. В конце недели она появится в голосовании.");
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function vote(id: string) {
    setBusy(true);
    setStatus("");
    try {
      setData(await api<IdeasState>("suggestion-vote", { suggestionId: id }));
      setStatus("Голос сохранён. До конца воскресенья выбор можно изменить.");
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const voting = data?.phase === "voting";
  return (
    <>
      <Button
        type="button"
        variant={voting ? "default" : "outline"}
        className="chat-ideas-button"
        onClick={() => {
          setOpen(true);
          setStatus("");
          void load();
        }}
      >
        {voting ? <Vote size={17} /> : <Lightbulb size={17} />}
        {voting ? "Голосование" : "Предложить идею"}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="ios-sheet max-h-[88vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{voting ? "Выберите улучшение" : "Идеи для Маминого помощника"}</DialogTitle>
            <DialogDescription>
              С понедельника по четверг собираем идеи, с пятницы по воскресенье голосуем. Победившие предложения попадают владельцу в план реализации.
            </DialogDescription>
          </DialogHeader>

          {loading && <p role="status" className="muted">Загружаем идеи…</p>}

          {data?.phase === "collecting" && (
            <form className="space-y-4" onSubmit={submit}>
              <p className="rounded-2xl bg-cream p-3 text-sm">
                На этой неделе собрано идей: {data.submissionCount}. Вы можете добавить ещё {data.remainingSubmissions}.
              </p>
              <label className="block space-y-1">
                <span>Коротко: что добавить или изменить?</span>
                <Input
                  required
                  minLength={10}
                  maxLength={120}
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="Например: сравнение сна за две недели"
                />
              </label>
              <label className="block space-y-1">
                <span>Почему это поможет — необязательно</span>
                <Textarea
                  maxLength={800}
                  value={detail}
                  onChange={(event) => setDetail(event.target.value)}
                  placeholder="Опишите удобный для вас результат. Не пишите контакты и личные сведения."
                />
              </label>
              <Button disabled={busy || loading || loadFailed || !data.canSubmit || title.trim().length < 10}>
                {busy ? "Сохраняем…" : "Добавить анонимно"}
              </Button>
            </form>
          )}

          {data?.phase === "voting" && (
            <div className="space-y-3">
              {!data.items.length && <p className="muted">На этой неделе идей для голосования нет.</p>}
              {data.items.map((idea) => (
                <article
                  key={idea.id}
                  className={`rounded-2xl border p-4 ${data.myVote === idea.id ? "border-primary bg-cream" : ""}`}
                >
                  <strong>{idea.title}</strong>
                  {idea.detail && <p className="mt-1 text-sm">{idea.detail}</p>}
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span className="muted text-sm">Голосов: {idea.votes}</span>
                    <Button
                      variant={data.myVote === idea.id ? "default" : "outline"}
                      disabled={busy || loading || loadFailed}
                      onClick={() => void vote(idea.id)}
                    >
                      {data.myVote === idea.id ? "Вы выбрали" : "Голосовать"}
                    </Button>
                  </div>
                </article>
              ))}
            </div>
          )}

          {!!data?.winners.length && (
            <section className="border-t pt-4">
              <h3 className="text-base font-semibold">Выбрано мамами раньше</h3>
              {data.winners.map((idea) => (
                <p className="mt-2 text-sm" key={idea.id}>✓ {idea.title}</p>
              ))}
            </section>
          )}
          {status && <p role={loadFailed ? "alert" : "status"} className="text-sm">{status}</p>}
          {loadFailed && <Button variant="outline" disabled={loading} onClick={() => void load()}>Обновить идеи</Button>}
        </DialogContent>
      </Dialog>
    </>
  );
}
