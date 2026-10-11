import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

const NotFound = () => {
  return (
    <main className="public-page route-message">
      <h1>Страница не найдена</h1>
      <p>Возможно, ссылка устарела. Можно открыть чат или вернуться на главную.</p>
      <div className="flex flex-wrap gap-3">
        <Button asChild className="min-h-11"><Link to="/chat">Открыть чат</Link></Button>
        <Button asChild variant="outline" className="min-h-11"><Link to="/">На главную</Link></Button>
      </div>
      <Link className="standalone-link" to="/first-aid">Срочная помощь · 112</Link>
    </main>
  );
};

export default NotFound;
