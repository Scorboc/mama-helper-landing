import { AvatarCritter, Bunny, Fox, Owl } from '@/components/Critters';

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

          <div className="tile flex flex-1 flex-col bg-pink">
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
          <div className="tile flex flex-1 flex-col justify-center">
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
          </div>
        </div>

        {/* ---------- правая область ---------- */}
        <div className="grid animate-fade-up grid-cols-1 gap-3 opacity-0 [animation-delay:160ms]">
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

          <div className="tile flex flex-col">
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
        </div>
      </div>
    </section>
  );
};

export default Hero;