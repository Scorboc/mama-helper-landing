import Icon from '@/components/ui/icon';
import { Fox } from '@/components/Critters';
import { Bib, Block, Bottle, HeartCloud, Pacifier, Rattle } from '@/components/BabyIcons';

const steps = [
  {
    n: '01',
    art: <Pacifier className="h-9 w-9" />,
    title: 'Создаёте свой аккаунт',
    text: 'У мамы и папы отдельные входы, профили и переписки. Один ребёнок на аккаунт.',
    bg: 'bg-violet-soft',
  },
  {
    n: '02',
    art: <Bottle className="h-9 w-9" />,
    title: 'Указываете свой этап',
    text: 'Срок беременности или дата рождения. Можно добавить кормление, режим сна и выбранные темы.',
    bg: 'bg-cream',
  },
  {
    n: '03',
    art: <Bib className="h-9 w-9" />,
    title: 'Задаёте вопрос в чате',
    text: 'Помощник объясняет тему простыми шагами с учётом указанного этапа.',
    bg: 'bg-sage-soft',
  },
  {
    n: '04',
    art: <HeartCloud className="h-9 w-9" />,
    title: 'Настраиваете напоминания',
    text: 'Советник показывает карточки по возрасту. Повторы выбираете вы, карточку можно отложить или скрыть.',
    bg: 'bg-blue-soft',
  },
];

const HowItWorks = () => (
  <section id="how" className="px-3 py-6 sm:px-5 sm:py-8">
    <div className="mx-auto max-w-[1120px]">
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div>
          <span className="cap mb-1">Как это работает</span>
          <h2 className="mb-4 max-w-[620px] font-heading text-[26px] font-normal leading-[1.15] tracking-[-0.02em] sm:text-[30px]">
            Четыре шага к <span className="mark-hl">своему помощнику</span>
          </h2>

          <div className="grid gap-3 sm:grid-cols-2">
            {steps.map((s) => (
              <article key={s.n} className="tile group flex gap-3 transition-transform duration-200 hover:-translate-y-1">
                <span className={`grid h-14 w-14 shrink-0 place-items-center rounded-[16px] ${s.bg}`}>
                  <span className="transition-transform duration-200 group-hover:scale-110">
                    {s.art}
                  </span>
                </span>
                <div>
                  <div className="text-[12px] font-bold text-primary">{s.n}</div>
                  <h3 className="mt-0.5 font-heading text-[16px] font-medium">{s.title}</h3>
                  <p className="mt-1.5 text-[13px] leading-[1.45] text-muted-foreground">{s.text}</p>
                </div>
              </article>
            ))}
          </div>
        </div>

        <aside className="tile relative flex flex-col overflow-hidden bg-card">
          <Block className="pointer-events-none absolute -right-2 top-10 h-16 w-16 rotate-12 opacity-25" />
          <div className="relative flex items-center gap-2">
            <Fox className="h-11 w-11 shrink-0" />
            <Rattle className="h-8 w-8 shrink-0 -rotate-12" />
            <span className="cap mb-0">Наш принцип</span>
          </div>
          <div className="relative mt-4 space-y-2.5">
            {[
              'Мы не ставим диагнозы',
              'Не назначаем лечение',
              'Не пугаем и не осуждаем',
              'При опасности — помощь специалистов',
            ].map((t) => (
              <div key={t} className="flex items-center gap-2 rounded-[10px] bg-inner px-3 py-2 text-[13px]">
                <Icon name="Check" size={15} className="text-primary" />
                {t}
              </div>
            ))}
          </div>
          <p className="mt-4 text-[11px] leading-[1.45] text-muted-foreground">
            Сервис информационный и не заменяет очный приём врача.
          </p>
        </aside>
      </div>
    </div>
  </section>
);

export default HowItWorks;
