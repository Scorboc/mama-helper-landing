export type CareRecord = {
  id: string;
  kind: "sleep" | "wake" | "feeding" | "food" | "achievement" | "mood";
  at: string;
  end?: string;
  note?: string;
  value?: string;
  side?: string;
  sleepType?: "day" | "night";
  wakeType?: "morning" | "night";
  settlingAt?: string;
  feeling?: string;
};

export type CareSummary = {
  periodDays: number;
  timezone: string;
  periodStart: string;
  periodEnd: string;
  records: number;
  recordedDays: number;
  completeness: "unknown";
  sleep: { sleepRecords: number; ongoing: boolean; days: { date: string; recordedSleepMinutes: number }[] };
  feeding: { records: number; lastRecordedAt: string | null; ongoingTimers: number };
};

export function journalDay(value: string | number, timezone = "Europe/Moscow") {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(value));
  const part = (kind: string) => parts.find((p) => p.type === kind)?.value || "";
  return [part("year"), part("month"), part("day")].join("-");
}

export function recordInPeriod(record: CareRecord, days: number, now: number, timezone = "Europe/Moscow") {
  if (record.kind === "mood" || !Number.isFinite(Date.parse(record.at)) || Date.parse(record.at) > now) return false;
  const lastDay = journalDay(now, timezone);
  const first = new Date(lastDay + "T12:00:00Z");
  first.setUTCDate(first.getUTCDate() - days + 1);
  const firstDay = first.toISOString().slice(0, 10);
  const startDay = journalDay(record.at, timezone);
  if (startDay >= firstDay) return true;
  return record.kind === "sleep" && journalDay(record.end || now, timezone) >= firstDay;
}

const recordLabels = { sleep: "Сон", wake: "Пробуждение", feeding: "Кормление", food: "Прикорм", achievement: "Наблюдение / новое умение", mood: "Самочувствие родителя" };

export function buildConsultationReport({ profile, records, selected, days, timezone = "Europe/Moscow", now = Date.now(), questions = "", appointments = [], achievements = [] }: {
  profile: { childName?: string; stage: string; birthDate?: string };
  records: CareRecord[];
  selected: string[];
  days: number;
  timezone?: string;
  now?: number;
  questions?: string;
  appointments?: { date: string; reason: string; questions: string; instructions: string }[];
  achievements?: { date: string; note: string }[];
}) {
  const time = (value: string | number) => new Date(value).toLocaleString("ru-RU", { timeZone: timezone, dateStyle: "short", timeStyle: "short" });
  const chosen = records.filter((r) => selected.includes(r.id) && recordInPeriod(r, days, now, timezone))
    .sort((a, b) => Date.parse(a.at) - Date.parse(b.at));
  const feedingCount = chosen.filter((r) => r.kind === "feeding").length;
  const sleepCount = chosen.filter((r) => r.kind === "sleep").length;
  return [
    "MAMA Helper — записи для консультации",
    "Профиль: " + (profile.childName || (profile.stage === "pregnancy" ? "Беременность" : "Ребёнок")),
    profile.stage === "child" ? "Дата рождения: " + (profile.birthDate || "не указана") : "Этап: беременность",
    "Период: последние " + days + " календарных дней, включая сегодня. Часовой пояс: " + timezone + ". Сформировано: " + time(now),
    "Включено только выбранное: " + chosen.length + " записей; эпизодов сна: " + sleepCount + "; отметок кормлений: " + feedingCount + ". Полнота дневника неизвестна; отсутствие записи не означает отсутствие события.",
    ...chosen.map((r) => {
      const label = r.kind === "sleep" ? (r.sleepType === "day" ? "Дневной сон" : r.sleepType === "night" ? "Ночной сон" : "Сон") : r.kind === "wake" && r.wakeType === "morning" ? "Утренний подъём" : recordLabels[r.kind];
      const side = { left: "левая грудь", right: "правая грудь", bottle: "бутылочка" }[r.side || ""] || "";
      const end = r.end ? "Окончание: " + time(r.end) + "." : r.kind === "sleep" ? "Окончание не отмечено." : r.kind === "feeding" ? "Событие; длительность не указана." : "";
      return [time(r.at) + " — " + label, r.value, side, r.note, r.settlingAt ? "Начало укладывания: " + time(r.settlingAt) : "", end].filter(Boolean).join(" · ");
    }),
    ...appointments.map((a) => "Приём " + a.date + ": " + a.reason + "\nВопросы: " + a.questions + "\nСо слов родителя, после приёма: " + a.instructions),
    ...achievements.map((a) => "Наблюдение " + a.date + ": " + a.note),
    "Вопросы специалисту: " + (questions.trim() || "не добавлены"),
    "Это записи родителя, не диагноз и не медицинское заключение. Они не определяют норму сна, достаточность питания или точное время следующего сна. Переписка и самочувствие родителя не включены. Проверьте текст перед передачей.",
  ].filter(Boolean).join("\n\n");
}
