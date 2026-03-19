import { apiGet, apiJson, evictCache } from './client';
import type { WishlistTerm } from '../types/wishlist';

export async function getWishlist(
  options?: { staleMs?: number; signal?: AbortSignal }
): Promise<WishlistTerm[]> {
  const data = await apiGet<WishlistTerm[]>('/api/wishlist', { staleMs: 30_000, ...options });
  return Array.isArray(data) ? data : [];
}

export async function addWishlistTerm(term: string): Promise<void> {
  await apiJson<unknown>('/api/wishlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ term }),
  });
  evictCache('/api/wishlist');
}

export async function removeWishlistTerm(id: number): Promise<void> {
  await apiJson<unknown>(`/api/wishlist/${id}`, { method: 'DELETE' });
  evictCache('/api/wishlist');
}

export interface RunWishlistResult {
  ok?: number;
  fail?: number;
  detail?: string;
}

export async function runWishlist(body: {
  term_ids?: number[];
  lines?: string[];
  content_type?: string;
  start_now?: boolean;
}): Promise<RunWishlistResult> {
  return apiJson<RunWishlistResult>('/api/wishlist/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}
