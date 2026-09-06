// No caching of authenticated pages or account data.
self.addEventListener('push', event => {
  event.waitUntil(self.registration.showNotification('Мамин помощник', {
    body: 'В вашем кабинете есть возрастная карточка. Откройте её, когда будет удобно.',
    tag: 'parent-age-event', data: { path: '/cabinet' }
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(self.clients.matchAll({type:'window',includeUncontrolled:true}).then(async clients => {
    const client = clients.find(c => new URL(c.url).origin === self.location.origin);
    if (client) { await client.navigate('/cabinet'); return client.focus(); }
    return self.clients.openWindow('/cabinet');
  }));
});
