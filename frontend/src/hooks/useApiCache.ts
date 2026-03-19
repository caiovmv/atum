/**
 * Cache em memória para respostas de API com suporte a ETag e SWR.
 *
 * Stale-While-Revalidate: retorna dados em cache imediatamente (mesmo que stale)
 * e revalida em background. Só bloqueia na primeira chamada (cache miss).
 */

type CacheEntry<T = unknown> = {
  data: T;
  etag: string | null;
  timestamp: number;
};

const store = new Map<string, CacheEntry>();
const inflightRevalidations = new Set<string>();
const inflightFetches = new Map<string, Promise<unknown>>();

const DEFAULT_STALE_MS = 60_000;

export async function cachedFetch<T = unknown>(
  url: string,
  options?: { staleMs?: number; signal?: AbortSignal },
): Promise<T> {
  const staleMs = options?.staleMs ?? DEFAULT_STALE_MS;
  const entry = store.get(url);

  if (entry) {
    const isFresh = Date.now() - entry.timestamp < staleMs;
    if (isFresh) {
      return entry.data as T;
    }

    if (!inflightRevalidations.has(url)) {
      inflightRevalidations.add(url);
      _revalidate(url, entry).finally(() => inflightRevalidations.delete(url));
    }

    return entry.data as T;
  }

  const existing = inflightFetches.get(url);
  if (existing) return existing as Promise<T>;

  const promise = _fetchAndStore<T>(url, options?.signal);
  inflightFetches.set(url, promise);
  promise.finally(() => inflightFetches.delete(url));
  return promise;
}

async function _fetchAndStore<T>(url: string, signal?: AbortSignal, etag?: string): Promise<T> {
  const headers: HeadersInit = {};
  if (etag) headers['If-None-Match'] = etag;

  const resp = await fetch(url, { headers, signal });

  if (resp.status === 304) {
    const existing = store.get(url);
    if (existing) {
      existing.timestamp = Date.now();
      return existing.data as T;
    }
  }

  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }

  const data = await resp.json();
  store.set(url, {
    data,
    etag: resp.headers.get('etag'),
    timestamp: Date.now(),
  });
  return data as T;
}

async function _revalidate(url: string, entry: CacheEntry): Promise<void> {
  try {
    const headers: HeadersInit = {};
    if (entry.etag) headers['If-None-Match'] = entry.etag;

    const resp = await fetch(url, { headers });

    if (resp.status === 304) {
      entry.timestamp = Date.now();
      return;
    }

    if (!resp.ok) return;

    const data = await resp.json();
    store.set(url, {
      data,
      etag: resp.headers.get('etag'),
      timestamp: Date.now(),
    });
  } catch {
    // revalidation failure is silent — stale data remains usable
  }
}

export function evictCache(pattern: string | RegExp): void {
  for (const key of store.keys()) {
    const match =
      typeof pattern === 'string' ? key.includes(pattern) : pattern.test(key);
    if (match) {
      store.delete(key);
    }
  }
}

export async function evictCoverCache(ids: number[]): Promise<void> {
  try {
    const cache = await caches.open('media-covers');
    const keys = await cache.keys();
    for (const req of keys) {
      for (const id of ids) {
        if (req.url.includes(`/cover/file/${id}`) || req.url.includes(`/cover/file/import/${id}`)) {
          await cache.delete(req);
          break;
        }
      }
    }
  } catch {
    /* Cache API unavailable */
  }
}

export function clearAllCache(): void {
  store.clear();
}
