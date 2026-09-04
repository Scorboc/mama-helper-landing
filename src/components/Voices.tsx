import { useState } from 'react';
import Icon from '@/components/ui/icon';
import { topics } from '@/data/content';
import { AvatarCritter, Fox } from '@/components/Critters';
import { Bib, Block, Bottle, HeartCloud, Pacifier, Socks } from '@/components/BabyIcons';

const topicArt: Record<string, JSX.Element> = {
  sleep: <Pacifier className="h-7 w-7" />,
  feeding: <Bottle className="h-7 w-7" />,
  vaccines: <Bib className="h-7 w-7" />,
  growth: <Block className="h-7 w-7" />,
  colic: <Socks className="h-7 w-7" />,
  mom: <HeartCloud className="h-7 w-7" />,
};

const highlight = (text: string, mark?: string) => {
  if (!mark || !text.includes(mark)) return text;
  const [before, after] = text.split(mark);
  return (
    <>
      {before}
      <span className="mark-hl">{mark}</span>
      {after}
    </>
  );
};

const Voices = () => {
  const [active, setActive] = useState(topics[0].id);
  const topic = topics.find((t) => t.id === active) ?? topics[0];

  return (
    <section id="voices" className="px-3 py-6 sm:px-5 sm:py-8">
      <div className="mx-auto max-w-[1120px]">
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <span className="cap mb-1">Суть сервиса</span>
            <h2 className="max-w-[600px] font-heading text-[26px] font-normal leading-[1.15] tracking-[-0.02em] sm:text-[30px]">
              Один вопрос — <span className="mark-hl">два ответа</span>: от врачей и от других мам.
            </h2>
          </div>
          <p className="max-w-[320px] text-[14px] text-muted-foreground">
            Выберите тему — и посмотрите, как выглядит настоящий ответ в чате.
          </p>
        </div>

        <div className="mb-3 flex flex-wrap gap-2">
          {topics.map((t) => (
            <button
              key={t.id}
              onClick={() => setActive(t.id)}
              className={`flex items-center gap-1.5 rounded-full py-1.5 pl-1.5 pr-4 text-[13px] transition-colors ${
                t.id === active
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-card text-muted-foreground hover:text-foreground'
              }`}
            >
              <span className="grid h-8 w-8 place-items-center rounded-full bg-card">
                {topicArt[t.id]}
              </span>
              {t.label}
            </button>
          ))}
        </div>

        <div className="tile">
          <div className="rounded-xl bg-inner p-3 sm:p-4">
            <div className="mb-3 flex items-center gap-2">
              <AvatarCritter variant={1} className="h-8 w-8 shrink-0 overflow-hidden rounded-full" />
              <div className="rounded-[10px] rounded-tl-[3px] bg-card px-3 py-2 text-[14px]">
                {topic.question}
              </div>
            </div>

            <div key={topic.id} className="grid animate-fade-up gap-3 opacity-0 md:grid-cols-2">
              <div className="rounded-[11px] bg-card p-4">
                <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
                  <span className="grid h-6 w-6 place-items-center rounded-full bg-pink-soft">
                    <Icon name="Stethoscope" size={13} />
                  </span>
                  Что говорят врачи
                </div>
                <p className="mt-2 font-heading text-[16px] leading-[1.4]">
                  {highlight(topic.doctor, topic.doctorMark)}
                </p>
              </div>

              <div className="rounded-[11px] bg-sage-soft p-4">
                <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
                  <span className="grid h-6 w-6 place-items-center rounded-full bg-card">
                    <Icon name="Heart" size={13} />
                  </span>
                  Что говорят другие мамы
                </div>
                <p className="mt-2 font-heading text-[16px] leading-[1.4]">{topic.mother}</p>
              </div>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            {topic.tags.map((t) => (
              <span
                key={t}
                className="rounded-[9px] bg-inner px-3 py-1.5 text-[12px] text-muted-foreground"
              >
                {t}
              </span>
            ))}
            <span className="ml-auto flex items-center gap-2 text-[12px] text-muted-foreground">
              <Fox className="h-6 w-6" />
              ответ приходит меньше чем за минуту
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Voices;