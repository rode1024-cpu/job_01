var CACHE = 'jobcheck-v1';
var FILES = ['./', 'index.html', 'engine.js', 'manifest.webmanifest'];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(FILES); }));
  self.skipWaiting();
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }));
});

self.addEventListener('fetch', function (e) {
  e.respondWith(fetch(e.request).catch(function () { return caches.match(e.request); }));
});

self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  e.waitUntil(self.clients.matchAll({ type: 'window' }).then(function (cs) {
    if (cs.length) return cs[0].focus();
    return self.clients.openWindow('./');
  }));
});
