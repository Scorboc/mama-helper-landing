import type { ParentState } from './parent-model';

export function conversationList(state: ParentState) {
  const active = { id: state.conversationId || 'legacy-active', title: state.conversationTitle || 'Общий разговор', messages: state.messages };
  const items = [active, ...(state.conversations || []).filter(t => t.id !== active.id)];
  const order = state.conversationOrder || items.map(t => t.id);
  return items.sort((a, b) => {
    const rank = (id: string) => { const index = order.indexOf(id); return index < 0 ? order.length : index; };
    return rank(a.id) - rank(b.id);
  });
}

export function openConversation(state: ParentState, request: { id: string } | { title: string }, newId = () => crypto.randomUUID()): ParentState {
  const items = conversationList(state);
  const activeId = state.conversationId || 'legacy-active';
  if ('id' in request && request.id === activeId) return state;
  if ('title' in request && (!request.title.trim() || items.length >= 21)) return state;
  const target = 'id' in request ? items.find(t => t.id === request.id) : { id: newId(), title: request.title.trim().slice(0, 80), messages: [] };
  if (!target) return state;
  const all = items.some(t => t.id === target.id) ? items : [...items, target];
  return { ...state, conversationId: target.id, conversationTitle: target.title, messages: target.messages,
    conversationOrder: all.map(t => t.id), conversations: all.filter(t => t.id !== target.id) };
}
