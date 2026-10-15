import { useState } from 'react';
import type { ParentState } from '@/lib/parent-model';
import { monthsOld } from '../../ai-proxy/services';

export default function FoodPreparation({profile}: {profile: ParentState['profile']}) {
  const [ready, setReady] = useState(false);
  const age = monthsOld(profile);
  if (profile?.stage !== 'child' || age === null) return <p>Для карточек нужен профиль ребёнка с датой рождения.</p>;
  if (age < 6) return <p>До примерно шести месяцев эти карточки не предлагают прикорм. Индивидуальные вопросы питания обсудите с педиатром.</p>;
  return <details className="sleep-section">
    <summary>Наглядно: подготовка еды</summary>
    <p>Возраст сам по себе не подтверждает готовность. Эти схемы не назначают начало прикорма, рацион или размер порции.</p>
    <label className="flex items-start gap-3 py-3 min-h-11"><input type="checkbox" checked={ready} onChange={e=>setReady(e.target.checked)}/><span>Ребёнок устойчиво держит голову и сидит вертикально с подходящей поддержкой, координирует движения к еде и глотает её. Если не уверены — сначала уточните готовность у специалиста.</span></label>
    {ready && <>
      <h3>Мягкий овощ</h3>
      <svg role="img" aria-label="Овощ: приготовить до мягкости, размять, проверить температуру" viewBox="0 0 320 92" className="w-full max-w-sm"><path d="M32 30 Q46 14 60 30 L50 63 Q43 77 38 62Z" fill="#b96736"/><path d="M82 46H115M105 38L115 46 105 54" stroke="currentColor" fill="none"/><ellipse cx="164" cy="52" rx="28" ry="15" fill="#c8884e"/><path d="M211 46H244M234 38L244 46 234 54" stroke="currentColor" fill="none"/><ellipse cx="274" cy="49" rx="17" ry="10" fill="#c8884e"/><path d="M285 51L308 60" stroke="currentColor" strokeWidth="4"/></svg>
      <p>Приготовьте до мягкости, разомните в подходящую уже освоенным навыкам текстуру и остудите. Не предлагайте сырой твёрдый овощ кусочками.</p>
      <h3>Знакомый мягкий фрукт</h3>
      <p>Уберите косточки и твёрдые части. Разомните мягкую мякоть в знакомую ребёнку текстуру. Целые круглые плоды и твёрдые кусочки не подходят для этой схемы.</p>
      <h3>Во время еды</h3>
      <p>Ребёнок сидит вертикально, взрослый рядом и наблюдает. Не кормите лёжа, на ходу или в движущейся машине. Остановитесь, если ребёнок отворачивается или отказывается.</p>
    </>}
    <p className="muted">При трудностях глотания, особых ограничениях или недоношенности нужна индивидуальная рекомендация. Если ребёнок не может дышать — срочная помощь, 112.</p>
    <a className="standalone-link" href="/first-aid">Открыть первую помощь</a>
  </details>;
}
