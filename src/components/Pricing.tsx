import { useState } from 'react';
import Icon from '@/components/ui/icon';
import { plans } from '@/data/content';

const Pricing = () => {
  const [yearly, setYearly] = useState(false);

  const priceOf = (raw: string) => {
    const value = parseInt(raw, 10);
    return yearly ? `${Math.round(value * 0.8)} ₽` : raw;
  };

  return (
    <section id="pricing" className="px-3 py-8 sm:px-5 sm:py-12">
      <div className="mx-auto max-w-[1120px]">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <span className="cap mb-1">Тарифы</span>
            <h2 className="font-heading text-[26px] font-normal leading-[1.15] tracking-[-0.02em] sm:text-[30px]">
              Подписка дешевле одного приёма
            </h2>
          </div>
          <div className="flex items-center gap-1 self-start rounded-full bg-card p-1 text-[13px]">
            <button
              onClick={() => setYearly(false)}
              className={`rounded-full px-4 py-2 transition-colors ${
                !yearly ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'
              }`}
            >
              Помесячно
            </button>
            <button
              onClick={() => setYearly(true)}
              className={`rounded-full px-4 py-2 transition-colors ${
                yearly ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'
              }`}
            >
              На год −20%
            </button>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {plans.map((p) => (
            <article
              key={p.name}
              className={`tile flex flex-col ${p.hot ? 'bg-pink-soft' : ''}`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[13px] text-muted-foreground">{p.name}</span>
                {p.hot && (
                  <span className="rounded-full bg-card px-2.5 py-1 text-[11px]">чаще всего</span>
                )}
              </div>
              <div className="mt-2 flex items-baseline gap-1.5">
                <span className="font-heading text-[30px] font-medium">{priceOf(p.price)}</span>
                <span className="text-[12px] text-muted-foreground">{p.period}</span>
              </div>

              <ul className="mt-3 flex-1 space-y-2">
                {p.features.map((f) => (
                  <li key={f} className="flex gap-2 text-[13px] leading-[1.4] text-muted-foreground">
                    <Icon name="Check" size={15} className="mt-0.5 shrink-0 text-primary" />
                    {f}
                  </li>
                ))}
              </ul>

              <a
                href="#chat"
                className={`mt-4 block rounded-[11px] py-2.5 text-center text-[14px] font-medium transition-opacity hover:opacity-90 ${
                  p.hot ? 'bg-primary text-primary-foreground' : 'bg-inner text-foreground'
                }`}
              >
                Попробовать
              </a>
            </article>
          ))}
        </div>

        <p className="mt-3 text-center text-[12px] text-muted-foreground">
          Первые вопросы бесплатно и без карты. Отмена подписки в один клик.
        </p>
      </div>
    </section>
  );
};

export default Pricing;
