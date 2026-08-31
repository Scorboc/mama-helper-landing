import { AvatarCritter, Bear, Bunny, Fox, Owl, SleepingBear } from '@/components/Critters';

const Hero = () => {
  return (
    <section id="top" className="px-3 pt-3 sm:px-5 sm:pt-5">
      <div className="mx-auto grid max-w-[1240px] grid-cols-1 gap-3 lg:grid-cols-[340px_380px_1fr]">
        {/* ---------- левая колонка ---------- */}
        <div className="flex animate-fade-up flex-col gap-3 opacity-0 [animation-delay:40ms]">
          <h1 className="px-0.5 pt-1 font-heading text-[30px] font-normal leading-[1.14] tracking-[-0.02em] sm:text-[34px]">
            Не форум и не поисковик.
            <br />
            Разговор, который <span className="mark-hl">слышит вас</span>.
          </h1>
          <p className="px-0.5 text-[15px] leading-[1.4] text-muted-foreground">
            Отвечаем по проверенным источникам и живому опыту мам.
          </p>
          <div className="flex flex-wrap gap-2">
            <span className="flex h-10 items-center rounded-[11px] bg-card px-3.5 text-[13px]">
              Первые ответы бесплатно
            </span>
            <span className="flex h-10 items-center rounded-[11px] bg-card px-3.5 text-[13px]">
              Без диагнозов
            </span>
          </div>

          <div className="tile flex flex-1 flex-col">
            <span className="cap text-center">Ваш круг тем.</span>
            <div className="flex flex-1 items-center justify-center py-1">
              <div
                className="relative h-[200px] w-[200px] rounded-full sm:h-[236px] sm:w-[236px]"
                style={{
                  background:
                    'radial-gradient(circle at 50% 50%, hsl(var(--card)) 0 6%, transparent 34%), conic-gradient(hsl(var(--pink)), hsl(var(--mark)), hsl(var(--sage)), hsl(var(--night)), hsl(var(--pink)))',
                }}
              >
                <span className="absolute left-[6%] top-[46%] h-3 w-3 rounded-full bg-card" />
                <span className="absolute right-[22%] top-[12%] h-3 w-3 rounded-full bg-card" />
                <span className="absolute bottom-[12%] left-[32%] h-3 w-3 rounded-full bg-card" />
                <span className="absolute left-1/2 top-1/2 -ml-[13px] -mt-[13px] h-[26px] w-[26px] rounded-full bg-card" />
              </div>
            </div>
          </div>

          <div className="tile bg-pink">
            <div className="text-[13px] text-foreground/75">Сегодня беспокоит</div>
            <div className="mt-1 font-heading text-[22px] font-medium">Сон малыша</div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <div className="grid h-[52px] place-items-center overflow-hidden rounded-[10px] bg-cream">
                <Bunny className="h-11 w-11" />
              </div>
              <div className="grid h-[52px] place-items-center overflow-hidden rounded-[10px] bg-sage-soft">
                <Owl className="h-11 w-11" />
              </div>
            </div>
          </div>
        </div>

        {/* ---------- средняя колонка ---------- */}
        <div className="flex animate-fade-up flex-col gap-3 opacity-0 [animation-delay:100ms]">
          <div className="tile flex flex-1 flex-col">
            <span className="cap text-center">Ваш собеседник.</span>
            <div className="flex justify-center">
              <div className="grid h-[168px] w-[168px] place-items-center rounded-full bg-inner">
                <Fox className="h-[124px] w-[124px]" />
              </div>
            </div>
            <div className="mx-auto mt-3 grid h-10 w-full max-w-[264px] place-items-center rounded-xl bg-inner font-heading text-[17px] font-medium">
              Мамин помощник
            </div>
            <p className="mt-2 text-center text-[13px] text-muted-foreground">
              Спросите так, как сказали бы подруге.
            </p>

            <div className="mt-3 rounded-[13px] bg-inner p-3">
              <div className="grid grid-cols-4 gap-2">
                {[
                  { node: <Bunny className="h-11 w-11" />, label: 'беременность' },
                  { node: <Fox className="h-11 w-11" />, label: 'малыш' },
                  { node: <Owl className="h-11 w-11" />, label: 'вы сами' },
                  { node: <Bear className="h-11 w-11" />, label: 'папам' },
                ].map((s) => (
                  <div key={s.label} className="text-center">
                    <div className="mx-auto grid aspect-square w-full max-w-[74px] place-items-center rounded-full bg-card">
                      {s.node}
                    </div>
                    <span className="mt-1.5 block text-[12px] text-muted-foreground">{s.label}</span>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex h-11 items-center justify-between rounded-full bg-card px-3">
                {['pink', 'mark', 'sage', 'cream', 'night', 'fur', 'gold', 'pink-soft'].map((t) => (
                  <span
                    key={t}
                    className="h-[26px] w-[26px] rounded-full"
                    style={{ background: `hsl(var(--${t}))` }}
                  />
                ))}
              </div>
            </div>
          </div>

          <div className="tile">
            <span className="cap text-center">Ваш вечер.</span>
            <div
              className="relative mt-0.5 h-[150px] overflow-hidden rounded-[10px]"
              style={{ background: 'linear-gradient(180deg, hsl(var(--night)), hsl(var(--pink-soft)))' }}
            >
              <span className="absolute right-[34px] top-[18px] h-[34px] w-[34px] rounded-full bg-mark" />
              <span className="absolute left-[44px] top-[26px] h-[5px] w-[5px] rounded-full bg-cream" />
              <span className="absolute left-[96px] top-[52px] h-[5px] w-[5px] rounded-full bg-cream" />
              <span className="absolute left-[220px] top-[18px] h-[5px] w-[5px] rounded-full bg-cream" />
              <SleepingBear className="absolute -bottom-1.5 left-1/2 w-[130px] -translate-x-1/2" />
            </div>
          </div>
        </div>

        {/* ---------- правая область ---------- */}
        <div className="grid animate-fade-up grid-cols-1 gap-3 opacity-0 [animation-delay:160ms] sm:grid-cols-[200px_1fr]">
          <div className="tile">
            <span className="cap text-center">Ваша неделя.</span>
            <div className="grid h-24 place-items-center rounded-[10px] bg-sage-soft">
              <svg viewBox="0 0 80 70" className="w-[70px]">
                <circle cx="40" cy="38" r="24" fill="hsl(var(--pink))" />
                <circle cx="46" cy="42" r="11" fill="hsl(var(--cream))" />
                <circle cx="40" cy="14" r="8" fill="hsl(var(--pink))" />
              </svg>
            </div>
            <div className="mt-2 text-center text-[12px] text-muted-foreground">23-я · спокойно</div>
          </div>

          <div className="tile flex flex-col">
            <span className="cap text-center">Ваш первый шаг.</span>
            <div className="text-center font-heading text-[30px] font-normal tracking-[-0.02em]">
              Открыть чат
            </div>
            <a
              href="#chat"
              className="mx-auto mt-2 block h-[38px] w-[200px] rounded-[11px] bg-primary text-center text-[15px] font-medium leading-[38px] text-primary-foreground transition-opacity hover:opacity-90"
            >
              Написать сейчас
            </a>
            <div className="mt-3 flex items-center gap-2 text-[12px] text-muted-foreground">
              <AvatarCritter variant={1} className="h-6 w-6 overflow-hidden rounded-full" />
              Аня спросила про колики минуту назад.
            </div>
          </div>

          <div className="tile flex flex-col sm:col-span-2">
            <span className="cap text-center">Два голоса в ответе.</span>
            <div className="relative flex-1 rounded-xl bg-inner p-3.5 pt-12">
              <div className="absolute left-2.5 top-2.5 rounded-[10px] bg-card px-3 py-1.5 text-[13px]">
                Вопрос: «Малыш не спит ночью»
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-[11px] bg-card p-3">
                  <div className="text-[12px] text-muted-foreground">Что говорят врачи</div>
                  <p className="mt-1.5 font-heading text-[15px] leading-[1.36]">
                    В 4 месяца сон перестраивается. Ритуал и <span className="mark-hl">тишина за час</span>{' '}
                    до сна помогают заснуть быстрее.
                  </p>
                </div>
                <div className="rounded-[11px] bg-sage-soft p-3">
                  <div className="text-[12px] text-muted-foreground">Что говорят другие мамы</div>
                  <p className="mt-1.5 font-heading text-[15px] leading-[1.36]">
                    У многих помогает тёплая ванна и одна и та же колыбельная. Это проходит.
                  </p>
                </div>
              </div>
            </div>
            <div className="mt-2.5 flex flex-wrap gap-2">
              {['проверено', 'живой опыт', 'без цитат'].map((t) => (
                <span
                  key={t}
                  className="rounded-[9px] bg-inner px-3 py-1.5 text-[12px] text-muted-foreground"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>

          <div className="tile sm:col-span-2">
            <span className="cap text-center">Ваш тариф.</span>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {[
                { n: 'Беременность', p: '440 ₽', hot: false },
                { n: 'Первый год', p: '540 ₽', hot: true },
                { n: 'Для пап', p: '340 ₽', hot: false },
                { n: 'Вместе', p: '590 ₽', hot: false },
              ].map((pl) => (
                <div
                  key={pl.n}
                  className={`rounded-[11px] px-3 py-2.5 ${pl.hot ? 'bg-pink-soft' : 'bg-inner'}`}
                >
                  <div className="text-[12px] text-muted-foreground">{pl.n}</div>
                  <div className="mt-1 font-heading text-[17px] font-medium">{pl.p}</div>
                </div>
              ))}
            </div>
            <p className="mt-2.5 text-center text-[11px] text-muted-foreground">
              Не заменяет консультацию врача и не ставит диагнозы.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;