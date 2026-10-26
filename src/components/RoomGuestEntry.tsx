import { Link } from "react-router-dom";
import { ArrowRight, CreditCard, Compass } from "lucide-react";
import "./room-guest.css";

/** First screen for a visitor who has not signed in: the room, the assistant's greeting, sign-in and optional tour. */
export default function RoomGuestEntry({ loginPath }: { loginPath: string }) {
  return <main className="room-guest" aria-labelledby="room-guest-title">
    <img className="room-guest-bg" src={`${import.meta.env.BASE_URL}media/room/rest-v12.webp`} alt="" aria-hidden="true" />
    <div className="room-guest-shade" aria-hidden="true" />
    <section className="room-guest-card">
      <span className="room-guest-eyebrow">Мамин помощник</span>
      <h1 id="room-guest-title">Я рядом.</h1>
      <p>Можно говорить обо всём, что волнует: сон, кормление, игры и ваше самочувствие.</p>
      <p className="room-guest-note">Чтобы сохранять профиль и историю, войдите в аккаунт. Диагнозы и назначения — к врачу.</p>
      <Link className="room-guest-primary" to={loginPath}>Войти или зарегистрироваться<ArrowRight size={18} aria-hidden="true" /></Link>
      <nav className="room-guest-links" aria-label="Ещё">
        <Link to="/about">О помощнике и примеры</Link>
        <Link to="/en" lang="en">English introduction</Link>
        <Link to="/?intro=1"><Compass size={18} aria-hidden="true" />Посмотреть знакомство</Link>
        <Link to="/billing"><CreditCard size={18} aria-hidden="true" />Цена и доступ</Link>
        <Link to="/first-aid">Срочная помощь · 112</Link>
      </nav>
    </section>
  </main>;
}
