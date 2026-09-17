import {Link} from 'react-router-dom';
import {CalendarDays,Heart,BookOpen,ClipboardList,ShieldCheck,MessageCircle} from 'lucide-react';
const features=[
 [CalendarDays,'От совета к действию','Сохраните следующий шаг, выберите дату и расскажите, помог ли он.'],
 [BookOpen,'Игры именно для вас','Небольшой план по возрасту и идеи из вещей, которые уже есть дома.'],
 [ClipboardList,'Меньше держать в голове','Дневник, вопросы к врачу и заметки после приёма — в одном кабинете.'],
 [Heart,'Забота о родителях','Поддержка в трудный момент, отдельные сценарии для папы и подготовка к переменам.'],
 [ShieldCheck,'Понятные границы','Видно, на чём основан ответ и загружался ли официальный материал. Без обещаний безошибочности.'],
 [MessageCircle,'Результат имеет значение','Помощник учитывает ваши сохранённые наблюдения и то, что уже пробовали.'],
] as const;
export default function WhatsNew(){return <section id="whats-new" className="px-3 py-8 sm:px-5"><div className="mx-auto max-w-[1120px]"><span className="cap">Что нового</span><h2 className="font-heading text-3xl mb-3">Не только разговор. <span className="mark-hl">Забота каждый день.</span></h2><p className="text-muted-foreground mb-5">Вы выбираете темп. Никаких оценок родительства и обязательных ежедневных заданий.</p><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{features.map(([Icon,title,description])=><article className="tile p-5" key={title}><Icon className="text-primary mb-3" size={26}/><h3 className="font-heading text-xl">{title}</h3><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p></article>)}</div><div className="flex flex-wrap gap-4 mt-6"><Link to="/cabinet" className="rounded-full bg-primary px-6 py-3 text-white">Открыть мой день</Link><a href="/mamin-pomoshchnik-new-features.pdf" className="rounded-full bg-white px-6 py-3 text-primary" target="_blank" rel="noreferrer">Что нового — памятка PDF</a></div></div></section>;}
