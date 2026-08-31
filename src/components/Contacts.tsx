import { FormEvent, useState } from 'react';
import Icon from '@/components/ui/icon';
import { Fox, Bunny } from '@/components/Critters';

type Message = { id: number; from: 'me' | 'doc' | 'mom'; text: string };

const Contacts = () => {
  const [name, setName] = useState('');
  const [contact, setContact] = useState('');
  const [question, setQuestion] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [messages, setMessages] = useState<Message[]>([]);
  const [sent, setSent] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const next: Record<string, string> = {};
    if (name.trim().length < 2) next.name = 'Как к вам обращаться?';
    if (!/^([^@\s]+@[^@\s]+\.[^@\s]+|\+?\d[\d\s()-]{8,})$/.test(contact.trim()))
      next.contact = 'Укажите почту или телефон';
    if (question.trim().length < 10) next.question = 'Опишите вопрос чуть подробнее';
    setErrors(next);
    if (Object.keys(next).length) return;

    setMessages([
      { id: Date.now(), from: 'me', text: question.trim() },
      {
        id: Date.now() + 1,
        from: 'doc',
        text: 'Врачи: приняли вопрос. Соберём ответ по проверенным источникам и без диагнозов.',
      },
      {
        id: Date.now() + 2,
        from: 'mom',
        text: 'Мамы: рядом обязательно будет живой опыт тех, у кого было так же.',
      },
    ]);
    setSent(true);
    setQuestion('');
  };

  return (
    <section id="chat" className="px-3 py-8 sm:px-5 sm:py-12">
      <div className="mx-auto grid max-w-[1120px] gap-3 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="tile bg-pink-soft p-5 sm:p-7">
          <span className="cap mb-1">Первый шаг</span>
          <h2 className="max-w-[520px] font-heading text-[26px] font-normal leading-[1.15] tracking-[-0.02em] sm:text-[30px]">
            Спросите — и мы <span className="mark-hl">спокойно ответим</span>
          </h2>
          <p className="mt-2 max-w-[460px] text-[14px] text-muted-foreground">
            Первые вопросы бесплатно и без карты. Мы напишем туда, где вам удобно.
          </p>

          <form onSubmit={submit} noValidate className="mt-5 grid gap-3 sm:grid-cols-2">
            <div>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ваше имя"
                className="h-12 w-full rounded-[11px] bg-card px-4 text-[14px] outline-none placeholder:text-muted-foreground/70"
              />
              {errors.name && <p className="mt-1 text-[12px] text-primary">{errors.name}</p>}
            </div>
            <div>
              <input
                value={contact}
                onChange={(e) => setContact(e.target.value)}
                placeholder="Почта или телефон"
                className="h-12 w-full rounded-[11px] bg-card px-4 text-[14px] outline-none placeholder:text-muted-foreground/70"
              />
              {errors.contact && <p className="mt-1 text-[12px] text-primary">{errors.contact}</p>}
            </div>
            <div className="sm:col-span-2">
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                rows={3}
                placeholder="Напишите так, как сказали бы подруге…"
                className="w-full resize-none rounded-[11px] bg-card p-4 text-[14px] outline-none placeholder:text-muted-foreground/70"
              />
              {errors.question && <p className="mt-1 text-[12px] text-primary">{errors.question}</p>}
            </div>
            <div className="flex flex-col gap-2 sm:col-span-2 sm:flex-row sm:items-center">
              <button
                type="submit"
                className="rounded-[11px] bg-primary px-6 py-3 text-[14px] font-medium text-primary-foreground transition-opacity hover:opacity-90"
              >
                Отправить вопрос
              </button>
              <span className="text-[12px] text-muted-foreground">
                Нажимая кнопку, вы соглашаетесь с политикой конфиденциальности.
              </span>
            </div>
          </form>
        </div>

        <div className="tile flex flex-col">
          <span className="cap text-center">Чат</span>
          <div className="flex-1 space-y-2 rounded-xl bg-inner p-3">
            {!sent && (
              <>
                <div className="flex items-center gap-2">
                  <Fox className="h-8 w-8 shrink-0" />
                  <div className="rounded-[10px] rounded-tl-[3px] bg-card px-3 py-2 text-[13px]">
                    Здравствуйте! Расскажите, что беспокоит.
                  </div>
                </div>
                <div className="flex items-center justify-end gap-2">
                  <div className="rounded-[10px] rounded-tr-[3px] bg-pink px-3 py-2 text-[13px]">
                    Пока просто смотрю…
                  </div>
                  <Bunny className="h-8 w-8 shrink-0" />
                </div>
              </>
            )}

            {messages.map((m) => (
              <div
                key={m.id}
                className={`animate-fade-up opacity-0 ${m.from === 'me' ? 'flex justify-end' : ''}`}
              >
                <div
                  className={`max-w-[92%] rounded-[10px] px-3 py-2 text-[13px] leading-[1.4] ${
                    m.from === 'me'
                      ? 'rounded-tr-[3px] bg-pink'
                      : m.from === 'doc'
                        ? 'rounded-tl-[3px] bg-card'
                        : 'rounded-tl-[3px] bg-sage-soft'
                  }`}
                >
                  {m.text}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-3 space-y-2 text-[13px]">
            <a
              href="mailto:hello@maminpomoshnik.ru"
              className="flex items-center gap-2 rounded-[10px] bg-inner px-3 py-2.5 transition-colors hover:bg-cream"
            >
              <Icon name="Mail" size={15} className="text-primary" />
              hello@maminpomoshnik.ru
            </a>
            <a
              href="tel:+78005553535"
              className="flex items-center gap-2 rounded-[10px] bg-inner px-3 py-2.5 transition-colors hover:bg-cream"
            >
              <Icon name="Phone" size={15} className="text-primary" />
              8 800 555-35-35
            </a>
            <div className="flex items-center gap-2 rounded-[10px] bg-inner px-3 py-2.5 text-muted-foreground">
              <Icon name="Clock" size={15} className="text-primary" />
              Чат отвечает круглосуточно
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Contacts;