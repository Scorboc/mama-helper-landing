import { Link, useLocation } from "react-router-dom";
import { campaignAccountPath } from "@/lib/campaign-entry";
import example from "@/content/campaign-game.json";
import "./campaign-games.css";

/** Public editorial example: no profile, contact collection or access grant. */
export default function CampaignGames() {
  const { search } = useLocation();
  return <main className="campaign-games public-page">
    <nav className="campaign-games__links" aria-label="Навигация страницы">
      <Link className="back-link" to="/">На главную</Link>
      <Link to="/first-aid">Срочная помощь · 112</Link>
    </nav>
    <header>
      <p className="campaign-games__brand">MAMA Helper · Мамин помощник</p>
      <h1>Одна идея для спокойной игры</h1>
      <p>В помощнике есть игры по возрасту, дневник и чат. Здесь можно посмотреть пример без регистрации.</p>
      <p>Закрытое тестирование · доступ по приглашениям.</p>
      <a className="standalone-link" href="#invite-heading">Как получить приглашение</a>
    </header>
    <section className="campaign-games__example" aria-labelledby="game-example">
      <p className="campaign-games__eyebrow">Пример из каталога · {example.completedMonths} полных месяцев · около {example.minutes} минут</p>
      <h2 id="game-example">{example.title}</h2>
      <p><strong>Приготовьте:</strong> {example.materials}.</p>
      <p>{example.instructions}</p>
      <p className="campaign-games__note">Это пример для указанного возраста, а не подбор для вашего ребёнка и не проверка его навыков. Играйте вместе со взрослым, используйте целые крупные игрушки по возрасту без мелких деталей. При усталости или отказе остановитесь.</p>
    </section>
    <section className="campaign-games__invite" aria-labelledby="invite-heading">
      <h2 id="invite-heading">Хотите посмотреть помощник?</h2>
      <p>Сейчас идёт закрытое тестирование. Если вы пришли из ролика, оставьте «ИГРЫ» в комментариях под ним. Не пишите там имя, дату рождения, сведения о здоровье ребёнка или контакты.</p>
      <p>Запрос на приглашение рассматривает команда вручную. Комментарий не создаёт аккаунт и не открывает доступ автоматически. О сроках ответа и наличии мест можно спросить под тем же роликом, без личных данных.</p>
      <Link className="campaign-games__button" to={campaignAccountPath(search)}>Уже есть доступ — войти</Link>
      <p>Получили приглашение? Откройте ссылку из сообщения команды. Регистрация сама по себе не заменяет приглашение.</p>
    </section>
    <nav aria-label="Полезные ссылки" className="campaign-games__links">
      <Link to="/guide">Что есть в помощнике</Link>
      <Link to="/privacy">О данных</Link>
      <Link to="/first-aid">Срочная помощь · 112</Link>
    </nav>
  </main>;
}
