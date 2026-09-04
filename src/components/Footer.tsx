import { AvatarCritter } from '@/components/Critters';
import { HeartCloud, Socks } from '@/components/BabyIcons';

const Footer = () => (
  <footer className="px-3 pb-5 sm:px-5">
    <div className="relative mx-auto max-w-[1120px] overflow-hidden rounded-2xl bg-card p-5 sm:p-7">
      <Socks className="pointer-events-none absolute -right-3 top-4 h-20 w-20 rotate-12 opacity-20" />
      <HeartCloud className="pointer-events-none absolute -left-4 bottom-2 h-20 w-20 opacity-15" />
      <div className="relative flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <AvatarCritter variant={0} className="h-9 w-9 overflow-hidden rounded-full" />
            <span className="font-heading text-[16px] font-medium">Мамин помощник</span>
          </div>
          <p className="mt-2 max-w-[320px] text-[13px] leading-[1.5] text-muted-foreground">
            Спокойные ответы на вопросы о беременности, малыше и вас самой.
          </p>
        </div>

        <nav className="grid grid-cols-2 gap-x-8 gap-y-2 text-[13px] text-muted-foreground sm:grid-cols-3">
          {[
            { href: '#voices', label: 'Как отвечаем' },
            { href: '#how', label: 'Как это работает' },
            { href: '#pricing', label: 'Тарифы' },
          ].map((l) => (
            <a key={l.href} href={l.href} className="transition-colors hover:text-foreground">
              {l.label}
            </a>
          ))}
        </nav>
      </div>

      <div className="mt-6 rounded-[11px] bg-inner px-4 py-3 text-[12px] leading-[1.5] text-muted-foreground">
        Сервис носит информационный характер, не ставит диагнозы и не заменяет очную консультацию
        врача. При тревожных симптомах обращайтесь к специалисту или вызывайте скорую помощь.
      </div>

      <div className="mt-4 flex flex-col gap-2 text-[12px] text-muted-foreground sm:flex-row sm:justify-between">
        <span>© {new Date().getFullYear()} Мамин помощник</span>
        <span>Политика конфиденциальности · Оферта</span>
      </div>
    </div>
  </footer>
);

export default Footer;