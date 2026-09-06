export type Profile = { stage: 'pregnancy' | 'child'; age: number; role: string };
export type Reply = { text: string; mode: 'simple' | 'deep' | 'urgent'; source?: string };
export const sources = { stress: 'https://www.who.int/publications/i/item/9789240003927', feeding: 'https://www.who.int/publications/i/item/9789240081864' };
// Demonstration only: keyword routing is NOT reliable clinical triage.
export function routeQuestion(question: string): Reply['mode'] {
  if (/не дыш|задыха|потер.*созн|без созн|судорог|суицид|убить|навредить|не хочу жить|покончить|кровотеч/iu.test(question)) return 'urgent';
  if (/бол|температур|лекар|доз|сып|рвот|беремен|корм|прикорм|груд|депресс|паник|стресс|тревог|гимнаст|зарядк/iu.test(question)) return 'deep';
  return 'simple';
}
export function demoReply(question: string, profile: Profile): Reply {
  const mode = routeQuestion(question);
  if (mode === 'urgent') return { mode, text: 'Если прямо сейчас есть угроза жизни или риск причинить вред себе либо ребёнку, позвоните 112. По возможности пригласите рядом взрослого, которому доверяете. Не ждите ответа чата. Демо не может оценить срочность состояния.' };
  if (/стресс|устал|тревог|поддерж|выгор/iu.test(question)) return { mode: 'deep', source: sources.stress, text: 'Вам не обязательно справляться со всем в одиночку. Можно сделать небольшую паузу: почувствовать опору под ногами, заметить окружающие звуки и предметы, затем выбрать одно посильное действие. Это краткий пример техники заземления из руководства ВОЗ, а не лечение. Если состояние мешает повседневной жизни или не проходит, обратитесь к специалисту. В демо я не могу провести индивидуальную беседу.' };
  if (/прикорм/iu.test(question)) return { mode: 'deep', source: sources.feeding, text: `${profile.stage === 'child' ? `В профиле указан возраст: ${profile.age} мес. ` : ''}ВОЗ рекомендует вводить прикорм в возрасте 6 месяцев. Это общий ориентир, а не индивидуальное назначение: особенности здоровья и готовность ребёнка нужно обсуждать с педиатром. В демо нет персональных схем, дозировок или меню.` };
  if (mode === 'deep') return { mode, text: 'Это вопрос о здоровье или индивидуальном уходе. Без подключённого AI и подходящих проверенных материалов я не могу безопасно дать персональную рекомендацию. Запишите для врача возраст или срок, что беспокоит и когда это началось. При угрозе жизни звоните 112. Не используйте демо для назначения лечения.' };
  if (/пап|помоч|помощь|обязан/iu.test(question)) return { mode, text: 'Можно начать с конкретного предложения: «Я возьму на себя ужин и покупки. Что ещё сейчас облегчит тебе день?» Обсудите, кому нужен отдых и какие бытовые дела можно отложить. Это готовый пример разговора, не индивидуальная рекомендация AI.' };
  return { mode, text: 'Сейчас я работаю без AI API и показываю только готовые сценарии. Попробуйте «Мне нужна поддержка», «Когда вводить прикорм?» или «Как папе помочь?». Свободный диалог появится после подключения провайдера. Демо не оценивает развитие и не назначает процедуры.' };
}
// Replace with a call to your own authenticated server. Never expose keys via VITE_*.
export const assistant = { async reply(question: string, profile: Profile): Promise<Reply> { return demoReply(question, profile); } };
