import { useState } from 'react';
import Icon from '@/components/ui/icon';
import { reviews } from '@/data/content';
import { AvatarCritter } from '@/components/Critters';

const Reviews = () => {
  const [index, setIndex] = useState(0);
  const move = (dir: number) =>
    setIndex((i) => (i + dir + reviews.length) % reviews.length);

  return (
    <section id="reviews" className="px-3 py-8 sm:px-5 sm:py-12">
      <div className="mx-auto max-w-[1120px]">
        <div className="mb-4 flex items-end justify-between gap-3">
          <div>
            <span className="cap mb-1">Отзывы</span>
            <h2 className="font-heading text-[26px] font-normal leading-[1.15] tracking-[-0.02em] sm:text-[30px]">
              Что пишут мамы
            </h2>
          </div>
          <div className="flex gap-2">
            <button
              aria-label="Предыдущий отзыв"
              onClick={() => move(-1)}
              className="grid h-10 w-10 place-items-center rounded-full bg-card transition-colors hover:bg-inner"
            >
              <Icon name="ArrowLeft" size={18} />
            </button>
            <button
              aria-label="Следующий отзыв"
              onClick={() => move(1)}
              className="grid h-10 w-10 place-items-center rounded-full bg-card transition-colors hover:bg-inner"
            >
              <Icon name="ArrowRight" size={18} />
            </button>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <article key={index} className="tile flex animate-fade-up flex-col justify-between bg-pink-soft opacity-0 p-5 sm:p-7">
            <p className="font-heading text-[19px] leading-[1.4] sm:text-[23px]">
              «{reviews[index].text}»
            </p>
            <div className="mt-5 flex items-center gap-3">
              <AvatarCritter
                variant={reviews[index].variant}
                className="h-11 w-11 overflow-hidden rounded-full"
              />
              <div>
                <div className="font-heading text-[15px] font-medium">{reviews[index].name}</div>
                <div className="text-[12px] text-muted-foreground">{reviews[index].role}</div>
              </div>
            </div>
          </article>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <div className="tile">
              <div className="font-heading text-[30px] font-medium">42 000</div>
              <p className="mt-1 text-[13px] text-muted-foreground">
                вопросов задано за последний год
              </p>
            </div>
            <div className="tile bg-sage-soft">
              <div className="font-heading text-[30px] font-medium">меньше минуты</div>
              <p className="mt-1 text-[13px] text-muted-foreground">
                среднее время ожидания ответа
              </p>
            </div>
            <div className="tile sm:col-span-2 lg:col-span-1">
              <div className="flex flex-wrap gap-1.5">
                {reviews.map((r, i) => (
                  <button
                    key={r.name}
                    onClick={() => setIndex(i)}
                    className={`rounded-full px-3 py-1.5 text-[12px] transition-colors ${
                      i === index ? 'bg-primary text-primary-foreground' : 'bg-inner text-muted-foreground'
                    }`}
                  >
                    {r.name}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Reviews;