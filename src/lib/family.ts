import { emptyState, type ParentState, type Message } from './parent-model';
import { randomId } from './id';

export const childKeys = ['profile', 'messages', 'medicalCard', 'pendingMemory', 'conversations', 'conversationTitle', 'conversationId', 'conversationOrder', 'events', 'care', 'saved', 'completed'] as const;
export type ChildData = Pick<ParentState, typeof childKeys[number]>;
export type ChildRecord = {id: string; data: ChildData};
export type Favorite = {id: string; childId: string; childName: string; text: string; question: string; savedAt: string};
export function childData(state: ParentState): ChildData {
  return Object.fromEntries(childKeys.map(key => [key, state[key]])) as ChildData;
}
export function familyList(state: ParentState): ChildRecord[] {
  return [{id: state.activeChildId || 'primary', data: childData(state)}, ...(state.children || [])];
}
export function switchChild(state: ParentState, id: string): ParentState {
  const all = familyList(state), target = all.find(child => child.id === id);
  if (!target) return state;
  const cleared = {...state};
  childKeys.forEach(key => { delete cleared[key]; });
  return {...cleared, ...target.data, activeChildId: id, children: all.filter(child => child.id !== id)};
}
export function addChild(state: ParentState): ParentState {
  if (familyList(state).length >= 10) return state;
  const id = randomId();
  return switchChild({...state, children: [...(state.children || []), {id, data: childData(emptyState())}]}, id);
}
export function favoriteAnswer(state: ParentState, message: Message): ParentState {
  const favorites = state.favorites || [], childId = state.activeChildId || 'primary';
  if (favorites.some(item => item.id === message.id && item.childId === childId)) return state;
  const index = state.messages.findIndex(item => item.id === message.id);
  const question = state.messages.slice(0, index).reverse().find(item => item.role === 'user')?.text || '';
  return {...state, favorites: [{id: message.id, childId, childName: state.profile?.childName || (state.profile?.stage === 'pregnancy' ? 'Ожидание малыша' : 'Мой ребёнок'), text: message.text, question, savedAt: new Date().toISOString()}, ...favorites]};
}
