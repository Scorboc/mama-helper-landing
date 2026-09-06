import Header from '@/components/Header';
import Hero from '@/components/Hero';
import { Bib, Bottle, Pacifier, Rattle, Socks, HeartCloud } from '@/components/BabyIcons';
import { Fox } from '@/components/Critters';

const topics = [
  { title: 'Ожидание малыша', text: 'Вопросы о беременности, подготовке к родам и первым дням дома. Помочь составить список вопросов для врача.', icon: Pacifier, bg: 'bg-violet-soft' },
  { title: 'Кормление без растерянности', text: 'Грудное и смешанное вскармливание, прикорм и бытовые вопросы питания. Понятные объяснения без осуждения вашего выбора.', icon: Bottle, bg: 'bg-cream' },
  { title: 'Сон и ежедневный уход', text: 'Гигиена, купание, прогулки, организация сна и домашнего быта. Разобраться в рекомендациях по шагам.', icon: Bib, bg: 'bg-blue-soft' },
  { title: 'Играем и растём', text: 'Идеи игр, общения и занятий по возрасту. Вопросы о движении и развитии без гонки за чужими достижениями.', icon: Rattle, bg: 'bg-sage-soft' },
  { title: 'Забота о родителях', text: 'Поддержка при усталости, стрессе и тревоге. Посильные способы сделать паузу, попросить помощи и позаботиться о себе.', icon: HeartCloud, bg: 'bg-pink-soft' },
  { title: 'Нужное — в своё время', text: 'Возрастные ориентиры и напоминания о новых темах ухода. Частоту повторов выбираете вы; возраст сам по себе не назначает процедур.', icon: Socks, bg: 'bg-violet-soft' },
];
export default function Index() {
  return <div className="min-h-screen overflow-x-hidden bg-background text-foreground">
    <Header /><main><Hero />
    <section id="help" className="scroll-mt-24 px-3 py-8 sm:px-5"><div className="mx-auto max-w-[1120px]">
      <span className="cap">О чём можно будет поговорить</span>
      <h2 className="mb-3 font-heading text-3xl sm:text-4xl">Маленькие вопросы. <span className="mark-hl">Большая поддержка.</span></h2>
      <p className="mb-6 max-w-2xl text-base leading-relaxed text-muted-foreground">Мы создаём помощника для этих задач. Сейчас можно познакомиться с интерфейсом и готовыми сценариями; свободные ответы появятся после подключения AI.</p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{topics.map(({title,text,icon:Art,bg}) => <article key={title} className="tile relative p-6 transition-transform motion-safe:hover:-translate-y-1"><span className={`mb-5 grid h-16 w-16 place-items-center rounded-[20px] ${bg}`}><Art className="h-11 w-11" /></span><h3 className="mb-3 font-heading text-xl font-medium">{title}</h3><p className="text-base leading-relaxed text-muted-foreground">{text}</p></article>)}</div>
    </div></section>
    <section id="parents" className="scroll-mt-24 px-3 py-6 sm:px-5"><div className="mx-auto grid max-w-[1120px] gap-4 md:grid-cols-2">
      <article className="tile bg-pink-soft p-7"><HeartCloud className="mb-4 h-14 w-14" /><h2 className="mb-4 font-heading text-3xl">Маме — немного опоры</h2><p className="mb-5 text-base leading-relaxed">Здесь можно говорить не только о малыше, но и о себе. Устать, растеряться, попросить поддержки — с этим не обязательно оставаться одной.</p><ul className="space-y-3 text-base"><li>«Я устала и чувствую вину. Как попросить помощи?»</li><li>«Какие вопросы о восстановлении задать врачу?»</li><li>«Как подготовиться к первым дням с малышом?»</li></ul></article>
      <article className="tile bg-blue-soft p-7"><Fox className="mb-4 h-14 w-14" /><h2 className="mb-4 font-heading text-3xl">Папе — своё место рядом</h2><p className="mb-5 text-base leading-relaxed">Вы тоже учитесь быть родителем. Вопросы об уходе, отношениях и собственных переживаниях важны не меньше.</p><ul className="space-y-3 text-base"><li>«Как взять на себя часть забот о малыше?»</li><li>«Как поддержать партнёршу и не забыть о себе?»</li><li>«Во что играть с ребёнком нашего возраста?»</li></ul></article>
    </div></section>
    <section className="px-3 py-8 sm:px-5"><div className="tile relative mx-auto max-w-[1120px] overflow-hidden p-7 sm:p-10"><span className="blob -right-12 -top-16 h-64 w-64 bg-orange/25" /><div className="relative flex flex-col justify-between gap-6 md:flex-row md:items-center"><div><h2 className="font-heading text-3xl">Можно начать с простого: «Мне нужна поддержка»</h2><p className="mt-3 max-w-2xl text-base leading-relaxed text-muted-foreground">В демо доступны готовые ответы, тестовый профиль и пример возрастного напоминания. Переписка сбрасывается при обновлении страницы.</p></div><a href="/chat" className="shrink-0 rounded-full bg-gradient-to-r from-violet to-blue px-7 py-4 text-center font-semibold text-white shadow-lg">Познакомиться с чатом</a></div></div></section>
    </main><footer className="mx-auto max-w-[1120px] px-5 pb-8 text-sm leading-relaxed text-muted-foreground"><p>Мамин помощник · Для мам и пап · Беременность и первые три года</p><p className="mt-2">Информационная поддержка не заменяет врача и не предназначена для назначения лечения. При угрозе жизни звоните 112. Не вводите личные медицинские данные в демо.</p></footer>
  </div>;
}
