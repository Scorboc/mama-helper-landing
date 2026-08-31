import { AvatarCritter, Fox } from '@/components/Critters';

const Hero = () => {
  return (
    <section id="top" className="px-3 pt-3 sm:px-5 sm:pt-5">
      <div className="tile mx-auto max-w-[1120px] px-5 py-10 sm:px-8 sm:py-14">
        <div className="mx-auto flex max-w-[720px] flex-col items-center text-center">
          <Fox className="h-16 w-16" />
          <h1 className="mt-4 font-heading text-[32px] font-normal leading-[1.12] tracking-[-0.02em] sm:text-[44px]">
            Не форум и не поисковик.
            <br />
            Разговор, который <span className="mark-hl">слышит вас</span>.
          </h1>
          <p className="mt-4 max-w-[520px] text-[15px] leading-[1.55] text-muted-foreground sm:text-[16px]">
            Спросите своими словами в любое время — спокойно объясним, что известно
            по проверенным источникам и что помогало другим мамам.
          </p>

          <div className="mt-6 flex flex-col items-center gap-3 sm:flex-row">
            <a
              href="#chat"
              className="rounded-[11px] bg-primary px-6 py-3 text-[15px] font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Написать сейчас
            </a>
            <span className="text-[13px] text-muted-foreground">
              Первые ответы бесплатно, без карты
            </span>
          </div>

          <div className="mt-6 flex items-center gap-2 text-[12px] text-muted-foreground">
            <AvatarCritter variant={1} className="h-6 w-6 overflow-hidden rounded-full" />
            Аня спросила про колики минуту назад
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;