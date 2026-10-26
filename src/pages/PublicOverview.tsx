import { useEffect } from "react";
import { Link } from "react-router-dom";
import "./public-overview.css";

/** Fixed editorial examples only: no account, child profile, AI call or email form. */
export default function PublicOverview({ english = false }: { english?: boolean }) {
  useEffect(() => {
    const oldTitle = document.title;
    const oldLanguage = document.documentElement.lang;
    document.title = english ? "Мамин помощник — English introduction" : "Мамин помощник — о помощнике";
    document.documentElement.lang = english ? "en" : "ru";
    return () => { document.title = oldTitle; document.documentElement.lang = oldLanguage; };
  }, [english]);

  const features = english ? [
    ["Questions, in one place", "A space for everyday parenting questions, with the active child’s profile kept separate. It does not replace a doctor."],
    ["Everyday notes", "Keep feeding, sleep and family notes together, so you can look back at your own records."],
    ["A book of memories", "Save the little moments you want to remember, in your own words."],
    ["Activities together", "Explore activities matched to the age in the active child’s profile. An adult chooses what suits the child today."],
  ] : [
    ["Вопросы в одном месте", "Повседневные вопросы о малыше — с учётом активного профиля. Помощник не заменяет врача."],
    ["Записи дня", "Сон, кормления и семейные заметки рядом: можно вернуться к собственным записям, когда это нужно."],
    ["Книга воспоминаний", "Маленькие моменты, которые хочется сохранить своими словами."],
    ["Занятия вместе", "Подборка учитывает возраст из активного профиля ребёнка. Подходящий вариант выбирает взрослый."],
  ];

  return <main className="public-overview" lang={english ? "en" : "ru"} aria-labelledby="overview-title">
    <header className="overview-header">
      <Link className="overview-brand" to={english ? "/en" : "/"} aria-label={english ? "Мамин помощник — English introduction" : "Мамин помощник — главная"}>
        <img src={`${import.meta.env.BASE_URL}logo-mark.png`} alt="" aria-hidden="true" width="52" height="52" />
        <span>Мамин помощник</span>
      </Link>
      <Link className="overview-language" to={english ? "/about" : "/en"} lang={english ? "ru" : "en"}>
        {english ? "Русская версия · Russian" : "English"}
      </Link>
    </header>

    <section className="overview-hero">
      <p className="overview-kicker">{english ? "For parents, from pregnancy through age six" : "Для мам и пап — от беременности до шести лет"}</p>
      <h1 id="overview-title">{english ? <>Everyday questions.<br />Little moments.<br />One place.</> : <>Вопросы о малыше.<br />Моменты вашей семьи.<br />В одном месте.</>}</h1>
      <p className="overview-lead">{english ? "Мамин помощник brings everyday questions, family notes, memories and shared activities together." : "Мамин помощник объединяет повседневные вопросы, записи, воспоминания и совместные занятия."}</p>
      {english && <aside className="overview-availability" aria-labelledby="availability-title">
        <h2 id="availability-title">English introduction, Russian application</h2>
        <p>The application currently works in Russian. A full English version is not available yet. These examples explain the features; they do not create an account or collect your email.</p>
      </aside>}
    </section>

    <section className="overview-features" aria-label={english ? "Features" : "Возможности"}>
      {features.map(([title, detail], i) => <article key={title}>
        <span className="overview-number" aria-hidden="true">0{i + 1}</span>
        <h2>{title}</h2><p>{detail}</p>
      </article>)}
    </section>

    <section className="overview-example" aria-labelledby="example-title">
      <div>
        <p className="overview-kicker">{english ? "An example, before signing in" : "Пример до регистрации"}</p>
        <h2 id="example-title">{english ? "A moment worth keeping." : "Момент, который хочется сохранить."}</h2>
        <p>{english ? "A memory can start with just a few words. This fixed example shows the idea of the memory book, without asking for details about your child." : "Воспоминание может начаться с пары строк. Этот пример показывает идею книги: чтобы посмотреть его, не нужно вводить сведения о ребёнке."}</p>
      </div>
      <figure className="overview-memory">
        <figcaption>{english ? "Example entry · fictional text" : "Пример записи · вымышленный текст"}</figcaption>
        <h3>{english ? "A walk after the rain" : "Прогулка после дождя"}</h3>
        <p>{english ? "The park smelled of wet leaves. We stopped by a puddle and watched the ripples together." : "В парке пахло мокрыми листьями. Мы остановились у лужи и вместе смотрели на круги по воде."}</p>
        <div className="overview-paper-rule" aria-hidden="true" />
        <p className="overview-memory-note">{english ? "A fixed illustration of an entry, not your saved record." : "Это иллюстрация записи, а не сохранённые данные вашей семьи."}</p>
      </figure>
    </section>

    <section className="overview-access" aria-labelledby="access-title">
      <h2 id="access-title">{english ? "What happens in the application" : "Как устроен доступ"}</h2>
      <p>{english ? "Personal features require an account. Activities use the active child’s profile; this page does not select an age or generate recommendations. Access and available services are explained in the Russian application." : "Для личных записей и подборок нужен аккаунт. Занятия учитывают возраст из активного профиля; здесь не выбирается возраст и не создаются рекомендации. Условия доступа указаны отдельно."}</p>
      {!english && <nav aria-label="Разделы помощника">
        <Link to="/account?mode=login&next=%2Fchat%3Fscene%3Droom">Аккаунт</Link>
        <Link to="/billing">Условия доступа</Link>
        <Link to="/">Главная</Link>
      </nav>}
    </section>
    <footer className="overview-footer">
      <p>{english ? "General information and family records do not replace medical care." : "Информация и семейные записи не заменяют медицинскую помощь."}</p>
      <nav aria-label={english ? "Information in Russian" : "Информация"}>
        <Link to="/privacy">{english ? "Privacy information (Russian)" : "Конфиденциальность"}</Link>
        <Link to="/terms">{english ? "Terms (Russian)" : "Условия использования"}</Link>
        {!english && <Link to="/first-aid">Срочная помощь · 112</Link>}
      </nav>
    </footer>
  </main>;
}
