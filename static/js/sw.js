// Hotel Rhino - Service Worker for PWA
const CACHE_NAME = 'hotel-rhino-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/khana-sets/',
  '/whats-inside-your-thali/',
  '/our-story/',
  '/gallery/',
  '/guest-experiences/',
  '/visit-us/',
  '/static/css/style.css',
  '/static/images/rhino_logo.svg',
  '/static/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Only cache GET requests; network-first for live POS and APIs
  if (event.request.method !== 'GET' || event.request.url.includes('/api/') || event.request.url.includes('/staff/')) {
    return;
  }
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});

// WebPush notification listener
self.addEventListener('push', (event) => {
  let data = { title: 'Hotel Rhino Alert', body: 'New restaurant activity' };
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }
  const options = {
    body: data.body,
    icon: '/static/images/rhino_logo.svg',
    badge: '/static/images/rhino_logo.svg',
    vibrate: [200, 100, 200],
    data: { url: data.url || '/staff/dashboard/' }
  };
  event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url)
  );
});

