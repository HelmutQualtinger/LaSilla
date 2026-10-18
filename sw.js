// Service worker: makes the page installable on more browsers and lets it start offline after one visit.
// Own files are network-first (a deploy shows up on the next load), the versioned three.js files from the CDN cache-first.
const CACHE = 'lasilla-v1';
const SHELL = ['./', 'index.html', 'data.js', 'sky.js', 'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/maskable-512.png'];

self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const r = e.request, url = new URL(r.url);
  if (r.method !== 'GET' || r.headers.has('range')) return;                 // the music streams with range requests: leave those to the network
  const put = res => { if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(r, copy)); } return res; };
  if (url.origin === location.origin) e.respondWith(fetch(r).then(put).catch(() => caches.match(r, { ignoreSearch: true })));
  else if (url.hostname === 'cdn.jsdelivr.net') e.respondWith(caches.match(r).then(hit => hit || fetch(r).then(put)));
});
