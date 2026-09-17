// Runs before the first paint; the React controls use the same clock and storage.
(function () {
  const key = 'mama-theme';
  const valid = value => ['auto', 'light', 'dark'].includes(value) ? value : 'auto';
  let mode = 'auto';
  try { mode = valid(localStorage.getItem(key)); } catch (_) { /* Private browsing. */ }
  function snapshot() {
    const hour = new Date().getHours();
    const theme = mode === 'auto' ? (hour >= 20 || hour < 7 ? 'dark' : 'light') : mode;
    return { mode, theme };
  }
  function apply() {
    const { theme } = snapshot();
    document.documentElement.classList.toggle('dark', theme === 'dark');
    document.documentElement.style.colorScheme = theme;
    window.dispatchEvent(new CustomEvent('mama-theme-change', { detail: { mode, theme } }));
    return { mode, theme };
  }
  window.mamaTheme = {
    get: snapshot,
    set(value) {
      mode = valid(value);
      try { localStorage.setItem(key, mode); } catch (_) { /* Keep the choice for this tab. */ }
      return apply();
    }
  };
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) { mode = valid(event.newValue); apply(); }
  });
  window.addEventListener('focus', apply);
  document.addEventListener('visibilitychange', apply);
  setInterval(apply, 30000);
  apply();
})();
