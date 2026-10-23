import { Link } from "react-router-dom";

const sections = [
  ["home", "Сегодня"], ["chat", "Чат"], ["trackers", "Записи"],
  ["favorites", "Избранное"], ["more", "Профиль"],
] as const;
export type RoomSection = typeof sections[number][0];

/** One geometry and label set for workspace tabs and standalone routes. */
export default function RoomNavigation({ active, onNavigate }: {
  active: RoomSection;
  onNavigate?: (section: RoomSection) => void;
}) {
  return <nav className="cabinet-tabs room-navigation" aria-label="Разделы личного кабинета">
    {sections.map(([id, label]) => {
      const props = { "aria-label": label, "aria-current": active === id ? "page" as const : undefined, "data-state": active === id ? "active" : "inactive" };
      return onNavigate
        ? <button type="button" key={id} {...props} onClick={() => onNavigate(id)}><span>{label}</span></button>
        : <Link key={id} {...props} to={`/chat?scene=room&tab=${id}`}><span>{label}</span></Link>;
    })}
  </nav>;
}
