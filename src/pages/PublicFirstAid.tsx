import { Link } from 'react-router-dom';
import FirstAid from '@/components/FirstAid';
import ThemeControl from '@/components/ThemeControl';

export default function PublicFirstAid(){
  return <main className="public-page public-first-aid">
    <nav className="public-page-nav" aria-label="Навигация первой помощи">
      <Link to="/">На главную</Link>
      <Link to="/chat">Открыть чат</Link>
      <ThemeControl />
    </nav>
    <h1>Первая помощь</h1>
    <FirstAid />
  </main>;
}
