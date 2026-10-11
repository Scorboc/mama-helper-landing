export function daysAgo(value: string, now = new Date()) {
  const date = new Date(value);
  // Calendar days, including daylight-saving transitions.
  return Math.round((Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) - Date.UTC(date.getFullYear(), date.getMonth(), date.getDate())) / 86400000);
}

export function careDay(value: string) {
  const days = daysAgo(value);
  if (days === 0) return "Сегодня";
  if (days === 1) return "Вчера";
  if (days === 2) return "Позавчера";
  return days > 0 ? `${days} дн. назад` : `${-days} дн. вперёд`;
}

export function careTime(value: string) {
  return `${careDay(value)} · ${new Date(value).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}`;
}
