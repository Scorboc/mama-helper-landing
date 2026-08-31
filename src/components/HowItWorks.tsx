import Icon from '@/components/ui/icon';
import { Fox } from '@/components/Critters';

const steps = [
  {
    n: '01',
    icon: 'MessageCircle',
    title: 'Спрашиваете своими словами',
    text: 'Без анкет и медицинских терминов. Так, как написали бы подруге в мессенджер — хоть в три часа ночи.',
    bg: 'bg-pink-soft',
  },
  {
    n: '02',
    icon: 'BookOpenCheck',
    title: 'Врачебная часть ответа',
    text: 'Собираем то, что говорят клинические рекомендации и наши консультанты-педиатры. Без диагнозов и без страшилок.',
    bg: 'bg-cream',
  },
  {
    n: '03',
    icon: 'Users',
    title: 'Голос других мам',
    text: 'Рядом — обезличенный опыт тех, кто уже прошёл через тот же вопрос. Что помогало, а что оказалось лишним.',
    bg: 'bg-sage-soft',
  },
  {
    n: '04',
    icon: 'HeartHandshake',
    title: 'Решаете спокойно',
    text: 'Два голоса рядом — и видно, где медицина, а где чужой опыт. Если случай срочный, мы сразу скажем идти к врачу.',
    bg: 'bg-inner',
  },
];

const HowItWorks = () => (
  <section id="how" className="px-3 py-8 sm:px-5 sm:py-12">
    <div className="mx-auto max-w-[1120px]">
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div>
          <span className="cap mb-1">Как это работает</span>
          <h2 className="mb-4 max-w-[620px] font-heading text-[26px] font-normal leading-[1.15] tracking-[-0.02em] sm:text-[30px]">
            Четыре шага от тревоги до <span className="mark-hl">спокойного решения</span>
          </h2>

          <div className="grid gap-3 sm:grid-cols-2">
            {steps.map((s) => (
              <article key={s.n} className="tile flex gap-3">
                <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-[12px] ${s.bg}`}>
                  <Icon name={s.icon} size={20} />
                </span>
                <div>
                  <div className="text-[12px] text-muted-foreground">{s.n}</div>
                  <h3 className="mt-0.5 font-heading text-[16px] font-medium">{s.title}</h3>
                  <p className="mt-1.5 text-[13px] leading-[1.45] text-muted-foreground">{s.text}</p>
                </div>
              </article>
            ))}
          </div>
        </div>

        <aside className="tile flex flex-col justify-between bg-card">
          <div className="flex items-center gap-3">
            <Fox className="h-11 w-11 shrink-0" />
            <span className="cap mb-0">Наш принцип</span>
          </div>
          <div className="mt-4 space-y-2.5">
            {[
              'Мы не ставим диагнозы',
              'Не назначаем лечение',
              'Не пугаем и не осуждаем',
              'Говорим, когда пора к врачу',
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