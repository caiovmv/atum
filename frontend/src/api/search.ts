import { apiGet, apiJson } from './client';
import type { SearchResult, FilterSuggestions } from '../types/search';

export async function getIndexerStatus(
  options?: { staleMs?: number; signal?: AbortSignal }
): Promise<Record<string, boolean>> {
  const data = await apiGet<Record<string, boolean>>('/api/indexers/status', { staleMs: 120_000, ...options });
  return data ?? {};
}

export async function resolveMagnet(indexer: string, torrentId: string): Promise<{ magnet?: string } | null> {
  try {
    return await apiJson<{ magnet?: string }>('/api/search/resolve-magnet', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ indexer, torrent_id: torrentId }),
    });
  } catch {
    return null;
  }
}

export async function getFilterSuggestions(
  params: { content_type: string; q?: string },
  options?: { signal?: AbortSignal }
): Promise<FilterSuggestions> {
  const searchParams = new URLSearchParams(params);
  const data = await apiGet<FilterSuggestions>(`/api/search-filter-suggestions?${searchParams}`, options);
  return data ?? { years: [], genres: [], qualities: [] };
}

export async function searchTorrents(
  params: Record<string, string>,
  options?: { signal?: AbortSignal }
): Promise<SearchResult[]> {
  const searchParams = new URLSearchParams(params);
  const data = await apiGet<SearchResult[]>(`/api/search?${searchParams}`, options);
  return Array.isArray(data) ? data : [];
}
