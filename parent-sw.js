// No caching of authenticated pages or account data.
self.addEventListener('push', event => {
  let payload={};
  try { payload=event.data?.json() || {}; } catch { /* Keep a safe generic message. */ }
  const path=typeof payload.path==='string' && /^\/cabinet(?:\?|$)/.test(payload.path) ? payload.path : '/cabinet';
  event.waitUntil(self.registration.showNotification('Мамин помощник', {
    body: typeof payload.body==='string' ? payload.body.slice(0,180) : 'Подборка занятий уже готова. Выберите игру, когда будет удобно.',
    tag: 'parent-daily-plan', data: { path }
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const raw=event.notification.data?.path;
  const path=typeof raw==='string' && /^\/cabinet(?:\?|$)/.test(raw) ? raw : '/cabinet';
  event.waitUntil(self.clients.matchAll({type:'window',includeUncontrolled:true}).then(async clients => {
    const client = clients.find(c => new URL(c.url).origin === self.location.origin);
    if (client) { await client.navigate(path); return client.focus(); }
    return self.clients.openWindow(path);
  }));
});
