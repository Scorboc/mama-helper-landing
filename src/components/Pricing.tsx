import { useState } from 'react';
import Icon from '@/components/ui/icon';
import { dadPlan, stages } from '@/data/content';
import { Bib, Block, Bottle, Pacifier, Stroller } from '@/components/BabyIcons';

const stageArt: Record<string, JSX.Element> = {
  pregnancy: <Bottle className="h-8 w-8" />,
  newborn: <Pacifier className="h-8 w-8" />,
  baby: <Bib className="h-8 w-8" />,
  toddler: <Block className="h-8 w-8" />,
};

const stageTint: Record<string, string> = {
  pregnancy: 'bg-violet-soft',
  newborn: 'bg-pink-soft',
  baby: 'bg-sage-soft',
  toddler: 'bg-blue-soft',
};

const Pricing = () => {
  const [active, setActive] = useState('newborn');
  const current = stages.find((s) => s.id === active) ?? stages[1];

  return (
    <section id="pricing" className="px-3 py-6 sm:px-5 sm:py-8">
      <div className="mx-auto max-w-[1120px]">
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <span className="cap mb-1">Подписка</span>
            <h2 className="max-w-[620px] font-heading text-[26px] font-normal leading-[1.15] tracking-[-0.02em] sm:text-[30px]">
              Одна подписка, которая <span className="mark-hl">растёт вместе с малышом</span>
            </h2>
          </div>
          <p className="max-w-[300px] text-[14px] text-muted-foreground">
            Цена не меняется — меняются вопросы. Выберите свой этап и посмотрите, о чём
            будем говорить.
          </p>
        </div>

        <div className="tile relative overflow-hidden p-0">
          <span className="blob -left-20 -top-20 h-56 w-56 bg-violet/20" />
          <span className="blob -bottom-20 -right-16 h-56 w-56 bg-teal/20" />

          <div className="relative grid gap-0 lg:grid-cols-[340px_minmax(0,1fr)]">
            <div className="border-b border-border p-4 lg:border-b-0 lg:border-r">
              <div className="mb-3 text-[12px] font-medium text-muted-foreground">
                Ваш этап пути
              </div>
              <div className="flex flex-col gap-2">
                {stages.map((s, i) => {
                  const on = s.id === active;
                  return (
                    <button
                      key={s.id}
                      onClick={() => setActive(s.id)}
                      className={`flex items-center gap-3 rounded-[16px] p-2 text-left transition-all ${
                        on
                          ? 'bg-gradient-to-r from-violet to-blue text-white shadow-[0_8px_18px_-8px_hsl(258_62%_49%_/_0.6)]'
                          : 'bg-inner hover:bg-violet-soft'
                      }`}
                    >
                      <span
                        className={`grid h-11 w-11 shrink-0 place-items-center rounded-[14px] ${
                          on ? 'bg-white/85' : stageTint[s.id]
                        }`}
                      >
                        {stageArt[s.id]}
                      </span>
                      <span className="min-w-0">
                        <span
                          className={`block text-[11px] ${on ? 'text-white/75' : 'text-muted-foreground'}`}
                        >
                          {s.stage} · {s.age}
                        </span>
                        <span className="block truncate font-heading text-[15px] font-medium">
                          {s.name}
                        </span>
                      </span>
                      {i < stages.length - 1 && (
                        <span className="ml-auto shrink-0">
                          <Icon
                            name="ChevronRight"
                            size={16}
                            className={on ? 'text-white/70' : 'text-muted-foreground'}
                          />
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-col p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <span className="inline-block rounded-full bg-violet-soft px-3 py-1 text-[11px] font-semibold text-primary">
                    {current.stage} · {current.age}
                  </span>
                  <h3 className="mt-2 font-heading text-[22px] font-medium">{current.name}</h3>
                  <p className="mt-1 max-w-[400px] text-[13px] leading-[1.45] text-muted-foreground">
                    {current.lead}
                  </p>
                </div>
                <div className="rounded-[18px] bg-inner px-4 py-3 text-center">
                  <div className="font-heading text-[30px] font-medium leading-none">490 ₽</div>
                  <div className="mt-1 text-[11px] text-muted-foreground">в месяц</div>
                </div>
              </div>

              <ul className="mt-4 grid gap-2 sm:grid-cols-2">
                {current.features.map((f) => (
                  <li
                    key={f}
                    className="flex gap-2 rounded-[12px] bg-inner px-3 py-2 text-[13px] leading-[1.35]"
                  >
                    <Icon name="Check" size={15} className="mt-0.5 shrink-0 text-primary" />
                    {f}
                  </li>
                ))}
              </ul>

              <div className="mt-4 flex flex-wrap items-center gap-3">
                <a
                  href="#top"
                  className="rounded-full bg-gradient-to-r from-violet to-blue px-6 py-3 text-[14px] font-semibold text-white shadow-[0_8px_20px_-6px_hsl(258_62%_49%_/_0.6)] transition-transform hover:-translate-y-0.5"
                >
                  Начать с этого этапа
                </a>
                <span className="text-[12px] text-muted-foreground">
                  Этап меняется сам — переплачивать не нужно
                </span>
              </div>
            </div>
          </div>
        </div>

        <article className="tile relative mt-3 overflow-hidden">
          <span className="blob -right-16 -top-16 h-48 w-48 bg-blue/25" />
          <div className="relative grid gap-4 lg:grid-cols-[minmax(0,1fr)_400px] lg:items-center">
            <div>
              <div className="flex items-start gap-3">
                <span className="grid h-14 w-14 shrink-0 place-items-center rounded-[18px] bg-blue-soft">
                  <Stroller className="h-9 w-9" />
                </span>
                <div>
                  <h3 className="font-heading text-[20px] font-medium">{dadPlan.name}</h3>
                  <p className="mt-1 max-w-[440px] text-[13px] leading-[1.45] text-muted-foreground">
                    {dadPlan.lead}
                  </p>
                </div>
              </div>

              <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                {dadPlan.features.map((f) => (
                  <li
                    key={f}
                    className="flex gap-2 rounded-[12px] bg-inner px-3 py-2 text-[13px] leading-[1.35]"
                  >
                    <Icon name="Check" size={15} className="mt-0.5 shrink-0 text-accent" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>

            <div className="grid gap-2 sm:grid-cols-2">
              {dadPlan.options.map((o) => (
                <div
                  key={o.id}
                  className="flex flex-col rounded-[18px] border border-border bg-inner p-3"
                >
                  <div className="text-[12px] font-medium">{o.title}</div>
                  <div className="mt-0.5 text-[11px] leading-[1.35] text-muted-foreground">
                    {o.note}
                  </div>
                  <div className="mt-2 font-heading text-[24px] font-medium leading-none">
                    {o.price}
                  </div>
                  <div className="mt-1 text-[11px] text-muted-foreground">{o.period}</div>
                  <a
                    href="#top"
                    className="mt-3 block rounded-full bg-gradient-to-r from-blue to-teal py-2 text-center text-[12px] font-semibold text-white shadow-[0_6px_14px_-6px_hsl(232_70%_60%_/_0.7)] transition-transform hover:-translate-y-0.5"
                  >
                    {o.cta}
                  </a>
                </div>
              ))}
            </div>
          </div>
        </article>

        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          {[
            { icon: 'Infinity', t: 'Все этапы включены', d: 'Малыш растёт — чат меняется вместе с ним, доплат нет' },
            { icon: 'Lock', t: 'Личная переписка', d: 'У каждого своя подписка и свой чат — вопросы видите только вы' },
            { icon: 'HeartHandshake', t: 'Отмена в один клик', d: 'Первые вопросы бесплатно и без привязки карты' },
          ].map((b) => (
            <div key={b.t} className="tile flex gap-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-[13px] bg-violet-soft">
                <Icon name={b.icon} size={18} className="text-primary" />
              </span>
              <div>
                <div className="font-heading text-[14px] font-medium">{b.t}</div>
                <p className="mt-1 text-[12px] leading-[1.4] text-muted-foreground">{b.d}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Pricing;