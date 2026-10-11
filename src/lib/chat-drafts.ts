// Drafts stay in this browser tab, scoped to account, child and conversation.
// No profile/history is copied; private-browsing storage failures are harmless.
const prefix = "mama-chat-draft:";
export function readChatDraft(key: string) {
  try { return (sessionStorage.getItem(prefix + key) || "").slice(0, 2000); }
  catch { return ""; }
}
export function writeChatDraft(key: string, value: string) {
  try {
    if (value) sessionStorage.setItem(prefix + key, value.slice(0, 2000));
    else sessionStorage.removeItem(prefix + key);
  } catch { /* The in-memory draft is still usable. */ }
}
export function clearChatDrafts(accountId: string) {
  try {
    Object.keys(sessionStorage).filter(key => key.startsWith(prefix + accountId + ":"))
      .forEach(key => sessionStorage.removeItem(key));
  } catch { /* Storage may be unavailable. */ }
}
