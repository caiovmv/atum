import { cleanupOutdatedCaches, createHandlerBoundToURL, matchPrecache, precacheAndRoute } from 'workbox-precaching';
import { NavigationRoute, registerRoute, setCatchHandler } from 'workbox-routing';
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

// /api/* não interceptado — evita offline.html em falhas via tunnel (timeout, basic auth, etc.)
// Google Fonts não são interceptadas — o HTTP cache do browser gerencia nativamente
// (Cache-Control: max-age=31536000 definido pelo Google). Interceptar via SW criava
// violação de connect-src no contexto de execução do SW.

// Prompt for update
self.addEventListener('message', (event: ExtendableMessageEvent) => {
  if (event.data?.type === 'SKIP_WAITING') void self.skipWaiting();
});
void self.skipWaiting();
clientsClaim();
