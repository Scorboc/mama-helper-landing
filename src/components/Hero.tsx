import { Bib, Bottle, Pacifier, Rattle, Socks, Stroller } from '@/components/BabyIcons';

const Hero = () => {
  return (
    <section id="top" className="px-3 pt-3 sm:px-5 sm:pt-5">
      <div className="tile relative mx-auto max-w-[1120px] overflow-hidden px-5 py-7 sm:px-8 sm:py-9">
        <span className="blob -left-16 -top-16 h-56 w-56 bg-violet/25" />
        <span className="blob -right-12 -top-10 h-52 w-52 bg-orange/25" />
        <span className="blob -bottom-16 left-1/3 h-56 w-56 bg-teal/25" />
        <span className="blob -bottom-12 -right-16 h-52 w-52 bg-coral/25" />

        <Rattle className="pointer-events-none absolute left-2 top-6 hidden h-16 w-16 -rotate-12 lg:block" />
        <Socks className="pointer-events-none absolute right-3 top-8 hidden h-16 w-16 rotate-12 lg:block" />
        <Stroller className="pointer-events-none absolute bottom-4 left-10 hidden h-14 w-14 lg:block" />
        <Bottle className="pointer-events-none absolute bottom-5 right-12 hidden h-14 w-14 rotate-6 lg:block" />

        <div className="relative mx-auto flex max-w-[680px] flex-col items-center text-center">
          <div className="mb-1 flex items-center gap-3">
            <Pacifier className="h-9 w-9" />
            <img src="/logo-mark.png" alt="Мамин помощник" className="h-20 w-auto" />
            <Bib className="h-9 w-9" />
          </div>
          <h1 className="mt-3 font-heading text-[28px] font-normal leading-[1.12] tracking-[-0.02em] sm:text-[38px]">
            Забота о малыше.
            <br />
            Поддержка для <span className="mark-hl">мамы и папы</span>.
          </h1>
          <p className="mt-3 max-w-[520px] text-[14px] leading-[1.5] text-muted-foreground sm:text-[15px]">
            Беременность и первые три года: ответы в чате, забота о себе,
            идеи общения и возрастные напоминания. Всё в своём темпе.
          </p>

          <div className="mt-5 flex flex-wrap items-center justify-center gap-x-4 gap-y-2">
            <a
              href="/account"
              className="rounded-full bg-gradient-to-r from-violet to-blue px-6 py-3 text-[14px] font-semibold text-white shadow-[0_8px_20px_-6px_hsl(258_62%_49%_/_0.6)] transition-transform hover:-translate-y-0.5"
            >
              Создать личный кабинет
            </a>
            <span className="text-[13px] text-muted-foreground">
              Тест без оплаты · небольшой демо-чат
            </span>
            <a href="/account" className="text-[14px] text-primary underline">Войти в тестовый чат</a>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
