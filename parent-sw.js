// Keep existing daily/birthday/topic links, adding only a validated milestone pair.
function safeCabinetPath(raw) {
  if (typeof raw !== 'string' || !/^\/cabinet(?:\?|$)/.test(raw)) return '/cabinet';
  try {
    const url = new URL(raw, self.location.origin);
    if (url.origin !== self.location.origin || url.pathname !== '/cabinet' || url.hash) return '/cabinet';
    const p = url.searchParams;
    if (p.has('mark')) {
      if ([...p.keys()].some(k => !['mark','child'].includes(k)) || p.getAll('mark').length !== 1 || p.getAll('child').length !== 1 || !['roll','crawl','stand','walk','words'].includes(p.get('mark')) || !/^[a-zA-Z0-9-]{1,100}$/.test(p.get('child') || '')) return '/cabinet';
      return '/cabinet?' + new URLSearchParams({mark:p.get('mark'),child:p.get('child')});
    }
    const allowed = {quick:/^(sleep|feed|note)$/,tab:/^(chat|today)$/,child:/^[a-zA-Z0-9-]{1,100}$/,day:/^\d{4}-\d{2}-\d{2}$/,birthday:/^\d{4}-\d{2}-\d{2}$/,topic:/^[a-zA-Z0-9-]{1,100}$/};
    const clean = new URLSearchParams();
    for (const [key,value] of p) if (allowed[key]?.test(value) && p.getAll(key).length === 1) clean.set(key,value);
    return '/cabinet' + (clean.size ? '?' + clean : '');
  } catch { return '/cabinet'; }
}
// No caching of authenticated pages or account data.
self.addEventListener('push', event => {
  let payload={};
  try { payload=event.data?.json() || {}; } catch { /* Keep a safe generic message. */ }
  const path=safeCabinetPath(payload.path);
  event.waitUntil(self.registration.showNotification('Мамин помощник', {
    body: typeof payload.body==='string' ? payload.body.slice(0,180) : 'Подборка занятий уже готова. Выберите игру, когда будет удобно.',
    tag: 'parent-daily-plan', data: { path }
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const raw=event.notification.data?.path;
  const path=safeCabinetPath(raw);
  event.waitUntil(self.clients.matchAll({type:'window',includeUncontrolled:true}).then(async clients => {
    const client = clients.find(c => new URL(c.url).origin === self.location.origin);
    if (client) { await client.navigate(path); return client.focus(); }
    return self.clients.openWindow(path);
  }));
});
