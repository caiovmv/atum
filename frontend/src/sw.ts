import { cleanupOutdatedCaches, createHandlerBoundToURL, matchPrecache, precacheAndRoute } from 'workbox-precaching';
import { NavigationRoute, registerRoute, setCatchHandler } from 'workbox-routing';
import { CacheFirst, StaleWhileRevalidate } from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';
import { clientsClaim } from 'workbox-core';

declare let self: ServiceWorkerGlobalScope;

const OFFLINE_URL = '/offline.html';

cleanupOutdatedCaches();
precacheAndRoute(self.__WB_MANIFEST);

// Navigation fallback: SPA routes → index.html
registerRoute(
  new NavigationRoute(createHandlerBoundToURL('/index.html'), { denylist: [/^\/api\//] })
);

// Fallback para document quando offline: serve offline.html (precached)
setCatchHandler(async ({ request }) => {
  if (request.destination === 'document') {
    const cached = await matchPrecache(OFFLINE_URL);
    return cached ?? Response.error();
  }
  return Response.error();
});

// Runtime caching (espelhando vite.config workbox)
registerRoute(
  /^https:\/\/fonts\.googleapis\.com\/.*/i,
  new StaleWhileRevalidate({ cacheName: 'google-fonts-stylesheets' })
);
registerRoute(
  /^https:\/\/fonts\.gstatic\.com\/.*/i,
  new CacheFirst({
    cacheName: 'google-fonts-webfonts',
    plugins: [new ExpirationPlugin({ maxEntries: 30, maxAgeSeconds: 60 * 60 * 24 * 365 })],
  })
);

// /api/* não interceptado — evita offline.html em falhas via tunnel (timeout, basic auth, etc.)
// Requisições vão direto à rede; capas usam fetch normal (sem cache SW).

// Prompt for update
self.addEventListener('message', (event: ExtendableMessageEvent) => {
  if (event.data?.type === 'SKIP_WAITING') void self.skipWaiting();
});
void self.skipWaiting();
clientsClaim();
