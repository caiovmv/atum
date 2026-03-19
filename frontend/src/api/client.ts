/**
 * Cliente de API - encapsula cachedFetch e fetch.
 */
import { cachedFetch, evictCache } from '../hooks/useApiCache';

export { evictCache };

export async function apiGet<T>(
  url: string,
  options?: { staleMs?: number; signal?: AbortSignal }
): Promise<T> {
  return cachedFetch<T>(url, options);
}

export async function apiJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  const text = await res.text();
  if (!text) return null as T;
  return JSON.parse(text) as T;
}

export async function apiFormData(url: string, formData: FormData, options?: Omit<RequestInit, 'body'>): Promise<void> {
  const res = await fetch(url, { method: 'POST', body: formData, ...options });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = Array.isArray(err.detail)
      ? err.detail.map((d: { msg?: string }) => d.msg).join(', ')
      : (err.detail || res.statusText);
    throw new Error(String(msg || res.statusText || 'Erro ao enviar'));
  }
}
