import { AvatarCritter, Fox } from '@/components/Critters';

const Hero = () => {
  return (
    <section id="top" className="px-3 pt-3 sm:px-5 sm:pt-5">
      <div className="tile mx-auto max-w-[1120px] px-5 py-7 sm:px-8 sm:py-9">
        <div className="mx-auto flex max-w-[680px] flex-col items-center text-center">
          <Fox className="h-12 w-12" />
          <h1 className="mt-3 font-heading text-[28px] font-normal leading-[1.12] tracking-[-0.02em] sm:text-[38px]">
            Не форум и не поисковик.
            <br />
            Разговор, который <span className="mark-hl">слышит вас</span>.
          </h1>
          <p className="mt-3 max-w-[520px] text-[14px] leading-[1.5] text-muted-foreground sm:text-[15px]">
            Спросите своими словами в любое время — спокойно объясним, что известно
            по проверенным источникам и что помогало другим мамам.
          </p>

          <div className="mt-5 flex flex-wrap items-center justify-center gap-x-4 gap-y-2">
            <a
              href="#pricing"
              className="rounded-[11px] bg-primary px-5 py-2.5 text-[14px] font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Написать сейчас
            </a>
            <span className="text-[13px] text-muted-foreground">
              Первые ответы бесплатно, без карты
            </span>
            <span className="flex items-center gap-2 text-[12px] text-muted-foreground">
              <AvatarCritter variant={1} className="h-5 w-5 overflow-hidden rounded-full" />
              Аня спросила про колики минуту назад
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;