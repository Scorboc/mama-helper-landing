// Scroll until the head begins to lower; the uninterrupted final shot then runs itself.
export const ROOM_CHAT = "/chat?scene=room";
export const ROOM_OUTRO_START = 20.25;
const SEEN_KEY = "mama_room_introduction_seen_v1";
export const roomCues = [
  { id: "play", start: 1.6, end: 4.6, title: "Игры по возрасту", text: "Идеи занятий с понятными шагами.", side: "left", top: 25 },
  { id: "discoveries", start: 7.1, end: 9.7, title: "Новые умения", text: "Сохраняйте открытия и наблюдения.", side: "right", top: 12 },
  { id: "parents", start: 12.7, end: 15.2, title: "Для мамы и папы", text: "Поддержка и дневник самочувствия.", side: "left", top: 10 },
  { id: "diary", start: 18, end: 20.8, title: "Сон, кормления и прикорм", text: "Таймеры, записи и сводка дня.", side: "left", top: 72 },
] as const;
export function rememberRoom() {
  try { localStorage.setItem(SEEN_KEY, "yes"); } catch { /* Navigation also works without storage. */ }
}
export function workspaceReturn(value: string | null) {
  return value && /^\/(?:chat|cabinet)(?:\?[^#]*)?$/.test(value) ? value : "/cabinet";
}
export function accountForRoom(mode = "login") {
  return `/account?mode=${mode}&next=${encodeURIComponent(ROOM_CHAT)}`;
}
export function isRoomLocation(search: string, pathname = "") {
  // The selected room design is the main application, including old bookmarks.
  if (/^\/(?:chat|cabinet|account)$/.test(pathname)) return true;
  const params = new URLSearchParams(search);
  if (params.get("scene") === "room") return true;
  const target = workspaceReturn(params.get("next"));
  return new URLSearchParams(target.split("?")[1]).get("scene") === "room";
}
