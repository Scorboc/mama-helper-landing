/* Public interface review only. No real accounts, external AI or remote writes. */
(() => {
  'use strict';
  const base = '/mama-helper-landing/';
  const realFetch = window.fetch.bind(window);
  const key = 'mama_room_public_preview_20261018';
  const profile = { childName: 'Малыш', childSex: 'unknown', role: 'mom', stage: 'child', birthDate: '2025-09-01', week: 20, weekDate: '2026-10-18', feeding: 'mixed', sleep: '', health: '', healthConfirmed: false, topics: [] };
  const initial = { activeChildId: 'primary', profile, saved: [], completed: [], events: {}, preferences: { repeat: 'never', push: false }, messages: [
    { id: 'preview-user', role: 'user', text: 'Мне сейчас нужна поддержка' },
    { id: 'preview-assistant', role: 'assistant', text: 'Расскажите, что сейчас даётся сложнее всего. Разберёмся вместе, шаг за шагом.' }
  ], medicalCard: [] };
  let state = structuredClone(initial);
  let revision = 1;
  try { const saved = JSON.parse(localStorage.getItem(key) || 'null'); if (saved?.profile && Array.isArray(saved.messages)) { state = saved; if (state.profile.childName === 'Тестовый профиль') state.profile.childName = 'Малыш'; } } catch { /* View still works without storage. */ }
  const store = () => { try { localStorage.setItem(key, JSON.stringify(state)); } catch { /* Optional local review state. */ } };
  const response = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
  const session = () => ({ user: { id: 'public-visual-preview', email: '1', emailVerified: true }, state, revision, quota: { limit: 50, used: 0, remaining: 50 }, billing: { mode: 'test', priceRub: 480, answerLimit: 50, paymentConfigured: false } });
  const target = new URL(location.href).searchParams.get('__route');
  if (target?.startsWith('/') && !target.startsWith('//')) history.replaceState(null, '', base.replace(/\/$/, '') + target);
  window.fetch = async (input, options = {}) => {
    const url = new URL(typeof input === 'string' ? input : input.url, location.href);
    if (url.origin !== location.origin) return realFetch(input, options);
    if (url.pathname === '/app-config.json' || url.pathname === base + 'app-config.json') return response({ apiUrl: base + '__preview-api' });
    if (url.pathname !== base + '__preview-api') return realFetch(input, options);
    let data;
    try { data = JSON.parse(options.body || '{}'); } catch { return response({ error: 'Не удалось прочитать запрос.' }, 400); }
    switch (data.action) {
      case 'session': return response(session());
      case 'save': if (data.state) { state = data.state; revision++; store(); } return response({ revision, state });
      case 'care-list': return response({ profile: state.profile, contextVersion: 'visual-preview', records: [], daily: [], achievements: [], appointments: [], permission: 'owner', authors: {} });
      case 'family-list': return response({ items: [] });
      case 'service': return response({ items: [], blocks: [] });
      case 'suggestion-list': return response({ phase: 'collecting', week: 'preview', canSubmit: false, remainingSubmissions: 0, submissionCount: 0, items: [], myVote: null, winners: [] });
      case 'chat': {
        const answer = 'Ответы ИИ доступны в полной версии сайта.';
        const question = data.question || data.message || '';
        state = { ...state, messages: [...state.messages, { id: crypto.randomUUID(), role: 'user', text: question }, { id: crypto.randomUUID(), role: 'assistant', text: answer }] };
        revision++; store();
        return response({ answer, state, revision, quota: session().quota });
      }
      default: return response({ error: 'Это действие доступно в полной версии сайта.' }, 409);
    }
  };
})();
