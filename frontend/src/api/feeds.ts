import { apiGet, apiJson, evictCache } from './client';
import type { Feed, PendingItem } from '../types/feeds';

export async function getFeeds(
  options?: { staleMs?: number; signal?: AbortSignal }
): Promise<Feed[]> {
  const data = await apiGet<Feed[]>('/api/feeds', { staleMs: 30_000, ...options });
  return Array.isArray(data) ? data : [];
}

export async function getPending(
  options?: { staleMs?: number; signal?: AbortSignal }
): Promise<PendingItem[]> {
  const data = await apiGet<PendingItem[]>('/api/feeds/pending', { staleMs: 15_000, ...options });
  return Array.isArray(data) ? data : [];
}

export async function addFeed(url: string, contentType: string): Promise<void> {
  await apiJson<unknown>('/api/feeds', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, content_type: contentType || 'music' }),
  });
  evictCache('/api/feeds');
}

export async function removeFeed(id: number): Promise<void> {
  await apiJson<unknown>(`/api/feeds/${id}`, { method: 'DELETE' });
  evictCache('/api/feeds');
}

export interface PollResult {
  saved?: number;
  errors?: string[];
}

export async function pollFeeds(): Promise<PollResult> {
  return apiJson<PollResult>('/api/feeds/poll', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
}

export interface AddToDownloadsResult {
  ok?: number;
  fail?: number;
  detail?: string;
}

export async function addPendingToDownloads(
  pendingIds: number[],
  organize: boolean
): Promise<AddToDownloadsResult> {
  const result = await apiJson<AddToDownloadsResult>('/api/feeds/pending/add-to-downloads', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pending_ids: pendingIds, organize }),
  });
  evictCache('/api/feeds/pending');
  return result;
}
