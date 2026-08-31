import { Bear, Bunny, Cat, Elephant, Fox, Hedgehog, Owl, Sheep } from '@/components/Critters';

const items = [
  { title: 'Сон', desc: 'Ночные пробуждения, ритуалы, режим по возрасту.', node: <Owl className="h-14 w-14" />, bg: 'bg-sage-soft' },
  { title: 'Кормление', desc: 'Грудное, смесь, прикорм и вечный вопрос «хватает ли».', node: <Bunny className="h-14 w-14" />, bg: 'bg-cream' },
  { title: 'Прививки', desc: 'Календарь, реакции, что считается нормой.', node: <Fox className="h-14 w-14" />, bg: 'bg-pink-soft' },
  { title: 'Развитие', desc: 'Что умеет в этом месяце и когда стоит подождать.', node: <Elephant className="h-14 w-14" />, bg: 'bg-inner' },
  { title: 'Здоровье', desc: 'Температура, сыпь, животик — и когда пора к врачу.', node: <Hedgehog className="h-14 w-14" />, bg: 'bg-cream' },
  { title: 'Беременность', desc: 'Недели, анализы, самочувствие и тревоги.', node: <Sheep className="h-14 w-14" />, bg: 'bg-pink-soft' },
  { title: 'Мама', desc: 'Усталость, восстановление, право на свои два часа.', node: <Cat className="h-14 w-14" />, bg: 'bg-sage-soft' },
  { title: 'Папа', desc: 'Короткие ответы «что делать прямо сейчас».', node: <Bear className="h-14 w-14" />, bg: 'bg-inner' },
];

const Topics = () => (
  <section id="topics" className="px-3 py-8 sm:px-5 sm:py-12">
    <div className="mx-auto max-w-[1120px]">
      <span className="cap mb-1">Круг тем</span>
      <h2 className="mb-4 max-w-[620px] font-heading text-[26px] font-normal leading-[1.15] tracking-[-0.02em] sm:text-[30px]">
        О чём спрашивают чаще всего
      </h2>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((it) => (
          <article
            key={it.title}
            className="tile group transition-transform duration-200 hover:-translate-y-1"
          >
            <div className={`grid h-24 place-items-center rounded-xl ${it.bg}`}>
              <div className="transition-transform duration-200 group-hover:scale-110">{it.node}</div>
            </div>
            <h3 className="mt-3 font-heading text-[17px] font-medium">{it.title}</h3>
            <p className="mt-1 text-[13px] leading-[1.45] text-muted-foreground">{it.desc}</p>
          </article>
        ))}
      </div>
    </div>
  </section>
);

export default Topics;
