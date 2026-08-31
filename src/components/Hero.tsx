import { AvatarCritter, Fox } from '@/components/Critters';

const Hero = () => {
  return (
    <section id="top" className="px-3 pt-3 sm:px-5 sm:pt-5">
      <div className="tile mx-auto flex max-w-[1240px] flex-col gap-6 p-6 sm:p-10 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex max-w-[560px] flex-col gap-4">
          <span className="cap">Мамин помощник</span>
          <h1 className="font-heading text-[32px] font-normal leading-[1.14] tracking-[-0.02em] sm:text-[42px]">
            Не форум и не поисковик.
            <br />
            Разговор, который <span className="mark-hl">слышит вас</span>.
          </h1>
          <p className="text-[15px] leading-[1.5] text-muted-foreground">
            Задайте вопрос один раз — получите два ответа: от врачей и от других мам.
            Отвечаем по проверенным источникам и живому опыту.
          </p>
          <div className="flex flex-wrap gap-2">
            <span className="flex h-9 items-center rounded-full bg-inner px-3.5 text-[13px] text-muted-foreground">
              Первые ответы бесплатно
            </span>
            <span className="flex h-9 items-center rounded-full bg-inner px-3.5 text-[13px] text-muted-foreground">
              Без диагнозов
            </span>
          </div>
          <div className="mt-1 flex flex-col gap-3 sm:flex-row sm:items-center">
            <a
              href="#chat"
              className="rounded-[11px] bg-primary px-6 py-3 text-center text-[15px] font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Написать сейчас
            </a>
            <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
              <AvatarCritter variant={1} className="h-6 w-6 overflow-hidden rounded-full" />
              Аня спросила про колики минуту назад
            </div>
          </div>
        </div>

        <Fox className="hidden h-24 w-24 shrink-0 opacity-90 lg:block" />
      </div>
    </section>
  );
};

export default Hero;
