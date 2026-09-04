import Icon from '@/components/ui/icon';
import { plans } from '@/data/content';
import { Bib, Bottle, Rattle, Stroller } from '@/components/BabyIcons';

const planArt = [
  <Stroller className="h-9 w-9" key="a" />,
  <Bottle className="h-9 w-9" key="b" />,
  <Rattle className="h-9 w-9" key="c" />,
  <Bib className="h-9 w-9" key="d" />,
];

const Pricing = () => {
  return (
    <section id="pricing" className="px-3 py-6 sm:px-5 sm:py-8">
      <div className="mx-auto max-w-[1120px]">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <span className="cap mb-1">Тарифы</span>
            <h2 className="font-heading text-[26px] font-normal leading-[1.15] tracking-[-0.02em] sm:text-[30px]">
              Подписка дешевле одного приёма
            </h2>
          </div>
          <span className="self-start rounded-full bg-card px-4 py-2 text-[13px] text-muted-foreground">
            Оплата помесячно
          </span>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {plans.map((p, i) => (
            <article
              key={p.name}
              className={`tile flex flex-col transition-transform duration-200 hover:-translate-y-1 ${p.hot ? 'bg-pink-soft' : ''}`}
            >
              <div className="flex items-center justify-between">
                <span className="grid h-12 w-12 place-items-center rounded-[14px] bg-inner">
                  {planArt[i % planArt.length]}
                </span>
                {p.hot && (
                  <span className="rounded-full bg-card px-2.5 py-1 text-[11px]">чаще всего</span>
                )}
              </div>
              <span className="mt-2 text-[13px] text-muted-foreground">{p.name}</span>
              <div className="mt-2 flex items-baseline gap-1.5">
                <span className="font-heading text-[30px] font-medium">{p.price}</span>
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
                href="#top"
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