export const milestoneLabels = { roll: "Переворачивается", crawl: "Ползает", stand: "Встаёт у опоры", walk: "Ходит", words: "Первые слова" } as const;
export type MilestoneSkill = keyof typeof milestoneLabels;
export const milestoneQuestions: Record<MilestoneSkill, string> = {
  roll: "Уже получается переворачиваться?",
  crawl: "Уже получается ползать?",
  stand: "Уже получается вставать у опоры?",
  walk: "Уже получается делать первые самостоятельные шаги?",
  words: "Уже появились первые слова?",
};
// Format calendar dates in UTC so the displayed day never shifts with the device timezone.
export function formatMilestoneDate(day: string, today: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return "";
  const date = new Date(day + "T12:00:00Z");
  if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== day) return "";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric", month: "long", ...(day.slice(0, 4) !== today.slice(0, 4) ? { year: "numeric" as const } : {}), timeZone: "UTC",
  }).format(date);
}
export function isMilestoneSkill(value: unknown): value is MilestoneSkill {
  return typeof value === "string" && Object.prototype.hasOwnProperty.call(milestoneLabels, value);
}
// Conservative: uncertainty, questions, regression or another child suppress the entire offer.
export function detectMilestones(text: string): MilestoneSkill[] {
  const t = text.toLowerCase().replace(/ё/g, "е");
  if (/(?:пошел|пошла)\s+(?:в|на|к|гулять|спать|дождь|снег)(?=$|[^а-я])/u.test(t)) return [];
  if (/(?:^|[^а-я])(?:я|мы|муж|папа|дождь|снег|поезд|автобус|скоро|завтра|будет|планируем|пытается)(?=$|[^а-я])/u.test(t)) return [];
  if (/[?？]|(?:^|[^а-я])(?:не|нет|перестал[аи]?|разучил[а-я]*|утратил[а-я]*|потерял[а-я]*|забыл[а-я]*|раньше|если|когда|кажется|вроде|почти|пока|хочу|научить|чужой|сосед[а-я]*|племян[а-я]*|старш[а-я]*)(?=$|[^а-я])/u.test(t)) return [];
  const patterns: Record<MilestoneSkill, RegExp> = {
    roll: /(?:^|[^а-я])(?:перевернул(?:ся|ась)|переворачивается)(?=$|[^а-я])/u,
    crawl: /(?:^|[^а-я])(?:пополз(?:ла)?|ползает)(?=$|[^а-я])/u,
    stand: /(?:^|[^а-я])(?:встал(?:а)?|встает)\s+(?:сам(?:а)?\s+)?у\s+опоры(?=$|[^а-я])/u,
    walk: /(?:^|[^а-я])(?:пошел|пошла|ходит сам(?:а)?|сделал[а]? первые шаги)(?=$|[^а-я])/u,
    words: /(?:^|[^а-я])(?:сказал[а]? первое слово|первые слова|заговорил[а]?)(?=$|[^а-я])/u,
  };
  return (Object.keys(patterns) as MilestoneSkill[]).filter(skill => patterns[skill].test(t));
}
export function milestoneFromSearch(search: string, childIds: string[]) {
  const p = new URLSearchParams(search), skill = p.get("mark"), childId = p.get("child");
  if (p.getAll("mark").length !== 1 || p.getAll("child").length !== 1 || !isMilestoneSkill(skill) || !childId || !/^[a-zA-Z0-9-]{1,100}$/.test(childId) || !childIds.includes(childId)) return null;
  return { skill, childId };
}
